from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional, Sequence
import math
from io import BytesIO

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from reportlab.lib.pagesizes import letter
from reportlab.platypus import (
    SimpleDocTemplate,
    Table,
    TableStyle,
    Paragraph,
    PageBreak,
    Image,
    Spacer,
)
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet

# =========================
# Config / Helpers
# =========================


@dataclass(frozen=True)
class ReportConfig:
    # Fontes core (Helvetica) nao suportam Unicode completo -> evite caracteres tipo "—", "→", aspas curvas etc.
    title: str = "Verificador Inteligente de Orçamentos de Obras - Validador LPU"
    subtitle: str = "Resultado da execução"
    author: str = "Auto-report"
    max_categorical_top: int = 5
    max_plots: int = 8
    clip_quantiles: tuple[float, float] = (0.01, 0.99)  # p1-p99
    prefer_columns: tuple[str, ...] = (
        "VALOR TOTAL PAGO",
        "DIFERENÇA TOTAL",
        "DISCREPÂNCIA PERCENTUAL",
        "PRECO PAGO",
        "PRECO LPU",
    )
    status_column: str = "STATUS CONCILIAÇÃO"
    currency_columns_hint: tuple[str, ...] = ("VALOR", "PRECO", "PREÇO", "R$", "TOTAL")
    percent_columns_hint: tuple[str, ...] = ("%", "PERCENT", "DISCREP", "DISCREPÂNCIA")


def _pdf_safe_text(s: str) -> str:
    if s is None:
        return ""
    s = str(s)
    s = (
        s.replace("—", "-")
        .replace("–", "-")
        .replace("−", "-")
        .replace("→", "->")
        .replace("•", "-")
        .replace("“", '"')
        .replace("”", '"')
        .replace("’", "'")
        .replace("‘", "'")
        .replace("\u00a0", " ")
    )
    return s.encode("latin-1", "ignore").decode("latin-1")


def _fmt_int(x) -> str:
    try:
        return f"{int(x):,}".replace(",", ".")
    except Exception:
        return str(x)


def _fmt_float(x, ndigits: int = 2) -> str:
    try:
        # Ensure the input is a valid float
        v = float(str(x).replace(",", "").strip())
        s = f"{v:,.{ndigits}f}"
        return s.replace(",", "X").replace(".", ",").replace("X", ".")
    except ValueError:
        return str(x)  # Return the original value if conversion fails


def _fmt_money(x) -> str:
    try:
        return f"R$ {_fmt_float(float(x), 2)}"
    except Exception:
        return str(x)


def _is_percent_col(name: str, cfg: ReportConfig) -> bool:
    n = (name or "").upper()
    return any(h.upper() in n for h in cfg.percent_columns_hint)


def _is_currency_col(name: str, cfg: ReportConfig) -> bool:
    n = (name or "").upper()
    return any(h.upper() in n for h in cfg.currency_columns_hint)


def _safe_filename(name: str, max_len: int = 80) -> str:
    name = str(name).strip().replace("\n", " ")
    keep = []
    for ch in name:
        if ch.isalnum() or ch in ("_", "-", ".", " "):
            keep.append(ch)
    out = "".join(keep).strip().replace(" ", "_")
    return out[:max_len] if len(out) > max_len else out


def _freedman_diaconis_bins(x: np.ndarray, max_bins: int = 80) -> int:
    x = x[~np.isnan(x)]
    n = x.size
    if n < 2:
        return 10
    q25, q75 = np.percentile(x, [25, 75])
    iqr = q75 - q25
    if iqr <= 0:
        return min(30, max(10, int(math.sqrt(n))))
    bin_width = 2 * iqr / (n ** (1 / 3))
    if bin_width <= 0:
        return min(30, max(10, int(math.sqrt(n))))
    bins = int(np.ceil((x.max() - x.min()) / bin_width))
    return int(np.clip(bins, 10, max_bins))


def _clip_series(s: pd.Series, q_low: float, q_high: float) -> pd.Series:
    s = pd.to_numeric(s, errors="coerce")
    if s.dropna().empty:
        return s
    lo, hi = s.quantile([q_low, q_high]).values
    return s.clip(lower=lo, upper=hi)


# =========================
# Main function
# =========================


def generate_statistics_report(
    df: pd.DataFrame,
    output_pdf: str,
    *,
    cfg: Optional[ReportConfig] = None
) -> None:
    cfg = cfg or ReportConfig()

    out_path = Path(output_pdf)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    doc = SimpleDocTemplate(
        str(out_path), pagesize=letter, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=18
    )
    elements = []

    styles = getSampleStyleSheet()
    title = Paragraph(cfg.title, styles['Title'])
    subtitle = Paragraph(cfg.subtitle, styles['Heading2'])
    elements.extend([title, subtitle])

    # -------------------------
    # Contextualização
    # -------------------------

    elements.append(Paragraph("Padrão de cálculo adotado:", styles["Heading2"]))

    context_text = """DIFERENÇA = VALOR_PAGO - VALOR_LPU
    ---------------------------------------------------------------------------
    INTERPRETAÇÃO DO SINAL
    ---------------------------------------------------------------------------
    - DIFERENÇA > 0 → Pagamento acima da LPU (sobrepreço)
    - DIFERENÇA = 0 → Total aderência à LPU.
    - DIFERENÇA < 0 → Pagamento abaixo da LPU (subpreço).
    """
    elements.append(Paragraph(context_text.replace("\n", "<br />"), styles["BodyText"]))

    # -------------------------
    # Resumo Geral
    # -------------------------
    n_rows = len(df)
    n_budgets = df["SOURCE_FILE"].nunique() if "SOURCE_FILE" in df.columns else 1
    total_difference = df["DIFERENÇA TOTAL"].sum() if "DIFERENÇA TOTAL" in df.columns else 0
    potential_recovery = (
        df["DIFERENÇA TOTAL"][df["DIFERENÇA TOTAL"] > 0].sum()
        if "DIFERENÇA TOTAL" in df.columns
        else 0
    )

    summary_data = [
        ["Indicador", "Valor"],
        ["Orçamentos analisados", f"{n_budgets:,}"],
        ["Itens analisados", f"{n_rows:,}"],
        ["Diferença total (R$)", f"R$ {total_difference:,.2f}"],
        ["Potencial de recuperação (R$)", f"R$ {potential_recovery:,.2f}"],
    ]

    summary_table = Table(summary_data, colWidths=[200, 200])
    summary_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.darkblue),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
                ("BACKGROUND", (0, 1), (-1, -1), colors.lightgrey),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
            ]
        )
    )
    elements.append(Paragraph("Resumo Geral:", styles["Heading2"]))
    elements.append(summary_table)

    # -------------------------
    # Resumo por Região
    # -------------------------
    if "REGIAO" in df.columns:
        region_summary = (
            df.groupby("REGIAO")
            .agg(
                quantidade=("DIFERENÇA TOTAL", "count"),
                soma_diferenca=("DIFERENÇA TOTAL", "sum"),
                potencial_recuperacao=("DIFERENÇA TOTAL", lambda x: x[x > 0].sum()),
                orcamentos_distintos=(
                    ("SOURCE_FILE", "nunique") if "SOURCE_FILE" in df.columns else None
                ),
                agencias_distintas=(
                    ("NUMERO_AGENCIA", "nunique") if "NUMERO_AGENCIA" in df.columns else None
                ),
            )
            .reset_index()
        )

        elements.append(Paragraph("Resumo por Região:", styles["Heading2"]))

        for _, row in region_summary.iterrows():
            region_data = [
                ["Região", row["REGIAO"]],
                ["Itens", f"{row['quantidade']:,}"],
                ["Diferença Total (R$)", f"R$ {row['soma_diferenca']:,.2f}"],
                ["Potencial Recuperação (R$)", f"R$ {row['potencial_recuperacao']:,.2f}"],
                [
                    "Orçamentos Distintos",
                    (
                        f"{row['orcamentos_distintos']:,}"
                        if row["orcamentos_distintos"] is not None
                        else "-"
                    ),
                ],
                [
                    "Agências Distintas",
                    (
                        f"{row['agencias_distintas']:,}"
                        if row["agencias_distintas"] is not None
                        else "-"
                    ),
                ],
            ]

            region_table = Table(region_data, colWidths=[200, 200])
            region_table.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), colors.darkblue),
                        ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                        ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
                        ("BACKGROUND", (0, 1), (-1, -1), colors.lightgrey),
                        ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
                    ]
                )
            )
            elements.append(region_table)
            elements.append(Spacer(1, 12))

    # -------------------------
    # Resumo por Agência
    # -------------------------
    if "NUMERO_AGENCIA" in df.columns:
        agency_summary = (
            df.groupby("NUMERO_AGENCIA")
            .agg(
                quantidade=("DIFERENÇA TOTAL", "count"),
                soma_diferenca=("DIFERENÇA TOTAL", "sum"),
                potencial_recuperacao=("DIFERENÇA TOTAL", lambda x: x[x > 0].sum()),
            )
            .reset_index()
        )

        agency_data = [["Agência", "Itens", "Diferença Total (R$)", "Potencial Recuperação (R$)"]]
        for _, row in agency_summary.iterrows():
            agency_data.append(
                [
                    row["NUMERO_AGENCIA"],
                    f"{row['quantidade']:,}",
                    f"R$ {row['soma_diferenca']:,.2f}",
                    f"R$ {row['potencial_recuperacao']:,.2f}",
                ]
            )

        agency_table = Table(agency_data, colWidths=[100, 100, 150, 150])
        agency_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.darkblue),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
                    ("BACKGROUND", (0, 1), (-1, -1), colors.lightgrey),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
                ]
            )
        )
        elements.append(Paragraph("Resumo por Agência:", styles["Heading2"]))
        elements.append(agency_table)

    # -------------------------
    # Finaliza o relatório
    # -------------------------
    execution_datetime = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    footer = Paragraph(f"Relatório gerado em: {execution_datetime}", styles['BodyText'])

    # Add footer to the bottom of the document
    def add_footer(canvas, doc):
        canvas.saveState()
        canvas.setFont('Helvetica', 9)
        canvas.drawString(30, 15, f"Relatório gerado em: {execution_datetime}")
        canvas.restoreState()

    doc.build(elements, onFirstPage=add_footer, onLaterPages=add_footer)

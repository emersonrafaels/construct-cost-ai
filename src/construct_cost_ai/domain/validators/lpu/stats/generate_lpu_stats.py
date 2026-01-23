"""
Relatório Executivo — Validador LPU (PDF)
----------------------------------------
Gera um PDF em formato "negócios" com:
- KPIs principais
- Distribuição de status
- Pareto de ressarcimento (Top N agências)
- Top N construtoras por ressarcimento

Inclui uma função orquestradora `run_lpu_validation_reporting(...)`.

⚠️ Fix principal: ReportLab no Windows pode falhar com WindowsPath.
Por isso, TODOS os caminhos são convertidos para str logo no início.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, Union

import pandas as pd
import matplotlib.pyplot as plt

from reportlab.lib.pagesizes import A4
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    Image,
    PageBreak,
)
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import cm

from config.config_logger import logger
from config.config_dynaconf import get_settings

settings = get_settings()


# -------------------------
# Path & formatting helpers
# -------------------------
PathLike = Union[str, Path]


def _as_path_str(p: PathLike) -> str:
    """Normalize path-like to a plain string (ReportLab-friendly)."""
    return str(Path(p))


def _safe_mkdir(p: Path) -> None:
    p.mkdir(parents=True, exist_ok=True)


def _brl(x: float) -> str:
    """Format float as BRL currency (pt-BR)."""
    try:
        s = f"{float(x):,.2f}"
        return "R$ " + s.replace(",", "X").replace(".", ",").replace("X", ".")
    except Exception:
        return str(x)


def _to_numeric_series(df: pd.DataFrame, col: str) -> pd.Series:
    return pd.to_numeric(df[col], errors="coerce").fillna(0.0)


# -------------------------
# Config resolution
# -------------------------
def _get_cfg(settings) -> Dict[str, Any]:
    """
    Centraliza todas as colunas/status.
    Ajuste aqui e o relatório todo acompanha.
    """
    return {
        # colunas
        "col_status": settings.get("module_validator_lpu.column_status", "VALIDADOR_LPU"),
        "col_total_paid": settings.get(
            "module_validator_lpu.column_total_paid", "VALOR TOTAL PAGO"
        ),
        "col_difference": settings.get("module_validator_lpu.column_difference", "DIFERENÇA TOTAL"),
        "col_total_lpu": settings.get("module_validator_lpu.column_total_lpu", "VALOR TOTAL LPU"),
        "col_agency": settings.get("module_validator_lpu.column_agency", "NUMERO_AGENCIA"),
        "col_city": settings.get("module_validator_lpu.column_city", "MUNICIPIO"),
        "col_uf": settings.get("module_validator_lpu.column_uf", "UF"),
        "col_constructor": settings.get("module_validator_lpu.column_constructor", "CONSTRUTORA"),
        # status
        "status_ok": settings.get("module_validator_lpu.status_ok", "OK"),
        "status_refund": settings.get("module_validator_lpu.status_refund", "PARA RESSARCIMENTO"),
        "status_below": settings.get("module_validator_lpu.status_below", "ABAIXO LPU"),
        "status_not_lpu": settings.get("module_validator_lpu.status_not_lpu", "ITEM_NAO_LPU"),
    }


# -------------------------
# Normalization
# -------------------------
def normalize_lpu_result(df: pd.DataFrame, cfg: Dict[str, Any]) -> pd.DataFrame:
    """
    Normaliza status e colunas numéricas (sem efeitos colaterais).
    """
    df = df.copy()

    col_status = cfg["col_status"]
    if col_status not in df.columns:
        raise KeyError(f"Coluna de status ausente: '{col_status}'")

    # padroniza status (evita: "Para ressarcimento" vs "PARA RESSARCIMENTO")
    df[col_status] = df[col_status].astype(str).str.strip().str.upper()

    # colunas numéricas obrigatórias
    for col in (cfg["col_total_paid"], cfg["col_difference"]):
        if col not in df.columns:
            raise KeyError(f"Coluna numérica ausente: '{col}'")
        df[col] = _to_numeric_series(df, col)

    # LPU total é opcional
    col_lpu = cfg.get("col_total_lpu")
    if col_lpu and col_lpu in df.columns:
        df[col_lpu] = _to_numeric_series(df, col_lpu)

    return df


# -------------------------
# PDF Executive renderer
# -------------------------
def generate_statistics_report_business(
    df_result: pd.DataFrame,
    output_pdf: PathLike,
    *,
    cfg: Optional[Dict[str, Any]] = None,
    workdir: Optional[PathLike] = None,
    top_n: int = 10,
) -> None:
    """
    Gera um relatório executivo (negócios) em PDF com:
      - KPIs principais
      - Distribuição de status
      - Pareto de ressarcimento (Top N agências)
      - Top N construtoras por ressarcimento

    Importante: `output_pdf` é convertido para `str` internamente (WindowsPath safe).
    """

    # ✅ reportlab/windows-safe: sempre string
    output_pdf_str = _as_path_str(output_pdf)

    cfg = cfg or {}
    col_status = cfg.get("col_status", "VALIDADOR_LPU")
    col_paid = cfg.get("col_total_paid", "VALOR TOTAL PAGO")
    col_lpu_total = cfg.get("col_total_lpu", "VALOR TOTAL LPU")  # opcional
    col_diff = cfg.get("col_difference", "DIFERENÇA TOTAL")

    col_agency = cfg.get("col_agency", "NUMERO_AGENCIA")
    col_city = cfg.get("col_city", "MUNICIPIO")
    col_uf = cfg.get("col_uf", "UF")
    col_constructor = cfg.get("col_constructor", "CONSTRUTORA")

    status_ok = cfg.get("status_ok", "OK")
    status_refund = cfg.get("status_refund", "PARA RESSARCIMENTO")
    status_below = cfg.get("status_below", "ABAIXO LPU")

    # Defensive checks
    required = [col_status, col_paid, col_diff]
    missing = [c for c in required if c not in df_result.columns]
    if missing:
        raise KeyError(f"Colunas obrigatórias ausentes: {missing}")

    df = df_result.copy()

    # Normalizações locais (para garantir standalone)
    df[col_status] = df[col_status].astype(str).str.strip().str.upper()
    df[col_paid] = _to_numeric_series(df, col_paid)
    df[col_diff] = _to_numeric_series(df, col_diff)

    if col_lpu_total in df.columns:
        df[col_lpu_total] = _to_numeric_series(df, col_lpu_total)

    # KPIs
    total_items = len(df)
    total_paid = float(df[col_paid].sum())
    total_lpu = float(df[col_lpu_total].sum()) if col_lpu_total in df.columns else 0.0
    total_div = float(df[col_diff].sum())

    refund_value = float(df.loc[df[col_status].eq(status_refund), col_diff].sum())
    below_abs = float((-df.loc[df[col_status].eq(status_below), col_diff]).sum())

    # Status distribution
    status_counts = df[col_status].value_counts().rename_axis("STATUS").reset_index(name="ITENS")
    status_counts["%"] = (
        (status_counts["ITENS"] / total_items * 100).round(1) if total_items else 0.0
    )

    # Pareto: top agencies by refund
    if all(c in df.columns for c in [col_agency, col_city, col_uf]):
        pareto = (
            df[df[col_status].eq(status_refund)]
            .groupby([col_agency, col_city, col_uf])[col_diff]
            .sum()
            .sort_values(ascending=False)
            .head(top_n)
            .reset_index()
        )
    else:
        pareto = pd.DataFrame(columns=[col_agency, col_city, col_uf, col_diff])

    # Top constructors by refund
    if col_constructor in df.columns:
        top_const = (
            df[df[col_status].eq(status_refund)]
            .groupby(col_constructor)[col_diff]
            .sum()
            .sort_values(ascending=False)
            .head(top_n)
            .reset_index()
        )
    else:
        top_const = pd.DataFrame(columns=[col_constructor, col_diff])

    # Workdir for chart images
    work = Path(workdir) if workdir else Path(output_pdf_str).resolve().parent / ".tmp_lpu_report"
    _safe_mkdir(work)

    chart_status = work / "status_bar.png"
    chart_pareto = work / "refund_pareto.png"

    # Chart 1: status bar
    plt.figure(figsize=(7.2, 3.6))
    plt.bar(status_counts["STATUS"], status_counts["ITENS"])
    plt.xticks(rotation=20, ha="right")
    plt.ylabel("Qtde de itens")
    plt.title(f"Distribuição de status ({col_status})")
    plt.tight_layout()
    plt.savefig(_as_path_str(chart_status), dpi=200)
    plt.close()

    # Chart 2: pareto agencies
    plt.figure(figsize=(7.2, 3.6))
    if len(pareto) > 0:
        plt.bar(pareto[col_agency].astype(str), pareto[col_diff])
        plt.ylabel("R$ (diferença total)")
        plt.title(f"Top {top_n} agências por potencial ressarcimento")
        plt.tight_layout()
    else:
        plt.title("Top agências por potencial ressarcimento")
        plt.text(0.5, 0.5, f"Sem dados em {status_refund}", ha="center")
        plt.axis("off")
    plt.savefig(_as_path_str(chart_pareto), dpi=200)
    plt.close()

    # -------------------------
    # PDF (ReportLab)
    # -------------------------
    styles = getSampleStyleSheet()
    title_style = styles["Title"]
    h2 = styles["Heading2"]
    body = styles["BodyText"]

    doc = SimpleDocTemplate(
        output_pdf_str,  # ✅ sempre str
        pagesize=A4,
        rightMargin=1.6 * cm,
        leftMargin=1.6 * cm,
        topMargin=1.4 * cm,
        bottomMargin=1.4 * cm,
    )

    elements = []
    elements.append(Paragraph("Relatório Executivo — Validador LPU", title_style))
    elements.append(Paragraph(f"Gerado em {datetime.now().strftime('%d/%m/%Y %H:%M')}", body))
    elements.append(Spacer(1, 10))

    # KPI table
    kpi_data = [
        ["Itens analisados", f"{total_items:,}".replace(",", ".")],
        ["Valor total pago", _brl(total_paid)],
        [
            "Valor total LPU (onde aplicável)",
            _brl(total_lpu) if col_lpu_total in df.columns else "—",
        ],
        ["Diferença total (pago - LPU)", _brl(total_div)],
        [f"Potencial ressarcimento ({status_refund})", _brl(refund_value)],
        [f"Volume {status_below} (|dif|)", _brl(below_abs)],
    ]
    kpi_table = Table(kpi_data, colWidths=[8.5 * cm, 7.5 * cm])
    kpi_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.whitesmoke),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("BACKGROUND", (0, 0), (-1, -1), colors.white),
            ]
        )
    )

    elements.append(Paragraph("Resumo de KPIs", h2))
    elements.append(kpi_table)
    elements.append(Spacer(1, 12))

    # Status section
    elements.append(Paragraph("Distribuição de status", h2))
    elements.append(Image(_as_path_str(chart_status), width=16.5 * cm, height=8 * cm))
    elements.append(Spacer(1, 8))

    status_tbl = Table(
        [["STATUS", "ITENS", "%"]] + status_counts.values.tolist(),
        colWidths=[7.5 * cm, 4 * cm, 4 * cm],
    )
    status_tbl.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.whitesmoke),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
            ]
        )
    )
    elements.append(status_tbl)
    elements.append(PageBreak())

    # Pareto section
    elements.append(Paragraph("Pareto de ressarcimento (drill-down)", h2))
    elements.append(
        Paragraph("Concentradores de impacto financeiro para priorização de tratativas.", body)
    )
    elements.append(Spacer(1, 8))
    elements.append(Image(_as_path_str(chart_pareto), width=16.5 * cm, height=8 * cm))
    elements.append(Spacer(1, 10))

    if len(pareto) > 0:
        pareto_fmt = pareto.copy()
        pareto_fmt[col_diff] = pareto_fmt[col_diff].map(_brl)

        t = Table(
            [[str(col_agency), "MUNICÍPIO", "UF", "POTENCIAL (R$)"]] + pareto_fmt.values.tolist(),
            colWidths=[3.2 * cm, 7.0 * cm, 1.2 * cm, 4.6 * cm],
        )
        t.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.whitesmoke),
                    ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                ]
            )
        )
        elements.append(t)
    else:
        elements.append(Paragraph(f"Não há registros em '{status_refund}' nesta base.", body))

    elements.append(Spacer(1, 14))

    # Top constructors
    elements.append(Paragraph("Top construtoras por potencial ressarcimento", h2))
    if len(top_const) > 0:
        tc = top_const.copy()
        tc[col_diff] = tc[col_diff].map(_brl)

        t2 = Table(
            [["CONSTRUTORA", "POTENCIAL (R$)"]] + tc.values.tolist(),
            colWidths=[11.5 * cm, 5.0 * cm],
        )
        t2.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.whitesmoke),
                    ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                ]
            )
        )
        elements.append(t2)
    else:
        elements.append(Paragraph("Sem dados de construtora para ranking.", body))

    doc.build(elements)


# -------------------------
# Orchestrator (entrypoint)
# -------------------------
def run_lpu_validation_reporting(
    *,
    df_result: pd.DataFrame,
    validator_output_pdf: Optional[bool] = None,
    output_pdf: PathLike = "VALIDADOR_LPU_EXECUTIVO.pdf",
    verbose: Optional[bool] = None,
    top_n: int = 10,
    workdir: Optional[PathLike] = None,
) -> None:
    """
    Orquestra (novo):
      - normaliza df
      - loga um resumo
      - gera PDF no formato executivo (novo)

    Fix WindowsPath: `output_pdf` é convertido para str antes de chegar no ReportLab.
    """

    if validator_output_pdf is None:
        validator_output_pdf = settings.get("module_validator_lpu.stats.validator_output_pdf", True)

    if verbose is None:
        verbose = settings.get("module_validator_lpu.verbose", True)

    cfg = _get_cfg(settings)
    df_norm = normalize_lpu_result(df_result, cfg)

    output_pdf_str = _as_path_str(output_pdf)  # ✅ blindagem
    workdir_str = _as_path_str(workdir) if workdir is not None else None

    if verbose:
        logger.info("📄 Gerando relatório executivo (Validador LPU)...")
        logger.info(f"Itens: {len(df_norm)} | PDF: {output_pdf_str}")

    if validator_output_pdf:
        generate_statistics_report_business(
            df_norm,
            output_pdf=output_pdf_str,
            workdir=workdir_str,
            top_n=top_n,
            cfg={
                "col_status": cfg["col_status"],
                "col_total_paid": cfg["col_total_paid"],
                "col_difference": cfg["col_difference"],
                "col_total_lpu": cfg.get("col_total_lpu", "VALOR TOTAL LPU"),
                "col_agency": cfg.get("col_agency", "NUMERO_AGENCIA"),
                "col_city": cfg.get("col_city", "MUNICIPIO"),
                "col_uf": cfg.get("col_uf", "UF"),
                "col_constructor": cfg.get("col_constructor", "CONSTRUTORA"),
                "status_ok": cfg["status_ok"],
                "status_refund": cfg["status_refund"],
                "status_below": cfg["status_below"],
            },
        )
        logger.info(f"✅ Relatório executivo gerado: {output_pdf_str}")
    else:
        logger.info("Geração de relatório em PDF desativada.")

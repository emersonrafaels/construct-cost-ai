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


def format_value(value, value_type='float', ndigits=2):
    """
    Formata valores numéricos.

    :param value: Valor a ser formatado.
    :param value_type: Tipo do valor ('int', 'float', 'money').
    :param ndigits: Número de casas decimais (para floats).
    :return: Valor formatado como string.
    """
    try:
        if value_type == 'int':
            return f"{int(value):,}".replace(",", ".")
        elif value_type == 'float':
            return f"{float(value):,.{ndigits}f}".replace(",", "X").replace(".", ",").replace("X", ".")
        elif value_type == 'money':
            return f"R$ {format_value(value, 'float', ndigits)}"
    except Exception:
        return "-"


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


def add_table(elements, data, col_widths=None, title=None, title_style='Heading2', table_style=None):
    """
    Adiciona uma tabela ao PDF.

    :param elements: Lista de elementos do PDF.
    :param data: Dados da tabela (lista de listas).
    :param col_widths: Largura das colunas (opcional).
    :param title: Título da tabela (opcional).
    :param title_style: Estilo do título (padrão: 'Heading2').
    :param table_style: Estilo da tabela (opcional).
    """
    if title:
        elements.append(Paragraph(title, getSampleStyleSheet()[title_style]))
    table = Table(data, colWidths=col_widths)
    table.setStyle(table_style or TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.lightgrey),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
    ]))
    elements.append(table)
    elements.append(Spacer(1, 12))


def add_paragraph(elements, text, style='BodyText'):
    """
    Adiciona um parágrafo ao PDF.

    :param elements: Lista de elementos do PDF.
    :param text: Texto do parágrafo.
    :param style: Estilo do parágrafo (padrão: 'BodyText').
    """
    elements.append(Paragraph(text, getSampleStyleSheet()[style]))


def add_page_break(elements):
    """
    Adiciona uma quebra de página ao PDF.

    :param elements: Lista de elementos do PDF.
    """
    elements.append(PageBreak())


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

    # -------------------------
    # Título e Subtítulo
    # -------------------------
    add_paragraph(elements, cfg.title, style='Title')
    add_paragraph(elements, cfg.subtitle, style='Heading2')

    # -------------------------
    # Contextualização
    # -------------------------
    add_paragraph(elements, "Padrão de cálculo adotado:", style='Heading2')
    context_text = """DIFERENÇA = VALOR_PAGO - VALOR_LPU
    ---------------------------------------------------------------------------
    - DIFERENÇA > 0 → Pagamento acima da LPU (sobrepreço)
    - DIFERENÇA = 0 → Total aderência à LPU.
    - DIFERENÇA < 0 → Pagamento abaixo da LPU (subpreço).
    """
    add_paragraph(elements, context_text.replace("\n", "<br />"))

    # -------------------------
    # Resumo Geral
    # -------------------------
    n_rows = len(df)
    n_budgets = df['SOURCE_FILE'].nunique() if 'SOURCE_FILE' in df.columns else 1
    total_difference = df['DIFERENÇA TOTAL'].sum() if 'DIFERENÇA TOTAL' in df.columns else 0
    potential_recovery = df['DIFERENÇA TOTAL'][df['DIFERENÇA TOTAL'] > 0].sum() if 'DIFERENÇA TOTAL' in df.columns else 0

    summary_data = [
        ["Indicador", "Valor"],
        ["Orçamentos analisados", format_value(n_budgets, 'int')],
        ["Itens analisados", format_value(n_rows, 'int')],
        ["Diferença total (R$)", format_value(total_difference, 'money')],
        ["Potencial de recuperação (R$)", format_value(potential_recovery, 'money')],
    ]
    add_table(elements, summary_data, col_widths=[200, 200], title="Resumo Geral:")

    # -------------------------
    # Resumo por Região
    # -------------------------
    add_paragraph(elements, "Resumo por Região:", style='Heading2')
    if 'REGIAO' in df.columns:
        region_summary = df.groupby('REGIAO').agg(
            quantidade=('DIFERENÇA TOTAL', 'count'),
            soma_diferenca=('DIFERENÇA TOTAL', 'sum'),
            potencial_recuperacao=('DIFERENÇA TOTAL', lambda x: x[x > 0].sum()),
            orcamentos_distintos=('SOURCE_FILE', 'nunique') if 'SOURCE_FILE' in df.columns else None,
            agencias_distintas=('NUMERO_AGENCIA', 'nunique') if 'NUMERO_AGENCIA' in df.columns else None
        ).reset_index()

        for _, row in region_summary.iterrows():
            region_data = [
                ["Região", row['REGIAO']],
                ["Orçamentos Distintos", format_value(row['orcamentos_distintos'], 'int') if row['orcamentos_distintos'] is not None else "-"],
                ["Agências Distintas", format_value(row['agencias_distintas'], 'int') if row['agencias_distintas'] is not None else "-"],
                ["Itens", format_value(row['quantidade'], 'int')],
                ["Diferença Total (R$)", format_value(row['soma_diferenca'], 'money')],
                ["Potencial Recuperação (R$)", format_value(row['potencial_recuperacao'], 'money')]
            ]
            add_table(elements, region_data, col_widths=[200, 200])

    # -------------------------
    # Glossário
    # -------------------------
    add_page_break(elements)

    # Adjust glossary data to ensure text fits within the correct columns
    glossary_data = [
        ["Termo", "Definição"],
        ["Diferença Total", "Diferença entre o valor pago e o valor da LPU."],
        ["Potencial Recuperação", "Soma das diferenças positivas."],
        ["Orçamentos Distintos", "Número de arquivos únicos."],
        ["Agências Distintas", "Número de agências únicas."],
        ["Itens", "Quantidade total de itens analisados."]
    ]

    add_paragraph(elements, "Glossário:", style='Heading1')
    add_table(elements, glossary_data, col_widths=[200, 300], title="Glossário de Termos")

    # -------------------------
    # Finaliza o relatório
    # -------------------------
    execution_datetime = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    def add_footer(canvas, doc):
        canvas.saveState()
        canvas.setFont('Helvetica', 9)
        canvas.drawString(30, 15, f"Relatório gerado em: {execution_datetime}")
        canvas.restoreState()

    doc.build(elements, onFirstPage=add_footer, onLaterPages=add_footer)

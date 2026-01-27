"""
Relatório Executivo — Validador LPU (PDF) — vNext (apresentação executiva)

Ajustes solicitados:
✅ Tabelas de itens: remover coluna "Chave" (fica: Item | Qtd | % | Valor)
✅ Voltar "Top Agências" (como antes) com gráfico + tabela
✅ Reordenar seções do PDF para:
   1) Resumo executivo (KPIs + Distribuição de status)
   2) Top Agências
   3) Top Fornecedores/Construtoras
   4) Top Itens (LPU e NÃO LPU)

Notas:
- LPU vs NÃO LPU continua baseado em STATUS == status_not_lpu (canônico)
- Top agências usa colunas (NUMERO_AGENCIA, MUNICIPIO, UF) e soma DIFERENÇA TOTAL
- Percentuais:
    - Top itens LPU: % sobre total de itens LPU
    - Top itens NÃO LPU: % sobre total de itens NÃO LPU
- Fix WindowsPath/ReportLab: sempre converte caminhos para str no build/imagens.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, Union, Tuple, List, Any as AnyType

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
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm

from config.config_logger import logger
from config.config_dynaconf import get_settings

settings = get_settings()

PathLike = Union[str, Path]


# -------------------------
# Helpers
# -------------------------
def _as_path_str(p: PathLike) -> str:
    return str(Path(p))


def _safe_mkdir(p: Path) -> None:
    p.mkdir(parents=True, exist_ok=True)


def _brl(x: float) -> str:
    try:
        s = f"{float(x):,.2f}"
        return "R$ " + s.replace(",", "X").replace(".", ",").replace("X", ".")
    except Exception:
        return str(x)


def _to_numeric_series(df: pd.DataFrame, col: str) -> pd.Series:
    return pd.to_numeric(df[col], errors="coerce").fillna(0.0)


def _fmt_int(n: int) -> str:
    return f"{int(n):,}".replace(",", ".")


def _fmt_pct(x: float) -> str:
    try:
        return f"{float(x):.1f}%".replace(".", ",")
    except Exception:
        return str(x)


def _canon_status(s: AnyType) -> str:
    s = "" if s is None else str(s)
    s = s.strip().upper().replace("_", " ")
    s = " ".join(s.split())
    return s


def _infer_budget_count(df: pd.DataFrame, *, verbose: bool) -> int:
    candidate_cols = [
        "ID_ORCAMENTO",
        "ORCAMENTO_ID",
        "NUM_ORCAMENTO",
        "ORCAMENTO",
        "COD_ORCAMENTO",
        "ORC_ID",
        "SOURCE_FILE",
        "ARQUIVO_ORCAMENTO",
        "NOME_ARQUIVO",
        "FILE_NAME",
    ]
    for c in candidate_cols:
        if c in df.columns:
            n = int(df[c].nunique(dropna=True))
            if n > 0:
                return n
    if verbose:
        logger.warning(
            "Não encontrei coluna identificadora de orçamento (ex: SOURCE_FILE/ID_ORCAMENTO). Assumindo 1 orçamento."
        )
    return 1


def _pick_item_columns(df: pd.DataFrame, cfg: Dict[str, Any]) -> Tuple[str, str]:
    col_item_id = cfg.get("col_item_id", "ID ITEM")
    col_item_name = cfg.get("col_item_name", "NOME ITEM")

    if col_item_id not in df.columns:
        for alt in ["CÓD ITEM", "COD ITEM", "ID", "CODIGO", "COD_LPU"]:
            if alt in df.columns:
                col_item_id = alt
                break

    if col_item_name not in df.columns:
        for alt in ["ITEM", "DESC ITEM", "DESCRICAO", "NOME"]:
            if alt in df.columns:
                col_item_name = alt
                break

    if col_item_id not in df.columns or col_item_name not in df.columns:
        raise KeyError(
            f"Não encontrei colunas de item para ranking. Tentado: '{col_item_id}'/'{col_item_name}'."
        )
    return col_item_id, col_item_name


def _top_items(
    df: pd.DataFrame,
    *,
    col_item_id: str,
    col_item_name: str,
    col_paid: str,
    n: int,
    denom_for_pct: int,
) -> pd.DataFrame:
    g = (
        df.groupby([col_item_id, col_item_name], dropna=False)
        .agg(qtd=(col_item_name, "size"), valor=(col_paid, "sum"))
        .reset_index()
        .sort_values(["qtd", "valor"], ascending=[False, False])
        .head(int(n))
    )
    denom = max(int(denom_for_pct), 1)
    g["pct"] = (g["qtd"] / denom * 100.0).round(1)
    return g


# -------------------------
# Config + Normalization
# -------------------------
def _get_cfg(settings) -> Dict[str, Any]:
    return {
        "col_status": settings.get("module_validator_lpu.column_status", "VALIDADOR_LPU"),
        "col_total_paid": settings.get("module_validator_lpu.column_total_paid", "VALOR TOTAL PAGO"),
        "col_difference": settings.get("module_validator_lpu.column_difference", "DIFERENÇA TOTAL"),
        "col_agency": settings.get("module_validator_lpu.column_agency", "NUMERO_AGENCIA"),
        "col_city": settings.get("module_validator_lpu.column_city", "MUNICIPIO"),
        "col_uf": settings.get("module_validator_lpu.column_uf", "UF"),
        "col_constructor": settings.get("module_validator_lpu.column_constructor", "CONSTRUTORA"),
        "col_item_id": settings.get("module_validator_lpu.column_item_id", "ID ITEM"),
        "col_item_name": settings.get("module_validator_lpu.column_item_name", "NOME ITEM"),
        "status_refund": settings.get("module_validator_lpu.status_refund", "PARA RESSARCIMENTO"),
        "status_not_lpu": settings.get("module_validator_lpu.status_not_lpu", "ITEM NAO LPU"),
    }


def normalize_lpu_result(df: pd.DataFrame, cfg: Dict[str, Any]) -> pd.DataFrame:
    df = df.copy()

    col_status = cfg["col_status"]
    if col_status not in df.columns:
        raise KeyError(f"Coluna de status ausente: '{col_status}'")

    df[col_status] = df[col_status].map(_canon_status)

    for col in (cfg["col_total_paid"], cfg["col_difference"]):
        if col not in df.columns:
            raise KeyError(f"Coluna numérica ausente: '{col}'")
        df[col] = _to_numeric_series(df, col)

    return df


# -------------------------
# Pretty tables (no "Chave")
# -------------------------
def _make_pretty_items_table(
    df_top: pd.DataFrame,
    *,
    col_item_name: str,
    styles,
) -> Table:
    item_style = ParagraphStyle(
        "item_style",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=8.6,
        leading=10.2,
    )

    header = ["Item", "Qtd", "%", "Valor"]
    data: List[list] = [header]

    for _, r in df_top.iterrows():
        data.append(
            [
                Paragraph(str(r[col_item_name]), item_style),
                _fmt_int(int(r["qtd"])),
                _fmt_pct(float(r["pct"])),
                _brl(float(r["valor"])),
            ]
        )

    # A4 widths (sem coluna chave)
    col_widths = [11.6 * cm, 1.6 * cm, 1.6 * cm, 2.8 * cm]

    t = Table(data, colWidths=col_widths, repeatRows=1)
    t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.whitesmoke),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), 9),
                ("FONTSIZE", (0, 1), (-1, -1), 8.6),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("ALIGN", (1, 1), (-1, -1), "RIGHT"),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F7F7F7")]),
            ]
        )
    )
    return t


def _make_pretty_agency_table(
    pareto: pd.DataFrame,
    *,
    col_agency: str,
    col_city: str,
    col_uf: str,
    col_value: str,
) -> Table:
    data = [["Agência", "Município", "UF", "Valor"]]
    for _, r in pareto.iterrows():
        data.append(
            [
                str(r[col_agency]),
                str(r[col_city]),
                str(r[col_uf]),
                _brl(float(r[col_value])),
            ]
        )

    t = Table(data, colWidths=[3.0 * cm, 8.0 * cm, 1.2 * cm, 3.8 * cm], repeatRows=1)
    t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.whitesmoke),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), 9),
                ("FONTSIZE", (0, 1), (-1, -1), 8.8),
                ("ALIGN", (3, 1), (3, -1), "RIGHT"),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F7F7F7")]),
            ]
        )
    )
    return t


# -------------------------
# PDF Executive (ORDERED as requested)
# -------------------------
def generate_statistics_report_business(
    df_result: pd.DataFrame,
    output_pdf: PathLike,
    *,
    cfg: Optional[Dict[str, Any]] = None,
    workdir: Optional[PathLike] = None,
    top_agencies_n: int = 10,
    top_suppliers_n: int = 10,
    top_items_n: int = 10,
    verbose: bool = False,
) -> None:
    output_pdf_str = _as_path_str(output_pdf)
    cfg = cfg or {}

    col_status = cfg.get("col_status", "VALIDADOR_LPU")
    col_paid = cfg.get("col_total_paid", "VALOR TOTAL PAGO")
    col_diff = cfg.get("col_difference", "DIFERENÇA TOTAL")

    col_agency = cfg.get("col_agency", "NUMERO_AGENCIA")
    col_city = cfg.get("col_city", "MUNICIPIO")
    col_uf = cfg.get("col_uf", "UF")

    col_constructor = cfg.get("col_constructor", "CONSTRUTORA")

    status_refund = _canon_status(cfg.get("status_refund", "PARA RESSARCIMENTO"))
    status_not_lpu = _canon_status(cfg.get("status_not_lpu", "ITEM NAO LPU"))

    # validate minimal
    for c in [col_status, col_paid, col_diff]:
        if c not in df_result.columns:
            raise KeyError(f"Coluna obrigatória ausente: {c}")

    df = df_result.copy()
    df[col_status] = df[col_status].map(_canon_status)
    df[col_paid] = _to_numeric_series(df, col_paid)
    df[col_diff] = _to_numeric_series(df, col_diff)

    # KPIs
    qtd_itens = int(len(df))
    qtd_orcamentos = _infer_budget_count(df, verbose=verbose)
    total_paid = float(df[col_paid].sum())

    mask_not_lpu = df[col_status].eq(status_not_lpu)
    qtd_nao_lpu = int(mask_not_lpu.sum())
    qtd_lpu = int((~mask_not_lpu).sum())

    pct_nao_lpu = (qtd_nao_lpu / qtd_itens * 100.0) if qtd_itens else 0.0
    pct_lpu = (qtd_lpu / qtd_itens * 100.0) if qtd_itens else 0.0

    total_paid_not_lpu = float(df.loc[mask_not_lpu, col_paid].sum())
    total_paid_lpu = float(df.loc[~mask_not_lpu, col_paid].sum())

    potential_refund = float(df.loc[df[col_status].eq(status_refund), col_diff].sum())

    # Status distribution
    status_counts = df[col_status].value_counts().rename_axis("STATUS").reset_index(name="ITENS")
    status_counts["%"] = (status_counts["ITENS"] / max(qtd_itens, 1) * 100).round(1)

    # Workdir + charts
    work = Path(workdir) if workdir else Path(output_pdf_str).resolve().parent / ".tmp_lpu_report"
    _safe_mkdir(work)

    chart_status = work / "status_bar.png"
    chart_agencies = work / "top_agencies.png"

    # Chart: status
    plt.figure(figsize=(7.2, 3.6))
    plt.bar(status_counts["STATUS"], status_counts["ITENS"])
    plt.xticks(rotation=20, ha="right")
    plt.ylabel("Qtde de itens")
    plt.title(f"Distribuição de status ({col_status})")
    plt.tight_layout()
    plt.savefig(_as_path_str(chart_status), dpi=200)
    plt.close()

    # Top Agências (como era)
    has_geo_cols = all(c in df.columns for c in [col_agency, col_city, col_uf])
    if has_geo_cols:
        pareto_agencies = (
            df[df[col_status].eq(status_refund)]
            .groupby([col_agency, col_city, col_uf])[col_diff]
            .sum()
            .sort_values(ascending=False)
            .head(int(top_agencies_n))
            .reset_index()
        )
    else:
        pareto_agencies = pd.DataFrame(columns=[col_agency, col_city, col_uf, col_diff])

    plt.figure(figsize=(7.2, 3.6))
    if len(pareto_agencies) > 0:
        plt.bar(pareto_agencies[col_agency].astype(str), pareto_agencies[col_diff])
        plt.ylabel("R$ (diferença total)")
        plt.title(f"Top {int(top_agencies_n)} agências por potencial ressarcimento")
        plt.tight_layout()
    else:
        plt.title("Top agências por potencial ressarcimento")
        plt.text(0.5, 0.5, "Sem dados em PARA RESSARCIMENTO", ha="center")
        plt.axis("off")
    plt.savefig(_as_path_str(chart_agencies), dpi=200)
    plt.close()

    # Top fornecedores/construtoras
    if col_constructor in df.columns:
        top_suppliers = (
            df[df[col_status].eq(status_refund)]
            .groupby(col_constructor)[col_diff]
            .sum()
            .sort_values(ascending=False)
            .head(int(top_suppliers_n))
            .reset_index()
        )
    else:
        top_suppliers = pd.DataFrame(columns=[col_constructor, col_diff])

    # Top itens
    col_item_id, col_item_name = _pick_item_columns(df, cfg)

    top_items_lpu = _top_items(
        df.loc[~mask_not_lpu],
        col_item_id=col_item_id,
        col_item_name=col_item_name,
        col_paid=col_paid,
        n=int(top_items_n),
        denom_for_pct=max(qtd_lpu, 1),
    )
    top_items_not_lpu = _top_items(
        df.loc[mask_not_lpu],
        col_item_id=col_item_id,
        col_item_name=col_item_name,
        col_paid=col_paid,
        n=int(top_items_n),
        denom_for_pct=max(qtd_nao_lpu, 1),
    )

    # -------------------------
    # PDF build (ORDER)
    # -------------------------
    styles = getSampleStyleSheet()
    title_style = styles["Title"]
    h2 = styles["Heading2"]
    body = styles["BodyText"]

    doc = SimpleDocTemplate(
        output_pdf_str,
        pagesize=A4,
        rightMargin=1.6 * cm,
        leftMargin=1.6 * cm,
        topMargin=1.4 * cm,
        bottomMargin=1.4 * cm,
    )

    elements: List[Any] = []

    # 1) Resumo executivo
    elements.append(Paragraph("Relatório Executivo — Validador LPU", title_style))
    elements.append(Paragraph(f"Gerado em {datetime.now().strftime('%d/%m/%Y %H:%M')}", body))
    elements.append(Spacer(1, 10))

    kpi_data = [
        ["Quantidade de orçamentos", _fmt_int(qtd_orcamentos)],
        ["Quantidade de itens", _fmt_int(qtd_itens)],
        ["Valor total pago", _brl(total_paid)],
        ["Itens LPU (qtd | % | valor)", f"{_fmt_int(qtd_lpu)} | {_fmt_pct(pct_lpu)} | {_brl(total_paid_lpu)}"],
        ["Itens NÃO LPU (qtd | % | valor)", f"{_fmt_int(qtd_nao_lpu)} | {_fmt_pct(pct_nao_lpu)} | {_brl(total_paid_not_lpu)}"],
        ["Potencial ressarcimento", _brl(potential_refund)],
    ]
    kpi_table = Table(kpi_data, colWidths=[6.4 * cm, 9.6 * cm])
    kpi_table.setStyle(
        TableStyle(
            [
                ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("BACKGROUND", (0, 0), (-1, 0), colors.whitesmoke),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ]
        )
    )
    elements.append(Paragraph("Resumo Executivo", h2))
    elements.append(kpi_table)
    elements.append(Spacer(1, 12))

    elements.append(Paragraph("Distribuição de status", h2))
    elements.append(Image(_as_path_str(chart_status), width=16.5 * cm, height=8 * cm))
    elements.append(Spacer(1, 8))

    status_tbl = Table(
        [["STATUS", "ITENS", "%"]] + status_counts.values.tolist(),
        colWidths=[7.5 * cm, 4 * cm, 4 * cm],
        repeatRows=1,
    )
    status_tbl.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.whitesmoke),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F7F7F7")]),
            ]
        )
    )
    elements.append(status_tbl)

    # 2) Top agências
    elements.append(PageBreak())
    elements.append(Paragraph(f"Top {int(top_agencies_n)} agências por potencial ressarcimento", h2))
    elements.append(Paragraph("Concentradores de impacto financeiro para priorização de tratativas.", body))
    elements.append(Spacer(1, 8))
    elements.append(Image(_as_path_str(chart_agencies), width=16.5 * cm, height=8 * cm))
    elements.append(Spacer(1, 10))

    if not has_geo_cols:
        elements.append(
            Paragraph(
                f"Não foi possível calcular Top Agências: faltam colunas ({col_agency}, {col_city}, {col_uf}).",
                body,
            )
        )
    elif len(pareto_agencies) == 0:
        elements.append(Paragraph("Não há registros em 'PARA RESSARCIMENTO' nesta base.", body))
    else:
        elements.append(
            _make_pretty_agency_table(
                pareto_agencies,
                col_agency=col_agency,
                col_city=col_city,
                col_uf=col_uf,
                col_value=col_diff,
            )
        )

    # 3) Top fornecedores
    elements.append(PageBreak())
    elements.append(Paragraph(f"Top {int(top_suppliers_n)} fornecedores/construtoras (ressarcimento)", h2))
    if len(top_suppliers) > 0:
        tc = top_suppliers.copy()
        tc[col_diff] = tc[col_diff].map(_brl)
        t2 = Table(
            [["FORNECEDOR/CONSTRUTORA", "POTENCIAL (R$)"]] + tc.values.tolist(),
            colWidths=[11.5 * cm, 5.0 * cm],
            repeatRows=1,
        )
        t2.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.whitesmoke),
                    ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F7F7F7")]),
                ]
            )
        )
        elements.append(t2)
    else:
        elements.append(Paragraph("Sem dados de fornecedor/construtora para ranking.", body))

    # 4) Top itens
    elements.append(PageBreak())
    elements.append(Paragraph(f"Top {int(top_items_n)} itens (frequência)", h2))
    elements.append(Spacer(1, 6))

    elements.append(Paragraph(f"Top {int(top_items_n)} itens LPU (mais aparecem)", h2))
    if len(top_items_lpu) > 0:
        elements.append(_make_pretty_items_table(top_items_lpu, col_item_name=col_item_name, styles=styles))
    else:
        elements.append(Paragraph("Sem itens LPU para ranquear.", body))

    elements.append(Spacer(1, 12))

    elements.append(Paragraph(f"Top {int(top_items_n)} itens NÃO LPU (mais aparecem)", h2))
    if len(top_items_not_lpu) > 0:
        elements.append(_make_pretty_items_table(top_items_not_lpu, col_item_name=col_item_name, styles=styles))
    else:
        elements.append(Paragraph("Sem itens NÃO LPU para ranquear.", body))

    doc.build(elements)


# -------------------------
# Orchestrator
# -------------------------
def run_lpu_validation_reporting(
    *,
    df_result: pd.DataFrame,
    validator_output_pdf: Optional[bool] = None,
    output_pdf: PathLike = "VALIDADOR_LPU_EXECUTIVO.pdf",
    verbose: Optional[bool] = None,
    workdir: Optional[PathLike] = None,
    top_agencies_n: int = 10,
    top_suppliers_n: int = 10,
    top_items_n: int = 10,
) -> None:

    cfg = _get_cfg(settings)
    df_norm = normalize_lpu_result(df_result, cfg)

    if verbose:
        logger.info("📄 Gerando relatório executivo (Validador LPU)...")
        logger.info(f"Itens: {len(df_norm)} | PDF: {_as_path_str(output_pdf)}")
        logger.info(f"Top agências: {top_agencies_n} | Top fornecedores: {top_suppliers_n} | Top itens: {top_items_n}")

    if validator_output_pdf:
        generate_statistics_report_business(
            df_norm,
            output_pdf=_as_path_str(output_pdf),
            workdir=_as_path_str(workdir) if workdir is not None else None,
            top_agencies_n=int(top_agencies_n),
            top_suppliers_n=int(top_suppliers_n),
            top_items_n=int(top_items_n),
            verbose=bool(verbose),
            cfg=cfg,
        )
        logger.info(f"✅ Relatório executivo gerado: {_as_path_str(output_pdf)}")
    else:
        logger.info("Geração de relatório em PDF desativada.")

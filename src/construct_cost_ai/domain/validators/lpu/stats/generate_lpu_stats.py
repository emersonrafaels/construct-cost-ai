"""
Relatório Executivo — Validador LPU (PDF)
----------------------------------------
Atualização solicitada (Resumo de KPIs):
✅ Incluir (nesta ordem):
  - Quantidade de orçamentos
  - Quantidade de itens
  - Valor total pago
  - Valor total itens LPU
  - Valor total itens não LPU
  - Potencial ressarcimento

Regras:
- Quantidade de itens = número de linhas do DF
- Quantidade de orçamentos:
    1) tenta detectar por colunas comuns (ex.: ID_ORCAMENTO, ORCAMENTO_ID, NUM_ORCAMENTO, SOURCE_FILE)
    2) se não achar, cai para 1 (assume "um orçamento processado") e loga warning (só quando verbose)
- Itens não LPU = status == status_not_lpu (default: ITEM_NAO_LPU)
- Itens LPU = demais (status != status_not_lpu)
- Potencial ressarcimento = soma DIF onde status == status_refund (default: PARA RESSARCIMENTO)

⚠️ Fix WindowsPath/ReportLab: todos os caminhos viram `str`.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, Union, Iterable, List

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
# Types
# -------------------------
PathLike = Union[str, Path]
StatusesLike = Union[str, Iterable[str], None]


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


def _norm_statuses(pareto_statuses: StatusesLike) -> List[str]:
    if pareto_statuses is None:
        return []
    if isinstance(pareto_statuses, str):
        s = pareto_statuses.strip()
        return [] if s == "" else [s.upper()]
    out: List[str] = []
    seen = set()
    for s in pareto_statuses:
        if s is None:
            continue
        s2 = str(s).strip()
        if not s2:
            continue
        s2 = s2.upper()
        if s2 not in seen:
            seen.add(s2)
            out.append(s2)
    return out


def _fmt_int(n: int) -> str:
    return f"{int(n):,}".replace(",", ".")


def _infer_budget_count(df: pd.DataFrame, *, verbose: bool) -> int:
    """
    Heurística para contar orçamentos distintos.
    Tenta identificar uma coluna de "id do orçamento".
    """
    candidate_cols = [
        # mais prováveis
        "ID_ORCAMENTO",
        "ORCAMENTO_ID",
        "NUM_ORCAMENTO",
        "ORCAMENTO",
        "COD_ORCAMENTO",
        "ORC_ID",
        # fallback comum em pipelines
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

    # fallback conservador
    if verbose:
        logger.warning(
            "Não encontrei coluna identificadora de orçamento (ex: ID_ORCAMENTO/ORCAMENTO_ID/SOURCE_FILE). "
            "Assumindo 1 orçamento."
        )
    return 1


# -------------------------
# Config
# -------------------------
def _get_cfg(settings) -> Dict[str, Any]:
    return {
        "col_status": settings.get("module_validator_lpu.column_status", "VALIDADOR_LPU"),
        "col_total_paid": settings.get("module_validator_lpu.column_total_paid", "VALOR TOTAL PAGO"),
        "col_difference": settings.get("module_validator_lpu.column_difference", "DIFERENÇA TOTAL"),
        "col_total_lpu": settings.get("module_validator_lpu.column_total_lpu", "VALOR TOTAL LPU"),
        "col_agency": settings.get("module_validator_lpu.column_agency", "NUMERO_AGENCIA"),
        "col_city": settings.get("module_validator_lpu.column_city", "MUNICIPIO"),
        "col_uf": settings.get("module_validator_lpu.column_uf", "UF"),
        "col_constructor": settings.get("module_validator_lpu.column_constructor", "CONSTRUTORA"),
        "status_ok": settings.get("module_validator_lpu.status_ok", "OK"),
        "status_refund": settings.get("module_validator_lpu.status_refund", "PARA RESSARCIMENTO"),
        "status_below": settings.get("module_validator_lpu.status_below", "ABAIXO LPU"),
        "status_not_lpu": settings.get("module_validator_lpu.status_not_lpu", "ITEM_NAO_LPU"),
    }


# -------------------------
# Normalization
# -------------------------
def normalize_lpu_result(df: pd.DataFrame, cfg: Dict[str, Any]) -> pd.DataFrame:
    df = df.copy()

    col_status = cfg["col_status"]
    if col_status not in df.columns:
        raise KeyError(f"Coluna de status ausente: '{col_status}'")

    df[col_status] = df[col_status].astype(str).str.strip().str.upper()

    for col in (cfg["col_total_paid"], cfg["col_difference"]):
        if col not in df.columns:
            raise KeyError(f"Coluna numérica ausente: '{col}'")
        df[col] = _to_numeric_series(df, col)

    col_lpu = cfg.get("col_total_lpu")
    if col_lpu and col_lpu in df.columns:
        df[col_lpu] = _to_numeric_series(df, col_lpu)

    return df


# -------------------------
# PDF Executive
# -------------------------
def generate_statistics_report_business(
    df_result: pd.DataFrame,
    output_pdf: PathLike,
    *,
    cfg: Optional[Dict[str, Any]] = None,
    workdir: Optional[PathLike] = None,
    top_n: int = 10,
    pareto_statuses: StatusesLike = "PARA RESSARCIMENTO",
    verbose: bool = False,  # ✅ para log de fallback de orçamentos
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

    status_refund = cfg.get("status_refund", "PARA RESSARCIMENTO")
    status_not_lpu = cfg.get("status_not_lpu", "ITEM_NAO_LPU")

    pareto_status_list = _norm_statuses(pareto_statuses)
    pareto_enabled = len(pareto_status_list) > 0

    required = [col_status, col_paid, col_diff]
    missing = [c for c in required if c not in df_result.columns]
    if missing:
        raise KeyError(f"Colunas obrigatórias ausentes: {missing}")

    df = df_result.copy()
    df[col_status] = df[col_status].astype(str).str.strip().str.upper()
    df[col_paid] = _to_numeric_series(df, col_paid)
    df[col_diff] = _to_numeric_series(df, col_diff)

    # -------------------------
    # KPIs solicitados
    # -------------------------
    qtd_itens = int(len(df))
    qtd_orcamentos = _infer_budget_count(df, verbose=verbose)

    total_paid = float(df[col_paid].sum())

    mask_not_lpu = df[col_status].eq(status_not_lpu)
    total_paid_not_lpu = float(df.loc[mask_not_lpu, col_paid].sum())
    total_paid_lpu_items = float(df.loc[~mask_not_lpu, col_paid].sum())

    potential_refund = float(df.loc[df[col_status].eq(status_refund), col_diff].sum())

    # Status distribution
    status_counts = df[col_status].value_counts().rename_axis("STATUS").reset_index(name="ITENS")
    status_counts["%"] = (status_counts["ITENS"] / qtd_itens * 100).round(1) if qtd_itens else 0.0

    # Workdir
    work = Path(workdir) if workdir else Path(output_pdf_str).resolve().parent / ".tmp_lpu_report"
    _safe_mkdir(work)

    chart_status = work / "status_bar.png"

    # Chart 1: status bar
    plt.figure(figsize=(7.2, 3.6))
    plt.bar(status_counts["STATUS"], status_counts["ITENS"])
    plt.xticks(rotation=20, ha="right")
    plt.ylabel("Qtde de itens")
    plt.title(f"Distribuição de status ({col_status})")
    plt.tight_layout()
    plt.savefig(_as_path_str(chart_status), dpi=200)
    plt.close()

    # Pareto 1..N
    paretos: Dict[str, pd.DataFrame] = {}
    pareto_charts: Dict[str, Path] = {}
    has_geo_cols = all(c in df.columns for c in [col_agency, col_city, col_uf])

    if pareto_enabled and has_geo_cols:
        for st in pareto_status_list:
            p = (
                df[df[col_status].eq(st)]
                .groupby([col_agency, col_city, col_uf])[col_diff]
                .sum()
                .sort_values(ascending=False)
                .head(top_n)
                .reset_index()
            )
            paretos[st] = p

            chart_path = work / f"pareto_{st.replace(' ', '_')}.png"
            plt.figure(figsize=(7.2, 3.6))
            if len(p) > 0:
                plt.bar(p[col_agency].astype(str), p[col_diff])
                plt.ylabel("R$ (diferença total)")
                plt.title(f"Top {top_n} agências — {st}")
                plt.tight_layout()
            else:
                plt.title(f"Top agências — {st}")
                plt.text(0.5, 0.5, f"Sem dados em {st}", ha="center")
                plt.axis("off")

            plt.savefig(_as_path_str(chart_path), dpi=200)
            plt.close()
            pareto_charts[st] = chart_path

    # Top constructors by refund (status_refund)
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

    # -------------------------
    # PDF
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

    elements = []
    elements.append(Paragraph("Relatório Executivo — Validador LPU", title_style))
    elements.append(Paragraph(f"Gerado em {datetime.now().strftime('%d/%m/%Y %H:%M')}", body))
    elements.append(Spacer(1, 10))

    # ✅ KPI table (exatamente como pedido)
    kpi_data = [
        ["Quantidade de orçamentos", _fmt_int(qtd_orcamentos)],
        ["Quantidade de itens", _fmt_int(qtd_itens)],
        ["Valor total pago", _brl(total_paid)],
        ["Valor total itens LPU", _brl(total_paid_lpu_items)],
        ["Valor total itens não LPU", _brl(total_paid_not_lpu)],
        ["Potencial ressarcimento", _brl(potential_refund)],
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

    # Pareto section (1..N)
    elements.append(Paragraph("Pareto (drill-down)", h2))

    if not pareto_enabled:
        elements.append(Paragraph("Pareto desativado por configuração.", body))
    elif not has_geo_cols:
        elements.append(
            Paragraph(
                f"Pareto solicitado para {', '.join([f'<b>{s}</b>' for s in pareto_status_list])}, "
                f"mas faltam colunas de localização ({col_agency}, {col_city}, {col_uf}).",
                body,
            )
        )
    else:
        elements.append(
            Paragraph(
                "Visão de concentração por agência para os status: "
                + ", ".join([f"<b>{s}</b>" for s in pareto_status_list]),
                body,
            )
        )

    elements.append(Spacer(1, 8))

    if pareto_enabled and has_geo_cols:
        for st in pareto_status_list:
            elements.append(Paragraph(f"Status: <b>{st}</b>", h2))

            chart_path = pareto_charts.get(st)
            if chart_path:
                elements.append(Image(_as_path_str(chart_path), width=16.5 * cm, height=8 * cm))
                elements.append(Spacer(1, 10))

            p = paretos.get(st)
            if p is not None and len(p) > 0:
                p_fmt = p.copy()
                p_fmt[col_diff] = p_fmt[col_diff].map(_brl)

                t = Table(
                    [[str(col_agency), "MUNICÍPIO", "UF", "VALOR (R$)"]] + p_fmt.values.tolist(),
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
                elements.append(Paragraph(f"Não há registros em '{st}' nesta base.", body))

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
# Orchestrator
# -------------------------
def run_lpu_validation_reporting(
    *,
    df_result: pd.DataFrame,
    validator_output_pdf: Optional[bool] = None,
    output_pdf: PathLike = "VALIDADOR_LPU_EXECUTIVO.pdf",
    verbose: Optional[bool] = None,
    top_n: int = 10,
    workdir: Optional[PathLike] = None,
    pareto_statuses: StatusesLike = "PARA RESSARCIMENTO",
) -> None:
    if validator_output_pdf is None:
        validator_output_pdf = settings.get("module_validator_lpu.stats.validator_output_pdf", True)

    if verbose is None:
        verbose = settings.get("module_validator_lpu.verbose", True)

    cfg = _get_cfg(settings)
    df_norm = normalize_lpu_result(df_result, cfg)

    output_pdf_str = _as_path_str(output_pdf)
    workdir_str = _as_path_str(workdir) if workdir is not None else None
    pareto_list = _norm_statuses(pareto_statuses)

    if verbose:
        logger.info("📄 Gerando relatório executivo (Validador LPU)...")
        logger.info(f"Itens: {len(df_norm)} | PDF: {output_pdf_str}")
        logger.info(f"Pareto: {pareto_list if pareto_list else 'DESATIVADO'}")

    if validator_output_pdf:
        generate_statistics_report_business(
            df_norm,
            output_pdf=output_pdf_str,
            workdir=workdir_str,
            top_n=top_n,
            pareto_statuses=pareto_list,
            verbose=bool(verbose),
            cfg={
                "col_status": cfg["col_status"],
                "col_total_paid": cfg["col_total_paid"],
                "col_difference": cfg["col_difference"],
                "col_total_lpu": cfg.get("col_total_lpu", "VALOR TOTAL LPU"),
                "col_agency": cfg.get("col_agency", "NUMERO_AGENCIA"),
                "col_city": cfg.get("col_city", "MUNICIPIO"),
                "col_uf": cfg.get("col_uf", "UF"),
                "col_constructor": cfg.get("col_constructor", "CONSTRUTORA"),
                "status_refund": cfg["status_refund"],
                "status_not_lpu": cfg["status_not_lpu"],
            },
        )
        logger.info(f"✅ Relatório executivo gerado: {output_pdf_str}")
    else:
        logger.info("Geração de relatório em PDF desativada.")

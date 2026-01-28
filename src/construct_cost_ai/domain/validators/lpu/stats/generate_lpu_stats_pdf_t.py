"""
Relatório Executivo — Validador LPU / NLPU (PDF) — Unificado
===========================================================

✅ Mesmo “formato executivo” do HTML v3, agora em PDF (ReportLab + Matplotlib).

Características
--------------
- Entrada única: `df_result` (base pós-LPU ou base de continuação pós-NLPU)
- Flags:
    * create_stats_lpu: seção LPU
    * create_stats_nlpu: seção NLPU (continuação)
- Resumo Executivo (quando LPU+NLPU ativos):
    Potencial ressarcimento (LPU) → (NLPU) → (TOTAL)
- Remove KPI confuso: "Valor total (match) NLPU"
- Remove do relatório o status "PARA COMPLEMENTO"
- Config parametrizável no topo (colunas e status)

Uso (exemplo):
--------------
from pathlib import Path
import pandas as pd
from relatorio_exec_unificado_pdf import run_validation_reporting_pdf, ReportConfig

df_lpu = pd.read_excel("02_BASE_RESULTADO_VALIDADOR_LPU.xlsx")
df_nlpu = pd.read_excel("03_BASE_RESULTADO_VALIDADOR_NLPU.xlsx")

# PDF só LPU (base pós-LPU)
run_validation_reporting_pdf(
    df_result=df_lpu,
    output_pdf=Path("REL_EXEC_LPU_ONLY.pdf"),
    create_stats_lpu=True,
    create_stats_nlpu=False,
    verbose=True,
)

# PDF LPU + NLPU (base de continuação pós-NLPU)
run_validation_reporting_pdf(
    df_result=df_nlpu,
    output_pdf=Path("REL_EXEC_LPU_NLPU.pdf"),
    create_stats_lpu=True,
    create_stats_nlpu=True,
    verbose=True,
)

# Ajustando colunas/status rapidamente:
cfg = ReportConfig(
    col_status_lpu="VALIDADOR_LPU",
    col_status_nlpu="RESULTADO VALIDADOR NLPU",
    status_not_lpu="ITEM NAO LPU",
)
run_validation_reporting_pdf(df_result=df_nlpu, output_pdf="X.pdf", config=cfg, create_stats_lpu=True, create_stats_nlpu=True)
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

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


# ------------------------------------------------------------
# Logger (pluga no seu se existir)
# ------------------------------------------------------------
try:
    from config.config_logger import logger  # type: ignore
except Exception:  # pragma: no cover
    import logging

    logger = logging.getLogger(__name__)
    logger.addHandler(logging.StreamHandler())
    logger.setLevel(logging.INFO)


PathLike = Union[str, Path]


# ============================================================
# 1) CONFIGURÁVEL NO TOPO (colunas + status)
# ============================================================

@dataclass(frozen=True)
class ReportConfig:
    # -----------------
    # Colunas numéricas
    # -----------------
    col_total_paid: str = "VALOR TOTAL PAGO"

    # LPU (fase 1)
    col_status_lpu: str = "RESULTADO VALIDADOR LPU"   # fallback: "VALIDADOR_LPU"
    col_diff_lpu: str = "DIFERENÇA TOTAL"

    # NLPU (fase 2) — continuidade
    col_status_nlpu: str = "RESULTADO VALIDADOR NLPU"
    col_diff_nlpu: str = "MATCH FUZZY - DIFERENÇA TOTAL"

    # -----------------
    # Dimensões
    # -----------------
    col_agency: str = "NUMERO_AGENCIA"
    col_city: str = "MUNICIPIO"
    col_uf: str = "UF"
    col_supplier: str = "CONSTRUTORA"

    col_item_name: str = "NOME ITEM"
    col_item_id: str = "ID ITEM"  # não exibimos no PDF, só fallback

    # -----------------
    # Status canônicos
    # -----------------
    status_refund: str = "PARA RESSARCIMENTO"
    status_not_lpu: str = "ITEM NAO LPU"
    status_complemento: str = "PARA COMPLEMENTO"  # ✅ oculto do relatório

    # -----------------
    # Heurística orçamento
    # -----------------
    budget_id_candidates: Tuple[str, ...] = (
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
    )

    # -----------------
    # Fallbacks de colunas
    # -----------------
    fallback_status_lpu: Tuple[str, ...] = ("VALIDADOR_LPU", "STATUS CONCILIAÇÃO")
    fallback_item_name: Tuple[str, ...] = ("ITEM", "DESC ITEM", "DESCRICAO", "NOME")
    fallback_item_id: Tuple[str, ...] = ("CÓD ITEM", "COD ITEM", "ID", "CODIGO", "COD_LPU")


# ============================================================
# 2) HELPERS
# ============================================================

def _as_path_str(p: PathLike) -> str:
    return str(Path(p))


def _canon_status(x: Any) -> str:
    s = "" if x is None else str(x)
    s = s.strip().upper().replace("_", " ")
    s = " ".join(s.split())
    return s


def _to_num(df: pd.DataFrame, col: str) -> pd.Series:
    return pd.to_numeric(df[col], errors="coerce").fillna(0.0)


def _fmt_int(n: int) -> str:
    return f"{int(n):,}".replace(",", ".")


def _fmt_pct(x: float) -> str:
    try:
        return f"{float(x):.1f}%".replace(".", ",")
    except Exception:
        return str(x)


def _brl(x: float) -> str:
    try:
        s = f"{float(x):,.2f}"
        return "R$ " + s.replace(",", "X").replace(".", ",").replace("X", ".")
    except Exception:
        return str(x)


def _infer_budget_count(df: pd.DataFrame, cfg: ReportConfig, *, verbose: bool) -> int:
    for c in cfg.budget_id_candidates:
        if c in df.columns:
            n = int(df[c].nunique(dropna=True))
            if n > 0:
                return n
    if verbose:
        logger.warning("Não encontrei coluna identificadora de orçamento. Assumindo 1 orçamento.")
    return 1


def _resolve_column(df: pd.DataFrame, preferred: str, fallbacks: Sequence[str]) -> str:
    if preferred in df.columns:
        return preferred
    for c in fallbacks:
        if c in df.columns:
            return c
    return preferred


def _resolve_item_cols(df: pd.DataFrame, cfg: ReportConfig) -> Tuple[str, str]:
    col_name = cfg.col_item_name
    col_id = cfg.col_item_id

    if col_name not in df.columns:
        col_name = _resolve_column(df, col_name, cfg.fallback_item_name)

    if col_id not in df.columns:
        col_id = _resolve_column(df, col_id, cfg.fallback_item_id)

    if col_name not in df.columns:
        raise KeyError(f"Não encontrei coluna de nome do item: '{cfg.col_item_name}' (ou fallbacks).")

    # id é opcional; se não existir, só usamos name
    if col_id not in df.columns:
        col_id = col_name

    return col_id, col_name


def _drop_complemento(df: pd.DataFrame, col_status: str, cfg: ReportConfig) -> pd.DataFrame:
    st_comp = _canon_status(cfg.status_complemento)
    return df[df[col_status] != st_comp].copy()


# ============================================================
# 3) COMPUTE (LPU / NLPU)
# ============================================================

def _compute_lpu(df: pd.DataFrame, cfg: ReportConfig) -> Dict[str, Any]:
    col_status = _resolve_column(df, cfg.col_status_lpu, cfg.fallback_status_lpu)
    col_paid = cfg.col_total_paid
    col_diff = cfg.col_diff_lpu

    for c in (col_status, col_paid, col_diff):
        if c not in df.columns:
            raise KeyError(f"Coluna obrigatória ausente (LPU): {c}")

    d = df.copy()
    d[col_status] = d[col_status].map(_canon_status)
    d[col_paid] = _to_num(d, col_paid)
    d[col_diff] = _to_num(d, col_diff)

    d_vis = _drop_complemento(d, col_status, cfg)

    st_not_lpu = _canon_status(cfg.status_not_lpu)
    st_refund = _canon_status(cfg.status_refund)

    mask_not_lpu = d_vis[col_status].eq(st_not_lpu)

    qtd_itens = int(len(d_vis))
    qtd_lpu = int((~mask_not_lpu).sum())
    qtd_nao_lpu = int(mask_not_lpu.sum())
    pct_lpu = (qtd_lpu / qtd_itens * 100.0) if qtd_itens else 0.0
    pct_nao_lpu = (qtd_nao_lpu / qtd_itens * 100.0) if qtd_itens else 0.0

    total_paid = float(d_vis[col_paid].sum())
    total_paid_lpu = float(d_vis.loc[~mask_not_lpu, col_paid].sum())
    total_paid_not_lpu = float(d_vis.loc[mask_not_lpu, col_paid].sum())

    pot_refund_lpu = float(d_vis.loc[d_vis[col_status].eq(st_refund), col_diff].sum())

    status_counts = (
        d_vis[col_status]
        .value_counts()
        .rename_axis("Status")
        .reset_index(name="Itens")
    )
    status_counts["%"] = (status_counts["Itens"] / max(qtd_itens, 1) * 100).round(1)

    return dict(
        col_status=col_status,
        col_paid=col_paid,
        col_diff=col_diff,
        df_vis=d_vis,
        qtd_itens=qtd_itens,
        total_paid=total_paid,
        qtd_lpu=qtd_lpu,
        qtd_nao_lpu=qtd_nao_lpu,
        pct_lpu=pct_lpu,
        pct_nao_lpu=pct_nao_lpu,
        total_paid_lpu=total_paid_lpu,
        total_paid_not_lpu=total_paid_not_lpu,
        pot_refund_lpu=pot_refund_lpu,
        status_counts=status_counts,
        mask_not_lpu=mask_not_lpu,
    )


def _compute_nlpu(df: pd.DataFrame, cfg: ReportConfig) -> Dict[str, Any]:
    col_status = cfg.col_status_nlpu
    col_diff = cfg.col_diff_nlpu

    for c in (col_status, col_diff):
        if c not in df.columns:
            raise KeyError(f"Coluna obrigatória ausente (NLPU): {c}")

    d = df.copy()
    d[col_status] = d[col_status].map(_canon_status)
    d[col_diff] = _to_num(d, col_diff)

    d_vis = _drop_complemento(d, col_status, cfg)

    st_refund = _canon_status(cfg.status_refund)

    qtd_itens_nlpu = int(len(d_vis))
    qtd_refund_nlpu = int(d_vis[col_status].eq(st_refund).sum())
    pot_refund_nlpu = float(d_vis.loc[d_vis[col_status].eq(st_refund), col_diff].sum())

    status_counts = (
        d_vis[col_status]
        .value_counts()
        .rename_axis("Status")
        .reset_index(name="Itens")
    )
    status_counts["%"] = (status_counts["Itens"] / max(qtd_itens_nlpu, 1) * 100).round(1)

    return dict(
        col_status=col_status,
        col_diff=col_diff,
        df_vis=d_vis,
        qtd_itens_nlpu=qtd_itens_nlpu,
        qtd_refund_nlpu=qtd_refund_nlpu,
        pot_refund_nlpu=pot_refund_nlpu,
        status_counts=status_counts,
    )


# ============================================================
# 4) RANKINGS
# ============================================================

def _top_agencies(df: pd.DataFrame, *, col_ag: str, col_city: str, col_uf: str, col_value: str, n: int) -> pd.DataFrame:
    if not all(c in df.columns for c in (col_ag, col_city, col_uf, col_value)):
        return pd.DataFrame(columns=["Agência", "Município", "UF", "Potencial (R$)"])
    t = (
        df.groupby([col_ag, col_city, col_uf])[col_value]
        .sum()
        .sort_values(ascending=False)
        .head(int(n))
        .reset_index()
        .rename(columns={col_ag: "Agência", col_city: "Município", col_uf: "UF", col_value: "Potencial (R$)"})
    )
    t["Agência"] = t["Agência"].astype(str)
    t["Potencial (R$)"] = t["Potencial (R$)"].map(lambda x: _brl(float(x)))
    return t


def _top_suppliers(df: pd.DataFrame, *, col_supplier: str, col_value: str, n: int) -> pd.DataFrame:
    if not all(c in df.columns for c in (col_supplier, col_value)):
        return pd.DataFrame(columns=["Fornecedor/Construtora", "Potencial (R$)"])
    t = (
        df.groupby(col_supplier)[col_value]
        .sum()
        .sort_values(ascending=False)
        .head(int(n))
        .reset_index()
        .rename(columns={col_supplier: "Fornecedor/Construtora", col_value: "Potencial (R$)"})
    )
    t["Fornecedor/Construtora"] = t["Fornecedor/Construtora"].astype(str)
    t["Potencial (R$)"] = t["Potencial (R$)"].map(lambda x: _brl(float(x)))
    return t


def _top_items(df: pd.DataFrame, *, col_item_name: str, col_paid: str, n: int, denom: int) -> pd.DataFrame:
    if not all(c in df.columns for c in (col_item_name, col_paid)):
        return pd.DataFrame(columns=["Item", "Qtd", "%", "Valor"])
    g = (
        df.groupby(col_item_name, dropna=False)
        .agg(qtd=(col_item_name, "size"), valor=(col_paid, "sum"))
        .reset_index()
        .sort_values(["qtd", "valor"], ascending=[False, False])
        .head(int(n))
    )
    denom = max(int(denom), 1)
    g["pct"] = (g["qtd"] / denom * 100.0).round(1)
    return pd.DataFrame(
        {
            "Item": g[col_item_name].astype(str),
            "Qtd": g["qtd"].astype(int),
            "%": g["pct"].map(_fmt_pct),
            "Valor": g["valor"].map(lambda x: _brl(float(x))),
        }
    )


# ============================================================
# 5) CHARTS
# ============================================================

def _save_bar_chart(df: pd.DataFrame, *, x: str, y: str, title: str, out_png: Path) -> None:
    plt.figure(figsize=(7.2, 3.6))
    plt.bar(df[x].astype(str), df[y])
    plt.xticks(rotation=20, ha="right")
    plt.ylabel(y)
    plt.title(title)
    plt.tight_layout()
    plt.savefig(str(out_png), dpi=200)
    plt.close()


# ============================================================
# 6) PDF RENDER
# ============================================================

def _table(df: pd.DataFrame, col_widths: List[float]) -> Table:
    data = [list(df.columns)] + df.values.tolist()
    t = Table(data, colWidths=col_widths)
    t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.whitesmoke),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        )
    )
    return t


def generate_executive_report_pdf(
    *,
    df_result: pd.DataFrame,
    output_pdf: PathLike,
    cfg: ReportConfig,
    create_stats_lpu: bool,
    create_stats_nlpu: bool,
    verbose: bool,
    top_agencies_n: int,
    top_suppliers_n: int,
    top_items_n: int,
    workdir: Optional[PathLike] = None,
) -> None:
    out_pdf = _as_path_str(output_pdf)
    work = Path(_as_path_str(workdir)) if workdir else Path(out_pdf).resolve().parent / ".tmp_exec_pdf"
    work.mkdir(parents=True, exist_ok=True)

    styles = getSampleStyleSheet()
    title_style = styles["Title"]
    h1 = styles["Heading1"]
    h2 = styles["Heading2"]
    body = styles["BodyText"]

    doc = SimpleDocTemplate(
        out_pdf,
        pagesize=A4,
        rightMargin=1.6 * cm,
        leftMargin=1.6 * cm,
        topMargin=1.4 * cm,
        bottomMargin=1.4 * cm,
    )

    generated_at = datetime.now().strftime("%d/%m/%Y %H:%M")

    elements: List[Any] = []
    elements.append(Paragraph("Relatório Executivo — Validador LPU / NLPU", title_style))
    elements.append(Paragraph(f"Gerado em {generated_at}", body))
    elements.append(Spacer(1, 10))

    # ---------
    # KPIs (Resumo Executivo)
    # ---------
    qtd_orcamentos = _infer_budget_count(df_result, cfg, verbose=verbose)
    qtd_itens_total = int(len(df_result))

    if cfg.col_total_paid not in df_result.columns:
        raise KeyError(f"Coluna obrigatória ausente: {cfg.col_total_paid}")
    total_paid_all = float(_to_num(df_result, cfg.col_total_paid).sum())

    pot_lpu = 0.0
    pot_nlpu = 0.0

    lpu_pack: Optional[Dict[str, Any]] = None
    nlpu_pack: Optional[Dict[str, Any]] = None

    if create_stats_lpu:
        lpu_pack = _compute_lpu(df_result, cfg)
        pot_lpu = float(lpu_pack["pot_refund_lpu"])

    if create_stats_nlpu:
        nlpu_pack = _compute_nlpu(df_result, cfg)
        pot_nlpu = float(nlpu_pack["pot_refund_nlpu"])

    pot_total = pot_lpu + pot_nlpu

    # LPU vs NÃO LPU (só faz sentido se LPU estiver ativo)
    if lpu_pack is not None:
        qtd_lpu = int(lpu_pack["qtd_lpu"])
        qtd_nao_lpu = int(lpu_pack["qtd_nao_lpu"])
        pct_lpu = float(lpu_pack["pct_lpu"])
        pct_nao_lpu = float(lpu_pack["pct_nao_lpu"])
        total_paid_lpu = float(lpu_pack["total_paid_lpu"])
        total_paid_not_lpu = float(lpu_pack["total_paid_not_lpu"])
    else:
        qtd_lpu = qtd_itens_total
        qtd_nao_lpu = 0
        pct_lpu = 100.0 if qtd_itens_total else 0.0
        pct_nao_lpu = 0.0
        total_paid_lpu = total_paid_all
        total_paid_not_lpu = 0.0

    kpi_rows: List[List[str]] = [
        ["Quantidade de orçamentos", _fmt_int(qtd_orcamentos)],
        ["Quantidade de itens", _fmt_int(qtd_itens_total)],
        ["Valor total pago", _brl(total_paid_all)],
        ["Itens LPU (qtd | % | valor)", f"{_fmt_int(qtd_lpu)} | {_fmt_pct(pct_lpu)} | {_brl(total_paid_lpu)}"],
        ["Itens NÃO LPU (qtd | % | valor)", f"{_fmt_int(qtd_nao_lpu)} | {_fmt_pct(pct_nao_lpu)} | {_brl(total_paid_not_lpu)}"],
    ]

    # ✅ Ordem correta: LPU -> NLPU -> TOTAL
    if create_stats_lpu:
        kpi_rows.append(["Potencial ressarcimento (LPU)", _brl(pot_lpu)])
    if create_stats_nlpu:
        kpi_rows.append(["Potencial ressarcimento (NLPU)", _brl(pot_nlpu)])
    if create_stats_lpu and create_stats_nlpu:
        kpi_rows.append(["Potencial ressarcimento (Total)", _brl(pot_total)])

    kpi_tbl = Table(kpi_rows, colWidths=[8.8 * cm, 7.2 * cm])
    kpi_tbl.setStyle(
        TableStyle(
            [
                ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("BACKGROUND", (0, 0), (-1, -1), colors.white),
            ]
        )
    )

    elements.append(Paragraph("1) Resumo Executivo", h1))
    elements.append(Paragraph("Visão consolidada para decisão: volume, mix LPU vs NÃO LPU e potenciais de ressarcimento.", body))
    elements.append(Spacer(1, 8))
    elements.append(Paragraph("KPIs principais", h2))
    elements.append(kpi_tbl)
    elements.append(Spacer(1, 14))

    # ---------
    # LPU: distribuição de status
    # ---------
    if lpu_pack is not None:
        elements.append(Paragraph("Distribuição de status (LPU)", h2))
        sc = lpu_pack["status_counts"].copy()
        sc["%"] = sc["%"].map(_fmt_pct)

        chart_status = work / "status_lpu.png"
        _save_bar_chart(sc, x="Status", y="Itens", title="Distribuição de status (LPU)", out_png=chart_status)

        elements.append(Image(str(chart_status), width=16.5 * cm, height=8 * cm))
        elements.append(Spacer(1, 8))
        elements.append(_table(sc, [9.0 * cm, 3.5 * cm, 3.5 * cm]))
        elements.append(PageBreak())

    # ---------
    # 2) Top Agências
    # ---------
    elements.append(Paragraph("2) Top Agências", h1))
    elements.append(Paragraph(f"Concentração de impacto para priorização operacional (status: {cfg.status_refund}).", body))
    elements.append(Spacer(1, 8))

    if create_stats_lpu and lpu_pack is not None:
        df_ref = lpu_pack["df_vis"]
        col_status = lpu_pack["col_status"]
        col_diff = lpu_pack["col_diff"]
        ref = df_ref[df_ref[col_status].eq(_canon_status(cfg.status_refund))].copy()

        top_ag_lpu = _top_agencies(
            ref,
            col_ag=cfg.col_agency,
            col_city=cfg.col_city,
            col_uf=cfg.col_uf,
            col_value=col_diff,
            n=top_agencies_n,
        )
        elements.append(Paragraph(f"Top {top_agencies_n} agências — potencial ressarcimento (LPU)", h2))
        elements.append(_table(top_ag_lpu, [3.0 * cm, 7.5 * cm, 1.2 * cm, 4.3 * cm]) if len(top_ag_lpu) else Paragraph("Sem dados para Top Agências (LPU).", body))
        elements.append(Spacer(1, 12))

    if create_stats_nlpu and nlpu_pack is not None:
        df_ref = nlpu_pack["df_vis"]
        col_status = nlpu_pack["col_status"]
        col_diff = nlpu_pack["col_diff"]
        ref = df_ref[df_ref[col_status].eq(_canon_status(cfg.status_refund))].copy()

        top_ag_nlpu = _top_agencies(
            ref,
            col_ag=cfg.col_agency,
            col_city=cfg.col_city,
            col_uf=cfg.col_uf,
            col_value=col_diff,
            n=top_agencies_n,
        )
        elements.append(Paragraph(f"Top {top_agencies_n} agências — potencial ressarcimento (NLPU)", h2))
        elements.append(_table(top_ag_nlpu, [3.0 * cm, 7.5 * cm, 1.2 * cm, 4.3 * cm]) if len(top_ag_nlpu) else Paragraph("Sem dados para Top Agências (NLPU).", body))
        elements.append(Spacer(1, 12))

    elements.append(PageBreak())

    # ---------
    # 3) Top Fornecedores
    # ---------
    elements.append(Paragraph("3) Top Fornecedores / Construtoras", h1))
    elements.append(Paragraph("Visão de concentradores por fornecedor para tratativa e negociação.", body))
    elements.append(Spacer(1, 8))

    if create_stats_lpu and lpu_pack is not None:
        df_ref = lpu_pack["df_vis"]
        col_status = lpu_pack["col_status"]
        col_diff = lpu_pack["col_diff"]
        ref = df_ref[df_ref[col_status].eq(_canon_status(cfg.status_refund))].copy()

        top_sup_lpu = _top_suppliers(ref, col_supplier=cfg.col_supplier, col_value=col_diff, n=top_suppliers_n)
        elements.append(Paragraph(f"Top {top_suppliers_n} fornecedores — ressarcimento (LPU)", h2))
        elements.append(_table(top_sup_lpu, [11.5 * cm, 4.5 * cm]) if len(top_sup_lpu) else Paragraph("Sem dados para Top Fornecedores (LPU).", body))
        elements.append(Spacer(1, 12))

    if create_stats_nlpu and nlpu_pack is not None:
        df_ref = nlpu_pack["df_vis"]
        col_status = nlpu_pack["col_status"]
        col_diff = nlpu_pack["col_diff"]
        ref = df_ref[df_ref[col_status].eq(_canon_status(cfg.status_refund))].copy()

        top_sup_nlpu = _top_suppliers(ref, col_supplier=cfg.col_supplier, col_value=col_diff, n=top_suppliers_n)
        elements.append(Paragraph(f"Top {top_suppliers_n} fornecedores — ressarcimento (NLPU)", h2))
        elements.append(_table(top_sup_nlpu, [11.5 * cm, 4.5 * cm]) if len(top_sup_nlpu) else Paragraph("Sem dados para Top Fornecedores (NLPU).", body))
        elements.append(Spacer(1, 12))

    elements.append(PageBreak())

    # ---------
    # 4) Top Itens
    # ---------
    elements.append(Paragraph("4) Top Itens", h1))
    elements.append(Paragraph("Itens mais recorrentes para priorizar padronização (LPU) e ações de conversão (NÃO LPU).", body))
    elements.append(Spacer(1, 8))

    if lpu_pack is not None:
        _, col_item_name = _resolve_item_cols(lpu_pack["df_vis"], cfg)
        d_vis = lpu_pack["df_vis"]
        col_status = lpu_pack["col_status"]
        col_paid = lpu_pack["col_paid"]

        mask_not_lpu = d_vis[col_status].eq(_canon_status(cfg.status_not_lpu))
        d_lpu = d_vis.loc[~mask_not_lpu].copy()
        d_not = d_vis.loc[mask_not_lpu].copy()

        top_lpu_items = _top_items(d_lpu, col_item_name=col_item_name, col_paid=col_paid, n=top_items_n, denom=len(d_lpu))
        top_not_items = _top_items(d_not, col_item_name=col_item_name, col_paid=col_paid, n=top_items_n, denom=len(d_not))

        elements.append(Paragraph(f"Top {top_items_n} itens LPU (mais frequentes)", h2))
        elements.append(_table(top_lpu_items, [9.8 * cm, 2.0 * cm, 2.0 * cm, 2.2 * cm]) if len(top_lpu_items) else Paragraph("Sem dados para Top Itens LPU.", body))
        elements.append(Spacer(1, 12))

        elements.append(Paragraph(f"Top {top_items_n} itens NÃO LPU (mais frequentes)", h2))
        elements.append(_table(top_not_items, [9.8 * cm, 2.0 * cm, 2.0 * cm, 2.2 * cm]) if len(top_not_items) else Paragraph("Sem dados para Top Itens NÃO LPU.", body))
        elements.append(Spacer(1, 12))
    else:
        elements.append(Paragraph("Top Itens disponível apenas quando create_stats_lpu=True.", body))

    doc.build(elements)

    if verbose:
        logger.info(f"✅ PDF gerado: {out_pdf}")


# ============================================================
# 7) ORQUESTRADOR (API pública)
# ============================================================

def run_validation_reporting_pdf(
    *,
    df_result: pd.DataFrame,
    output_pdf: PathLike = "REL_EXEC_LPU_NLPU.pdf",
    validator_output_pdf: bool = True,
    create_stats_lpu: bool = True,
    create_stats_nlpu: bool = False,
    verbose: bool = False,
    top_agencies_n: int = 10,
    top_suppliers_n: int = 10,
    top_items_n: int = 10,
    workdir: Optional[PathLike] = None,
    config: Optional[ReportConfig] = None,
) -> None:
    """
    Wrapper simples para gerar PDF executivo.

    Observação:
    - Se create_stats_nlpu=True, espera que `df_result` seja a base de continuação (pós-NLPU),
      contendo as colunas NLPU configuradas (col_status_nlpu/col_diff_nlpu).
    """
    if not validator_output_pdf:
        if verbose:
            logger.info("Geração de relatório em PDF desativada.")
        return

    cfg = config or ReportConfig()

    generate_executive_report_pdf(
        df_result=df_result,
        output_pdf=output_pdf,
        cfg=cfg,
        create_stats_lpu=bool(create_stats_lpu),
        create_stats_nlpu=bool(create_stats_nlpu),
        verbose=bool(verbose),
        top_agencies_n=int(top_agencies_n),
        top_suppliers_n=int(top_suppliers_n),
        top_items_n=int(top_items_n),
        workdir=workdir,
    )

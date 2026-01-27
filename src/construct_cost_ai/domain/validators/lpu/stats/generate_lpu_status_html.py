"""
Relatório Executivo — Validador LPU (HTML + Plotly) — Unificado (LPU + NLPU)
============================================================================

✅ 1 único dataframe de entrada (`df_result`)
- Use a base "pós-LPU" para relatório só de LPU
- Use a base "pós-NLPU" (continuação) para relatório LPU+NLPU

✅ Ativação por flags
- create_stats_lpu=True/False
- create_stats_nlpu=True/False  (só renderiza se colunas NLPU existirem)

✅ Parametrização fácil (no topo do arquivo)
- nomes/alternativas das colunas
- valores canônicos de status e filtros
- tamanhos de TOP N

Ordem das seções (executivo):
1) Resumo (KPIs + distribuição de status)
2) Top Agências (potencial ressarcimento)
3) Top Fornecedores/Construtoras (potencial ressarcimento)
4) Top Itens (LPU e NÃO LPU)
5) (Opcional) Resultado NLPU (KPIs + Top Agências/Fornecedores/Itens NLPU)

Observações importantes (base exemplo do Emerson):
- Base LPU: colunas incluem "VALIDADOR_LPU", "DIFERENÇA TOTAL", "VALOR TOTAL PAGO", "VALOR TOTAL LPU", "ID", "NOME"
- Base NLPU (continuação): colunas incluem "RESULTADO VALIDADOR LPU", "RESULTADO VALIDADOR NLPU",
  "MATCH FUZZY - DIFERENÇA TOTAL" (potencial NLPU), "MATCH FUZZY - VALOR TOTAL", "CÓD ITEM", "NOME ITEM"

Requisito do usuário:
- Quando create_stats_lpu e create_stats_nlpu estiverem ativos:
    - mostrar Potencial ressarcimento LPU
    - mostrar Potencial ressarcimento NLPU
    - mostrar Potencial ressarcimento TOTAL (LPU + NLPU)
- Parametrizável no topo: colunas e valores de filtro

"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple, Union

import pandas as pd
import plotly.express as px


# =============================================================================
# 1) PARAMETRIZAÇÃO (AJUSTE AQUI)
# =============================================================================

@dataclass(frozen=True)
class ReportConfig:
    # -------------------------
    # Colunas — LPU (aceita alternativas)
    # -------------------------
    lpu_status_cols: Tuple[str, ...] = ("VALIDADOR_LPU", "RESULTADO VALIDADOR LPU")
    paid_cols: Tuple[str, ...] = ("VALOR TOTAL PAGO",)
    diff_cols: Tuple[str, ...] = ("DIFERENÇA TOTAL",)

    # opcional
    total_lpu_cols: Tuple[str, ...] = ("VALOR TOTAL LPU",)

    # localização
    agency_cols: Tuple[str, ...] = ("NUMERO_AGENCIA", "AGENCIA", "NUM_AGENCIA")
    city_cols: Tuple[str, ...] = ("MUNICIPIO", "CIDADE")
    uf_cols: Tuple[str, ...] = ("UF",)

    # fornecedor/construtora
    supplier_cols: Tuple[str, ...] = ("CONSTRUTORA", "FORNECEDOR")

    # item (LPU)
    item_id_cols: Tuple[str, ...] = ("ID", "ID ITEM", "COD ITEM", "CÓD ITEM")
    item_name_cols: Tuple[str, ...] = ("NOME", "NOME ITEM", "ITEM", "DESCRICAO", "DESCRIÇÃO")

    # orçamento (para contagem de orçamentos)
    budget_id_cols: Tuple[str, ...] = (
        "ID_ORCAMENTO", "ORCAMENTO_ID", "NUM_ORCAMENTO", "ORCAMENTO", "COD_ORCAMENTO", "ORC_ID",
        "SOURCE_FILE", "ARQUIVO_ORCAMENTO", "NOME_ARQUIVO", "FILE_NAME",
    )

    # -------------------------
    # Colunas — NLPU (continuação)
    # -------------------------
    nlpu_status_cols: Tuple[str, ...] = ("RESULTADO VALIDADOR NLPU", "VALIDADOR_NLPU")
    nlpu_diff_cols: Tuple[str, ...] = ("MATCH FUZZY - DIFERENÇA TOTAL", "DIFERENÇA TOTAL NLPU", "DIFERENÇA TOTAL (NLPU)")
    nlpu_paid_cols: Tuple[str, ...] = ("MATCH FUZZY - VALOR TOTAL", "VALOR TOTAL (MATCH)", "VALOR TOTAL NLPU")

    # para top itens NLPU (normalmente são itens originais não-LPU)
    nlpu_item_id_cols: Tuple[str, ...] = ("CÓD ITEM", "COD ITEM", "ID", "ID ITEM")
    nlpu_item_name_cols: Tuple[str, ...] = ("NOME ITEM", "ITEM", "DESCRICAO", "DESCRIÇÃO")

    # -------------------------
    # Valores canônicos de status (ajuste aqui)
    # -------------------------
    status_refund: str = "PARA RESSARCIMENTO"
    status_not_lpu: str = "ITEM NAO LPU"     # canonizado: "ITEM NAO LPU" (sem underscore)
    status_ok: str = "OK"
    hidden_statuses: tuple[str, ...] = ("PARA COMPLEMENTO",)

    # -------------------------
    # Top N defaults
    # -------------------------
    top_agencies_n: int = 10
    top_suppliers_n: int = 10
    top_items_n: int = 10

    # visual
    plotly_template: str = "plotly_dark"


CFG = ReportConfig()


# =============================================================================
# 2) FALLBACK logger/settings (compatível fora do projeto)
# =============================================================================
try:
    from config.config_logger import logger  # type: ignore
except Exception:  # pragma: no cover
    import logging
    logger = logging.getLogger("relatorio_exec")
    if not logger.handlers:
        logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")


PathLike = Union[str, Path]


# =============================================================================
# 3) Helpers
# =============================================================================
def _as_path_str(p: PathLike) -> str:
    return str(Path(p))


def _canon_status(x: Any) -> str:
    s = "" if x is None else str(x)
    s = s.strip().upper().replace("_", " ")
    s = " ".join(s.split())
    return s


def _pick_first_existing(df: pd.DataFrame, candidates: Sequence[str], *, required: bool = True, label: str = "") -> Optional[str]:
    for c in candidates:
        if c in df.columns:
            return c
    if required:
        raise KeyError(f"Coluna não encontrada para {label or 'campo'}; tentado: {list(candidates)}")
    return None


def _to_numeric(df: pd.DataFrame, col: str) -> pd.Series:
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


def _infer_budget_count(df: pd.DataFrame, *, verbose: bool) -> int:
    c = _pick_first_existing(df, CFG.budget_id_cols, required=False, label="ID orçamento")
    if c is None:
        if verbose:
            logger.warning("Não encontrei coluna de orçamento (ex: SOURCE_FILE/ID_ORCAMENTO). Assumindo 1 orçamento.")
        return 1
    n = int(df[c].nunique(dropna=True))
    return max(n, 1)


def _df_to_html_table(df: pd.DataFrame, *, table_id: str) -> str:
    if df is None or len(df) == 0:
        return "<div class='empty'>Sem dados.</div>"
    return df.to_html(index=False, escape=True, table_id=table_id, classes="tbl", border=0)


def _html_shell(*, title: str, body_html: str) -> str:
    return f"""<!doctype html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>{title}</title>
  <script src="https://cdn.plot.ly/plotly-2.30.0.min.js"></script>
  <style>
    :root {{
      --bg: #0b0f17;
      --card: #0f172a;
      --muted: #9CA3AF;
      --text: #E5E7EB;
      --line: rgba(255,255,255,0.10);
      --zebra: rgba(255,255,255,0.03);
      --chip: rgba(255,255,255,0.06);
      --shadow: 0 18px 40px rgba(0,0,0,0.35);
    }}
    body {{
      margin: 0; padding: 28px 18px;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial;
      background: radial-gradient(1200px 500px at 20% -10%, rgba(99,102,241,0.22), transparent 60%),
                  radial-gradient(900px 400px at 90% 10%, rgba(14,165,233,0.16), transparent 60%),
                  var(--bg);
      color: var(--text);
    }}
    .wrap {{ max-width: 1120px; margin: 0 auto; }}
    .header {{
      display: flex; flex-wrap: wrap; justify-content: space-between; gap: 12px;
      padding: 16px 18px;
      background: linear-gradient(180deg, rgba(255,255,255,0.06), rgba(255,255,255,0.02));
      border: 1px solid var(--line);
      border-radius: 16px;
      box-shadow: var(--shadow);
    }}
    .h-title {{ font-size: 20px; font-weight: 750; letter-spacing: 0.2px; }}
    .h-sub {{ margin-top: 6px; color: var(--muted); font-size: 12.5px; }}
    .chips {{ display: flex; gap: 8px; flex-wrap: wrap; align-items: flex-start; }}
    .chip {{
      padding: 8px 10px; border-radius: 999px;
      background: var(--chip); border: 1px solid var(--line);
      font-size: 12px; color: var(--text); white-space: nowrap;
    }}
    .chip span {{ color: var(--muted); margin-right: 6px; font-weight: 600; }}
    .grid {{
      display: grid; grid-template-columns: repeat(12, 1fr);
      gap: 14px; margin-top: 16px;
    }}
    .section {{ grid-column: span 12; margin-top: 8px; padding: 0 2px; }}
    .section h1 {{ margin: 0; font-size: 14px; letter-spacing: 0.2px; color: var(--text); }}
    .section p {{ margin: 6px 0 0 0; font-size: 12.5px; color: var(--muted); }}
    .divider {{ margin-top: 10px; height: 1px; background: var(--line); }}

    .card {{
      grid-column: span 12;
      background: linear-gradient(180deg, rgba(255,255,255,0.03), rgba(255,255,255,0.01));
      border: 1px solid var(--line);
      border-radius: 16px;
      padding: 14px 14px;
      box-shadow: var(--shadow);
    }}
    .card h2 {{ font-size: 13px; margin: 0; letter-spacing: .2px; }}
    .card .hint {{ margin-top: 6px; color: var(--muted); font-size: 12.5px; }}

    .kpis {{
      display: grid; gap: 10px;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      margin-top: 12px;
    }}
    .kpi {{
      background: rgba(255,255,255,0.02);
      border: 1px solid var(--line);
      border-radius: 14px;
      padding: 12px;
    }}
    .kpi .label {{ color: var(--muted); font-size: 12px; }}
    .kpi .value {{ margin-top: 6px; font-size: 16px; font-weight: 800; }}

    .plot {{ width: 100%; height: 420px; margin-top: 10px; }}

    .tbl {{
      width: 100%;
      border-collapse: collapse;
      font-size: 12.5px;
      margin-top: 12px;
      overflow: hidden;
      border-radius: 12px;
    }}
    .tbl th, .tbl td {{
      padding: 10px 10px;
      border-bottom: 1px solid var(--line);
      vertical-align: top;
    }}
    .tbl th {{
      text-align: left;
      position: sticky;
      top: 0;
      background: rgba(17,24,39,0.92);
      backdrop-filter: blur(6px);
      z-index: 1;
      font-size: 12px;
      color: rgba(229,231,235,0.95);
    }}
    .tbl tr:nth-child(even) td {{ background: var(--zebra); }}

    .empty {{
      color: var(--muted);
      padding: 10px;
      border: 1px dashed var(--line);
      border-radius: 10px;
      margin-top: 10px;
    }}

    @media (max-width: 1000px) {{
      .kpis {{ grid-template-columns: 1fr; }}
    }}
  </style>
</head>
<body>
  <div class="wrap">
    {body_html}
  </div>
</body>
</html>"""


# =============================================================================
# 4) Computations (LPU / NLPU)
# =============================================================================
def _top_items_table(
    df: pd.DataFrame,
    *,
    col_item_name: str,
    col_paid: str,
    n: int,
    denom_for_pct: int,
) -> pd.DataFrame:
    """
    Tabela: Item | Qtd | % | Valor (sem coluna chave/código)
    """
    g = (
        df.groupby(col_item_name, dropna=False)
        .agg(qtd=(col_item_name, "size"), valor=(col_paid, "sum"))
        .reset_index()
        .sort_values(["qtd", "valor"], ascending=[False, False])
        .head(int(n))
    )
    denom = max(int(denom_for_pct), 1)
    g["pct"] = (g["qtd"] / denom * 100.0).round(1)

    return pd.DataFrame(
        {
            "Item": g[col_item_name].astype(str),
            "Qtd": g["qtd"].astype(int),
            "%": g["pct"].map(_fmt_pct),
            "Valor": g["valor"].map(_brl),
        }
    )


def _top_agencies_raw(
    df: pd.DataFrame,
    *,
    col_agency: str,
    col_city: str,
    col_uf: str,
    col_value: str,
    n: int,
) -> pd.DataFrame:
    out = (
        df.groupby([col_agency, col_city, col_uf])[col_value]
        .sum()
        .sort_values(ascending=False)
        .head(int(n))
        .reset_index()
    )
    out[col_agency] = out[col_agency].astype(str)  # ✅ eixo categórico
    return out


def _top_agencies_table_from_raw(
    agencies_raw: pd.DataFrame,
    *,
    col_agency: str,
    col_city: str,
    col_uf: str,
    col_value: str,
    value_label: str,
) -> pd.DataFrame:
    out = agencies_raw.rename(
        columns={col_agency: "Agência", col_city: "Município", col_uf: "UF", col_value: value_label}
    ).copy()
    out[value_label] = out[value_label].map(_brl)
    return out


def _top_suppliers_raw(
    df: pd.DataFrame,
    *,
    col_supplier: str,
    col_value: str,
    n: int,
) -> pd.DataFrame:
    out = (
        df.groupby(col_supplier)[col_value]
        .sum()
        .sort_values(ascending=False)
        .head(int(n))
        .reset_index()
    )
    out[col_supplier] = out[col_supplier].astype(str)
    return out


def _top_suppliers_table_from_raw(
    suppliers_raw: pd.DataFrame,
    *,
    col_supplier: str,
    col_value: str,
    value_label: str,
) -> pd.DataFrame:
    out = suppliers_raw.rename(columns={col_supplier: "Fornecedor/Construtora", col_value: value_label}).copy()
    out[value_label] = out[value_label].map(_brl)
    return out


# =============================================================================
# 5) HTML Report (Main)
# =============================================================================
def generate_exec_report_html(
    df_result: pd.DataFrame,
    output_html: PathLike,
    *,
    create_stats_lpu: bool = True,
    create_stats_nlpu: bool = False,
    cfg: ReportConfig = CFG,
    verbose: bool = False,
    # override Top N (opcional)
    top_agencies_n: Optional[int] = None,
    top_suppliers_n: Optional[int] = None,
    top_items_n: Optional[int] = None,
) -> None:
    top_agencies_n = int(top_agencies_n or cfg.top_agencies_n)
    top_suppliers_n = int(top_suppliers_n or cfg.top_suppliers_n)
    top_items_n = int(top_items_n or cfg.top_items_n)

    df = df_result.copy()

    # pick columns
    col_paid = _pick_first_existing(df, cfg.paid_cols, label="valor pago")
    col_diff = _pick_first_existing(df, cfg.diff_cols, label="diferença")
    col_lpu_total = _pick_first_existing(df, cfg.total_lpu_cols, required=False, label="valor total LPU")

    col_agency = _pick_first_existing(df, cfg.agency_cols, required=False, label="agência")
    col_city = _pick_first_existing(df, cfg.city_cols, required=False, label="município")
    col_uf = _pick_first_existing(df, cfg.uf_cols, required=False, label="UF")
    col_supplier = _pick_first_existing(df, cfg.supplier_cols, required=False, label="fornecedor/construtora")

    col_item_name = _pick_first_existing(df, cfg.item_name_cols, required=False, label="nome item")
    if col_item_name is None:
        raise KeyError("Não encontrei coluna de item para ranking (LPU). Ajuste CFG.item_name_cols.")

    # LPU status col
    col_status_lpu = _pick_first_existing(df, cfg.lpu_status_cols, required=False, label="status LPU")

    # NLPU cols
    col_status_nlpu = _pick_first_existing(df, cfg.nlpu_status_cols, required=False, label="status NLPU")
    col_diff_nlpu = _pick_first_existing(df, cfg.nlpu_diff_cols, required=False, label="diferença NLPU")
    col_paid_nlpu = _pick_first_existing(df, cfg.nlpu_paid_cols, required=False, label="valor NLPU")
    col_item_name_nlpu = _pick_first_existing(df, cfg.nlpu_item_name_cols, required=False, label="nome item NLPU")

    # normalize types
    df[col_paid] = _to_numeric(df, col_paid)
    df[col_diff] = _to_numeric(df, col_diff)

    if col_lpu_total and col_lpu_total in df.columns:
        df[col_lpu_total] = _to_numeric(df, col_lpu_total)

    if col_status_lpu and col_status_lpu in df.columns:
        df[col_status_lpu] = df[col_status_lpu].map(_canon_status)

    if col_status_nlpu and col_status_nlpu in df.columns:
        df[col_status_nlpu] = df[col_status_nlpu].map(_canon_status)

    if col_diff_nlpu and col_diff_nlpu in df.columns:
        df[col_diff_nlpu] = _to_numeric(df, col_diff_nlpu)

    if col_paid_nlpu and col_paid_nlpu in df.columns:
        df[col_paid_nlpu] = _to_numeric(df, col_paid_nlpu)

    # canons
    status_refund = _canon_status(cfg.status_refund)
    status_not_lpu = _canon_status(cfg.status_not_lpu)

    # KPIs base
    qtd_itens = int(len(df))
    qtd_orcamentos = _infer_budget_count(df, verbose=verbose)
    total_paid = float(df[col_paid].sum())

    # LPU vs NÃO LPU (sempre baseado em status LPU)
    if col_status_lpu is not None and col_status_lpu in df.columns:
        mask_not_lpu = df[col_status_lpu].eq(status_not_lpu)
    else:
        mask_not_lpu = pd.Series([False] * len(df), index=df.index)

    qtd_nao_lpu = int(mask_not_lpu.sum())
    qtd_lpu = int((~mask_not_lpu).sum())
    pct_nao_lpu = (qtd_nao_lpu / qtd_itens * 100.0) if qtd_itens else 0.0
    pct_lpu = (qtd_lpu / qtd_itens * 100.0) if qtd_itens else 0.0

    total_paid_not_lpu = float(df.loc[mask_not_lpu, col_paid].sum())
    total_paid_lpu = float(df.loc[~mask_not_lpu, col_paid].sum())

    # Potenciais (LPU / NLPU)
    potential_refund_lpu = 0.0
    if create_stats_lpu and col_status_lpu is not None and col_status_lpu in df.columns:
        potential_refund_lpu = float(df.loc[df[col_status_lpu].eq(status_refund), col_diff].sum())

    nlpu_available = col_status_nlpu in df.columns if col_status_nlpu else False
    nlpu_available = nlpu_available and (col_diff_nlpu in df.columns if col_diff_nlpu else False)

    potential_refund_nlpu = 0.0
    if create_stats_nlpu and nlpu_available:
        potential_refund_nlpu = float(df.loc[df[col_status_nlpu].eq(status_refund), col_diff_nlpu].sum())

    potential_refund_total = float(potential_refund_lpu + potential_refund_nlpu)

    # Status distribution (LPU status)
    if create_stats_lpu and col_status_lpu and col_status_lpu in df.columns:
        s = df[col_status_lpu]
        if getattr(CFG, "hidden_statuses", ()):
            s = s[~s.isin(CFG.hidden_statuses)]
        status_counts = s.value_counts().rename_axis("Status").reset_index(name="Itens")
        status_counts["%"] = (status_counts["Itens"] / max(qtd_itens, 1) * 100).round(1).map(_fmt_pct)
    else:
        status_counts = pd.DataFrame(columns=["Status", "Itens", "%"])

    # Plotly: status bar
    if len(status_counts) > 0:
        fig_status = px.bar(
            status_counts,
            x="Status",
            y="Itens",
            title="Distribuição de status (LPU)",
            template=cfg.plotly_template,
        )
        fig_status.update_layout(margin=dict(l=10, r=10, t=60, b=10), title=dict(x=0, xanchor="left"))
        fig_status_html = fig_status.to_html(include_plotlyjs=False, full_html=False, config={"displaylogo": False})
    else:
        fig_status_html = "<div class='empty'>Sem dados de status LPU para plot.</div>"

    # -------------------------
    # Top Agências / Fornecedores (LPU ressarcimento)
    # -------------------------
    agencies_tbl = pd.DataFrame()
    suppliers_tbl = pd.DataFrame()
    fig_agencies_html = "<div class='empty'>Sem dados para Top Agências.</div>"
    fig_suppliers_html = "<div class='empty'>Sem dados para Top Fornecedores.</div>"

    has_geo = all([col_agency, col_city, col_uf]) and all(c in df.columns for c in [col_agency, col_city, col_uf])
    if create_stats_lpu and has_geo and col_status_lpu and col_status_lpu in df.columns:
        df_refund = df[df[col_status_lpu].eq(status_refund)]
        if len(df_refund) > 0:
            agencies_raw = _top_agencies_raw(
                df_refund,
                col_agency=col_agency,
                col_city=col_city,
                col_uf=col_uf,
                col_value=col_diff,
                n=top_agencies_n,
            )
            fig_ag = px.bar(
                agencies_raw,
                x=col_agency,
                y=col_diff,
                title=f"Top {top_agencies_n} agências — potencial ressarcimento (LPU)",
                template=cfg.plotly_template,
            )
            fig_ag.update_layout(
                margin=dict(l=10, r=10, t=60, b=10),
                title=dict(x=0, xanchor="left"),
                xaxis=dict(type="category"),
            )
            fig_agencies_html = fig_ag.to_html(include_plotlyjs=False, full_html=False, config={"displaylogo": False})
            agencies_tbl = _top_agencies_table_from_raw(
                agencies_raw,
                col_agency=col_agency,
                col_city=col_city,
                col_uf=col_uf,
                col_value=col_diff,
                value_label="Potencial (R$)",
            )

            if col_supplier and col_supplier in df.columns:
                suppliers_raw = _top_suppliers_raw(
                    df_refund,
                    col_supplier=col_supplier,
                    col_value=col_diff,
                    n=top_suppliers_n,
                )
                fig_sup = px.bar(
                    suppliers_raw,
                    x=col_supplier,
                    y=col_diff,
                    title=f"Top {top_suppliers_n} fornecedores/construtoras — ressarcimento (LPU)",
                    template=cfg.plotly_template,
                )
                fig_sup.update_layout(
                    margin=dict(l=10, r=10, t=60, b=10),
                    title=dict(x=0, xanchor="left"),
                    xaxis=dict(type="category"),
                )
                fig_suppliers_html = fig_sup.to_html(include_plotlyjs=False, full_html=False, config={"displaylogo": False})
                suppliers_tbl = _top_suppliers_table_from_raw(
                    suppliers_raw,
                    col_supplier=col_supplier,
                    col_value=col_diff,
                    value_label="Potencial (R$)",
                )

    # -------------------------
    # Top Itens (LPU / NÃO LPU)
    # -------------------------
    top_items_lpu_tbl = pd.DataFrame()
    top_items_not_lpu_tbl = pd.DataFrame()
    if create_stats_lpu:
        if qtd_lpu > 0:
            top_items_lpu_tbl = _top_items_table(
                df.loc[~mask_not_lpu],
                col_item_name=col_item_name,
                col_paid=col_paid,
                n=top_items_n,
                denom_for_pct=qtd_lpu,
            )
        if qtd_nao_lpu > 0:
            top_items_not_lpu_tbl = _top_items_table(
                df.loc[mask_not_lpu],
                col_item_name=col_item_name,
                col_paid=col_paid,
                n=top_items_n,
                denom_for_pct=qtd_nao_lpu,
            )

    # -------------------------
    # NLPU seção (opcional)
    # -------------------------
    nlpu_block_html = ""
    if create_stats_nlpu and nlpu_available:
        df_nlpu_refund = df[df[col_status_nlpu].eq(status_refund)]

        # KPIs NLPU
        qtd_itens_nlpu = int(len(df[col_status_nlpu].dropna()))
        qtd_refund_nlpu = int(df_nlpu_refund.shape[0])
        total_match_value = float(df[col_paid_nlpu].sum()) if col_paid_nlpu and col_paid_nlpu in df.columns else 0.0

        # Top agências NLPU (se tiver geo)
        fig_ag_nlpu_html = "<div class='empty'>Sem dados NLPU para Top Agências.</div>"
        ag_nlpu_tbl = pd.DataFrame()
        if has_geo and len(df_nlpu_refund) > 0:
            ag_raw_nlpu = _top_agencies_raw(
                df_nlpu_refund,
                col_agency=col_agency,
                col_city=col_city,
                col_uf=col_uf,
                col_value=col_diff_nlpu,
                n=top_agencies_n,
            )
            fig = px.bar(
                ag_raw_nlpu,
                x=col_agency,
                y=col_diff_nlpu,
                title=f"Top {top_agencies_n} agências — potencial ressarcimento (NLPU)",
                template=cfg.plotly_template,
            )
            fig.update_layout(
                margin=dict(l=10, r=10, t=60, b=10),
                title=dict(x=0, xanchor="left"),
                xaxis=dict(type="category"),
            )
            fig_ag_nlpu_html = fig.to_html(include_plotlyjs=False, full_html=False, config={"displaylogo": False})
            ag_nlpu_tbl = _top_agencies_table_from_raw(
                ag_raw_nlpu,
                col_agency=col_agency,
                col_city=col_city,
                col_uf=col_uf,
                col_value=col_diff_nlpu,
                value_label="Potencial (R$)",
            )

        # Top fornecedores NLPU (se tiver)
        fig_sup_nlpu_html = "<div class='empty'>Sem dados NLPU para Top Fornecedores.</div>"
        sup_nlpu_tbl = pd.DataFrame()
        if col_supplier and col_supplier in df.columns and len(df_nlpu_refund) > 0:
            sup_raw_nlpu = _top_suppliers_raw(
                df_nlpu_refund,
                col_supplier=col_supplier,
                col_value=col_diff_nlpu,
                n=top_suppliers_n,
            )
            fig = px.bar(
                sup_raw_nlpu,
                x=col_supplier,
                y=col_diff_nlpu,
                title=f"Top {top_suppliers_n} fornecedores/construtoras — ressarcimento (NLPU)",
                template=cfg.plotly_template,
            )
            fig.update_layout(
                margin=dict(l=10, r=10, t=60, b=10),
                title=dict(x=0, xanchor="left"),
                xaxis=dict(type="category"),
            )
            fig_sup_nlpu_html = fig.to_html(include_plotlyjs=False, full_html=False, config={"displaylogo": False})
            sup_nlpu_tbl = _top_suppliers_table_from_raw(
                sup_raw_nlpu,
                col_supplier=col_supplier,
                col_value=col_diff_nlpu,
                value_label="Potencial (R$)",
            )

        # Top itens NLPU (por frequência) — usa nome item NLPU se existir; senão usa col_item_name
        item_col_for_nlpu = col_item_name_nlpu if (col_item_name_nlpu and col_item_name_nlpu in df.columns) else col_item_name
        top_items_nlpu_tbl = pd.DataFrame()
        if item_col_for_nlpu and len(df_nlpu_refund) > 0:
            # denominador %: total de registros NLPU com status_refund
            denom = int(len(df_nlpu_refund))
            top_items_nlpu_tbl = _top_items_table(
                df_nlpu_refund,
                col_item_name=item_col_for_nlpu,
                col_paid=col_paid,  # valor original pago (visão executiva)
                n=top_items_n,
                denom_for_pct=max(denom, 1),
            )

        nlpu_block_html = f"""
        <div class="section">
          <h1>5) Resultado NÃO LPU</h1>
          <p>Visão do módulo NLPU (ex.: match fuzzy/contextual), com potencial de ressarcimento separado.</p>
          <div class="divider"></div>
        </div>

        <div class="card">
          <h2>KPIs — NÃO LPU</h2>
          <div class="hint">Baseada em <b>{col_status_nlpu}</b> e diferença <b>{col_diff_nlpu}</b>.</div>
          <div class="kpis">
            <div class="kpi"><div class="label">Itens com avaliação NLPU</div><div class="value">{_fmt_int(qtd_itens_nlpu)}</div></div>
            <div class="kpi"><div class="label">Itens em {status_refund} (NLPU)</div><div class="value">{_fmt_int(qtd_refund_nlpu)}</div></div>

            <div class="kpi"><div class="label">Potencial ressarcimento (LPU)</div><div class="value">{_brl(potential_refund_lpu)}</div></div>
            <div class="kpi"><div class="label">Potencial ressarcimento (NLPU)</div><div class="value">{_brl(potential_refund_nlpu)}</div></div>
            <div class="kpi"><div class="label">Potencial ressarcimento (Total)</div><div class="value">{_brl(potential_refund_total)}</div></div>
          </div>
        </div>

        <div class="card">
          <h2>Top {top_agencies_n} agências — potencial ressarcimento (NLPU)</h2>
          <div class="plot">{fig_ag_nlpu_html}</div>
          <div class="hint">Tabela</div>
          {_df_to_html_table(ag_nlpu_tbl, table_id="tbl_agencias_nlpu")}
        </div>

        <div class="card">
          <h2>Top {top_suppliers_n} fornecedores/construtoras — ressarcimento (NLPU)</h2>
          <div class="plot">{fig_sup_nlpu_html}</div>
          <div class="hint">Tabela</div>
          {_df_to_html_table(sup_nlpu_tbl, table_id="tbl_fornecedores_nlpu")}
        </div>

        <div class="card">
          <h2>Top {top_items_n} itens (NLPU → {status_refund})</h2>
          <div class="hint">Frequência e participação relativa dentro dos itens NLPU em ressarcimento.</div>
          {_df_to_html_table(top_items_nlpu_tbl, table_id="tbl_itens_nlpu")}
        </div>
        """

    # -------------------------
    # Resumo executivo — KPIs
    # -------------------------
    generated_at = datetime.now().strftime("%d/%m/%Y %H:%M")
    title = "Relatório Executivo — Validador LPU / NLPU"

    # chips
    chips = f"""
      <div class="chips">
        <div class="chip"><span>Orçamentos</span>{_fmt_int(qtd_orcamentos)}</div>
        <div class="chip"><span>Itens</span>{_fmt_int(qtd_itens)}</div>
        <div class="chip"><span>Total pago</span>{_brl(total_paid)}</div>
      </div>
    """

    header_html = f"""
      <div class="header">
        <div>
          <div class="h-title">{title}</div>
          <div class="h-sub">Gerado em {generated_at}</div>
        </div>
        {chips}
      </div>
    """

    # KPIs list: inclui LPU/NLPU separados quando ambos ativos e NLPU disponível
    kpi_cards_extra = ""
    if create_stats_lpu and create_stats_nlpu and nlpu_available:
        kpi_cards_extra = f"""
            <div class="kpi"><div class="label">Potencial ressarcimento (LPU)</div><div class="value">{_brl(potential_refund_lpu)}</div></div>
            <div class="kpi"><div class="label">Potencial ressarcimento (NLPU)</div><div class="value">{_brl(potential_refund_nlpu)}</div></div>
            <div class="kpi"><div class="label">Potencial ressarcimento (Total)</div><div class="value">{_brl(potential_refund_total)}</div></div>
        """
        # substitui o card simples de "Potencial ressarcimento" pelo trio
        kpi_potential_block = ""
    else:
        kpi_potential_block = f"""
            <div class="kpi"><div class="label">Potencial ressarcimento</div><div class="value">{_brl(potential_refund_lpu)}</div></div>
        """

    body_html = f"""
      {header_html}

      <div class="grid">

        <div class="section">
          <h1>1) Resumo Executivo</h1>
          <p>Visão consolidada para decisão: volume, mix LPU vs NÃO LPU e potenciais de ressarcimento.</p>
          <div class="divider"></div>
        </div>

        <div class="card">
          <h2>KPIs principais</h2>
          <div class="hint">Indicadores-chave do processamento atual.</div>
          <div class="kpis">
            <div class="kpi"><div class="label">Quantidade de orçamentos</div><div class="value">{_fmt_int(qtd_orcamentos)}</div></div>
            <div class="kpi"><div class="label">Quantidade de itens</div><div class="value">{_fmt_int(qtd_itens)}</div></div>
            <div class="kpi"><div class="label">Valor total pago</div><div class="value">{_brl(total_paid)}</div></div>
            <div class="kpi"><div class="label">Itens LPU (qtd | % | valor)</div><div class="value">{_fmt_int(qtd_lpu)} | {_fmt_pct(pct_lpu)} | {_brl(total_paid_lpu)}</div></div>
            <div class="kpi"><div class="label">Itens NÃO LPU (qtd | % | valor)</div><div class="value">{_fmt_int(qtd_nao_lpu)} | {_fmt_pct(pct_nao_lpu)} | {_brl(total_paid_not_lpu)}</div></div>
            {kpi_potential_block}
            {kpi_cards_extra}
          </div>
        </div>

        <div class="card">
          <h2>Distribuição de status (LPU)</h2>
          <div class="hint">Composição dos itens por classificação (coluna: {col_status_lpu or '—'}).</div>
          <div class="plot">{fig_status_html}</div>
          <div class="hint">Tabela de status</div>
          {_df_to_html_table(status_counts, table_id="tbl_status")}
        </div>

        <div class="section">
          <h1>2) Top Agências</h1>
          <p>Concentração de impacto para priorização operacional (status: {status_refund}).</p>
          <div class="divider"></div>
        </div>

        <div class="card">
          <h2>Top {top_agencies_n} agências — potencial ressarcimento (LPU)</h2>
          <div class="hint">Ranking por soma da diferença total (itens em {status_refund}).</div>
          <div class="plot">{fig_agencies_html}</div>
          <div class="hint">Tabela</div>
          {_df_to_html_table(agencies_tbl, table_id="tbl_agencias")}
        </div>

        <div class="section">
          <h1>3) Top Fornecedores / Construtoras</h1>
          <p>Concentradores por fornecedor para tratativa e negociação.</p>
          <div class="divider"></div>
        </div>

        <div class="card">
          <h2>Top {top_suppliers_n} fornecedores/construtoras — ressarcimento (LPU)</h2>
          <div class="plot">{fig_suppliers_html}</div>
          <div class="hint">Tabela</div>
          {_df_to_html_table(suppliers_tbl, table_id="tbl_fornecedores")}
        </div>

        <div class="section">
          <h1>4) Top Itens</h1>
          <p>Itens mais recorrentes para priorizar padronização (LPU) e conversão (NÃO LPU).</p>
          <div class="divider"></div>
        </div>

        <div class="card">
          <h2>Top {top_items_n} itens LPU (mais frequentes)</h2>
          <div class="hint">Frequência e participação relativa entre itens LPU.</div>
          {_df_to_html_table(top_items_lpu_tbl, table_id="tbl_itens_lpu")}
        </div>

        <div class="card">
          <h2>Top {top_items_n} itens NÃO LPU (mais frequentes)</h2>
          <div class="hint">Frequência e participação relativa entre itens NÃO LPU.</div>
          {_df_to_html_table(top_items_not_lpu_tbl, table_id="tbl_itens_nao_lpu")}
        </div>

        {nlpu_block_html}

      </div>
    """

    html = _html_shell(title=title, body_html=body_html)

    out_path = Path(_as_path_str(output_html))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html, encoding="utf-8")


# =============================================================================
# 6) Orchestrator (API pública)
# =============================================================================
def run_validation_reporting_html(
    *,
    df_result: pd.DataFrame,
    output_html: PathLike = "RELATORIO_EXEC_LPU_NLPU.html",
    validator_output_html: bool = True,
    create_stats_lpu: bool = True,
    create_stats_nlpu: bool = False,
    verbose: bool = True,
    # Top N (opcional)
    top_agencies_n: Optional[int] = None,
    top_suppliers_n: Optional[int] = None,
    top_items_n: Optional[int] = None,
) -> None:
    if not validator_output_html:
        if verbose:
            logger.info("Geração de relatório HTML desativada.")
        return

    if verbose:
        logger.info("🌐 Gerando relatório executivo (HTML + Plotly)...")
        logger.info(
            f"Itens: {len(df_result)} | HTML: {_as_path_str(output_html)} | "
            f"LPU: {create_stats_lpu} | NLPU: {create_stats_nlpu}"
        )

    generate_exec_report_html(
        df_result=df_result,
        output_html=output_html,
        create_stats_lpu=create_stats_lpu,
        create_stats_nlpu=create_stats_nlpu,
        verbose=bool(verbose),
        top_agencies_n=top_agencies_n,
        top_suppliers_n=top_suppliers_n,
        top_items_n=top_items_n,
    )

    if verbose:
        logger.info(f"✅ Relatório executivo gerado: {_as_path_str(output_html)}")

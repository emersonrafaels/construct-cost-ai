"""
Relatório Executivo — Validador LPU (HTML + Plotly)
--------------------------------------------------
Ordem:
1) Resumo Executivo (KPIs + Distribuição de status)
2) Top Agências
3) Top Fornecedores/Construtoras
4) Top Itens (LPU e NÃO LPU)

Fix:
- Corrigido erro "unhashable type: 'dict'" (Top Agências não re-agrupa DF já agregado)
- Orchestrator com defaults: validator_output_html / verbose
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, Union, Tuple, Any as AnyType

import pandas as pd
import plotly.express as px

from config.config_logger import logger
from config.config_dynaconf import get_settings

settings = get_settings()

PathLike = Union[str, Path]


# -------------------------
# Helpers
# -------------------------
def _as_path_str(p: PathLike) -> str:
    return str(Path(p))


def _canon_status(s: AnyType) -> str:
    s = "" if s is None else str(s)
    s = s.strip().upper().replace("_", " ")
    s = " ".join(s.split())
    return s


def _to_numeric_series(df: pd.DataFrame, col: str) -> pd.Series:
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
# Ranking helpers
# -------------------------
def _top_items_table(
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

    return pd.DataFrame(
        {
            "Item": g[col_item_name].astype(str),
            "Qtd": g["qtd"].astype(int),
            "%": g["pct"].map(lambda x: _fmt_pct(float(x))),
            "Valor": g["valor"].map(lambda x: _brl(float(x))),
        }
    )


def _top_agencies_raw(
    df_refund: pd.DataFrame,
    *,
    col_agency: str,
    col_city: str,
    col_uf: str,
    col_diff: str,
    n: int,
) -> pd.DataFrame:
    """
    ✅ Retorna DF agregado (raw) para plot.
    """
    return (
        df_refund.groupby([col_agency, col_city, col_uf])[col_diff]
        .sum()
        .sort_values(ascending=False)
        .head(int(n))
        .reset_index()
    )


def _top_agencies_table_from_raw(
    agencies_raw: pd.DataFrame,
    *,
    col_agency: str,
    col_city: str,
    col_uf: str,
    col_diff: str,
) -> pd.DataFrame:
    """
    ✅ Formata o DF agregado (sem re-agrupamento) para tabela.
    """
    out = agencies_raw.rename(
        columns={
            col_agency: "Agência",
            col_city: "Município",
            col_uf: "UF",
            col_diff: "Valor",
        }
    ).copy()
    out["Valor"] = out["Valor"].map(lambda x: _brl(float(x)))
    return out


def _top_suppliers_raw(
    df_refund: pd.DataFrame,
    *,
    col_supplier: str,
    col_diff: str,
    n: int,
) -> pd.DataFrame:
    return (
        df_refund.groupby(col_supplier)[col_diff]
        .sum()
        .sort_values(ascending=False)
        .head(int(n))
        .reset_index()
    )


def _top_suppliers_table_from_raw(
    suppliers_raw: pd.DataFrame,
    *,
    col_supplier: str,
    col_diff: str,
) -> pd.DataFrame:
    out = suppliers_raw.rename(columns={col_supplier: "Fornecedor/Construtora", col_diff: "Potencial (R$)"}).copy()
    out["Potencial (R$)"] = out["Potencial (R$)"].map(lambda x: _brl(float(x)))
    return out


# -------------------------
# HTML builder
# -------------------------
def _df_to_html_table(df: pd.DataFrame, *, table_id: str, numeric_cols: Optional[list[str]] = None) -> str:
    if df is None or len(df) == 0:
        return "<div class='empty'>Sem dados.</div>"

    html = df.to_html(index=False, escape=True, table_id=table_id, classes="tbl", border=0)

    # marca colunas numéricas com class "num" (alinhamento à direita)
    if numeric_cols:
        for col in numeric_cols:
            html = html.replace(f"<th>{col}</th>", f"<th class='num'>{col}</th>")
            html = html.replace(f"<td>{col}</td>", f"<td class='num'>{col}</td>")  # harmless fallback
    return html


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
      --card: #111827;
      --muted: #9CA3AF;
      --text: #E5E7EB;
      --line: rgba(255,255,255,0.10);
      --zebra: rgba(255,255,255,0.03);
    }}
    body {{
      margin: 0; padding: 24px;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial;
      background: var(--bg); color: var(--text);
    }}
    .wrap {{ max-width: 1100px; margin: 0 auto; }}
    .title {{ font-size: 22px; font-weight: 700; }}
    .subtitle {{ color: var(--muted); margin-top: 6px; }}
    .grid {{
      display: grid; gap: 12px;
      grid-template-columns: repeat(12, 1fr);
      margin-top: 16px;
    }}
    .card {{
      grid-column: span 12;
      background: var(--card);
      border: 1px solid var(--line);
      border-radius: 14px;
      padding: 14px 14px;
      box-shadow: 0 10px 30px rgba(0,0,0,0.25);
    }}
    .card h2 {{
      font-size: 14px; margin: 0 0 10px 0;
      color: var(--text); letter-spacing: .2px;
    }}
    .kpis {{
      display: grid; gap: 10px;
      grid-template-columns: repeat(2, minmax(0, 1fr));
    }}
    .kpi {{
      background: rgba(255,255,255,0.02);
      border: 1px solid var(--line);
      border-radius: 12px;
      padding: 12px;
    }}
    .kpi .label {{ color: var(--muted); font-size: 12px; }}
    .kpi .value {{ margin-top: 6px; font-size: 16px; font-weight: 700; }}
    .section {{ margin-top: 18px; font-size: 14px; color: var(--muted); }}

    .tbl {{
      width: 100%;
      border-collapse: collapse;
      font-size: 12.5px;
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
    }}
    .tbl tr:nth-child(even) td {{
      background: var(--zebra);
    }}
    .num {{ text-align: right; white-space: nowrap; }}
    .empty {{
      color: var(--muted);
      padding: 10px;
      border: 1px dashed var(--line);
      border-radius: 10px;
    }}
    .plot {{ width: 100%; height: 420px; }}
    @media (max-width: 900px) {{
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


# -------------------------
# Main HTML Report
# -------------------------
def generate_statistics_report_business_html(
    df_result: pd.DataFrame,
    output_html: PathLike,
    *,
    cfg: Optional[Dict[str, Any]] = None,
    top_agencies_n: int = 10,
    top_suppliers_n: int = 10,
    top_items_n: int = 10,
    verbose: bool = False,
) -> None:
    cfg = cfg or {}
    col_status = cfg.get("col_status", "VALIDADOR_LPU")
    col_paid = cfg.get("col_total_paid", "VALOR TOTAL PAGO")
    col_diff = cfg.get("col_difference", "DIFERENÇA TOTAL")

    col_agency = cfg.get("col_agency", "NUMERO_AGENCIA")
    col_city = cfg.get("col_city", "MUNICIPIO")
    col_uf = cfg.get("col_uf", "UF")
    col_supplier = cfg.get("col_constructor", "CONSTRUTORA")

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
    status_counts = df[col_status].value_counts().rename_axis("Status").reset_index(name="Itens")
    status_counts["%"] = (status_counts["Itens"] / max(qtd_itens, 1) * 100).round(1).map(_fmt_pct)

    # Plotly: status bar
    fig_status = px.bar(status_counts, x="Status", y="Itens", title=f"Distribuição de status ({col_status})")
    fig_status.update_layout(
        margin=dict(l=10, r=10, t=50, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )
    fig_status_html = fig_status.to_html(include_plotlyjs=False, full_html=False, config={"displaylogo": False})

    # Top Agências
    has_geo_cols = all(c in df.columns for c in [col_agency, col_city, col_uf])
    df_refund = df[df[col_status].eq(status_refund)]

    if has_geo_cols and len(df_refund) > 0:
        agencies_raw = _top_agencies_raw(
            df_refund,
            col_agency=col_agency,
            col_city=col_city,
            col_uf=col_uf,
            col_diff=col_diff,
            n=top_agencies_n,
        )
        fig_agencies = px.bar(
            agencies_raw,
            x=col_agency,
            y=col_diff,
            title=f"Top {int(top_agencies_n)} agências por potencial ressarcimento",
        )
        fig_agencies.update_layout(
            margin=dict(l=10, r=10, t=50, b=10),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
        )
        fig_agencies_html = fig_agencies.to_html(include_plotlyjs=False, full_html=False, config={"displaylogo": False})

        agencies_tbl = _top_agencies_table_from_raw(
            agencies_raw,
            col_agency=col_agency,
            col_city=col_city,
            col_uf=col_uf,
            col_diff=col_diff,
        )
    else:
        fig_agencies_html = "<div class='empty'>Sem dados para Top Agências (ou faltam colunas de localização).</div>"
        agencies_tbl = pd.DataFrame()

    # Top Fornecedores/Construtoras
    if col_supplier in df.columns and len(df_refund) > 0:
        suppliers_raw = _top_suppliers_raw(
            df_refund, col_supplier=col_supplier, col_diff=col_diff, n=top_suppliers_n
        )
        fig_suppliers = px.bar(
            suppliers_raw,
            x=col_supplier,
            y=col_diff,
            title=f"Top {int(top_suppliers_n)} fornecedores/construtoras (ressarcimento)",
        )
        fig_suppliers.update_layout(
            margin=dict(l=10, r=10, t=50, b=10),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
        )
        fig_suppliers_html = fig_suppliers.to_html(include_plotlyjs=False, full_html=False, config={"displaylogo": False})

        suppliers_tbl = _top_suppliers_table_from_raw(
            suppliers_raw, col_supplier=col_supplier, col_diff=col_diff
        )
    else:
        fig_suppliers_html = "<div class='empty'>Sem dados para Top Fornecedores/Construtoras.</div>"
        suppliers_tbl = pd.DataFrame()

    # Top Itens
    col_item_id, col_item_name = _pick_item_columns(df, cfg)

    top_items_lpu_tbl = _top_items_table(
        df.loc[~mask_not_lpu],
        col_item_id=col_item_id,
        col_item_name=col_item_name,
        col_paid=col_paid,
        n=top_items_n,
        denom_for_pct=max(qtd_lpu, 1),
    )
    top_items_not_lpu_tbl = _top_items_table(
        df.loc[mask_not_lpu],
        col_item_id=col_item_id,
        col_item_name=col_item_name,
        col_paid=col_paid,
        n=top_items_n,
        denom_for_pct=max(qtd_nao_lpu, 1),
    )

    # Build HTML body
    title = "Relatório Executivo — Validador LPU (HTML)"
    generated_at = datetime.now().strftime("%d/%m/%Y %H:%M")

    body_html = f"""
      <div class="title">{title}</div>
      <div class="subtitle">Gerado em {generated_at}</div>

      <div class="grid">
        <div class="card">
          <h2>Resumo Executivo</h2>
          <div class="kpis">
            <div class="kpi"><div class="label">Quantidade de orçamentos</div><div class="value">{_fmt_int(qtd_orcamentos)}</div></div>
            <div class="kpi"><div class="label">Quantidade de itens</div><div class="value">{_fmt_int(qtd_itens)}</div></div>
            <div class="kpi"><div class="label">Valor total pago</div><div class="value">{_brl(total_paid)}</div></div>
            <div class="kpi"><div class="label">Itens LPU (qtd | % | valor)</div><div class="value">{_fmt_int(qtd_lpu)} | {_fmt_pct(pct_lpu)} | {_brl(total_paid_lpu)}</div></div>
            <div class="kpi"><div class="label">Itens NÃO LPU (qtd | % | valor)</div><div class="value">{_fmt_int(qtd_nao_lpu)} | {_fmt_pct(pct_nao_lpu)} | {_brl(total_paid_not_lpu)}</div></div>
            <div class="kpi"><div class="label">Potencial ressarcimento</div><div class="value">{_brl(potential_refund)}</div></div>
          </div>
        </div>

        <div class="card">
          <h2>Distribuição de status</h2>
          <div class="plot">{fig_status_html}</div>
          <div class="section">Tabela de status</div>
          {_df_to_html_table(status_counts, table_id="tbl_status")}
        </div>

        <div class="card">
          <h2>Top {int(top_agencies_n)} Agências (potencial ressarcimento)</h2>
          <div class="plot">{fig_agencies_html}</div>
          <div class="section">Tabela de agências</div>
          {_df_to_html_table(agencies_tbl, table_id="tbl_agencias")}
        </div>

        <div class="card">
          <h2>Top {int(top_suppliers_n)} Fornecedores/Construtoras (ressarcimento)</h2>
          <div class="plot">{fig_suppliers_html}</div>
          <div class="section">Tabela de fornecedores</div>
          {_df_to_html_table(suppliers_tbl, table_id="tbl_fornecedores")}
        </div>

        <div class="card">
          <h2>Top {int(top_items_n)} Itens (frequência)</h2>
          <div class="section">Top {int(top_items_n)} Itens LPU</div>
          {_df_to_html_table(top_items_lpu_tbl, table_id="tbl_itens_lpu")}
          <div class="section">Top {int(top_items_n)} Itens NÃO LPU</div>
          {_df_to_html_table(top_items_not_lpu_tbl, table_id="tbl_itens_nao_lpu")}
        </div>
      </div>
    """

    html = _html_shell(title=title, body_html=body_html)

    out_path = Path(_as_path_str(output_html))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html, encoding="utf-8")


# -------------------------
# Orchestrator
# -------------------------
def run_lpu_validation_reporting_html(
    *,
    df_result: pd.DataFrame,
    validator_output_html: Optional[bool] = None,
    output_html: PathLike = "VALIDADOR_LPU_EXECUTIVO.html",
    verbose: Optional[bool] = None,
    top_agencies_n: int = 10,
    top_suppliers_n: int = 10,
    top_items_n: int = 10,
) -> None:
    if validator_output_html is None:
        validator_output_html = settings.get("module_validator_lpu.stats.validator_output_html", True)

    if verbose is None:
        verbose = settings.get("module_validator_lpu.verbose", True)

    cfg = _get_cfg(settings)
    df_norm = normalize_lpu_result(df_result, cfg)

    if verbose:
        logger.info("🌐 Gerando relatório executivo (HTML + Plotly)...")
        logger.info(
            f"Itens: {len(df_norm)} | HTML: {_as_path_str(output_html)} | "
            f"Top agências: {top_agencies_n} | Top fornecedores: {top_suppliers_n} | Top itens: {top_items_n}"
        )

    if validator_output_html:
        generate_statistics_report_business_html(
            df_norm,
            output_html=_as_path_str(output_html),
            cfg=cfg,
            top_agencies_n=int(top_agencies_n),
            top_suppliers_n=int(top_suppliers_n),
            top_items_n=int(top_items_n),
            verbose=bool(verbose),
        )
        logger.info(f"✅ Relatório executivo gerado: {_as_path_str(output_html)}")
    else:
        logger.info("Geração de relatório em HTML desativada.")

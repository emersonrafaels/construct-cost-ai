"""
Módulo de Validação LPU - Verifica discrepâncias entre orçamento e base de preços.

Este módulo realiza a conciliação entre o orçamento enviado pela construtora
e a base de dados oficial da LPU (Lista de Preços Unitários), identificando discrepâncias
nos valores com tolerância configurável.
"""

__author__ = "Emerson V. Rafael (emervin)"
__copyright__ = "Copyright 2025, Construct Cost AI"
__credits__ = ["Emerson V. Rafael"]
__license__ = "MIT"
__version__ = "1.0.0"
__maintainer__ = "Emerson V. Rafael"
__email__ = "emersonssmile@gmail.com"
__status__ = "Development"

import sys
from pathlib import Path
from typing import Union, Tuple, List, Optional, Literal, NamedTuple

import pandas as pd

# Adiciona o diretório src ao path
base_dir = Path(__file__).parents[5]
sys.path.insert(0, str(Path(base_dir, "src")))

from config.config_logger import logger
from config.config_dynaconf import get_settings
from utils.data.data_functions import read_data, export_data, cast_columns, transform_case
from utils.lpu.lpu_functions import generate_region_group_combinations, split_regiao_grupo

settings = get_settings()


class ValidatorLPUError(Exception):
    """Exceção base para erros do validador LPU."""

    pass


class FileNotFoundError(ValidatorLPUError):
    """Exceção para arquivo não encontrado."""

    pass


class MissingColumnsError(ValidatorLPUError):
    """Exceção para colunas obrigatórias ausentes."""

    pass


def load_budget(file_path: Union[str, Path]) -> pd.DataFrame:
    """
    Carrega o arquivo de orçamento.

    Args:
        path: Caminho para o arquivo de orçamento (Excel ou CSV)

    Returns:
        DataFrame com o orçamento carregado

    Raises:
        FileNotFoundError: Se o arquivo não for encontrado
        MissingColumnsError: Se colunas obrigatórias estiverem ausentes
    """
    file_path = Path(file_path)

    if not file_path.exists():
        raise FileNotFoundError(f"Arquivo de orçamento não encontrado: {file_path}")

    # Colunas obrigatórias
    required_columns = settings.get(
        "module_validator_lpu.budget_data.required_columns_with_types", []
    )

    # Coluna valor total
    column_total_value = settings.get("module_validator_lpu.column_total_value", "VALOR TOTAL")

    try:
        df = read_data(
            file_path=file_path,
            sheet_name=settings.get(
                "module_validator_lpu.budget_data.sheet_name_budget_table", "Tables"
            ),
        )
    except Exception as e:
        raise ValidatorLPUError(f"Erro ao carregar orçamento: {e}")

    # Valida colunas obrigatórias
    empty_columns = set(required_columns.keys()) - set(df.columns)
    if empty_columns:
        raise MissingColumnsError(
            f"Colunas obrigatórias ausentes no orçamento: {', '.join(empty_columns)}"
        )

    # Garante tipos corretos usando cast_columns
    try:
        df = cast_columns(df, required_columns)
    except ValueError as e:
        raise ValidatorLPUError(f"Erro ao converter tipos de colunas: {e}")

    # Se total_orcado não existir, calcula
    df = calculate_total_item(
        df=df,
        column_total_value=column_total_value,
        column_quantity=settings.get("module_validator_lpu.budget_data.column_quantity", "qtde"),
        column_unit_price=settings.get(
            "module_validator_lpu.budget_data.column_unit_price", "unitario_orcado"
        ),
    )

    return df


class LPUFormatReport(NamedTuple):
    """
    Representa o formato detectado de uma base LPU (Lista de Preços Unitários).

    Attributes:
        format (str): O formato detectado da base, podendo ser "wide", "long" ou "unknown".
    """

    format: str
    columns: list = []

    def __str__(self):
        return f"LPUFormatReport(format={self.format}, columns={self.columns})"


def identify_lpu_format(
    df: pd.DataFrame,
    *,
    expected_core_cols: Tuple[str, str, str] = ("CÓD ITEM", "ITEM", "UN"),
    long_required_cols: Tuple[str, str, str] = ("REGIAO", "GRUPO", "PRECO"),
) -> "LPUFormatReport":
    """
    Identifica se a base está no formato:
      - wide: colunas de preço por REGIAO/GRUPO (ex: 'NORTE-GRUPO1', ...)
      - long: colunas explícitas 'regiao', 'grupo', 'preco' (nomes flexíveis)
      - unknown: não dá pra inferir com confiança

    Args:
        df (pd.DataFrame): DataFrame a ser analisado.
        expected_core_cols (Tuple[str, str, str]): Colunas principais esperadas no DataFrame.
        long_required_cols (Tuple[str, str, str]): Colunas esperadas no formato long.

    Returns:
        LPUFormatReport: Relatório contendo o formato identificado e as colunas encontradas.

    Observação:
        O argumento `col_to_regiao_grupo` pode ser enviado como `report.columns` para reutilizar as colunas detectadas.
    """
    # Colunas esperadas no formato "wide"
    regions = settings.get("module_validator_lpu.lpu_data.regions", [])
    groups = settings.get("module_validator_lpu.lpu_data.groups", [])
    expected_wide_cols = generate_region_group_combinations(regions, groups, combine_regions=False) + generate_region_group_combinations(
        regions, groups, combine_regions=True)

    # Identifica colunas que seguem o padrão de região-grupo
    found_wide_cols = [col for col in df.columns if col in expected_wide_cols]

    # Verifica se todas as colunas principais estão presentes
    if all(col in df.columns for col in expected_core_cols):
        # Se as colunas de preço seguem o padrão esperado, é wide
        if found_wide_cols:
            return LPUFormatReport(format="wide", columns=found_wide_cols)
        # Se as colunas 'regiao', 'grupo' e 'preco' estão presentes, é long
        elif all(col in df.columns for col in long_required_cols):
            return LPUFormatReport(
                format="long",
                columns=settings.get(
                    "module_validator_lpu.lpu_data.long_format_columns", {}
                ).keys(),
            )

    # Se chegou aqui, o formato é desconhecido
    return LPUFormatReport(format="unknown", columns=[])


def wide_to_long(
    df_wide: pd.DataFrame,
    id_col: str = "CÓD ITEM",
    item_col: str = "ITEM",
    unit_col: str = "UN",
    keep_cols: Optional[List[str]] = None,
    col_to_regiao_grupo: List[str] = None,  # Agora espera uma lista de colunas já filtradas
    value_name: str = "preco",
) -> pd.DataFrame:
    """
    Converte uma base LPU no formato WIDE para LONG.

    No formato WIDE, os preços são organizados em colunas que representam combinações de regiões e grupos,
    como 'NORTE-GRUPO1', 'SUDESTE-GRUPO2', etc. No formato LONG, essas informações são transformadas em
    linhas, com colunas explícitas para 'regiao', 'grupo' e 'preco'.

    Args:
        df_wide (pd.DataFrame): DataFrame no formato WIDE.
        id_col (str): Nome da coluna que identifica o item (ex.: 'CÓD ITEM').
        item_col (str): Nome da coluna que descreve o item (ex.: 'ITEM').
        unit_col (str): Nome da coluna que indica a unidade (ex.: 'UN').
        keep_cols (Optional[List[str]]): Lista de colunas adicionais a serem mantidas no formato LONG.
        col_to_regiao_grupo (List[str]): Lista de colunas de região/grupo já filtradas no DataFrame.
        value_name (str): Nome da coluna que conterá os valores (ex.: 'preco').

    Returns:
        pd.DataFrame: DataFrame convertido para o formato LONG.

    Raises:
        ValueError: Se as colunas necessárias não forem encontradas ou se a conversão falhar.
    """

    # Definindo as regiões e grupos esperados
    regions = settings.get("module_validator_lpu.lpu_data.regions", [])
    groups = settings.get("module_validator_lpu.lpu_data.groups", [])

    # Copia o DataFrame para evitar alterações no original
    df_wide = df_wide.copy()

    # Verifica se col_to_regiao_grupo foi fornecido
    if not col_to_regiao_grupo:
        raise ValueError(
            "A lista de colunas de região/grupo (col_to_regiao_grupo) não foi fornecida."
        )

    # Transforma o DataFrame para o formato LONG usando a função melt
    df_long = df_wide.melt(
        id_vars=[id_col, item_col, unit_col] + (keep_cols or []),  # Colunas que permanecem fixas
        value_vars=col_to_regiao_grupo,  # Colunas que serão transformadas em linhas
        var_name="regiao_grupo",  # Nome da coluna que conterá os nomes das colunas originais
        value_name=value_name,  # Nome da coluna que conterá os valores
    )

    # Divide regiao_grupo em 'regiao' e 'grupo' usando a função split_regiao_grupo
    df_long["regiao"], df_long["grupo"] = zip(
        *df_long["regiao_grupo"].apply(lambda col: split_regiao_grupo(col, regions, groups))
    )

    # Retorna o DataFrame no formato LONG
    return df_wide, df_long


def long_to_wide(
    df_long: pd.DataFrame,
    *,
    id_col: str = "cod_item",
    item_col: str = "item",
    unit_col: str = "unidade",
    regiao_col: str = "regiao",
    grupo_col: str = "grupo",
    value_col: str = "preco",
    wide_col_formatter: Optional[callable] = None,
    aggfunc: str = "first",
) -> pd.DataFrame:
    """
    Converte LPU LONG -> WIDE.
    """
    # Cria coluna única para região-grupo se não existir
    if regiao_col in df_long.columns and grupo_col in df_long.columns:
        df_long["regiao_grupo"] = df_long[regiao_col] + "-" + df_long[grupo_col]
    else:
        df_long["regiao_grupo"] = df_long.get(regiao_col, df_long.get(grupo_col))

    # Agrega dados se necessário
    df_agg = (
        df_long.groupby([id_col, item_col, unit_col, "regiao_grupo"])
        .agg({value_col: aggfunc})
        .reset_index()
    )

    # Transforma para formato largo
    df_wide = df_agg.pivot_table(
        index=[id_col, item_col, unit_col],
        columns="regiao_grupo",
        values=value_col,
        aggfunc=aggfunc,
    ).reset_index()

    # Formata colunas largas se função fornecida
    if wide_col_formatter:
        df_wide.columns = [
            wide_col_formatter(col) if col not in [id_col, item_col, unit_col] else col
            for col in df_wide.columns
        ]

    return df_wide


def convert_lpu(
    df: pd.DataFrame,
    target: Literal["wide", "long"],
    *,
    detect: bool = True,
    **kwargs,
) -> pd.DataFrame:
    """
    Converte a LPU para o formato desejado.
    """
    if detect:
        report = identify_lpu_format(df)
        if report.format == "wide" and target == "long":
            df_wide, df_long = wide_to_long(df, col_to_regiao_grupo=report.columns, **kwargs)
        elif report.format == "long" and target == "wide":
            df_wide, df_long = long_to_wide(df, **kwargs)
        else:
            raise ValidatorLPUError(
                f"Conversão de {report.format} para {target} não suportada ou formato desconhecido."
            )
    else:
        if target == "long":
            df_wide, df_long = wide_to_long(df, **kwargs)
        elif target == "wide":
            df_wide, df_long = long_to_wide(df, **kwargs)
        else:
            raise ValidatorLPUError(f"Formato alvo desconhecido: {target}")

    return df


def load_lpu(file_path: Union[str, Path]) -> pd.DataFrame:
    """
    Carrega o arquivo base da LPU.

    Args:
        file_path: Caminho para o arquivo da LPU

    Returns:
        DataFrame com a base da LPU carregada

    Raises:
        FileNotFoundError: Se o arquivo não for encontrado
        MissingColumnsError: Se colunas obrigatórias estiverem ausentes
    """
    file_path = Path(file_path)

    if not file_path.exists():
        raise FileNotFoundError(f"Arquivo LPU não encontrado: {file_path}")

    # Colunas obrigatórias
    required_columns = settings.get(
        "module_validator_lpu.lpu_data.required_columns_with_types",
        [
            "CÓD ITEM",
            "ITEM",
            "UN",
        ],
    )

    try:
        # Ler os dados de LPU e realizar pré processing
        df = transform_case(
            read_data(
                file_path=file_path,
                sheet_name=settings.get(
                    "module_validator_lpu.lpu_data.sheet_name_budget_lpu", "sheet_name_budget_lpu"
                ),
            ),
            to_upper=True,
            columns=True,
        )
    except Exception as e:
        raise ValidatorLPUError(f"Erro ao carregar base LPU: {e}")

    # Valida colunas obrigatórias na base de LPU
    missing_columns = set(required_columns) - set(df.columns)
    if missing_columns:
        raise MissingColumnsError(
            f"Colunas obrigatórias ausentes na LPU: {', '.join(missing_columns)}"
        )

    # Detecta formato e converte se necessário
    report = identify_lpu_format(df)
    if report.format == "wide":
        df_wide, df_long = wide_to_long(df, col_to_regiao_grupo=report.columns)
        logger.info("Convertido LPU de WIDE para LONG.")
    elif report.format == "long":
        # df = long_to_wide(df)
        logger.info("Mantido LPU no formato LONG.")
    else:
        raise ValidatorLPUError(f"Formato desconhecido: {report.format}")

    try:
        # Adiciona as colunas detectadas ao required_columns
        required_columns.update({column: float for column in report.columns})
        
        # Converter as colunas do dataframe para os tipos corretos
        df_wide = cast_columns(df_wide, required_columns)
    except ValueError as e:
        raise ValidatorLPUError(f"Erro ao converter tipos de colunas: {e}")

    return df_wide


def cross_budget_lpu(budget: pd.DataFrame, lpu: pd.DataFrame) -> pd.DataFrame:
    """
    Mescla orçamento e LPU usando cod_item + unidade.

    Args:
        budget: DataFrame do orçamento
        lpu: DataFrame da base LPU

    Returns:
        DataFrame combinado com INNER JOIN

    Raises:
        ValidatorLPUError: Se a mesclagem resultar em um DataFrame vazio
    """
    # Mescla em cod_item + unidade
    merged_df = pd.merge(
        budget, lpu, on=["cod_item", "unidade"], how="inner", suffixes=("_orc", "_lpu")
    )

    if merged_df.empty:
        raise ValidatorLPUError(
            "Nenhuma correspondência encontrada entre orçamento e LPU. "
            "Verifique se cod_item e unidade estão consistentes."
        )

    # Calcula itens não encontrados na LPU
    items_not_in_lpu = len(budget) - len(merged_df)
    if items_not_in_lpu > 0:
        logger.warning(f"⚠️  Atenção: {items_not_in_lpu} itens do orçamento não encontrados na LPU")

    return merged_df


def calculate_discrepancies(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calcula discrepâncias entre orçamento e LPU.

    Adiciona as colunas:
    - valor_total_orcado: qtde * unitario_orcado
    - dif_unitario: unitario_orcado - unitario_lpu
    - dif_total: dif_unitario * qtde
    - perc_dif: (dif_unitario / unitario_lpu) * 100
    - status_conciliacao: classificação da discrepância

    Regras de classificação (tolerância configurável em settings.toml):
    - "OK": -tolerancia <= discrepância <= +tolerancia
    - "Para ressarcimento": discrepância > +tolerancia
    - "Abaixo LPU": discrepância < -tolerancia

    Args:
        df: DataFrame com dados cruzados

    Returns:
        DataFrame com colunas de discrepância calculadas
    """
    df = df.copy()

    # Obtém tolerância das configurações
    tolerance = settings.validador_lpu.tolerancia_percentual
    logger.debug(f"Calculando discrepâncias com tolerância de {tolerance}%")

    # Calcula valor total orçado (revalida)
    df["valor_total_orcado"] = df["qtde"] * df["unitario_orcado"]

    # Verifica consistência de total_orcado se existir
    if "total_orcado" in df.columns:
        inconsistencies = (abs(df["total_orcado"] - df["valor_total_orcado"]) > 0.01).sum()
        if inconsistencies > 0:
            logger.warning(
                f"⚠️  Atenção: {inconsistencies} inconsistências em total_orcado detectadas"
            )

    # Calcula diferenças
    df["dif_unitario"] = df["unitario_orcado"] - df["unitario_lpu"]
    df["dif_total"] = df["dif_unitario"] * df["qtde"]

    # Calcula porcentagem (tratando divisão por zero)
    df["perc_dif"] = 0.0
    valid_mask = df["unitario_lpu"] != 0
    df.loc[valid_mask, "perc_dif"] = (
        df.loc[valid_mask, "dif_unitario"] / df.loc[valid_mask, "unitario_lpu"]
    ) * 100

    # Classificação COM TOLERÂNCIA (configurável)
    def classify_discrepancy(row):
        perc = row["perc_dif"]
        if -tolerance <= perc <= tolerance:
            return "OK"
        elif perc > tolerance:
            return "Para ressarcimento"
        else:
            return "Abaixo LPU"

    df["status_conciliacao"] = df.apply(classify_discrepancy, axis=1)

    logger.debug(f"Discrepâncias calculadas para {len(df)} itens")

    # Arredonda valores para 2 casas decimais
    columns_to_round = [
        "unitario_orcado",
        "unitario_lpu",
        "valor_total_orcado",
        "dif_unitario",
        "dif_total",
        "perc_dif",
    ]
    for col in columns_to_round:
        if col in df.columns:
            df[col] = df[col].round(2)

    return df


def save_results(df: pd.DataFrame, output_dir: Union[str, Path], base_name: str = None) -> None:
    """
    Salva os resultados nos formatos Excel e CSV.

    Args:
        df: DataFrame com os resultados da validação
        output_dir: Diretório de saída
        base_name: Nome base para os arquivos (padrão configurado nas configurações)
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Usa nome base das configurações se não fornecido
    if base_name is None:
        base_name = settings.validador_lpu.arquivo_excel_basico.replace(".xlsx", "")

    logger.debug(f"Salvando resultados em {output_dir}")

    # Define ordem das colunas
    ordered_columns = [
        "cod_upe",
        "cod_item",
        "nome",
        "categoria",
        "unidade",
        "qtde",
        "unitario_orcado",
        "unitario_lpu",
        "dif_unitario",
        "perc_dif",
        "valor_total_orcado",
        "dif_total",
        "status_conciliacao",
        "fonte",
        "descricao",
        "data_referencia",
        "composicao",
        "fornecedor",
        "observacoes_orc",
        "observacoes_lpu",
    ]

    # Seleciona apenas colunas existentes
    existing_columns = [col for col in ordered_columns if col in df.columns]
    output_df = df[existing_columns].copy()

    # Salva como Excel com formatação
    excel_filename = settings.validador_lpu.arquivo_excel_basico
    excel_path = output_dir / excel_filename

    logger.debug(f"Gerando arquivo Excel: {excel_filename}")

    with pd.ExcelWriter(excel_path, engine="openpyxl") as writer:
        # Planilha principal com validação completa
        output_df.to_excel(writer, sheet_name="Complete Validation", index=False)

        # Planilha de resumo por status
        status_summary = (
            df.groupby("status_conciliacao")
            .agg({"cod_item": "count", "dif_total": "sum", "valor_total_orcado": "sum"})
            .reset_index()
        )
        status_summary.columns = [
            "Status",
            "Item Count",
            "Total Difference (R$)",
            "Total Budgeted Value (R$)",
        ]
        status_summary.to_excel(writer, sheet_name="Status Summary", index=False)

        # Planilha de resumo por categoria
        if "categoria" in df.columns:
            category_summary = (
                df.groupby(["categoria", "status_conciliacao"])
                .agg({"cod_item": "count", "dif_total": "sum"})
                .reset_index()
            )
            category_summary.columns = ["Category", "Status", "Item Count", "Total Difference (R$)"]
            category_summary.to_excel(writer, sheet_name="Category Summary", index=False)

        # Planilha de resumo por UPE
        if "cod_upe" in df.columns:
            upe_summary = (
                df.groupby(["cod_upe", "status_conciliacao"])
                .agg({"cod_item": "count", "dif_total": "sum"})
                .reset_index()
            )
            upe_summary.columns = ["UPE Code", "Status", "Item Count", "Total Difference (R$)"]
            upe_summary.to_excel(writer, sheet_name="UPE Summary", index=False)

    logger.success(f"✅ Excel salvo em: {excel_path}")

    # Salva como CSV
    csv_filename = settings.validador_lpu.arquivo_csv
    csv_path = output_dir / csv_filename
    output_df.to_csv(csv_path, index=False, sep=";", encoding="utf-8-sig")
    logger.success(f"✅ CSV salvo em: {csv_path}")


def generate_html_report(
    df: pd.DataFrame, output_dir: Union[str, Path], base_name: str = None
) -> None:
    """
    Gera um relatório HTML para validação LPU.

    Args:
        df (pd.DataFrame): DataFrame contendo os resultados da validação.
        output_dir (Union[str, Path]): Diretório para salvar o relatório HTML.
        base_name (str): Nome base para o arquivo HTML. Padrão é None.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Usa nome base das configurações se não fornecido
    if base_name is None:
        base_name = settings.validador_lpu.arquivo_html.replace(".html", "")

    html_path = output_dir / f"{base_name}.html"

    logger.debug(f"Gerando relatório HTML: {base_name}.html")

    # Estatísticas gerais
    total_items = len(df)
    items_ok = (df["status_conciliacao"] == "OK").sum()
    items_refund = (df["status_conciliacao"] == "Para ressarcimento").sum()
    items_below = (df["status_conciliacao"] == "Abaixo LPU").sum()

    total_value = df["valor_total_orcado"].sum()
    total_divergence = df["dif_total"].sum()
    refund_divergence = df[df["status_conciliacao"] == "Para ressarcimento"]["dif_total"].sum()

    # Top 10 divergências
    df["perc_dif_abs"] = abs(df["perc_dif"])
    top_10_abs = df.nlargest(10, "dif_total")[
        [
            "cod_item",
            "nome",
            "unitario_orcado",
            "unitario_lpu",
            "dif_unitario",
            "dif_total",
            "status_conciliacao",
        ]
    ]
    top_10_perc = df.nlargest(10, "perc_dif_abs")[
        [
            "cod_item",
            "nome",
            "unitario_orcado",
            "unitario_lpu",
            "perc_dif",
            "dif_total",
            "status_conciliacao",
        ]
    ]

    # Resumo por status
    status_summary = (
        df.groupby("status_conciliacao")
        .agg({"cod_item": "count", "dif_total": "sum", "valor_total_orcado": "sum"})
        .reset_index()
    )
    status_summary.columns = [
        "Status",
        "Item Count",
        "Total Difference (R$)",
        "Total Budgeted Value (R$)",
    ]

    # Resumo por categoria
    category_summary = None
    if "categoria" in df.columns:
        category_summary = (
            df.groupby(["categoria", "status_conciliacao"])
            .agg({"cod_item": "count", "dif_total": "sum"})
            .reset_index()
        )
        category_summary.columns = ["Category", "Status", "Item Count", "Total Difference (R$)"]

    # Resumo por UPE
    upe_summary = None
    if "cod_upe" in df.columns:
        upe_summary = (
            df.groupby(["cod_upe", "status_conciliacao"])
            .agg({"cod_item": "count", "dif_total": "sum"})
            .reset_index()
        )
        upe_summary.columns = ["UPE Code", "Status", "Item Count", "Total Difference (R$)"]

    # Cria HTML
    html_content = f"""
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Relatório de Validação LPU</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 20px;
            color: #333;
        }}
        
        .container {{
            max-width: 1400px;
            margin: 0 auto;
            background: white;
            border-radius: 15px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.2);
            overflow: hidden;
        }}
        
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 40px;
            text-align: center;
        }}
        
        .header h1 {{
            font-size: 2.5em;
            margin-bottom: 10px;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.2);
        }}
        
        .header p {{
            font-size: 1.1em;
            opacity: 0.9;
        }}
        
        .content {{
            padding: 40px;
        }}
        
        .section {{
            margin-bottom: 40px;
            background: #f8f9fa;
            padding: 30px;
            border-radius: 10px;
            border-left: 5px solid #667eea;
        }}
        
        .section h2 {{
            color: #667eea;
            margin-bottom: 20px;
            font-size: 1.8em;
            display: flex;
            align-items: center;
        }}
        
        .section h2::before {{
            content: '📊';
            margin-right: 10px;
        }}
        
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-top: 20px;
        }}
        
        .stat-card {{
            background: white;
            padding: 25px;
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            text-align: center;
            transition: transform 0.3s ease;
        }}
        
        .stat-card:hover {{
            transform: translateY(-5px);
            box-shadow: 0 6px 12px rgba(0,0,0,0.15);
        }}
        
        .stat-label {{
            color: #666;
            font-size: 0.9em;
            margin-bottom: 10px;
            text-transform: uppercase;
            letter-spacing: 1px;
        }}
        
        .stat-value {{
            font-size: 2em;
            font-weight: bold;
            color: #667eea;
        }}
        
        .stat-ok {{ color: #28a745; }}
        .stat-warning {{ color: #ffc107; }}
        .stat-danger {{ color: #dc3545; }}
        
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
            background: white;
            border-radius: 10px;
            overflow: hidden;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }}
        
        thead {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
        }}
        
        th {{
            padding: 15px;
            text-align: left;
            font-weight: 600;
            text-transform: uppercase;
            font-size: 0.85em;
            letter-spacing: 0.5px;
        }}
        
        td {{
            padding: 12px 15px;
            border-bottom: 1px solid #eee;
        }}
        
        tr:hover {{
            background: #f8f9fa;
        }}
        
        .status-ok {{
            background: #d4edda;
            color: #155724;
            padding: 5px 10px;
            border-radius: 5px;
            font-weight: bold;
        }}
        
        .status-refund {{
            background: #fff3cd;
            color: #856404;
            padding: 5px 10px;
            border-radius: 5px;
            font-weight: bold;
        }}
        
        .status-below {{
            background: #f8d7da;
            color: #721c24;
            padding: 5px 10px;
            border-radius: 5px;
            font-weight: bold;
        }}
        
        .value-positive {{
            color: #dc3545;
            font-weight: bold;
        }}
        
        .value-negative {{
            color: #28a745;
            font-weight: bold;
        }}
        
        .footer {{
            background: #f8f9fa;
            padding: 20px;
            text-align: center;
            color: #666;
            border-top: 1px solid #dee2e6;
        }}
        
        @media print {{
            body {{
                background: white;
                padding: 0;
            }}
            
            .container {{
                box-shadow: none;
            }}
            
            .stat-card:hover {{
                transform: none;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📋 Relatório de Validação LPU</h1>
            <p>Conciliação de Orçamento vs Base de Preços de Referência</p>
            <p style="font-size: 0.9em; margin-top: 10px;">Gerado em: {pd.Timestamp.now().strftime('%d/%m/%Y %H:%M:%S')}</p>
        </div>
        
        <div class="content">
            <!-- ESTATÍSTICAS GERAIS -->
            <div class="section">
                <h2>Estatísticas Gerais</h2>
                <div class="stats-grid">
                    <div class="stat-card">
                        <div class="stat-label">Total de Itens</div>
                        <div class="stat-value">{total_items}</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-label">Itens OK</div>
                        <div class="stat-value stat-ok">{items_ok} ({items_ok/total_items*100:.1f}%)</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-label">Para Ressarcimento</div>
                        <div class="stat-value stat-warning">{items_refund} ({items_refund/total_items*100:.1f}%)</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-label">Abaixo LPU</div>
                        <div class="stat-value stat-danger">{items_below} ({items_below/total_items*100:.1f}%)</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-label">Valor Total Orçado</div>
                        <div class="stat-value">R$ {total_value:,.2f}</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-label">Divergência Total</div>
                        <div class="stat-value stat-warning">R$ {total_divergence:,.2f}</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-label">Potencial Ressarcimento</div>
                        <div class="stat-value stat-danger">R$ {refund_divergence:,.2f}</div>
                    </div>
                </div>
            </div>
            
            <!-- RESUMO POR STATUS -->
            <div class="section">
                <h2>Resumo por Status</h2>
                {status_summary.to_html(index=False, classes='dataframe', escape=False, float_format=lambda x: f'R$ {x:,.2f}' if pd.notna(x) else '')}
            </div>
            
            <!-- TOP 10 DIVERGÊNCIAS ABSOLUTAS -->
            <div class="section">
                <h2>🔴 Top 10 Maiores Divergências Absolutas</h2>
                {top_10_abs.to_html(index=False, classes='dataframe', escape=False, float_format=lambda x: f'R$ {x:,.2f}' if pd.notna(x) else '')}
            </div>
            
            <!-- TOP 10 DIVERGÊNCIAS PERCENTUAIS -->
            <div class="section">
                <h2>📈 Top 10 Maiores Divergências Percentuais</h2>
                {top_10_perc.to_html(index=False, classes='dataframe', escape=False, float_format=lambda x: f'{x:.2f}%' if 'perc' in str(x) else (f'R$ {x:,.2f}' if pd.notna(x) else ''))}
            </div>
            {"<!-- RESUMO POR CATEGORIA -->" if category_summary is not None else ""}
            {f'''<div class="section">
                <h2>Resumo por Categoria</h2>
                {category_summary.to_html(index=False, classes='dataframe', escape=False, float_format=lambda x: 'R$ {x:,.2f}' if pd.notna(x) else '')}
            </div>''' if category_summary is not None else ""}
            {"<!-- RESUMO POR UPE -->" if upe_summary is not None else ""}
            {f'''<div class="section">
                <h2>Resumo por UPE</h2>
                {upe_summary.to_html(index=False, classes='dataframe', escape=False, float_format=lambda x: 'R$ {x:,.2f}' if pd.notna(x) else '')}
            </div>''' if upe_summary is not None else ""}
        </div>
        
        <div class="footer">
            <p>Relatório gerado automaticamente pelo sistema Validador LPU</p>
            <p style="margin-top: 5px; font-size: 0.9em;">Construct Cost AI - Verificador Inteligente de Obras</p>
        </div>
    </div>
</body>
</html>
"""

    # Salvar HTML
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html_content)

    logger.success(f"✅ Relatório HTML salvo em: {html_path}")


def generate_complete_excel_report(
    df: pd.DataFrame, output_dir: Union[str, Path], base_name: str = None
) -> None:
    """
    Gera um relatório Excel completo com todas as análises em planilhas separadas.

    Args:
        df: DataFrame com os resultados da validação
        output_dir: Diretório de saída
        base_name: Nome base para o arquivo Excel (padrão configurado nas configurações)
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Usa nome base das configurações se não fornecido
    if base_name is None:
        base_name = settings.validador_lpu.arquivo_excel_completo.replace(".xlsx", "")

    excel_path = output_dir / f"{base_name}.xlsx"

    logger.debug(f"Gerando relatório Excel completo: {base_name}.xlsx")

    # Prepara dados
    df["perc_dif_abs"] = abs(df["perc_dif"])

    # Obtém configuração top_n das configurações
    top_n = settings.validador_lpu.top_n_divergencias
    top_n_extended = settings.validador_lpu.top_n_divergencias_extended

    # Top divergências
    top_10_abs = df.nlargest(top_n, "dif_total")[
        [
            "cod_item",
            "nome",
            "unitario_orcado",
            "unitario_lpu",
            "dif_unitario",
            "dif_total",
            "status_conciliacao",
        ]
    ]
    top_20_abs = df.nlargest(top_n_extended, "dif_total")[
        [
            "cod_item",
            "nome",
            "unitario_orcado",
            "unitario_lpu",
            "dif_unitario",
            "dif_total",
            "status_conciliacao",
        ]
    ]

    top_10_perc = df.nlargest(top_n, "perc_dif_abs")[
        [
            "cod_item",
            "nome",
            "unitario_orcado",
            "unitario_lpu",
            "perc_dif",
            "dif_total",
            "status_conciliacao",
        ]
    ]
    top_20_perc = df.nlargest(top_n_extended, "perc_dif_abs")[
        [
            "cod_item",
            "nome",
            "unitario_orcado",
            "unitario_lpu",
            "perc_dif",
            "dif_total",
            "status_conciliacao",
        ]
    ]

    # Estatísticas
    total_items = len(df)
    items_ok = (df["status_conciliacao"] == "OK").sum()
    items_refund = (df["status_conciliacao"] == "Para ressarcimento").sum()
    items_below = (df["status_conciliacao"] == "Abaixo LPU").sum()

    total_value = df["valor_total_orcado"].sum()
    total_divergence = df["dif_total"].sum()
    refund_divergence = df[df["status_conciliacao"] == "Para ressarcimento"]["dif_total"].sum()

    stats_data = {
        "Métrica": [
            "Total de Itens",
            "Itens OK",
            "Itens Para Ressarcimento",
            "Itens Abaixo LPU",
            "% OK",
            "% Para Ressarcimento",
            "% Abaixo LPU",
            "Valor Total Orçado (R$)",
            "Divergência Total (R$)",
            "Ressarcimento Potencial (R$)",
        ],
        "Valor": [
            total_items,
            items_ok,
            items_refund,
            items_below,
            f"{items_ok/total_items*100:.2f}%",
            f"{items_refund/total_items*100:.2f}%",
            f"{items_below/total_items*100:.2f}%",
            f"R$ {total_value:,.2f}",
            f"R$ {total_divergence:,.2f}",
            f"R$ {refund_divergence:,.2f}",
        ],
    }
    df_stats = pd.DataFrame(stats_data)

    # Resumo por status
    status_summary = (
        df.groupby("status_conciliacao")
        .agg({"cod_item": "count", "dif_total": "sum", "valor_total_orcado": "sum"})
        .reset_index()
    )
    status_summary.columns = [
        "Status",
        "Item Count",
        "Total Difference (R$)",
        "Total Budgeted Value (R$)",
    ]

    # Itens para ressarcimento
    items_for_refund = df[df["status_conciliacao"] == "Para ressarcimento"][
        [
            "cod_item",
            "nome",
            "categoria",
            "unitario_orcado",
            "unitario_lpu",
            "dif_unitario",
            "perc_dif",
            "qtde",
            "dif_total",
            "fonte",
        ]
    ].sort_values("dif_total", ascending=False)

    # Itens abaixo da LPU
    items_below_lpu = df[df["status_conciliacao"] == "Abaixo LPU"][
        [
            "cod_item",
            "nome",
            "categoria",
            "unitario_orcado",
            "unitario_lpu",
            "dif_unitario",
            "perc_dif",
            "qtde",
            "dif_total",
            "fonte",
        ]
    ].sort_values("dif_total")

    # Salva como Excel
    with pd.ExcelWriter(excel_path, engine="openpyxl") as writer:
        # Planilha 1: Estatísticas Gerais
        df_stats.to_excel(writer, sheet_name="Statistics", index=False)

        # Planilha 2: Resumo por Status
        status_summary.to_excel(writer, sheet_name="Status Summary", index=False)

        # Planilha 3: Top 10 Divergências (Valor)
        top_10_abs.to_excel(writer, sheet_name="Top 10 Absolute Divergence", index=False)

        # Planilha 4: Top 20 Divergências (Valor)
        top_20_abs.to_excel(writer, sheet_name="Top 20 Absolute Divergence", index=False)

        # Planilha 5: Top 10 Divergências (%)
        top_10_perc.to_excel(writer, sheet_name="Top 10 Percentual Divergence", index=False)

        # Planilha 6: Top 20 Divergências (%)
        top_20_perc.to_excel(writer, sheet_name="Top 20 Percentual Divergence", index=False)

        # Planilha 7: Itens para Ressarcimento
        items_for_refund.to_excel(writer, sheet_name="Items For Refund", index=False)

        # Planilha 8: Itens Abaixo LPU
        items_below_lpu.to_excel(writer, sheet_name="Items Below LPU", index=False)

        # Planilha 9: Resumo por Categoria (se existir)
        if "categoria" in df.columns:
            category_summary = (
                df.groupby(["categoria", "status_conciliacao"])
                .agg({"cod_item": "count", "dif_total": "sum"})
                .reset_index()
            )
            category_summary.columns = ["Category", "Status", "Item Count", "Total Difference (R$)"]
            category_summary.to_excel(writer, sheet_name="Category Summary", index=False)

            # Divergência total por categoria
            divergence_by_category = (
                df.groupby("categoria")
                .agg({"cod_item": "count", "dif_total": "sum", "valor_total_orcado": "sum"})
                .reset_index()
                .sort_values("dif_total", ascending=False)
            )
            divergence_by_category.columns = [
                "Category",
                "Item Count",
                "Total Difference (R$)",
                "Total Value (R$)",
            ]
            divergence_by_category.to_excel(
                writer, sheet_name="Divergence by Category", index=False
            )

        # Planilha 10: Resumo por UPE (se existir)
        if "cod_upe" in df.columns:
            upe_summary = (
                df.groupby(["cod_upe", "status_conciliacao"])
                .agg({"cod_item": "count", "dif_total": "sum"})
                .reset_index()
                .sort_values("cod_upe")
            )
            upe_summary.columns = ["UPE Code", "Status", "Item Count", "Total Difference (R$)"]
            upe_summary.to_excel(writer, sheet_name="UPE Summary", index=False)

            # Divergência total por UPE
            divergence_by_upe = (
                df.groupby("cod_upe")
                .agg({"cod_item": "count", "dif_total": "sum", "valor_total_orcado": "sum"})
                .reset_index()
                .sort_values("dif_total", ascending=False)
            )
            divergence_by_upe.columns = [
                "UPE Code",
                "Item Count",
                "Total Difference (R$)",
                "Total Value (R$)",
            ]
            divergence_by_upe.to_excel(writer, sheet_name="Divergence by UPE", index=False)

        # Planilha 11: Dados Completos
        df.to_excel(writer, sheet_name="Complete Data", index=False)

    logger.success(f"✅ Relatório Excel completo salvo em: {excel_path}")


def calculate_total_item(
    df: pd.DataFrame, column_total_value: str, column_quantity: str, column_unit_price: str
) -> pd.DataFrame:
    """
    Calcula o valor total orçado em um DataFrame.

    Args:
        df (pd.DataFrame): DataFrame contendo os dados.
        column_total_value (str): Nome da coluna de valor total orçado.
        column_quantity (str): Nome da coluna de quantidade.
        column_unit_price (str): Nome da coluna de preço unitário.

    Returns:
        pd.DataFrame: DataFrame atualizado com a coluna de valor total orçado calculada ou convertida.
    """
    if column_total_value not in df.columns:
        df[column_total_value] = df[column_quantity] * df[column_unit_price]
    else:
        df[column_total_value] = pd.to_numeric(df[column_total_value], errors="coerce")

    return df


def get_default_settings(key):
    """
    Retorna os valores padrão das configurações do validador LPU.

    Returns:
        Dicionário com configurações padrão
    """
    return {
        "default_budget_path": settings.validador_lpu.caminho_padrao_orcamento,
        "default_lpu_path": settings.validador_lpu.caminho_padrao_lpu,
        "output_dir": settings.validador_lpu.output_dir,
        "tolerance_percentual": settings.validador_lpu.tolerancia_percentual,
        "basic_excel_file": settings.validador_lpu.arquivo_excel_basico,
        "complete_excel_file": settings.validador_lpu.arquivo_excel_completo,
        "csv_file": settings.validador_lpu.arquivo_csv,
        "html_file": settings.validador_lpu.arquivo_html,
        "top_n_divergences": settings.validador_lpu.top_n_divergencias,
        "top_n_divergences_extended": settings.validador_lpu.top_n_divergencias_extended,
    }


def validate_lpu(
    file_path_budget: Union[str, Path] = None,
    file_path_lpu: Union[str, Path] = None,
    output_dir: Union[str, Path] = None,
    output_file: str = "02_BASE_RESULTADO_VALIDADOR_LPU.xlsx",
    verbose: bool = True,
) -> pd.DataFrame:
    """
    Função orquestradora para validação LPU.

    Realiza todo o fluxo de validação:
    1. Carrega orçamento e LPU
    2. Cruza os dados (INNER JOIN em cod_item + unidade)
    3. Calcula discrepâncias com tolerância configurável
    4. Classifica itens (OK, Para ressarcimento, Abaixo LPU)
    5. Salva resultados em formatos Excel, CSV e HTML

    Args:
        file_path_budget: Caminho para o arquivo de orçamento (padrão nas configurações)
        file_path_lpu: Caminho para o arquivo da LPU (padrão nas configurações)
        output_dir: Diretório para salvar resultados (padrão nas configurações)
        output_file_name: Nome base para os arquivos de saída (sem extensão)
        verbose: Se True, exibe estatísticas no console

    Returns:
        DataFrame com os resultados completos da validação

    Raises:
        ValidatorLPUError: Em caso de erro na validação
    """

    if verbose:
        print("-" * 50)
        logger.info("VALIDADOR LPU - Conciliação Orçamento vs Base de Preços")
        logger.info(
            f"Tolerância configurada: {settings.get('module_validator_lpu.tol_percentile')}%"
        )
        print("-" * 50)

    # 1. Carrega dados
    if verbose:
        logger.info("📂 Carregando arquivos...")

    try:
        logger.info(f"Carregando orçamento de: {file_path_budget}")
        df_budget = load_budget(file_path_budget)
        if verbose:
            logger.info(f"   ✅ Orçamento carregado: {len(df_budget)} itens")
    except Exception as e:
        logger.error(f"Erro ao carregar orçamento: {e}")
        raise ValidatorLPUError(f"Erro ao carregar orçamento: {e}")

    try:
        logger.debug(f"Carregando LPU de: {file_path_lpu}")
        df_lpu = load_lpu(file_path_lpu)
        if verbose:
            logger.info(f"   ✅ LPU carregada: {len(df_lpu)} itens")
    except Exception as e:
        logger.error(f"Erro ao carregar LPU: {e}")
        raise ValidatorLPUError(f"Erro ao carregar LPU: {e}")

    # 2. Cruza dados
    if verbose:
        logger.info("🔗 Cruzando orçamento com LPU...")

    try:
        # Realiza o merge entre orçamento e lpu
        df_crossed = cross_budget_lpu(df_budget, df_lpu)
        if verbose:
            logger.info(f"   ✅ Itens cruzados: {len(df_crossed)}")
    except Exception as e:
        logger.error(f"Erro ao cruzar dados: {e}")
        raise ValidatorLPUError(f"Erro ao cruzar dados: {e}")

    if verbose:
        logger.info("")

    # 3. Calcula discrepâncias
    if verbose:
        logger.info(
            f"🧮 Calculando discrepâncias (tolerância {settings.validador_lpu.tolerancia_percentual}%)..."
        )

    try:
        df_result = calculate_discrepancies(df_crossed)
    except Exception as e:
        logger.error(f"Erro ao calcular discrepâncias: {e}")
        raise ValidatorLPUError(f"Erro ao calcular discrepâncias: {e}")

    # Estatísticas
    if verbose:
        logger.info("")
        logger.info("📊 ESTATÍSTICAS DA VALIDAÇÃO")
        logger.info("-" * 80)

        total_items = len(df_result)
        items_ok = (df_result["status_conciliacao"] == "OK").sum()
        items_refund = (df_result["status_conciliacao"] == "Para ressarcimento").sum()
        items_below = (df_result["status_conciliacao"] == "Abaixo LPU").sum()

        logger.info(f"   Total de itens validados: {total_items}")
        logger.info(f"   ✅ OK: {items_ok} ({items_ok/total_items*100:.1f}%)")
        logger.info(
            f"   ⚠️  Para ressarcimento: {items_refund} ({items_refund/total_items*100:.1f}%)"
        )
        logger.info(f"   📉 Abaixo LPU: {items_below} ({items_below/total_items*100:.1f}%)")
        logger.info("")

        total_budgeted_value = df_result["valor_total_orcado"].sum()
        total_divergence = df_result["dif_total"].sum()
        refund_divergence = df_result[df_result["status_conciliacao"] == "Para ressarcimento"][
            "dif_total"
        ].sum()

        logger.info(f"   💰 Valor total orçado: R$ {total_budgeted_value:,.2f}")
        logger.info(f"   💵 Divergência total: R$ {total_divergence:,.2f}")
        logger.info(f"   💸 Ressarcimento potencial: R$ {refund_divergence:,.2f}")
        logger.info("")

    # Registra estatísticas no logger
    logger.debug("📊 ESTATÍSTICAS DA VALIDAÇÃO")
    total_items = len(df_result)
    items_ok = (df_result["status_conciliacao"] == "OK").sum()
    items_refund = (df_result["status_conciliacao"] == "Para ressarcimento").sum()
    items_below = (df_result["status_conciliacao"] == "Abaixo LPU").sum()

    logger.debug(f"Total de itens validados: {total_items}")
    logger.debug(f"✅ OK: {items_ok} ({items_ok/total_items*100:.1f}%)")
    logger.debug(f"⚠️  Para ressarcimento: {items_refund} ({items_refund/total_items*100:.1f}%)")
    logger.debug(f"📉 Abaixo LPU: {items_below} ({items_below/total_items*100:.1f}%)")

    total_budgeted_value = df_result["valor_total_orcado"].sum()
    total_divergence = df_result["dif_total"].sum()
    refund_divergence = df_result[df_result["status_conciliacao"] == "Para ressarcimento"][
        "dif_total"
    ].sum()

    logger.debug(f"💰 Valor total orçado: R$ {total_budgeted_value:,.2f}")
    logger.debug(f"💵 Divergência total: R$ {total_divergence:,.2f}")
    logger.debug(f"💸 Ressarcimento potencial: R$ {refund_divergence:,.2f}")

    # 4. Salva resultados
    if verbose:
        logger.info("")
        logger.info("💾 Salvando resultados...")

    try:
        # Salva formato básico (4 planilhas)
        save_results(df_result, output_dir)

        # Salva relatório completo em Excel (11+ planilhas)
        generate_complete_excel_report(df_result, output_dir)

        # Salva relatório HTML
        generate_html_report(df_result, output_dir)

    except Exception as e:
        logger.error(f"Erro ao salvar resultados: {e}")
        raise ValidatorLPUError(f"Erro ao salvar resultados: {e}")

    if verbose:
        logger.info("")
        logger.info("=" * 80)
        logger.success("✅ VALIDAÇÃO CONCLUÍDA COM SUCESSO!")
        logger.info("=" * 80)

    logger.debug("=" * 80)
    logger.success("✅ VALIDAÇÃO CONCLUÍDA COM SUCESSO!")
    logger.debug("=" * 80)

    return df_result


def orchestrate_validate_lpu(
    file_path_budget: Union[str, Path] = None,
    file_path_lpu: Union[str, Path] = None,
    output_dir: Union[str, Path] = None,
    output_file: str = None,
    verbose: bool = True,
) -> int:
    """
    Função principal para execução direta do módulo ou chamada externa.

    Args:
        file_path_budget: Caminho para o arquivo de orçamento (padrão nas configurações se None).
        file_path_lpu: Caminho para o arquivo da LPU (padrão nas configurações se None).
        output_dir: Diretório para salvar resultados (padrão nas configurações se None).
        output_file: Nome base para os arquivos de saída (padrão nas configurações se None).
        verbose: Se True, exibe estatísticas no console.

    Returns:
        int: Código de status (0 para sucesso, 1 para erro).
    """
    # Configura caminhos padrão se não fornecidos
    base_dir = Path(__file__).parents[5]
    path_file_budget = Path(
        base_dir,
        file_path_budget or settings.get("module_validator_lpu.budget_data.file_path_budget"),
    )
    path_file_lpu = Path(
        base_dir, file_path_lpu or settings.get("module_validator_lpu.lpu_data.file_path_lpu")
    )
    output_dir = Path(
        base_dir, output_dir or settings.get("module_validator_lpu.output_settings.output_dir")
    )
    output_file = output_file or settings.get(
        "module_validator_lpu.output_settings.file_path_output"
    )

    logger.debug(f"Orçamento: {path_file_budget}")
    logger.debug(f"LPU: {path_file_lpu}")
    logger.debug(f"Saída: {output_dir}")

    try:
        df_result = validate_lpu(
            file_path_budget=path_file_budget,
            file_path_lpu=path_file_lpu,
            output_dir=output_dir,
            output_file=output_file,
            verbose=verbose,
        )

        # Exibe primeiras linhas
        if verbose:
            logger.info("\n📋 VISUALIZAÇÃO DOS RESULTADOS:")
            logger.info("-" * 80)
            preview_columns = [
                "cod_item",
                "nome",
                "unidade",
                "qtde",
                "unitario_orcado",
                "unitario_lpu",
                "dif_unitario",
                "perc_dif",
                "status_conciliacao",
            ]
            preview_columns = [col for col in preview_columns if col in df_result.columns]
            logger.info(f"\n{df_result[preview_columns].head(10).to_string(index=False)}")

        logger.success("Execução principal concluída com sucesso!")
        return 0

    except ValidatorLPUError as e:
        logger.error(f"ERRO: {e}")
        return 1
    except Exception as e:
        logger.error(f"ERRO INESPERADO: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(orchestrate_validate_lpu())

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
from utils.data.data_functions import (
    read_data,
    export_data,
    cast_columns,
    transform_case,
    merge_data_with_columns,
)
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
        # Ler os dados de Orçamento e realizar pré processing
        df = transform_case(
            read_data(
                file_path=file_path,
                sheet_name=settings.get("module_validator_lpu.budget_data.sheet_name", "Tables"),
            ),
            columns_to_upper=True,
            cells_to_upper=True,
            cells_to_remove_spaces=settings.get("module_validator_lpu.budget_data.cells_to_remove_spaces", []),
            cells_to_remove_accents=settings.get("module_validator_lpu.budget_data.cells_to_remove_accents", []),
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


def load_metadata(file_path: Union[str, Path] = None) -> pd.DataFrame:
    """
    Carrega o arquivo de metadados.

    Args:
        file_path: Caminho para o arquivo de metadados (Excel ou CSV). Se não for fornecido, usa o caminho padrão.

    Returns:
        DataFrame com a base de metadados carregada.

    Raises:
        FileNotFoundError: Se o arquivo não for encontrado.
        MissingColumnsError: Se colunas obrigatórias estiverem ausentes.
        ValueError: Se houver erro ao converter os tipos de colunas.
    """
    
    logger.info("Iniciando o carregamento da base de metadados")
    
    # Obtém o caminho e a aba do arquivo a partir das configurações
    file_path = file_path or settings.get("module_validator_lpu.budget_metadados.file_path")
    sheet_name = settings.get("module_validator_lpu.budget_metadados.sheet_name", "Metadata")

    # Colunas obrigatórias e seus tipos
    required_columns = settings.get(
        "module_validator_lpu.budget_metadados.required_columns_with_types", {}
    )

    file_path = Path(file_path)

    # Verifica se o arquivo existe
    if not file_path.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {file_path}")

    try:
        # Lê os dados e realiza o pré-processamento
        df = transform_case(
            read_data(file_path=file_path, sheet_name=sheet_name),
            columns_to_upper=True,
            cells_to_upper=True,
            cells_to_remove_spaces=settings.get("module_validator_lpu.budget_metadados.cells_to_remove_spaces", []),
            cells_to_remove_accents=settings.get("module_validator_lpu.budget_metadados.cells_to_remove_accents", []),
        )

        # Converte as colunas para os tipos corretos
        df = cast_columns(df, required_columns)
    except ValueError as e:
        logger.error(f"Erro ao converter tipos de colunas na base de metadados: {e}")
        raise

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
    expected_wide_cols = generate_region_group_combinations(
        regions, groups, combine_regions=False
    ) + generate_region_group_combinations(regions, groups, combine_regions=True)

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
    
    logger.info("Iniciando o carregamento da base LPU")
    
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
                sheet_name=settings.get("module_validator_lpu.lpu_data.sheet_name", "LPU"),
            ),
            columns_to_upper=True,
            cells_to_upper=True,
            cells_to_remove_spaces=settings.get("module_validator_lpu.lpu_data.cells_to_remove_spaces", []),
            cells_to_remove_accents=settings.get("module_validator_lpu.lpu_data.cells_to_remove_accents", []),
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


def load_agencies(file_path: Union[str, Path]) -> pd.DataFrame:
    """
    Carrega o arquivo de agências.

    Args:
        file_path: Caminho para o arquivo de agências (Excel ou CSV).

    Returns:
        DataFrame com a base de agências carregada.

    Raises:
        FileNotFoundError: Se o arquivo não for encontrado.
        MissingColumnsError: Se colunas obrigatórias estiverem ausentes.
    """
    
    logger.info("Iniciando o carregamento da base de agências")
    
    file_path = Path(file_path)

    if not file_path.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {file_path}")

    # Colunas obrigatórias
    required_columns = settings.get(
        "module_validator_lpu.agencies_data.required_columns_with_types", []
    )

    try:
        # Ler os dados de Agências e realizar pré processing
        df = transform_case(
            read_data(
                file_path=file_path,
                sheet_name=settings.get("module_validator_lpu.agencies_data.sheet_name", "Sheet1"),
            ),
            columns_to_upper=True,
            cells_to_upper=True,
            cells_to_remove_spaces=settings.get("module_validator_lpu.agencies_data.cells_to_remove_spaces", []),
            cells_to_remove_accents=settings.get("module_validator_lpu.agencies_data.cells_to_remove_accents", []),
        )
    except Exception as e:
        logger.error(f"Erro ao carregar o arquivo de agências: {e}")
        raise

    # Valida colunas obrigatórias
    missing_columns = set(required_columns.keys()) - set(df.columns)
    if missing_columns:
        raise MissingColumnsError(
            f"Colunas obrigatórias ausentes na base de agências: {missing_columns}"
        )

    # Garante tipos corretos usando cast_columns
    try:
        df = cast_columns(df, required_columns)
    except ValueError as e:
        logger.error(f"Erro ao converter tipos de colunas na base de agências: {e}")
        raise

    return df


def load_constructors(file_path: Union[str, Path]) -> pd.DataFrame:
    """
    Carrega o arquivo de construtoras.

    Args:
        file_path: Caminho para o arquivo de construtoras (Excel ou CSV).

    Returns:
        DataFrame com a base de construtoras carregada.

    Raises:
        FileNotFoundError: Se o arquivo não for encontrado.
        MissingColumnsError: Se colunas obrigatórias estiverem ausentes.
    """
    
    logger.info("Iniciando o carregamento da base de construtoras")
    
    file_path = Path(file_path)

    if not file_path.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {file_path}")

    # Colunas obrigatórias
    required_columns = settings.get(
        "module_validator_lpu.constructors_data.required_columns_with_types", []
    )

    try:
        # Ler os dados de Fornecedores/Construtoras e realizar pré processing
        df = transform_case(
            read_data(
                file_path=file_path,
                sheet_name=settings.get("module_validator_lpu.constructors_data.sheet_name", "Sheet1"),
            ),
            columns_to_upper=True,
            cells_to_upper=True,
            cells_to_remove_spaces=settings.get("module_validator_lpu.constructors_data.cells_to_remove_spaces", []),
            cells_to_remove_accents=settings.get("module_validator_lpu.constructors_data.cells_to_remove_accents", []),
        )
    except Exception as e:
        logger.error(f"Erro ao carregar o arquivo de construtoras: {e}")
        raise

    # Valida colunas obrigatórias
    missing_columns = set(required_columns.keys()) - set(df.columns)
    if missing_columns:
        raise MissingColumnsError(
            f"Colunas obrigatórias ausentes na base de construtoras: {missing_columns}"
        )

    # Garante tipos corretos usando cast_columns
    try:
        df = cast_columns(df, required_columns)
    except ValueError as e:
        logger.error(f"Erro ao converter tipos de colunas na base de construtoras: {e}")
        raise

    return df


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


def validate_and_merge(
    df_left: pd.DataFrame,
    df_right: pd.DataFrame,
    left_on: List[str],
    right_on: List[str],
    how: str = "left",
    log_message: str = "",
) -> Tuple[pd.DataFrame, int, int]:
    """
    Função genérica para validar tipos, realizar merge e contar os resultados.

    Args:
        df_left (pd.DataFrame): DataFrame à esquerda.
        df_right (pd.DataFrame): DataFrame à direita.
        left_on (List[str]): Colunas do DataFrame à esquerda para o merge.
        right_on (List[str]): Colunas do DataFrame à direita para o merge.
        how (str): Tipo de merge (ex.: 'left', 'inner').
        log_message (str): Mensagem de log para identificar o merge.

    Returns:
        Tuple[pd.DataFrame, int, int]:
            - DataFrame resultante do merge.
            - Quantidade de itens que deram match.
            - Quantidade total de itens no DataFrame à esquerda.
    """
    # Valida se os tipos das colunas são compatíveis
    for col_left, col_right in zip(left_on, right_on):
        if df_left[col_left].dtype != df_right[col_right].dtype:
            logger.warning(
                f"⚠️ Tipos diferentes nas colunas: {col_left} ({df_left[col_left].dtype}) e {col_right} ({df_right[col_right].dtype})."
            )

    # Realiza o merge
    merged_df = pd.merge(
        df_left,
        df_right,
        left_on=left_on,
        right_on=right_on,
        how=how,
        suffixes=("_orc", "_lpu"),
        indicator=True,
    )

    # Conta os itens que deram match
    matched_count = merged_df[merged_df["_merge"] == "both"].shape[0]
    total_count = df_left.shape[0]

    # Loga a informação do merge
    logger.info(
        f"{log_message} - {matched_count} dados de {total_count} ({round((matched_count / total_count) * 100, 2) if total_count > 0 else 0}%)"
    )

    return merged_df, matched_count, total_count


def merge_budget_lpu(
    df_budget: pd.DataFrame,
    df_lpu: pd.DataFrame,
    columns_on_budget: List[str],
    columns_on_lpu: List[str],
    secondary_columns_on_budget: Optional[List[str]] = None,
    secondary_columns_on_lpu: Optional[List[str]] = None,
) -> pd.DataFrame:
    """
    Mescla orçamento e LPU usando colunas especificadas, com fallback para colunas secundárias.

    Args:
        df_budget: DataFrame do orçamento.
        df_lpu: DataFrame da base LPU.
        columns_on_budget: Colunas primárias do df_budget para usar na mesclagem.
        columns_on_lpu: Colunas primárias do df_lpu para usar na mesclagem.
        secondary_columns_on_budget: Colunas secundárias do df_budget para fallback.
        secondary_columns_on_lpu: Colunas secundárias do df_lpu para fallback.

    Returns:
        DataFrame combinado com INNER JOIN.

    Raises:
        ValidatorLPUError: Se a mesclagem resultar em um DataFrame vazio.
    """
    # Realiza o primeiro merge (colunas primárias)
    merged_df, matched_count, total_count = validate_and_merge(
        df_budget,
        df_lpu,
        columns_on_budget,
        columns_on_lpu,
        how="left",
        log_message=f"Match realizado usando as colunas primárias: {columns_on_budget} - {columns_on_lpu}",
    )

    # Filtra os itens que não foram cruzados no primeiro merge
    not_matched = merged_df[merged_df["_merge"] == "left_only"].drop(columns=["_merge"])

    # Se houver itens não cruzados e colunas secundárias forem fornecidas, tenta o merge secundário
    if not not_matched.empty and secondary_columns_on_budget and secondary_columns_on_lpu:
        # Realiza o segundo merge (colunas secundárias)
        secondary_merge, matched_secondary_count, not_matched_count = validate_and_merge(
            not_matched,
            df_lpu,
            secondary_columns_on_budget,
            secondary_columns_on_lpu,
            how="left",
            log_message=f"Segundo match realizado usando as colunas secundárias: {secondary_columns_on_budget} - {secondary_columns_on_lpu}",
        )

        # Atualiza os itens cruzados e não cruzados
        matched_secondary = secondary_merge[secondary_merge["_merge"] == "both"].drop(
            columns=["_merge"]
        )
        not_matched_secondary = secondary_merge[secondary_merge["_merge"] == "left_only"].drop(
            columns=["_merge"]
        )

        # Concatena os resultados do primeiro e segundo cruzamento
        merged_df = pd.concat(
            [merged_df[merged_df["_merge"] == "both"], matched_secondary],
            ignore_index=True,
        )
        not_matched = not_matched_secondary
    logger.info(
        "Match realizado usando as colunas: {} - {} - {} dados de {} ({}%)".format(
            columns_on_budget,
            columns_on_lpu,
            matched_count,
            total_count,
            round((matched_count / total_count) * 100, 2),
        )
    )

    # Se ainda houver itens não cruzados, adiciona uma coluna de status
    if not not_matched.empty:
        not_matched["status"] = "Não cruzado"
        logger.warning(f"⚠️ {len(not_matched)} itens não foram cruzados.")

    # Retorna o DataFrame final
    return merged_df


def validate_lpu(
    file_path_budget: Union[str, Path] = None,
    file_path_metadata: Union[str, Path] = None,
    file_path_lpu: Union[str, Path] = None,
    file_path_agencies: Union[str, Path] = None,
    file_path_constructors: Union[str, Path] = None,
    output_dir: Union[str, Path] = None,
    output_file: str = "02_BASE_RESULTADO_VALIDADOR_LPU.xlsx",
    verbose: bool = True,
) -> pd.DataFrame:
    """
    Função orquestradora para validação LPU.

    Realiza todo o fluxo de validação:
    1. Carrega orçamento, LPU, agências e construtoras.
    2. Cruza os dados (INNER JOIN em cod_item + unidade).
    3. Calcula discrepâncias com tolerância configurável.
    4. Classifica itens (OK, Para ressarcimento, Abaixo LPU).
    5. Salva resultados em formatos Excel, CSV e HTML.

    Args:
        file_path_budget: Caminho para o arquivo de orçamento (padrão nas configurações).
        file_path_metadata: Caminho para o arquivo de metadados (padrão nas configurações).
        file_path_lpu: Caminho para o arquivo da LPU (padrão nas configurações).
        file_path_agencies: Caminho para o arquivo de agências (padrão nas configurações).
        file_path_constructors: Caminho para o arquivo de construtoras (padrão nas configurações).
        output_dir: Diretório para salvar resultados (padrão nas configurações).
        output_file_name: Nome base para os arquivos de saída (sem extensão).
        verbose: Se True, exibe estatísticas no console.

    Returns:
        DataFrame com os resultados completos da validação.

    Raises:
        ValidatorLPUError: Em caso de erro na validação.
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
        logger.info(f"Carregando metadados de orçamentos de: {file_path_metadata}")
        df_budget_metadata = load_metadata(file_path_metadata)
        if verbose:
            logger.info(
                f"   ✅ Metadados dos orçamentos carregado: {len(df_budget_metadata)} itens"
            )
    except Exception as e:
        logger.error(f"Erro ao carregar metadados dos orçamentos: {e}")
        raise ValidatorLPUError(f"Erro ao carregar metadados dos orçamentos: {e}")

    try:
        logger.debug(f"Carregando LPU de: {file_path_lpu}")
        df_lpu = load_lpu(file_path_lpu)
        if verbose:
            logger.info(f"   ✅ LPU carregada: {len(df_lpu)} itens")
    except Exception as e:
        logger.error(f"Erro ao carregar LPU: {e}")
        raise ValidatorLPUError(f"Erro ao carregar LPU: {e}")

    try:
        logger.debug(f"Carregando agências de: {file_path_agencies}")
        df_agencies = load_agencies(file_path_agencies)
        if verbose:
            logger.info(f"   ✅ Agências carregadas: {len(df_agencies)} itens")
    except Exception as e:
        logger.error(f"Erro ao carregar agências: {e}")
        raise ValidatorLPUError(f"Erro ao carregar agências: {e}")

    try:
        logger.debug(f"Carregando construtoras de: {file_path_constructors}")
        df_constructors = load_constructors(file_path_constructors)
        if verbose:
            logger.info(f"   ✅ Construtoras carregadas: {len(df_constructors)} itens")
    except Exception as e:
        logger.error(f"Erro ao carregar construtoras: {e}")
        raise ValidatorLPUError(f"Erro ao carregar construtoras: {e}")

    # 2. Cruza dados
    if verbose:
        logger.info("🔗 Cruzando orçamento com LPU...")
    
    try:
        # Realiza o merge entre budget e metadados
        df_merge_budget_metadata = merge_data_with_columns(
            df_left=df_budget,
            df_right=df_budget_metadata,
            left_on=settings.get("module_validator_lpu.merge_budget_metadata.left_on"),
            right_on=settings.get("module_validator_lpu.merge_budget_metadata.right_on"),
            how=settings.get("module_validator_lpu.merge_budget_metadata.how", "left"),
            suffixes=("_orc", "_meta"),
            validate=settings.get("module_validator_lpu.merge_budget_metadata.validate", "many_to_one"),
        )
        if verbose:
            logger.info(f"   ✅ Itens cruzados: {len(df_merge_budget_metadata)}")
            logger.info(f"   ✅ Qtd de linhas e colunas: {df_merge_budget_metadata.shape}")
    except Exception as e:
        logger.error(f"Erro ao cruzar dados: {e}")
        raise ValidatorLPUError(f"Erro ao cruzar dados: {e}")
    
    try:
        # Realiza o merge entre budget/metadados e agencias
        df_merge_budget_metadata_agencias = merge_data_with_columns(
            df_left=df_merge_budget_metadata,
            df_right=df_agencies,
            left_on=settings.get("module_validator_lpu.merge_budget_metadata_agencies.left_on"),
            right_on=settings.get("module_validator_lpu.merge_budget_metadata_agencies.right_on"),
            how=settings.get("module_validator_lpu.merge_budget_metadata_agencies.how", "left"),
            suffixes=("_meta", "_age"),
            validate=settings.get("module_validator_lpu.merge_budget_metadata_agencies.validate", "many_to_one"),
        )
        if verbose:
            logger.info(f"   ✅ Itens cruzados: {len(df_merge_budget_metadata_agencias)}")
            logger.info(f"   ✅ Qtd de linhas e colunas: {df_merge_budget_metadata_agencias.shape}")
    except Exception as e:
        logger.error(f"Erro ao cruzar dados: {e}")
        raise ValidatorLPUError(f"Erro ao cruzar dados: {e}")
    
    try:
        # Realiza o merge entre budget/metadados e agencias
        df_merge_budget_metadata_agencias_constructors = merge_data_with_columns(
            df_left=df_merge_budget_metadata_agencias,
            df_right=df_constructors,
            left_on=settings.get("module_validator_lpu.merge_budget_metadata_agencies_constructors.left_on"),
            right_on=settings.get("module_validator_lpu.merge_budget_metadata_agencies_constructors.right_on"),
            how=settings.get("module_validator_lpu.merge_budget_metadata_agencies_constructors.how", "left"),
            suffixes=("_age", "_constr"),
            validate=settings.get("module_validator_lpu.merge_budget_metadata_agencies_constructors.validate", "many_to_one"),
        )
        if verbose:
            logger.info(f"   ✅ Itens cruzados: {len(df_merge_budget_metadata_agencias_constructors)}")
            logger.info(f"   ✅ Qtd de linhas e colunas: {df_merge_budget_metadata_agencias_constructors.shape}")
    except Exception as e:
        logger.error(f"Erro ao cruzar dados: {e}")
        raise ValidatorLPUError(f"Erro ao cruzar dados: {e}")
    
    # Salvar o resultado em um arquivo Excel
    export_data(data=df_merge_budget_metadata_agencias_constructors, 
                file_path=Path(output_dir, output_file), 
                index=False)
    logger.success(f"Resultado salvo em: {output_file}")

    try:
        # Realiza o merge entre orçamento e LPU
        df_merge_budget_metadata_agencias_constructors_lpu = merge_budget_lpu(
            df_budget=df_merge_budget_metadata_agencias_constructors,
            df_lpu=df_lpu,
            columns_on_budget=[
                settings.get("module_validator_lpu.merge_budget_lpu.columns_on_budget_id"),
            ],  # Coluna primária do df_budget
            columns_on_lpu=[
                settings.get("module_validator_lpu.merge_budget_lpu.columns_on_lpu_id"),
            ],  # Coluna primária do df_lpu
            secondary_columns_on_budget=[
                settings.get("module_validator_lpu.merge_budget_lpu.columns_on_budget_nome"),
            ],  # Coluna secundária do df_budget
            secondary_columns_on_lpu=[
                settings.get("module_validator_lpu.merge_budget_lpu.columns_on_lpu_nome"),
            ],  # Coluna secundária do df_lpu
        )
        if verbose:
            logger.info(f"   ✅ Itens cruzados: {len(df_merge_budget_metadata_agencias_constructors_lpu)}")
    except Exception as e:
        logger.error(f"Erro ao cruzar dados: {e}")
        raise ValidatorLPUError(f"Erro ao cruzar dados: {e}")

    if verbose:
        logger.info("")

    # 3. Calcula discrepâncias
    if verbose:
        logger.info(
            f"🧮 Calculando discrepâncias (tolerância {settings.get('validador_lpu.tolerancia_percentual')}%)..."
        )

    try:
        df_result = calculate_discrepancies(df_budget_lpu)
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
    file_path_metadata: Union[str, Path] = None,
    file_path_lpu: Union[str, Path] = None,
    file_path_agencies: Union[str, Path] = None,
    file_path_constructors: Union[str, Path] = None,
    output_dir: Union[str, Path] = None,
    output_file: str = None,
    verbose: bool = True,
) -> int:
    """
    Função principal para execução direta do módulo ou chamada externa.

    Args:
        file_path_budget: Caminho para o arquivo de orçamento (padrão nas configurações se None).
        file_path_metadata: Caminho para o arquivo de metadados dos orçamentos (padrão nas configurações se None).
        file_path_lpu: Caminho para o arquivo da LPU (padrão nas configurações se None).
        file_path_agencies: Caminho para o arquivo de agências (padrão nas configurações se None).
        file_path_constructors: Caminho para o arquivo de construtoras (padrão nas configurações se None).
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
        file_path_budget or settings.get("module_validator_lpu.budget_data.file_path"),
    )
    path_file_metadata = Path(
        base_dir,
        file_path_metadata or settings.get("module_validator_lpu.budget_metadados.file_path"),
    )
    path_file_lpu = Path(
        base_dir, file_path_lpu or settings.get("module_validator_lpu.lpu_data.file_path")
    )
    path_file_agencies = Path(
        base_dir, file_path_agencies or settings.get("module_validator_lpu.agencies_data.file_path")
    )
    path_file_constructors = Path(
        base_dir,
        file_path_constructors or settings.get("module_validator_lpu.constructors_data.file_path"),
    )
    output_dir = Path(
        base_dir, output_dir or settings.get("module_validator_lpu.output_settings.output_dir")
    )
    output_file = output_file or settings.get(
        "module_validator_lpu.output_settings.file_path_output"
    )

    logger.debug(f"Orçamento: {path_file_budget}")
    logger.debug(f"LPU: {path_file_lpu}")
    logger.debug(f"Agências: {path_file_agencies}")
    logger.debug(f"Construtoras: {path_file_constructors}")
    logger.debug(f"Saída: {output_dir}")

    try:
        df_result = validate_lpu(
            file_path_budget=path_file_budget,
            file_path_metadata=path_file_metadata,
            file_path_lpu=path_file_lpu,
            file_path_agencies=path_file_agencies,
            file_path_constructors=path_file_constructors,
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

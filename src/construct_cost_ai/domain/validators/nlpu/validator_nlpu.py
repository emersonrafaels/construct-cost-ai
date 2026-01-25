"""
Módulo de Validação Não LPU - Verifica discrepâncias entre orçamento e base de preços.

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
    select_columns,
    rename_columns,
    filter_by_merge_column,
    filter_dataframe_dict_values,
)
from utils.lpu.lpu_functions import (
    generate_region_group_combinations,
    split_regiao_grupo,
    separate_regions,
)

from construct_cost_ai.domain.validators.utils.calculate_price_functions import calculate_total_item
from utils.python_functions import get_item_safe
from utils.fuzzy.fuzzy_functions import apply_match_fuzzy_two_dataframes

settings = get_settings()


class ValidatorNLPUError(Exception):
    """Exceção base para erros do validador LPU."""

    pass


class FileNotFoundError(ValidatorNLPUError):
    """Exceção para arquivo não encontrado."""

    pass


class MissingColumnsError(ValidatorNLPUError):
    """Exceção para colunas obrigatórias ausentes."""

    pass


def load_budget(
    file_path: Union[str, Path], validator_output_data: bool = False, output_dir_file: str = None
) -> pd.DataFrame:
    """
    Carrega o arquivo de orçamento.

    Args:
        path: Caminho para o arquivo de orçamento (Excel ou CSV)
        validator_output_data: Validador se é desejado salvar os dados após processamento (Boolean)
        output_dir_file: Arquivo que deve ser salvo, se o validator_output_data for True (str)

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
        "module_validator_nlpu.budget_data.required_columns_with_types", []
    )

    # Coluna valor total
    column_total_value = settings.get(
        "module_validator_nlpu.budget_data.column_total_value", "VALOR TOTAL"
    )

    try:
        # Ler os dados de Orçamento e realizar pré processing
        df = transform_case(
            read_data(
                file_path=file_path,
                sheet_name=settings.get("module_validator_nlpu.budget_data.sheet_name", "Tables"),
            ),
            columns_to_upper=True,
            cells_to_upper=True,
            cells_to_remove_spaces=settings.get(
                "module_validator_nlpu.budget_data.cells_to_remove_spaces", []
            ),
            cells_to_remove_accents=settings.get(
                "module_validator_nlpu.budget_data.cells_to_remove_accents", []
            ),
            cells_to_strip=True,
        )
    except Exception as e:
        raise ValidatorNLPUError(f"Erro ao carregar orçamento: {e}")

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
        raise ValidatorNLPUError(f"Erro ao converter tipos de colunas: {e}")

    # Se total_orcado não existir, calcula
    df = calculate_total_item(
        df=df,
        column_total_value=column_total_value,
        column_quantity=settings.get("module_validator_nlpu.budget_data.column_quantity", "qtde"),
        column_unit_price=settings.get(
            "module_validator_nlpu.budget_data.column_unit_price", "unitario_orcado"
        ),
    )

    # Verificando se há colunas para renomear
    if settings.get("module_validator_nlpu.budget_data.columns_to_rename"):
        df = rename_columns(
            df, rename_dict=settings.get("module_validator_nlpu.budget_data.columns_to_rename")
        )

    # Verificando se é desejado salvar os dados resultantes
    if validator_output_data:
        export_data(data=df, file_path=output_dir_file)

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
    filter_columns_not_matching: bool = True,
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
        filter_columns_not_matching (bool): Se True, filtra colunas que não correspondem ao padrão esperado.

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
    if any(col in df.columns for col in expected_core_cols):

        if filter_columns_not_matching:
            # Filtra colunas que não correspondem ao padrão esperado
            df = select_columns(df, target_columns=found_wide_cols)

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

    # Separa as regiões em colunas de regiões individuais
    df_wide, col_to_regiao_grupo = separate_regions(
        df=df_wide, col_to_regiao_grupo=col_to_regiao_grupo, regions=regions
    )

    # Transforma o DataFrame para o formato LONG usando a função melt
    df_long = df_wide.melt(
        id_vars=[id_col, item_col, unit_col] + (keep_cols or []),  # Colunas que permanecem fixas
        value_vars=col_to_regiao_grupo,  # Colunas que serão transformadas em linhas
        var_name="REGIAO_GRUPO",  # Nome da coluna que conterá os nomes das colunas originais
        value_name=value_name,  # Nome da coluna que conterá os valores
    )

    # Divide regiao_grupo em 'regiao' e 'grupo' usando a função split_regiao_grupo
    df_long["REGIAO"], df_long["GRUPO"] = zip(
        *df_long["REGIAO_GRUPO"].apply(lambda col: split_regiao_grupo(col, regions, groups))
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
            raise ValidatorNLPUError(
                f"Conversão de {report.format} para {target} não suportada ou formato desconhecido."
            )
    else:
        if target == "long":
            df_wide, df_long = wide_to_long(df, **kwargs)
        elif target == "wide":
            df_wide, df_long = long_to_wide(df, **kwargs)
        else:
            raise ValidatorNLPUError(f"Formato alvo desconhecido: {target}")

    return df


def load_lpu(
    file_path: Union[str, Path], validator_output_data: bool = False, output_dir_file: str = None
) -> pd.DataFrame:
    """
    Carrega o arquivo base da LPU.

    Args:
        file_path: Caminho para o arquivo da LPU
        validator_output_data: Validador se é desejado salvar os dados após processamento (Boolean)
        output_dir_file: Arquivo que deve ser salvo, se o validator_output_data for True (str)

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
        {"CÓD ITEM": "object", "ITEM": "object", "UNID.": "object"},
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
            cells_to_remove_spaces=settings.get(
                "module_validator_lpu.lpu_data.cells_to_remove_spaces", []
            ),
            cells_to_remove_accents=settings.get(
                "module_validator_lpu.lpu_data.cells_to_remove_accents", []
            ),
            cells_to_strip=True,
        )
    except Exception as e:
        raise ValidatorNLPUError(f"Erro ao carregar base LPU: {e}")

    # Valida colunas obrigatórias na base de LPU
    missing_columns = set(required_columns) - set(df.columns)
    if missing_columns:
        raise MissingColumnsError(
            f"Colunas obrigatórias ausentes na LPU: {', '.join(missing_columns)}"
        )

    # Detecta formato e converte se necessário
    report = identify_lpu_format(df)

    if report.format == "wide":
        df_wide, df_long = wide_to_long(
            df,
            id_col=get_item_safe(required_columns, 0, return_key=True),
            item_col=get_item_safe(required_columns, 1, return_key=True),
            unit_col=get_item_safe(required_columns, 2, return_key=True),
            col_to_regiao_grupo=report.columns,
        )
        logger.info("Convertido LPU de WIDE para LONG.")
    elif report.format == "long":
        # df = long_to_wide(df)
        logger.info("Mantido LPU no formato LONG.")
    else:
        raise ValidatorNLPUError(f"Formato desconhecido: {report.format}")

    try:
        # Adiciona as colunas detectadas ao required_columns
        required_columns.update({column: float for column in report.columns})

        # Converter as colunas do dataframe para os tipos corretos
        df_wide = cast_columns(df_wide, required_columns)
    except ValueError as e:
        raise ValidatorNLPUError(f"Erro ao converter tipos de colunas: {e}")

    # Realizando as transformações finais dos dataframes
    df_wide = transform_case(df=df_wide, columns_to_upper=True)
    df_long = transform_case(df=df_long, columns_to_upper=True)

    # Verificando se há colunas para renomear
    if settings.get("module_validator_lpu.lpu_data.columns_to_rename"):
        df_long = rename_columns(
            df_long, rename_dict=settings.get("module_validator_lpu.lpu_data.columns_to_rename")
        )

    # Verificando se é desejado salvar os dados resultantes
    if validator_output_data:
        export_data(data=df, file_path=output_dir_file)

    return df_wide, df_long


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


def generate_format_result(df: pd.DataFrame) -> pd.DataFrame:
    """
    Cria o DataFrame de resultado formatado para exportação.

    Args:
        df (pd.DataFrame): DataFrame com os resultados completos da validação.

    Returns:
        pd.DataFrame: DataFrame formatado para exportação.
    """

    # Seleciona as colunas necessárias para o resultado final
    list_select_columns = settings.get(
        "module_validator_lpu.output_settings.list_columns_result", []
    )

    if list_select_columns:
        df_result = select_columns(df=df, target_columns=list_select_columns)

    return df_result


def apply_match_fuzzy_budget_lpu(
    df_left: pd.DataFrame,
    df_right: pd.DataFrame,
    df_left_column: str = None,
    df_choices_column: str = None,
    filter_cols_to_match: dict = None,
    list_columns_get_df_right: list = None,
    threshold: int = 80,
    replace_column: bool = False,
    drop_columns_result: bool = False,
    merge_fuzzy_column_right: str = None,
) -> pd.DataFrame:
    """
    Realiza um match fuzzy entre dois DataFrames e combina os resultados.

    Args:
        df_left (pd.DataFrame): DataFrame à esquerda (base principal para o match).
        df_right (pd.DataFrame): DataFrame à direita (base de referência para o match).
        df_left_column (str, opcional): Nome da coluna no DataFrame à esquerda usada para o match.
        df_choices_column (str, opcional): Nome da coluna no DataFrame à direita usada como referência para o match.
        filter_cols_to_match (dict, opcional): Filtros a serem aplicados no DataFrame à esquerda antes do match.
        list_columns_get_df_right (list, opcional): Colunas do DataFrame à direita a serem incluídas no resultado.
        threshold (int, opcional): Pontuação mínima para considerar um match válido. Padrão é 80.
        replace_column (bool, opcional): Substitui a coluna original pelo melhor match, se True. Padrão é False.
        drop_columns_result (bool, opcional): Remove colunas auxiliares do resultado, se True. Padrão é False.
        merge_fuzzy_column_right (str, opcional): Nome da coluna no DataFrame à direita usada para mapear colunas adicionais. Padrão é None.

    Returns:
        pd.DataFrame: DataFrame combinado com linhas correspondentes e não correspondentes.
    """

    df_result = apply_match_fuzzy_two_dataframes(
        df_left=df_left,
        df_right=df_right,
        filter_cols_to_match=filter_cols_to_match,
        list_columns_get_df_right=list_columns_get_df_right,
        df_left_column=df_left_column,
        df_choices_column=df_choices_column,
        threshold=threshold,
        replace_column=replace_column,
        drop_columns_result=drop_columns_result,
        merge_fuzzy_column_right=merge_fuzzy_column_right,
    )

    # Retornar o DataFrame final
    return df_result


def validate_nlpu(
    file_path_budget: Union[str, Path] = None,
    file_path_lpu: Union[str, Path] = None,
    base_dir: Union[str, Path] = None,
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
        file_path_lpu: Caminho para o arquivo da LPU (padrão nas configurações).
        base_dir: Diretório raiz do projeto (padrão nas configurações).
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
        logger.info("VALIDADOR Não LPU - Conciliação Orçamento vs Base de Preços")
        print("-" * 50)

    # 1. Carrega dados
    if verbose:
        logger.info("📂 Carregando arquivos...")

    try:
        logger.info(f"Carregando orçamento de: {file_path_budget}")
        df_budget = load_budget(
            file_path_budget,
            validator_output_data=settings.get(
                "module_validator_nlpu.budget_data.validator_save_sot", True
            ),
            output_dir_file=Path(
                base_dir, settings.get("module_validator_lpu.budget_data.dir_path_file_sot")
            ),
        )
        if verbose:
            logger.info(f"✅ Orçamento carregado: {len(df_budget)} itens")
    except Exception as e:
        logger.error(f"Erro ao carregar orçamento: {e}")
        raise ValidatorNLPUError(f"Erro ao carregar orçamento: {e}")

    try:
        logger.info(f"Carregando LPU de: {file_path_lpu}")
        df_lpu_wide, df_lpu_long = load_lpu(
            file_path_lpu,
            validator_output_data=settings.get(
                "module_validator_lpu.lpu_data.validator_save_sot", True
            ),
            output_dir_file=Path(
                base_dir, settings.get("module_validator_lpu.lpu_data.dir_path_file_sot")
            ),
        )
        if verbose:
            logger.info(f"✅ LPU carregada: {len(df_lpu_long)} itens")
    except Exception as e:
        logger.error(f"Erro ao carregar LPU: {e}")
        raise ValidatorNLPUError(f"Erro ao carregar LPU: {e}")

    try:
        # Realiza o merge entre budget e lpu usando match fuzzy
        logger.info(f"🔗 Cruzando orçamento com LPU usando Match Fuzzy")

        indicator = settings.get(
            "module_validator_nlpu.match_fuzzy_budget_lpu.indicator",
            "_match_fuzzy_budget_lpu",
        )

        validator_use_merge_fuzzy_budget_lpu = settings.get(
            "module_validator_nlpu.match_fuzzy_budget_lpu.validator_use_merge_fuzzy"
        )

        if validator_use_merge_fuzzy_budget_lpu:

            # Aplicando match fuzzy
            df_match_fuzzy_budget_lpu = apply_match_fuzzy_budget_lpu(
                df_left=df_budget,
                df_right=df_lpu_long,
                df_left_column=settings.get(
                    "module_validator_nlpu.match_fuzzy_budget_lpu.validator_use_merge_fuzzy_column_left"
                ),
                df_choices_column=settings.get(
                    "module_validator_nlpu.match_fuzzy_budget_lpu.validator_use_merge_fuzzy_column_right"
                ),
                filter_cols_to_match=settings.get(
                    "module_validator_nlpu.match_fuzzy_budget_lpu.filter_cols_to_match"
                ),
                list_columns_get_df_right=[],
                threshold=settings.get(
                    "module_validator_nlpu.match_fuzzy_budget_lpu.validator_use_merge_fuzzy_threshold"
                ),
                replace_column=settings.get(
                    "module_validator_nlpu.match_fuzzy_budget_lpu.replace_column"
                ),
                drop_columns_result=settings.get(
                    "module_validator_nlpu.match_fuzzy_budget_lpu.drop_columns_result"
                ),
            )

        if verbose:

            logger.info(f"✅ Qtd de linhas e colunas: {df_match_fuzzy_budget_lpu.shape}")

    except Exception as e:
        logger.error(f"Erro ao cruzar dados: {e}")
        raise ValidatorNLPUError(f"Erro ao cruzar dados: {e}")

    """
    # Calcula discrepâncias
    try:
        df_result = calculate_lpu_discrepancies(
            df=df_merge_budget_metadata_agencias_constructors_lpu,
            column_quantity=settings.get("module_validator_lpu.column_quantity"),
            column_unit_price_paid=settings.get("module_validator_lpu.column_unit_price_paid"),
            column_unit_price_lpu=settings.get("module_validator_lpu.column_unit_price_lpu"),
            column_total_paid=settings.get("module_validator_lpu.column_total_paid"),
            column_total_lpu=settings.get("module_validator_lpu.column_total_lpu"),
            column_difference=settings.get("module_validator_lpu.column_difference"),
            column_discrepancy=settings.get("module_validator_lpu.column_discrepancy"),
            column_status=settings.get("module_validator_lpu.column_status"),
            tol_percentile=settings.get("module_validator_lpu.tol_percentile"),
            verbose=settings.get("module_validator_lpu.verbose", True),
        )
    except Exception as e:
        logger.error(f"Erro ao calcular discrepâncias: {e}")
        raise ValidatorNLPUError(f"Erro ao calcular discrepâncias: {e}")
        
    """

    # Formatando o resultado final
    df_result = generate_format_result(df_result)

    # Salvar o resultado em um arquivo Excel
    export_data(
        data=df_result,
        file_path=Path(output_dir, output_file),
        index=False,
    )

    logger.success(f"Resultado salvo em: {output_file}")

    """
    # Estatísticas
    if settings.get("module_validator_lpu.get_lpu_status", False):
        output_pdf = Path(
            output_dir,
            settings.get("module_validator_lpu.output_settings.file_path_stats_output_pdf"),
        )
        calculate_validation_stats_and_generate_report(
            df_result=df_result,
            validator_output_pdf=settings.get(
                "module_validator_lpu.stats.validator_output_pdf", True
            ),
            output_pdf=output_pdf,
            verbose=settings.get("module_validator_lpu.verbose", True),
        )
        
    """

    return df_result


def orchestrate_validate_nlpu(
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

    # Define os caminhos dos arquivos com base nas configurações ou argumentos fornecidos
    # Arquivo de orçamento
    path_file_budget = Path(
        base_dir,
        settings.get("module_validator_lpu.output_settings.output_dir"),
        file_path_budget or settings.get("module_validator_lpu.output_settings.file_path_output"),
    )

    # Arquivo da LPU
    path_file_lpu = Path(
        base_dir, file_path_lpu or settings.get("module_validator_lpu.lpu_data.file_path")
    )

    # Diretório de outputs dos resultados
    output_dir = Path(
        base_dir, output_dir or settings.get("module_validator_nlpu.output_settings.output_dir")
    )

    # Nome do arquivo de output
    output_file = output_file or settings.get(
        "module_validator_nlpu.output_settings.file_path_output"
    )

    logger.debug(f"Orçamento: {path_file_budget}")
    logger.debug(f"LPU: {path_file_lpu}")
    logger.debug(f"Saída: {output_dir}")
    logger.debug(f"Arquivo de saída: {output_file}")

    try:
        df_result = validate_nlpu(
            file_path_budget=path_file_budget,
            file_path_lpu=path_file_lpu,
            base_dir=base_dir,
            output_dir=output_dir,
            output_file=output_file,
            verbose=verbose,
        )

        logger.success("Verificador Inteligente executado com sucesso - Modulo Não LPU")
        return df_result

    except ValidatorNLPUError as e:
        logger.error(f"ERRO: {e}")
        return 1
    except Exception as e:
        logger.error(f"ERRO INESPERADO: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(orchestrate_validate_lpu())

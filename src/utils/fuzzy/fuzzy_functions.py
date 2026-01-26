"""
Realiza o uso do Módulo: fuzzy_validations
------------------------

Responsável por realizar validações fuzzy, como encontrar matches aproximados
entre a base de orçamentos e a base de LPU, utilizando o módulo fuzzy_validations.

"""

__author__ = "Emerson V. Rafael (emervin)"
__copyright__ = "Verificador Inteligente de Orçamentos de Obras"
__credits__ = ["Emerson V. Rafael", "Lucas Ken", "Clarissa Simoyama"]
__license__ = "MIT"
__version__ = "1.0.0"
__maintainer__ = "Emerson V. Rafael (emervin), Lucas Ken (kushida), Clarissa Simoyama (simoyam)"
__squad__ = "DataCraft"
__email__ = "emersonssmile@gmail.com"
__status__ = "Development"

import sys
from pathlib import Path
from pprint import pprint
from typing import Callable, Union

import pandas as pd
from fuzzywuzzy import fuzz

# Adicionar src ao path
base_dir = Path(__file__).parents[3]
sys.path.insert(0, str(Path(base_dir, "src")))

from utils.data.data_functions import drop_columns, filter_dataframe_dict_values
from utils.fuzzy.fuzzy_validations import fuzzy_match
from utils.data.data_functions import export_data
from utils.python_functions import measure_execution_time
from config.config_logger import logger


def get_columns_from_best_match(
    df_fuzzy_result: pd.DataFrame,
    df_right: pd.DataFrame,
    best_match_column: str = "BEST_MATCH",
    columns_to_get: list = None,
    list_columns_merge_fuzzy_df_left: Union[list, str] = None,
    list_columns_merge_fuzzy_df_right: Union[list, str] = None,
    keep_original_columns_names_df_right: bool = False,
) -> pd.DataFrame:
    """
    Obtém colunas do DataFrame `df_right` com base na coluna `BEST_MATCH` do DataFrame fuzzy.

    Args:
        df_fuzzy_result (pd.DataFrame): DataFrame resultante do processo fuzzy, contendo a coluna `BEST_MATCH`.
        df_right (pd.DataFrame): DataFrame de referência (direita) contendo os dados a serem obtidos.
        best_match_column (str): Nome da coluna no DataFrame fuzzy que contém os melhores matches. Default é "BEST_MATCH".
        columns_to_get (list): Lista de colunas do DataFrame `df_right` a serem obtidas. Default é None (todas as colunas).
        list_columns_merge_fuzzy_df_left (Union[list, str]): Coluna(s) no DataFrame `df_fuzzy_result` usada(s) para o merge. Default é None (usa `BEST_MATCH`).
        list_columns_merge_fuzzy_df_right (Union[list, str]): Coluna(s) no DataFrame `df_right` usada(s) para o merge. Default é None (usa `BEST_MATCH`).
        keep_original_columns_names_df_right (bool): Se True, mantém os nomes originais das colunas do `df_right`. Default é False.

    Returns:
        pd.DataFrame: DataFrame atualizado com as colunas obtidas do `df_right`.
    """
    columns_to_get = columns_to_get or df_right.columns.tolist()

    # Garantir que list_columns_merge_fuzzy_df_left e list_columns_merge_fuzzy_df_right sejam listas
    if isinstance(list_columns_merge_fuzzy_df_left, str):
        list_columns_merge_fuzzy_df_left = [list_columns_merge_fuzzy_df_left]
    if isinstance(list_columns_merge_fuzzy_df_right, str):
        list_columns_merge_fuzzy_df_right = [list_columns_merge_fuzzy_df_right]

    # Usar `best_match_column` como padrão se as listas não forem fornecidas
    list_columns_merge_fuzzy_df_left = list_columns_merge_fuzzy_df_left or [best_match_column]
    list_columns_merge_fuzzy_df_right = list_columns_merge_fuzzy_df_right or [best_match_column]

    # Garantir que as colunas de merge existem nos DataFrames
    for col in list_columns_merge_fuzzy_df_left:
        if col not in df_fuzzy_result.columns:
            raise ValueError(f"A coluna '{col}' não foi encontrada no DataFrame `df_fuzzy_result`.")
    for col in list_columns_merge_fuzzy_df_right:
        if col not in df_right.columns:
            raise ValueError(f"A coluna '{col}' não foi encontrada no DataFrame `df_right`.")

    # Garantir que a coluna de merge no `df_right` possui valores únicos
    if not df_right[list_columns_merge_fuzzy_df_right].drop_duplicates().shape[0] == df_right.shape[0]:
        logger.warning(
            f"As colunas '{list_columns_merge_fuzzy_df_right}' no DataFrame `df_right` contêm valores duplicados. Apenas a primeira ocorrência será usada."
        )
        df_right = df_right.drop_duplicates(subset=list_columns_merge_fuzzy_df_right)

    # Garantir que as colunas especificadas existem no DataFrame `df_right`
    missing_columns = [col for col in columns_to_get if col not in df_right.columns]
    if missing_columns:
        logger.warning(f"As seguintes colunas não foram encontradas no DataFrame `df_right`: {missing_columns}")

    # Remover colunas de merge de columns_to_get, se estiverem presentes
    columns_to_get = [col for col in columns_to_get if col not in list_columns_merge_fuzzy_df_right]

    # Selecionar as colunas necessárias para o merge
    df_right_subset = df_right[list_columns_merge_fuzzy_df_right + columns_to_get].drop_duplicates(
        subset=list_columns_merge_fuzzy_df_right
    )

    # Realizar o merge
    df_temp = df_fuzzy_result[list_columns_merge_fuzzy_df_left].merge(
        df_right_subset,
        how="left",
        left_on=list_columns_merge_fuzzy_df_left,
        right_on=list_columns_merge_fuzzy_df_right
    )

    # Adicionar as colunas ao DataFrame resultante
    for col in columns_to_get:
        new_col_name = f"{col}_MATCH_FUZZY" if not keep_original_columns_names_df_right else col
        df_fuzzy_result[new_col_name] = df_temp[col]

    return df_fuzzy_result


@measure_execution_time(condition=True)
def process_fuzzy_comparison_dataframes(
    df: str,
    df_choices: str,
    df_column: str,
    df_choices_column: str,
    threshold: int = 80,
    library: str = "rapidfuzz",
    validator_export_data: bool = False,
    output_file: str = "fuzzy_comparison_output.xlsx",
    replace_column: bool = False,
    drop_columns_result: bool = False,
    col_best_match: str = "BEST_MATCH",
    col_score_match: str = "SCORE_MATCH",
):
    """
    Processa os dados de orçamentos e LPU, realizando uma busca fuzzy entre as colunas especificadas.

    Args:
        df (str): Caminho para o arquivo de orçamentos.
        df_choices (str): Caminho para o arquivo de LPU.
        df_column (str): Nome da coluna na base de orçamentos a ser percorrida.
        lpu_column (str): Nome da coluna na base de LPU a ser usada como choices.
        threshold (int): Percentual mínimo de match para considerar válido. Default é 80.
        library (str): Biblioteca de fuzzy matching a ser usada ("rapidfuzz" ou "fuzzywuzzy").
        validator_export_data (bool): Se True, exporta o DataFrame resultante para um arquivo Excel. Default é False.
        output_file (str): Caminho do arquivo de saída para exportação dos
        replace_column (bool): Se True, substitui a coluna original pelo best_match e remove colunas auxiliares. Default é False.
        drop_columns_result (bool): Se True, remove as colunas auxiliares do resultado. Default é False.
        col_best_match (str): Nome da coluna para armazenar o melhor match. Default é "BEST_MATCH".
        col_score_match (str): Nome da coluna para armazenar o score do match. Default é "SCORE_MATCH".

    Returns:
        pd.DataFrame: DataFrame de orçamentos com uma nova coluna contendo os melhores matches.
    """

    # Iniciando as colunas
    col_best_match = col_best_match if col_best_match else "BEST_MATCH"
    col_score_match = col_score_match if col_score_match else "SCORE_MATCH"

    # Garantir que as colunas existem
    if df_column not in df.columns:
        logger.error(f"Coluna '{df_column}' não encontrada na base de orçamentos.")
    if df_choices_column not in df_choices.columns:
        logger.error(f"Coluna '{df_choices_column}' não encontrada na base de LPU.")

    # Extrair os choices da base de LPU
    choices = df_choices[df_choices_column].dropna().tolist()

    # Aplicar fuzzy_match para cada valor na coluna de orçamentos em um único apply
    matches = df[df_column].apply(
        lambda x: fuzzy_match(
            value=str(x), choices=choices, top_matches=1, threshold=threshold, library=library
        )
    )

    # Atribuir os valores às colunas do DataFrame
    df[col_best_match] = matches.apply(lambda x: x.choice if x else None)
    df[col_score_match] = matches.apply(lambda x: x.score if x else None)

    # Substituir a coluna original pelo best_match, se solicitado
    if replace_column:
        df[df_column] = df[col_best_match]

    if drop_columns_result:
        df = drop_columns(df, drop_column_list=[col_best_match, col_score_match])

    # Salvar o resultado em um arquivo Excel
    if validator_export_data:
        export_data(data=df, file_path=output_file, index=False)
        logger.info(
            f"Função: process_fuzzy_comparison_dataframes - Resultado salvo em: {output_file}"
        )

    return df


def apply_match_fuzzy_two_dataframes(
    df_left: pd.DataFrame,
    df_right: pd.DataFrame,
    filter_cols_to_match: dict = None,
    list_columns_get_df_right: list = None,
    df_left_column: str = None,
    df_choices_column: str = None,
    threshold: int = 80,
    replace_column: bool = False,
    drop_columns_result: bool = False,
    list_columns_merge_fuzzy_df_left: Union[list, str] = None,
    list_columns_merge_fuzzy_df_right: Union[list, str] = None,
    validator_get_columns_from_best_match: bool = False,
    keep_original_columns_names_df_right: bool = False,
) -> pd.DataFrame:
    """
    Realiza um match fuzzy entre dois DataFrames e combina os resultados.

    Args:
        df_left (pd.DataFrame): DataFrame à esquerda (base principal para o match).
        df_right (pd.DataFrame): DataFrame à direita (base de referência para o match).
        filter_cols_to_match (dict, opcional): Filtros a serem aplicados no DataFrame à esquerda antes do match.
        list_columns_get_df_right (list, opcional): Colunas do DataFrame à direita a serem incluídas no resultado.
        df_left_column (str, opcional): Nome da coluna no DataFrame à esquerda usada para o match.
        df_choices_column (str, opcional): Nome da coluna no DataFrame à direita usada como referência para o match.
        threshold (int, opcional): Pontuação mínima para considerar um match válido. Padrão é 80.
        replace_column (bool, opcional): Substitui a coluna original pelo melhor match, se True. Padrão é False.
        drop_columns_result (bool, opcional): Remove colunas auxiliares do resultado, se True. Padrão é False.
        list_columns_merge_fuzzy_df_left (str, opcional): Nome da coluna no DataFrame à esquerda usada para mapear colunas adicionais. Padrão é None.
        list_columns_merge_fuzzy_df_right (str, opcional): Nome da coluna no DataFrame à direita usada para mapear colunas adicionais. Padrão é None.
        validator_get_columns_from_best_match (bool, opcional): Se True, obtém colunas do DataFrame à direita com base no melhor match. Padrão é False.
        keep_original_columns_names_df_right (bool, opcional): Se True, mantém os nomes originais das colunas do DataFrame à direita. Padrão é False.

    Returns:
        pd.DataFrame: DataFrame combinado com linhas correspondentes e não correspondentes.
    """
    
    filter_cols_to_match = filter_cols_to_match or {}
    list_columns_get_df_right = list_columns_get_df_right or []

    # Filtra as linhas do DataFrame à esquerda com base nos filtros fornecidos
    df_left_match_fuzzy = filter_dataframe_dict_values(df=df_left, filters=filter_cols_to_match)

    # Identifica as linhas que não atendem aos critérios de filtro
    df_left_unmatched = df_left[~df_left.index.isin(df_left_match_fuzzy.index)]

    # Realiza o match fuzzy entre os DataFrames filtrados
    df_match_fuzzy = process_fuzzy_comparison_dataframes(
        df=df_left_match_fuzzy,
        df_choices=df_right,
        df_column=df_left_column,
        df_choices_column=df_choices_column,
        threshold=threshold,
        replace_column=replace_column,
        drop_columns_result=drop_columns_result,
    )
    

    if validator_get_columns_from_best_match:

        # Preenche as colunas especificadas do DataFrame à direita no DataFrame à esquerda
        df_match_fuzzy = get_columns_from_best_match(
            df_fuzzy_result=df_match_fuzzy,
            df_right=df_right,
            best_match_column="BEST_MATCH",
            columns_to_get=list_columns_get_df_right,
            list_columns_merge_fuzzy_df_left=list_columns_merge_fuzzy_df_left,
            list_columns_merge_fuzzy_df_right=list_columns_merge_fuzzy_df_right,
            keep_original_columns_names_df_right=keep_original_columns_names_df_right
        )

    # Combina as linhas correspondentes e não correspondentes em um único DataFrame
    df_result = pd.concat([df_match_fuzzy, df_left_unmatched], axis=0)

    return df_result

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
from typing import Callable

import pandas as pd
from fuzzywuzzy import fuzz

# Adicionar src ao path
base_dir = Path(__file__).parents[3]
sys.path.insert(0, str(Path(base_dir, "src")))

from utils.data.data_functions import drop_columns
from utils.fuzzy.fuzzy_validations import fuzzy_match
from utils.data.data_functions import export_data
from utils.python_functions import measure_execution_time
from config.config_logger import logger


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

    Returns:
        pd.DataFrame: DataFrame de orçamentos com uma nova coluna contendo os melhores matches.
    """

    # Iniciando as colunas
    col_best_match = "BEST_MATCH"
    col_score_match = "SCORE_MATCH"

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

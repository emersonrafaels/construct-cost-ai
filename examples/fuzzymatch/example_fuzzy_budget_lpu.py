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
__status__ = "Production"

import sys
from pathlib import Path
from pprint import pprint
from typing import Callable

import pandas as pd
from fuzzywuzzy import fuzz

# Adicionar src ao path
base_dir = Path(__file__).parents[2]
sys.path.insert(0, str(Path(base_dir, "src")))

from utils.fuzzy.fuzzy_validations import fuzzy_match
from utils.data.data_functions import export_data
from utils.python_functions import measure_execution_time


@measure_execution_time
def process_match_value_and_lpu(budget_item: str, 
                                lpu_file: str, 
                                lpu_column: str, 
                                threshold: int = 80, 
                                scorer: Callable = fuzz.token_set_ratio):
    """
    Processa os dados de orçamentos e LPU, realizando uma busca fuzzy entre as colunas especificadas.

    Args:
        budget_item (str): Item de orçamento a ser processado.
        lpu_file (str): Caminho para o arquivo de LPU.
        lpu_column (str): Nome da coluna na base de LPU a ser usada como choices.
        threshold (int): Percentual mínimo de match para considerar válido. Default é 80.
        scorer (Callable): Função de pontuação fuzzy a ser usada. Default é fuzz.ratio.

    Returns:
        pd.DataFrame: DataFrame de orçamentos com uma nova coluna contendo os melhores matches.
    """
    # Ler os arquivos
    lpu_df = pd.read_excel(lpu_file)

    # Garantir que as colunas existem
    if lpu_column not in lpu_df.columns:
        raise ValueError(f"Coluna '{lpu_column}' não encontrada na base de LPU.")

    # Extrair os choices da base de LPU
    choices = lpu_df[lpu_column].dropna().tolist()
    
    # budget_df = budget_df.iloc[:100]

    # Aplicar fuzzy_match para cada valor na coluna de orçamentos em um único apply
    matches = fuzzy_match(value=budget_item, 
                          choices=choices, 
                          top_matches=1, 
                          threshold=threshold, 
                          scorer=scorer)

    # Atribuir os valores às colunas do DataFrame
    pprint(matches)
    
    return matches


@measure_execution_time
def process_budget_and_lpu(budget_file: str, 
                           lpu_file: str, 
                           budget_column: str, 
                           lpu_column: str, 
                           threshold: int = 80, 
                           scorer: Callable = fuzz.token_set_ratio):
    """
    Processa os dados de orçamentos e LPU, realizando uma busca fuzzy entre as colunas especificadas.

    Args:
        budget_file (str): Caminho para o arquivo de orçamentos.
        lpu_file (str): Caminho para o arquivo de LPU.
        budget_column (str): Nome da coluna na base de orçamentos a ser percorrida.
        lpu_column (str): Nome da coluna na base de LPU a ser usada como choices.
        threshold (int): Percentual mínimo de match para considerar válido. Default é 80.
        scorer (Callable): Função de pontuação fuzzy a ser usada. Default é fuzz.ratio.

    Returns:
        pd.DataFrame: DataFrame de orçamentos com uma nova coluna contendo os melhores matches.
    """
    # Ler os arquivos
    budget_df = pd.read_excel(budget_file)
    lpu_df = pd.read_excel(lpu_file)

    # Garantir que as colunas existem
    if budget_column not in budget_df.columns:
        raise ValueError(f"Coluna '{budget_column}' não encontrada na base de orçamentos.")
    if lpu_column not in lpu_df.columns:
        raise ValueError(f"Coluna '{lpu_column}' não encontrada na base de LPU.")

    # Extrair os choices da base de LPU
    choices = lpu_df[lpu_column].dropna().tolist()
    
    # budget_df = budget_df.iloc[:100]

    # Aplicar fuzzy_match para cada valor na coluna de orçamentos em um único apply
    matches = budget_df[budget_column].apply(
        lambda x: fuzzy_match(value=x, 
                              choices=choices, 
                              top_matches=1, 
                              threshold=threshold, 
                              scorer=scorer)
    )

    # Atribuir os valores às colunas do DataFrame
    budget_df['Melhor Match'] = matches.apply(lambda x: x.choice if x else None)
    budget_df['Percentual Match'] = matches.apply(lambda x: x.score if x else None)

    # Salvar o resultado em um arquivo Excel
    output_file = "data/outputs/02_BASE_RESULTADO_VALIDADOR_LPU.xlsx"
    export_data(data=budget_df, file_path=output_file, index=False)
    print(f"Resultado salvo em: {output_file}")

    return budget_df

if __name__ == "__main__":
    
    # Exemplo de uso
    budget_file = "data/outputs/01_BASE_RESULTADO_ORCAMENTOS_CONCATENADOS.xlsx"
    lpu_file = "data/inputs/lpu/BASE_LPU.xlsx"
    budget_column = "NOME"
    lpu_column = "Item"
    threshold = 85

    result_df = process_budget_and_lpu(budget_file=budget_file, 
                                       lpu_file=lpu_file, 
                                       budget_column=budget_column, 
                                       lpu_column=lpu_column, 
                                       threshold=threshold)
    print("-"*50)
    
    # Executando o teste para um único valor
    result_value = process_match_value_and_lpu(budget_item="Serviço de Instalação de Ar Condicionado Tipo Split", 
                                               lpu_file=lpu_file, 
                                               lpu_column=lpu_column,
                                               threshold=threshold, 
                                               scorer=fuzz.token_sort_ratio)
    print("-"*50)
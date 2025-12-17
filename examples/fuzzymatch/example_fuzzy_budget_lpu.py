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

# Adicionar src ao path
base_dir = Path(__file__).parents[2]
sys.path.insert(0, str(Path(base_dir, "src")))

import pandas as pd
from utils.fuzzy.fuzzy_validations import fuzzy_match

def process_budget_and_lpu(budget_file: str, lpu_file: str, budget_column: str, lpu_column: str, threshold: int = 80):
    """
    Processa os dados de orçamentos e LPU, realizando uma busca fuzzy entre as colunas especificadas.

    Args:
        budget_file (str): Caminho para o arquivo de orçamentos.
        lpu_file (str): Caminho para o arquivo de LPU.
        budget_column (str): Nome da coluna na base de orçamentos a ser percorrida.
        lpu_column (str): Nome da coluna na base de LPU a ser usada como choices.
        threshold (int): Percentual mínimo de match para considerar válido. Default é 80.

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

    # Aplicar fuzzy_match para cada valor na coluna de orçamentos
    budget_df['Melhor Match'] = budget_df[budget_column].apply(
        lambda x: fuzzy_match(x, choices, top_matches=1, threshold=threshold)
    )

    return budget_df

if __name__ == "__main__":
    # Exemplo de uso
    budget_file = "data/outputs/01_BASE_RESULTADO_ORCAMENTOS_CONCATENADOS.xlsx"
    lpu_file = "data/inputs/lpu/BASE_LPU.xlsx"
    budget_column = "NOME"
    lpu_column = "Item"

    result_df = process_budget_and_lpu(budget_file, lpu_file, budget_column, lpu_column)
    print(result_df.head())
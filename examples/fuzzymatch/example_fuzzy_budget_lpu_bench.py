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
import time
import json

import pandas as pd
from fuzzywuzzy import fuzz

# Adicionar src ao path
base_dir = Path(__file__).parents[2]
sys.path.insert(0, str(Path(base_dir, "src")))

from utils.fuzzy.fuzzy_validations import fuzzy_match
from utils.data.data_functions import export_to_json


def benchmark_fuzzy_match(
    budget_file: str,
    lpu_file: str,
    budget_column: str,
    lpu_column: str,
    threshold: int = 80,
    samples: int = None,
):
    """
    Realiza um benchmark entre as implementações de fuzzy_match usando fuzzywuzzy e rapidfuzz.
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

    # Selecionar um exemplo de orçamento
    if samples:
        budget_df = budget_df.iloc[:samples]

    # Benchmark para fuzzywuzzy
    start_time = time.time()
    result_fuzzywuzzy = budget_df[budget_column].apply(
        lambda x: fuzzy_match(
            value=x, choices=choices, top_matches=1, threshold=threshold, library="fuzzywuzzy"
        )
    )
    time_fuzzywuzzy = time.time() - start_time

    # Benchmark para rapidfuzz
    start_time = time.time()
    result_rapidfuzz = budget_df[budget_column].apply(
        lambda x: fuzzy_match(
            value=x, choices=choices, top_matches=1, threshold=threshold, library="rapidfuzz"
        )
    )
    time_rapidfuzz = time.time() - start_time

    # Resultados
    print("Benchmark Results:")
    print("FuzzyWuzzy:")
    pprint(f"Results: {result_fuzzywuzzy}")
    print(f"Execution Time: {time_fuzzywuzzy:.6f} seconds")
    print("RapidFuzz:")
    pprint(f"Results: {result_rapidfuzz}")
    print(f"Execution Time: {time_rapidfuzz:.6f} seconds")
    print(f"Difference in Execution Time: {time_fuzzywuzzy - time_rapidfuzz:.6f} seconds")

    # Salvar os resultados em um arquivo JSON
    output_file = Path(Path(__file__).parent, "data/outputs/benchmark_results.json")
    results = {
        "fuzzywuzzy": {
            "results": result_fuzzywuzzy.to_dict(),
            "execution_time": time_fuzzywuzzy,
        },
        "rapidfuzz": {
            "results": result_rapidfuzz.to_dict(),
            "execution_time": time_rapidfuzz,
        },
        "execution_time_difference": time_fuzzywuzzy - time_rapidfuzz,
    }

    export_to_json(results, output_file, create_dirs=True)
    print(f"Resultados do benchmark salvos em: {output_file}")


if __name__ == "__main__":
    # Exemplo de uso
    budget_file = "data/outputs/01_BASE_RESULTADO_ORCAMENTOS_CONCATENADOS.xlsx"
    lpu_file = "data/inputs/lpu/BASE_LPU.xlsx"
    budget_column = "NOME"
    lpu_column = "Item"
    threshold = 85
    samples = None  # Defina o número de amostras para o benchmark, ou None para usar todas

    benchmark_fuzzy_match(
        budget_file=budget_file,
        lpu_file=lpu_file,
        budget_column=budget_column,
        lpu_column=lpu_column,
        threshold=threshold,
        samples=samples,
    )

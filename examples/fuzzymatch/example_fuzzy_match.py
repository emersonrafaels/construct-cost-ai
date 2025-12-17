"""
Realiza o uso do Módulo: fuzzy_validations
------------------------

Responsável por realizar validações fuzzy, como encontrar matches aproximados
em listas e DataFrames, utilizando o módulo fuzzy_validations.

Este módulo foi projetado para suportar validações aproximadas em diferentes contextos.
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

from utils.fuzzy.fuzzy_validations import (
    fuzzy_match,
    top_n_fuzzy_matches,
    best_fuzzy_match,
    filter_fuzzy_matches,
)
import pandas as pd

if __name__ == "__main__":
    # Exemplo 1: fuzzy_match com uma lista
    choices = ["Residencial", "Comercial", "Industrial", "Hospitalar"]
    value = "Resindencial"
    result = fuzzy_match(value, choices, threshold=85)
    print(f"Fuzzy match encontrado: {result}")

    # Exemplo 2: top_n_fuzzy_matches com uma lista
    top_matches = top_n_fuzzy_matches(value, choices, n=3)
    print("Top 3 matches:")
    for match in top_matches:
        print(match)

    # Exemplo 3: best_fuzzy_match com uma lista
    best_match = best_fuzzy_match("Hospitar", choices)
    print(f"Melhor match: {best_match}")

    # Exemplo 4: filter_fuzzy_matches com uma lista
    filtered_matches = filter_fuzzy_matches(value, choices, threshold=80)
    print("Valores filtrados:")
    for match in filtered_matches:
        print(match)

    # Exemplo 5: fuzzy_match com DataFrame
    df = pd.DataFrame(
        {
            "Categoria": ["Residencial", "Comercial", "Industrial", "Hospitalar"],
            "Descrição": ["Casa", "Loja", "Fábrica", "Clínica"],
        }
    )
    df["Fuzzy Match"] = df["Categoria"].apply(
        lambda x: fuzzy_match("Resindencial", [x], threshold=85)
    )
    print(df)

    # Exemplo 6: Filtrando DataFrame com fuzzy_match
    filtered_df = df[
        df["Categoria"].apply(lambda x: fuzzy_match("Resindencial", [x], threshold=85))
    ]
    print(filtered_df)

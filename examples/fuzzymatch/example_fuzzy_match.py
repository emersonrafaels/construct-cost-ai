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
__status__ = "Development"

import sys
from pathlib import Path

import pandas as pd

# Adicionar src ao path
base_dir = Path(__file__).parents[2]
sys.path.insert(0, str(Path(base_dir, "src")))

from utils.fuzzy.fuzzy_validations import (
    fuzzy_match,
)


def example_fuzzy_match_list():
    """
    Exemplo de uso da função fuzzy_match com uma lista.
    """
    choices = ["Residencial", "Comercial", "Industrial", "Hospitalar"]
    value = "Resindencial"
    result = fuzzy_match(value, choices, top_matches=1, threshold=85)
    print(f"Fuzzy match encontrado: {result}")


def example_top_n_fuzzy_matches():
    """
    Exemplo de uso da função fuzzy_match para obter os top N matches com uma lista.
    """
    choices = ["Residencial", "Comercial", "Industrial", "Hospitalar"]
    value = "Resindencial"
    top_matches = fuzzy_match(value, choices, top_matches=3, threshold=50)
    print("Top 3 matches:")
    for match in top_matches:
        print(match)


def example_fuzzy_match_dataframe():
    """
    Exemplo de uso da função fuzzy_match com um DataFrame.
    """
    df = pd.DataFrame(
        {
            "Categoria": ["Residencial", "Comercial", "Industrial", "Hospitalar"],
            "Descrição": ["Casa", "Loja", "Fábrica", "Clínica"],
        }
    )
    df["Fuzzy Match"] = df["Categoria"].apply(
        lambda x: fuzzy_match("Resindencial", [x], top_matches=1, threshold=85)
    )
    print(df)


def example_filter_dataframe():
    """
    Exemplo de filtragem de um DataFrame com fuzzy_match.
    """
    df = pd.DataFrame(
        {
            "Categoria": ["Residencial", "Comercial", "Industrial", "Hospitalar"],
            "Descrição": ["Casa", "Loja", "Fábrica", "Clínica"],
        }
    )
    filtered_df = df[
        df["Categoria"].apply(
            lambda x: fuzzy_match("Resindencial", [x], top_matches=1, threshold=85) is not None
        )
    ]
    print(filtered_df)


def example_fuzzy_match_with_dataframes():
    """
    Exemplo de uso da função fuzzy_match com dois DataFrames: um com valores e outro com choices.
    """
    # DataFrame com valores
    df_values = pd.DataFrame(
        {
            "Valores": ["Residencial", "Comercial", "Industrial", "Hospitalar", "Educacional"],
        }
    )

    # DataFrame com choices
    df_choices = pd.DataFrame(
        {
            "Choices": ["Residencial", "Comercial", "Industrial", "Hospitalar"],
        }
    )

    # Aplicar fuzzy_match para encontrar o melhor match para cada valor
    df_values["Melhor Match"] = df_values["Valores"].apply(
        lambda x: fuzzy_match(x, df_choices["Choices"].tolist(), top_matches=1, threshold=80)
    )

    print("DataFrame com os melhores matches:")
    print(df_values)

    # Filtrar valores que possuem matches acima do threshold
    filtered_values = df_values[df_values["Melhor Match"].apply(lambda x: x is not None)]

    print("DataFrame filtrado com matches válidos:")
    print(filtered_values)


if __name__ == "__main__":
    example_fuzzy_match_list()
    example_top_n_fuzzy_matches()
    example_fuzzy_match_dataframe()
    example_filter_dataframe()
    example_fuzzy_match_with_dataframes()

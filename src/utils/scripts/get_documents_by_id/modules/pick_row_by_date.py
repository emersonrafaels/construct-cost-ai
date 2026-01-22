import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.append(Path(__file__).parents[0])

from modules.datetime_utils import preprocess_datetime_columns


def pick_row(
    df: pd.DataFrame,
    strategy: list[str] = ["between_else_nearest"],
    strategy_options: list[str] = ["between", "nearest", "last", "between_else_nearest"],
    strict: bool = False,
    prefer: str = "DATA_INCLUSAO_DOC",
    start_col: str = "DATA_INICIO_REAL",
    end_col: str = "DATA_FIM_REAL",
    between_preference: str = "last",
) -> pd.Series:
    """
    Seleciona uma linha de um DataFrame com base na estratégia fornecida e retorna a linha com a DATA_INCLUSAO_DOC mais próxima do intervalo.

    Args:
        df (pd.DataFrame): DataFrame já filtrado para o contexto desejado.
        strategy (list[str]): Lista de estratégias em ordem de prioridade.
        strategy_options (list[str]): Estratégias permitidas para validação.
        strict (bool): Se True, aplica rigorosamente a lista de estratégias.
        prefer (str): Coluna preferida para desempate ou ordenação.
        start_col (str): Nome da coluna para a data de início.
        end_col (str): Nome da coluna para a data de fim.
        between_preference (str): Define se seleciona a primeira ('first') ou última ('last') linha para a estratégia 'between'.

    Returns:
        pd.Series: Linha selecionada do DataFrame.

    Raises:
        ValueError: Se nenhuma linha válida for encontrada no modo estrito.
    """
    # Preprocess datetime columns to ensure resilience
    df = preprocess_datetime_columns(df, [prefer, start_col, end_col])

    print("\nIniciando pick_row com as seguintes estratégias:", strategy)
    print("-" * 50)

    # Valida as opções de estratégia
    for strat in strategy:
        if strat not in strategy_options:
            raise ValueError(
                f"Estratégia inválida: {strat}. Estratégias permitidas são {strategy_options}."
            )

    print("DataFrame recebido:")
    print(df)
    print("-" * 50)

    # Define a lista de estratégias a ser usada
    strategies_to_use = (
        strategy if strict else strategy + [s for s in strategy_options if s not in strategy]
    )
    print("Estratégias a serem usadas:", strategies_to_use)
    print("-" * 50)

    # Itera pela lista de estratégias em ordem de prioridade
    for strat in strategies_to_use:
        print(f"Avaliando estratégia: {strat}")
        print("-" * 50)

        if strat == "last":
            # Ordena pela coluna preferida e retorna a última linha
            selected_row = df.sort_values(prefer).iloc[-1]
            print("Estratégia 'last' selecionou a seguinte linha:")
            print(selected_row)
            print("-" * 50)
            return selected_row

        if strat in ["between", "between_else_nearest"]:
            # Identifica linhas onde DATA_INCLUSAO_DOC está dentro do intervalo
            between_mask = (df[start_col] <= df[prefer]) & (df[prefer] <= df[end_col])
            candidates = df[between_mask]

            print("Linhas candidatas para 'between':")
            print(candidates)
            print("-" * 50)

            if not candidates.empty:
                # Retorna a linha com base na preferência ('first' ou 'last')
                if between_preference == "first":
                    selected_row = candidates.sort_values(prefer).iloc[0]
                else:  # Default to 'last'
                    selected_row = candidates.sort_values(prefer).iloc[-1]

                print(f"Estratégia 'between' selecionou a seguinte linha ({between_preference}):")
                print(selected_row)
                print("-" * 50)
                return selected_row

            if strat == "between":
                # Se o modo estrito estiver ativado, levanta um erro se nenhuma linha for encontrada
                if strict:
                    raise ValueError("Nenhuma linha contém DATA_INCLUSAO_DOC dentro do intervalo.")

        if strat in ["nearest", "between_else_nearest"]:
            # Calcula a distância para o intervalo de cada linha
            start = df[start_col]
            end = df[end_col]
            inclusion = df[prefer]

            dist = np.where(
                inclusion < start,
                (
                    start - inclusion
                ).dt.days,  # Distância se DATA_INCLUSAO_DOC for antes do intervalo
                np.where(
                    inclusion > end, (inclusion - end).dt.days, 0
                ),  # Distância se for depois do intervalo
            )
            df["_dist_days"] = dist

            print("Distâncias calculadas para 'nearest':")
            print(df[[prefer, start_col, end_col, "_dist_days"]])
            print("-" * 50)

            # Ordena pela distância e pela coluna preferida, então retorna a linha mais próxima
            df = df.sort_values(["_dist_days", prefer], ascending=[True, True])
            best = df.iloc[0]
            print("Estratégia 'nearest' selecionou a seguinte linha:")
            print(best)
            print("-" * 50)
            return best.drop(labels=["_dist_days"])

    # Se nenhuma linha válida for encontrada e o modo estrito estiver ativado, levanta um erro
    if strict:
        raise ValueError("Nenhuma linha válida encontrada para as estratégias fornecidas.")

    # Comportamento padrão: retorna uma Series vazia se nenhuma linha for encontrada
    print("Nenhuma linha válida encontrada. Retornando Series vazia.")
    print("-" * 50)
    return pd.Series()

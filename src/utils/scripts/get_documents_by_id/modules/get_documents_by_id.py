import sys
from pathlib import Path

import pandas as pd

sys.path.append(Path(__file__).parents[0])

from modules.pick_row_by_date import pick_row


def orchestra_pick_row_by_date(
    df: pd.DataFrame,
    strategy: list[str],
    strict: bool = False,
    upe_col: str = "UPE",
    date_col: str = "DATA_INCLUSAO_DOC",
    start_col: str = "DATA_INICIO_REAL",
    end_col: str = "DATA_FIM_REAL",
    prefer_col: str = "DATA_INCLUSAO_DOC",
    between_preference: str = "last",
) -> pd.DataFrame:
    """
    Gera um DataFrame final contendo as linhas selecionadas para cada UPE, usando DATA_INCLUSAO_DOC como target.

    Args:
        df (pd.DataFrame): DataFrame contendo o conjunto de dados original.
        strategy (list[str]): Lista de estratégias a serem aplicadas para seleção de linhas.
        strict (bool): Se True, aplica rigorosamente a lista de estratégias.
        upe_col (str): Nome da coluna que identifica as UPEs.
        date_col (str): Nome da coluna que contém as datas alvo.
        start_col (str): Nome da coluna que contém as datas de início.
        end_col (str): Nome da coluna que contém as datas de fim.
        prefer_col (str): Nome da coluna preferida para seleção de linhas.
        between_preference (str): Define se seleciona a primeira ('first') ou última ('last') linha para a estratégia 'between'.

    Returns:
        pd.DataFrame: DataFrame final com as colunas selecionadas e a estratégia usada.
    """
    selected_rows = []

    # Itera sobre cada UPE único no DataFrame
    for upe in df[upe_col].unique():
        try:
            # Filtra o DataFrame para o UPE atual
            filtered_df = df[df[upe_col] == upe]

            print(f"UPE atual: {upe}")

            # Itera pelas estratégias para encontrar a linha válida
            for strat in strategy:
                try:
                    selected_row = pick_row(
                        filtered_df,
                        strategy=[strat],
                        strict=strict,
                        prefer=prefer_col,
                        start_col=start_col,
                        end_col=end_col,
                        between_preference=between_preference,
                    )

                    # Adiciona a estratégia usada na linha selecionada
                    selected_row = selected_row.to_dict()
                    selected_row["STRATEGY_USED"] = strat
                    selected_rows.append(selected_row)
                    break

                except ValueError:
                    continue

        except ValueError as e:
            print(f"Erro ao processar UPE {upe}: {e}")

    # Cria um DataFrame com as linhas selecionadas
    final_df = pd.DataFrame(selected_rows)

    # Remove duplicatas por UPE, mantendo a linha com a DATA_INCLUSAO_DOC mais recente
    final_df = final_df.sort_values(date_col, ascending=False).drop_duplicates(
        subset=upe_col, keep="first"
    )

    return final_df

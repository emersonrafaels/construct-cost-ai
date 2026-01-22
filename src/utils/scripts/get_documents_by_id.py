import numpy as np
import pandas as pd
from pathlib import Path


def make_synthetic_upe_dataset(
    n_upe: int = 8,
    rows_per_upe: tuple[int, int] = (2, 6),
    seed: int = 42,
) -> pd.DataFrame:
    """
    Gera um conjunto de dados sintético para UPEs (Unidades de Planejamento e Execução).

    Args:
        n_upe (int): Número de UPEs a serem geradas.
        rows_per_upe (tuple[int, int]): Faixa de linhas por UPE.
        seed (int): Semente aleatória para reprodutibilidade.

    Returns:
        pd.DataFrame: Conjunto de dados sintético com as colunas DOCUMENTO, UPE, DATA_INCLUSAO_DOC, etc.
    """
    rng = np.random.default_rng(seed)

    base_upe = rng.integers(190000, 199999, size=n_upe)
    fornecedores = [
        "KALFER CONSTRUÇÃO",
        "PBA ENGENHARIA",
        "JAPJ CONSTRUÇÕES",
        "CONSTRUTORA FATECRIL",
        "L MENDES CONSTRUÇÕES",
        "HBT ENGENHARIA",
        "SISTEL SISTEMAS",
        "BWT ENGENHARIA",
        "MANFER ENG MANUT",
        "EXPLORE CONSTRUTORA",
        "DR CONSTRUÇÕES",
        "ELLO COSTA LIMA",
    ]

    rows = []
    doc_id = 400000

    for upe in base_upe:
        k = int(rng.integers(rows_per_upe[0], rows_per_upe[1] + 1))
        start = pd.Timestamp("2024-01-01") + pd.Timedelta(days=int(rng.integers(0, 500)))
        duration_days = int(rng.integers(10, 120))
        end = start + pd.Timedelta(days=duration_days)

        for _ in range(k):
            inclusion_offset = int(rng.integers(-15, 45))
            inclusion = (
                start
                + pd.Timedelta(days=inclusion_offset)
                + pd.Timedelta(
                    hours=int(rng.integers(0, 24)),
                    minutes=int(rng.integers(0, 60)),
                    seconds=int(rng.integers(0, 60)),
                )
            )

            rows.append(
                {
                    "DOCUMENTO": doc_id,
                    "UPE": int(upe),
                    "DATA_INCLUSAO_DOC": inclusion,
                    "DATA_INICIO_REAL": start.normalize(),
                    "DATA_FIM_REAL": end.normalize(),
                    "FORNECEDOR": rng.choice(fornecedores),
                }
            )

            doc_id += int(rng.integers(1, 80))

    df = pd.DataFrame(rows)
    df = df.sort_values(["UPE", "DATA_INICIO_REAL", "DATA_INCLUSAO_DOC"]).reset_index(drop=True)
    return df


def pick_row(
    df: pd.DataFrame,
    strategy: list[str] = ["between_else_nearest"],
    strategy_options: list[str] = ["between", "nearest", "last", "between_else_nearest"],
    strict: bool = False,
    prefer: str = "DATA_INCLUSAO_DOC",
    start_col: str = "DATA_INICIO_REAL",
    end_col: str = "DATA_FIM_REAL",
    between_preference: str = "last",  # New parameter to specify 'first' or 'last' for 'between'
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
    print("\nIniciando pick_row com as seguintes estratégias:", strategy)
    print("-" * 50)

    # Valida as opções de estratégia
    for strat in strategy:
        if strat not in strategy_options:
            raise ValueError(f"Estratégia inválida: {strat}. Estratégias permitidas são {strategy_options}.")

    print("DataFrame recebido:")
    print(df)
    print("-" * 50)

    # Define a lista de estratégias a ser usada
    strategies_to_use = strategy if strict else strategy + [s for s in strategy_options if s not in strategy]
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
                (start - inclusion).dt.days,  # Distância se DATA_INCLUSAO_DOC for antes do intervalo
                np.where(inclusion > end, (inclusion - end).dt.days, 0),  # Distância se for depois do intervalo
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


def generate_final_dataframe(
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
        pd.DataFrame: DataFrame final com as colunas selecionadas.
    """
    selected_rows = []

    # Itera sobre cada UPE único no DataFrame
    for upe in df[upe_col].unique():
        try:
            # Filtra o DataFrame para o UPE atual
            filtered_df = df[df[upe_col] == upe]

            print(f"UPE atual: {upe}")

            # Seleciona a linha para o UPE atual
            selected_row = pick_row(
                filtered_df,
                strategy=strategy,
                strict=strict,
                prefer=prefer_col,
                start_col=start_col,
                end_col=end_col,
                between_preference="last",
            )
            # Adiciona a linha selecionada à lista
            selected_rows.append(selected_row)
        except ValueError as e:
            print(f"Aviso: {e}")

    # Cria um DataFrame com as linhas selecionadas
    final_df = pd.DataFrame(selected_rows)

    # Remove duplicatas por UPE, mantendo a linha com a DATA_INCLUSAO_DOC mais recente
    final_df = final_df.sort_values(date_col, ascending=False).drop_duplicates(
        subset=upe_col, keep="first"
    )

    return final_df


def main():
    """
    Função principal para demonstrar o uso do script.
    """
    # Parâmetros hardcoded
    strategy = ["between", "nearest", "last"]
    strict = False
    upe_col = "UPE"
    date_col = "DATA_INCLUSAO_DOC"
    start_col = "DATA_INICIO_REAL"
    end_col = "DATA_FIM_REAL"
    prefer_col = "DATA_INCLUSAO_DOC"
    between_preference = "last"

    # Diretório atual
    current_dir = Path(__file__).parents[0]

    # Gera o conjunto de dados sintético
    df = make_synthetic_upe_dataset(n_upe=6, rows_per_upe=(3, 6), seed=7)

    # Salva o conjunto de dados gerado para análise
    generated_file = current_dir / "dados_gerados.xlsx"
    df.to_excel(generated_file, index=False)
    print(f"Conjunto de dados gerado salvo em '{generated_file}'.")

    # Gera o DataFrame final
    df_result = generate_final_dataframe(
        df,
        strategy=strategy,
        strict=strict,
        upe_col=upe_col,
        date_col=date_col,
        start_col=start_col,
        end_col=end_col,
        prefer_col=prefer_col,
        between_preference=between_preference,
    )

    # Salva o DataFrame final para análise
    final_file = current_dir / "dados_finais.xlsx"
    df_result.to_excel(final_file, index=False)
    print(f"DataFrame final salvo em '{final_file}'.")

    print("\nDataFrame final:")
    print(df_result)


if __name__ == "__main__":
    main()

import pandas as pd

def calculate_total_item(
    df: pd.DataFrame, column_total_value: str, column_quantity: str, column_unit_price: str
) -> pd.DataFrame:
    """
    Calcula o valor total orçado em um DataFrame.

    Args:
        df (pd.DataFrame): DataFrame contendo os dados.
        column_total_value (str): Nome da coluna de valor total orçado.
        column_quantity (str): Nome da coluna de quantidade.
        column_unit_price (str): Nome da coluna de preço unitário.

    Returns:
        pd.DataFrame: DataFrame atualizado com a coluna de valor total orçado calculada ou convertida.
    """

    # Verifica se a coluna de valor total orçado existe
    if column_total_value not in df.columns:

        # Se não existe, ele calcula usando quantidade * preço unitário
        df[column_total_value] = df[column_quantity] * df[column_unit_price]
    else:
        # Nesse caso a coluna existe, então:
        # 1 - Garante que está no formato numérico
        df[column_total_value] = pd.to_numeric(df[column_total_value], errors="coerce")

        # Filtra linhas onde o valor total é nulo ou menor/igual a zero
        mask = df[column_total_value].isna() | (df[column_total_value] <= 0)

        # 2 - Recalcula o valor total apenas para essas linhas
        df.loc[mask, column_total_value] = (
            df.loc[mask, column_quantity] * df.loc[mask, column_unit_price]
        )

    return df
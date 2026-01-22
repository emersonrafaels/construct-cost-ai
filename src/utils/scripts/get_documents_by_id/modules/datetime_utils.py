import pandas as pd

def ensure_datetime(series: pd.Series) -> pd.Series:
    """
    Converts a pandas Series to datetime, handling strings and null values gracefully.

    Args:
        series (pd.Series): The Series to convert.

    Returns:
        pd.Series: The converted Series with datetime values.
    """
    return pd.to_datetime(series, errors="coerce")

def preprocess_datetime_columns(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    """
    Ensures specified columns in a DataFrame are converted to datetime.

    Args:
        df (pd.DataFrame): The DataFrame to process.
        columns (list[str]): List of column names to convert to datetime.

    Returns:
        pd.DataFrame: The DataFrame with datetime columns processed.
    """
    for col in columns:
        if col in df.columns:
            df[col] = ensure_datetime(df[col])
    return df
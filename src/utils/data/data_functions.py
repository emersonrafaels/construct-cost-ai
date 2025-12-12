from pathlib import Path
from typing import Dict, List, Optional, Union

import pandas as pd


def read_data(file_path: Union[str, Path]) -> pd.DataFrame:
    """
    Reads data from various file formats using the file extension to determine the appropriate method.

    Args:
        file_path (Union[str, Path]): Path to the file to be read

    Returns:
        pd.DataFrame: DataFrame containing the read data

    Raises:
        ValueError: If file extension is not supported
        FileNotFoundError: If file doesn't exist
    """
    file_path = Path(file_path)

    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    extension = file_path.suffix.lower()

    readers = {
        ".csv": pd.read_csv,
        ".xlsx": pd.read_excel,
        ".xls": pd.read_excel,
        ".json": pd.read_json,
        ".parquet": pd.read_parquet,
        ".feather": pd.read_feather,
        ".pkl": pd.read_pickle,
    }

    reader = readers.get(extension)
    if reader is None:
        raise ValueError(f"Unsupported file extension: {extension}")

    try:
        return reader(file_path)
    except Exception as e:
        raise RuntimeError(f"Error reading file {file_path}: {str(e)}")


def export_data(
    data: Union[pd.DataFrame, Dict[str, pd.DataFrame]],
    file_path: Union[str, Path],
    create_dirs: bool = True,
    **kwargs,
) -> None:
    """
    Exports data to various formats, with support for multiple sheets in Excel.

    Args:
        data: DataFrame or dict of DataFrames for Excel multi-sheet
        file_path (Union[str, Path]): Path where to save the file
        create_dirs (bool): Whether to create directories if they don't exist
        **kwargs: Additional arguments passed to the pandas export function

    Raises:
        ValueError: If file extension is not supported
    """
    file_path = Path(file_path)

    if create_dirs:
        file_path.parent.mkdir(parents=True, exist_ok=True)

    extension = file_path.suffix.lower()

    exporters = {
        ".csv": lambda df, path: df.to_csv(path, **kwargs),
        ".xlsx": lambda df, path: (
            df.to_excel(path, **kwargs)
            if isinstance(df, pd.DataFrame)
            else (
                pd.ExcelWriter(path, engine="openpyxl").__enter__().close()
                if all(isinstance(d, pd.DataFrame) for d in df.values())
                and all(
                    sheet.to_excel(path, sheet_name=name, **kwargs) for name, sheet in df.items()
                )
                else None
            )
        ),
        ".json": lambda df, path: df.to_json(path, **kwargs),
        ".parquet": lambda df, path: df.to_parquet(path, **kwargs),
        ".feather": lambda df, path: df.to_feather(path, **kwargs),
        ".pkl": lambda df, path: df.to_pickle(path, **kwargs),
    }

    exporter = exporters.get(extension)
    if exporter is None:
        raise ValueError(f"Unsupported file extension: {extension}")

    try:
        exporter(data, file_path)
    except Exception as e:
        raise RuntimeError(f"Error exporting to {file_path}: {str(e)}")


# Example usage:
if __name__ == "__main__":
    # Reading example
    try:
        df = read_data("sample.csv")
        print("Data read successfully")
    except Exception as e:
        print(f"Error reading data: {e}")

    # Single DataFrame export example
    try:
        df = pd.DataFrame({"A": [1, 2], "B": [3, 4]})
        export_data(df, "output/single_sheet.xlsx", create_dirs=True)
        print("Single sheet exported successfully")
    except Exception as e:
        print(f"Error exporting single sheet: {e}")

    # Multi-sheet Excel export example
    try:
        sheets = {
            "Sheet1": pd.DataFrame({"A": [1, 2], "B": [3, 4]}),
            "Sheet2": pd.DataFrame({"C": [5, 6], "D": [7, 8]}),
        }
        export_data(sheets, "output/multi_sheet.xlsx", create_dirs=True)
        print("Multiple sheets exported successfully")
    except Exception as e:
        print(f"Error exporting multiple sheets: {e}")

"""
Módulo: data_io
----------------

Fornece funções utilitárias padronizadas para leitura e escrita de dados em
diferentes formatos de dados (excel, csv, parquet, etc) utilizados no ecossistema do Verificador Inteligente de
Orçamentos de Obras.

Este módulo abstrai a complexidade de múltiplos formatos (CSV, Excel,
Parquet, JSON, Feather, Pickle), garantindo uma interface consistente para
todas as etapas do pipeline — desde prototipação local até uso em produção.

🧩 Funcionalidades principais:
------------------------------

1) read_data(file_path, sheet_name=None, header=0)
   - Detecta automaticamente o método de leitura a partir da extensão.
   - Suporta:
       .csv, .xlsx, .xls, .json, .parquet, .feather, .pkl
   - Permite leitura de abas específicas em arquivos Excel.
   - Utilizado por:
       • Parsing de orçamentos
       • Testes unitários
       • Pipelines determinísticos

2) export_data(data, file_path, create_dirs=True)
   - Exporta DataFrames ou múltiplos DataFrames (multi-sheet Excel).
   - Cria diretórios automaticamente, quando necessário.
   - Suporta:
       .csv, .xlsx, .json, .parquet, .feather, .pkl
   - Utilizado por:
       • Geração de relatórios técnicos
       • Salvamento de artefatos do verificador
       • Outputs intermediários do pipeline

🎯 Motivação e valor:
---------------------
- Unifica a manipulação de dados em todo o projeto.
- Reduz duplicação de código em parseadores, validadores e testes.
- Facilita a troca futura de formato sem alterar o restante do pipeline.
- Padroniza I/O para rodar em ambientes diversos (local, AWS, CI/CD).


📁 Localização:
--------------
Faz parte da camada utilitária `utils/`.

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

from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

import pandas as pd


def read_data(
    file_path: Union[str, Path],
    sheet_name: Optional[Union[str, int]] = None,
    header: Optional[Union[int, List[int]]] = 0,
) -> pd.DataFrame:
    """
    Reads data from various file formats using the file extension to determine the appropriate method.

    Args:
        file_path (Union[str, Path]): Path to the file to be read.
        sheet_name (Optional[Union[str, int]]): Name or index of the sheet to read (for Excel files). Default is None.
        header (Optional[Union[int, List[int]]]): Row number(s) to use as the column names. Default is 0.

    Returns:
        pd.DataFrame: DataFrame containing the read data.

    Raises:
        ValueError: If file extension is not supported.
        FileNotFoundError: If file doesn't exist.
    """
    file_path = Path(file_path)

    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    # Obtendo a extensão do dado recebido
    extension = file_path.suffix.lower()

    # Definindo os leitores disponíveis no data functions
    readers = {
        ".csv": lambda path: pd.read_csv(path, header=header),
        ".xlsx": lambda path: pd.read_excel(path, sheet_name=sheet_name, header=header),
        ".xls": lambda path: pd.read_excel(path, sheet_name=sheet_name, header=header),
        ".xlsm": lambda path: pd.read_excel(
            path, sheet_name=sheet_name, header=header
        ),  # Added support for .xlsm files
        ".json": lambda path: pd.read_json(path),
        ".parquet": lambda path: pd.read_parquet(path),
        ".feather": lambda path: pd.read_feather(path),
        ".pkl": lambda path: pd.read_pickle(path),
    }

    reader = readers.get(extension)
    if reader is None:
        raise ValueError(f"Unsupported file extension: {extension}")

    try:
        return reader(file_path)
    except Exception as e:
        print(f"Error reading file {file_path}: {str(e)}")


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
            else (_export_multiple_sheets(df, path, **kwargs))
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


def _export_multiple_sheets(data: Dict[str, pd.DataFrame], path: Union[str, Path], **kwargs):
    """
    Helper function to export multiple sheets to an Excel file.

    Args:
        data: Dictionary of DataFrames to export.
        path: Path to the Excel file.
        **kwargs: Additional arguments for pandas to_excel.
    """
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        for sheet_name, sheet_data in data.items():
            sheet_data.to_excel(writer, sheet_name=sheet_name, index=False, **kwargs)


def transform_case(
    df: pd.DataFrame,
    to_upper: bool = True,
    columns: Union[bool, List[str]] = False,
    cells: Union[bool, List[Tuple[int, int]]] = False,
) -> pd.DataFrame:
    """
    Transforma valores de texto em um DataFrame para uppercase ou lowercase, com opções para todas as colunas ou células específicas.

    Args:
        df (pd.DataFrame): DataFrame a ser transformado.
        to_upper (bool): Se True, transforma os valores para uppercase. Se False, transforma para lowercase. Default é True.
        columns (Union[bool, List[str]]): Se True, todas as colunas serão transformadas. Se lista, apenas as colunas especificadas serão transformadas. Default é False.
        cells (Union[bool, List[Tuple[int, int]]]): Se True, todas as células serão transformadas. Se lista, apenas as células especificadas serão transformadas. Default é False.

    Returns:
        pd.DataFrame: DataFrame com os valores transformados.
    """

    def transform_value(value):
        if isinstance(value, str):
            return value.upper() if to_upper else value.lower()
        return value

    if cells:
        if cells is True:
            # Transforma todas as células do DataFrame
            df = df.map(transform_value)
        else:
            # Transforma apenas as células especificadas
            for row, col in cells:
                if row < len(df) and col < len(df.columns):
                    df.iat[row, col] = transform_value(df.iat[row, col])
    elif columns:
        if columns is True:
            # Transforma todas as colunas do DataFrame
            df = df.map(transform_value)
        else:
            # Transforma apenas as colunas especificadas
            for col in columns:
                if col in df.columns:
                    df[col] = df[col].apply(transform_value)
    else:
        # Transforma todo o DataFrame
        df = df.map(transform_value)

    return df


def filter_columns(df: pd.DataFrame, columns: list, allow_partial: bool = True) -> pd.DataFrame:
    """
    Filtra as colunas de um DataFrame com base em uma lista de colunas fornecida.

    Args:
        df (pd.DataFrame): DataFrame a ser filtrado.
        columns (list): Lista de colunas a serem mantidas no DataFrame.
        allow_partial (bool): Se True, mantém apenas as colunas existentes no DataFrame.
                             Se False, gera um erro se alguma coluna não existir.

    Returns:
        pd.DataFrame: DataFrame filtrado com as colunas especificadas.

    Raises:
        ValueError: Se `allow_partial` for False e alguma coluna não existir no DataFrame.
    """
    # Verifica as colunas que existem no DataFrame
    existing_columns = [col for col in columns if col in df.columns]

    # Se não permitir parcial e houver colunas faltantes, gera um erro
    if not allow_partial and len(existing_columns) != len(columns):
        missing_columns = [col for col in columns if col not in df.columns]
        raise ValueError(f"As seguintes colunas estão ausentes no DataFrame: {missing_columns}")

    # Retorna o DataFrame filtrado com as colunas existentes
    return df[existing_columns]

def rename_columns(df: pd.DataFrame, rename_dict: Union[dict, "Box"]) -> pd.DataFrame:
    """
    Renomeia as colunas de um DataFrame de forma resiliente, lidando com colunas NaN e colunas inexistentes.

    Args:
        df (pd.DataFrame): DataFrame cujas colunas serão renomeadas.
        rename_dict (Union[dict, Box]): Dicionário ou Box (Dynaconf) contendo o mapeamento de renomeação.

    Returns:
        pd.DataFrame: DataFrame com as colunas renomeadas.
    """
    # Converte Box para dict, se necessário
    if not isinstance(rename_dict, dict):
        rename_dict = dict(rename_dict)

    # Substitui colunas NaN por strings vazias
    df.columns = df.columns.fillna("")

    # Filtra o rename_dict para incluir apenas colunas que existem no DataFrame
    valid_rename_dict = {col: rename_dict[col] for col in rename_dict if col in df.columns}

    # Renomeia as colunas do DataFrame
    df = df.rename(columns=valid_rename_dict)

    return df

def select_columns(df: pd.DataFrame, target_columns: list) -> pd.DataFrame:
    """
    Seleciona colunas de um DataFrame com base em uma lista de colunas alvo, mantendo a ordem fornecida.

    Args:
        df (pd.DataFrame): DataFrame original.
        target_columns (list): Lista de nomes de colunas desejadas.

    Returns:
        pd.DataFrame: DataFrame com as colunas correspondentes selecionadas.
    """
    # Verifica quais colunas da lista alvo existem no DataFrame
    existing_columns = [col for col in target_columns if col in df.columns]

    # Retorna o DataFrame com as colunas existentes na ordem fornecida
    return df[existing_columns]


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

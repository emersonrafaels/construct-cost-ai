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
__status__ = "Development"

from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union
import json

import pandas as pd


def read_data(
    file_path: Union[str, Path],
    sheet_name: Optional[Union[str, int]] = None,
    header: Optional[Union[int, List[int]]] = 0,
    default_sheet: Optional[Union[str, List[str]]] = ["Sheet1", "Planilha1"],
) -> pd.DataFrame:
    """
    Lê dados de vários formatos de arquivo usando a extensão do arquivo para determinar o método apropriado.
    Se a aba especificada (sheet_name) não existir, utiliza a aba padrão (default_sheet).
    
    Args:
        file_path (Union[str, Path]): Caminho para o arquivo a ser lido.
        sheet_name (Optional[Union[str, int]]): Nome ou índice da aba a ser lida (para arquivos Excel). Padrão é None.
        header (Optional[Union[int, List[int]]]): Número(s) da(s) linha(s) a ser(em) usada(s) como nomes das colunas. Padrão é 0.
        default_sheet (Optional[Union[str, List[str]]]): Nome ou lista de nomes das abas padrão a serem lidas se a aba especificada não for encontrada.
    
    Returns:
        pd.DataFrame: DataFrame contendo os dados lidos.
    
    Raises:
        ValueError: Se a extensão do arquivo não for suportada.
        FileNotFoundError: Se o arquivo não existir.
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
        # Tenta carregar a aba especificada
        return reader(file_path)
    except ValueError as e:
        # Tratamento específico para erro de aba não encontrada
        if "Worksheet named" in str(e) and "not found" in str(e):
            try:
                # Listar todas as abas disponíveis no arquivo
                available_sheets = pd.ExcelFile(file_path).sheet_names
                if isinstance(default_sheet, str) and default_sheet in available_sheets:
                    logger.warning(
                        f"Aba '{sheet_name}' não encontrada. Carregando a aba padrão '{default_sheet}'."
                    )
                    return pd.read_excel(file_path, sheet_name=default_sheet, header=header)
                elif isinstance(default_sheet, list):
                    for sheet in default_sheet:
                        if sheet in available_sheets:
                            logger.warning(
                                f"Aba '{sheet_name}' não encontrada. Carregando a aba padrão '{sheet}'."
                            )
                            return pd.read_excel(file_path, sheet_name=sheet, header=header)
                raise ValueError(
                    f"Aba '{sheet_name}' não encontrada no arquivo '{file_path}'. "
                    f"As abas disponíveis são: {available_sheets}"
                )
            except Exception as inner_e:
                raise RuntimeError(
                    f"Erro ao tentar listar as abas disponíveis no arquivo '{file_path}': {str(inner_e)}"
                )
        else:
            raise e
    except Exception as e:
        raise RuntimeError(f"Erro ao ler o arquivo {file_path}: {str(e)}")


def export_data(
    data: Union[pd.DataFrame, Dict[str, pd.DataFrame]],
    file_path: Union[str, Path],
    create_dirs: bool = True,
    index: bool = False,
    **kwargs,
) -> None:
    """
    Exporta dados para vários formatos, com suporte para múltiplas abas em arquivos Excel.

    Args:
        data (Union[pd.DataFrame, Dict[str, pd.DataFrame]]): DataFrame ou dicionário de DataFrames para exportação.
        file_path (Union[str, Path]): Caminho onde o arquivo será salvo.
        create_dirs (bool): Se True, cria diretórios automaticamente se não existirem. Default é True.
        index (bool): Se True, inclui o índice ao salvar os dados. Default é False.
        **kwargs: Argumentos adicionais passados para a função de exportação do pandas.

    Raises:
        ValueError: Se a extensão do arquivo não for suportada.
        RuntimeError: Se ocorrer um erro durante a exportação.
    """
    file_path = Path(file_path)

    if create_dirs:
        file_path.parent.mkdir(parents=True, exist_ok=True)

    extension = file_path.suffix.lower()

    exporters = {
        ".csv": lambda df, path: df.to_csv(path, index=index, **kwargs),
        ".xlsx": lambda df, path: (
            df.to_excel(path, index=index, **kwargs)
            if isinstance(df, pd.DataFrame)
            else (_export_multiple_sheets(df, path, index=index, **kwargs))
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


def _export_multiple_sheets(
    data: Dict[str, pd.DataFrame], path: Union[str, Path], index: bool = False, **kwargs
):
    """
    Função auxiliar para exportar múltiplas abas para um arquivo Excel.

    Args:
        data (Dict[str, pd.DataFrame]): Dicionário de DataFrames para exportação.
        path (Union[str, Path]): Caminho para o arquivo Excel.
        index (bool): Se True, inclui o índice ao salvar os dados. Default é False.
        **kwargs: Argumentos adicionais para pandas.to_excel.
    """
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        for sheet_name, sheet_data in data.items():
            sheet_data.to_excel(writer, sheet_name=sheet_name, index=index, **kwargs)


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


def export_to_json(
    data: Union[pd.DataFrame, Dict[str, Union[pd.DataFrame, dict]]],
    file_path: Union[str, Path],
    create_dirs: bool = True,
    orient: str = "records",
    **kwargs,
) -> None:
    """
    Exporta dados para o formato JSON, com suporte para criar diretórios automaticamente.

    Args:
        data (Union[pd.DataFrame, Dict[str, Union[pd.DataFrame, dict]]]): DataFrame, dicionário de DataFrames ou dicionário de dados para exportação.
        file_path (Union[str, Path]): Caminho onde o arquivo JSON será salvo.
        create_dirs (bool): Se True, cria diretórios automaticamente se não existirem. Default é True.
        orient (str): Orientação do JSON (ex.: "records", "split", "index", etc.). Default é "records".
        **kwargs: Argumentos adicionais passados para `DataFrame.to_json`.

    Raises:
        ValueError: Se o tipo de dado não for suportado.
        RuntimeError: Se ocorrer um erro durante a exportação.
    """
    def default_serializer(obj):
        """Serializador padrão para objetos não serializáveis pelo JSON."""
        if hasattr(obj, "__dict__"):
            return obj.__dict__
        return str(obj)

    file_path = Path(file_path)

    if create_dirs:
        file_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        if isinstance(data, pd.DataFrame):
            # Exporta um único DataFrame para JSON
            data.to_json(file_path, orient=orient, **kwargs)
        elif isinstance(data, dict):
            # Verifica se os valores do dicionário são DataFrames ou outros dicionários
            json_data = {
                key: (df.to_dict(orient=orient) if isinstance(df, pd.DataFrame) else df)
                for key, df in data.items()
            }
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(json_data, f, ensure_ascii=False, indent=4, default=default_serializer)
        else:
            raise ValueError("O tipo de dado fornecido não é suportado. Use um DataFrame ou um dicionário de DataFrames/dados.")
    except Exception as e:
        raise RuntimeError(f"Erro ao exportar para JSON em {file_path}: {str(e)}")


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

    # JSON export example
    try:
        export_to_json(df, "output/data.json", create_dirs=True)
        print("Data exported to JSON successfully")
    except Exception as e:
        print(f"Error exporting to JSON: {e}")

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

import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union
import json

import pandas as pd
from unidecode import unidecode

# Adiciona o diretório src ao path
base_dir = Path(__file__).parents[5]
sys.path.insert(0, str(Path(base_dir, "src")))

from config.config_logger import logger


def read_data(
    file_path: Union[str, Path],
    sheet_name: Optional[Union[str, int]] = None,
    header: Optional[Union[int, List[int]]] = 0,
    default_sheet: Optional[Union[str, List[str]]] = ["Sheet1", "Planilha1", "Plan1"],
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
    columns_to_upper: Union[List[str], str, bool] = None,
    cells_to_upper: Union[List[str], str, bool] = None,
    columns_to_lower: Union[List[str], str, bool] = None,
    cells_to_lower: Union[List[str], str, bool] = None,
    columns_to_remove_spaces: Union[List[str], str, bool] = None,
    cells_to_remove_spaces: Union[List[str], str, bool] = None,
    columns_to_remove_accents: Union[List[str], str, bool] = None,
    cells_to_remove_accents: Union[List[str], str, bool] = None,
) -> pd.DataFrame:
    """
    Aplica transformações específicas em colunas e células de um DataFrame, como transformar em maiúsculas/minúsculas,
    remover espaços e remover acentos.

    Args:
        df (pd.DataFrame): DataFrame a ser transformado.
        columns_to_upper (Union[List[str], str, bool]): Colunas para transformar os nomes em maiúsculas. Use True para todas.
        cells_to_upper (Union[List[str], str, bool]): Colunas para transformar os valores das células em maiúsculas. Use True para todas.
        columns_to_lower (Union[List[str], str, bool]): Colunas para transformar os nomes em minúsculas. Use True para todas.
        cells_to_lower (Union[List[str], str, bool]): Colunas para transformar os valores das células em minúsculas. Use True para todas.
        columns_to_remove_spaces (Union[List[str], str, bool]): Colunas para remover espaços dos nomes. Use True para todas.
        cells_to_remove_spaces (Union[List[str], str, bool]): Colunas para remover espaços dos valores das células. Use True para todas.
        columns_to_remove_accents (Union[List[str], str, bool]): Colunas para remover acentos dos nomes. Use True para todas.
        cells_to_remove_accents (Union[List[str], str, bool]): Colunas para remover acentos dos valores das células. Use True para todas.

    Returns:
        pd.DataFrame: DataFrame com as transformações aplicadas.
    """

    def transform_value(
        value, to_upper=False, to_lower=False, remove_spaces=False, remove_accents=False
    ):
        """Aplica transformações a um único valor."""
        if isinstance(value, str):
            if remove_accents:
                value = unidecode(value)
            if remove_spaces:
                value = value.replace(" ", "")
            if to_upper:
                value = value.upper()
            if to_lower:
                value = value.lower()
        return value

    def resolve_columns(param):
        """Resolve o parâmetro para retornar uma lista de colunas."""
        if param is True:
            return df.columns.tolist()
        elif isinstance(param, str):
            return [param]
        elif isinstance(param, list):
            return param
        return []

    # Garantir que os nomes das colunas sejam strings
    df.columns = df.columns.map(str)

    # Resolver colunas para cada transformação
    columns_to_upper = resolve_columns(columns_to_upper)
    cells_to_upper = resolve_columns(cells_to_upper)
    columns_to_lower = resolve_columns(columns_to_lower)
    cells_to_lower = resolve_columns(cells_to_lower)
    columns_to_remove_spaces = resolve_columns(columns_to_remove_spaces)
    cells_to_remove_spaces = resolve_columns(cells_to_remove_spaces)
    columns_to_remove_accents = resolve_columns(columns_to_remove_accents)
    cells_to_remove_accents = resolve_columns(cells_to_remove_accents)

    # Transformar nomes de colunas
    if columns_to_upper:
        df.rename(
            columns={col: col.upper() for col in columns_to_upper if col in df.columns},
            inplace=True,
        )
    if columns_to_lower:
        df.rename(
            columns={col: col.lower() for col in columns_to_lower if col in df.columns},
            inplace=True,
        )
    if columns_to_remove_spaces:
        df.rename(
            columns={
                col: col.replace(" ", "") for col in columns_to_remove_spaces if col in df.columns
            },
            inplace=True,
        )
    if columns_to_remove_accents:
        df.rename(
            columns={col: unidecode(col) for col in columns_to_remove_accents if col in df.columns},
            inplace=True,
        )

    # Transformar valores das células
    if cells_to_upper:
        for col in cells_to_upper:
            if col in df.columns:
                df[col] = df[col].apply(lambda x: transform_value(x, to_upper=True))
    if cells_to_lower:
        for col in cells_to_lower:
            if col in df.columns:
                df[col] = df[col].apply(lambda x: transform_value(x, to_lower=True))
    if cells_to_remove_spaces:
        for col in cells_to_remove_spaces:
            if col in df.columns:
                df[col] = df[col].apply(lambda x: transform_value(x, remove_spaces=True))
    if cells_to_remove_accents:
        for col in cells_to_remove_accents:
            if col in df.columns:
                df[col] = df[col].apply(lambda x: transform_value(x, remove_accents=True))

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
            raise ValueError(
                "O tipo de dado fornecido não é suportado. Use um DataFrame ou um dicionário de DataFrames/dados."
            )
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


def cast_columns(df: pd.DataFrame, column_types: Dict[str, str]) -> pd.DataFrame:
    """
    Tenta converter as colunas de um DataFrame para os tipos especificados.

    Args:
        df (pd.DataFrame): O DataFrame a ser convertido.
        column_types (Dict[str, str]): Um dicionário onde as chaves são os nomes das colunas
                                       e os valores são os tipos esperados (ex.: "float64", "object").

    Returns:
        pd.DataFrame: O DataFrame com as colunas convertidas.

    Raises:
        ValueError: Se uma coluna especificada não existir no DataFrame.
    """
    for column, col_type in column_types.items():
        if column in df.columns:
            try:
                df[column] = df[column].astype(col_type)
            except Exception as e:
                raise ValueError(
                    f"Erro ao converter a coluna '{column}' para o tipo '{col_type}': {e}"
                )
        else:
            raise ValueError(f"A coluna '{column}' não existe no DataFrame.")
    return df


def merge_data(
    df_left: pd.DataFrame,
    df_right: pd.DataFrame,
    left_on: list,
    right_on: list,
    how: str = "inner",
    suffixes: tuple = ("_left", "_right"),
) -> pd.DataFrame:
    """
    Perform a generic merge between two DataFrames.

    Args:
        df_left (pd.DataFrame): The left DataFrame.
        df_right (pd.DataFrame): The right DataFrame.
        left_on (list): Columns to merge on from the left DataFrame.
        right_on (list): Columns to merge on from the right DataFrame.
        how (str): Type of merge to perform. Defaults to "inner".
        suffixes (tuple): Suffixes to apply to overlapping column names. Defaults to ("_left", "_right").

    Returns:
        pd.DataFrame: The merged DataFrame.

    Raises:
        ValueError: If the merge operation fails.
    """
    try:
        merged_df = pd.merge(
            df_left,
            df_right,
            left_on=left_on,
            right_on=right_on,
            how=how,
            suffixes=suffixes,
        )
        return merged_df
    except Exception as e:
        logger.error(f"Error during merge: {e}")
        raise ValueError(f"Error during merge: {e}")


def perform_merge(
    df_left: pd.DataFrame,
    df_right: pd.DataFrame,
    left_on: list,
    right_on: list,
    how: str,
    suffixes: tuple,
    validate: Optional[str],
    indicator: bool,
    handle_duplicates: bool,
) -> pd.DataFrame:
    """
    Função auxiliar para realizar o merge entre dois DataFrames, com tratamento de duplicidades.

    Args:
        df_left (pd.DataFrame): DataFrame da esquerda.
        df_right (pd.DataFrame): DataFrame da direita.
        left_on (list): Colunas do DataFrame da esquerda para realizar o merge.
        right_on (list): Colunas do DataFrame da direita para realizar o merge.
        how (str): Tipo de merge a ser realizado.
        suffixes (tuple): Sufixos aplicados a colunas sobrepostas.
        validate (Optional[str]): Valida o tipo de relacionamento entre os DataFrames.
        indicator (bool): Se True, adiciona uma coluna indicando a origem de cada linha no merge.
        handle_duplicates (bool): Se True, remove duplicidades automaticamente em caso de erro.

    Returns:
        pd.DataFrame: DataFrame resultante do merge.
    """
    try:
        return pd.merge(
            df_left,
            df_right,
            left_on=left_on,
            right_on=right_on,
            how=how,
            suffixes=suffixes,
            validate=validate,
            indicator=indicator,
        )
    except pd.errors.MergeError as e:
        if handle_duplicates and "not a many-to-one merge" in str(e):
            logger.warning("Removendo duplicidades para tentar novamente o merge.")
            df_left = df_left.drop_duplicates(subset=left_on)
            df_right = df_right.drop_duplicates(subset=right_on)
            return pd.merge(
                df_left,
                df_right,
                left_on=left_on,
                right_on=right_on,
                how=how,
                suffixes=suffixes,
                validate=validate,
                indicator=indicator,
            )
        logger.error(f"Erro durante o merge: {e}")
        raise ValueError(f"Erro durante o merge: {e}")


def merge_data_with_columns(
    df_left: pd.DataFrame,
    df_right: pd.DataFrame,
    left_on: list,
    right_on: list,
    selected_left_columns: list = None,
    selected_right_columns: list = None,
    how: str = "inner",
    suffixes: tuple = ("_left", "_right"),
    validate: str = None,
    indicator: bool = False,
    handle_duplicates: bool = False,
) -> pd.DataFrame:
    """
    Realiza um merge entre dois DataFrames, permitindo selecionar colunas específicas e lidar com duplicidades.

    Parâmetros:
        (mesmos parâmetros da função original)
    """
    # Filtra as colunas do DataFrame da esquerda, se especificado
    if selected_left_columns:
        df_left = df_left[left_on + selected_left_columns]

    # Filtra as colunas do DataFrame da direita, se especificado
    if selected_right_columns:
        df_right = df_right[right_on + selected_right_columns]

    # Realiza o merge usando a função auxiliar
    return perform_merge(
        df_left=df_left,
        df_right=df_right,
        left_on=left_on,
        right_on=right_on,
        how=how,
        suffixes=suffixes,
        validate=validate,
        indicator=indicator,
        handle_duplicates=handle_duplicates,
    )


def two_stage_merge(
    left: pd.DataFrame,
    right: pd.DataFrame,
    keys_stage1: List[List[str]],
    keys_stage2: List[List[str]],
    how: str = "left",
    suffixes: Tuple[str, str] = ("_l", "_r"),
    keep_indicator: bool = True,
    validate_stage1: Optional[str] = None,
    validate_stage2: Optional[str] = None,
    handle_duplicates: bool = False,
) -> pd.DataFrame:
    """
    Faz merge em 2 estágios:
      - Estágio 1: merge por cada conjunto de chaves em keys_stage1.
      - Estágio 2: somente para linhas sem match no estágio 1, merge por cada conjunto de chaves em keys_stage2.
    Regra: se der match no estágio 1, ele prevalece.

    Args:
        left (pd.DataFrame): DataFrame da esquerda.
        right (pd.DataFrame): DataFrame da direita.
        keys_stage1 (List[List[str]]): Lista bidimensional de chaves para o estágio 1.
        keys_stage2 (List[List[str]]): Lista bidimensional de chaves para o estágio 2.
        how (str): Tipo de merge (padrão é "left").
        suffixes (Tuple[str, str]): Sufixos para colunas sobrepostas.
        keep_indicator (bool): Se True, mantém o indicador de origem.
        validate_stage1 (Optional[str]): Validação para o estágio 1 (ex.: "m:1", "1:1").
        validate_stage2 (Optional[str]): Validação para o estágio 2 (ex.: "m:1", "1:1").
        handle_duplicates (bool): Se True, remove duplicidades automaticamente em caso de erro.

    Returns:
        pd.DataFrame: DataFrame resultante do merge em dois estágios.
    """
    # DataFrame inicial para consolidar os resultados
    consolidated_df = pd.DataFrame()

    # Itera sobre as combinações de chaves em keys_stage1 e keys_stage2
    for idx, (stage1_keys, stage2_keys) in enumerate(zip(keys_stage1, keys_stage2)):
        logger.info(f"Iniciando merge para combinação {idx + 1}: Stage1={stage1_keys}, Stage2={stage2_keys}")

        # 1) Merge estágio 1
        m1 = perform_merge(
            df_left=left,
            df_right=right,
            left_on=stage1_keys,
            right_on=stage1_keys,
            how=how,
            suffixes=suffixes,
            validate=validate_stage1,
            indicator=True,
            handle_duplicates=handle_duplicates,
        )

        # Separar matched vs unmatched
        matched_1 = m1[m1["_merge"] != "left_only"].copy()
        unmatched_1 = m1[m1["_merge"] == "left_only"].copy()

        # Se não houver unmatched, adiciona os resultados ao consolidado e continua
        if unmatched_1.empty:
            consolidated_df = pd.concat([consolidated_df, matched_1], ignore_index=True)
            continue

        # 2) Preparar unmatched para merge estágio 2
        right_cols = set(right.columns)
        safe_drop = [c for c in unmatched_1.columns if (c in right_cols and c not in left.columns)]
        unmatched_left_clean = unmatched_1.drop(columns=safe_drop + ["_merge"], errors="ignore")

        # 3) Merge estágio 2
        m2 = perform_merge(
            df_left=unmatched_left_clean,
            df_right=right,
            left_on=stage2_keys,
            right_on=stage2_keys,
            how=how,
            suffixes=suffixes,
            validate=validate_stage2,
            indicator=True,
            handle_duplicates=handle_duplicates,
        )

        # Recombina os resultados do estágio 1 e estágio 2
        combined = pd.concat([matched_1, m2], ignore_index=True)
        consolidated_df = pd.concat([consolidated_df, combined], ignore_index=True)

    # Adiciona o indicador de estágio, se necessário
    if keep_indicator:
        consolidated_df["_merge_stage"] = "none"
        consolidated_df.loc[consolidated_df["_merge"] == "both", "_merge_stage"] = "stage1"
        consolidated_df.loc[consolidated_df["_merge"] == "left_only", "_merge_stage"] = "stage2"
    else:
        consolidated_df = consolidated_df.drop(columns=["_merge"], errors="ignore")

    return consolidated_df
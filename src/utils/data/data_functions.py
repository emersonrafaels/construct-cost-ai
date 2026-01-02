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
base_dir = Path(__file__).parents[3]
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


def ensure_columns_exist(df: pd.DataFrame, columns: list, default_value=None) -> pd.DataFrame:
    """
    Garante que todas as colunas especificadas existam no DataFrame, criando-as com um valor padrão se necessário.

    Args:
        df (pd.DataFrame): DataFrame a ser verificado.
        columns (list): Lista de colunas que devem existir no DataFrame.
        default_value (Any): Valor padrão para preencher as colunas criadas. Default é None.

    Returns:
        pd.DataFrame: DataFrame com as colunas garantidas.
    """
    for col in columns:
        if col not in df.columns:
            df[col] = default_value  # Cria a coluna com o valor padrão
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
    keys_stage1: List[List[str]],  # colunas do LEFT (Budget)
    keys_stage2: List[List[str]],  # colunas do RIGHT (LPU)
    how: str = "left",
    suffixes: Tuple[str, str] = ("_l", "_r"),
    keep_indicator: bool = True,
    validate_stage1: Optional[str] = None,
    validate_stage2: Optional[str] = None,  # mantido por compatibilidade
    handle_duplicates: bool = False,
) -> pd.DataFrame:
    """
    Merge priorizado (sem duplicar linhas do LEFT), pareando regras por índice:

        regra i:
            left_on  = keys_stage1[i]
            right_on = keys_stage2[i]

    Exemplo (Budget x LPU):
        ['ID','REGIAO','GRUPO'] <-> ['CÓD ITEM','REGIAO','GRUPO']
        ['NOME','REGIAO','GRUPO'] <-> ['ITEM','REGIAO','GRUPO']

    Comportamento:
    - tenta regra 1 no conjunto "remaining"
    - o que casar sai do remaining e entra no output
    - tenta regra 2 só no restante
    - sobras entram como left_only

    Retorna:
    - cada linha do left aparece no máximo 1 vez
    - adiciona:
        _merge_stage: stage1 | none
        _merge_rule : rule_01, rule_02...
    """

    if how != "left":
        raise ValueError("two_stage_merge (consumo) suporta apenas how='left'.")

    def _to_list_str(x) -> List[str]:
        # BoxList/list/tuple -> list[str]
        return [str(c) for c in list(x)]

    # Normaliza BoxList -> list[str]
    left_keysets = [_to_list_str(k) for k in keys_stage1]
    right_keysets = [_to_list_str(k) for k in keys_stage2]

    # Garantia de pareamento por regra
    if len(left_keysets) != len(right_keysets):
        raise ValueError(
            f"keys_stage1 e keys_stage2 precisam ter o mesmo tamanho. "
            f"Recebido: {len(left_keysets)} vs {len(right_keysets)}."
        )

    # Preserva ordem original do left
    base_left = left.copy()
    row_id_col = "_row_id__tsm"
    if row_id_col in base_left.columns:
        raise ValueError(f"Coluna reservada já existe no DataFrame: {row_id_col}")

    # Adiciona coluna de ID (Int) temporária
    base_left[row_id_col] = range(len(base_left))
    
    # Mapeando todas as colunas que o dataframe possui
    base_left_cols = list(left.columns) + [row_id_col]

    # Inicia um dataframe com todos os dados
    remaining = base_left[base_left_cols].copy()
    
    # Inicia o dataframe que conterá o resultado final (merged + unmerged)
    collected_parts: List[pd.DataFrame] = []

    def _clean_remaining(df: pd.DataFrame) -> pd.DataFrame:
        # Mantém apenas colunas do left (evita levar colunas do right para a próxima tentativa)
        return df[base_left_cols].copy()

    # Executa regras em ordem (prioridade)
    for i, (lkeys, rkeys) in enumerate(zip(left_keysets, right_keysets), start=1):
        
        # Verificando se há ainda linhas para processar
        if remaining.empty:
            break

        # Criando identificador da regra
        rule = f"rule_{i:02d}"
        logger.info(f"[two_stage_merge] Tentativa {i} | LEFT={lkeys} <-> RIGHT={rkeys}")

        # Executando o merge
        merged = perform_merge(
            df_left=remaining,
            df_right=right,
            left_on=lkeys,
            right_on=rkeys,
            how="left",
            suffixes=suffixes,
            validate=validate_stage1,
            indicator=True,
            handle_duplicates=handle_duplicates,
        )

        # Separa matched e unmatched
        matched = merged[merged["_merge"] == "both"].copy()
        unmatched = merged[merged["_merge"] == "left_only"].copy()

        if not matched.empty:
            matched["_merge_stage"] = f"stage{i}"
            matched["_merge_rule"] = rule
            collected_parts.append(matched)

        # mantém só o left para próxima tentativa
        unmatched = unmatched.drop(columns=["_merge"], errors="ignore")
        remaining = _clean_remaining(unmatched)

    # Adiciona as linhas restantes (não casaram em nenhuma regra) ao resultado final.
    if not remaining.empty:
        remaining_out = remaining.copy()
        remaining_out["_merge"] = "left_only"
        remaining_out["_merge_stage"] = "none"
        remaining_out["_merge_rule"] = None
        collected_parts.append(remaining_out)

    # Consolida todas as partes (matched e unmatched) em um único DataFrame.
    out = pd.concat(collected_parts, ignore_index=True, sort=False)

    # Restaura a ordem original do DataFrame com base na coluna de ID temporária.
    out = out.sort_values(by=row_id_col, kind="stable").reset_index(drop=True)

    # Remove a coluna de ID temporária.
    out = out.drop(columns=[row_id_col], errors="ignore")

    # Remove a coluna "_merge" se o indicador não for necessário.
    if not keep_indicator:
        out = out.drop(columns=["_merge"], errors="ignore")

    # Retorna o DataFrame final consolidado
    return out

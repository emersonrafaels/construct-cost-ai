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
from rapidfuzz import process, fuzz
from unidecode import unidecode
from utils.fuzzy.fuzzy_validations import fuzzy_match

# Adiciona o diretório src ao path
base_dir = Path(__file__).parents[3]
sys.path.insert(0, str(Path(base_dir, "src")))

from config.config_logger import logger
from src.utils.python_functions import to_float_resilient


def read_data(
    file_path: Union[str, Path],
    sheet_name: Optional[Union[str, int]] = None,
    header: Optional[Union[int, List[int]]] = 0,
    default_sheet: Optional[Union[str, List[str]]] = ["Sheet1", "Planilha1", "Plan1"],
    engine: Optional[str] = None,
) -> pd.DataFrame:
    """
    Lê dados de vários formatos de arquivo usando a extensão do arquivo para determinar o método apropriado.
    Se a aba especificada (sheet_name) não existir, utiliza a aba padrão (default_sheet).

    Args:
        file_path (Union[str, Path]): Caminho para o arquivo a ser lido.
        sheet_name (Optional[Union[str, int]]): Nome ou índice da aba a ser lida (para arquivos Excel). Padrão é None.
        header (Optional[Union[int, List[int]]]): Número(s) da(s) linha(s) a ser(em) usada(s) como nomes das colunas. Padrão é 0.
        default_sheet (Optional[Union[str, List[str]]]): Nome ou lista de nomes das abas padrão a serem lidas se a aba especificada não for encontrada.
        engine (Optional[str]): Motor a ser usado para leitura de arquivos Excel. Padrão é None.

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
        ".xlsx": lambda path: pd.read_excel(
            path, sheet_name=sheet_name, header=header, engine=engine
        ),
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
        logger.error(f"Erro ao ler o arquivo {file_path}: {str(e)}")


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
    columns_to_strip: Union[List[str], str, bool] = None,
    cells_to_strip: Union[List[str], str, bool] = None,
) -> pd.DataFrame:
    """
    Aplica transformações específicas em colunas e células de um DataFrame, como transformar em maiúsculas/minúsculas,
    remover espaços, remover acentos e aplicar strip.
    """
    def transform_value(
        value,
        to_upper=False,
        to_lower=False,
        remove_spaces=False,
        remove_accents=False,
        strip=False,
    ):
        """Aplica transformações a um único valor."""
        if not isinstance(value, str):
            return value
        if remove_accents:
            value = unidecode(value)
        if remove_spaces:
            value = value.replace(" ", "")
        if to_upper:
            value = value.upper()
        if to_lower:
            value = value.lower()
        if strip:
            value = value.strip()
        return value

    def resolve_columns(param, current_columns):
        """Resolve o parâmetro para retornar uma lista de colunas."""
        if param in [True, "true", "True"]:
            return list(current_columns)
        elif isinstance(param, str):
            return [param]
        elif isinstance(param, list):
            return param
        return []

    # Garantir nomes de colunas como string
    df.columns = df.columns.map(str)
    col_names = list(df.columns)

    def apply_col_transform(cols, func):
        nonlocal col_names
        updated = []
        for col in cols:
            if col in col_names:
                new_col = func(col)
                idx = col_names.index(col)
                col_names[idx] = new_col
                updated.append(new_col)
        return updated

    # Resolve listas de colunas para cada transformação
    col_transforms = [
        ("columns_to_upper", lambda c: c.upper()),
        ("columns_to_lower", lambda c: c.lower()),
        ("columns_to_remove_spaces", lambda c: c.replace(" ", "")),
        ("columns_to_remove_accents", unidecode),
        ("columns_to_strip", lambda c: c.strip()),
    ]
    params = {
        "columns_to_upper": columns_to_upper,
        "columns_to_lower": columns_to_lower,
        "columns_to_remove_spaces": columns_to_remove_spaces,
        "columns_to_remove_accents": columns_to_remove_accents,
        "columns_to_strip": columns_to_strip,
    }

    # Aplica transformações sequenciais e atualiza listas
    for key, func in col_transforms:
        cols = resolve_columns(params[key], col_names)
        updated_cols = apply_col_transform(cols, func)
        # Atualiza os parâmetros com os novos nomes das colunas
        params[key] = updated_cols

    # Atualiza os nomes das colunas no DataFrame
    df.columns = col_names

    # Atualiza listas de colunas para células com nomes finais
    cells_params = {
        "cells_to_upper": cells_to_upper,
        "cells_to_lower": cells_to_lower,
        "cells_to_remove_spaces": cells_to_remove_spaces,
        "cells_to_remove_accents": cells_to_remove_accents,
        "cells_to_strip": cells_to_strip,
    }

    for key in cells_params:
        cells_params[key] = resolve_columns(cells_params[key], df.columns)

    # Aplica transformações nas células
    cells_ops = [
        ("cells_to_upper", dict(to_upper=True)),
        ("cells_to_lower", dict(to_lower=True)),
        ("cells_to_remove_spaces", dict(remove_spaces=True)),
        ("cells_to_remove_accents", dict(remove_accents=True)),
        ("cells_to_strip", dict(strip=True)),
    ]

    for key, kwargs in cells_ops:
        for col in cells_params[key]:
            if col in df.columns:
                df[col] = df[col].apply(lambda x: transform_value(x, **kwargs))

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


def drop_columns(
    df: pd.DataFrame, drop_column_list: Union[str, List[str]], inplace: bool = False
) -> pd.DataFrame:
    """
    Remove colunas de um DataFrame de forma resiliente, ignorando colunas que não existem.

    Args:
        df (pd.DataFrame): DataFrame original.
        columns (Union[str, List[str]]): Nome ou lista de nomes das colunas a serem removidas.
        inplace (bool): Se True, modifica o DataFrame original. Caso contrário, retorna uma cópia. Default é False.

    Returns:
        pd.DataFrame: DataFrame com as colunas removidas (se inplace=False).

    Raises:
        ValueError: Se `columns` não for uma string ou uma lista de strings.
    """
    if isinstance(drop_column_list, str):
        drop_column_list = [drop_column_list]
    elif not isinstance(drop_column_list, list):
        raise ValueError("O parâmetro 'columns' deve ser uma string ou uma lista de strings.")

    # Filtra apenas as colunas que existem no DataFrame
    existing_columns = [col for col in drop_column_list if col in df.columns]

    if inplace:
        df.drop(columns=existing_columns, inplace=True)
        return df
    else:
        return df.drop(columns=existing_columns, inplace=False)


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


def cast_columns(df: pd.DataFrame, column_types: Dict[str, Union[str, type]]) -> pd.DataFrame:
    """
    Tenta converter as colunas de um DataFrame para os tipos especificados.

    Args:
        df (pd.DataFrame): O DataFrame a ser convertido.
        column_types (Dict[str, Union[str, type]]): Um dicionário onde as chaves são os nomes das colunas
                                                    e os valores são os tipos esperados (ex.: "float64", int).

    Returns:
        pd.DataFrame: O DataFrame com as colunas convertidas.

    Raises:
        ValueError: Se uma coluna especificada não existir no DataFrame ou se o tipo for inválido.
    """
    valid_types = {
        "int",
        "float",
        "object",
        "category",
        "bool",
        "datetime64",
    }  # Tipos válidos baseados no pandas

    for column, col_type in column_types.items():
        if column in df.columns:
            try:
                # Se col_type for um tipo numérico (ex.: float), aplica diretamente
                if isinstance(col_type, type):
                    df[column] = df[column].astype(col_type)
                else:
                    # Garante que col_type seja uma string
                    col_type = str(col_type).lower()
                    # Verifica se o tipo é válido
                    if not any(col_type.startswith(t) for t in valid_types):
                        logger.error(
                            f"Tipo de dado '{col_type}' não é válido para a coluna '{column}'."
                        )
                    if col_type.startswith("int"):
                        # Preenche NaN com 0 antes de converter para int
                        df[column] = (
                            pd.to_numeric(df[column], errors="coerce").fillna(0).astype(col_type)
                        )

                        # Após a conversão, substitui valores NaN por string vazia
                        df[column] = df[column].replace(
                            {0: ""} if col_type == "int" else {pd.NA: "", None: ""}
                        )
                    else:
                        if col_type in ["float64", "float32", "float"]:
                            # Aplica a conversão para float
                            df[column] = df[column].apply(to_float_resilient)
                        else:
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
    use_similarity_for_unmatched: bool = False,  # Renomeado para indicar uso em cenários de não correspondência
    similarity_threshold: float = 90.0,
) -> pd.DataFrame:
    """
    Realiza um merge genérico entre dois DataFrames, com opção de correspondência baseada em similaridade para linhas não correspondidas.

    Args:
        df_left (pd.DataFrame): DataFrame da esquerda.
        df_right (pd.DataFrame): DataFrame da direita.
        left_on (list): Colunas do DataFrame da esquerda para realizar o merge.
        right_on (list): Colunas do DataFrame da direita para realizar o merge.
        how (str): Tipo de merge a ser realizado. Padrão é "inner".
        suffixes (tuple): Sufixos aplicados a colunas sobrepostas. Padrão é ("_left", "_right").
        use_similarity_for_unmatched (bool): Se True, realiza um merge secundário usando similaridade para linhas não correspondidas. Padrão é False.
        similarity_threshold (float): Pontuação mínima de similaridade (0-100) para considerar uma correspondência. Padrão é 90.0.

    Returns:
        pd.DataFrame: O DataFrame resultante do merge.

    Raises:
        ValueError: Se ocorrer um erro durante a operação de merge.
    """
    try:
        # Realiza o merge inicial
        merged_df = pd.merge(
            df_left,
            df_right,
            left_on=left_on,
            right_on=right_on,
            how=how,
            suffixes=suffixes,
        )

        # Se o uso de similaridade para linhas não correspondidas estiver ativado
        if use_similarity_for_unmatched and how in ["inner", "left"]:
            # Identifica as linhas não correspondidas no DataFrame da esquerda
            unmatched_left = df_left[~df_left[left_on[0]].isin(merged_df[left_on[0]])]

            # Realiza a correspondência baseada em similaridade para as linhas não correspondidas
            for l_col, r_col in zip(left_on, right_on):
                unmatched_left[f"{l_col}_matched"] = unmatched_left[l_col].apply(
                    lambda x: (
                        process.extractOne(
                            x, df_right[r_col], scorer=fuzz.ratio, score_cutoff=similarity_threshold
                        )[0]
                        if x is not None
                        else None
                    )
                )

            # Substitui as colunas para usar os valores correspondidos
            similarity_left_on = [f"{col}_matched" for col in left_on]

            # Realiza o merge das linhas não correspondidas usando similaridade
            similarity_merged = pd.merge(
                unmatched_left,
                df_right,
                left_on=similarity_left_on,
                right_on=right_on,
                how="inner",
                suffixes=suffixes,
            )

            # Combina o merge original com o merge baseado em similaridade
            merged_df = pd.concat([merged_df, similarity_merged], ignore_index=True)

        return merged_df

    except Exception as e:
        # Loga o erro e levanta uma exceção com a mensagem
        logger.error(f"Erro durante o merge: {e}")
        raise ValueError(f"Erro durante o merge: {e}")


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
) -> Tuple[pd.DataFrame, List[str]]:
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
        Tuple[pd.DataFrame, List[str]]: DataFrame resultante do merge e lista de colunas criadas no processo.
    """
    try:
        # Remove a coluna '_merge' se indicator estiver ativado e ela já existir
        if indicator:
            if (indicator in df_left.columns) or ("_merge" in df_left.columns):
                logger.warning(
                    "A coluna '_merge' já existe no DataFrame da esquerda. Ela será removida."
                )
                df_left = drop_columns(df=df_left, drop_column_list=[indicator, "_merge"])

        # Lista de colunas antes do merge
        original_columns = list(df_left.columns)

        # Realiza o merge
        df_merged = pd.merge(
            df_left,
            df_right,
            left_on=left_on,
            right_on=right_on,
            how=how,
            suffixes=suffixes,
            validate=validate,
            indicator=indicator,
        )

        # Identifica as colunas criadas após o merge, preservando a ordem
        new_columns = [col for col in df_merged.columns if col not in original_columns]

        return df_merged, new_columns
    except pd.errors.MergeError as e:
        if handle_duplicates and "not a many-to-one merge" in str(e):
            logger.warning("Removendo duplicidades para tentar novamente o merge.")
            df_right = df_right.drop_duplicates(subset=right_on)
            df_merged = pd.merge(
                df_left,
                df_right,
                left_on=left_on,
                right_on=right_on,
                how=how,
                suffixes=suffixes,
                validate=validate,
                indicator=indicator,
            )
            # Identifica as colunas criadas após o merge, preservando a ordem
            new_columns = [col for col in df_merged.columns if col not in original_columns]
            return df_merged, new_columns
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
    use_similarity_for_unmatched: bool = False,  # Adicionado para habilitar similaridade
    similarity_threshold: float = 90.0,  # Adicionado para definir o limite de similaridade
) -> pd.DataFrame:
    """
    Realiza um merge entre dois DataFrames, permitindo selecionar colunas específicas, lidar com duplicidades e usar similaridade para linhas não correspondidas.

    Parâmetros:
        df_left (pd.DataFrame): DataFrame da esquerda.
        df_right (pd.DataFrame): DataFrame da direita.
        left_on (list): Colunas do DataFrame da esquerda para realizar o merge.
        right_on (list): Colunas do DataFrame da direita para realizar o merge.
        selected_left_columns (list, opcional): Colunas adicionais do DataFrame da esquerda a serem incluídas no merge.
        selected_right_columns (list, opcional): Colunas adicionais do DataFrame da direita a serem incluídas no merge.
        how (str): Tipo de merge a ser realizado. Padrão é "inner".
        suffixes (tuple): Sufixos aplicados a colunas sobrepostas. Padrão é ("_left", "_right").
        validate (str, opcional): Valida o tipo de relacionamento entre os DataFrames.
        indicator (bool): Se True, adiciona uma coluna indicando a origem de cada linha no merge.
        handle_duplicates (bool): Se True, remove duplicidades automaticamente em caso de erro.
        use_similarity_for_unmatched (bool): Se True, realiza um merge secundário usando similaridade para linhas não correspondidas. Padrão é False.
        similarity_threshold (float): Pontuação mínima de similaridade (0-100) para considerar uma correspondência. Padrão é 90.0.

    Returns:
        pd.DataFrame: O DataFrame resultante do merge.

    Raises:
        ValueError: Se ocorrer um erro durante a operação de merge.
    """

    # Filtra as colunas do DataFrame da esquerda, se especificado
    if selected_left_columns:
        df_left = df_left[left_on + selected_left_columns]

    # Filtra as colunas do DataFrame da direita, se especificado
    if selected_right_columns:
        df_right = df_right[right_on + selected_right_columns]

    try:
        # Realiza o merge inicial usando a função perform_merge
        merged_df, new_cols = perform_merge(
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

        # Se o uso de similaridade para linhas não correspondidas estiver ativado
        if use_similarity_for_unmatched and how in ["inner", "left"]:
            if not indicator:
                # Realiza o merge inicial usando a função perform_merge
                merged_df, new_cols = perform_merge(
                    df_left=df_left,
                    df_right=df_right,
                    left_on=left_on,
                    right_on=right_on,
                    how=how,
                    suffixes=suffixes,
                    validate=validate,
                    indicator=True,
                    handle_duplicates=handle_duplicates,
                )

            # Identifica as linhas não correspondidas no DataFrame da esquerda
            unmatched_left = merged_df[merged_df[indicator] == "left_only"].copy()

            # Dos dados unmatched, dropa as colunas antes de testar similaridade
            unmatched_left = drop_columns(df=unmatched_left, drop_column_list=new_cols)

            # Armazenamos os dados que deram match (que a condição anterior não satisfeita)
            matched = merged_df[merged_df[indicator] != "left_only"].copy()

            # Realiza o merge das linhas não correspondidas usando a função merge_data_with_similarity
            similarity_merged = merge_data_with_similarity(
                df_left=unmatched_left,
                df_right=df_right,
                left_on=left_on,
                right_on=right_on,
                how=how,
                suffixes=suffixes,
                use_similarity=use_similarity_for_unmatched,
                similarity_threshold=similarity_threshold,
                update_cols=[],
                overwrite=False,
                keep_match_info=False,
                canonical_cols=df_right.columns,
                canonical_priority="right",
            )

            # Lista de DataFrames a serem concatenados
            dataframes = [matched, similarity_merged]

            # Concatena os DataFrames usando a função concat_dataframes
            try:
                merged_df = concat_dataframes(dataframes, ignore_index=True, fill_missing=True)
                print("DataFrames concatenados com sucesso!")
            except Exception as e:
                logger.error(f"Erro ao concatenar DataFrames: {e}")
                raise

        return merged_df

    except Exception as e:
        # Loga o erro e levanta uma exceção com a mensagem
        logger.error(f"Erro durante o merge: {e}")
        raise ValueError(f"Erro durante o merge: {e}")


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
        merged, new_cols = perform_merge(
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


def merge_data_with_similarity(
    df_left: pd.DataFrame,
    df_right: pd.DataFrame,
    left_on: list[str],
    right_on: list[str],
    how: str = "left",
    suffixes: tuple[str, str] = ("_left", "_right"),
    use_similarity: bool = False,
    similarity_threshold: float = 90.0,
    update_cols: list[str] | None = None,
    overwrite: bool = True,
    keep_match_info: bool = False,
    drop_right_updated_cols: bool = True,
    canonical_cols: list[str] | None = None,
    canonical_priority: str = "right",
    drop_canonical_suffix_variants: bool = True,
    verbose=True,
) -> pd.DataFrame:
    """
    Faz merge (com opção de similaridade nas chaves) e atualiza colunas do df_left
    usando valores do df_right apenas quando houver match.

    NOVO:
      - canonical_cols: colunas que DEVEM existir no output com o nome original)
      - canonical_priority:
          * "right": canonical = valor do right (quando existe), senão left
          * "left": canonical = valor do left (já atualizado), senão right
      - drop_canonical_suffix_variants: remove versões sufixadas dessas colunas após criar canônicas
    """

    left = df_left.copy()
    right = df_right.copy()

    if len(left_on) != len(right_on):
        raise ValueError("left_on e right_on precisam ter o mesmo tamanho.")

    if canonical_cols is None:
        # por padrão, costuma ser o schema do right
        canonical_cols = right_on[:]  # ex.: ["FORNECEDOR","REGIAO","GRUPO"]

    # =========================
    # Helpers
    # =========================
    def _resolve_lr_cols(merged: pd.DataFrame, base: str) -> tuple[str, str]:
        l_suf, r_suf = suffixes

        left_candidates = []
        right_candidates = []

        if l_suf:
            left_candidates.append(f"{base}{l_suf}")
        if r_suf:
            right_candidates.append(f"{base}{r_suf}")

        left_candidates.append(base)
        right_candidates.append(base)

        left_col = next((c for c in left_candidates if c in merged.columns), None)
        right_col = next((c for c in right_candidates if c in merged.columns), None)

        if left_col is None:
            raise KeyError(f"Não achei coluna do LEFT para '{base}'. Candidatas: {left_candidates}")
        if right_col is None:
            raise KeyError(
                f"Não achei coluna do RIGHT para '{base}'. Candidatas: {right_candidates}"
            )

        return left_col, right_col

    # =========================
    # 1) Preparar chaves (com ou sem similaridade)
    # =========================
    left_keys = left_on[:]
    right_keys = right_on[:]
    temp_key_cols: list[str] = []

    if use_similarity:
        # Percorrendo as colunas para testar match,
        for l_col, r_col in zip(left_on, right_on):
            unique_left = left[l_col].dropna().unique()
            unique_right = right[r_col].dropna().unique()

            match_dict = {}
            for value in unique_left:
                # Percorrendo os dados do dataframe left, que precisam de match
                res = fuzzy_match(
                    value=value,
                    choices=unique_right,
                    top_matches=1,
                    threshold=similarity_threshold,
                    normalize=True,
                )

                # Salvando no dict o resultado obtido
                match_dict[value] = res.choice if res else None

                if verbose:
                    if res:
                        logger.info(f"Valor: {value} - Match: {res} - Score: {res.score}")

            # Salvando no dataframe left usando colunas temporárias
            key_col = f"__key_{r_col}"
            left[key_col] = left[l_col].map(match_dict)

            idx = left_keys.index(l_col)
            left_keys[idx] = key_col
            temp_key_cols.append(key_col)

    # =========================
    # 2) Definir colunas a atualizar
    # =========================
    if update_cols is None:
        update_cols = [c for c in right.columns if c not in right_on]

    update_cols = [c for c in update_cols if c not in right_on]

    # =========================
    # 3) Merge para trazer colunas do right
    # =========================
    right_select = [c for c in (right_on + update_cols) if c in right.columns]

    merged = left.merge(
        right[right_select],
        left_on=left_keys,
        right_on=right_keys,
        how=how,
        suffixes=suffixes,
        indicator=True if keep_match_info else False,
    )

    if keep_match_info:
        merged["_matched"] = merged["_merge"].eq("both")
        # mantém _merge só se você quiser debug
        # merged = merged.drop(columns=["_merge"])

    # =========================
    # 4) Atualizar colunas do left com right
    # =========================
    for base in update_cols:
        # se não veio do right, pula
        if (
            base not in right.columns
            and f"{base}{suffixes[1]}" not in merged.columns
            and base not in merged.columns
        ):
            continue

        lcol, rcol = _resolve_lr_cols(merged, base)

        if lcol == rcol:
            continue

        if overwrite:
            merged[lcol] = merged[lcol].where(merged[rcol].isna(), merged[rcol])
        else:
            merged[lcol] = merged[lcol].fillna(merged[rcol])

        if drop_right_updated_cols:
            merged = merged.drop(columns=[rcol], errors="ignore")

    # =========================
    # 5) Criar colunas canônicas (nomes do df_right)
    # =========================
    # Ex.: garantir FORNECEDOR, REGIAO, GRUPO
    for base in canonical_cols:
        # tenta achar versões sufixadas que existam
        lcol = f"{base}{suffixes[0]}" if suffixes[0] else base
        rcol = f"{base}{suffixes[1]}" if suffixes[1] else base

        # fallback: se não existe com sufixo, tenta base puro
        if lcol not in merged.columns and base in merged.columns:
            lcol = base
        if rcol not in merged.columns and base in merged.columns:
            rcol = base

        left_exists = lcol in merged.columns
        right_exists = rcol in merged.columns

        # cria a coluna base, priorizando right ou left
        if canonical_priority == "right":
            if right_exists and left_exists:
                merged[base] = merged[rcol].where(merged[rcol].notna(), merged[lcol])
            elif right_exists:
                merged[base] = merged[rcol]
            elif left_exists:
                merged[base] = merged[lcol]
        else:  # "left"
            if right_exists and left_exists:
                merged[base] = merged[lcol].where(merged[lcol].notna(), merged[rcol])
            elif left_exists:
                merged[base] = merged[lcol]
            elif right_exists:
                merged[base] = merged[rcol]

        # remove versões sufixadas das canônicas (se pedido)
        if drop_canonical_suffix_variants:
            cols_to_drop = []
            if f"{base}{suffixes[0]}" in merged.columns and f"{base}{suffixes[0]}" != base:
                cols_to_drop.append(f"{base}{suffixes[0]}")
            if f"{base}{suffixes[1]}" in merged.columns and f"{base}{suffixes[1]}" != base:
                cols_to_drop.append(f"{base}{suffixes[1]}")
            # também remove "base" duplicada se ela era técnica (não é o caso aqui, mas safe)
            merged = merged.drop(columns=cols_to_drop, errors="ignore")

    # =========================
    # 6) Limpar colunas temporárias de chave (similaridade)
    # =========================
    if temp_key_cols:
        merged = merged.drop(columns=temp_key_cols, errors="ignore")

    # se keep_match_info=False, remove _merge se existir
    if not keep_match_info and "_merge" in merged.columns:
        merged = merged.drop(columns=["_merge"], errors="ignore")

    return merged


def concat_dataframes(
    dataframes: list, ignore_index: bool = True, fill_missing: bool = True
) -> pd.DataFrame:
    """
    Concatena uma lista de DataFrames, lidando com índices duplicados e colunas inconsistentes.

    Args:
        dataframes (list): Lista de DataFrames a serem concatenados.
        ignore_index (bool): Se deve ignorar os índices originais e criar um novo índice.
        fill_missing (bool): Se deve preencher valores ausentes com NaN para colunas inconsistentes.

    Returns:
        pd.DataFrame: DataFrame concatenado.
    """
    if not dataframes:
        raise ValueError("A lista de DataFrames está vazia.")

    # Verifica se todos os elementos da lista são DataFrames
    if not all(isinstance(df, pd.DataFrame) for df in dataframes):
        raise TypeError("Todos os elementos da lista devem ser DataFrames.")

    # Preenche valores ausentes para colunas inconsistentes, se necessário
    if fill_missing:
        all_columns = set(col for df in dataframes for col in df.columns)
        dataframes = [df.reindex(columns=all_columns) for df in dataframes]

    # Concatena os DataFrames
    concatenated_df = pd.concat(dataframes, ignore_index=ignore_index)

    return concatenated_df


def resolve_duplicate_columns(
    df: pd.DataFrame,
    column_name: Optional[str] = None,  # Nome da coluna ou None para todas as colunas
    strategy: str = "rename",  # Opções: "rename", "keep_first", "keep_last", "drop"
    suffix: str = "_dup",
) -> pd.DataFrame:
    """
    Resolve colunas duplicadas em um DataFrame com base na estratégia escolhida.

    Args:
        df (pd.DataFrame): DataFrame com possíveis colunas duplicadas.
        column_name (Optional[str]): Nome da coluna a ser verificada para duplicatas.
                                      Use None para aplicar a estratégia a todas as colunas.
        strategy (str): Estratégia para lidar com duplicatas:
            - "rename": Renomeia colunas duplicadas adicionando um sufixo.
            - "keep_first": Mantém apenas a primeira ocorrência da coluna.
            - "keep_last": Mantém apenas a última ocorrência da coluna.
            - "drop": Remove todas as colunas duplicadas.
        suffix (str): Sufixo a ser adicionado ao renomear colunas duplicadas (apenas para "rename").

    Returns:
        pd.DataFrame: DataFrame com as colunas duplicadas resolvidas.

    Raises:
        ValueError: Se a estratégia fornecida não for válida.
    """

    # Função auxiliar para renomear colunas duplicadas
    def rename_duplicates(columns):
        seen = {}
        new_columns = []
        for col in columns:
            if col in seen:
                seen[col] += 1
                new_columns.append(f"{col}{suffix}{seen[col]}")
            else:
                seen[col] = 0
                new_columns.append(col)
        return new_columns

    # logger.info(f"Colunas antes: {df.columns.tolist()}")

    # Se column_name for None, aplica a estratégia a todas as colunas
    if column_name is None:
        if strategy == "rename":
            # Renomeia todas as colunas duplicadas no DataFrame
            df.columns = rename_duplicates(df.columns)
        elif strategy in ["keep_first", "keep_last", "drop"]:
            # Identifica colunas duplicadas
            duplicated_mask = df.columns.duplicated(keep=strategy.split("_")[1])
            if strategy == "drop":
                # Remove todas as duplicatas
                df = df.loc[:, ~df.columns.duplicated(keep=False)]
            else:
                # Mantém apenas a primeira ou última ocorrência
                df = df.loc[:, ~duplicated_mask]
        else:
            raise ValueError(
                f"Estratégia inválida: '{strategy}'. Use 'rename', 'keep_first', 'keep_last' ou 'drop'."
            )
    else:
        # Aplica a estratégia apenas à coluna especificada
        if column_name not in df.columns:
            raise ValueError(f"A coluna '{column_name}' não existe no DataFrame.")

        # Identifica colunas duplicadas com o mesmo nome
        duplicate_columns = [col for col in df.columns if col == column_name]

        # Se não houver duplicatas, retorna o DataFrame original
        if len(duplicate_columns) <= 1:
            return df

        if strategy == "rename":
            # Renomeia colunas duplicadas adicionando um sufixo
            for i, col in enumerate(duplicate_columns[1:], start=1):
                new_name = f"{col}{suffix}{i}"
                df.rename(columns={col: new_name}, inplace=True)
        elif strategy == "keep_first":
            # Mantém apenas a primeira ocorrência da coluna
            df = df.loc[:, ~df.columns.duplicated(keep="first")]
        elif strategy == "keep_last":
            # Mantém apenas a última ocorrência da coluna
            df = df.loc[:, ~df.columns.duplicated(keep="last")]
        elif strategy == "drop":
            # Remove todas as colunas duplicadas
            df = df.loc[:, ~df.columns.duplicated(keep=False)]
        else:
            raise ValueError(
                f"Estratégia inválida: '{strategy}'. Use 'rename', 'keep_first', 'keep_last' ou 'drop'."
            )

    # logger.info(f"Colunas depois: {df.columns.tolist()}")

    return df


def filter_by_merge_column(
    df: pd.DataFrame,
    merge_column: str = "_merge",
    value: Union[str, List[str]] = "both",
    raise_on_missing: bool = False,
) -> Optional[pd.DataFrame]:
    """
    Filtra um DataFrame com base nos valores da coluna '_merge'.

    Args:
        df (pd.DataFrame): DataFrame a ser filtrado.
        merge_column (str): Nome da coluna de merge a ser utilizada. Padrão é '_merge'.
        value (Union[str, List[str]]): Valor ou lista de valores a serem buscados na coluna '_merge' (ex.: 'both', ['both', 'left']).
        raise_on_missing (bool): Se True, lança um erro se a coluna '_merge' não for encontrada. Caso contrário, retorna None.

    Returns:
        Optional[pd.DataFrame]: DataFrame filtrado contendo apenas as linhas com os valores especificados na coluna '_merge'.
                                Retorna None se a coluna '_merge' não for encontrada e `raise_on_missing` for False.

    Raises:
        ValueError: Se a coluna '_merge' não for encontrada e `raise_on_missing` for True.
    """
    if merge_column not in df.columns:
        message = f"A coluna '{merge_column}' não foi encontrada no DataFrame."
        if raise_on_missing:
            raise ValueError(message)
        else:
            logger.debug(message)
            return None

    # Garante que `value` seja uma lista
    if isinstance(value, str):
        value = [value]

    # Filtra o DataFrame com base nos valores especificados
    try:
        return len(df[df[merge_column].isin(value)])
    except Exception as e:
        return None

"""
Módulo: budget_reader
------------------------

Responsável por localizar e extrair, de forma robusta e independente de posição,
a tabela principal de itens de orçamento no padrão utilizado pelas construtoras
(GOT), normalmente presente na aba "LPU" das planilhas recebidas.

Este módulo foi projetado para suportar arquivos enviados por diferentes fornecedores.

🧩 O que este módulo faz:
-------------------------
1) Lê a aba "LPU" como planilha bruta, sem assumir header fixo.
2) Localiza dinamicamente o cabeçalho da tabela contendo as colunas:

   Filtro | ID | Descrição | Un. | Unitário | Comentário | Quantidade | Total

3) Extrai somente a tabela — ignorando cabeçalhos superiores, metadados e rodapés.
4) Normaliza e limpa linhas vazias ou inválidas.
5) Disponibiliza as seguintes funções:

    - ler_planilha_tabela_orcamento(caminho_arquivo, nome_aba="LPU"):
         Função principal para ingestão de um arquivo no padrão das construtoras.

   - localizar_tabela(df):
         Detecta a posição (linha, coluna) onde o cabeçalho se inicia.

   - extrair_tabela(df, header_row, first_col):
         Extrai todas as linhas subsequentes da tabela até as linhas vazias.

🎯 Por que este módulo é essencial:
----------------------------------
- As planilhas reais apresentam alta variabilidade de layout.
- A posição da tabela nunca é garantida: pode estar na linha 10, 20, 40 ou mais.
- O verificador precisa garantir parsing estável antes de aplicar regras de IA.
- Pessoas usuárias enviam arquivos com linhas extras, logos, disclaimers etc.
- Minimiza erros de ingestão e padroniza o fluxo interno do Verificador Inteligente.

🚀 Benefícios para o Verificador Inteligente de Orçamentos:
-----------------------------------------------------------
- Padroniza leitura → menos erros nas etapas determinísticas.
- Permite parsing massivo de orçamentos (processamento diário / batch).
- Suporta testes automatizados com grande variedade de layouts reais.
- Fornece uma base estruturada para agentes de IA avaliarem preços, quantidades,
  desvios e itens fora da LPU.

📁 Localização:
--------------
O módulo faz parte da arquitetura "utils/", permitindo reutilização limpa em:

- CLI (rich)
- Orquestrações de agentes
- Fluxos Streamlit
- Pipelines via Step Functions / Lambda
- Testes automatizados

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

import math
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import pandas as pd
from pydantic.dataclasses import dataclass

# Adicionar src ao path
base_dir = Path(__file__).parents[4]
sys.path.insert(0, str(Path(base_dir, "src")))

from config.config_logger import logger
from utils.readers.budget_reader.config_dynaconf_budget_reader import get_settings
from utils.readers.budget_reader.config_metadata import get_metadata_keys
from utils.data.data_functions import (
    read_data,
    transform_case,
    filter_columns,
    export_data,
    rename_columns,
    select_columns,
)

# Obtendo a instância de configurações
settings = get_settings()

# Substituí as constantes centralizadas por chamadas ao Dynaconf
DEFAULT_SHEET_NAME = settings.get("default_sheet.name", None)
SHEET_NAMES_TRY = settings.get("default_sheet.sheet_candidates", ["LPU", "01"])
PATTERN_DEFAULT = settings.get("default_sheet.pattern_default", "default01")

# Colunas mínimas esperadas
EXPECTED_COLUMNS = {
    "default01": settings.get("expected_columns.default01.columns", []),
    "default02": settings.get("expected_columns.default02.columns", []),
}

# Colunas mínimas alternativas
ALTERNATIVE_COLUMNS = {
    "default01": settings.get("alternative_columns.default01.columns", []),
    "default02": settings.get("alternative_columns.default02.columns", []),
}

# Criando o dicionário de renomeação de colunas
DICT_RENAME = {
    "default01": settings.get("default01.result", {}),
    "default02": settings.get("default02.result", {}),
}

# Obtendo as chaves de metadados padrão
DEFAULT_METADATA_KEYS = get_metadata_keys()

# Definindo a coluna desejado no resultado
SELECTED_COLUMNS = settings.get("result.list_result_columns", [])

# Filtros no pós processamento
FILTROS = settings.get("filtros.dict_filtros", {})  # Nome da coluna usada para filtragem

# Diretório de saída padrão
DIR_OUTPUTS = settings.get("dir_outputs.path", "outputs")


@dataclass
class FileInput:
    """
    Representa um arquivo de entrada com caminho e nome da aba opcional.

    Attributes:
        file_path (str): Caminho do arquivo.
        sheet_name (Optional[str]): Nome da aba a ser lida (padrão: "LPU").
    """

    file_path: str  # Caminho completo do arquivo
    sheet_name: Optional[str] = None  # Nome da aba (padrão: None para todas as abas)


# Funções auxiliares


# Função para normalizar uma lista de valores, removendo espaços, convertendo para letras minúsculas e tratando valores NaN
def normalize_values(values: list) -> list:
    """
    Normaliza uma lista de valores, removendo espaços, convertendo para letras minúsculas
    e substituindo valores NaN ou vazios por strings vazias.

    Args:
        values (list): Lista de valores a serem normalizados.

    Returns:
        list: Lista de valores normalizados.
    """
    return [
        (
            ""
            if pd.isna(val) or (isinstance(val, float) and math.isnan(val))
            else str(val).strip().lower()
        )
        for val in values  # Remove espaços, converte para minúsculas e trata NaN
    ]


# Função para pré-processar o DataFrame, removendo linhas completamente em branco e resetando o índice
def preprocess_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Realiza o pré-processamento inicial dos dados, incluindo a remoção de linhas totalmente em branco.

    Args:
        df (pd.DataFrame): DataFrame bruto lido da planilha.

    Returns:
        pd.DataFrame: DataFrame pré-processado.
    """
    # Remove linhas vazias e reseta o índice
    df = df.dropna(how="all").reset_index(drop=True)

    # Converte todas as colunas e celulas em uppercase
    return transform_case(df=df, to_upper=True, columns=True, cells=True)


# Função para localizar dinamicamente o cabeçalho da tabela no DataFrame
def locate_table(
    df: pd.DataFrame,
    expected_columns: dict = EXPECTED_COLUMNS,
    alternative_columns: dict = ALTERNATIVE_COLUMNS,
) -> Tuple[Optional[int], Optional[int], Optional[list]]:
    """
    Detecta a posição (linha, coluna) onde o cabeçalho da tabela começa, testando múltiplos padrões de colunas.

    Args:
        df (pd.DataFrame): DataFrame contendo os dados da planilha.
        expected_columns (dict): Dicionário com listas de colunas esperadas para diferentes padrões.
        alternative_columns (dict): Dicionário com listas alternativas mínimas de colunas aceitas para diferentes padrões.

    Returns:
        tuple: Uma tupla (linha, coluna, colunas_encontradas) indicando a posição do cabeçalho e as colunas encontradas,
               ou (None, None, None) se não encontrado.
    """
    for pattern_key in expected_columns:
        # Normaliza colunas esperadas e alternativas para uppercase
        normalized_expected = [
            str(col).upper() if isinstance(col, str) else col
            for col in expected_columns[pattern_key]
        ]
        normalized_alternative = [
            str(col).upper() if isinstance(col, str) else col
            for col in alternative_columns[pattern_key]
        ]

        # Número de colunas esperadas
        num_cols = len(normalized_expected)

        # Itera sobre as linhas do DataFrame
        for row in range(df.shape[0]):

            # Itera sobre as colunas possíveis
            for col in range(df.shape[1] - num_cols + 1):

                # Extrai valores da linha e colunas
                values = df.iloc[row, col : col + num_cols].tolist()

                # Normaliza os valores extraídos para uppercase
                normalized = [
                    "" if pd.isna(val) else str(val).upper() if isinstance(val, str) else val
                    for val in values
                ]

                # Verifica se os valores correspondem às colunas esperadas
                if normalized == normalized_expected:
                    return row, col, pattern_key, expected_columns[pattern_key]

                # Verifica colunas alternativas
                if all(col in normalized for col in normalized_alternative):
                    return row, col, pattern_key, alternative_columns[pattern_key]

    # Retorna None se não encontrar o cabeçalho
    return None, None, None, None


# Função auxiliar para encontrar e atribuir valores de metadados a um dicionário
def find_metadata_value(
    row: pd.Series,
    col_idx: int,
    metadata_key: str,
    metadata: Dict[str, Any],
    df: pd.DataFrame,
    row_idx: int,
    specific_cell: Optional[Tuple[int, int]] = None,
    max_rows_to_iterate: Optional[int] = None,
) -> None:
    """
    Busca e atribui um valor de metadado ao dicionário, descendo pelas linhas até encontrar o valor
    ou buscando uma célula específica.

    Args:
        row (pd.Series): Linha do DataFrame.
        col_idx (int): Índice da coluna atual.
        metadata_key (str): Chave do metadado a ser buscado.
        metadata (dict): Dicionário de metadados.
        df (pd.DataFrame): DataFrame completo para buscar o valor nas linhas subsequentes.
        row_idx (int): Índice da linha atual no DataFrame.
        specific_cell (Optional[Tuple[int, int]]): Coordenadas (linha, coluna) de uma célula específica a ser buscada.
        max_rows_to_iterate (Optional[int]): Número máximo de linhas para iterar ao buscar o valor.
    """
    # Verifica se o metadado já foi atribuído
    if metadata[metadata_key] is not None:
        return

    if specific_cell:
        # Busca o valor na célula específica
        specific_row, specific_col = specific_cell
        if 0 <= specific_row < len(df) and 0 <= specific_col < len(df.columns):
            value = df.iloc[specific_row, specific_col]
            if not pd.isna(value):
                metadata[metadata_key] = str(value).upper()
        return

    # Itera pelas linhas subsequentes
    rows_to_iterate = range(row_idx + 1, len(df))
    if max_rows_to_iterate is not None:
        rows_to_iterate = range(row_idx + 1, min(row_idx + 1 + max_rows_to_iterate, len(df)))

    for next_row_idx in rows_to_iterate:
        # Obtém o valor da célula na linha subsequente
        value = df.iloc[next_row_idx, col_idx]
        if not pd.isna(value):  # Verifica se o valor não é NaN
            metadata[metadata_key] = str(value).upper()  # Atribui o valor encontrado em uppercase
            break


# Função para extrair metadados dinamicamente do DataFrame
def extract_metadata(
    df: pd.DataFrame, metadata_keys: dict = DEFAULT_METADATA_KEYS, pattern_key: str = "default01"
) -> Dict[str, Optional[Any]]:
    """
    Extrai metadados da tabela de orçamento de forma genérica e dinâmica.

    Args:
        df (pd.DataFrame): DataFrame contendo os dados da planilha.
        metadata_keys (dict): Dicionário com as chaves de metadados e suas configurações.
        pattern_key (str): Chave do padrão de metadados a ser usado.

    Returns:
        dict: Dicionário contendo os metadados extraídos.
    """
    # Obtém o dicionário de metadados para o padrão especificado
    selected_metadata_keys = metadata_keys.get(pattern_key, {})

    # Inicializa o dicionário de metadados
    metadata = {key: None for key in selected_metadata_keys}

    # Itera sobre as linhas do DataFrame
    for row_idx, row in df.iterrows():
        for col_idx, cell in enumerate(row):
            # Ignora células vazias
            if pd.isna(cell):
                continue

            # Normaliza o valor da célula para uppercase
            cell_str = str(cell).strip().upper()

            # Verifica padrões de metadados
            for key, config in selected_metadata_keys.items():
                # Obtém o padrão e método de busca
                pattern = config["pattern"]
                method = config.get("method", "iterate")

                # Verifica se o padrão está na célula atual ou se o método é "specific_cell"
                if metadata[key] is None and (
                    pattern.upper() in cell_str or method == "specific_cell"
                ):
                    # Busca o valor do metadado com base na configuração
                    find_metadata_value(
                        row=row,
                        col_idx=col_idx,
                        metadata_key=key,
                        metadata=metadata,
                        df=df,
                        row_idx=row_idx,
                        specific_cell=config.get("specific_cell"),
                        max_rows_to_iterate=config.get("max_rows"),
                    )

    return metadata


def rename_and_select_columns(
    df: pd.DataFrame, pattern_key: str, rename_mappings: dict, selected_columns: list
) -> pd.DataFrame:
    """
    Renomeia as colunas e seleciona apenas as colunas desejadas com base no padrão fornecido.

    Args:
        df (pd.DataFrame): DataFrame original.
        pattern_key (str): Chave do padrão a ser usado para renomear e selecionar colunas.
        rename_mappings (dict): Dicionário contendo os mapeamentos de renomeação para cada padrão.

    Returns:
        pd.DataFrame: DataFrame com colunas renomeadas e filtradas.
    """
    # Obtém o dicionário de renomeação para o padrão fornecido
    if pattern_key not in rename_mappings:
        raise ValueError(f"Padrão '{pattern_key}' não encontrado nos mapeamentos de renomeação.")

    rename_dict = rename_mappings[pattern_key].get("dict_rename", {})

    # Renomeia as colunas do DataFrame
    df = rename_columns(df, rename_dict=rename_dict)

    # Seleciona apenas as colunas desejadas (valores do dicionário de renomeação)
    df = select_columns(df, target_columns=selected_columns)

    return df


# Função para extrair a tabela do DataFrame a partir da linha do cabeçalho
def extract_table(
    df: pd.DataFrame,
    header_row: int,
    first_col: int,
    columns_found: list,
    col_filter: str = FILTROS,
    pattern_key: str = PATTERN_DEFAULT,
) -> pd.DataFrame:
    """
    A partir da posição do cabeçalho, extrai a tabela até as linhas vazias.

    Args:
        df (pd.DataFrame): DataFrame contendo os dados da planilha.
        header_row (int): Linha onde o cabeçalho da tabela começa.
        first_col (int): Coluna onde o cabeçalho da tabela começa.
        columns_found (list): Lista de colunas encontradas no cabeçalho.
        col_filter (str): Nome da coluna usada para filtrar linhas vazias.

    Returns:
        pd.DataFrame: DataFrame contendo apenas a tabela extraída e processada.
    """

    # Número de colunas encontradas
    num_cols = len(columns_found)

    # Define o cabeçalho a partir da linha encontrada
    header = df.iloc[header_row, :].tolist()

    # Extrai os dados abaixo do cabeçalho
    data = df.iloc[header_row + 1 :, :].copy()

    # Define o cabeçalho no DataFrame
    data.columns = header

    # Renomeia o nome das colunas para manter consistência
    data = rename_and_select_columns(df=data, 
                                     pattern_key=pattern_key, 
                                     rename_mappings=DICT_RENAME, 
                                     selected_columns=SELECTED_COLUMNS)

    # Aplica pós-processamento e filtros
    return post_process_table(data, col_filter=col_filter)


# Separei a lógica de filtros em uma função dedicada e tornei-a resiliente para diferentes tipos de filtros.
def apply_filter(data: pd.DataFrame, col: str, filter_value: Any) -> pd.DataFrame:
    """
    Aplica um filtro resiliente a uma coluna do DataFrame.

    Args:
        data (pd.DataFrame): DataFrame contendo os dados.
        col (str): Nome da coluna a ser filtrada.
        filter_value (Any): Valor ou condição de filtro (e.g., "greater_than:0", "less_than:10", "equal:SIM", ["SIM", "sim"]).

    Returns:
        pd.DataFrame: DataFrame filtrado.
    """
    if isinstance(filter_value, str):
        if "greater_than:" in filter_value:
            threshold = float(filter_value.split(":")[1])
            return data[data[col] > threshold]
        elif "less_than:" in filter_value:
            threshold = float(filter_value.split(":")[1])
            return data[data[col] < threshold]
        elif "equal:" in filter_value:
            target = filter_value.split(":")[1].lower()
            return data[data[col].str.lower() == target]
    elif isinstance(filter_value, list):
        return data[data[col].str.lower().isin([val.lower() for val in filter_value])]

    return data


def post_process_table(
    data: pd.DataFrame, col_filter: Dict[str, Any] = FILTROS
) -> pd.DataFrame:
    """
    Aplica filtros e pós-processamentos em um DataFrame extraído.

    Args:
        data (pd.DataFrame): DataFrame contendo os dados extraídos da tabela.
        col_filter (dict): Dicionário onde a chave é o nome da coluna e o valor pode ser uma string ou uma lista de valores filtráveis.

    Returns:
        pd.DataFrame: DataFrame pós-processado com filtros aplicados.
    """

    # Aplica os filtros definidos no dicionário col_filter
    for col, filter_value in col_filter.items():
        if col in data.columns:
            data = apply_filter(data, col, filter_value)

    # Reseta o índice do DataFrame
    return data.reset_index(drop=True)


def read_data_budget(
    file_path: str, sheet_name: str = DEFAULT_SHEET_NAME, header: Optional[int] = None
) -> pd.DataFrame:
    """
    Lê a planilha e retorna o DataFrame bruto.

    Args:
        file_path (str): Caminho do arquivo da planilha.
        sheet_name (str): Nome da aba a ser lida.

    Returns:
        pd.DataFrame: DataFrame bruto lido da planilha.
    """
    # Lê a planilha sem cabeçalho
    raw_df = read_data(file_path, sheet_name=sheet_name, header=None)
    
    if isinstance(raw_df, pd.DataFrame) or isinstance(raw_df, dict):

        if sheet_name is None:
            # Tenta ler abas comuns se nenhuma aba for especificada
            for sheet in SHEET_NAMES_TRY:
                try:
                    if sheet in raw_df.keys():
                        df_selected_sheet = raw_df[sheet]
                        logger.info(f"Aba '{sheet}' encontrada e lida com sucesso.")
                        break
                except Exception as e:
                    logger.warning(f"Aba '{sheet}' não encontrada: {e}")
        else:
            """ 
                A leitura já foi feita exatamente da aba especificada
                Para manter as variáveis consistentes, fazemos a cópia do raw_df
                copy() garante que df_selected_sheet é um DataFrame independente (ponteiro separado)
            """
            df_selected_sheet = raw_df.copy()
            sheet = sheet_name
            logger.info(f"Aba '{sheet_name}' encontrada e lida com sucesso.")

        # Pré-processa os dados
        df_selected_sheet = preprocess_data(df_selected_sheet)

        return raw_df, df_selected_sheet, sheet
    
    return None, None, None


# Função para ler a tabela de orçamento do arquivo e aba especificados
def read_budget_table(
    file_path: str, sheet_name: str = DEFAULT_SHEET_NAME
) -> Tuple[pd.DataFrame, Dict[str, Optional[Any]]]:
    """
    Lê a planilha (aba LPU) e retorna apenas a tabela de orçamento.

    Args:
        file_path (str): Caminho do arquivo da planilha.
        sheet_name (str): Nome da aba a ser lida.

    Returns:
        tuple: DataFrame contendo a tabela extraída e dicionário com os metadados.
    """
    # Lê a planilha sem cabeçalho
    raw_df, df_selected_sheet, sheet_name = read_data_budget(
        file_path=file_path, sheet_name=sheet_name, header=None
    )
    
    if isinstance(df_selected_sheet, pd.DataFrame):

        # Localiza o cabeçalho da tabela
        (
            row,
            col,
            pattern,
            columns_found,
        ) = locate_table(df_selected_sheet)

        # Verifica se o cabeçalho foi encontrado
        if row:
            # Extrai os metadados
            metadata = extract_metadata(
                df=df_selected_sheet, metadata_keys=DEFAULT_METADATA_KEYS, pattern_key=pattern
            )

            # Extrai a tabela
            table = extract_table(
                df=df_selected_sheet,
                header_row=row,
                first_col=col,
                columns_found=columns_found,
                col_filter=FILTROS,
                pattern_key=pattern,
            )

            # Retorna a tabela e os metadados
            return table, sheet_name, metadata
    
    return None, None, None


# Função para adicionar e salvar resultados processados em um arquivo
def append_and_save_results(
    all_tables: List[pd.DataFrame],
    all_metadatas: List[Dict[str, Any]],
    output_file: str,
) -> None:
    """
    Adiciona os resultados processados (tabelas e metadados) a um arquivo Excel existente ou cria um novo arquivo e salva os dados.

    Args:
        all_tables (List[pd.DataFrame]): Lista de DataFrames contendo as tabelas processadas.
        all_metadatas (List[Dict[str, Any]]): Lista de dicionários contendo os metadados processados.
        output_file (str): Nome do arquivo de saída.

    Returns:
        None
    """
    # Concatena todas as tabelas
    data_result = pd.concat(all_tables, ignore_index=True)
    
    # Seleciona apenas as colunas desejadas
    data_result = select_columns(data_result, target_columns=SELECTED_COLUMNS)

    # Concatena todos os metadados em um DataFrame
    metadata_result = pd.DataFrame(all_metadatas)

    # Loga o sucesso na concatenação
    logger.info("Todas as tabelas e metadados foram concatenados com sucesso.")

    # Define o caminho completo do arquivo de saída
    output_path = Path(base_dir, DIR_OUTPUTS, output_file)

    # Cria o diretório de saída, se não existir
    output_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        # Salva os dados no arquivo de saída em abas separadas usando export_data
        export_data({"Tables": data_result, "Metadata": metadata_result}, output_path)
        
        print("-"*50)
        
        # Loga o sucesso na exportação
        logger.success(f"Resultados salvos com sucesso em {output_path}")
    except Exception as e:
        logger.error(f"Erro ao salvar os resultados em {output_path}: {e}")


def append_data(list_all_tables, list_all_metadata, file_input, table, metadata):
    """
    Adiciona informações de arquivo e aba à tabela extraída e aos metadados, e os adiciona às respectivas listas.

    Args:
        list_all_tables (List): Lista para armazenar todas as tabelas processadas.
        list_all_metadata (List): Lista para armazenar todos os metadados processados.
        file_input (FileInput): Instância FileInput contendo o caminho do arquivo e o nome da aba.
        table (pd.DataFrame): DataFrame contendo a tabela extraída.
        metadata (Dict): Dicionário contendo os metadados extraídos.

    Returns:
        Tuple[List, List]: Listas atualizadas com a nova tabela e os novos metadados adicionados.
    """
    # Adiciona o nome do arquivo e o nome da aba aos metadados
    metadata_with_source = metadata.copy()
    metadata_with_source["SOURCE_FILE"] = Path(file_input.file_path).name
    metadata_with_source["SHEET_NAME"] = file_input.sheet_name

    # Adiciona os metadados à lista de metadados
    list_all_metadata.append(metadata_with_source)

    # Adiciona o nome do arquivo como coluna na tabela
    table[settings.get("SOURCE_FILE_COLUMN_NAME", "SOURCE_FILE")] = Path(file_input.file_path).name

    # Adiciona o nome da aba como coluna na tabela
    table[settings.get("SHEET_NAME_COLUMN_NAME", "SHEET_NAME")] = file_input.sheet_name

    # Resetando o index da tabela
    table.reset_index(drop=True, inplace=True)

    # Adiciona a tabela à lista de tabelas
    list_all_tables.append(table)

    # Loga o sucesso na extração da tabela e dos metadados
    logger.info(
        f"Tabela e metadados extraídos com sucesso do arquivo: {file_input.file_path}, aba: {file_input.sheet_name}"
    )

    return list_all_tables, list_all_metadata


# Função para obter arquivos de um diretório com filtros opcionais
def get_files_from_directory(
    directory: str,
    extension: Optional[str] = None,
    prefix: Optional[str] = None,
    suffix: Optional[str] = None,
) -> List[Path]:
    """
    Obtém uma lista de arquivos em um diretório com base em filtros opcionais de extensão, prefixo e sufixo.

    Args:
        directory (str): Caminho do diretório.
        extension (Optional[str]): Extensão dos arquivos a serem filtrados (e.g., ".xlsx").
        prefix (Optional[str]): Prefixo dos arquivos a serem filtrados.
        suffix (Optional[str]): Sufixo dos arquivos a serem filtrados.

    Returns:
        List[Path]: Lista de objetos Path correspondentes aos arquivos filtrados.
    """
    dir_path = Path(directory)
    if not dir_path.is_dir():
        raise ValueError(f"O caminho fornecido não é um diretório válido: {directory}")

    files = dir_path.iterdir()
    if extension:
        files = filter(lambda f: f.suffix == extension, files)
    if prefix:
        files = filter(lambda f: f.name.startswith(prefix), files)
    if suffix:
        files = filter(lambda f: f.name.endswith(suffix), files)

    return list(files)


# Função para orquestrar o processamento de múltiplos arquivos de orçamento
def orchestrate_budget_reader(*inputs: Union[FileInput, str], 
                              extensions: Optional[Union[str, List[str]]] = None,
                              prefix: Optional[Union[str, List[str]]] = None,
                              suffix: Optional[Union[str, List[str]]] = None) -> pd.DataFrame:
    """
    Orquestra o processamento de múltiplos arquivos de orçamento ou diretórios.

    Args:
        *inputs (Union[FileInput, str]): Lista de FileInput ou diretórios.
        extensions (Optional[Union[str, List[str]]]): Extensão ou lista de extensões permitidas para arquivos em diretórios.
        prefix (Optional[Union[str, List[str]]]): Prefixo ou lista de prefixos permitidos para arquivos em diretórios.
        suffix (Optional[Union[str, List[str]]]): Sufixo ou lista de sufixos permitidos para arquivos em diretórios.

    Returns:
        pd.DataFrame: DataFrame consolidado com os dados processados.
    """
    all_tables = []  # Lista para armazenar todas as tabelas processadas
    all_metadata = []  # Lista para armazenar todos os metadados processados

    def process_file(file_path: str, sheet_name: Optional[str] = None):
        """
        Processa um único arquivo e adiciona os resultados às listas.

        Args:
            file_path (str): Caminho do arquivo.
            sheet_name (Optional[str]): Nome da aba a ser lida.
        """
        
        print("-"*50)
        logger.info(f"Iniciando o processamento do arquivo: {file_path}")
        
        # Lê a tabela de orçamento do arquivo
        table, sheet_name, metadata = read_budget_table(file_path=file_path, sheet_name=sheet_name)
        
        if isinstance(table, pd.DataFrame):
        
            # Adiciona os resultados às listas
            append_data(all_tables, all_metadata, FileInput(file_path, sheet_name), table, metadata)
            
            # Loga o sucesso no processamento do arquivo
            logger.success(f"Processamento concluído para o arquivo: {file_path}")
            
            return True
            
        else:
            # Loga a falha no processamento do arquivo
            logger.error(f"Falha ao processar o arquivo: {file_path}")
            
            return False

    for input_item in inputs:
        if isinstance(input_item, FileInput):
            # Processa um único arquivo
            _ = process_file(file_path=input_item.file_path, sheet_name=input_item.sheet_name)
        elif isinstance(input_item, str):
            # Processa todos os arquivos em um diretório
            files = get_files_from_directory(
                directory=input_item, 
                extension=extensions if isinstance(extensions, str) else None,
                prefix=tuple(prefix) if isinstance(prefix, list) else prefix,
                suffix=tuple(suffix) if isinstance(suffix, list) else suffix
            )
            for file_path in files:
                _ = process_file(file_path=str(file_path))

    # Verifica se há tabelas processadas
    if all_tables:
        # Concatena e salva os resultados
        append_and_save_results(
            all_tables=all_tables,
            all_metadatas=all_metadata,
            output_file="budget_tables_concatenated.xlsx",
        )

    # Retorna os dados consolidados
    return pd.concat(all_tables, ignore_index=True) if all_tables else pd.DataFrame()

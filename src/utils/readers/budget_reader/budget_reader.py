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
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
from pydantic.dataclasses import dataclass

# Adicionar src ao path
base_dir = Path(__file__).parents[4]
sys.path.insert(0, str(Path(base_dir, "src")))

from config.config_logger import logger
from utils.data.data_functions import read_data, transform_case, filter_columns

# Constantes centralizadas
DEFAULT_SHEET_NAME = "LPU"  # Nome padrão da aba a ser lida
EXPECTED_COLUMNS = [
    "FILTRO",  # Coluna que indica se a linha deve ser filtrada
    "ID",  # Identificador único do item
    "DESCRIÇÃO",  # Descrição do item
    "UN.",  # Unidade de medida
    "UNITÁRIO",  # Preço unitário
    "COMENTÁRIO",  # Comentários adicionais
    "QUANTIDADE",  # Quantidade do item
    "TOTAL",  # Valor total do item
]
ALTERNATIVE_COLUMNS = ["FILTRO", 
                       "ID", 
                       "UN.", 
                       "UNITÁRIO", 
                       "QUANTIDADE"]  # Colunas mínimas alternativas
FILTROS = {"FILTRO": ["SIM"]}  # Nome da coluna usada para filtragem

# Metadados padrão
DEFAULT_METADATA_KEYS = {
    "CÓDIGO_UPE": "UPE",  # Código UPE
    "NUMERO_AGENCIA": "AGÊNCIA|AGENCIA",  # Número da agência
    "NOME_AGENCIA": "NOME DA AGÊNCIA|NOME DA AGENCIA",  # Nome da agência
    "TOTAL": "TOTAL",  # Total geral
    "CONTRATO": "CONTRATO",  # Número do contrato
    "VERSAO": "VERSÃO|VERSAO",  # Versão do documento
    "TIPO": "TIPO",  # Tipo do orçamento
    "QUANTIDADE_SINERGIAS": "QUANTIDADE SINERGIAS",  # Quantidade de sinergias
    "PROGRAMA_DONO": "DONO",  # Dono do orçamento
}

@dataclass
class FileInput:
    """
    Representa um arquivo de entrada com caminho e nome da aba opcional.

    Attributes:
        file_path (str): Caminho do arquivo.
        sheet_name (Optional[str]): Nome da aba a ser lida (padrão: "LPU").
    """
    file_path: str  # Caminho completo do arquivo
    sheet_name: Optional[str] = "LPU"  # Nome da aba a ser lida, padrão "LPU"

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
        "" if pd.isna(val) or (isinstance(val, float) and math.isnan(val)) else str(val).strip().lower()
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
    expected_columns: list = EXPECTED_COLUMNS,
    alternative_columns: list = ALTERNATIVE_COLUMNS,
) -> Tuple[Optional[int], Optional[int], Optional[list]]:
    """
    Detecta a posição (linha, coluna) onde o cabeçalho da tabela começa.

    Args:
        df (pd.DataFrame): DataFrame contendo os dados da planilha.
        expected_columns (list): Lista de colunas esperadas no cabeçalho da tabela.
        alternative_columns (list): Lista alternativa mínima de colunas aceitas.

    Returns:
        tuple: Uma tupla (linha, coluna, colunas_encontradas) indicando a posição do cabeçalho e as colunas encontradas,
               ou (None, None, None) se não encontrado.
    """
    # Normaliza colunas esperadas para uppercase
    normalized_expected = [col.upper() for col in expected_columns]
    
    # Normaliza colunas alternativas para uppercase
    normalized_alternative = [col.upper() for col in alternative_columns]
    
    # Número de colunas esperadas
    num_cols = len(normalized_expected)

    # Itera sobre as linhas do DataFrame
    for row in range(df.shape[0]):
        
        # Itera sobre as colunas possíveis
        for col in range(df.shape[1] - num_cols + 1):
            
            # Extrai valores da linha e colunas
            values = df.iloc[row, col : col + num_cols].tolist()
            
            # Normaliza os valores extraídos para uppercase
            normalized = [str(val).upper() if isinstance(val, str) else val for val in values]

            # Verifica se os valores correspondem às colunas esperadas
            if normalized == normalized_expected:
                return row, col, expected_columns
            
            # Verifica colunas alternativas
            if all(col in normalized for col in normalized_alternative):
                return row, col, alternative_columns

    # Retorna None se não encontrar o cabeçalho
    return None, None, None

# Função auxiliar para encontrar e atribuir valores de metadados a um dicionário
def find_metadata_value(
    row: pd.Series,
    col_idx: int,
    metadata_key: str,
    metadata: Dict[str, Any],
    df: pd.DataFrame,
    row_idx: int,
) -> None:
    """
    Busca e atribui um valor de metadado ao dicionário, descendo pelas linhas até encontrar o valor.

    Args:
        row (pd.Series): Linha do DataFrame.
        col_idx (int): Índice da coluna atual.
        metadata_key (str): Chave do metadado a ser buscado.
        metadata (dict): Dicionário de metadados.
        df (pd.DataFrame): DataFrame completo para buscar o valor nas linhas subsequentes.
        row_idx (int): Índice da linha atual no DataFrame.
    """
    # Verifica se o metadado já foi atribuído
    if metadata[metadata_key] is None:
        # Itera pelas linhas subsequentes
        for next_row_idx in range(row_idx + 1, len(df)):
            # Obtém o valor da célula na linha subsequente
            value = df.iloc[next_row_idx, col_idx]
            if not pd.isna(value):  # Verifica se o valor não é NaN
                metadata[metadata_key] = str(value).upper()  # Atribui o valor encontrado em uppercase
                break  # Interrompe a busca ao encontrar o valor

# Função para extrair metadados dinamicamente do DataFrame
def extract_metadata(
    df: pd.DataFrame, metadata_keys: dict = DEFAULT_METADATA_KEYS
) -> Dict[str, Optional[Any]]:
    """
    Extrai metadados da tabela de orçamento de forma genérica e dinâmica.

    Args:
        df (pd.DataFrame): DataFrame contendo os dados da planilha.
        metadata_keys (dict): Dicionário com as chaves de metadados e padrões de busca.

    Returns:
        dict: Dicionário contendo os metadados extraídos.
    """
    # Inicializa o dicionário de metadados
    metadata = {key: None for key in metadata_keys}

    # Itera sobre as linhas do DataFrame
    for row_idx, row in df.iterrows():
        for col_idx, cell in enumerate(row):  # Itera sobre as células da linha
            if pd.isna(cell):  # Ignora células vazias
                continue

            # Normaliza o valor da célula para uppercase
            cell_str = str(cell).strip().upper()

            # Verifica padrões de metadados
            for key, pattern in metadata_keys.items():
                # Se o metadado ainda não foi encontrado e o padrão corresponde
                if metadata[key] is None and any(p.upper() in cell_str for p in pattern.split("|")):
                    # Busca o valor do metadado
                    find_metadata_value(row, col_idx, key, metadata, df, row_idx)

    return metadata  # Retorna o dicionário de metadados

# Função para extrair a tabela do DataFrame a partir da linha do cabeçalho
def extract_table(
    df: pd.DataFrame,
    header_row: int,
    first_col: int,
    columns_found: list,
    col_filter: str = FILTROS,
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
    header = df.iloc[header_row, first_col:first_col + num_cols].tolist()
    
    # Extrai os dados abaixo do cabeçalho
    data = df.iloc[header_row + 1:, first_col:first_col + num_cols].copy()
    
    # Define o cabeçalho no DataFrame
    data.columns = header
    
    # Aplica pós-processamento e filtros
    return post_process_table(data, cols_expected=columns_found, col_filter=col_filter)

# Função para aplicar filtros e pós-processamento na tabela extraída
def post_process_table(data: pd.DataFrame, 
                       cols_expected: list = [], 
                       col_filter: Dict[str, Any] = FILTROS) -> pd.DataFrame:
    """
    Aplica filtros e pós-processamentos em um DataFrame extraído.

    Args:
        data (pd.DataFrame): DataFrame contendo os dados extraídos da tabela.
        cols_expected (list): Lista de colunas esperadas no cabeçalho.
        col_filter (dict): Dicionário onde a chave é o nome da coluna e o valor pode ser uma string ou uma lista de valores filtráveis.

    Returns:
        pd.DataFrame: DataFrame pós-processado com filtros aplicados.
    """
    # Filtra as colunas esperadas, mantendo apenas as colunas encontradas
    if cols_expected:
        data = filter_columns(df=data, 
                              columns=cols_expected, 
                              allow_partial=True)

    # Aplica os filtros definidos no dicionário col_filter
    for col, filter_values in col_filter.items():
        if col in data.columns:
            # Garante que filter_values seja uma lista
            if isinstance(filter_values, str):
                filter_values = [filter_values]
            
            # Filtra linhas onde o valor está na lista de valores filtráveis
            data = data[data[col].str.lower().isin([val.lower() for val in filter_values])]

    # Padroniza os dados para uppercase
    data = data.applymap(lambda x: str(x).upper() if isinstance(x, str) else x)

    # Reseta o índice do DataFrame
    return data.reset_index(drop=True)

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
    raw_df = read_data(file_path, sheet_name=sheet_name, header=None)
    
    # Pré-processa os dados
    raw_df = preprocess_data(raw_df)
    
    # Localiza o cabeçalho da tabela
    row, col, columns_found = locate_table(raw_df)
    
    # Verifica se o cabeçalho foi encontrado
    if row is None:
        raise ValueError("Cabeçalho da tabela não encontrado na planilha.")
    
    # Extrai os metadados
    metadata = extract_metadata(raw_df)
    
    # Extrai a tabela
    table = extract_table(raw_df, row, col, columns_found)
    
    # Retorna a tabela e os metadados
    return table, metadata

# Função para orquestrar o processamento de múltiplos arquivos de orçamento
def orchestrate_budget_reader(*files: List[FileInput]) -> pd.DataFrame:
    """
    Orquestra a execução do budget_reader.

    Args:
        *files (List[FileInput]): Lista de instâncias FileInput contendo o caminho do arquivo e, opcionalmente, o nome da aba.

    Returns:
        pd.DataFrame: DataFrame concatenado de todas as tabelas processadas.
    """
    all_tables = []  # Lista para armazenar todas as tabelas processadas

    # Itera sobre os arquivos de entrada
    for file_input in files:
        # Loga o início do processamento do arquivo
        logger.info(f"Iniciando processamento do arquivo: {file_input.file_path}, aba: {file_input.sheet_name}")
        try:
            # Lê a tabela
            table, metadata = read_budget_table(file_input.file_path, sheet_name=file_input.sheet_name)
            # Adiciona o nome do arquivo como coluna
            table["source_file"] = Path(file_input.file_path).name
            # Adiciona o nome da aba como coluna
            table["sheet_name"] = file_input.sheet_name
            # Adiciona a tabela à lista
            all_tables.append(table)
            # Loga o sucesso na extração da tabela
            logger.success(f"Tabela extraída com sucesso do arquivo: {file_input.file_path}, aba: {file_input.sheet_name}")
        except Exception as e:
            # Loga o erro ao processar o arquivo
            logger.error(f"Erro ao processar o arquivo {file_input.file_path}, aba {file_input.sheet_name}: {e}")

    # Verifica se há tabelas processadas
    if all_tables:
        # Concatena todas as tabelas
        final_df = pd.concat(all_tables, ignore_index=True)
        # Loga o sucesso na concatenação
        logger.success("Todas as tabelas foram concatenadas com sucesso.")
        # Loga o DataFrame final
        logger.info(final_df)
        return final_df

    # Loga o aviso de que nenhuma tabela foi processada
    logger.warning("Nenhuma tabela foi processada com sucesso.")
    # Retorna um DataFrame vazio se nenhuma tabela foi processada
    return pd.DataFrame()

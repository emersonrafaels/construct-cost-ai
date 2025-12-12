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
from typing import Union, Optional, List, Tuple, Dict, Any

import pandas as pd
from pydantic.dataclasses import dataclass

# Adicionar src ao path
base_dir = Path(__file__).parents[4]
sys.path.insert(0, str(Path(base_dir, "src")))

from config.config_logger import logger
from utils.data.data_functions import read_data

# Constantes centralizadas
DEFAULT_SHEET_NAME = "LPU"  # Nome padrão da aba a ser lida
EXPECTED_COLUMNS = [
    "Filtro",  # Coluna que indica se a linha deve ser filtrada
    "ID",  # Identificador único do item
    "Descrição",  # Descrição do item
    "Un.",  # Unidade de medida
    "Unitário",  # Preço unitário
    "Comentário",  # Comentários adicionais
    "Quantidade",  # Quantidade do item
    "Total",  # Valor total do item
]
ALTERNATIVE_COLUMNS = ["ID", "Un.", "Unitário", "Quantidade"]  # Colunas mínimas alternativas
COL_FILTRO = "Filtro"  # Nome da coluna usada para filtragem

# Metadados padrão
DEFAULT_METADATA_KEYS = {
    "codigo_upe": "upe",  # Código UPE
    "numero_agencia": "agência|agencia",  # Número da agência
    "nome_agencia": "nome da agência|nome da agencia",  # Nome da agência
    "total": "total",  # Total geral
    "contrato": "contrato",  # Número do contrato
    "versao": "versão|versao",  # Versão do documento
    "tipo": "tipo",  # Tipo do orçamento
    "quantidade_sinergias": "quantidade sinergias",  # Quantidade de sinergias
    "dono": "dono",  # Dono do orçamento
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

def preprocess_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Realiza o pré-processamento inicial dos dados, incluindo a remoção de linhas totalmente em branco.

    Args:
        df (pd.DataFrame): DataFrame bruto lido da planilha.

    Returns:
        pd.DataFrame: DataFrame pré-processado.
    """
    return df.dropna(how="all").reset_index(drop=True)  # Remove linhas vazias e reseta o índice

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
    normalized_expected = [col.lower() for col in expected_columns]  # Normaliza colunas esperadas
    normalized_alternative = [col.lower() for col in alternative_columns]  # Normaliza colunas alternativas
    num_cols = len(expected_columns)  # Número de colunas esperadas

    for row in range(df.shape[0]):  # Itera sobre as linhas do DataFrame
        for col in range(df.shape[1] - num_cols + 1):  # Itera sobre as colunas possíveis
            values = df.iloc[row, col : col + num_cols].tolist()  # Extrai valores da linha e colunas
            normalized = normalize_values(values)  # Normaliza os valores extraídos

            if normalized == normalized_expected:  # Verifica se os valores correspondem às colunas esperadas
                return row, col, expected_columns
            if all(col in normalized for col in normalized_alternative):  # Verifica colunas alternativas
                return row, col, alternative_columns

    return None, None, None  # Retorna None se não encontrar o cabeçalho

def find_metadata_value(
    row: pd.Series,
    col_idx: int,
    metadata_key: str,
    metadata: Dict[str, Any],
    df: pd.DataFrame,
    row_idx: int,
) -> None:
    """
    Busca e atribui um valor de metadado ao dicionário, se ainda não atribuído.

    Args:
        row (pd.Series): Linha do DataFrame.
        col_idx (int): Índice da coluna atual.
        metadata_key (str): Chave do metadado a ser buscado.
        metadata (dict): Dicionário de metadados.
        df (pd.DataFrame): DataFrame completo para buscar o valor na linha seguinte.
        row_idx (int): Índice da linha atual no DataFrame.
    """
    if metadata[metadata_key] is None:  # Verifica se o metadado já foi atribuído
        if row_idx + 1 < len(df):  # Verifica se a próxima linha existe
            metadata[metadata_key] = df.iloc[row_idx + 1, col_idx]  # Atribui o valor da próxima linha
        else:
            metadata[metadata_key] = None  # Define como None se não houver próxima linha

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
    metadata = {key: None for key in metadata_keys}  # Inicializa o dicionário de metadados

    for row_idx, row in df.iterrows():  # Itera sobre as linhas do DataFrame
        for col_idx, cell in enumerate(row):  # Itera sobre as células da linha
            if pd.isna(cell):  # Ignora células vazias
                continue

            cell_str = str(cell).strip().lower()  # Normaliza o valor da célula

            for key, pattern in metadata_keys.items():  # Verifica padrões de metadados
                if metadata[key] is None and any(p in cell_str for p in pattern.split("|")):
                    find_metadata_value(row, col_idx, key, metadata, df, row_idx)  # Busca o valor do metadado

    return metadata  # Retorna o dicionário de metadados

def extract_table(
    df: pd.DataFrame,
    header_row: int,
    first_col: int,
    columns_found: list,
    col_filter: str = COL_FILTRO,
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
    num_cols = len(columns_found)  # Número de colunas encontradas
    data = df.iloc[header_row + 1 :, first_col : first_col + num_cols].copy()  # Extrai os dados abaixo do cabeçalho
    data.columns = columns_found  # Define os nomes das colunas
    return post_process_table(data, col_filter=col_filter)  # Aplica pós-processamento

def post_process_table(data: pd.DataFrame, col_filter: str = COL_FILTRO) -> pd.DataFrame:
    """
    Aplica filtros e pós-processamentos em um DataFrame extraído.

    Args:
        data (pd.DataFrame): DataFrame contendo os dados extraídos da tabela.
        col_filter (str): Nome da coluna usada para filtrar linhas vazias.

    Returns:
        pd.DataFrame: DataFrame pós-processado com filtros aplicados.
    """
    data = data.dropna(how="all")  # Remove linhas completamente vazias
    if col_filter in data.columns:  # Verifica se a coluna de filtro existe
        data = data[data[col_filter].str.lower() == "sim"]  # Filtra linhas onde o valor é "sim"
    return data.reset_index(drop=True)  # Reseta o índice do DataFrame

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
    raw_df = read_data(file_path, sheet_name=sheet_name, header=None)  # Lê a planilha sem cabeçalho
    raw_df = preprocess_data(raw_df)  # Pré-processa os dados
    row, col, columns_found = locate_table(raw_df)  # Localiza o cabeçalho da tabela
    if row is None:
        raise ValueError("Cabeçalho da tabela não encontrado na planilha.")
    metadata = extract_metadata(raw_df)  # Extrai os metadados
    table = extract_table(raw_df, row, col, columns_found)  # Extrai a tabela
    return table, metadata  # Retorna a tabela e os metadados

def orchestrate_budget_reader(*files: List[FileInput]) -> pd.DataFrame:
    """
    Orquestra a execução do budget_reader.

    Args:
        *files (List[FileInput]): Lista de instâncias FileInput contendo o caminho do arquivo e, opcionalmente, o nome da aba.

    Returns:
        pd.DataFrame: DataFrame concatenado de todas as tabelas processadas.
    """
    all_tables = []  # Lista para armazenar todas as tabelas processadas

    for file_input in files:  # Itera sobre os arquivos de entrada
        logger.info(f"Iniciando processamento do arquivo: {file_input.file_path}, aba: {file_input.sheet_name}")
        try:
            table, metadata = read_budget_table(file_input.file_path, sheet_name=file_input.sheet_name)  # Lê a tabela
            table["source_file"] = Path(file_input.file_path).name  # Adiciona o nome do arquivo como coluna
            table["sheet_name"] = file_input.sheet_name  # Adiciona o nome da aba como coluna
            all_tables.append(table)  # Adiciona a tabela à lista
            logger.success(f"Tabela extraída com sucesso do arquivo: {file_input.file_path}, aba: {file_input.sheet_name}")
        except Exception as e:
            logger.error(f"Erro ao processar o arquivo {file_input.file_path}, aba {file_input.sheet_name}: {e}")

    if all_tables:  # Verifica se há tabelas processadas
        final_df = pd.concat(all_tables, ignore_index=True)  # Concatena todas as tabelas
        logger.success("Todas as tabelas foram concatenadas com sucesso.")
        logger.info(final_df)  # Loga o DataFrame final
        return final_df

    logger.warning("Nenhuma tabela foi processada com sucesso.")
    return pd.DataFrame()  # Retorna um DataFrame vazio se nenhuma tabela foi processada

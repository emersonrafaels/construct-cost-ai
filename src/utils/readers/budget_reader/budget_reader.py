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
from typing import Union, Optional

import pandas as pd
from pydantic.dataclasses import dataclass

# Adicionar src ao path
base_dir = Path(__file__).parents[4]
sys.path.insert(0, str(Path(base_dir, "src")))

from config.config_logger import logger
from utils.data.data_functions import read_data

# Cabeçalho esperado da tabela
EXPECTED_COLUMNS = [
    "Filtro",
    "ID",
    "Descrição",
    "Un.",
    "Unitário",
    "Comentário",
    "Quantidade",
    "Total",
]

ALTERNATIVE_COLUMNS = [
    "ID",
    "Un.",
    "Unitário",
    "Quantidade",
]

@dataclass
class FileInput:
    file_path: str
    sheet_name: Optional[str] = "LPU"
    

def locate_table(df, expected_columns=EXPECTED_COLUMNS, 
                 alternative_columns=ALTERNATIVE_COLUMNS):
    """
    Procura no DataFrame a linha/coluna onde começa o cabeçalho da tabela:
    Filtro | ID | Descrição | Unidade | Preço Unitário | Comentário | Quantidade | Total
    ou uma alternativa mínima contendo as colunas: ID, Un., Unitário, Quantidade.
    
    Retorna (linha, coluna) do início do cabeçalho.

    Args:
        df (pd.DataFrame): DataFrame contendo os dados da planilha.
        expected_columns (list): Lista de colunas esperadas no cabeçalho da tabela.

    Returns:
        tuple: Uma tupla (linha, coluna) indicando a posição do cabeçalho, ou (None, None) se não encontrado.
    """
    # Normaliza os nomes das colunas esperadas para letras minúsculas
    normalized_expected = [col.lower() for col in expected_columns]

    # Define um conjunto mínimo de colunas que também pode ser aceito como cabeçalho
    normalized_alternative = [col.lower() for col in alternative_columns]

    # Calcula o número de colunas esperadas
    num_cols = len(expected_columns)

    # Itera sobre todas as linhas do DataFrame
    for row in range(df.shape[0]):
        # Itera sobre todas as colunas possíveis, garantindo espaço suficiente para as colunas esperadas
        for col in range(df.shape[1] - num_cols + 1):
            # Extrai os valores do trecho correspondente às colunas esperadas
            values = df.iloc[row, col : col + num_cols].tolist()

            # Normaliza os valores extraídos (remove espaços, converte para minúsculas, substitui NaN por vazio)
            normalized = [
                "" if pd.isna(val) or (isinstance(val, float) and math.isnan(val)) else str(val).strip().lower()
                for val in values
            ]

            # Verifica se os valores normalizados correspondem às colunas esperadas
            if normalized == normalized_expected or all(col in normalized for col in normalized_alternative):
                return row, col  # Retorna a posição do cabeçalho

    # Retorna None, None se o cabeçalho não for encontrado
    return None, None


def extract_table(df, header_row, first_col, expected_columns=EXPECTED_COLUMNS):
    """
    A partir da posição do cabeçalho, extrai a tabela até as linhas vazias.

    Args:
        df (pd.DataFrame): DataFrame contendo os dados da planilha.
        header_row (int): Linha onde o cabeçalho da tabela começa.
        first_col (int): Coluna onde o cabeçalho da tabela começa.
        expected_columns (list): Lista de colunas esperadas na tabela.

    Returns:
        pd.DataFrame: DataFrame contendo apenas a tabela extraída e processada.
    """
    # Calcula o número de colunas esperadas
    num_cols = len(expected_columns)

    # Extrai os dados a partir da linha seguinte ao cabeçalho e das colunas esperadas
    data = df.iloc[header_row + 1 :, first_col : first_col + num_cols].copy()

    # Define os nomes das colunas do DataFrame extraído
    data.columns = expected_columns

    # Remove linhas completamente vazias
    data = data.dropna(how="all")

    # Remove linhas onde a coluna "Filter" está vazia (geralmente rodapés ou espaços)
    data = data[~data["Filter"].isna()]

    # Reseta o índice do DataFrame para uma sequência contínua
    data = data.reset_index(drop=True)

    # Retorna o DataFrame processado
    return data


def read_budget_table(file_path, sheet_name="LPU"):
    """
    Lê a planilha (aba LPU) e retorna apenas a tabela de orçamento
    no formato Filtro | ID | Descrição | ... | Total.
    """
    # Lê tudo como planilha "crua", sem header
    raw_df = read_data(file_path, 
                       sheet_name=sheet_name, 
                       header=None)

    # Localiza o cabeçalho da tabela
    row, col = locate_table(raw_df)
    if row is None:
        raise ValueError("Cabeçalho da tabela não encontrado na planilha.")

    # Extrai só a tabela
    return extract_table(raw_df, row, col)


def orchestrate_budget_reader(*files: FileInput):
    """
    Orquestra a execução do budget_reader.

    Args:
        *files: Lista de instâncias FileInput contendo o caminho do arquivo e, opcionalmente, o nome da aba.

    Returns:
        pd.DataFrame: DataFrame concatenado de todas as tabelas processadas.
    """
    all_tables = []

    for file_input in files:
        
        logger.info(f"Iniciando processamento do arquivo: {file_input.file_path}, aba: {file_input.sheet_name}")
        
        try:
            table = read_budget_table(file_input.file_path, sheet_name=file_input.sheet_name)
            table["source_file"] = Path(file_input.file_path).name
            table["sheet_name"] = file_input.sheet_name
            all_tables.append(table)
            logger.success(f"Tabela extraída com sucesso do arquivo: {file_input.file_path}, aba: {file_input.sheet_name}")
        except Exception as e:
            logger.error(f"Erro ao processar o arquivo {file_input.file_path}, aba {file_input.sheet_name}: {e}")

    if all_tables:
        final_df = pd.concat(all_tables, ignore_index=True)
        logger.success("Todas as tabelas foram concatenadas com sucesso.")
        logger.info(final_df)
        return final_df

    logger.warning("Nenhuma tabela foi processada com sucesso.")
    return pd.DataFrame()

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
__copyright__ = "Copyright 2025, Verificador Inteligente de Orçamentos de Obras"
__credits__ = ["Emerson V. Rafael", "Lucas Ken", "Clarissa Simoyama"]
__license__ = "MIT"
__version__ = "1.0.0"
__maintainer__ = "Emerson V. Rafael (emervin), Lucas Ken, Clarissa Simoyama"
__squad__ = "DataCraft"
__email__ = "emersonssmile@gmail.com"
__status__ = "Production"

import math
import sys
from pathlib import Path

import pandas as pd

# Adicionar src ao path
base_dir = Path(__file__).parents[4]
sys.path.insert(0, str(Path(base_dir, "src")))

from config.config_logger import logger
from utils.data.data_functions import read_data

# Cabeçalho esperado da tabela
EXPECTED_COLUMNS = [
    "Filter",
    "ID",
    "Description",
    "Unit",
    "Unit Price",
    "Comment",
    "Quantity",
    "Total",
]


def read_budget_table(file_path, sheet_name="LPU"):
    """
    Lê a planilha (aba LPU) e retorna apenas a tabela de orçamento
    no formato Filtro | ID | Descrição | ... | Total.
    """
    # Lê tudo como planilha "crua", sem header
    raw_df = read_data(file_path, sheet_name=sheet_name, header=None)

    # Localiza o cabeçalho da tabela
    row, col = locate_table(raw_df)
    if row is None:
        raise ValueError("Cabeçalho da tabela não encontrado na planilha.")

    # Extrai só a tabela
    return extract_table(raw_df, row, col)


def locate_table(df, expected_columns=EXPECTED_COLUMNS):
    """
    Procura no DataFrame a linha/coluna onde começa o cabeçalho da tabela:
    Filter | ID | Description | Unit | Unit Price | Comment | Quantity | Total
    Retorna (linha, coluna) do início do cabeçalho.
    """
    normalized_expected = [col.lower() for col in expected_columns]
    num_cols = len(expected_columns)

    for row in range(df.shape[0]):
        for col in range(df.shape[1] - num_cols + 1):
            values = df.iloc[row, col : col + num_cols].tolist()

            normalized = [
                "" if pd.isna(val) or (isinstance(val, float) and math.isnan(val)) else str(val).strip().lower()
                for val in values
            ]

            if normalized == normalized_expected:
                return row, col

    return None, None


def extract_table(df, header_row, first_col, expected_columns=EXPECTED_COLUMNS):
    """
    A partir da posição do cabeçalho, extrai a tabela até as linhas vazias.
    """
    num_cols = len(expected_columns)

    # Tudo que vem depois do cabeçalho, nas mesmas colunas
    data = df.iloc[header_row + 1 :, first_col : first_col + num_cols].copy()

    # Define o nome correto das colunas
    data.columns = expected_columns

    # Remove linhas totalmente vazias
    data = data.dropna(how="all")

    # Remove linhas sem valor no campo Filtro (em geral são espaços/rodapés)
    data = data[~data["Filter"].isna()]

    # Ajusta índice
    data = data.reset_index(drop=True)

    return data


def orchestrate_budget_reader(file_list, sheet_name="LPU"):
    """
    Orquestra a execução do budget_reader.
    """
    all_tables = []

    for file_path in file_list:
        try:
            table = read_budget_table(file_path, sheet_name=sheet_name)
            table["source_file"] = Path(file_path).name
            all_tables.append(table)
            logger.success(f"Tabela extraída com sucesso do arquivo: {file_path}")
        except Exception as e:
            logger.error(f"Erro ao processar o arquivo {file_path}: {e}")

    if all_tables:
        final_df = pd.concat(all_tables, ignore_index=True)
        logger.success("Tabelas concatenadas com sucesso.")
        logger.info(final_df)
        return final_df

    logger.warning("Nenhuma tabela foi processada com sucesso.")
    return pd.DataFrame()


if __name__ == "__main__":
    # Exemplo com um único arquivo
    file_path = r"C:\Users\emers\OneDrive\Área de Trabalho\Itaú\CICF\DataCraft\Verificador Inteligente de Obras\codes\construct-cost-ai\data\sample_padrao2_fg.xlsx"
    sheet_name = "LPU"

    orchestrate_budget_reader([file_path], sheet_name=sheet_name)

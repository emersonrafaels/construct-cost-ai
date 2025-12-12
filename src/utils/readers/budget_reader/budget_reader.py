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
from src.utils.data.data_functions import read_data

# Cabeçalho esperado da tabela
COLS_EXPECTED = [
    "Filtro",
    "ID",
    "Descrição",
    "Un.",
    "Unitário",
    "Comentário",
    "Quantidade",
    "Total",
]


def ler_planilha_tabela_orcamento(caminho_arquivo, nome_aba="LPU"):
    """
    Lê a planilha (aba LPU) e retorna apenas a tabela de orçamento
    no formato Filtro | ID | Descrição | ... | Total.
    """
    # Lê tudo como planilha "crua", sem header
    df_raw = read_data(caminho_arquivo, sheet_name=nome_aba, header=None)

    # Localiza o cabeçalho da tabela
    r, c = localizar_tabela(df_raw)
    if r is None:
        raise ValueError("Cabeçalho da tabela não encontrado na planilha.")

    # Extrai só a tabela
    return extrair_tabela(df_raw, r, c)


def localizar_tabela(df, cols_esperadas=COLS_EXPECTED):
    """
    Procura no DataFrame a linha/coluna onde começa o cabeçalho da tabela:
    Filtro | ID | Descrição | Un. | Unitário | Comentário | Quantidade | Total
    Retorna (linha, coluna) do início do cabeçalho.
    """
    cols_exp_norm = [c.lower() for c in cols_esperadas]
    n = len(cols_esperadas)

    for r in range(df.shape[0]):
        for c in range(df.shape[1] - n + 1):
            vals = df.iloc[r, c : c + n].tolist()

            norm = []
            for v in vals:
                if (isinstance(v, float) and math.isnan(v)) or pd.isna(v):
                    norm.append("")
                else:
                    norm.append(str(v).strip().lower())

            if norm == cols_exp_norm:
                return r, c

    return None, None


def extrair_tabela(df, header_row, first_col, cols_esperadas=COLS_EXPECTED):
    """
    A partir da posição do cabeçalho, extrai a tabela até as linhas vazias.
    """
    n = len(cols_esperadas)

    # Tudo que vem depois do cabeçalho, nas mesmas colunas
    data = df.iloc[header_row + 1 :, first_col : first_col + n].copy()

    # Define o nome correto das colunas
    data.columns = cols_esperadas

    # Remove linhas totalmente vazias
    data = data.dropna(how="all")

    # Remove linhas sem valor no campo Filtro (em geral são espaços/rodapés)
    data = data[~data["Filtro"].isna()]

    # Se quiser só as linhas com Filtro == "Sim", descomente:
    # data = data[data["Filtro"].astype(str).str.strip().str.lower() == "sim"]

    # Ajusta índice
    data = data.reset_index(drop=True)

    return data


def orchestrator_budget_reader(list_files):
    """Orquestra a execução do budget_reader."""

    try:
        tabela = ler_planilha_tabela_orcamento(caminho, nome_aba="LPU")
        logger.success(f"Tabela extraída com sucesso do arquivo: {caminho}")
        logger.info(tabela)
    except Exception as e:
        logger.error(f"Erro ao processar o arquivo {caminho}: {e}")

    # Exemplo lendo vários .xlsx de uma pasta e concatenando
    pasta = Path(".")
    todas_tabelas = []

    for arq in pasta.glob("*.xlsx"):
        try:
            df_tab = ler_planilha_tabela_orcamento(arq, nome_aba="LPU")
            df_tab["arquivo_origem"] = arq.name
            todas_tabelas.append(df_tab)
            logger.success(f"Tabela extraída com sucesso do arquivo: {arq.name}")
        except Exception as e:
            logger.error(f"Erro ao processar {arq.name}: {e}")

    if todas_tabelas:
        df_final = pd.concat(todas_tabelas, ignore_index=True)
        logger.success("Tabelas concatenadas com sucesso.")
        logger.info(df_final)
    else:
        logger.warning("Nenhuma tabela foi processada com sucesso.")


if __name__ == "__main__":
    # Exemplo com um único arquivo
    caminho = r"C:\Users\emers\OneDrive\Área de Trabalho\Itaú\CICF\DataCraft\Verificador Inteligente de Obras\codes\construct-cost-ai\data\sample_padrao2_fg.xlsx"

    orchestrator_budget_reader(caminho)

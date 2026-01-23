"""
Realiza o backtest completo do produto: Módulo de Validação LPU (Lista de Preços Unitários)

1) Lê orçamentos a partir de um diretório específico.
2) Aplica o módulo de validação LPU para cruzar orçamentos com dados
3) Aplica o módulo de validação Não LPU - Match Fuzzy

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

# Adicionar src ao path
base_dir = Path(__file__).parents[2]
sys.path.insert(0, str(Path(base_dir, "src")))

from utils.readers.budget_reader.budget_reader import orchestrate_budget_reader
from examples.backtest.utils.merge_backtest_saude_esteira import merge_backtest_saude_esteira


def main_orchestrate_budget_reader():

    # Executando a orquestração do módulo de leitura de orçamentos
    df_result_tables = orchestrate_budget_reader(
        Path(Path(__file__).parents[2], "data/inputs/orcamentos"),
        extensions=[".xlsx", ".xlsm", ".xls"],
        recursive=True,
    )

    # Realizando a leitura dos dados de saude da esteira
    df_result_tables = merge_backtest_saude_esteira(df=df_result_tables)


if __name__ == "__main__":

    # Executando a orquestração do módulo de leitura de orçamentos
    main_orchestrate_budget_reader()

"""
Realiza o uso do Módulo: budget_reader
------------------------

Responsável por localizar e extrair, de forma robusta e independente de posição,
a tabela principal de itens de orçamento no padrão utilizado pelas construtoras
(GOT), normalmente presente na aba "LPU" das planilhas recebidas.

Este módulo foi projetado para suportar arquivos enviados por diferentes fornecedores.
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

from utils.readers.budget_reader.budget_reader import orchestrate_budget_reader, FileInput

if __name__ == "__main__":

    # # Exemplo com múltiplos arquivos e nomes de abas opcionais
    # orchestrate_budget_reader(
    #     FileInput(
    #         file_path=r"C:\Users\emers\OneDrive\Área de Trabalho\Itaú\CICF\DataCraft\Verificador Inteligente de Obras\codes\construct-cost-ai\data\sample_padrao1.xlsx",
    #     ),
    #     FileInput(
    #         file_path=r"C:\Users\emers\OneDrive\Área de Trabalho\Itaú\CICF\DataCraft\Verificador Inteligente de Obras\codes\construct-cost-ai\data\sample_padrao2_fg.xlsx",
    #         sheet_name="LPU",
    #     ),
    #     FileInput(
    #         file_path=r"C:\Users\emers\OneDrive\Área de Trabalho\Itaú\CICF\DataCraft\Verificador Inteligente de Obras\codes\construct-cost-ai\data\sample_padrao2_japj.xlsx"
    #     ),
    # )

    # Exemplo com múltiplos arquivos e nomes de abas opcionais
    # orchestrate_budget_reader(
    #     FileInput(
    #         file_path=r"C:\Users\emers\OneDrive\Área de Trabalho\Itaú\CICF\DataCraft\Verificador Inteligente de Obras\codes\construct-cost-ai\data\sample_padrao2_fg.xlsx",
    #     ),
    #     FileInput(
    #         file_path=r"C:\Users\emers\OneDrive\Área de Trabalho\Itaú\CICF\DataCraft\Verificador Inteligente de Obras\codes\construct-cost-ai\data\sample_padrao2_japj.xlsx"
    #     ),
    # )

    # Exemplo com diretório
    orchestrate_budget_reader(
        Path(Path(__file__).parents[2], "data/inputs/orcamentos"),
        extensions=[".xlsx", ".xlsm", ".xls"],
    )

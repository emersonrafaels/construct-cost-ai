"""
Realiza o uso do Módulo: validator_lpu
------------------------

Este script exemplifica como utilizar o módulo de validação LPU (Lista de Preços Unitários) para cruzar orçamentos com dados de LPU, metadados, agências e construtoras. Ele demonstra a leitura de arquivos de orçamento a partir de um diretório específico e a aplicação do módulo de validação para verificar a consistência dos dados.
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
from construct_cost_ai.domain.validators.lpu.validator_lpu import orchestrate_validate_lpu

if __name__ == "__main__":
    
    # Executa a orquestração do módulo de validação LPU
    orchestrate_validate_lpu()

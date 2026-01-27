"""
Realiza o uso do Módulo: validator_nlpu
------------------------

Este script exemplifica como utilizar o módulo de validação Não LPU (Lista de Preços Unitários) para buscar matches aproximados entre orçamentos não LPU e uma base de LPU, utilizando técnicas de fuzzy matching ou contexto semântico
"""

__author__ = "Emerson V. Rafael (emervin)"
__copyright__ = "Verificador Inteligente de Orçamentos de Obras"
__credits__ = ["Emerson V. Rafael", "Clarissa Simoyama"]
__license__ = "MIT"
__version__ = "1.0.0"
__maintainer__ = "Emerson V. Rafael (emervin), Clarissa Simoyama (simoyam)"
__squad__ = "DataCraft"
__email__ = "emersonssmile@gmail.com"
__status__ = "Development"

import sys
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")

# Adicionar src ao path
base_dir = Path(__file__).parents[2]
sys.path.insert(0, str(Path(base_dir, "src")))

from construct_cost_ai.domain.validators.nlpu.validator_nlpu import NLPUValidator

if __name__ == "__main__":

    # Executa a orquestração do módulo de validação LPU
    nlpu_validator = NLPUValidator()
    df_result = nlpu_validator.orchestrate_validate_nlpu()
"""
Quick Start - Validador LPU.

Exemplo mínimo de uso do validador de orçamentos LPU.
"""

__author__ = "Emerson V. Rafael (emervin)"
__copyright__ = "Copyright 2025, Construct Cost AI"
__credits__ = ["Emerson V. Rafael"]
__license__ = "MIT"
__version__ = "1.0.0"
__maintainer__ = "Emerson V. Rafael"
__email__ = "emersonssmile@gmail.com"
__status__ = "Production"

import sys
from pathlib import Path

# Adicionar src ao path
base_dir = Path(__file__).parent.parent
sys.path.insert(0, str(Path(base_dir, "src")))

from construct_cost_ai.domain import validar_lpu
from config.config_logger import logger

# ========================================
# USO BÁSICO (1 linha)
# ========================================
logger.info("Executando validação LPU...")
df = validar_lpu()

# ========================================
# ANÁLISE RÁPIDA
# ========================================
logger.debug("=" * 80)
logger.info("ANÁLISE RÁPIDA")
logger.debug("=" * 80)

# Resumo por status
logger.info("📊 Resumo por Status:")
logger.info(f"\n{df['status_conciliacao'].value_counts()}")

# Top 5 divergências
logger.info("🔴 Top 5 Maiores Divergências:")
logger.info(
    f"\n{df.nlargest(5, 'dif_total')[['cod_item', 'nome', 'dif_total', 'status_conciliacao']].to_string(index=False)}"
)

# Total para ressarcimento
ressarcimento = df[df["status_conciliacao"] == "Para ressarcimento"]
total = ressarcimento["dif_total"].sum()
logger.info(f"\n💰 Total para ressarcimento: R$ {total:,.2f}")

logger.success("\n✅ Resultados salvos em: outputs/")

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

from pathlib import Path
import sys

# Adicionar src ao path
base_dir = Path(__file__).parent.parent
sys.path.insert(0, str(Path(base_dir, "src")))

from construct_cost_ai.domain import validar_lpu

# ========================================
# USO BÁSICO (1 linha)
# ========================================
print("Executando validação LPU...")
df = validar_lpu()

# ========================================
# ANÁLISE RÁPIDA
# ========================================
print("\n" + "="*80)
print("ANÁLISE RÁPIDA")
print("="*80)

# Resumo por status
print("\n📊 Resumo por Status:")
print(df['status_conciliacao'].value_counts())

# Top 5 divergências
print("\n🔴 Top 5 Maiores Divergências:")
print(df.nlargest(5, 'dif_total')[
    ['cod_item', 'nome', 'dif_total', 'status_conciliacao']
].to_string(index=False))

# Total para ressarcimento
ressarcimento = df[df['status_conciliacao'] == 'Para ressarcimento']
total = ressarcimento['dif_total'].sum()
print(f"\n💰 Total para ressarcimento: R$ {total:,.2f}")

print("\n✅ Resultados salvos em: outputs/")

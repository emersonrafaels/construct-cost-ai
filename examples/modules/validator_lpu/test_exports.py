"""
Script de teste para verificar as funcionalidades de exportação.

Este script testa as funções de geração de relatórios em Excel completo e HTML.
"""

__author__ = "Emerson V. Rafael (emervin)"
__copyright__ = "Copyright 2026, Verificador Inteligente de Orçamentos de Obras, DataCraft"
__credits__ = ["Emerson V. Rafael"]
__license__ = "MIT"
__version__ = "1.0.0"
__maintainer__ = "Emerson V. Rafael"
__email__ = "emersonssmile@gmail.com"
__status__ = "Development"

from pathlib import Path
import sys

# Adicionar o diretório src ao path
base_dir = Path(__file__).parent.parent
sys.path.insert(0, str(Path(base_dir, "src")))

from construct_cost_ai.domain.validators.lpu.validator_lpu import (
    validar_lpu,
    gerar_relatorio_html,
    gerar_relatorio_excel_completo,
)
from config.config_logger import logger


def test_exports():
    """Testa as exportações em Excel e HTML."""

    # Configurar caminhos
    caminho_orcamento = Path(base_dir, "data", "orcamento_exemplo.xlsx")
    caminho_lpu = Path(base_dir, "data", "lpu_exemplo.xlsx")
    output_dir = Path(base_dir, "outputs", "test_exports")

    logger.debug("=" * 80)
    logger.info("TESTE DE EXPORTAÇÕES - Excel + HTML")
    logger.debug("=" * 80)

    # Executar validação
    logger.info("🔄 Executando validação...")
    df_resultado = validar_lpu(
        caminho_orcamento=caminho_orcamento,
        caminho_lpu=caminho_lpu,
        output_dir=output_dir,
        verbose=False,
    )

    logger.success(f"✅ Validação concluída: {len(df_resultado)} itens processados")

    # Testar exportações individuais
    logger.info("📊 Testando exportação Excel completo...")
    gerar_relatorio_excel_completo(df_resultado, output_dir, "teste_excel_completo")

    logger.info("🌐 Testando exportação HTML...")
    gerar_relatorio_html(df_resultado, output_dir, "teste_html")

    logger.debug("=" * 80)
    logger.success("✅ TESTES CONCLUÍDOS COM SUCESSO!")
    logger.debug("=" * 80)

    logger.info(f"📁 Arquivos gerados em: {output_dir.resolve()}")
    logger.debug("Arquivos criados:")
    logger.debug("✅ validacao_lpu.xlsx (4 abas)")
    logger.debug("✅ validacao_lpu.csv")
    logger.debug("✅ relatorio_completo_validacao_lpu.xlsx (11+ abas)")
    logger.debug("✅ relatorio_validacao_lpu.html")
    logger.debug("✅ teste_excel_completo.xlsx (teste individual)")
    logger.debug("✅ teste_html.html (teste individual)")
    logger.debug("=" * 80)


if __name__ == "__main__":
    try:
        test_exports()
    except Exception as e:
        print(f"\n❌ ERRO: {e}\n")
        import traceback

        traceback.print_exc()
        sys.exit(1)

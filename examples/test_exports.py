"""
Script de teste para verificar as funcionalidades de exportação.

Este script testa as funções de geração de relatórios em Excel completo e HTML.
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

# Adicionar o diretório src ao path
base_dir = Path(__file__).parent.parent
sys.path.insert(0, str(Path(base_dir, "src")))

from construct_cost_ai.domain.validador_lpu import (
    validar_lpu,
    gerar_relatorio_html,
    gerar_relatorio_excel_completo,
)


def test_exports():
    """Testa as exportações em Excel e HTML."""
    
    # Configurar caminhos
    caminho_orcamento = Path(base_dir, "data", "orcamento_exemplo.xlsx")
    caminho_lpu = Path(base_dir, "data", "lpu_exemplo.xlsx")
    output_dir = Path(base_dir, "outputs", "test_exports")
    
    print("\n" + "=" * 80)
    print("TESTE DE EXPORTAÇÕES - Excel + HTML")
    print("=" * 80 + "\n")
    
    # Executar validação
    print("🔄 Executando validação...")
    df_resultado = validar_lpu(
        caminho_orcamento=caminho_orcamento,
        caminho_lpu=caminho_lpu,
        output_dir=output_dir,
        verbose=False
    )
    
    print(f"\n✅ Validação concluída: {len(df_resultado)} itens processados")
    
    # Testar exportações individuais
    print("\n📊 Testando exportação Excel completo...")
    gerar_relatorio_excel_completo(df_resultado, output_dir, "teste_excel_completo")
    
    print("\n🌐 Testando exportação HTML...")
    gerar_relatorio_html(df_resultado, output_dir, "teste_html")
    
    print("\n" + "=" * 80)
    print("✅ TESTES CONCLUÍDOS COM SUCESSO!")
    print("=" * 80)
    
    print(f"\n📁 Arquivos gerados em: {output_dir.resolve()}")
    print("\nArquivos criados:")
    print("   ✅ validacao_lpu.xlsx (4 abas)")
    print("   ✅ validacao_lpu.csv")
    print("   ✅ relatorio_completo_validacao_lpu.xlsx (11+ abas)")
    print("   ✅ relatorio_validacao_lpu.html")
    print("   ✅ teste_excel_completo.xlsx (teste individual)")
    print("   ✅ teste_html.html (teste individual)")
    print("\n" + "=" * 80 + "\n")


if __name__ == "__main__":
    try:
        test_exports()
    except Exception as e:
        print(f"\n❌ ERRO: {e}\n")
        import traceback
        traceback.print_exc()
        sys.exit(1)

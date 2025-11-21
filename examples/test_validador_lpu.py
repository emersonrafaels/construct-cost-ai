"""
Script de exemplo para testar o Validador LPU.

Este script demonstra como usar o módulo validador_lpu para conciliar
orçamentos com a base de preços LPU.
"""

from pathlib import Path
import sys

# Adicionar o diretório src ao path
base_dir = Path(__file__).parent.parent
sys.path.insert(0, str(base_dir / "src"))

from construct_cost_ai.domain.validador_lpu import (
    validar_lpu,
    carregar_orcamento,
    carregar_lpu,
    ValidadorLPUError
)


def exemplo_1_validacao_completa():
    """Exemplo 1: Validação completa com arquivos de exemplo."""
    print("\n" + "=" * 80)
    print("EXEMPLO 1: Validação Completa")
    print("=" * 80 + "\n")
    
    # Definir caminhos
    caminho_orcamento = base_dir / "data" / "orcamento_exemplo.xlsx"
    caminho_lpu = base_dir / "data" / "lpu_exemplo.xlsx"
    output_dir = base_dir / "outputs"
    
    try:
        # Executar validação completa
        df_resultado = validar_lpu(
            caminho_orcamento=caminho_orcamento,
            caminho_lpu=caminho_lpu,
            output_dir=output_dir,
            verbose=True
        )
        
        print("\n✅ Validação executada com sucesso!")
        print(f"   Total de registros: {len(df_resultado)}")
        
        return df_resultado
        
    except ValidadorLPUError as e:
        print(f"\n❌ Erro na validação: {e}")
        return None


def exemplo_2_analise_divergencias():
    """Exemplo 2: Análise detalhada de divergências."""
    print("\n" + "=" * 80)
    print("EXEMPLO 2: Análise de Divergências")
    print("=" * 80 + "\n")
    
    # Definir caminhos
    caminho_orcamento = base_dir / "data" / "orcamento_exemplo.xlsx"
    caminho_lpu = base_dir / "data" / "lpu_exemplo.xlsx"
    output_dir = base_dir / "outputs"
    
    try:
        # Executar validação sem verbose para análise customizada
        df_resultado = validar_lpu(
            caminho_orcamento=caminho_orcamento,
            caminho_lpu=caminho_lpu,
            output_dir=output_dir,
            verbose=False
        )
        
        print("📊 ANÁLISE DE DIVERGÊNCIAS\n")
        
        # Top 10 maiores divergências absolutas
        print("🔴 TOP 10 Maiores Divergências (Valor Absoluto):")
        print("-" * 80)
        top_divergencias = df_resultado.nlargest(10, 'dif_total')[
            ['cod_item', 'nome', 'unitario_orcado', 'unitario_lpu', 
             'dif_unitario', 'dif_total', 'status_conciliacao']
        ]
        print(top_divergencias.to_string(index=False))
        
        # Top 10 maiores divergências percentuais
        print("\n\n📈 TOP 10 Maiores Divergências (Percentual):")
        print("-" * 80)
        df_resultado['perc_dif_abs'] = abs(df_resultado['perc_dif'])
        top_perc = df_resultado.nlargest(10, 'perc_dif_abs')[
            ['cod_item', 'nome', 'unitario_orcado', 'unitario_lpu', 
             'perc_dif', 'status_conciliacao']
        ]
        print(top_perc.to_string(index=False))
        
        # Itens para ressarcimento
        print("\n\n💰 ITENS PARA RESSARCIMENTO:")
        print("-" * 80)
        ressarcimento = df_resultado[
            df_resultado['status_conciliacao'] == 'Para ressarcimento'
        ]
        total_ressarcimento = ressarcimento['dif_total'].sum()
        print(f"Total de itens: {len(ressarcimento)}")
        print(f"Valor total para ressarcimento: R$ {total_ressarcimento:,.2f}")
        
        if len(ressarcimento) > 0:
            print("\nPrimeiros 5 itens:")
            print(ressarcimento.head()[
                ['cod_item', 'nome', 'unitario_orcado', 'unitario_lpu', 'dif_total']
            ].to_string(index=False))
        
        return df_resultado
        
    except ValidadorLPUError as e:
        print(f"\n❌ Erro na validação: {e}")
        return None


def exemplo_3_filtros_customizados():
    """Exemplo 3: Aplicando filtros customizados."""
    print("\n" + "=" * 80)
    print("EXEMPLO 3: Filtros Customizados")
    print("=" * 80 + "\n")
    
    # Definir caminhos
    caminho_orcamento = base_dir / "data" / "orcamento_exemplo.xlsx"
    caminho_lpu = base_dir / "data" / "lpu_exemplo.xlsx"
    output_dir = base_dir / "outputs"
    
    try:
        df_resultado = validar_lpu(
            caminho_orcamento=caminho_orcamento,
            caminho_lpu=caminho_lpu,
            output_dir=output_dir,
            verbose=False
        )
        
        # Filtro 1: Divergências acima de 10%
        print("🎯 FILTRO 1: Divergências > 10%")
        print("-" * 80)
        divergencias_altas = df_resultado[
            abs(df_resultado['perc_dif']) > 10
        ]
        print(f"Itens encontrados: {len(divergencias_altas)}")
        if len(divergencias_altas) > 0:
            print(divergencias_altas[
                ['cod_item', 'nome', 'perc_dif', 'dif_total', 'status_conciliacao']
            ].head(10).to_string(index=False))
        
        # Filtro 2: Itens de uma categoria específica
        if 'categoria' in df_resultado.columns:
            categorias = df_resultado['categoria'].unique()
            if len(categorias) > 0:
                categoria_exemplo = categorias[0]
                print(f"\n\n🎯 FILTRO 2: Categoria = '{categoria_exemplo}'")
                print("-" * 80)
                por_categoria = df_resultado[
                    df_resultado['categoria'] == categoria_exemplo
                ]
                print(f"Itens encontrados: {len(por_categoria)}")
                print(f"\nResumo:")
                print(por_categoria['status_conciliacao'].value_counts())
        
        # Filtro 3: Valores unitários acima de R$ 1000
        print("\n\n🎯 FILTRO 3: Itens com valor unitário > R$ 1.000,00")
        print("-" * 80)
        valores_altos = df_resultado[
            df_resultado['unitario_orcado'] > 1000
        ]
        print(f"Itens encontrados: {len(valores_altos)}")
        if len(valores_altos) > 0:
            print(valores_altos[
                ['cod_item', 'nome', 'unitario_orcado', 'unitario_lpu', 
                 'dif_unitario', 'status_conciliacao']
            ].to_string(index=False))
        
        return df_resultado
        
    except ValidadorLPUError as e:
        print(f"\n❌ Erro na validação: {e}")
        return None


def exemplo_4_uso_modular():
    """Exemplo 4: Uso modular das funções."""
    print("\n" + "=" * 80)
    print("EXEMPLO 4: Uso Modular")
    print("=" * 80 + "\n")
    
    caminho_orcamento = base_dir / "data" / "orcamento_exemplo.xlsx"
    caminho_lpu = base_dir / "data" / "lpu_exemplo.xlsx"
    
    try:
        # Passo 1: Carregar dados separadamente
        print("📂 Passo 1: Carregando dados...")
        df_orcamento = carregar_orcamento(caminho_orcamento)
        df_lpu = carregar_lpu(caminho_lpu)
        print(f"   Orçamento: {len(df_orcamento)} itens")
        print(f"   LPU: {len(df_lpu)} itens")
        
        # Passo 2: Análise prévia do orçamento
        print("\n📊 Passo 2: Análise do orçamento...")
        print(f"   Categorias: {df_orcamento['categoria'].nunique()}")
        print(f"   UPEs: {df_orcamento['cod_upe'].nunique()}")
        print(f"   Valor total: R$ {df_orcamento['total_orcado'].sum():,.2f}")
        
        # Passo 3: Análise da base LPU
        print("\n📊 Passo 3: Análise da base LPU...")
        print(f"   Fontes: {df_lpu['fonte'].nunique()}")
        print(f"   Fontes disponíveis: {', '.join(df_lpu['fonte'].unique())}")
        
        # Passo 4: Executar validação completa
        print("\n🔗 Passo 4: Executando validação completa...")
        df_resultado = validar_lpu(
            caminho_orcamento=caminho_orcamento,
            caminho_lpu=caminho_lpu,
            output_dir=base_dir / "outputs",
            verbose=False
        )
        print(f"   ✅ Validação concluída: {len(df_resultado)} itens processados")
        
        return df_resultado
        
    except ValidadorLPUError as e:
        print(f"\n❌ Erro: {e}")
        return None


def main():
    """Executa todos os exemplos."""
    print("\n" + "=" * 80)
    print("DEMONSTRAÇÃO DO VALIDADOR LPU")
    print("=" * 80)
    
    exemplos = [
        ("Validação Completa", exemplo_1_validacao_completa),
        ("Análise de Divergências", exemplo_2_analise_divergencias),
        ("Filtros Customizados", exemplo_3_filtros_customizados),
        ("Uso Modular", exemplo_4_uso_modular),
    ]
    
    print("\nEscolha um exemplo para executar:")
    print("0 - Executar todos")
    for i, (nome, _) in enumerate(exemplos, 1):
        print(f"{i} - {nome}")
    
    try:
        escolha = input("\nSua escolha (0-4): ").strip()
        
        if escolha == "0":
            for nome, func in exemplos:
                func()
                input("\nPressione ENTER para continuar...")
        elif escolha in ["1", "2", "3", "4"]:
            idx = int(escolha) - 1
            exemplos[idx][1]()
        else:
            print("Opção inválida! Executando todos os exemplos...")
            for nome, func in exemplos:
                func()
                input("\nPressione ENTER para continuar...")
    
    except KeyboardInterrupt:
        print("\n\n⚠️ Execução interrompida pelo usuário.")
    except Exception as e:
        print(f"\n❌ Erro: {e}")
    
    print("\n" + "=" * 80)
    print("FIM DA DEMONSTRAÇÃO")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    main()

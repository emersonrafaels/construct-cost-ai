"""
Script de exemplo para testar o Validador LPU.

Este script demonstra como usar o módulo validador_lpu para conciliar
orçamentos com a base de preços LPU com opções configuráveis.
"""

from pathlib import Path
from typing import Optional
import sys

# Adicionar o diretório src ao path
base_dir = Path(__file__).parent.parent
sys.path.insert(0, str(base_dir / "src"))

from construct_cost_ai.domain.validators.lpu.validator_lpu import (
    validar_lpu,
    load_budget,
    carregar_lpu,
    cruzar_orcamento_lpu,
    calcular_divergencias,
    ValidatorLPUError,
)
import pandas as pd


def executar_validacao(
    caminho_orcamento: Optional[str] = None,
    caminho_lpu: Optional[str] = None,
    output_dir: Optional[str] = None,
    verbose: bool = True,
    gerar_estatisticas: bool = True,
    gerar_top_divergencias: bool = False,
    top_n: int = 10,
    gerar_analise_categorias: bool = False,
    gerar_analise_upes: bool = False,
    filtro_percentual: Optional[float] = None,
    filtro_categoria: Optional[str] = None,
    filtro_valor_minimo: Optional[float] = None,
    exibir_preview: bool = True,
    analise_modular: bool = False,
) -> Optional[pd.DataFrame]:
    """
    Executa validação LPU com opções configuráveis.

    Args:
        caminho_orcamento: Caminho do arquivo de orçamento (padrão: data/orcamento_exemplo.xlsx)
        caminho_lpu: Caminho do arquivo LPU (padrão: data/lpu_exemplo.xlsx)
        output_dir: Diretório de saída (padrão: outputs)
        verbose: Exibir progresso detalhado durante validação
        gerar_estatisticas: Gerar estatísticas resumidas
        gerar_top_divergencias: Gerar ranking de maiores divergências
        top_n: Quantidade de itens no ranking (padrão: 10)
        gerar_analise_categorias: Gerar análise por categoria
        gerar_analise_upes: Gerar análise por UPE
        filtro_percentual: Filtrar divergências acima deste percentual (ex: 10.0 para 10%)
        filtro_categoria: Filtrar por categoria específica
        filtro_valor_minimo: Filtrar itens com valor unitário acima deste valor
        exibir_preview: Exibir preview dos primeiros resultados
        analise_modular: Executar análise modular passo a passo

    Returns:
        DataFrame com resultados da validação ou None em caso de erro

    Exemplos:
        # Validação simples
        >>> executar_validacao()

        # Validação com top divergências
        >>> executar_validacao(gerar_top_divergencias=True, top_n=5)

        # Validação com filtros
        >>> executar_validacao(
        ...     filtro_percentual=10.0,
        ...     filtro_categoria="Estrutura e Alvenaria"
        ... )

        # Análise completa
        >>> executar_validacao(
        ...     verbose=True,
        ...     gerar_estatisticas=True,
        ...     gerar_top_divergencias=True,
        ...     gerar_analise_categorias=True,
        ...     gerar_analise_upes=True
        ... )
    """
    # Configurar caminhos padrão
    if caminho_orcamento is None:
        caminho_orcamento = base_dir / "data" / "orcamento_exemplo.xlsx"
    if caminho_lpu is None:
        caminho_lpu = base_dir / "data" / "lpu_exemplo.xlsx"
    if output_dir is None:
        output_dir = base_dir / "outputs"

    print("\n" + "=" * 80)
    print("VALIDADOR LPU - ANÁLISE CONFIGURÁVEL")
    print("=" * 80 + "\n")

    try:
        # ====================================================================
        # ANÁLISE MODULAR (se solicitada)
        # ====================================================================
        if analise_modular:
            print("📂 ANÁLISE MODULAR - Passo a Passo")
            print("-" * 80)

            print("\n[1/4] Carregando orçamento...")
            df_orcamento = load_budget(caminho_orcamento)
            print(f"      ✅ {len(df_orcamento)} itens carregados")
            print(f"      📊 Categorias: {df_orcamento['categoria'].nunique()}")
            print(f"      📋 UPEs: {df_orcamento['cod_upe'].nunique()}")
            print(f"      💰 Valor total: R$ {df_orcamento['total_orcado'].sum():,.2f}")

            print("\n[2/4] Carregando base LPU...")
            df_lpu = carregar_lpu(caminho_lpu)
            print(f"      ✅ {len(df_lpu)} itens carregados")
            print(f"      📚 Fontes: {df_lpu['fonte'].nunique()}")
            print(f"      🏷️  Fontes disponíveis: {', '.join(df_lpu['fonte'].unique())}")

            print("\n[3/4] Cruzando dados...")
            df_cruzado = cruzar_orcamento_lpu(df_orcamento, df_lpu)
            print(f"      ✅ {len(df_cruzado)} itens correspondidos")

            print("\n[4/4] Calculando divergências...")
            df_resultado = calcular_divergencias(df_cruzado)
            print("      ✅ Cálculos concluídos\n")

            # Salvar resultados
            from construct_cost_ai.domain.validators.lpu.validator_lpu import salvar_resultado

            salvar_resultado(df_resultado, output_dir)
        else:
            # Validação padrão
            df_resultado = validar_lpu(
                caminho_orcamento=caminho_orcamento,
                caminho_lpu=caminho_lpu,
                output_dir=output_dir,
                verbose=verbose,
            )

        # ====================================================================
        # ESTATÍSTICAS GERAIS
        # ====================================================================
        if gerar_estatisticas and not verbose:
            print("\n📊 ESTATÍSTICAS DA VALIDAÇÃO")
            print("-" * 80)

            total_itens = len(df_resultado)
            itens_ok = (df_resultado["status_conciliacao"] == "OK").sum()
            itens_ressarcimento = (df_resultado["status_conciliacao"] == "Para ressarcimento").sum()
            itens_abaixo = (df_resultado["status_conciliacao"] == "Abaixo LPU").sum()

            print(f"Total de itens: {total_itens}")
            print(f"  ✅ OK: {itens_ok} ({itens_ok/total_itens*100:.1f}%)")
            print(
                f"  ⚠️  Para ressarcimento: {itens_ressarcimento} ({itens_ressarcimento/total_itens*100:.1f}%)"
            )
            print(f"  📉 Abaixo LPU: {itens_abaixo} ({itens_abaixo/total_itens*100:.1f}%)")

            valor_total = df_resultado["valor_total_orcado"].sum()
            dif_total = df_resultado["dif_total"].sum()
            dif_ressarcimento = df_resultado[
                df_resultado["status_conciliacao"] == "Para ressarcimento"
            ]["dif_total"].sum()

            print(f"\n💰 Valor total orçado: R$ {valor_total:,.2f}")
            print(f"💵 Divergência total: R$ {dif_total:,.2f}")
            print(f"💸 Potencial ressarcimento: R$ {dif_ressarcimento:,.2f}")

        # ====================================================================
        # TOP DIVERGÊNCIAS
        # ====================================================================
        if gerar_top_divergencias:
            print(f"\n\n🔴 TOP {top_n} MAIORES DIVERGÊNCIAS (Valor Absoluto)")
            print("-" * 80)
            top_abs = df_resultado.nlargest(top_n, "dif_total")[
                [
                    "cod_item",
                    "nome",
                    "unitario_orcado",
                    "unitario_lpu",
                    "dif_unitario",
                    "dif_total",
                    "status_conciliacao",
                ]
            ]
            print(top_abs.to_string(index=False))

            print(f"\n\n📈 TOP {top_n} MAIORES DIVERGÊNCIAS (Percentual)")
            print("-" * 80)
            df_resultado["perc_dif_abs"] = abs(df_resultado["perc_dif"])
            top_perc = df_resultado.nlargest(top_n, "perc_dif_abs")[
                [
                    "cod_item",
                    "nome",
                    "unitario_orcado",
                    "unitario_lpu",
                    "perc_dif",
                    "dif_total",
                    "status_conciliacao",
                ]
            ]
            print(top_perc.to_string(index=False))

        # ====================================================================
        # ANÁLISE POR CATEGORIA
        # ====================================================================
        if gerar_analise_categorias and "categoria" in df_resultado.columns:
            print("\n\n📊 ANÁLISE POR CATEGORIA")
            print("-" * 80)

            resumo_cat = (
                df_resultado.groupby(["categoria", "status_conciliacao"])
                .agg({"cod_item": "count", "dif_total": "sum"})
                .reset_index()
            )
            resumo_cat.columns = ["Categoria", "Status", "Qtd Itens", "Dif Total (R$)"]

            print(resumo_cat.to_string(index=False))

            print("\n💰 Divergência Total por Categoria:")
            dif_por_cat = (
                df_resultado.groupby("categoria")["dif_total"].sum().sort_values(ascending=False)
            )
            for cat, valor in dif_por_cat.head(10).items():
                print(f"  {cat}: R$ {valor:,.2f}")

        # ====================================================================
        # ANÁLISE POR UPE
        # ====================================================================
        if gerar_analise_upes and "cod_upe" in df_resultado.columns:
            print("\n\n📋 ANÁLISE POR UPE")
            print("-" * 80)

            resumo_upe = (
                df_resultado.groupby(["cod_upe", "status_conciliacao"])
                .agg({"cod_item": "count", "dif_total": "sum"})
                .reset_index()
            )
            resumo_upe.columns = ["Código UPE", "Status", "Qtd Itens", "Dif Total (R$)"]
            resumo_upe = resumo_upe.sort_values("Código UPE")

            print(resumo_upe.to_string(index=False))

        # ====================================================================
        # APLICAR FILTROS
        # ====================================================================
        df_filtrado = df_resultado.copy()
        filtros_aplicados = []

        if filtro_percentual is not None:
            df_filtrado = df_filtrado[abs(df_filtrado["perc_dif"]) > filtro_percentual]
            filtros_aplicados.append(f"Divergência > {filtro_percentual}%")

        if filtro_categoria is not None:
            df_filtrado = df_filtrado[df_filtrado["categoria"] == filtro_categoria]
            filtros_aplicados.append(f"Categoria = '{filtro_categoria}'")

        if filtro_valor_minimo is not None:
            df_filtrado = df_filtrado[df_filtrado["unitario_orcado"] > filtro_valor_minimo]
            filtros_aplicados.append(f"Valor unitário > R$ {filtro_valor_minimo:,.2f}")

        if filtros_aplicados:
            print("\n\n🎯 RESULTADOS FILTRADOS")
            print("-" * 80)
            print("Filtros aplicados:")
            for filtro in filtros_aplicados:
                print(f"  • {filtro}")

            print(f"\nItens encontrados: {len(df_filtrado)}")

            if len(df_filtrado) > 0:
                print("\nResumo por status:")
                print(df_filtrado["status_conciliacao"].value_counts())

                print(f"\nDivergência total filtrada: R$ {df_filtrado['dif_total'].sum():,.2f}")

                if exibir_preview:
                    print("\nPrimeiros 10 itens:")
                    preview_cols = [
                        "cod_item",
                        "nome",
                        "unitario_orcado",
                        "unitario_lpu",
                        "perc_dif",
                        "dif_total",
                        "status_conciliacao",
                    ]
                    print(df_filtrado[preview_cols].head(10).to_string(index=False))
            else:
                print("\n⚠️  Nenhum item encontrado com os filtros aplicados.")

        # ====================================================================
        # PREVIEW GERAL
        # ====================================================================
        elif exibir_preview and not gerar_top_divergencias:
            print("\n\n📋 PREVIEW DOS RESULTADOS (Primeiros 10 itens)")
            print("-" * 80)
            preview_cols = [
                "cod_item",
                "nome",
                "unidade",
                "qtde",
                "unitario_orcado",
                "unitario_lpu",
                "dif_unitario",
                "perc_dif",
                "status_conciliacao",
            ]
            print(df_resultado[preview_cols].head(10).to_string(index=False))

        print("\n" + "=" * 80)
        print("✅ VALIDAÇÃO CONCLUÍDA COM SUCESSO!")
        print("=" * 80 + "\n")

        return df_resultado if not filtros_aplicados else df_filtrado

    except ValidatorLPUError as e:
        print(f"\n❌ ERRO NA VALIDAÇÃO: {e}\n")
        return None
    except Exception as e:
        print(f"\n❌ ERRO INESPERADO: {e}\n")
        return None


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
            verbose=True,
        )

        print("\n✅ Validação executada com sucesso!")
        print(f"   Total de registros: {len(df_resultado)}")

        return df_resultado

    except ValidatorLPUError as e:
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
            verbose=False,
        )

        print("📊 ANÁLISE DE DIVERGÊNCIAS\n")

        # Top 10 maiores divergências absolutas
        print("🔴 TOP 10 Maiores Divergências (Valor Absoluto):")
        print("-" * 80)
        top_divergencias = df_resultado.nlargest(10, "dif_total")[
            [
                "cod_item",
                "nome",
                "unitario_orcado",
                "unitario_lpu",
                "dif_unitario",
                "dif_total",
                "status_conciliacao",
            ]
        ]
        print(top_divergencias.to_string(index=False))

        # Top 10 maiores divergências percentuais
        print("\n\n📈 TOP 10 Maiores Divergências (Percentual):")
        print("-" * 80)
        df_resultado["perc_dif_abs"] = abs(df_resultado["perc_dif"])
        top_perc = df_resultado.nlargest(10, "perc_dif_abs")[
            [
                "cod_item",
                "nome",
                "unitario_orcado",
                "unitario_lpu",
                "perc_dif",
                "status_conciliacao",
            ]
        ]
        print(top_perc.to_string(index=False))

        # Itens para ressarcimento
        print("\n\n💰 ITENS PARA RESSARCIMENTO:")
        print("-" * 80)
        ressarcimento = df_resultado[df_resultado["status_conciliacao"] == "Para ressarcimento"]
        total_ressarcimento = ressarcimento["dif_total"].sum()
        print(f"Total de itens: {len(ressarcimento)}")
        print(f"Valor total para ressarcimento: R$ {total_ressarcimento:,.2f}")

        if len(ressarcimento) > 0:
            print("\nPrimeiros 5 itens:")
            print(
                ressarcimento.head()[
                    ["cod_item", "nome", "unitario_orcado", "unitario_lpu", "dif_total"]
                ].to_string(index=False)
            )

        return df_resultado

    except ValidatorLPUError as e:
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
            verbose=False,
        )

        # Filtro 1: Divergências acima de 10%
        print("🎯 FILTRO 1: Divergências > 10%")
        print("-" * 80)
        divergencias_altas = df_resultado[abs(df_resultado["perc_dif"]) > 10]
        print(f"Itens encontrados: {len(divergencias_altas)}")
        if len(divergencias_altas) > 0:
            print(
                divergencias_altas[
                    ["cod_item", "nome", "perc_dif", "dif_total", "status_conciliacao"]
                ]
                .head(10)
                .to_string(index=False)
            )

        # Filtro 2: Itens de uma categoria específica
        if "categoria" in df_resultado.columns:
            categorias = df_resultado["categoria"].unique()
            if len(categorias) > 0:
                categoria_exemplo = categorias[0]
                print(f"\n\n🎯 FILTRO 2: Categoria = '{categoria_exemplo}'")
                print("-" * 80)
                por_categoria = df_resultado[df_resultado["categoria"] == categoria_exemplo]
                print(f"Itens encontrados: {len(por_categoria)}")
                print("\nResumo:")
                print(por_categoria["status_conciliacao"].value_counts())

        # Filtro 3: Valores unitários acima de R$ 1000
        print("\n\n🎯 FILTRO 3: Itens com valor unitário > R$ 1.000,00")
        print("-" * 80)
        valores_altos = df_resultado[df_resultado["unitario_orcado"] > 1000]
        print(f"Itens encontrados: {len(valores_altos)}")
        if len(valores_altos) > 0:
            print(
                valores_altos[
                    [
                        "cod_item",
                        "nome",
                        "unitario_orcado",
                        "unitario_lpu",
                        "dif_unitario",
                        "status_conciliacao",
                    ]
                ].to_string(index=False)
            )

        return df_resultado

    except ValidatorLPUError as e:
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
        df_orcamento = load_budget(caminho_orcamento)
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
            verbose=False,
        )
        print(f"   ✅ Validação concluída: {len(df_resultado)} itens processados")

        return df_resultado

    except ValidatorLPUError as e:
        print(f"\n❌ Erro: {e}")
        return None


def exibir_explicacoes():
    """Exibe explicações detalhadas sobre cada exemplo."""
    explicacoes = {
        "1": {
            "titulo": "EXEMPLO 1: Validação Completa",
            "descricao": """
Este exemplo demonstra o uso mais simples e direto do validador.

🎯 O QUE FAZ:
- Executa o fluxo completo end-to-end
- Carrega orçamento e LPU automaticamente
- Realiza merge, cálculo de divergências e exportação
- Exibe todas as estatísticas com verbose=True

💡 QUANDO USAR:
- Primeira vez usando o validador
- Validação rápida e completa
- Quando precisa ver todo o progresso
- Geração de relatórios padrão

📊 SAÍDA:
- Console: Estatísticas completas (itens OK, ressarcimento, divergências)
- Arquivos: Excel (4 abas) + CSV em outputs/

💻 CÓDIGO EQUIVALENTE:
    df = validar_lpu(
        caminho_orcamento="data/orcamento_exemplo.xlsx",
        caminho_lpu="data/lpu_exemplo.xlsx",
        output_dir="outputs",
        verbose=True
    )
""",
        },
        "2": {
            "titulo": "EXEMPLO 2: Análise de Divergências",
            "descricao": """
Este exemplo foca na análise financeira detalhada das divergências.

🎯 O QUE FAZ:
- Executa validação em modo silencioso (verbose=False)
- Identifica TOP 10 maiores divergências absolutas (R$)
- Identifica TOP 10 maiores divergências percentuais (%)
- Calcula total para ressarcimento
- Lista primeiros 5 itens para ressarcimento

💡 QUANDO USAR:
- Análise financeira e priorização
- Identificar itens críticos
- Relatórios executivos
- Planejamento de ações corretivas

📊 SAÍDA:
- Rankings de divergências (valor e percentual)
- Total financeiro para ressarcimento
- Detalhamento dos itens mais impactantes

🔍 ANÁLISES REALIZADAS:
    top_abs = df.nlargest(10, 'dif_total')        # Maior impacto em R$
    top_perc = df.nlargest(10, 'perc_dif_abs')    # Maior variação %
    total_ressarc = ressarcimento['dif_total'].sum()
""",
        },
        "3": {
            "titulo": "EXEMPLO 3: Filtros Customizados",
            "descricao": """
Este exemplo demonstra como aplicar filtros específicos ao resultado.

🎯 O QUE FAZ:
- Filtro 1: Itens com divergência > 10%
- Filtro 2: Itens de uma categoria específica
- Filtro 3: Itens com valor unitário > R$ 1.000,00

💡 QUANDO USAR:
- Análises segmentadas por critérios
- Auditorias específicas
- Relatórios customizados
- Investigação de anomalias

📊 SAÍDA:
- Subconjuntos filtrados do resultado completo
- Estatísticas por categoria
- Itens de alto valor

🔍 EXEMPLOS DE FILTROS:
    # Por percentual
    df[abs(df['perc_dif']) > 10]
    
    # Por categoria
    df[df['categoria'] == 'Estrutura']
    
    # Por valor
    df[df['unitario_orcado'] > 1000]
    
    # Combinar filtros
    df[(df['perc_dif'] > 10) & (df['categoria'] == 'Estrutura')]
""",
        },
        "4": {
            "titulo": "EXEMPLO 4: Uso Modular",
            "descricao": """
Este exemplo mostra como usar cada função separadamente.

🎯 O QUE FAZ:
- Passo 1: Carrega orçamento separadamente
- Passo 2: Analisa dados do orçamento (categorias, UPEs)
- Passo 3: Carrega e analisa base LPU (fontes)
- Passo 4: Executa validação completa

💡 QUANDO USAR:
- Integração em pipelines existentes
- Validações customizadas pré/pós processamento
- Necessidade de manipular dados antes da validação
- Automação e scripts personalizados

📊 SAÍDA:
- Controle total de cada etapa
- Análises intermediárias
- Flexibilidade para customização

💻 FUNÇÕES INDIVIDUAIS:
    from construct_cost_ai.domain import (
        carregar_orcamento,
        carregar_lpu,
        cruzar_orcamento_lpu,
        calcular_divergencias,
        salvar_resultado
    )
    
    # Pipeline customizado
    df_orc = carregar_orcamento("orcamento.xlsx")
    # ... fazer análises/transformações ...
    df_lpu = carregar_lpu("lpu.xlsx")
    # ... validações customizadas ...
    df_resultado = validar_lpu(...)
""",
        },
    }

    print("\n" + "=" * 80)
    print("EXPLICAÇÕES DOS EXEMPLOS")
    print("=" * 80)

    for num in ["1", "2", "3", "4"]:
        print(f"\n{explicacoes[num]['titulo']}")
        print("=" * 80)
        print(explicacoes[num]["descricao"])
        print("\n" + "-" * 80)

    input("\nPressione ENTER para voltar ao menu...")


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

    while True:
        print("\nEscolha uma opção:")
        print("0 - Executar todos os exemplos")
        for i, (nome, _) in enumerate(exemplos, 1):
            print(f"{i} - {nome}")
        print("5 - Ver explicações sobre os exemplos")
        print("9 - Sair")

        try:
            escolha = input("\nSua escolha (0-5, 9): ").strip()

            if escolha == "9":
                print("\n👋 Encerrando...")
                break
            elif escolha == "5":
                exibir_explicacoes()
            elif escolha == "0":
                for nome, func in exemplos:
                    func()
                    input("\nPressione ENTER para continuar...")
            elif escolha in ["1", "2", "3", "4"]:
                idx = int(escolha) - 1
                exemplos[idx][1]()
                input("\nPressione ENTER para voltar ao menu...")
            else:
                print("⚠️  Opção inválida! Escolha entre 0-5 ou 9.")

        except KeyboardInterrupt:
            print("\n\n⚠️ Execução interrompida pelo usuário.")
            break
        except Exception as e:
            print(f"\n❌ Erro: {e}")

    print("\n" + "=" * 80)
    print("FIM DA DEMONSTRAÇÃO")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    main()

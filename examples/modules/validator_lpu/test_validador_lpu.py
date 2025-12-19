"""
Script de teste interativo para o Validador LPU.

Este script demonstra como usar o módulo validador_lpu para conciliar
orçamentos com a base de preços LPU com opções configuráveis via menu.
"""

__author__ = "Emerson V. Rafael (emervin)"
__copyright__ = "Copyright 2025, Construct Cost AI"
__credits__ = ["Emerson V. Rafael"]
__license__ = "MIT"
__version__ = "1.0.0"
__maintainer__ = "Emerson V. Rafael"
__email__ = "emersonssmile@gmail.com"
__status__ = "Development"

from pathlib import Path
from typing import Optional
import sys

# Adicionar o diretório src ao path
base_dir = Path(__file__).parent.parent
sys.path.insert(0, str(Path(base_dir, "src")))

from construct_cost_ai.domain.validators.lpu.validator_lpu import (
    validar_lpu,
    carregar_orcamento,
    carregar_lpu,
    cruzar_orcamento_lpu,
    calcular_divergencias,
    ValidadorLPUError,
)
from config.config_logger import logger
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
    """
    # Configurar caminhos padrão
    if caminho_orcamento is None:
        caminho_orcamento = Path(base_dir, "data", "orcamento_exemplo.xlsx")
    if caminho_lpu is None:
        caminho_lpu = Path(base_dir, "data", "lpu_exemplo.xlsx")
    if output_dir is None:
        output_dir = Path(base_dir, "outputs")

    logger.debug("=" * 80)
    logger.info("VALIDADOR LPU - ANÁLISE CONFIGURÁVEL")
    logger.debug("=" * 80)

    try:
        # ====================================================================
        # ANÁLISE MODULAR (se solicitada)
        # ====================================================================
        if analise_modular:
            logger.debug("📂 ANÁLISE MODULAR - Passo a Passo")
            logger.debug("-" * 80)

            logger.info("[1/4] Carregando orçamento...")
            df_orcamento = carregar_orcamento(caminho_orcamento)
            logger.debug(f"      ✅ {len(df_orcamento)} itens carregados")
            logger.debug(f"      📊 Categorias: {df_orcamento['categoria'].nunique()}")
            logger.debug(f"      📋 UPEs: {df_orcamento['cod_upe'].nunique()}")
            logger.debug(f"      💰 Valor total: R$ {df_orcamento['total_orcado'].sum():,.2f}")

            logger.info("[2/4] Carregando base LPU...")
            df_lpu = carregar_lpu(caminho_lpu)
            logger.debug(f"      ✅ {len(df_lpu)} itens carregados")
            logger.debug(f"      📚 Fontes: {df_lpu['fonte'].nunique()}")
            logger.debug(f"      🏷️  Fontes disponíveis: {', '.join(df_lpu['fonte'].unique())}")

            logger.info("[3/4] Cruzando dados...")
            df_cruzado = cruzar_orcamento_lpu(df_orcamento, df_lpu)
            logger.debug(f"      ✅ {len(df_cruzado)} itens correspondidos")

            logger.info("[4/4] Calculando divergências...")
            df_resultado = calcular_divergencias(df_cruzado)
            logger.debug("      ✅ Cálculos concluídos")

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
            logger.debug("📊 ESTATÍSTICAS DA VALIDAÇÃO")
            logger.debug("-" * 80)

            total_itens = len(df_resultado)
            itens_ok = (df_resultado["status_conciliacao"] == "OK").sum()
            itens_ressarcimento = (df_resultado["status_conciliacao"] == "Para ressarcimento").sum()
            itens_abaixo = (df_resultado["status_conciliacao"] == "Abaixo LPU").sum()

            logger.debug(f"Total de itens: {total_itens}")
            logger.debug(f"  ✅ OK: {itens_ok} ({itens_ok/total_itens*100:.1f}%)")
            logger.debug(
                f"  ⚠️  Para ressarcimento: {itens_ressarcimento} ({itens_ressarcimento/total_itens*100:.1f}%)"
            )
            logger.debug(f"  📉 Abaixo LPU: {itens_abaixo} ({itens_abaixo/total_itens*100:.1f}%)")

            valor_total = df_resultado["valor_total_orcado"].sum()
            dif_total = df_resultado["dif_total"].sum()
            dif_ressarcimento = df_resultado[
                df_resultado["status_conciliacao"] == "Para ressarcimento"
            ]["dif_total"].sum()

            logger.debug(f"💰 Valor total orçado: R$ {valor_total:,.2f}")
            logger.debug(f"💵 Divergência total: R$ {dif_total:,.2f}")
            logger.debug(f"💸 Potencial ressarcimento: R$ {dif_ressarcimento:,.2f}")

        # ====================================================================
        # TOP DIVERGÊNCIAS
        # ====================================================================
        if gerar_top_divergencias:
            logger.debug(f"🔴 TOP {top_n} MAIORES DIVERGÊNCIAS (Valor Absoluto)")
            logger.debug("-" * 80)
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

            logger.debug(f"📈 TOP {top_n} MAIORES DIVERGÊNCIAS (Percentual)")
            logger.debug("-" * 80)
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
            logger.debug("📊 ANÁLISE POR CATEGORIA")
            logger.debug("-" * 80)

            resumo_cat = (
                df_resultado.groupby(["categoria", "status_conciliacao"])
                .agg({"cod_item": "count", "dif_total": "sum"})
                .reset_index()
            )
            resumo_cat.columns = ["Categoria", "Status", "Qtd Itens", "Dif Total (R$)"]

            print(resumo_cat.to_string(index=False))

            logger.debug("💰 Divergência Total por Categoria:")
            dif_por_cat = (
                df_resultado.groupby("categoria")["dif_total"].sum().sort_values(ascending=False)
            )
            for cat, valor in dif_por_cat.head(10).items():
                logger.debug(f"  {cat}: R$ {valor:,.2f}")

        # ====================================================================
        # ANÁLISE POR UPE
        # ====================================================================
        if gerar_analise_upes and "cod_upe" in df_resultado.columns:
            logger.debug("📋 ANÁLISE POR UPE")
            logger.debug("-" * 80)

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
            logger.debug("🎯 RESULTADOS FILTRADOS")
            logger.debug("-" * 80)
            logger.debug("Filtros aplicados:")
            for filtro in filtros_aplicados:
                logger.debug(f"  • {filtro}")

            logger.debug(f"Itens encontrados: {len(df_filtrado)}")

            if len(df_filtrado) > 0:
                logger.debug("Resumo por status:")
                print(df_filtrado["status_conciliacao"].value_counts())

                logger.debug(
                    f"Divergência total filtrada: R$ {df_filtrado['dif_total'].sum():,.2f}"
                )

                if exibir_preview:
                    logger.debug("Primeiros 10 itens:")
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
                logger.warning("⚠️  Nenhum item encontrado com os filtros aplicados.")

        # ====================================================================
        # PREVIEW GERAL
        # ====================================================================
        elif exibir_preview and not gerar_top_divergencias:
            logger.debug("📋 PREVIEW DOS RESULTADOS (Primeiros 10 itens)")
            logger.debug("-" * 80)
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

        logger.debug("=" * 80)
        logger.success("✅ VALIDAÇÃO CONCLUÍDA COM SUCESSO!")
        logger.debug("=" * 80)

        logger.info("📁 ARQUIVOS GERADOS:")
        logger.debug("-" * 80)
        logger.debug("   ✅ validacao_lpu.xlsx           - Exportação básica (4 abas)")
        logger.debug("   ✅ validacao_lpu.csv            - Exportação CSV")
        logger.debug("   ✅ relatorio_completo_validacao_lpu.xlsx - Relatório completo (11+ abas)")
        logger.debug("      └─ Estatísticas gerais, Top divergências, Análises por categoria/UPE")
        logger.debug("   ✅ relatorio_validacao_lpu.html - Relatório HTML interativo")
        logger.debug("      └─ Dashboard visual com gráficos e tabelas formatadas")
        logger.debug("-" * 80)
        logger.debug(f"   📂 Localização: {Path(output_dir).resolve()}")
        logger.debug("=" * 80)

        return df_resultado if not filtros_aplicados else df_filtrado

    except ValidadorLPUError as e:
        logger.error(f"ERRO NA VALIDAÇÃO: {e}")
        return None
    except Exception as e:
        logger.error(f"ERRO INESPERADO: {e}")
        return None


def exibir_menu_opcoes():
    """Exibe menu de opções configuráveis."""
    opcoes = {
        "verbose": {
            "desc": "Modo verboso (exibe progresso detalhado)",
            "tipo": "bool",
            "padrao": True,
        },
        "gerar_estatisticas": {
            "desc": "Gerar estatísticas resumidas",
            "tipo": "bool",
            "padrao": True,
        },
        "gerar_top_divergencias": {
            "desc": "Gerar ranking de maiores divergências",
            "tipo": "bool",
            "padrao": False,
        },
        "top_n": {
            "desc": "Quantidade de itens no ranking",
            "tipo": "int",
            "padrao": 10,
            "dependencia": "gerar_top_divergencias",
        },
        "gerar_analise_categorias": {
            "desc": "Gerar análise por categoria",
            "tipo": "bool",
            "padrao": False,
        },
        "gerar_analise_upes": {"desc": "Gerar análise por UPE", "tipo": "bool", "padrao": False},
        "filtro_percentual": {
            "desc": "Filtrar divergências acima de N% (ex: 10.0)",
            "tipo": "float",
            "padrao": None,
        },
        "filtro_categoria": {
            "desc": "Filtrar por categoria específica",
            "tipo": "str",
            "padrao": None,
        },
        "filtro_valor_minimo": {
            "desc": "Filtrar itens com valor unitário acima de R$",
            "tipo": "float",
            "padrao": None,
        },
        "exibir_preview": {
            "desc": "Exibir preview dos primeiros resultados",
            "tipo": "bool",
            "padrao": True,
        },
        "analise_modular": {
            "desc": "Executar análise modular passo a passo",
            "tipo": "bool",
            "padrao": False,
        },
    }

    print("\n" + "=" * 80)
    print("CONFIGURAÇÃO DE OPÇÕES")
    print("=" * 80)
    print("\nOpções disponíveis:\n")

    for i, (key, opt) in enumerate(opcoes.items(), 1):
        dependencia = f" (requer {opt['dependencia']}=True)" if "dependencia" in opt else ""
        print(f"{i:2d}. {opt['desc']}{dependencia}")
        print(f"    Tipo: {opt['tipo']}, Padrão: {opt['padrao']}")

    return opcoes


def configurar_opcoes_interativo():
    """Configura opções de forma interativa."""
    opcoes = exibir_menu_opcoes()
    config = {}

    print("\n" + "-" * 80)
    print("Configure as opções (pressione ENTER para usar padrão):\n")

    for key, opt in opcoes.items():
        padrao_str = str(opt["padrao"]) if opt["padrao"] is not None else "None"

        # Pular se for dependente e a dependência não foi ativada
        if "dependencia" in opt and not config.get(opt["dependencia"], False):
            config[key] = opt["padrao"]
            continue

        while True:
            valor_input = input(f"{opt['desc']} [{padrao_str}]: ").strip()

            # Usar padrão se vazio
            if not valor_input:
                config[key] = opt["padrao"]
                break

            # Converter para tipo correto
            try:
                if opt["tipo"] == "bool":
                    config[key] = valor_input.lower() in ["true", "t", "yes", "y", "s", "sim", "1"]
                elif opt["tipo"] == "int":
                    config[key] = int(valor_input)
                elif opt["tipo"] == "float":
                    config[key] = float(valor_input)
                else:  # str
                    config[key] = valor_input if valor_input.lower() != "none" else None
                break
            except ValueError:
                print(f"  ⚠️  Valor inválido para {opt['tipo']}. Tente novamente.")

    return config


def exibir_presets():
    """Exibe presets pré-configurados."""
    presets = {
        "1": {
            "nome": "Validação Simples",
            "desc": "Validação básica com progresso detalhado",
            "config": {
                "verbose": True,
                "gerar_estatisticas": False,
                "gerar_top_divergencias": False,
                "gerar_analise_categorias": False,
                "gerar_analise_upes": False,
                "exibir_preview": True,
                "analise_modular": False,
            },
        },
        "2": {
            "nome": "Análise Completa",
            "desc": "Todas as análises e estatísticas",
            "config": {
                "verbose": False,
                "gerar_estatisticas": True,
                "gerar_top_divergencias": True,
                "top_n": 10,
                "gerar_analise_categorias": True,
                "gerar_analise_upes": True,
                "exibir_preview": True,
                "analise_modular": False,
            },
        },
        "3": {
            "nome": "Top Divergências",
            "desc": "Foco nos itens com maiores divergências",
            "config": {
                "verbose": False,
                "gerar_estatisticas": True,
                "gerar_top_divergencias": True,
                "top_n": 20,
                "gerar_analise_categorias": False,
                "gerar_analise_upes": False,
                "exibir_preview": False,
                "analise_modular": False,
            },
        },
        "4": {
            "nome": "Filtro: Divergências Altas (>10%)",
            "desc": "Apenas itens com divergência acima de 10%",
            "config": {
                "verbose": False,
                "gerar_estatisticas": True,
                "gerar_top_divergencias": False,
                "gerar_analise_categorias": True,
                "gerar_analise_upes": False,
                "filtro_percentual": 10.0,
                "exibir_preview": True,
                "analise_modular": False,
            },
        },
        "5": {
            "nome": "Filtro: Itens de Alto Valor (>R$ 1000)",
            "desc": "Apenas itens com valor unitário acima de R$ 1.000",
            "config": {
                "verbose": False,
                "gerar_estatisticas": True,
                "gerar_top_divergencias": True,
                "top_n": 10,
                "gerar_analise_categorias": False,
                "gerar_analise_upes": False,
                "filtro_valor_minimo": 1000.0,
                "exibir_preview": True,
                "analise_modular": False,
            },
        },
        "6": {
            "nome": "Análise Modular",
            "desc": "Execução passo a passo com detalhes",
            "config": {
                "verbose": False,
                "gerar_estatisticas": True,
                "gerar_top_divergencias": False,
                "gerar_analise_categorias": True,
                "gerar_analise_upes": True,
                "exibir_preview": True,
                "analise_modular": True,
            },
        },
    }

    print("\n" + "=" * 80)
    print("PRESETS DISPONÍVEIS")
    print("=" * 80 + "\n")

    for num, preset in presets.items():
        print(f"{num}. {preset['nome']}")
        print(f"   {preset['desc']}\n")

    return presets


def exibir_ajuda():
    """Exibe ajuda sobre as opções."""
    print("\n" + "=" * 80)
    print("AJUDA - OPÇÕES DISPONÍVEIS")
    print("=" * 80 + "\n")

    ajuda = """
📖 DESCRIÇÃO DAS OPÇÕES:

1. verbose (bool)
   Exibe progresso detalhado durante a validação (carregamento, merge, cálculos)
   Útil para primeira execução ou debug.

2. gerar_estatisticas (bool)
   Gera estatísticas resumidas: total de itens, % por status, valores totais.
   
3. gerar_top_divergencias (bool)
   Gera rankings de maiores divergências (absolutas e percentuais).
   
4. top_n (int)
   Define quantos itens aparecem nos rankings (padrão: 10).
   
5. gerar_analise_categorias (bool)
   Agrupa resultados por categoria de serviço.
   
6. gerar_analise_upes (bool)
   Agrupa resultados por código UPE (orçamento).
   
7. filtro_percentual (float)
   Filtra apenas itens com divergência > N% (ex: 10.0 para 10%).
   
8. filtro_categoria (str)
   Filtra apenas itens de uma categoria específica.
   
9. filtro_valor_minimo (float)
   Filtra apenas itens com valor unitário > R$ N.
   
10. exibir_preview (bool)
    Mostra preview dos primeiros 10 resultados.
    
11. analise_modular (bool)
    Executa validação passo a passo com detalhes de cada etapa.

� ARQUIVOS DE SAÍDA:

A validação gera automaticamente 4 tipos de arquivos:

1. validacao_lpu.xlsx (4 abas)
   - Validação Completa: todos os itens com divergências
   - Resumo por Status: agrupamento por OK/Ressarcimento/Abaixo
   - Resumo por Categoria: análise por categoria de serviço
   - Resumo por UPE: análise por código UPE

2. validacao_lpu.csv
   - Exportação CSV com todos os dados (separador ;)
   
3. relatorio_completo_validacao_lpu.xlsx (11+ abas)
   - Estatísticas: métricas gerais e percentuais
   - Resumo por Status: detalhamento por conciliação
   - Top 10/20 Divergências (Absoluta): maiores valores
   - Top 10/20 Divergências (Percentual): maiores %
   - Itens Para Ressarcimento: todos os itens problemáticos
   - Itens Abaixo LPU: itens com preço abaixo da referência
   - Resumo/Divergências por Categoria: análises por categoria
   - Resumo/Divergências por UPE: análises por UPE
   - Dados Completos: dataset completo

4. relatorio_validacao_lpu.html
   - Dashboard interativo com visualização moderna
   - Estatísticas em cards coloridos
   - Tabelas formatadas e responsivas
   - Pronto para impressão ou compartilhamento

�💡 DICAS:

- Use verbose=True na primeira execução para entender o processo
- Combine filtros para análises específicas
- Use presets para configurações comuns
- Filtros podem ser combinados (ex: categoria + percentual)

🎯 EXEMPLOS DE USO:

# Validação simples
executar_validacao()

# Top 5 maiores divergências
executar_validacao(gerar_top_divergencias=True, top_n=5)

# Filtrar categoria específica
executar_validacao(filtro_categoria="Estrutura e Alvenaria")

# Análise completa
executar_validacao(
    gerar_estatisticas=True,
    gerar_top_divergencias=True,
    gerar_analise_categorias=True,
    gerar_analise_upes=True
)
"""

    print(ajuda)
    input("\nPressione ENTER para voltar ao menu...")


def main():
    """Executa o validador com menu interativo."""
    print("\n" + "=" * 80)
    print("VALIDADOR LPU - CONCILIAÇÃO DE ORÇAMENTOS")
    print("=" * 80)

    while True:
        print("\n📋 MENU PRINCIPAL\n")
        print("1 - Executar com preset pré-configurado")
        print("2 - Executar com opções personalizadas")
        print("3 - Executar validação simples (padrão)")
        print("4 - Ver ajuda sobre as opções")
        print("9 - Sair")

        try:
            escolha = input("\nSua escolha: ").strip()

            if escolha == "9":
                print("\n👋 Encerrando...")
                break

            elif escolha == "1":
                # Executar com preset
                presets = exibir_presets()
                preset_num = input("\nEscolha um preset (1-6): ").strip()

                if preset_num in presets:
                    preset = presets[preset_num]
                    print(f"\n✅ Executando: {preset['nome']}")
                    print(f"   {preset['desc']}\n")
                    executar_validacao(**preset["config"])
                    input("\nPressione ENTER para voltar ao menu...")
                else:
                    print("⚠️  Preset inválido!")

            elif escolha == "2":
                # Configurar opções manualmente
                config = configurar_opcoes_interativo()
                print("\n✅ Configuração concluída! Executando validação...\n")
                executar_validacao(**config)
                input("\nPressione ENTER para voltar ao menu...")

            elif escolha == "3":
                # Validação simples padrão
                print("\n✅ Executando validação simples (configuração padrão)...\n")
                executar_validacao()
                input("\nPressione ENTER para voltar ao menu...")

            elif escolha == "4":
                # Exibir ajuda
                exibir_ajuda()

            else:
                print("⚠️  Opção inválida! Escolha entre 1-4 ou 9.")

        except KeyboardInterrupt:
            print("\n\n⚠️ Execução interrompida pelo usuário.")
            break
        except Exception as e:
            print(f"\n❌ Erro: {e}")
            import traceback

            traceback.print_exc()

    print("\n" + "=" * 80)
    print("FIM DA SESSÃO")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    main()

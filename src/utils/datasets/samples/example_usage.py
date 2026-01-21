"""
Script de demonstração dos geradores de datasets.

Este exemplo mostra como usar os geradores para criar orçamentos
e LPU, além de fazer análises e comparações entre eles.
"""

from pathlib import Path

import pandas as pd

from utils.datasets.samples.lpu.create_sample_dataset_budget import (
    BankBranchBudgetGenerator,
    BudgetMetadata,
)
from utils.datasets.samples.lpu.create_sample_dataset_lpu import BankBranchLPUGenerator
from utils.datasets.samples.lpu.create_sample_dataset_realistic_budget import (
    gerar_sample_padrao1,
    gerar_sample_padrao2_japj,
    gerar_sample_padrao2_fg,
)


def exemplo_basico():
    """Exemplo básico de uso dos geradores."""
    print("=" * 80)
    print("EXEMPLO 1: USO BÁSICO")
    print("=" * 80)

    # Gerar orçamento
    print("\n📋 Gerando orçamento...")
    budget_gen = BankBranchBudgetGenerator()
    budget_gen.generate_standard_budget()

    # Gerar LPU
    print("📋 Gerando LPU...")
    lpu_gen = BankBranchLPUGenerator()
    lpu_gen.generate_standard_lpu()

    # Mostrar resumos
    budget_summary = budget_gen.get_summary()
    lpu_summary = lpu_gen.get_summary()

    print(f"\n✅ Orçamento gerado com {budget_summary['estatisticas']['total_itens']} itens")
    print(f"   Valor Total: R$ {budget_summary['estatisticas']['valor_total']:,.2f}")

    print(f"\n✅ LPU gerada com {lpu_summary['metadata']['total_itens']} itens")
    print(f"   Preço Médio: R$ {lpu_summary['estatisticas']['preco_medio']:,.2f}")


def exemplo_customizado():
    """Exemplo de orçamento customizado."""
    print("\n\n" + "=" * 80)
    print("EXEMPLO 2: ORÇAMENTO CUSTOMIZADO")
    print("=" * 80)

    # Criar metadados específicos
    metadata = BudgetMetadata(
        projeto="Reforma Agência Itaú - Shopping Iguatemi",
        local="São Paulo - SP - Shopping Iguatemi",
        area_total_m2=520.0,
        tipo_obra="Retrofit Completo - Conceito Novo",
        versao="2.0",
    )

    # Gerar orçamento
    print("\n📋 Gerando orçamento customizado...")
    budget_gen = BankBranchBudgetGenerator(metadata)
    budget_gen.generate_standard_budget()

    summary = budget_gen.get_summary()

    print(f"\n✅ Projeto: {summary['metadata']['projeto']}")
    print(f"   Local: {summary['metadata']['local']}")
    print(f"   Área: {summary['metadata']['area_total_m2']} m²")
    print(f"   Valor Total: R$ {summary['estatisticas']['valor_total']:,.2f}")
    print(f"   Valor/m²: R$ {summary['estatisticas']['valor_por_m2']:,.2f}")


def exemplo_analise_comparativa():
    """Exemplo de análise comparativa entre orçamento e LPU."""
    print("\n\n" + "=" * 80)
    print("EXEMPLO 3: ANÁLISE COMPARATIVA ORÇAMENTO vs LPU")
    print("=" * 80)

    # Gerar ambos
    budget_gen = BankBranchBudgetGenerator()
    budget_gen.generate_standard_budget()

    lpu_gen = BankBranchLPUGenerator()
    lpu_gen.generate_standard_lpu()

    # Obter DataFrames
    df_budget = budget_gen.get_dataframe()
    df_lpu = lpu_gen.get_dataframe()

    # Fazer merge por código do item
    df_merged = pd.merge(
        df_budget[["cod_item", "nome", "unitario_orcado", "qtde", "total_orcado"]],
        df_lpu[["cod_item", "unitario_lpu", "fonte"]],
        on="cod_item",
        how="inner",
    )

    # Calcular desvios
    df_merged["desvio_unitario"] = (
        (df_merged["unitario_orcado"] - df_merged["unitario_lpu"]) / df_merged["unitario_lpu"] * 100
    )
    df_merged["desvio_abs"] = abs(df_merged["desvio_unitario"])

    # Análise de desvios
    print(f"\n📊 Análise de {len(df_merged)} itens comparáveis:")
    print(f"   Desvio médio: {df_merged['desvio_unitario'].mean():.2f}%")
    print(f"   Desvio mediano: {df_merged['desvio_unitario'].median():.2f}%")
    print(f"   Desvio máximo: {df_merged['desvio_unitario'].max():.2f}%")
    print(f"   Desvio mínimo: {df_merged['desvio_unitario'].min():.2f}%")

    # Itens com maior desvio
    print("\n⚠️  Top 5 itens com maior desvio:")
    top_desvios = df_merged.nlargest(5, "desvio_abs")[
        ["cod_item", "nome", "unitario_orcado", "unitario_lpu", "desvio_unitario"]
    ]

    for _, item in top_desvios.iterrows():
        print(f"\n   {item['cod_item']} - {item['nome'][:50]}")
        print(f"   Orçado: R$ {item['unitario_orcado']:,.2f}")
        print(f"   LPU: R$ {item['unitario_lpu']:,.2f}")
        print(f"   Desvio: {item['desvio_unitario']:+.2f}%")

    # Análise por fonte
    print("\n📋 Desvio médio por fonte de preço:")
    desvio_por_fonte = df_merged.groupby("fonte")["desvio_unitario"].agg(["count", "mean", "std"])
    for fonte, stats in desvio_por_fonte.iterrows():
        print(
            f"   {fonte[:40]:<40} | Média: {stats['mean']:+6.2f}% | Itens: {int(stats['count']):>3}"
        )


def exemplo_analise_categorias():
    """Exemplo de análise por categorias."""
    print("\n\n" + "=" * 80)
    print("EXEMPLO 4: ANÁLISE POR CATEGORIAS")
    print("=" * 80)

    budget_gen = BankBranchBudgetGenerator()
    budget_gen.generate_standard_budget()

    df = budget_gen.get_dataframe()

    # Análise por categoria
    print("\n📊 Resumo por Categoria:")
    print("-" * 80)

    categoria_stats = (
        df.groupby("categoria")
        .agg({"cod_item": "count", "total_orcado": "sum"})
        .sort_values("total_orcado", ascending=False)
    )

    total_geral = df["total_orcado"].sum()

    for categoria, stats in categoria_stats.iterrows():
        percentual = (stats["total_orcado"] / total_geral) * 100
        print(f"\n{categoria}")
        print(f"   Itens: {int(stats['cod_item']):>3}")
        print(f"   Valor: R$ {stats['total_orcado']:>12,.2f}")
        print(f"   Percentual: {percentual:>5.1f}%")
        print(f"   Barra: {'█' * int(percentual)}")


def exemplo_exportacao():
    """Exemplo de exportação de dados."""
    print("\n\n" + "=" * 80)
    print("EXEMPLO 5: EXPORTAÇÃO DE DADOS")
    print("=" * 80)

    output_dir = Path(Path(__file__).parent, "output")
    output_dir.mkdir(exist_ok=True)

    # Gerar e salvar orçamento
    print("\n📄 Gerando arquivos de orçamento...")
    budget_gen = BankBranchBudgetGenerator()
    budget_gen.generate_standard_budget()
    budget_gen.save_to_csv(str(Path(output_dir, "orcamento_exemplo.csv")))
    budget_gen.save_to_excel(str(Path(output_dir, "orcamento_exemplo.xlsx")))

    # Gerar e salvar LPU
    print("\n📄 Gerando arquivos de LPU...")
    lpu_gen = BankBranchLPUGenerator()
    lpu_gen.generate_standard_lpu()
    lpu_gen.save_to_csv(str(output_dir / "lpu_exemplo.csv"))
    lpu_gen.save_to_excel(str(output_dir / "lpu_exemplo.xlsx"))

    print(f"\n✅ Arquivos salvos em: {output_dir}")


def exemplo_geracao_realistic_budget():
    """Exemplo de geração de budgets realistas."""
    print("\n\n" + "=" * 80)
    print("EXEMPLO 6: GERAÇÃO DE BUDGETS REALISTAS")
    print("=" * 80)

    # Diretório de saída
    output_dir = Path(Path(__file__).parent, "output")
    output_dir.mkdir(exist_ok=True)

    # Gerar budgets realistas
    print("\n📄 Gerando budgets realistas...")
    data_inputs = output_dir

    arq1 = gerar_sample_padrao1(data_inputs=data_inputs)
    arq2 = gerar_sample_padrao2_japj(data_inputs=data_inputs)
    arq3 = gerar_sample_padrao2_fg(data_inputs=data_inputs)

    print(f"\n✅ Arquivos gerados:\n  - {arq1}\n  - {arq2}\n  - {arq3}")


def main():
    """Executa todos os exemplos."""
    print("\n")
    print("╔" + "=" * 78 + "╗")
    print("║" + " " * 15 + "DEMONSTRAÇÃO DOS GERADORES DE DATASETS" + " " * 24 + "║")
    print("║" + " " * 20 + "Agências Bancárias Itaú Unibanco" + " " * 25 + "║")
    print("╚" + "=" * 78 + "╝")

    # Executar exemplos
    exemplo_basico()
    exemplo_customizado()
    exemplo_analise_comparativa()
    exemplo_analise_categorias()
    exemplo_exportacao()
    exemplo_geracao_realistic_budget()

    print("\n\n" + "=" * 80)
    print("✅ DEMONSTRAÇÃO CONCLUÍDA!")
    print("=" * 80)
    print("\nPara mais informações, consulte o arquivo README.md")
    print()


if __name__ == "__main__":
    main()

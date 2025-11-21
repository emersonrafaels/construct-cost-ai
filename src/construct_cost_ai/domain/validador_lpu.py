"""
Módulo de validação LPU - Verifica divergências entre orçamento e base de preços.

Este módulo realiza a conciliação entre o orçamento enviado pela construtora
e a base LPU (Lista de Preços Unitários) oficial, identificando divergências
de valores sem tolerância.

Autor: Construct Cost AI
Data: 2025-11-21
"""

from pathlib import Path
from typing import Union, Optional
import sys
import pandas as pd


class ValidadorLPUError(Exception):
    """Exceção base para erros do validador LPU."""
    pass


class ArquivoNaoEncontradoError(ValidadorLPUError):
    """Exceção para arquivo não encontrado."""
    pass


class ColunasFaltandoError(ValidadorLPUError):
    """Exceção para colunas obrigatórias ausentes."""
    pass


def carregar_orcamento(path: Union[str, Path]) -> pd.DataFrame:
    """
    Carrega o arquivo de orçamento.

    Args:
        path: Caminho para o arquivo de orçamento (Excel ou CSV)

    Returns:
        DataFrame com o orçamento carregado

    Raises:
        ArquivoNaoEncontradoError: Se o arquivo não for encontrado
        ColunasFaltandoError: Se colunas obrigatórias estiverem ausentes
    """
    path = Path(path)
    
    if not path.exists():
        raise ArquivoNaoEncontradoError(f"Arquivo de orçamento não encontrado: {path}")
    
    # Colunas obrigatórias
    colunas_obrigatorias = [
        "cod_upe",
        "cod_item",
        "nome",
        "categoria",
        "unidade",
        "qtde",
        "unitario_orcado",
    ]
    
    try:
        if path.suffix in ['.xlsx', '.xls']:
            df = pd.read_excel(path)
        elif path.suffix == '.csv':
            df = pd.read_csv(path, sep=';', encoding='utf-8-sig')
        else:
            raise ValidadorLPUError(f"Formato não suportado: {path.suffix}")
    except Exception as e:
        raise ValidadorLPUError(f"Erro ao carregar orçamento: {e}")
    
    # Validar colunas obrigatórias
    colunas_faltando = set(colunas_obrigatorias) - set(df.columns)
    if colunas_faltando:
        raise ColunasFaltandoError(
            f"Colunas obrigatórias ausentes no orçamento: {', '.join(colunas_faltando)}"
        )
    
    # Garantir tipos corretos
    df['cod_item'] = df['cod_item'].astype(str)
    df['unidade'] = df['unidade'].astype(str)
    df['qtde'] = pd.to_numeric(df['qtde'], errors='coerce')
    df['unitario_orcado'] = pd.to_numeric(df['unitario_orcado'], errors='coerce')
    
    # Se total_orcado não existir, calcular
    if 'total_orcado' not in df.columns:
        df['total_orcado'] = df['qtde'] * df['unitario_orcado']
    else:
        df['total_orcado'] = pd.to_numeric(df['total_orcado'], errors='coerce')
    
    return df


def carregar_lpu(path: Union[str, Path]) -> pd.DataFrame:
    """
    Carrega o arquivo de base LPU.

    Args:
        path: Caminho para o arquivo LPU (Excel ou CSV)

    Returns:
        DataFrame com a base LPU carregada

    Raises:
        ArquivoNaoEncontradoError: Se o arquivo não for encontrado
        ColunasFaltandoError: Se colunas obrigatórias estiverem ausentes
    """
    path = Path(path)
    
    if not path.exists():
        raise ArquivoNaoEncontradoError(f"Arquivo LPU não encontrado: {path}")
    
    # Colunas obrigatórias
    colunas_obrigatorias = [
        "cod_item",
        "descricao",
        "unidade",
        "unitario_lpu",
        "fonte",
    ]
    
    try:
        if path.suffix in ['.xlsx', '.xls']:
            df = pd.read_excel(path)
        elif path.suffix == '.csv':
            df = pd.read_csv(path, sep=';', encoding='utf-8-sig')
        else:
            raise ValidadorLPUError(f"Formato não suportado: {path.suffix}")
    except Exception as e:
        raise ValidadorLPUError(f"Erro ao carregar LPU: {e}")
    
    # Validar colunas obrigatórias
    colunas_faltando = set(colunas_obrigatorias) - set(df.columns)
    if colunas_faltando:
        raise ColunasFaltandoError(
            f"Colunas obrigatórias ausentes no LPU: {', '.join(colunas_faltando)}"
        )
    
    # Garantir tipos corretos
    df['cod_item'] = df['cod_item'].astype(str)
    df['unidade'] = df['unidade'].astype(str)
    df['unitario_lpu'] = pd.to_numeric(df['unitario_lpu'], errors='coerce')
    
    return df


def cruzar_orcamento_lpu(orcamento: pd.DataFrame, lpu: pd.DataFrame) -> pd.DataFrame:
    """
    Faz o merge entre orçamento e LPU usando cod_item + unidade.

    Args:
        orcamento: DataFrame do orçamento
        lpu: DataFrame da base LPU

    Returns:
        DataFrame combinado com INNER JOIN

    Raises:
        ValidadorLPUError: Se o merge resultar em DataFrame vazio
    """
    # Fazer merge em cod_item + unidade
    df_merged = pd.merge(
        orcamento,
        lpu,
        on=["cod_item", "unidade"],
        how="inner",
        suffixes=("_orc", "_lpu")
    )
    
    if df_merged.empty:
        raise ValidadorLPUError(
            "Nenhuma correspondência encontrada entre orçamento e LPU. "
            "Verifique se cod_item e unidade estão consistentes."
        )
    
    # Calcular itens não encontrados no LPU
    itens_sem_lpu = len(orcamento) - len(df_merged)
    if itens_sem_lpu > 0:
        print(f"⚠️  Atenção: {itens_sem_lpu} itens do orçamento não encontrados no LPU")
    
    return df_merged


def calcular_divergencias(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calcula divergências entre orçamento e LPU sem tolerância.

    Adiciona as colunas:
    - valor_total_orcado: qtde * unitario_orcado
    - dif_unitario: unitario_orcado - unitario_lpu
    - dif_total: dif_unitario * qtde
    - perc_dif: (dif_unitario / unitario_lpu) * 100
    - status_conciliacao: classificação da divergência

    Regras de classificação (tolerância ZERO):
    - "OK": unitario_orcado == unitario_lpu
    - "Para ressarcimento": unitario_orcado > unitario_lpu
    - "Abaixo LPU": unitario_orcado < unitario_lpu

    Args:
        df: DataFrame com dados cruzados

    Returns:
        DataFrame com colunas de divergências calculadas
    """
    df = df.copy()
    
    # Calcular valor total orçado (revalidar)
    df['valor_total_orcado'] = df['qtde'] * df['unitario_orcado']
    
    # Verificar consistência do total_orcado se existir
    if 'total_orcado' in df.columns:
        inconsistencias = (
            abs(df['total_orcado'] - df['valor_total_orcado']) > 0.01
        ).sum()
        if inconsistencias > 0:
            print(f"⚠️  Atenção: {inconsistencias} inconsistências em total_orcado detectadas")
    
    # Calcular diferenças
    df['dif_unitario'] = df['unitario_orcado'] - df['unitario_lpu']
    df['dif_total'] = df['dif_unitario'] * df['qtde']
    
    # Calcular percentual (tratando divisão por zero)
    df['perc_dif'] = 0.0
    mask_validos = df['unitario_lpu'] != 0
    df.loc[mask_validos, 'perc_dif'] = (
        (df.loc[mask_validos, 'dif_unitario'] / df.loc[mask_validos, 'unitario_lpu']) * 100
    )
    
    # Classificação SEM TOLERÂNCIA
    def classificar_divergencia(row):
        if row['unitario_orcado'] == row['unitario_lpu']:
            return "OK"
        elif row['unitario_orcado'] > row['unitario_lpu']:
            return "Para ressarcimento"
        else:
            return "Abaixo LPU"
    
    df['status_conciliacao'] = df.apply(classificar_divergencia, axis=1)
    
    # Arredondar valores para 2 casas decimais
    colunas_arredondar = [
        'unitario_orcado', 'unitario_lpu', 'valor_total_orcado',
        'dif_unitario', 'dif_total', 'perc_dif'
    ]
    for col in colunas_arredondar:
        if col in df.columns:
            df[col] = df[col].round(2)
    
    return df


def salvar_resultado(
    df: pd.DataFrame,
    output_dir: Union[str, Path],
    nome_base: str = "validacao_lpu"
) -> None:
    """
    Salva o resultado em Excel e CSV.

    Args:
        df: DataFrame com resultados da validação
        output_dir: Diretório de saída
        nome_base: Nome base dos arquivos (padrão: "validacao_lpu")
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Definir ordem das colunas
    colunas_ordenadas = [
        'cod_upe',
        'cod_item',
        'nome',
        'categoria',
        'unidade',
        'qtde',
        'unitario_orcado',
        'unitario_lpu',
        'dif_unitario',
        'perc_dif',
        'valor_total_orcado',
        'dif_total',
        'status_conciliacao',
        'fonte',
        'descricao',
        'data_referencia',
        'composicao',
        'fornecedor',
        'observacoes_orc',
        'observacoes_lpu',
    ]
    
    # Selecionar apenas colunas existentes
    colunas_existentes = [col for col in colunas_ordenadas if col in df.columns]
    df_output = df[colunas_existentes].copy()
    
    # Salvar em Excel com formatação
    excel_path = output_dir / f"{nome_base}.xlsx"
    with pd.ExcelWriter(excel_path, engine='openpyxl') as writer:
        # Aba principal com validação completa
        df_output.to_excel(writer, sheet_name='Validação Completa', index=False)
        
        # Aba com resumo por status
        resumo_status = df.groupby('status_conciliacao').agg({
            'cod_item': 'count',
            'dif_total': 'sum',
            'valor_total_orcado': 'sum'
        }).reset_index()
        resumo_status.columns = ['Status', 'Qtd Itens', 'Dif Total (R$)', 'Valor Total Orçado (R$)']
        resumo_status.to_excel(writer, sheet_name='Resumo por Status', index=False)
        
        # Aba com resumo por categoria
        if 'categoria' in df.columns:
            resumo_categoria = df.groupby(['categoria', 'status_conciliacao']).agg({
                'cod_item': 'count',
                'dif_total': 'sum'
            }).reset_index()
            resumo_categoria.columns = ['Categoria', 'Status', 'Qtd Itens', 'Dif Total (R$)']
            resumo_categoria.to_excel(writer, sheet_name='Resumo por Categoria', index=False)
        
        # Aba com resumo por UPE
        if 'cod_upe' in df.columns:
            resumo_upe = df.groupby(['cod_upe', 'status_conciliacao']).agg({
                'cod_item': 'count',
                'dif_total': 'sum'
            }).reset_index()
            resumo_upe.columns = ['Código UPE', 'Status', 'Qtd Itens', 'Dif Total (R$)']
            resumo_upe.to_excel(writer, sheet_name='Resumo por UPE', index=False)
    
    print(f"✅ Excel salvo em: {excel_path}")
    
    # Salvar em CSV
    csv_path = output_dir / f"{nome_base}.csv"
    df_output.to_csv(csv_path, index=False, sep=';', encoding='utf-8-sig')
    print(f"✅ CSV salvo em: {csv_path}")


def validar_lpu(
    caminho_orcamento: Union[str, Path] = "data/orcamento_exemplo.xlsx",
    caminho_lpu: Union[str, Path] = "data/lpu_exemplo.xlsx",
    output_dir: Union[str, Path] = "outputs",
    verbose: bool = True
) -> pd.DataFrame:
    """
    Função orquestradora para validação LPU.

    Realiza todo o fluxo de validação:
    1. Carrega orçamento e LPU
    2. Cruza os dados (INNER JOIN em cod_item + unidade)
    3. Calcula divergências sem tolerância
    4. Classifica itens (OK, Para ressarcimento, Abaixo LPU)
    5. Salva resultados em Excel e CSV

    Args:
        caminho_orcamento: Caminho do arquivo de orçamento
        caminho_lpu: Caminho do arquivo LPU
        output_dir: Diretório para salvar resultados
        verbose: Se True, exibe estatísticas no console

    Returns:
        DataFrame com validação completa

    Raises:
        ValidadorLPUError: Em caso de erro na validação
    """
    if verbose:
        print("=" * 80)
        print("VALIDADOR LPU - Conciliação de Orçamento vs Base de Preços")
        print("=" * 80)
        print()
    
    # 1. Carregar dados
    if verbose:
        print("📂 Carregando arquivos...")
    
    try:
        df_orcamento = carregar_orcamento(caminho_orcamento)
        if verbose:
            print(f"   ✅ Orçamento carregado: {len(df_orcamento)} itens")
    except Exception as e:
        raise ValidadorLPUError(f"Erro ao carregar orçamento: {e}")
    
    try:
        df_lpu = carregar_lpu(caminho_lpu)
        if verbose:
            print(f"   ✅ LPU carregado: {len(df_lpu)} itens")
    except Exception as e:
        raise ValidadorLPUError(f"Erro ao carregar LPU: {e}")
    
    print()
    
    # 2. Cruzar dados
    if verbose:
        print("🔗 Cruzando orçamento com LPU...")
    
    try:
        df_cruzado = cruzar_orcamento_lpu(df_orcamento, df_lpu)
        if verbose:
            print(f"   ✅ Itens cruzados: {len(df_cruzado)}")
    except Exception as e:
        raise ValidadorLPUError(f"Erro ao cruzar dados: {e}")
    
    print()
    
    # 3. Calcular divergências
    if verbose:
        print("🧮 Calculando divergências (tolerância ZERO)...")
    
    try:
        df_resultado = calcular_divergencias(df_cruzado)
    except Exception as e:
        raise ValidadorLPUError(f"Erro ao calcular divergências: {e}")
    
    # Estatísticas
    if verbose:
        print()
        print("📊 ESTATÍSTICAS DA VALIDAÇÃO")
        print("-" * 80)
        
        total_itens = len(df_resultado)
        itens_ok = (df_resultado['status_conciliacao'] == 'OK').sum()
        itens_ressarcimento = (df_resultado['status_conciliacao'] == 'Para ressarcimento').sum()
        itens_abaixo = (df_resultado['status_conciliacao'] == 'Abaixo LPU').sum()
        
        print(f"   Total de itens validados: {total_itens}")
        print(f"   ✅ OK: {itens_ok} ({itens_ok/total_itens*100:.1f}%)")
        print(f"   ⚠️  Para ressarcimento: {itens_ressarcimento} ({itens_ressarcimento/total_itens*100:.1f}%)")
        print(f"   📉 Abaixo LPU: {itens_abaixo} ({itens_abaixo/total_itens*100:.1f}%)")
        print()
        
        valor_total_orcado = df_resultado['valor_total_orcado'].sum()
        dif_total = df_resultado['dif_total'].sum()
        dif_ressarcimento = df_resultado[
            df_resultado['status_conciliacao'] == 'Para ressarcimento'
        ]['dif_total'].sum()
        
        print(f"   💰 Valor total orçado: R$ {valor_total_orcado:,.2f}")
        print(f"   💵 Divergência total: R$ {dif_total:,.2f}")
        print(f"   💸 Potencial ressarcimento: R$ {dif_ressarcimento:,.2f}")
        print()
    
    # 4. Salvar resultados
    if verbose:
        print("💾 Salvando resultados...")
    
    try:
        salvar_resultado(df_resultado, output_dir)
    except Exception as e:
        raise ValidadorLPUError(f"Erro ao salvar resultados: {e}")
    
    if verbose:
        print()
        print("=" * 80)
        print("✅ VALIDAÇÃO CONCLUÍDA COM SUCESSO!")
        print("=" * 80)
    
    return df_resultado


def main():
    """Função principal para execução direta do módulo."""
    # Configurar caminhos padrão
    base_dir = Path(__file__).parent.parent.parent.parent
    caminho_orcamento = base_dir / "data" / "orcamento_exemplo.xlsx"
    caminho_lpu = base_dir / "data" / "lpu_exemplo.xlsx"
    output_dir = base_dir / "outputs"
    
    try:
        df_resultado = validar_lpu(
            caminho_orcamento=caminho_orcamento,
            caminho_lpu=caminho_lpu,
            output_dir=output_dir,
            verbose=True
        )
        
        # Exibir primeiras linhas
        print("\n📋 PREVIEW DOS RESULTADOS:")
        print("-" * 80)
        colunas_preview = [
            'cod_item', 'nome', 'unidade', 'qtde',
            'unitario_orcado', 'unitario_lpu', 'dif_unitario',
            'perc_dif', 'status_conciliacao'
        ]
        colunas_preview = [col for col in colunas_preview if col in df_resultado.columns]
        print(df_resultado[colunas_preview].head(10).to_string(index=False))
        
        return 0
        
    except ValidadorLPUError as e:
        print(f"\n❌ ERRO: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"\n❌ ERRO INESPERADO: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())

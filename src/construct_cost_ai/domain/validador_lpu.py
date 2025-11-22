"""
Módulo de validação LPU - Verifica divergências entre orçamento e base de preços.

Este módulo realiza a conciliação entre o orçamento enviado pela construtora
e a base LPU (Lista de Preços Unitários) oficial, identificando divergências
de valores com tolerância configurável.
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
from typing import Union, Optional
import sys
import pandas as pd

# Importar logger e settings
sys.path.insert(0, str(Path(__file__).parents[3]))
from src.config.config_logger import logger
from src.config.config_dynaconf import get_settings

settings = get_settings()


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
        logger.warning(f"⚠️  Atenção: {itens_sem_lpu} itens do orçamento não encontrados no LPU")
    
    return df_merged


def calcular_divergencias(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calcula divergências entre orçamento e LPU.

    Adiciona as colunas:
    - valor_total_orcado: qtde * unitario_orcado
    - dif_unitario: unitario_orcado - unitario_lpu
    - dif_total: dif_unitario * qtde
    - perc_dif: (dif_unitario / unitario_lpu) * 100
    - status_conciliacao: classificação da divergência

    Regras de classificação (tolerância configurável em settings.toml):
    - "OK": -tolerancia <= divergência <= +tolerancia
    - "Para ressarcimento": divergência > +tolerancia
    - "Abaixo LPU": divergência < -tolerancia

    Args:
        df: DataFrame com dados cruzados

    Returns:
        DataFrame com colunas de divergências calculadas
    """
    df = df.copy()
    
    # Obter tolerância do settings
    tolerancia = settings.validador_lpu.tolerancia_percentual
    logger.info(f"Calculando divergências com tolerância de {tolerancia}%")
    
    # Calcular valor total orçado (revalidar)
    df['valor_total_orcado'] = df['qtde'] * df['unitario_orcado']
    
    # Verificar consistência do total_orcado se existir
    if 'total_orcado' in df.columns:
        inconsistencias = (
            abs(df['total_orcado'] - df['valor_total_orcado']) > 0.01
        ).sum()
        if inconsistencias > 0:
            logger.warning(f"⚠️  Atenção: {inconsistencias} inconsistências em total_orcado detectadas")
    
    # Calcular diferenças
    df['dif_unitario'] = df['unitario_orcado'] - df['unitario_lpu']
    df['dif_total'] = df['dif_unitario'] * df['qtde']
    
    # Calcular percentual (tratando divisão por zero)
    df['perc_dif'] = 0.0
    mask_validos = df['unitario_lpu'] != 0
    df.loc[mask_validos, 'perc_dif'] = (
        (df.loc[mask_validos, 'dif_unitario'] / df.loc[mask_validos, 'unitario_lpu']) * 100
    )
    
    # Classificação COM TOLERÂNCIA (configurável)
    def classificar_divergencia(row):
        perc = row['perc_dif']
        if -tolerancia <= perc <= tolerancia:
            return "OK"
        elif perc > tolerancia:
            return "Para ressarcimento"
        else:
            return "Abaixo LPU"
    
    df['status_conciliacao'] = df.apply(classificar_divergencia, axis=1)
    
    logger.debug(f"Divergências calculadas para {len(df)} itens")
    
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
    nome_base: str = None
) -> None:
    """
    Salva o resultado em Excel e CSV.

    Args:
        df: DataFrame com resultados da validação
        output_dir: Diretório de saída
        nome_base: Nome base dos arquivos (padrão configurado em settings)
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Usar nome base do settings se não fornecido
    if nome_base is None:
        nome_base = settings.validador_lpu.arquivo_excel_basico.replace('.xlsx', '')
    
    logger.info(f"Salvando resultados em {output_dir}")
    
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
    excel_filename = settings.validador_lpu.arquivo_excel_basico
    excel_path = output_dir / excel_filename
    
    logger.debug(f"Gerando arquivo Excel: {excel_filename}")
    
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
    
    logger.success(f"✅ Excel salvo em: {excel_path}")
    
    # Salvar em CSV
    csv_filename = settings.validador_lpu.arquivo_csv
    csv_path = output_dir / csv_filename
    df_output.to_csv(csv_path, index=False, sep=';', encoding='utf-8-sig')
    logger.success(f"✅ CSV salvo em: {csv_path}")


def gerar_relatorio_html(
    df: pd.DataFrame,
    output_dir: Union[str, Path],
    nome_base: str = None
) -> None:
    """
    Gera relatório HTML completo com todas as análises.
    
    Args:
        df: DataFrame com resultados da validação
        output_dir: Diretório de saída
        nome_base: Nome base do arquivo HTML (padrão configurado em settings)
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Usar nome base do settings se não fornecido
    if nome_base is None:
        nome_base = settings.validador_lpu.arquivo_html.replace('.html', '')
    
    html_path = output_dir / f"{nome_base}.html"
    
    logger.debug(f"Gerando relatório HTML: {nome_base}.html")
    
    # Estatísticas gerais
    total_itens = len(df)
    itens_ok = (df['status_conciliacao'] == 'OK').sum()
    itens_ressarcimento = (df['status_conciliacao'] == 'Para ressarcimento').sum()
    itens_abaixo = (df['status_conciliacao'] == 'Abaixo LPU').sum()
    
    valor_total = df['valor_total_orcado'].sum()
    dif_total = df['dif_total'].sum()
    dif_ressarcimento = df[df['status_conciliacao'] == 'Para ressarcimento']['dif_total'].sum()
    
    # Top 10 divergências
    df['perc_dif_abs'] = abs(df['perc_dif'])
    top_10_abs = df.nlargest(10, 'dif_total')[
        ['cod_item', 'nome', 'unitario_orcado', 'unitario_lpu', 'dif_unitario', 'dif_total', 'status_conciliacao']
    ]
    top_10_perc = df.nlargest(10, 'perc_dif_abs')[
        ['cod_item', 'nome', 'unitario_orcado', 'unitario_lpu', 'perc_dif', 'dif_total', 'status_conciliacao']
    ]
    
    # Resumo por status
    resumo_status = df.groupby('status_conciliacao').agg({
        'cod_item': 'count',
        'dif_total': 'sum',
        'valor_total_orcado': 'sum'
    }).reset_index()
    resumo_status.columns = ['Status', 'Qtd Itens', 'Dif Total (R$)', 'Valor Total Orçado (R$)']
    
    # Resumo por categoria
    resumo_cat = None
    if 'categoria' in df.columns:
        resumo_cat = df.groupby(['categoria', 'status_conciliacao']).agg({
            'cod_item': 'count',
            'dif_total': 'sum'
        }).reset_index()
        resumo_cat.columns = ['Categoria', 'Status', 'Qtd Itens', 'Dif Total (R$)']
    
    # Resumo por UPE
    resumo_upe = None
    if 'cod_upe' in df.columns:
        resumo_upe = df.groupby(['cod_upe', 'status_conciliacao']).agg({
            'cod_item': 'count',
            'dif_total': 'sum'
        }).reset_index()
        resumo_upe.columns = ['Código UPE', 'Status', 'Qtd Itens', 'Dif Total (R$)']
    
    # Criar HTML
    html_content = f"""
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Relatório de Validação LPU</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 20px;
            color: #333;
        }}
        
        .container {{
            max-width: 1400px;
            margin: 0 auto;
            background: white;
            border-radius: 15px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.2);
            overflow: hidden;
        }}
        
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 40px;
            text-align: center;
        }}
        
        .header h1 {{
            font-size: 2.5em;
            margin-bottom: 10px;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.2);
        }}
        
        .header p {{
            font-size: 1.1em;
            opacity: 0.9;
        }}
        
        .content {{
            padding: 40px;
        }}
        
        .section {{
            margin-bottom: 40px;
            background: #f8f9fa;
            padding: 30px;
            border-radius: 10px;
            border-left: 5px solid #667eea;
        }}
        
        .section h2 {{
            color: #667eea;
            margin-bottom: 20px;
            font-size: 1.8em;
            display: flex;
            align-items: center;
        }}
        
        .section h2::before {{
            content: '📊';
            margin-right: 10px;
        }}
        
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-top: 20px;
        }}
        
        .stat-card {{
            background: white;
            padding: 25px;
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            text-align: center;
            transition: transform 0.3s ease;
        }}
        
        .stat-card:hover {{
            transform: translateY(-5px);
            box-shadow: 0 6px 12px rgba(0,0,0,0.15);
        }}
        
        .stat-label {{
            color: #666;
            font-size: 0.9em;
            margin-bottom: 10px;
            text-transform: uppercase;
            letter-spacing: 1px;
        }}
        
        .stat-value {{
            font-size: 2em;
            font-weight: bold;
            color: #667eea;
        }}
        
        .stat-ok {{ color: #28a745; }}
        .stat-warning {{ color: #ffc107; }}
        .stat-danger {{ color: #dc3545; }}
        
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
            background: white;
            border-radius: 10px;
            overflow: hidden;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }}
        
        thead {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
        }}
        
        th {{
            padding: 15px;
            text-align: left;
            font-weight: 600;
            text-transform: uppercase;
            font-size: 0.85em;
            letter-spacing: 0.5px;
        }}
        
        td {{
            padding: 12px 15px;
            border-bottom: 1px solid #eee;
        }}
        
        tr:hover {{
            background: #f8f9fa;
        }}
        
        .status-ok {{
            background: #d4edda;
            color: #155724;
            padding: 5px 10px;
            border-radius: 5px;
            font-weight: bold;
        }}
        
        .status-ressarcimento {{
            background: #fff3cd;
            color: #856404;
            padding: 5px 10px;
            border-radius: 5px;
            font-weight: bold;
        }}
        
        .status-abaixo {{
            background: #f8d7da;
            color: #721c24;
            padding: 5px 10px;
            border-radius: 5px;
            font-weight: bold;
        }}
        
        .valor-positivo {{
            color: #dc3545;
            font-weight: bold;
        }}
        
        .valor-negativo {{
            color: #28a745;
            font-weight: bold;
        }}
        
        .footer {{
            background: #f8f9fa;
            padding: 20px;
            text-align: center;
            color: #666;
            border-top: 1px solid #dee2e6;
        }}
        
        @media print {{
            body {{
                background: white;
                padding: 0;
            }}
            
            .container {{
                box-shadow: none;
            }}
            
            .stat-card:hover {{
                transform: none;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📋 Relatório de Validação LPU</h1>
            <p>Conciliação de Orçamento vs Base de Preços de Referência</p>
            <p style="font-size: 0.9em; margin-top: 10px;">Gerado em: {pd.Timestamp.now().strftime('%d/%m/%Y %H:%M:%S')}</p>
        </div>
        
        <div class="content">
            <!-- ESTATÍSTICAS GERAIS -->
            <div class="section">
                <h2>Estatísticas Gerais</h2>
                <div class="stats-grid">
                    <div class="stat-card">
                        <div class="stat-label">Total de Itens</div>
                        <div class="stat-value">{total_itens}</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-label">Itens OK</div>
                        <div class="stat-value stat-ok">{itens_ok} ({itens_ok/total_itens*100:.1f}%)</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-label">Para Ressarcimento</div>
                        <div class="stat-value stat-warning">{itens_ressarcimento} ({itens_ressarcimento/total_itens*100:.1f}%)</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-label">Abaixo LPU</div>
                        <div class="stat-value stat-danger">{itens_abaixo} ({itens_abaixo/total_itens*100:.1f}%)</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-label">Valor Total Orçado</div>
                        <div class="stat-value">R$ {valor_total:,.2f}</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-label">Divergência Total</div>
                        <div class="stat-value stat-warning">R$ {dif_total:,.2f}</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-label">Potencial Ressarcimento</div>
                        <div class="stat-value stat-danger">R$ {dif_ressarcimento:,.2f}</div>
                    </div>
                </div>
            </div>
            
            <!-- RESUMO POR STATUS -->
            <div class="section">
                <h2>Resumo por Status</h2>
                {resumo_status.to_html(index=False, classes='dataframe', escape=False, float_format=lambda x: f'R$ {x:,.2f}' if pd.notna(x) else '')}
            </div>
            
            <!-- TOP 10 DIVERGÊNCIAS ABSOLUTAS -->
            <div class="section">
                <h2>🔴 Top 10 Maiores Divergências (Valor Absoluto)</h2>
                {top_10_abs.to_html(index=False, classes='dataframe', escape=False, float_format=lambda x: f'R$ {x:,.2f}' if pd.notna(x) else '')}
            </div>
            
            <!-- TOP 10 DIVERGÊNCIAS PERCENTUAIS -->
            <div class="section">
                <h2>📈 Top 10 Maiores Divergências (Percentual)</h2>
                {top_10_perc.to_html(index=False, classes='dataframe', escape=False, float_format=lambda x: f'{x:.2f}%' if 'perc' in str(x) else (f'R$ {x:,.2f}' if pd.notna(x) else ''))}
            </div>
            
            {"<!-- RESUMO POR CATEGORIA -->" if resumo_cat is not None else ""}
            {f'''<div class="section">
                <h2>Resumo por Categoria</h2>
                {resumo_cat.to_html(index=False, classes='dataframe', escape=False, float_format=lambda x: f'R$ {{x:,.2f}}' if pd.notna(x) else '')}
            </div>''' if resumo_cat is not None else ""}
            
            {"<!-- RESUMO POR UPE -->" if resumo_upe is not None else ""}
            {f'''<div class="section">
                <h2>Resumo por UPE</h2>
                {resumo_upe.to_html(index=False, classes='dataframe', escape=False, float_format=lambda x: f'R$ {{x:,.2f}}' if pd.notna(x) else '')}
            </div>''' if resumo_upe is not None else ""}
        </div>
        
        <div class="footer">
            <p>Relatório gerado automaticamente pelo sistema Validador LPU</p>
            <p style="margin-top: 5px; font-size: 0.9em;">Construct Cost AI - Verificador Inteligente de Obras</p>
        </div>
    </div>
</body>
</html>
"""
    
    # Salvar HTML
    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    logger.success(f"✅ Relatório HTML salvo em: {html_path}")


def gerar_relatorio_excel_completo(
    df: pd.DataFrame,
    output_dir: Union[str, Path],
    nome_base: str = None
) -> None:
    """
    Gera relatório Excel completo com todas as análises em abas separadas.
    
    Args:
        df: DataFrame com resultados da validação
        output_dir: Diretório de saída
        nome_base: Nome base do arquivo Excel (padrão configurado em settings)
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Usar nome base do settings se não fornecido
    if nome_base is None:
        nome_base = settings.validador_lpu.arquivo_excel_completo.replace('.xlsx', '')
    
    excel_path = output_dir / f"{nome_base}.xlsx"
    
    logger.debug(f"Gerando relatório Excel completo: {nome_base}.xlsx")
    
    # Preparar dados
    df['perc_dif_abs'] = abs(df['perc_dif'])
    
    # Obter configuração de top_n do settings
    top_n = settings.validador_lpu.top_n_divergencias
    top_n_extended = settings.validador_lpu.top_n_divergencias_extended
    
    # Top divergências
    top_10_abs = df.nlargest(top_n, 'dif_total')[
        ['cod_item', 'nome', 'unitario_orcado', 'unitario_lpu', 'dif_unitario', 'dif_total', 'status_conciliacao']
    ]
    top_20_abs = df.nlargest(top_n_extended, 'dif_total')[
        ['cod_item', 'nome', 'unitario_orcado', 'unitario_lpu', 'dif_unitario', 'dif_total', 'status_conciliacao']
    ]
    
    top_10_perc = df.nlargest(top_n, 'perc_dif_abs')[
        ['cod_item', 'nome', 'unitario_orcado', 'unitario_lpu', 'perc_dif', 'dif_total', 'status_conciliacao']
    ]
    top_20_perc = df.nlargest(top_n_extended, 'perc_dif_abs')[
        ['cod_item', 'nome', 'unitario_orcado', 'unitario_lpu', 'perc_dif', 'dif_total', 'status_conciliacao']
    ]
    
    # Estatísticas
    total_itens = len(df)
    itens_ok = (df['status_conciliacao'] == 'OK').sum()
    itens_ressarcimento = (df['status_conciliacao'] == 'Para ressarcimento').sum()
    itens_abaixo = (df['status_conciliacao'] == 'Abaixo LPU').sum()
    
    valor_total = df['valor_total_orcado'].sum()
    dif_total = df['dif_total'].sum()
    dif_ressarcimento = df[df['status_conciliacao'] == 'Para ressarcimento']['dif_total'].sum()
    
    stats_data = {
        'Métrica': [
            'Total de Itens',
            'Itens OK',
            'Itens Para Ressarcimento',
            'Itens Abaixo LPU',
            '% OK',
            '% Para Ressarcimento',
            '% Abaixo LPU',
            'Valor Total Orçado (R$)',
            'Divergência Total (R$)',
            'Potencial Ressarcimento (R$)'
        ],
        'Valor': [
            total_itens,
            itens_ok,
            itens_ressarcimento,
            itens_abaixo,
            f'{itens_ok/total_itens*100:.2f}%',
            f'{itens_ressarcimento/total_itens*100:.2f}%',
            f'{itens_abaixo/total_itens*100:.2f}%',
            f'R$ {valor_total:,.2f}',
            f'R$ {dif_total:,.2f}',
            f'R$ {dif_ressarcimento:,.2f}'
        ]
    }
    df_stats = pd.DataFrame(stats_data)
    
    # Resumo por status
    resumo_status = df.groupby('status_conciliacao').agg({
        'cod_item': 'count',
        'dif_total': 'sum',
        'valor_total_orcado': 'sum'
    }).reset_index()
    resumo_status.columns = ['Status', 'Qtd Itens', 'Dif Total (R$)', 'Valor Total Orçado (R$)']
    
    # Itens para ressarcimento
    itens_para_ressarcimento = df[df['status_conciliacao'] == 'Para ressarcimento'][
        ['cod_item', 'nome', 'categoria', 'unitario_orcado', 'unitario_lpu', 
         'dif_unitario', 'perc_dif', 'qtde', 'dif_total', 'fonte']
    ].sort_values('dif_total', ascending=False)
    
    # Itens abaixo LPU
    itens_abaixo_lpu = df[df['status_conciliacao'] == 'Abaixo LPU'][
        ['cod_item', 'nome', 'categoria', 'unitario_orcado', 'unitario_lpu', 
         'dif_unitario', 'perc_dif', 'qtde', 'dif_total', 'fonte']
    ].sort_values('dif_total')
    
    # Salvar em Excel
    with pd.ExcelWriter(excel_path, engine='openpyxl') as writer:
        # Aba 1: Estatísticas Gerais
        df_stats.to_excel(writer, sheet_name='Estatísticas', index=False)
        
        # Aba 2: Resumo por Status
        resumo_status.to_excel(writer, sheet_name='Resumo por Status', index=False)
        
        # Aba 3: Top 10 Divergências (Valor)
        top_10_abs.to_excel(writer, sheet_name='Top 10 Div Absoluta', index=False)
        
        # Aba 4: Top 20 Divergências (Valor)
        top_20_abs.to_excel(writer, sheet_name='Top 20 Div Absoluta', index=False)
        
        # Aba 5: Top 10 Divergências (%)
        top_10_perc.to_excel(writer, sheet_name='Top 10 Div Percentual', index=False)
        
        # Aba 6: Top 20 Divergências (%)
        top_20_perc.to_excel(writer, sheet_name='Top 20 Div Percentual', index=False)
        
        # Aba 7: Itens para Ressarcimento
        itens_para_ressarcimento.to_excel(writer, sheet_name='Itens Para Ressarcimento', index=False)
        
        # Aba 8: Itens Abaixo LPU
        itens_abaixo_lpu.to_excel(writer, sheet_name='Itens Abaixo LPU', index=False)
        
        # Aba 9: Resumo por Categoria (se existir)
        if 'categoria' in df.columns:
            resumo_cat = df.groupby(['categoria', 'status_conciliacao']).agg({
                'cod_item': 'count',
                'dif_total': 'sum'
            }).reset_index()
            resumo_cat.columns = ['Categoria', 'Status', 'Qtd Itens', 'Dif Total (R$)']
            resumo_cat.to_excel(writer, sheet_name='Resumo por Categoria', index=False)
            
            # Divergência total por categoria
            dif_por_cat = df.groupby('categoria').agg({
                'cod_item': 'count',
                'dif_total': 'sum',
                'valor_total_orcado': 'sum'
            }).reset_index().sort_values('dif_total', ascending=False)
            dif_por_cat.columns = ['Categoria', 'Qtd Itens', 'Dif Total (R$)', 'Valor Total (R$)']
            dif_por_cat.to_excel(writer, sheet_name='Dif por Categoria', index=False)
        
        # Aba 10: Resumo por UPE (se existir)
        if 'cod_upe' in df.columns:
            resumo_upe = df.groupby(['cod_upe', 'status_conciliacao']).agg({
                'cod_item': 'count',
                'dif_total': 'sum'
            }).reset_index().sort_values('cod_upe')
            resumo_upe.columns = ['Código UPE', 'Status', 'Qtd Itens', 'Dif Total (R$)']
            resumo_upe.to_excel(writer, sheet_name='Resumo por UPE', index=False)
            
            # Divergência total por UPE
            dif_por_upe = df.groupby('cod_upe').agg({
                'cod_item': 'count',
                'dif_total': 'sum',
                'valor_total_orcado': 'sum'
            }).reset_index().sort_values('dif_total', ascending=False)
            dif_por_upe.columns = ['Código UPE', 'Qtd Itens', 'Dif Total (R$)', 'Valor Total (R$)']
            dif_por_upe.to_excel(writer, sheet_name='Dif por UPE', index=False)
        
        # Aba 11: Dados Completos
        df.to_excel(writer, sheet_name='Dados Completos', index=False)
    
    logger.success(f"✅ Relatório Excel completo salvo em: {excel_path}")


def validar_lpu(
    caminho_orcamento: Union[str, Path] = None,
    caminho_lpu: Union[str, Path] = None,
    output_dir: Union[str, Path] = None,
    verbose: bool = True
) -> pd.DataFrame:
    """
    Função orquestradora para validação LPU.

    Realiza todo o fluxo de validação:
    1. Carrega orçamento e LPU
    2. Cruza os dados (INNER JOIN em cod_item + unidade)
    3. Calcula divergências com tolerância configurável
    4. Classifica itens (OK, Para ressarcimento, Abaixo LPU)
    5. Salva resultados em Excel, CSV e HTML

    Args:
        caminho_orcamento: Caminho do arquivo de orçamento (padrão em settings)
        caminho_lpu: Caminho do arquivo LPU (padrão em settings)
        output_dir: Diretório para salvar resultados (padrão em settings)
        verbose: Se True, exibe estatísticas no console

    Returns:
        DataFrame com validação completa

    Raises:
        ValidadorLPUError: Em caso de erro na validação
    """
    # Usar valores padrão do settings se não fornecidos
    if caminho_orcamento is None:
        caminho_orcamento = settings.validador_lpu.caminho_padrao_orcamento
    if caminho_lpu is None:
        caminho_lpu = settings.validador_lpu.caminho_padrao_lpu
    if output_dir is None:
        output_dir = settings.validador_lpu.output_dir
    
    logger.info("=" * 80)
    logger.info("VALIDADOR LPU - Conciliação de Orçamento vs Base de Preços")
    logger.info(f"Tolerância configurada: {settings.validador_lpu.tolerancia_percentual}%")
    logger.info("=" * 80)
    
    if verbose:
        print("=" * 80)
        print("VALIDADOR LPU - Conciliação de Orçamento vs Base de Preços")
        print(f"Tolerância: {settings.validador_lpu.tolerancia_percentual}%")
        print("=" * 80)
        print()
    
    # 1. Carregar dados
    logger.info("📂 Carregando arquivos...")
    if verbose:
        print("📂 Carregando arquivos...")
    
    try:
        logger.debug(f"Carregando orçamento de: {caminho_orcamento}")
        df_orcamento = carregar_orcamento(caminho_orcamento)
        logger.info(f"✅ Orçamento carregado: {len(df_orcamento)} itens")
        if verbose:
            print(f"   ✅ Orçamento carregado: {len(df_orcamento)} itens")
    except Exception as e:
        logger.error(f"Erro ao carregar orçamento: {e}")
        raise ValidadorLPUError(f"Erro ao carregar orçamento: {e}")
    
    try:
        logger.debug(f"Carregando LPU de: {caminho_lpu}")
        df_lpu = carregar_lpu(caminho_lpu)
        logger.info(f"✅ LPU carregado: {len(df_lpu)} itens")
        if verbose:
            print(f"   ✅ LPU carregado: {len(df_lpu)} itens")
    except Exception as e:
        logger.error(f"Erro ao carregar LPU: {e}")
        raise ValidadorLPUError(f"Erro ao carregar LPU: {e}")
    
    logger.info("")
    
    # 2. Cruzar dados
    logger.info("🔗 Cruzando orçamento com LPU...")
    if verbose:
        print("🔗 Cruzando orçamento com LPU...")
    
    try:
        df_cruzado = cruzar_orcamento_lpu(df_orcamento, df_lpu)
        logger.info(f"✅ Itens cruzados: {len(df_cruzado)}")
        if verbose:
            print(f"   ✅ Itens cruzados: {len(df_cruzado)}")
    except Exception as e:
        logger.error(f"Erro ao cruzar dados: {e}")
        raise ValidadorLPUError(f"Erro ao cruzar dados: {e}")
    
    logger.info("")
    
    # 3. Calcular divergências
    logger.info(f"🧮 Calculando divergências (tolerância {settings.validador_lpu.tolerancia_percentual}%)...")
    if verbose:
        print(f"🧮 Calculando divergências (tolerância {settings.validador_lpu.tolerancia_percentual}%)...")
    
    try:
        df_resultado = calcular_divergencias(df_cruzado)
    except Exception as e:
        logger.error(f"Erro ao calcular divergências: {e}")
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
    
    # Registrar estatísticas no logger
    logger.info("📊 ESTATÍSTICAS DA VALIDAÇÃO")
    total_itens = len(df_resultado)
    itens_ok = (df_resultado['status_conciliacao'] == 'OK').sum()
    itens_ressarcimento = (df_resultado['status_conciliacao'] == 'Para ressarcimento').sum()
    itens_abaixo = (df_resultado['status_conciliacao'] == 'Abaixo LPU').sum()
    
    logger.info(f"Total de itens validados: {total_itens}")
    logger.info(f"✅ OK: {itens_ok} ({itens_ok/total_itens*100:.1f}%)")
    logger.info(f"⚠️  Para ressarcimento: {itens_ressarcimento} ({itens_ressarcimento/total_itens*100:.1f}%)")
    logger.info(f"📉 Abaixo LPU: {itens_abaixo} ({itens_abaixo/total_itens*100:.1f}%)")
    
    valor_total_orcado = df_resultado['valor_total_orcado'].sum()
    dif_total = df_resultado['dif_total'].sum()
    dif_ressarcimento = df_resultado[
        df_resultado['status_conciliacao'] == 'Para ressarcimento'
    ]['dif_total'].sum()
    
    logger.info(f"💰 Valor total orçado: R$ {valor_total_orcado:,.2f}")
    logger.info(f"💵 Divergência total: R$ {dif_total:,.2f}")
    logger.info(f"💸 Potencial ressarcimento: R$ {dif_ressarcimento:,.2f}")
    
    # 4. Salvar resultados
    logger.info("💾 Salvando resultados...")
    if verbose:
        print("💾 Salvando resultados...")
    
    try:
        # Salvar formato básico (4 abas)
        salvar_resultado(df_resultado, output_dir)
        
        # Salvar relatório completo em Excel (11+ abas)
        gerar_relatorio_excel_completo(df_resultado, output_dir)
        
        # Salvar relatório HTML
        gerar_relatorio_html(df_resultado, output_dir)
        
    except Exception as e:
        logger.error(f"Erro ao salvar resultados: {e}")
        raise ValidadorLPUError(f"Erro ao salvar resultados: {e}")
    
    if verbose:
        print()
        print("=" * 80)
        print("✅ VALIDAÇÃO CONCLUÍDA COM SUCESSO!")
        print("=" * 80)
    
    logger.success("=" * 80)
    logger.success("✅ VALIDAÇÃO CONCLUÍDA COM SUCESSO!")
    logger.success("=" * 80)
    
    return df_resultado


def main():
    """Função principal para execução direta do módulo."""
    # Configurar caminhos padrão
    base_dir = Path(__file__).parent.parent.parent.parent
    caminho_orcamento = Path(base_dir, settings.validador_lpu.caminho_padrao_orcamento)
    caminho_lpu = Path(base_dir, settings.validador_lpu.caminho_padrao_lpu)
    output_dir = Path(base_dir, settings.validador_lpu.output_dir)
    
    logger.info("Iniciando validador LPU via main()...")
    logger.info(f"Orçamento: {caminho_orcamento}")
    logger.info(f"LPU: {caminho_lpu}")
    logger.info(f"Output: {output_dir}")
    
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
        
        logger.success("Execução principal concluída com sucesso!")
        return 0
        
    except ValidadorLPUError as e:
        logger.error(f"ERRO: {e}")
        print(f"\n❌ ERRO: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        logger.error(f"ERRO INESPERADO: {e}")
        print(f"\n❌ ERRO INESPERADO: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())

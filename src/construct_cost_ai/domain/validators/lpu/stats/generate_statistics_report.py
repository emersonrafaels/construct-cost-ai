"""
Script para gerar estatísticas de um DataFrame e salvar os resultados em um arquivo PDF.
"""

import pandas as pd
from matplotlib import pyplot as plt
from fpdf import FPDF
from pathlib import Path

class PDFReport(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 12)
        self.cell(0, 10, 'Relatório de Estatísticas do DataFrame', 0, 1, 'C')
        self.ln(10)

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 10, f'Página {self.page_no()}', 0, 0, 'C')

def generate_statistics_report(df: pd.DataFrame, output_pdf: str):
    """
    Gera estatísticas descritivas de um DataFrame e salva em um arquivo PDF.

    Args:
        df (pd.DataFrame): DataFrame de entrada.
        output_pdf (str): Caminho para salvar o arquivo PDF.
    """
    # Cria o relatório PDF
    pdf = PDFReport()
    pdf.add_page()

    # Estatísticas descritivas
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(0, 10, 'Estatísticas Descritivas', 0, 1, 'L')
    pdf.set_font('Arial', '', 10)

    stats = df.describe(include='all').transpose()

    for col in stats.index:
        pdf.cell(0, 10, f'Coluna: {col}', 0, 1, 'L')
        for stat, value in stats.loc[col].items():
            pdf.cell(0, 10, f'  {stat}: {value}', 0, 1, 'L')
        pdf.ln(5)

    # Gráficos
    pdf.add_page()
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(0, 10, 'Gráficos', 0, 1, 'L')

    for column in df.select_dtypes(include=['number']).columns:
        plt.figure()
        df[column].hist(bins=20, edgecolor='black')
        plt.title(f'Distribuição - {column}')
        plt.xlabel(column)
        plt.ylabel('Frequência')
        plt.tight_layout()

        # Salva o gráfico temporariamente
        temp_image = f'{column}_hist.png'
        plt.savefig(temp_image)
        plt.close()

        # Adiciona o gráfico ao PDF
        pdf.add_page()
        pdf.cell(0, 10, f'Gráfico: {column}', 0, 1, 'L')
        pdf.image(temp_image, x=10, y=30, w=190)

    # Salva o PDF
    pdf.output(output_pdf)

# Exemplo de uso
if __name__ == '__main__':
    # Exemplo de DataFrame
    data = {
        'Coluna1': [1, 2, 3, 4, 5],
        'Coluna2': [10, 20, 30, 40, 50],
        'Coluna3': ['A', 'B', 'A', 'B', 'C']
    }
    df = pd.DataFrame(data)

    # Gera o relatório
    generate_statistics_report(df, 'relatorio_estatisticas.pdf')

    # Carregar o DataFrame de exemplo
    data = {
        'CÓDIGO_UPE': [None, None, None, None, None],
        'PROGRAMA_DONO': [None, None, None, None, None],
        'NUMERO_AGENCIA': [605, 605, 605, 605, 605],
        'NOME_AGENCIA': ['Agência 1', 'Agência 1', 'Agência 1', 'Agência 1', 'Agência 1'],
        'REGIAO': ['Nordeste', 'Nordeste', 'Nordeste', 'Nordeste', 'Nordeste'],
        'UF': ['PE', 'PE', 'PE', 'PE', 'PE'],
        'CIDADE': ['Recife', 'Recife', 'Recife', 'Recife', 'Recife'],
        'CONSTRUTORA': ['Construtora A', 'Construtora A', 'Construtora A', 'Construtora A', 'Construtora A'],
        'GRUPO': ['Grupo 1', 'Grupo 1', 'Grupo 1', 'Grupo 1', 'Grupo 1'],
        'ID': [1, 2, 3, 4, 5],
        'NOME': ['Obra 1', 'Obra 2', 'Obra 3', 'Obra 4', 'Obra 5'],
        'UNIDADE': ['m²', 'm²', 'm²', 'm²', 'm²'],
        'TIPO': ['Tipo A', 'Tipo A', 'Tipo A', 'Tipo A', 'Tipo A'],
        'COMENTÁRIO': ['Comentário 1', 'Comentário 2', 'Comentário 3', 'Comentário 4', 'Comentário 5'],
        'QUANTIDADE': [10, 20, 30, 40, 50],
        'PRECO PAGO': [100, 200, 300, 400, 500],
        'VALOR TOTAL PAGO': [1000, 4000, 9000, 16000, 25000],
        'PRECO LPU': [90, 190, 290, 390, 490],
        'VALOR TOTAL LPU': [900, 3800, 8700, 15600, 24500],
        'DIFERENÇA TOTAL': [100, 200, 300, 400, 500],
        'DISCREPÂNCIA PERCENTUAL': [10, 5.26, 3.45, 2.56, 2.04],
        'STATUS CONCILIAÇÃO': ['OK', 'OK', 'OK', 'OK', 'OK'],
        'SOURCE_FILE': ['file1.xlsx', 'file2.xlsx', 'file3.xlsx', 'file4.xlsx', 'file5.xlsx'],
        'SHEET_NAME_orc': ['Sheet1', 'Sheet1', 'Sheet1', 'Sheet1', 'Sheet1']
    }

    df_result = pd.DataFrame(data)

    # Gerar o relatório final
    output_path = Path("relatorio_final_resultado.pdf")
    generate_statistics_report(df_result, str(output_path))
    print(f"Relatório gerado com sucesso: {output_path}")
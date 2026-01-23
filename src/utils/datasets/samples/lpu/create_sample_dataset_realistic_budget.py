"""
Módulo: generate_realistic_samples
---------------------------------

Gera planilhas de exemplo (mock) que simulam os dois principais padrões
de orçamento utilizados no Itaú:

1) Padrão 1 – Orçamentos por capítulos/itens da LPU.
   Estrutura com abas "Resumo" e "01", semelhante ao modelo visto no S392.

2) Padrão 2 – Planilhas enviadas pelas construtoras (JAPJ, FG, etc.).
   Estrutura com cabeçalho completo (UPE, Agência, Contrato, Dono...)
   e uma aba chamada "LPU", que contém itens linha a linha.

Esses arquivos são úteis para:
- desenvolvimento local sem acesso aos arquivos reais
- testes automatizados de parsing e detecção de padrão
- validação dos fluxos do Verificador Inteligente

Os arquivos são gravados em:  data/inputs/
"""

import sys
from pathlib import Path
from typing import List

import pandas as pd

# Adicionar src ao path
base_dir = Path(__file__).parents[4]
sys.path.insert(0, str(Path(base_dir, "src")))

from config.config_logger import logger


def create_data_inputs_dir() -> Path:
    """
    Cria o diretório data/inputs/ se não existir e retorna o caminho.

    Returns:
        Path: Caminho do diretório criado ou existente.
    """
    root = Path(__file__).resolve().parents[0]
    data_inputs = root / "output"
    data_inputs.mkdir(parents=True, exist_ok=True)
    return data_inputs


# Função auxiliar para calcular totais e percentuais


def calcular_totais_e_percentuais(itens: List[dict]) -> List[dict]:
    total_geral = sum(item["quantidade"] * item["preco_unitario"] * item["bdi"] for item in itens)
    for item in itens:
        item["preco_total"] = item["quantidade"] * item["preco_unitario"] * item["bdi"]
        item["percentual"] = (item["preco_total"] / total_geral * 100) if total_geral > 0 else 0
    return itens, total_geral


# Função para construir as linhas do padrão 1


def build_rows_padrao1(itens: List[dict]) -> List[List[object]]:
    # Calcular totais e percentuais antes de construir as linhas
    itens, total_geral = calcular_totais_e_percentuais(itens)

    rows = [
        ["", "ITAÚ UNIBANCO S/A - Ag. 4830 - SANTOS - BOQUEIRÃO - SP", "", "", "", "", "", ""],
        ["", "ORÇAMENTO - S392 - NOVO AUTO ATENDIMENTO", "", "", "", "", "", ""],
        [None] * 8,
        ["Item", "Descrição", "Un", "Quant.", "P.U.", "BDI", "Preço Total", "%", "OBS"],
    ]

    # Adicionar itens
    for item in itens:
        rows.append(
            [
                item["codigo"],
                item["descricao"],
                item["unidade"],
                item["quantidade"],
                item["preco_unitario"],
                item["bdi"],
                item["preco_total"],
                item["percentual"],
                "",
            ]
        )

    # Adicionar linha TOTAL
    rows.append(["TOTAL", "", "", "", "", "", total_geral, 100.0, ""])

    return rows


# Função para gerar o arquivo padrão 1


def gerar_sample_padrao1(data_inputs: Path, nome_arquivo: str = "sample_padrao1.xlsx") -> Path:
    itens = [
        {
            "codigo": "02.01.001",
            "descricao": "CORTE DE PISO CERÂMICO COM MAKITA",
            "unidade": "M2",
            "quantidade": 10.5,
            "preco_unitario": 119.37,
            "bdi": 1.3,
        },
        {
            "codigo": "02.01.002",
            "descricao": "DEMOLIÇÃO DE BASE COFRE E ATM",
            "unidade": "UN",
            "quantidade": 5.0,
            "preco_unitario": 369.84,
            "bdi": 1.3,
        },
        {
            "codigo": "02.01.003",
            "descricao": "RETIRADA DE PISO CERÂMICO C/ TRANSP.",
            "unidade": "M2",
            "quantidade": 26.85,
            "preco_unitario": 39.94,
            "bdi": 1.3,
        },
    ]

    rows = build_rows_padrao1(itens)
    df = pd.DataFrame(rows)

    caminho = data_inputs / nome_arquivo
    with pd.ExcelWriter(caminho) as writer:
        df.to_excel(writer, sheet_name="Resumo", header=False, index=False)
        df.to_excel(writer, sheet_name="01", header=False, index=False)

    logger.success(
        "Arquivo gerado: %s com %d linhas e %d colunas", caminho, len(df), len(df.columns)
    )
    return caminho


# -------------------------------------------------------------------------
# PADRÃO 2 — JAPJ / FG com aba "LPU"
# -------------------------------------------------------------------------


def _build_header_lpu(
    upe: str,
    agencia: str,
    nome_agencia: str,
    contrato: str,
    dono: str,
    fornecedor: str,
    regional: str,
) -> List[List[object]]:
    """
    Monta o cabeçalho do padrão 2, antes da tabela.

    Args:
        upe (str): Código UPE.
        agencia (str): Código da agência.
        nome_agencia (str): Nome da agência.
        contrato (str): Número do contrato.
        dono (str): Nome do dono.
        fornecedor (str): Nome do fornecedor.
        regional (str): Nome da regional.

    Returns:
        List[List[object]]: linhas brutas do cabeçalho.
    """
    return [
        ["itaú", "", "", "", "", "", "", ""],
        [f"{fornecedor} {regional}", "", "", "", "", "", "", ""],
        ["", f"{nome_agencia} - Simulação", "", "", "", "", "", ""],
        ["", "", "", "", "", "", "", ""],
        ["", "UPE", "AGÊNCIA", "NOME AGÊNCIA", "", "TOTAL", "DESLOCAMENTO", "SERVIÇOS"],
        ["", upe, agencia, nome_agencia, "", "", 0, 0],
        ["", "", "", "", "", "", "", ""],
        ["", "CONTRATO", "VERSÃO", "TIPO", "", "OMISSOS", "TOTAL", ""],
        ["", contrato, 1, "EXECUÇÃO DE OBRA", "", 0, 0, ""],
        ["", "", "", "", "", "", "", ""],
        ["", "Filtro", "ID", "Descrição", "Un.", "Unitário", "Comentário", "Quantidade", "Total"],
    ]


def _build_items_japj() -> List[List[object]]:
    """Items idênticos (aproximados) aos da planilha JAPJ das fotos."""
    return [
        ["", "Sim", "OBA-0034", "FORRO GESSO ACARTONADO", "M2", 124.57, "", 4, 498.30],
        ["", "Sim", "OBA-0043", "LATEX PVA MASSA CORRIDA", "M2", 49.10, "", 5, 245.50],
        ["", "Sim", "OBA-0067", "RETIRADA DE FORRO MANUAL", "M2", 19.21, "", 50, 960.50],
        ["", "Sim", "OBB-0232", "ANDAIME TUBULAR", "M", 91.35, "", 4, 365.40],
        ["", "Sim", "OBB-0470", "FURO EM CONCRETO", "UN", 120.21, "", 16, 1919.36],
        ["", "Sim", "OBB-1522", "CABO CAT6 - VERMELHO", "M", 7.67, "", 150, 1150.50],
        ["", "Sim", "NÃO LPU", "SUPORTE SIMPLES ANTENAS", "UN", 164.09, "", 1, 164.09],
        ["", "Sim", "NÃO LPU", "HASTE PARA FIXAÇÃO", "M", 157.29, "", 3, 471.87],
    ]


def _build_items_fg() -> List[List[object]]:
    """Items idênticos (aproximados) aos da planilha da FG."""
    return [
        ["", "Sim", "OBA-0067", "RETIRADA DE FORRO MANUAL", "M2", 13.21, "", 2, 26.42],
        ["", "Sim", "OBA-0111", "LIMPEZA FINAL DE OBRA", "M2", 9.49, "", 30, 284.63],
        ["", "Sim", "OBB-0232", "ANDAIME TUBULAR", "M", 91.35, "", 4, 365.42],
        ["", "Sim", "OBB-0470", "FURO EM CONCRETO", "UN", 120.21, "", 20, 2404.20],
        ["", "Sim", "OBB-1522", "CABO CAT6", "M", 2.34, "", 30, 70.31],
        ["", "Sim", "OBB-0161", "LONA PLÁSTICA", "M2", 7.67, "", 150, 1150.50],
    ]


def _to_df_with_rows(rows: List[List[object]]) -> pd.DataFrame:
    """
    Converte uma lista de listas em um DataFrame sem header.

    Args:
        rows (List[List[object]]): lista onde cada item representa uma linha.

    Returns:
        pd.DataFrame: dataframe estruturado como tabela bruta.
    """
    return pd.DataFrame(rows)


def gerar_sample_padrao2_japj(
    data_inputs: Path, nome_arquivo: str = "sample_padrao2_japj.xlsx"
) -> Path:
    """
    Gera uma planilha modelo JAPJ (padrão 2) com aba LPU.

    Args:
        data_inputs (Path): Caminho do diretório onde o arquivo será salvo.
        nome_arquivo (str): Nome do arquivo a ser salvo.

    Returns:
        Path: Caminho final do arquivo gerado.
    """
    header = _build_header_lpu(
        upe="190272",
        agencia="0167",
        nome_agencia="SP-LINS DE VASCONCELOS",
        contrato="4900037181",
        dono="C379 - Ampliação WiFi",
        fornecedor="JAPJ CONSTRUCOES CIVIS LTDA",
        regional="pu_sudeste",
    )

    rows = header + _build_items_japj()
    df = _to_df_with_rows(rows)

    caminho = data_inputs / nome_arquivo
    with pd.ExcelWriter(caminho) as writer:
        df.to_excel(writer, sheet_name="LPU", header=False, index=False)

    logger.success(
        "Arquivo gerado: %s com %d linhas e %d colunas", caminho, len(df), len(df.columns)
    )
    return caminho


def gerar_sample_padrao2_fg(
    data_inputs: Path, nome_arquivo: str = "sample_padrao2_fg.xlsx"
) -> Path:
    """
    Gera uma planilha modelo FG (padrão 2) com aba LPU.

    Args:
        data_inputs (Path): Caminho do diretório onde o arquivo será salvo.
        nome_arquivo (str): Nome do arquivo a ser salvo.

    Returns:
        Path: Caminho final do arquivo gerado.
    """
    header = _build_header_lpu(
        upe="190245",
        agencia="3893",
        nome_agencia="LONDRINA AV-TIRADENTES",
        contrato="4900037417",
        dono="T101 - SDWAN",
        fornecedor="FG EMPREIT. MAO DE OBRA LTDA",
        regional="pu_sul",
    )

    rows = header + _build_items_fg()
    df = _to_df_with_rows(rows)

    caminho = data_inputs / nome_arquivo
    with pd.ExcelWriter(caminho) as writer:
        df.to_excel(writer, sheet_name="LPU", header=False, index=False)

    logger.success(
        "Arquivo gerado: %s com %d linhas e %d colunas", caminho, len(df), len(df.columns)
    )
    return caminho


# -------------------------------------------------------------------------
# Entrypoint
# -------------------------------------------------------------------------


def main():
    """
    Executa a geração dos três arquivos mock:

    - sample_padrao1.xlsx
    - sample_padrao2_japj.xlsx
    - sample_padrao2_fg.xlsx
    """

    # Garante que o diretório existe
    DATA_INPUTS = create_data_inputs_dir()

    logger.info("Gerando arquivos de exemplo em: %s", DATA_INPUTS)

    arq1 = gerar_sample_padrao1(data_inputs=DATA_INPUTS)
    arq2 = gerar_sample_padrao2_japj(data_inputs=DATA_INPUTS)
    arq3 = gerar_sample_padrao2_fg(data_inputs=DATA_INPUTS)

    logger.success("✔ Arquivos gerados:")
    logger.success(arq1)
    logger.success(arq2)
    logger.success(arq3)


if __name__ == "__main__":
    main()

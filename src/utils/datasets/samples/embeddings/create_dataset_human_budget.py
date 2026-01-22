"""
Gerador de Orçamento "Humano" (Não-LPU) a partir de uma base LPU sintética.

Objetivo:
- Criar um dataset de orçamento com descrições escritas por humanos (variações, sinônimos, ruído),
  mantendo a unidade, quantidade e preço pago.
- Manter "ground truth" (GT_COD_LPU) para backtest offline.
- Incluir itens "ruído" (BDI, mobilização, frete etc.) que NÃO devem mapear para LPU.

Entrada:
- Um Excel da LPU (ex: BASE_LPU_EMBEDDINGS.xlsx) com colunas:
  COD_LPU, DESC_LPU, UN, PRECO_REF

Saída:
- Excel do orçamento (orcamento_humano.xlsx) com colunas:
  ID_ITEM, NOME_ITEM, UN, QTD, PRECO_PAGO_UNIT, GT_COD_LPU, FLAG_NAO_LPU, TIPO_LINHA

Autor: Emerson V. Rafael (emervin) + Copilot (ChatGPT)
"""

__author__ = "Emerson V. Rafael (emervin)"
__copyright__ = "Verificador Inteligente de Orçamentos de Obras"
__credits__ = ["Emerson V. Rafael", "Clarissa Simoyama"]
__license__ = "MIT"
__version__ = "1.1.0"
__maintainer__ = "Emerson V. Rafael (emervin), Clarissa Simoyama (simoyam)"
__squad__ = "DataCraft"
__email__ = "emersonssmile@gmail.com"
__status__ = "Development"

import random
import re
import math
from pathlib import Path
from typing import Optional, Dict, List, Tuple

import pandas as pd
import numpy as np

# ------------------------------
# Config
# ------------------------------
SEED = 42
random.seed(SEED)
np.random.seed(SEED)

DEFAULT_LPU_PATH = Path(Path(__file__).parents[0], 
                        "BASE_LPU_EMBEDDINGS.xlsx")
DEFAULT_LPU_SHEET = "BASE_LPU"

DEFAULT_OUT_PATH = Path(Path(__file__).parents[0], 
                        "BASE_HUMAN_BUDGET_EMBEDDINGS.xlsx")
DEFAULT_OUT_SHEET = "BASE_ORCAMENTO"


# ------------------------------
# Helpers
# ------------------------------
def normalize_text(s: str) -> str:
    s = s.upper()
    s = re.sub(r"\s+", " ", s).strip()
    return s


def strip_parentheses(s: str) -> str:
    return re.sub(r"\([^)]*\)", " ", s)


def remove_noise_phrases(s: str) -> str:
    # remove frases típicas que aparecem na LPU e atrapalham "humanização"
    patterns = [
        r"\bINCLUSO MATERIAL\b",
        r"\bCOM TRANSP\.\b",
        r"\bC/ TRANSP\.\b",
        r"\bSEM TRANSP\.\b",
        r"\bMEC\.\b",
    ]
    out = s
    for p in patterns:
        out = re.sub(p, " ", out)
    out = re.sub(r"\s+", " ", out).strip()
    return out


def family_unit(un: str) -> str:
    un = un.upper().strip()
    if un in ["M2"]:
        return "AREA"
    if un in ["M", "ML"]:
        return "COMPRIMENTO"
    if un in ["M3"]:
        return "VOLUME"
    if un in ["KG"]:
        return "PESO"
    return "UNIDADE"  # UN, PT, CJ, VB, BR etc.


def lognormal_qty(mean_base: float, sigma: float = 0.6) -> float:
    return float(np.random.lognormal(mean=math.log(mean_base), sigma=sigma))


def sample_qty_for_unit(un: str) -> float | int:
    un = un.upper()
    fam = family_unit(un)
    if fam == "AREA":
        qtd = lognormal_qty(20, 0.7)  # m2
        return round(qtd, 2)
    if fam == "COMPRIMENTO":
        qtd = lognormal_qty(30, 0.7)  # m
        return round(qtd, 2)
    if fam == "VOLUME":
        qtd = lognormal_qty(2, 0.6)   # m3
        return round(qtd, 2)
    if fam == "PESO":
        qtd = lognormal_qty(120, 0.8) # kg
        return round(qtd, 2)
    # UNIDADE
    qtd = max(1, int(round(lognormal_qty(2, 0.7))))
    return qtd


def paid_price_from_ref(preco_ref: float) -> float:
    # preço pago como ref +/- ~12% com clipping
    p = float(np.clip(np.random.normal(loc=preco_ref, scale=preco_ref * 0.12),
                      preco_ref * 0.6, preco_ref * 1.6))
    return round(p, 2)


# ------------------------------
# "Humanização" por intent / padrões
# ------------------------------
# Heurísticas simples (sem embeddings) para produzir descrições humanas com cara de orçamento.
REPLACEMENTS = [
    ("DEMOLICAO", ["demolir", "quebrar", "retirada", "remoção"]),
    ("REMOCAO", ["retirada", "remoção", "desmontagem"]),
    ("PAREDE", ["parede", "fechamento", "divisória"]),
    ("DIVISORIA", ["divisória", "parede leve", "separação"]),
    ("DRYWALL", ["drywall", "gesso acartonado", "parede de gesso"]),
    ("GESSO ACARTONADO", ["drywall", "gesso acartonado"]),
    ("FORRO", ["forro", "teto", "forro modular"]),
    ("PISO", ["piso", "revestimento do chão"]),
    ("PORCELANATO", ["porcelanato", "piso porcelanato"]),
    ("CERAMICO", ["cerâmica", "piso cerâmico"]),
    ("PINTURA", ["pintura", "pintar"]),
    ("ELETRODUTO", ["eletroduto", "conduíte"]),
    ("ACO GALVANIZADO", ["aço galvanizado", "galvanizado"]),
    ("LUMINARIA", ["luminária", "iluminação"]),
    ("PONTO DE ILUMINACAO", ["ponto de luz", "ponto iluminação"]),
    ("PONTO DE FORCA", ["ponto de tomada", "ponto força"]),
    ("PONTO DE LOGICA", ["ponto de rede", "ponto lógica"]),
    ("TUBO PVC", ["tubulação pvc", "tubo pvc"]),
    ("BACIA SANITARIA", ["vaso sanitário", "bacia"]),
    ("LAVATORIO", ["lavatório", "pia do banheiro"]),
    ("CUBA INOX", ["cuba inox", "cuba"]),
    ("PORTA", ["porta"]),
    ("VIDRO TEMPERADO", ["vidro temperado", "vidro"]),
    ("ALUGUEL", ["locação", "aluguel"]),
    ("PLATAFORMA", ["plataforma elevatória", "plataforma"]),
    ("ALVENARIA", ["alvenaria", "parede de blocos"]),
    ("SIPOREX", ["siporex", "pumex"]),
    ("ARMACAO", ["armação", "ferragem", "aço"]),
    ("CA-50", ["CA-50", "CA50"]),
    ("BARRA DE APOIO", ["barra de apoio", "apoio pcd"]),
    ("PCD", ["PCD", "acessibilidade"]),
    ("ATM", ["ATM", "caixa eletrônico"]),
]

HUMAN_SUFFIXES = [
    "conforme projeto",
    "mão de obra inclusa",
    "com fornecimento e instalação",
    "para área da agência",
    "para sala de atendimento",
    "acabamento padrão",
    "inclui fixação e consumíveis",
]

HUMAN_PREFIXES = [
    "",
    "serviço de",
    "execução de",
    "instalação de",
    "montagem de",
    "fornecimento e instalação de",
]

# Ruídos (não devem mapear)
NOISE_LINES = [
    ("BDI / taxa administrativa", "VB"),
    ("mobilização de equipe e canteiro", "VB"),
    ("frete de materiais", "VB"),
    ("ajustes e complementos diversos", "VB"),
    ("taxa de ART e documentação", "VB"),
    ("projeto executivo e as built", "VB"),
    ("gestão de obra / acompanhamento", "VB"),
    ("custo de deslocamento", "VB"),
    ("diárias de viagem / hospedagem", "VB"),
    ("taxas e emolumentos", "VB"),
]


def humanize_from_lpu(desc_lpu: str, un: str) -> str:
    """
    Converte uma descrição LPU 'operacional' em algo mais humano.
    Mantém termos técnicos e dimensões, mas troca algumas palavras por sinônimos,
    adiciona contexto e remove ruídos típicos da LPU (TRANSP/INCLUSO etc.).

    Args:
        desc_lpu (str): Descrição do item na LPU.
        un (str): Unidade do item.

    Returns:
        str: Descrição humanizada do item.
    """
    raw = normalize_text(desc_lpu)
    raw = strip_parentheses(raw)
    raw = remove_noise_phrases(raw)

    # mantém dimensões (ex: 7/8"x1/8", 32MM, 62,5X62,5)
    s = raw.lower()

    # substituições contextuais (não é para ficar perfeito, é para parecer humano)
    for token, options in REPLACEMENTS:
        if token.lower() in s:
            s = s.replace(token.lower(), random.choice(options))

    # pequenos "despadronizadores" típicos
    s = s.replace("c/ ", "com ")
    s = s.replace(" + ", " + ")
    s = re.sub(r"\s+", " ", s).strip()

    # adiciona prefixo/sufixo com probabilidade
    if random.random() < 0.55:
        pref = random.choice(HUMAN_PREFIXES).strip()
        if pref:
            s = f"{pref} {s}"

    if random.random() < 0.55:
        s = f"{s} {random.choice(HUMAN_SUFFIXES)}"

    # capitalização estilo orçamento (misto)
    return s.strip()


def should_be_non_lpu_line(prob_non_lpu: float = 0.65) -> bool:
    """
    Decide se a linha será humanizada (não-LPU) ou ficará muito próxima da LPU (seria pega no fuzzy).
    """
    return random.random() < prob_non_lpu


# ------------------------------
# Main generator
# ------------------------------
def generate_orcamento_from_lpu(
    lpu_df: pd.DataFrame,
    n_lines_from_lpu: int = 300,
    n_noise_lines: int = 40,
    prob_non_lpu: float = 0.65,
) -> pd.DataFrame:
    """
    Gera orçamento a partir de uma amostra da LPU.

    Args:
        lpu_df: DataFrame LPU com colunas COD_LPU, DESC_LPU, UN, PRECO_REF
        n_lines_from_lpu: quantas linhas do orçamento serão derivadas de itens LPU (com GT)
        n_noise_lines: quantas linhas de ruído (sem GT)
        prob_non_lpu: probabilidade de criar uma linha humanizada (Não-LPU)

    Returns:
        DataFrame orçamento com GT_COD_LPU e flags.
    """
    required_cols = {"COD_LPU", "DESC_LPU", "UN", "PRECO_REF"}
    missing = required_cols - set(lpu_df.columns)
    if missing:
        raise ValueError(f"LPU está faltando colunas obrigatórias: {missing}")

    sample = lpu_df.sample(n=min(n_lines_from_lpu, len(lpu_df)), random_state=SEED).reset_index(drop=True)

    rows = []
    id_item = 1

    for _, r in sample.iterrows():
        cod = str(r["COD_LPU"])
        desc = str(r["DESC_LPU"])
        un = str(r["UN"]).upper().strip()
        preco_ref = float(r["PRECO_REF"])

        is_non_lpu = should_be_non_lpu_line(prob_non_lpu=prob_non_lpu)

        if is_non_lpu:
            nome_item = humanize_from_lpu(desc, un)
            tipo_linha = "NAO_LPU_HUMANO"
        else:
            # linha bem próxima do catálogo (seria pega por fuzzy)
            nome_item = normalize_text(desc)
            tipo_linha = "PROXIMO_LPU"

        qtd = sample_qty_for_unit(un)
        preco_pago = paid_price_from_ref(preco_ref)

        rows.append(
            {
                "ID_ITEM": id_item,
                "NOME_ITEM": nome_item,
                "UN": un,
                "QTD": qtd,
                "PRECO_PAGO_UNIT": preco_pago,
                "GT_COD_LPU": cod,
                "FLAG_NAO_LPU": 1 if is_non_lpu else 0,
                "TIPO_LINHA": tipo_linha,
            }
        )
        id_item += 1

    # ruído/admin
    for _ in range(n_noise_lines):
        nome, un = random.choice(NOISE_LINES)
        preco_pago = round(float(np.random.lognormal(mean=math.log(6000), sigma=0.7)), 2)
        rows.append(
            {
                "ID_ITEM": id_item,
                "NOME_ITEM": nome,
                "UN": un,
                "QTD": 1,
                "PRECO_PAGO_UNIT": preco_pago,
                "GT_COD_LPU": None,
                "FLAG_NAO_LPU": 1,
                "TIPO_LINHA": "RUIDO_ADMIN",
            }
        )
        id_item += 1

    return pd.DataFrame(rows)


def load_lpu_excel(path: str, sheet: str) -> pd.DataFrame:
    df = pd.read_excel(path, sheet_name=sheet)
    # normaliza nomes de coluna se vierem diferentes
    rename = {}
    for c in df.columns:
        cu = c.upper().strip()
        if cu == "COD_LPU":
            rename[c] = "COD_LPU"
        elif cu in ["DESC_LPU", "DESCRICAO", "DESCRIÇÃO", "DESC"]:
            rename[c] = "DESC_LPU"
        elif cu in ["UN", "UNIDADE"]:
            rename[c] = "UN"
        elif cu in ["PRECO_REF", "PRECO", "PREÇO", "PRECOREFERENCIA"]:
            rename[c] = "PRECO_REF"
    df = df.rename(columns=rename)

    # garante colunas
    if "DESC_LPU" in df.columns:
        df["DESC_LPU"] = df["DESC_LPU"].astype(str).map(normalize_text)
    if "UN" in df.columns:
        df["UN"] = df["UN"].astype(str).map(lambda x: x.upper().strip())
    return df


def save_orcamento_excel(df: pd.DataFrame, out_path: str, sheet: str):
    """
    Salva o DataFrame gerado em um arquivo Excel.

    Args:
        df (pd.DataFrame): DataFrame contendo os dados do orçamento.
        out_path (str): Caminho do arquivo de saída.
        sheet (str): Nome da aba no Excel.
    """
    with pd.ExcelWriter(out_path, engine="openpyxl") as w:
        df.to_excel(w, index=False, sheet_name=sheet)


if __name__ == "__main__":
    # Caminhos ajustados para salvar no mesmo diretório do script embeddings
    lpu_path = Path(DEFAULT_LPU_PATH)
    out_path = Path(__file__).parent / DEFAULT_OUT_PATH

    # Carrega a LPU
    lpu_df = load_lpu_excel(str(lpu_path), sheet=DEFAULT_LPU_SHEET)

    # Gera orçamento
    orc_df = generate_orcamento_from_lpu(
        lpu_df=lpu_df,
        n_lines_from_lpu=300,   # ajuste
        n_noise_lines=40,       # ajuste
        prob_non_lpu=0.65,      # 65% humanizado (não-LPU)
    )

    # Salva o orçamento gerado
    save_orcamento_excel(orc_df, str(out_path), sheet=DEFAULT_OUT_SHEET)

    print(f"✅ Orçamento gerado: {out_path}")
    print(f"Linhas: {orc_df.shape[0]} | Colunas: {orc_df.shape[1]}")

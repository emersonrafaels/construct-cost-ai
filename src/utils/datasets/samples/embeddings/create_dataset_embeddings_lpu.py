"""
Este script gera um conjunto de dados sintético para análise de custos de construção
(LPU - Lista de Preços Unitários), no padrão operacional usado em bases de obra.

Ele cria itens com descrições semelhantes às LPUs reais (siglas, dimensões, qualificadores),
unidades (M2, M, UN, PT, CJ, VB, BR, M3, ML, KG) e preços de referência plausíveis.

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

import pandas as pd
import numpy as np

# ------------------------------
# Config
# ------------------------------
SEED = 42
random.seed(SEED)
np.random.seed(SEED)


def choose(seq):
    """Seleciona aleatoriamente um elemento de uma sequência."""
    return random.choice(seq)


def join_clean(parts, sep=" "):
    """Junta partes com limpeza de espaços e formatação básica."""
    s = sep.join([p for p in parts if p and str(p).strip()])
    s = re.sub(r"\s+", " ", s).strip()
    s = re.sub(r"\s+\+", " +", s)
    s = re.sub(r"\+\s+", "+ ", s)
    return s


# Faixas de preço base por unidade (ajustáveis)
unit_price_base = {
    "M2": (15, 450),
    "M": (10, 250),
    "UN": (50, 6500),
    "PT": (30, 900),
    "CJ": (80, 9000),
    "VB": (50, 25000),
    "M3": (120, 2200),
    "ML": (10, 250),
    "BR": (20, 600),
    "KG": (3, 60),  # ✅ novo: aço, armaduras, etc.
}


def price_for_unit(un: str) -> float:
    """Gera um preço aleatório (lognormal) respeitando faixa por unidade."""
    lo, hi = unit_price_base.get(un, (20, 500))
    x = np.random.lognormal(mean=math.log((lo + hi) / 4), sigma=0.6)
    return float(np.clip(x, lo, hi))


def add_transport(desc: str) -> str:
    """Adiciona COM TRANSP. quando aplicável."""
    return desc + ("" if "TRANSP" in desc else " COM TRANSP.")


dims_inch = ['1/2"', '3/4"', '7/8"', '1"', '1 1/4"', '1 1/2"', '2"', '3"', '4"']
dims_mm = ["8MM", "10MM", "12MM", "15MM", "20MM", "25MM", "32MM"]
sizes_grid = ["62,5X62,5", "60X60", "120X60", "30X30", "45X45", "90X90"]


# ------------------------------
# Geradores "core" (já existentes)
# ------------------------------
def gen_vedacao_variants():
    base = []
    faces = ["1 FACE", "2 FACES"]
    qualificadores = ["", "ACUSTICA", "HIDRORREPELENTE", "COM REFORCO", "ESTRUTURAL LEVE"]
    objs = ["PAREDE", "DIVISORIA", "FECHAMENTO VERTICAL"]
    mats = ["GESSO", "DRYWALL", "GESSO ACARTONADO", "MDF"]

    for obj in objs:
        for mat in mats:
            for f in faces:
                for q in qualificadores:
                    desc = join_clean([obj, "DE", mat, f, q])
                    base.append((desc, "M2"))

    for q in ["", "COM PORTAS", "COM PERFIL U", "COM PORTAS + PERFIL"]:
        base.append((join_clean(["DIVISORIA SANITARIA", q]).replace("+", "+"), "M2"))

    return base


def gen_forro_variants():
    base = []
    for mat in ["GESSO", "DRYWALL", "MINERAL", "PVC"]:
        for size in ["", choose(sizes_grid)]:
            for q in ["", "REMOVIVEL", "ACUSTICO", "LISO", "MODULAR"]:
                d = join_clean(["FORRO", "DW" if mat == "DRYWALL" else mat, q, size])
                base.append((d, "M2"))
    return base


def gen_pintura_variants():
    base = []
    for tipo in ["PINTURA LATEX", "PINTURA ACRILICA", "PINTURA ESMALTE", "PINTURA EPOXI"]:
        for base_mat in ["SOBRE GESSO", "SOBRE ALVENARIA", "EM METAL", "EM PISO"]:
            for q in ["", "2 DEMAOS", "3 DEMAOS", "ACABAMENTO FOSCO", "ACABAMENTO SEMIBRILHO"]:
                base.append((join_clean([tipo, base_mat, q]), "M2"))
    return base


def gen_demolicao_variants():
    base = []
    targets = [
        ("PISO", "M2"),
        ("PAREDE EM ALVENARIA", "M2"),
        ("CONCRETO ARMADO", "M3"),
        ("FORRO", "M2"),
        ("REVESTIMENTO CERAMICO", "M2"),
        ("COBERTURA", "M2"),
    ]
    for t, un in targets:
        for q in ["", "+ LASTRO", "+ REBOCO", "+ CONTRAPISO", "MEC."]:
            d = join_clean(["DEMOLICAO DE", t, q])
            if random.random() < 0.75:
                d = add_transport(d)
            base.append((d, un))
        for q in ["", "COM TRANSP.", "SEM TRANSP."]:
            base.append((join_clean(["REMOCAO DE", t, q]), un))
    return base


def gen_pisos_variants():
    base = []
    for mat in ["PORCELANATO", "CERAMICO", "VINILICO", "PISO EPOXI"]:
        for q in ["", "ANTIDERRAPANTE", "CIMENTO NATURAL", "ACABAMENTO POLIDO", "ALTO TRAFEGO"]:
            base.append((join_clean(["PISO", mat, q]), "M2"))
    for item in ["CONTRAPISO", "REGULARIZACAO DE PISO", "CIMENTADO DESEMPENADO E=2CM"]:
        for q in ["", "COM ADITIVO", "COM MALHA POP", "COM TRANSP."]:
            base.append((join_clean([item, q]), "M2"))
    return base


def gen_eletrica_variants():
    base = []
    for d in ['1/2"', '3/4"', '1"', '1 1/4"', '1 1/2"', '2"']:
        base.append((f"ELETRODUTO {d} PVC", "M"))
        base.append((f"ELETRODUTO {d} ACO GALVANIZADO", "M"))
    for w in ["40CM", "60CM", "70CM", "100MM", "150MM"]:
        base.append((f"CALHA EM CHAPA GALVANIZADA {w}", "M"))
        base.append((f"ELETROCALHA PERFURADA {w}", "M"))
    for size in ['4"X2"', '4"X4"', "20X20X10CM", "20X20X12CM"]:
        base.append((f"CAIXA PASSAGEM {size} COM TAMPA PARAFUSADA", "UN"))
    for p in [
        "PONTO DE FORCA",
        "PONTO DE ILUMINACAO",
        "PONTO PARA CAMERA",
        "PONTO PARA SENSOR",
        "PONTO PARA CFTV",
    ]:
        base.append((p, "PT"))
        base.append((p + " (AREA DA AGENCIA)", "PT"))
    for q in ["LED EMBUTIR", "LED SOBREPOR", "DE EMERGENCIA", "PAINEL 60X60", "LUMINARIA DE SAIDA"]:
        base.append((f"LUMINARIA {q}", "UN"))
    base.append(("QUADRO ELETRICO (MONTAGEM)", "UN"))
    base.append(("QUADRO DE DISTRIBUICAO C/ DISJUNTORES", "UN"))
    return base


def gen_dados_variants():
    base = []
    for p in ["PONTO DE LOGICA", "PONTO DE REDE", "PONTO CAT6", "PONTO DE TELEFONE"]:
        base.append((p, "PT"))
    for t in ["CABO UTP CAT6", "CABO TELEFONE CCI 50-2", "CABO DE COBRE NU 35MM2"]:
        base.append((t, "M"))
    return base


def gen_hidraulica_variants():
    base = []
    for d in ["20MM", "25MM", "32MM", "40MM", "50MM", "75MM", "100MM"]:
        base.append((f"TUBO PVC {d}", "M"))
    for item in [
        "BACIA SANITARIA",
        "LAVATORIO",
        "CUBA INOX",
        "TORNEIRA",
        "MISTURADOR",
        "VALVULA DE DESCARGA",
    ]:
        base.append((item, "UN"))
    return base


def gen_esquadrias_vidros_variants():
    base = []
    for mm in ["8MM", "10MM", "12MM", "15MM"]:
        base.append((f"VIDRO TEMPERADO {mm} INCOLOR", "M2"))
        base.append((f"VIDRO TEMPERADO {mm} COM PERFIL", "M2"))
    for item in [
        "PORTA DE MADEIRA",
        "PORTA DE VIDRO TEMPERADO",
        "JANELA DE ALUMINIO",
        "ESQUADRIA DE ALUMINIO",
    ]:
        for q in ["", "COM BATENTE", "COM FERRAGEM", "COM PUXADOR", "SOB MEDIDA"]:
            base.append((join_clean([item, q]), "UN" if "PORTA" in item else "M2"))
    return base


def gen_metalicos_variants():
    base = []
    for item in [
        "CORRIMAO",
        "GUARDA-CORPO",
        "GRADIL",
        "PAINEL METALICO",
        "ESTRUTURA METALICA AUX.",
    ]:
        for mat in ["ACO", "INOX", "ALUMINIO"]:
            for q in [
                "",
                "PISO DUPLO 1 LADO",
                "PISO DUPLO 2 LADOS",
                "CHAPA GALVANIZADA",
                "REFORCADO",
            ]:
                un = "M" if item in ["CORRIMAO", "GRADIL", "GUARDA-CORPO"] else "M2"
                base.append((join_clean([item, mat, q]), un))
    return base


def gen_limpeza_variants():
    return [
        ("LIMPEZA FINAL DE OBRA", "M2"),
        ("LIMPEZA POS-OBRA", "M2"),
        ("LIMPEZA GERAL - FINAL DE OBRA", "M2"),
    ]


# ------------------------------
# ✅ Novos geradores (mais parecidos com seus exemplos)
# ------------------------------
def gen_locacoes_variants():
    """ALUGUEL DE PLATAFORMA / andaimes / equipamentos (VB)."""
    base = []
    eqs = [
        "PLATAFORMA",
        "PLATAFORMA ELEVATORIA",
        "ANDAIME",
        "BETONEIRA",
        "COMPACTADOR",
        "MARTELETE",
        "GERADOR",
        "BOMBA D'AGUA",
    ]
    for e in eqs:
        for q in ["", "DIARIA", "SEMANAL", "MENSAL", "COM OPERADOR", "SEM OPERADOR"]:
            base.append((join_clean(["ALUGUEL DE", e, q]), "VB"))
    return base


def gen_alvenaria_siporex_variants():
    """ALVENARIA SIPOREX/PUMEX com espessuras (M2)."""
    base = []
    blocos = ["SIPOREX", "SIPOREX (PUMEX)", "SIPOREX (PUMEX)"]
    esp = ["10CM", "12,5CM", "15CM", "20CM"]
    for b in blocos:
        for e in esp:
            # Exemplo do Emerson: ALVENARIASIPOREX 15CM (PUMEX)
            base.append((f"ALVENARIA {b} {e}", "M2"))
            base.append((f"ALVENARIA{b.replace(' ', '')} {e}", "M2"))
    return base


def gen_armacao_ca_variants():
    """ARMAÇÃO CA-50/CA-60 para fundação etc. (KG)."""
    base = []
    aco = ["CA-50", "CA-60"]
    aplic = ["PARA FUNDACAO", "PARA PILARES", "PARA VIGAS", "PARA LAJE", "PARA SAPATA"]
    bit = ["6,3MM", "8MM", "10MM", "12,5MM", "16MM", "20MM"]
    for a in aco:
        for ap in aplic:
            for b in bit:
                base.append((join_clean(["ARMACAO", a, ap, "BITOLA", b]), "KG"))
            base.append((join_clean(["ARMACAO", a, ap]), "KG"))  # versão curta
    return base


def gen_barras_perfis_aluminio_variants():
    """BARRA CHATA / PERFIS TE/UE etc. alumínio, com medidas em polegadas (BR)."""
    base = []
    perfis = ["BARRA CHATA", "PERFIL TE", "PERFIL U", "PERFIL L"]
    mats = ["ALUMINIO", "ACO INOX", "ACO GALVANIZADO"]
    medidas = ['7/8"x1/8"', '1"x1/8"', '1 1/4"x1/8"', '1 1/2"x3/16"', '2"x1/4"']
    for p in perfis:
        for m in mats:
            for med in medidas:
                base.append(
                    (
                        join_clean([p, "TE" if p == "BARRA CHATA" else "", m, med, "COM FIXACAO"]),
                        "BR",
                    )
                )
    # Exemplo idêntico ao seu
    base.append(('BARRA CHATA TE ALUMINIO 7/8"x1/8" COM FIXACAO', "BR"))
    return base


def gen_pcd_variants():
    """Itens PCD, barra de apoio etc. (CJ)."""
    base = []
    diam = ["D=32MM", "D=38MM"]
    for d in diam:
        base.append((join_clean(["BARRA DE APOIO PARA SANIT PCD ACO INOX", d]), "CJ"))
        base.append((join_clean(["BARRA DE APOIO PCD ACO INOX", d, "COM FIXACAO"]), "CJ"))
    # Exemplo idêntico
    base.append(("BARRA DE APOIO PARA SANIT PCD ACO INOX D=32MM", "CJ"))
    return base


def gen_atm_variants():
    """Itens de ATM (UN)."""
    base = []
    base.append(("BASE PARA ATM NO SOLO", "UN"))  # exemplo idêntico
    for q in ["", "REFORCADA", "COM CHUMBADORES", "COM NIVELAMENTO", "COM CONCRETO"]:
        base.append((join_clean(["BASE PARA ATM NO SOLO", q]), "UN"))
    return base


def gen_seed_examples():
    """
    Injeta exemplos "âncora" exatamente como você trouxe, com preço aproximado.
    Esses itens entram SEM depender de variação aleatória.
    """
    # (desc, un, preco_fixo_opcional)
    return [
        ("ALUGUEL DE PLATAFORMA", "VB", 9790.00),
        ("ALVENARIASIPOREX 15CM (PUMEX)", "M2", 202.90),
        ("ARMACAO CA-50 PARA FUNDACAO", "KG", 22.62),
        ('BARRA CHATA TE ALUMINIO 7/8"x1/8" COM FIXACAO', "BR", 42.14),
        ("BARRA DE APOIO PARA SANIT PCD ACO INOX D=32MM", "CJ", 1950.60),
        ("BASE PARA ATM NO SOLO", "UN", 592.11),
    ]


def minor_variations(desc: str):
    """Pequenas variações de escrita (abreviações) mantendo padrão LPU."""
    vars_ = [desc]
    reps = [
        (" DRYWALL", " DW"),
        (" COM TRANSP.", " C/ TRANSP."),
        (" ACUSTICO", " ACUST."),
        (" ACO GALVANIZADO", " ACO GALV."),
        (" COM FIXACAO", " C/ FIXACAO"),
    ]
    for a, b in reps:
        if a in desc and random.random() < 0.55:
            vars_.append(desc.replace(a, b))

    if random.random() < 0.20:
        vars_.append(desc + " INCLUSO MATERIAL")

    # variações comuns com hífen/sem hífen (ex: CA-50 / CA50)
    if "CA-50" in desc and random.random() < 0.4:
        vars_.append(desc.replace("CA-50", "CA50"))
    if "CA-60" in desc and random.random() < 0.4:
        vars_.append(desc.replace("CA-60", "CA60"))

    return list(dict.fromkeys(vars_))


def build_lpu(n_items=1500, out_path="BASE_LPU_EMBEDDINGS.xlsx"):
    """
    Constrói uma LPU sintética com ~n_items itens, padrão semelhante a base real.

    Output:
        - Excel (aba BASE_LPU)
        - Colunas: COD_LPU, DESC_LPU, UN, PRECO_REF
    """
    library = []

    # core
    for fn in [
        gen_vedacao_variants,
        gen_forro_variants,
        gen_pintura_variants,
        gen_demolicao_variants,
        gen_pisos_variants,
        gen_eletrica_variants,
        gen_dados_variants,
        gen_hidraulica_variants,
        gen_esquadrias_vidros_variants,
        gen_metalicos_variants,
        gen_limpeza_variants,
    ]:
        library.extend(fn())

    # ✅ novos blocos "reais"
    for fn in [
        gen_locacoes_variants,
        gen_alvenaria_siporex_variants,
        gen_armacao_ca_variants,
        gen_barras_perfis_aluminio_variants,
        gen_pcd_variants,
        gen_atm_variants,
    ]:
        library.extend(fn())

    # dedup
    uniq = {}
    for desc, un in library:
        uniq[(desc.upper(), un.upper())] = (desc.upper(), un.upper())
    library = list(uniq.values())

    # expand com pequenas variações
    expanded = []
    for desc, un in library:
        for v in minor_variations(desc):
            expanded.append((v, un))

    uniq2 = {}
    for d, u in expanded:
        uniq2[(d, u)] = (d, u)
    expanded = list(uniq2.values())

    # injeta exemplos âncora com preços fixos
    anchors = gen_seed_examples()
    anchor_rows = []
    for desc, un, preco in anchors:
        anchor_rows.append(("ANCHOR", desc.upper(), un.upper(), float(preco)))

    # completa até n_items (com sufixos)
    while len(expanded) < n_items:
        d, u = random.choice(expanded)
        suf = choose(["", " (AREA DA AGENCIA)", " (SALAS)", " (SANITARIO)", " (CORREDOR)"])
        expanded.append((d + suf if suf and suf not in d else d, u))

    expanded = expanded[:n_items]

    prefixes = ["OBA", "OBB", "OBC", "OBD", "OBE"]  # mais diversidade
    rows = []

    # adiciona anchors primeiro
    # Obs.: cod será gerado normalmente, mas mantendo preço fixo para os anchors
    i = 1
    for _, desc, un, preco in anchor_rows:
        prefix = random.choices(prefixes, weights=[10, 45, 15, 15, 15])[0]
        cod = f"{prefix}-{i:03d}"
        rows.append((cod, desc, un, round(float(preco), 2)))
        i += 1

    # adiciona o restante
    for desc, un in expanded:
        prefix = random.choices(prefixes, weights=[10, 45, 15, 15, 15])[0]
        cod = f"{prefix}-{i:03d}"
        preco = round(price_for_unit(un), 2)
        rows.append((cod, desc, un, preco))
        i += 1

    df = pd.DataFrame(rows, columns=["COD_LPU", "DESC_LPU", "UN", "PRECO_REF"])

    with pd.ExcelWriter(out_path, engine="openpyxl") as w:
        df.to_excel(w, index=False, sheet_name="BASE_LPU")

    return df


if __name__ == "__main__":
    out_path = Path(Path(__file__).parents[0], "BASE_LPU_EMBEDDINGS.xlsx")
    df_lpu = build_lpu(n_items=1500, out_path=str(out_path))
    print(df_lpu.shape, f"-> arquivo gerado: {out_path}")

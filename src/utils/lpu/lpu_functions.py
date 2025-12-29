from typing import List, Tuple
from itertools import product

import pandas as pd


def generate_region_group_combinations(
    regions: List[str], groups: List[str], combine_regions: bool = True
) -> List[str]:
    """
    Gera combinações de regiões e grupos.

    Args:
        regions (List[str]): Lista de regiões.
        groups (List[str]): Lista de grupos.
        combine_regions (bool): Se True, combina duas regiões com grupos (ex.: 'NORTE/NORDESTE-GRUPO1').
                                Se False, combina apenas uma região com grupos (ex.: 'NORTE-GRUPO1').

    Returns:
        List[str]: Lista de combinações geradas.
    """
    if combine_regions:
        # Combina duas regiões com grupos
        return [
            f"{r1}/{r2}-{g}" for r1, r2 in product(regions, regions) if r1 != r2 for g in groups
        ]
    else:
        # Combina apenas uma região com grupos
        return [f"{region}-{group}" for region in regions for group in groups]


def split_regiao_grupo(regiao_grupo: str, regions: List[str], groups: List[str]) -> Tuple[str, str]:
    """
    Divide a coluna regiao_grupo em 'regiao' e 'grupo' com base nas regiões e grupos definidos.

    Args:
        regiao_grupo (str): Valor da coluna regiao_grupo (ex.: 'CENTRO-OESTE/NORDESTE-GRUPO1').
        regions (List[str]): Lista de regiões definidas no settings.
        groups (List[str]): Lista de grupos definidos no settings.

    Returns:
        Tuple[str, str]: Uma tupla contendo 'regiao' e 'grupo'.

    Raises:
        ValueError: Se o valor não puder ser dividido corretamente.
    """
    for region in regions:
        for group in groups:
            if f"-{group}" in regiao_grupo and region in regiao_grupo:
                regiao = regiao_grupo.split(f"-{group}")[0].strip()
                grupo = group
                return regiao, grupo
    raise ValueError(f"Não foi possível dividir o valor '{regiao_grupo}' em 'regiao' e 'grupo'.")

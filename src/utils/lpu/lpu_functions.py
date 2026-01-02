"""
Módulo de funções utilitárias para manipulação de dados LPU (Lista de Preços Unitários).
"""

__author__ = "Emerson V. Rafael (emervin)"
__copyright__ = "Copyright 2025, Construct Cost AI"
__credits__ = ["Emerson V. Rafael"]
__license__ = "MIT"
__version__ = "1.0.0"
__maintainer__ = "Emerson V. Rafael"
__email__ = "emersonssmile@gmail.com"
__status__ = "Development"

import re
import sys
from itertools import product

from pathlib import Path
from typing import List, Tuple

import pandas as pd

# Adiciona o diretório src ao path
base_dir = Path(__file__).parents[3]
sys.path.insert(0, str(Path(base_dir, "src")))

from config.config_logger import logger
from config.config_dynaconf import get_settings
from utils.data.data_functions import (
    merge_data_with_columns,
    two_stage_merge,
)

settings = get_settings()


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


def extract_group(value: str) -> str:
    """
    Extrai o grupo de um valor combinado de região-grupo.

    Args:
        value (str): Valor no formato 'REGIAO1/REGIAO2-GRUPO1'.

    Returns:
        str: O grupo extraído (ex.: 'GRUPO1', 'GRUPO2', 'GRUPO3').
    """
    # Define o padrão regex para capturar o grupo no formato '-GRUPOX'
    pattern = settings.get("regex_patterns.group_pattern", r"-GRUPO\d+")
    match = re.search(pattern, value)
    if match:
        return match.group(0).lstrip("-").strip()  # Remove o "-" do início e retorna o grupo
    return None


def separate_regions(
    df: pd.DataFrame, col_to_regiao_grupo: List[str], regions: List[str]
) -> pd.DataFrame:
    """
    Separa as regiões presentes nas colunas combinadas em colunas individuais.

    Args:
        df (pd.DataFrame): DataFrame contendo a coluna `regiao_grupo`.
        col_to_regiao_grupo (List[str]): Lista de colunas combinadas no formato 'REGIAO1/REGIAO2-GRUPO'.
        regions (List[str]): Lista de regiões possíveis.

    Returns:
        pd.DataFrame: DataFrame com colunas separadas para cada região.
    """

    def check_region_presence(value: str, region: str) -> int:
        """
        Verifica se uma região está presente em um valor combinado de regiões usando regex.

        Args:
            value (str): Valor no formato 'REGIAO1/REGIAO2-GRUPO'.
            region (str): Região a ser verificada.

        Returns:
            str: regiao se a região estiver presente, None caso contrário.
        """
        # Define o padrão regex para encontrar a região no início da string, após "/", ou no final
        pattern = rf"(?:^|/){re.escape(region)}(?:/|-[^/]+$)"
        return region if re.search(pattern, value) else None

    # Cria uma cópia do DataFrame para evitar alterações no original
    df_regions = df.copy()

    # Percorrendo todas as regiões para criar colunas separadas
    for region in regions:
        # Percorrendo todas as colujnas do dataframe que contêm regiões/grupos
        for column in df_regions[col_to_regiao_grupo].columns:
            # Verificando se a região está presente na coluna atual
            result = check_region_presence(value=column, region=region)
            if result:

                # Obtendo o valor do grupo correspondente
                group = extract_group(value=column)

                # Cria o valor da nova coluna (região-grupo)
                region_grupo = f"{region}-{group}"

                # Salva a região na nova coluna
                df_regions[region_grupo] = df_regions[column]

                col_to_regiao_grupo.append(region_grupo)

    # Retorna o DataFrame atualizado e a lista de colunas atualizada
    return df_regions, col_to_regiao_grupo


def merge_budget_lpu(
    df_budget: pd.DataFrame,
    df_lpu: pd.DataFrame,
    columns_on_budget: List[List[str]],
    columns_on_lpu: List[List[str]],
    how: str = "inner",
    validate: str = "many_to_many",
    use_two_stage_merge: bool = False,
) -> dict:
    results = {}

    # Evita efeito colateral
    budget = df_budget.copy()
    lpu = df_lpu.copy()

    # Verifica se a coluna _merge já existe e renomeia para evitar conflitos
    if "_merge" in budget.columns:
        budget = budget.rename(columns={"_merge": "_merge_budget"})
    if "_merge" in lpu.columns:
        lpu = lpu.rename(columns={"_merge": "_merge_lpu"})

    # Verifica se é desejado usar o merge em duas etapas
    if use_two_stage_merge:
        merged_df = two_stage_merge(
            left=budget,
            right=lpu,
            keys_stage1=columns_on_budget,
            keys_stage2=columns_on_lpu,
            how=how,
            suffixes=("_budget", "_lpu"),
            keep_indicator=True,
            validate_stage1=validate,
            validate_stage2=validate,
            handle_duplicates=True,
        )

        return merged_df

    # caso antigo: mantém o for (merge simples por combinação)
    consolidated_df = pd.DataFrame()
    
    # Itera sobre as combinações de colunas para realizar múltiplos merges
    for idx, (budget_cols, lpu_cols) in enumerate(zip(columns_on_budget, columns_on_lpu)):
        key = f"Budget: {budget_cols} <-> LPU: {lpu_cols}"
        merged_df = merge_data_with_columns(
            df_left=budget,
            df_right=lpu,
            left_on=budget_cols,
            right_on=lpu_cols,
            how=how,
            validate=validate_norm,
            suffixes=("_budget", f"_lpu_{idx}"),
            indicator=True,
            handle_duplicates=True,
        )
        consolidated_df = pd.concat([consolidated_df, merged_df], ignore_index=True)
        results[key] = {"success": True, "merged_rows": len(merged_df), "dataframe": merged_df}

    return consolidated_df
"""
Modulo para calcular discrepâncias entre valores pagos e valores da LPU.
"""

__author__ = "Emerson V. Rafael (emervin)"
__copyright__ = "Copyright 2025, Construct Cost AI"
__credits__ = ["Emerson V. Rafael"]
__license__ = "MIT"
__version__ = "1.0.0"
__maintainer__ = "Emerson V. Rafael"
__email__ = "emersonssmile@gmail.com"
__status__ = "Development"

import sys
from pathlib import Path
from typing import Union, Tuple, List, Optional, Literal, NamedTuple

import pandas as pd

# Adiciona o diretório src ao path
base_dir = Path(__file__).parents[5]
sys.path.insert(0, str(Path(base_dir, "src")))

from config.config_logger import logger
from config.config_dynaconf import get_settings
from utils.data.data_functions import (
    transform_case,
)

settings = get_settings()

def calculate_lpu_discrepancies(
    df: pd.DataFrame,
    column_quantity: str = "qtde",
    column_unit_price_paid: str = "unitario_pago",
    column_unit_price_lpu: str = "unitario_lpu",
    column_total_paid: str = "valor_pago",
    column_total_lpu: str = "valor_lpu",
    column_difference: str = "dif_total",
    column_status: str = "status_conciliacao",
    tol_percentile: float = None,
) -> pd.DataFrame:
    """
    Calcula o valor LPU e compara com o valor pago, identificando discrepâncias.

    Args:
        df (pd.DataFrame): DataFrame contendo os dados.
        column_quantity (str): Nome da coluna de quantidade.
        column_unit_price_paid (str): Nome da coluna de preço unitário pago.
        column_unit_price_lpu (str): Nome da coluna de preço unitário LPU.
        column_total_paid (str): Nome da coluna de valor total pago.
        column_total_lpu (str): Nome da coluna de valor total LPU.
        column_difference (str): Nome da coluna de diferença total.
        column_status (str): Nome da coluna de status de conciliação.
        tol_percentile (float): Tolerância percentual para discrepâncias.

    Returns:
        pd.DataFrame: DataFrame atualizado com as colunas de valor LPU, diferença e status.
    """
    
    if verbose:
        logger.info(
            f"🧮 Calculando discrepâncias (tolerância {settings.get('validador_lpu.tolerancia_percentual')}%)..."
        )
    
    # Calcula o valor total LPU
    df[column_total_lpu] = df[column_quantity] * df[column_unit_price_lpu]

    # Calcula a diferença entre o valor pago e o valor LPU
    df[column_difference] = df[column_total_paid] - df[column_total_lpu]

    # Define o status de conciliação com base na tolerância
    if tol_percentile is None:
        tol_percentile = settings.get("module_validator_lpu.tol_percentile", 0)

    tolerance_value = df[column_total_lpu] * (tol_percentile / 100)

    def classify_discrepancy(row):
        if abs(row[column_difference]) <= tolerance_value[row.name]:
            return "OK"
        elif row[column_difference] > 0:
            return "Para ressarcimento"
        else:
            return "Abaixo LPU"

    df[column_status] = df.apply(classify_discrepancy, axis=1)

    return df
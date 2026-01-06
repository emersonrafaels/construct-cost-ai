"""
Modulo para obter as estatísticas de validação da LPU.
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
base_dir = Path(__file__).parents[6]
sys.path.insert(0, str(Path(base_dir, "src")))

from config.config_logger import logger
from config.config_dynaconf import get_settings

settings = get_settings()


def calculate_validation_stats(df_result: pd.DataFrame, verbose: bool = True) -> None:
    """
    Calculate and display validation statistics for LPU.

    This function computes various statistics related to the validation of LPU data, such as the total number of items,
    the number of items in different reconciliation statuses, and the total budgeted and divergence values. The results
    can be displayed in the console and logged for debugging purposes.

    Args:
        df_result (pd.DataFrame): DataFrame containing the validation results. It must include the following columns:
            - "status_conciliacao": Status of reconciliation (e.g., "OK", "Para ressarcimento", "Abaixo LPU").
            - "valor_total_orcado": Total budgeted value.
            - "dif_total": Total divergence value.
        verbose (bool): If True, displays the statistics in the console. Defaults to True.

    Returns:
        None
    """
    # General statistics
    total_items = len(df_result)
    items_ok = (df_result["status_conciliacao"] == "OK").sum()
    items_refund = (df_result["status_conciliacao"] == "Para ressarcimento").sum()
    items_below = (df_result["status_conciliacao"] == "Abaixo LPU").sum()

    total_budgeted_value = df_result["valor_total_orcado"].sum()
    total_divergence = df_result["dif_total"].sum()
    refund_divergence = df_result[df_result["status_conciliacao"] == "Para ressarcimento"][
        "dif_total"
    ].sum()

    # Display statistics in the console
    if verbose:
        logger.info("")
        logger.info("📊 VALIDATION STATISTICS")
        logger.info("-" * 80)
        logger.info(f"   Total items validated: {total_items}")
        logger.info(f"   ✅ OK: {items_ok} ({items_ok/total_items*100:.1f}%)")
        logger.info(f"   ⚠️  For refund: {items_refund} ({items_refund/total_items*100:.1f}%)")
        logger.info(f"   📉 Below LPU: {items_below} ({items_below/total_items*100:.1f}%)")
        logger.info("")
        logger.info(f"   💰 Total budgeted value: R$ {total_budgeted_value:,.2f}")
        logger.info(f"   💵 Total divergence: R$ {total_divergence:,.2f}")
        logger.info(f"   💸 Potential refund: R$ {refund_divergence:,.2f}")
        logger.info("")

    # Log statistics for debugging
    logger.debug("📊 VALIDATION STATISTICS")
    logger.debug(f"Total items validated: {total_items}")
    logger.debug(f"✅ OK: {items_ok} ({items_ok/total_items*100:.1f}%)")
    logger.debug(f"⚠️  For refund: {items_refund} ({items_refund/total_items*100:.1f}%)")
    logger.debug(f"📉 Below LPU: {items_below} ({items_below/total_items*100:.1f}%)")
    logger.debug(f"💰 Total budgeted value: R$ {total_budgeted_value:,.2f}")
    logger.debug(f"💵 Total divergence: R$ {total_divergence:,.2f}")
    logger.debug(f"💸 Potential refund: R$ {refund_divergence:,.2f}")

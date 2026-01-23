"""
Modulo para obter as estatísticas de validação da LPU e gerar um relatório em PDF.
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
from construct_cost_ai.domain.validators.lpu.stats.generate_statistics_report import (
    generate_statistics_report,
)

settings = get_settings()


def calculate_validation_stats_and_generate_report(
    df_result: pd.DataFrame,
    validator_output_pdf: bool = True,
    output_pdf: str = "VALIDADOR_LPU.pdf",
    verbose: bool = None,
) -> None:
    """
    Calcula estatísticas de validação da LPU e gera um relatório em PDF.

    Args:
        df_result (pd.DataFrame): DataFrame contendo os resultados da validação. Deve incluir as seguintes colunas:
            - "STATUS CONCILIAÇÃO": Status da conciliação (e.g., "OK", "Para ressarcimento", "Abaixo LPU").
            - "VALOR TOTAL PAGO": Valor total pago.
            - "DIFERENÇA TOTAL": Valor total da divergência.
        validator_output_pdf (bool): Se True, salva o relatório em PDF. Caso contrário, não salva. Padrão é True.
        output_pdf (str): Caminho para salvar o relatório em PDF.
        verbose (bool): Se True, exibe as estatísticas no console. Padrão é None, e será lido do settings.


    Returns:
        None
    """
    # Define o valor padrão de verbose a partir do settings, se não for fornecido
    if verbose is None:
        verbose = settings.get("module_validator_lpu.verbosa")

    # Estatísticas gerais
    total_items = len(df_result)  # Total de itens validados
    items_ok = (
        df_result[settings.get("module_validator_lpu.column_status")] == "OK"
    ).sum()  # Itens com status OK
    items_refund = (
        df_result[settings.get("module_validator_lpu.column_status")] == "Para ressarcimento"
    ).sum()  # Itens para ressarcimento
    items_below = (
        df_result[settings.get("module_validator_lpu.column_status")] == "Abaixo LPU"
    ).sum()  # Itens abaixo da LPU
    items_not_lpu = (
        df_result[settings.get("module_validator_lpu.column_status")] == "Sem base LPU"
    ).sum()  # Itens sem base LPU

    total_paid_value = df_result[
        settings.get("module_validator_lpu.column_total_paid")
    ].sum()  # Valor total pago
    total_divergence = df_result[
        settings.get("module_validator_lpu.column_difference")
    ].sum()  # Divergência total
    refund_divergence = df_result[
        df_result[settings.get("module_validator_lpu.column_status")] == "Para ressarcimento"
    ][
        settings.get("module_validator_lpu.column_difference")
    ].sum()  # Potencial ressarcimento

    # Exibe estatísticas no console
    if verbose:
        logger.info("")
        logger.info("📊 ESTATÍSTICAS DE VALIDAÇÃO")
        logger.info("-" * 50)
        logger.info(f"   Total de itens validados: {total_items}")
        logger.info(f"✅ OK: {items_ok} ({items_ok/total_items*100:.1f}%)")
        logger.info(
            f"   ⚠️  Para ressarcimento: {items_refund} ({items_refund/total_items*100:.1f}%)"
        )
        logger.info(f"   📉 Abaixo LPU: {items_below} ({items_below/total_items*100:.1f}%)")
        logger.info(f"   📉 Sem base LPU: {items_not_lpu} ({items_not_lpu/total_items*100:.1f}%)")
        print("-" * 50)
        logger.info(f"   💰 Valor total pago: R$ {total_paid_value:,.2f}")
        logger.info(f"   💵 Divergência total: R$ {total_divergence:,.2f}")
        logger.info(f"   💸 Potencial ressarcimento: R$ {refund_divergence:,.2f}")
        print("-" * 50)

    # Gera o relatório em PDF, se permitido
    if validator_output_pdf:
        generate_statistics_report(df_result, output_pdf)
        logger.info(f"Relatório gerado com sucesso: {output_pdf}")
    else:
        logger.info("Geração de relatório em PDF foi desativada.")


# Exemplo de uso
if __name__ == "__main__":
    # Exemplo de DataFrame
    data = {
        settings.get("module_validator_lpu.column_status"): [
            "OK",
            "Para ressarcimento",
            "Abaixo LPU",
            "OK",
            "Para ressarcimento",
        ],
        settings.get("module_validator_lpu.column_total_paid"): [1000, 2000, 1500, 1200, 1800],
        settings.get("module_validator_lpu.column_difference"): [100, 200, -150, 0, 250],
    }
    df_result = pd.DataFrame(data)

    # Caminho para salvar o relatório
    output_pdf = "relatorio_validacao_lpu.pdf"

    # Calcula estatísticas e gera o relatório
    calculate_validation_stats_and_generate_report(df_result, output_pdf, validator_output_pdf=True)

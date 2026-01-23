"""
Módulo para calcular discrepâncias entre valores pagos e valores da LPU.
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

import numpy as np
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
    column_discrepancy: str = "discrepancia_percentual",
    column_status: str = "status_conciliacao",
    tol_percentile: float = None,
    verbose: bool = False,
) -> pd.DataFrame:
    """
    Calcula discrepâncias entre valores pagos e valores da LPU em um DataFrame.

    Args:
        df (pd.DataFrame): DataFrame de entrada contendo os dados.
        column_quantity (str): Nome da coluna para quantidade.
        column_unit_price_paid (str): Nome da coluna para preço unitário pago.
        column_unit_price_lpu (str): Nome da coluna para preço unitário LPU.
        column_total_paid (str): Nome da coluna para valor total pago.
        column_total_lpu (str): Nome da coluna para valor total LPU.
        column_difference (str): Nome da coluna para a diferença entre valores pagos e LPU.
        column_discrepancy (str): Nome da coluna para a discrepância percentual.
        column_status (str): Nome da coluna para o status de conciliação.
        tol_percentile (float): Percentual de tolerância para discrepâncias.
        verbose (bool): Se True, habilita logs detalhados.

    Returns:
        pd.DataFrame: DataFrame atualizado com as colunas calculadas.
    """

    def calculate_total_item(
        df: pd.DataFrame, column_total_value: str, column_quantity: str, column_unit_price: str
    ) -> None:
        """
        Calcula o valor total orçado em um DataFrame.

        Args:
            df (pd.DataFrame): DataFrame contendo os dados.
            column_total_value (str): Nome da coluna de valor total orçado.
            column_quantity (str): Nome da coluna de quantidade.
            column_unit_price (str): Nome da coluna de preço unitário.

        Returns:
            None: Atualiza o DataFrame com a coluna de valor total orçado calculada ou convertida.
        """

        # Verifica se a coluna de valor total orçado existe
        if column_total_value not in df.columns:

            # Se não existe, ele calcula usando quantidade * preço unitário
            df[column_total_value] = df[column_quantity] * df[column_unit_price]
        else:
            # Nesse caso a coluna existe, então:
            # 1 - Garante que está no formato numérico
            df[column_total_value] = pd.to_numeric(df[column_total_value], errors="coerce")

            # Filtra linhas onde o valor total é nulo ou menor/igual a zero
            mask = df[column_total_value].isna() | (df[column_total_value] <= 0)

            # 2 - Recalcula o valor total apenas para essas linhas
            df.loc[mask, column_total_value] = (
                df.loc[mask, column_quantity] * df.loc[mask, column_unit_price]
            )

    def calculate_total_paid(df: pd.DataFrame) -> None:
        """
        Calcula o valor total pago com base na quantidade e no preço unitário pago.
        """
        calculate_total_item(df, column_total_paid, column_quantity, column_unit_price_paid)

    def calculate_total_lpu(df: pd.DataFrame) -> None:
        """
        Calcula o valor total da LPU com base na quantidade e no preço unitário da LPU.
        """
        calculate_total_item(df, column_total_lpu, column_quantity, column_unit_price_lpu)

    def calculate_difference(df: pd.DataFrame) -> None:
        """
        Calcula a diferença entre os valores totais pagos e os valores totais da LPU.
        """
        if column_total_paid not in df.columns or column_total_lpu not in df.columns:
            logger.error(
                f"Colunas '{column_total_paid}' ou '{column_total_lpu}' não encontradas no DataFrame."
            )
        else:
            if verbose:
                logger.info("Calculando diferença entre valor total pago e valor total da LPU...")
            df[column_difference] = df[column_total_paid] - df[column_total_lpu]

    def calculate_discrepancy(df: pd.DataFrame) -> None:
        """
        Calcula a discrepância percentual com base na diferença e no valor total da LPU.
        """
        if tol_percentile is None:
            logger.error("Parâmetro 'tol_percentile' não fornecido.")
        else:
            if verbose:
                logger.info(f"Calculando discrepâncias com tolerância de {tol_percentile}%...")
            denom = df[column_total_lpu].replace({0: np.nan})  # Evita divisão por zero
            df[column_discrepancy] = (df[column_difference] / denom) * 100

    def classify_discrepancy(pct: float, tol: float) -> str:
        """
        Classifica a discrepância com base no valor de tolerância.

        Args:
            pct (float): Discrepância percentual.
            tol (float): Valor de tolerância.

        Returns:
            str: Classificação da discrepância.
        """
        if pd.isna(pct):
            return "ITEM NAO LPU"
        if abs(pct) <= tol:
            return "OK"
        return "PARA RESSARCIMENTO" if pct > 0 else "OK"

    def assign_status(df: pd.DataFrame, column_status) -> None:
        """
        Atribui um status de conciliação com base na discrepância e na tolerância.

        # Args:
            df (pd.DataFrame): DataFrame contendo os dados.
            column_status (str): Nome da coluna para o status de conciliação.

        # Returns:
            None: Atualiza o DataFrame com a coluna de status atribuída.

        """
        if tol_percentile is not None:
            if not (0 <= tol_percentile <= 100):
                logger.error("'tol_percentile' deve estar entre 0 e 100.")
            else:
                tolerance_value = tol_percentile  # A tolerância é diretamente o valor percentual
                df[column_status] = df[column_discrepancy].apply(
                    lambda pct: classify_discrepancy(pct, tolerance_value)
                )

    # Executa as etapas em sequência
    calculate_total_paid(df)
    calculate_total_lpu(df)
    calculate_difference(df)
    calculate_discrepancy(df)
    assign_status(df, column_status=column_status)

    return df

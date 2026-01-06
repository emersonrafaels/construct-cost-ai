"""
===============================================================================
MÓDULO: Validação de Discrepâncias LPU (Pago vs Referência)
===============================================================================

Este módulo implementa a lógica oficial de cálculo e classificação de
discrepâncias entre valores pagos em orçamentos de obras e os valores de
referência da LPU (Lista de Preços Unitários).

---------------------------------------------------------------------------
PADRÃO DE CÁLCULO ADOTADO (REGRA OFICIAL DO PRODUTO)
---------------------------------------------------------------------------

A diferença financeira é calculada SEMPRE como:

    DIFERENÇA = VALOR_PAGO − VALOR_LPU

Onde:
- VALOR_LPU representa o preço de referência oficial (benchmark esperado).
- VALOR_PAGO representa o preço efetivamente orçado ou realizado.

Este padrão segue a semântica clássica de auditoria, finanças e controle:
    desvio = observado − esperado

---------------------------------------------------------------------------
INTERPRETAÇÃO DO SINAL
---------------------------------------------------------------------------

- DIFERENÇA > 0  → Pagamento acima da LPU (sobrepreço)
                   → Caso potencial para ressarcimento.
- DIFERENÇA = 0  → Total aderência à LPU.
- DIFERENÇA < 0  → Pagamento abaixo da LPU (subpreço).

A discrepância percentual é calculada utilizando a LPU como denominador:

    DISCREPÂNCIA (%) = (VALOR_PAGO − VALOR_LPU) / VALOR_LPU × 100

Esse formato garante:
- Coerência matemática com o benchmark oficial.
- Leitura intuitiva do sinal (positivo = risco financeiro).
- Consistência com métricas executivas e indicadores de recuperação.

---------------------------------------------------------------------------
CLASSIFICAÇÃO DE STATUS (CONCEITO)
---------------------------------------------------------------------------

A classificação final do item considera uma tolerância percentual definida
pelo produto (ex: ±5%):

- |DISCREPÂNCIA (%)| ≤ tolerância → "OK"
- DISCREPÂNCIA (%)  > tolerância → "Para ressarcimento"
- DISCREPÂNCIA (%)  < -tolerância → "Abaixo LPU"
- VALOR_LPU inexistente ou zero  → "Sem base LPU"

---------------------------------------------------------------------------
MÉTRICA EXECUTIVA DERIVADA
---------------------------------------------------------------------------

Este padrão viabiliza o cálculo direto do indicador de negócio:

    Potencial de Recuperação (R$) = Σ max(0, VALOR_PAGO − VALOR_LPU)

Métrica utilizada para priorização de auditorias, análises de impacto
financeiro e acompanhamento de resultados do produto.

---------------------------------------------------------------------------
OBSERVAÇÃO IMPORTANTE
---------------------------------------------------------------------------

⚠️ NÃO inverter a fórmula para (VALOR_LPU − VALOR_PAGO).
Essa inversão quebra a semântica do sinal, dificulta a interpretação
executiva e aumenta o risco de erro operacional e analítico.

===============================================================================
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

    def calculate_total_paid(df: pd.DataFrame) -> None:
        """
        Calcula o valor total pago com base na quantidade e no preço unitário pago.
        """
        if column_quantity not in df.columns or column_unit_price_paid not in df.columns:
            logger.error(f"Colunas '{column_quantity}' ou '{column_unit_price_paid}' não encontradas no DataFrame.")
        else:
            if verbose:
                logger.info(f"Calculando valor total pago usando as colunas '{column_quantity}' e '{column_unit_price_paid}'...")
            df[column_total_paid] = df[column_quantity] * df[column_unit_price_paid]

    def calculate_total_lpu(df: pd.DataFrame) -> None:
        """
        Calcula o valor total da LPU com base na quantidade e no preço unitário da LPU.
        """
        if column_quantity not in df.columns or column_unit_price_lpu not in df.columns:
            logger.error(f"Colunas '{column_quantity}' ou '{column_unit_price_lpu}' não encontradas no DataFrame.")
        else:
            if verbose:
                logger.info(f"Calculando valor total da LPU usando as colunas '{column_quantity}' e '{column_unit_price_lpu}'...")
            df[column_total_lpu] = df[column_quantity] * df[column_unit_price_lpu]

    def calculate_difference(df: pd.DataFrame) -> None:
        """
        Calcula a diferença entre os valores totais pagos e os valores totais da LPU.
        """
        if column_total_paid not in df.columns or column_total_lpu not in df.columns:
            logger.error(f"Colunas '{column_total_paid}' ou '{column_total_lpu}' não encontradas no DataFrame.")
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
            return "Sem base LPU"
        if abs(pct) <= tol:
            return "OK"
        return "Para ressarcimento" if pct > 0 else "Abaixo LPU"

    def assign_status(df: pd.DataFrame) -> None:
        """
        Atribui um status de conciliação com base na discrepância e na tolerância.
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
    assign_status(df)

    return df

"""
Módulo para calcular discrepâncias entre valores pagos e valores da LPU.
"""

__author__ = "Emerson V. Rafael (emervin)"
__copyright__ = "Copyright 2026, Verificador Inteligente de Orçamentos de Obras, DataCraft"
__credits__ = ["Emerson V. Rafael"]
__license__ = "MIT"
__version__ = "1.0.0"
__maintainer__ = "Emerson V. Rafael"
__email__ = "emersonssmile@gmail.com"
__status__ = "Development"

import sys
from pathlib import Path

import numpy as np
import pandas as pd

# Adiciona o diretório src ao path
base_dir = Path(__file__).parents[5]
sys.path.insert(0, str(Path(base_dir, "src")))

from config.config_logger import logger
from config.config_dynaconf import get_settings


class LPUDiscrepancyConfig:
    """
    Classe para encapsular as configurações e parâmetros do cálculo de discrepâncias.
    """

    def __init__(
        self,
        settings=get_settings(),
        column_quantity: str = "qtde",
        column_unit_price_paid: str = "unitario_pago",
        column_unit_price_lpu: str = "unitario_lpu",
        column_total_paid: str = "valor_pago",
        column_total_lpu: str = "valor_lpu",
        column_difference: str = "dif_total",
        column_discrepancy: str = "discrepancia_percentual",
        column_status: str = "status_conciliacao",
        name_status_nullable: str = "ITEM NAO LPU",
        name_status_ok: str = "OK",
        name_status_payment_more: str = "PARA RESSARCIMENTO",
        name_status_payment_less: str = "PARA COMPLEMENTO",
        tol_percentile: float = 5.0,
        verbose: bool = True,
    ):
        self.settings = settings
        self.column_quantity = column_quantity
        self.column_unit_price_paid = column_unit_price_paid
        self.column_unit_price_lpu = column_unit_price_lpu
        self.column_total_paid = column_total_paid
        self.column_total_lpu = column_total_lpu
        self.column_difference = column_difference
        self.column_discrepancy = column_discrepancy
        self.column_status = column_status
        self.tol_percentile = tol_percentile
        self.verbose = verbose
        
        # Definição de constantes para os status
        self.status_nullable = name_status_nullable
        self.status_ok = name_status_ok
        self.status_payment_more = name_status_payment_more
        self.status_payment_less = name_status_payment_less


class LPUDiscrepancyCalculator:
    """
    Classe para calcular discrepâncias entre valores pagos e valores da LPU.
    """

    def __init__(self, config: LPUDiscrepancyConfig):
        self.config = config

    def calculate_total_item(
        self,
        df: pd.DataFrame,
        column_total_value: str,
        column_quantity: str,
        column_unit_price: str,
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

    def calculate_total_paid(self, df: pd.DataFrame) -> None:
        """
        Calcula o valor total pago com base na quantidade e no preço unitário pago.
        """
        self.calculate_total_item(
            df,
            self.config.column_total_paid,
            self.config.column_quantity,
            self.config.column_unit_price_paid,
        )

    def calculate_total_lpu(self, df: pd.DataFrame) -> None:
        """
        Calcula o valor total da LPU com base na quantidade e no preço unitário da LPU.
        """
        self.calculate_total_item(
            df,
            self.config.column_total_lpu,
            self.config.column_quantity,
            self.config.column_unit_price_lpu,
        )

    def calculate_difference(self, df: pd.DataFrame) -> None:
        """
        Calcula a diferença entre os valores totais pagos e os valores totais da LPU.
        """
        if (
            self.config.column_total_paid not in df.columns
            or self.config.column_total_lpu not in df.columns
        ):
            logger.error(
                f"Colunas '{self.config.column_total_paid}' ou '{self.config.column_total_lpu}' não encontradas no DataFrame."
            )
        else:
            if self.config.verbose:
                logger.info("Calculando diferença entre valor total pago e valor total da LPU")
            df[self.config.column_difference] = (
                df[self.config.column_total_paid] - df[self.config.column_total_lpu]
            )

    def calculate_discrepancy(self, df: pd.DataFrame) -> None:
        """
        Calcula a discrepância percentual com base na diferença e no valor total da LPU.
        """
        if self.config.tol_percentile is None:
            logger.error("Parâmetro 'tol_percentile' não fornecido.")
        else:
            if self.config.verbose:
                logger.info(
                    f"Calculando discrepâncias com tolerância de {self.config.tol_percentile}%..."
                )
            denom = df[self.config.column_total_lpu].replace({0: np.nan})  # Evita divisão por zero
            df[self.config.column_discrepancy] = (df[self.config.column_difference] / denom) * 100

    def classify_discrepancy(self, pct: float) -> str:
        """
        Classifica a discrepância com base no valor de tolerância.

        Args:
            pct (float): Discrepância percentual.

        Returns:
            str: Classificação da discrepância.
        """
        if pd.isna(pct):
            return self.config.status_nullable
        if abs(pct) <= self.config.tol_percentile:
            return self.config.status_ok
        return self.config.status_payment_more if pct > 0 else self.config.status_payment_less

    def assign_status(self, df: pd.DataFrame) -> None:
        """
        Atribui um status de conciliação com base na discrepância e na tolerância.

        # Args:
            df (pd.DataFrame): DataFrame contendo os dados.

        # Returns:
            None: Atualiza o DataFrame com a coluna de status atribuída.

        """
        if self.config.tol_percentile is not None:
            if not (0 <= self.config.tol_percentile <= 100):
                logger.error("'tol_percentile' deve estar entre 0 e 100.")
            else:
                tolerance_value = (
                    self.config.tol_percentile
                )  # A tolerância é diretamente o valor percentual
                df[self.config.column_status] = df[self.config.column_discrepancy].apply(
                    lambda pct: self.classify_discrepancy(pct)
                )

    def calculate(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Executa o cálculo completo das discrepâncias no DataFrame.

        Args:
            df (pd.DataFrame): DataFrame de entrada contendo os dados.

        Returns:
            pd.DataFrame: DataFrame atualizado com as colunas calculadas.
        """
        self.calculate_total_paid(df)
        self.calculate_total_lpu(df)
        self.calculate_difference(df)
        self.calculate_discrepancy(df)
        self.assign_status(df)
        return df


# Exemplo de uso
if __name__ == "__main__":
    config = LPUDiscrepancyConfig(tol_percentile=5.0)
    calculator = LPUDiscrepancyCalculator(config)

    # Suponha que `df` seja o DataFrame de entrada
    df = pd.DataFrame()  # Substitua pelo DataFrame real
    result = calculator.calculate(df)

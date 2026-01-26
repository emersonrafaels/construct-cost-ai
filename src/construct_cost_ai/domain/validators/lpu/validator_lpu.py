"""
Módulo de Validação LPU - Verifica discrepâncias entre orçamento e base de preços.

Este módulo realiza a conciliação entre o orçamento enviado pela construtora
e a base de dados oficial da LPU (Lista de Preços Unitários), identificando discrepâncias
nos valores com tolerância configurável.
"""

__author__ = "Emerson V. Rafael (emervin)"
__copyright__ = "Verificador Inteligente de Orçamentos de Obras"
__credits__ = ["Emerson V. Rafael", "Clarissa Simoyama"]
__license__ = "MIT"
__version__ = "1.0.0"
__maintainer__ = "Emerson V. Rafael (emervin), Clarissa Simoyama (simoyam)"
__squad__ = "DataCraft"
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
    read_data,
    export_data,
    cast_columns,
    transform_case,
    merge_data_with_columns,
    select_columns,
    rename_columns,
    filter_by_merge_column,
    remove_duplicate_columns,
)
from utils.lpu.lpu_functions import (
    generate_region_group_combinations,
    split_regiao_grupo,
    separate_regions,
    merge_budget_lpu,
)
from construct_cost_ai.domain.validators.lpu.calculate_discrepancies import (
    LPUDiscrepancyConfig,
    LPUDiscrepancyCalculator,
)
from construct_cost_ai.domain.validators.lpu.stats.generate_lpu_stats import (
    run_lpu_validation_reporting,
)
from construct_cost_ai.domain.validators.utils.calculate_price_functions import calculate_total_item
from utils.python_functions import get_item_safe
from utils.fuzzy.fuzzy_functions import process_fuzzy_comparison_dataframes


class ValidatorLPUError(Exception):
    """Exceção base para erros do validador LPU."""

    pass


class FileNotFoundError(ValidatorLPUError):
    """Exceção para arquivo não encontrado."""

    pass


class MissingColumnsError(ValidatorLPUError):
    """Exceção para colunas obrigatórias ausentes."""

    pass


class LPUFormatReport(NamedTuple):
    """
    Represents the detected format of an LPU (Unit Price List) database.

    Attributes:
        format (str): The detected format of the database, which can be "wide", "long", or "unknown".
    """

    format: str
    columns: list = []

    def __str__(self):
        return f"LPUFormatReport(format={self.format}, columns={self.columns})"


class LPUValidator:
    def __init__(self):
        # Inicializa o settings diretamente dentro da classe
        self.settings = get_settings()

    def load_budget(self, file_path, validator_output_data=False, output_dir_file=None):
        """
        Carrega o arquivo de orçamento.

        Args:
            path: Caminho para o arquivo de orçamento (Excel ou CSV)
            validator_output_data: Validador se é desejado salvar os dados após processamento (Boolean)
            output_dir_file: Arquivo que deve ser salvo, se o validator_output_data for True (str)

        Returns:
            DataFrame com o orçamento carregado

        Raises:
            FileNotFoundError: Se o arquivo não for encontrado
            MissingColumnsError: Se colunas obrigatórias estiverem ausentes
        """
        file_path = Path(file_path)

        if not file_path.exists():
            raise FileNotFoundError(f"Arquivo de orçamento não encontrado: {file_path}")

        # Colunas obrigatórias
        required_columns = self.settings.get(
            "module_validator_lpu.budget_data.required_columns_with_types", []
        )

        # Coluna valor total
        column_total_value = self.settings.get(
            "module_validator_lpu.budget_data.column_total_value", "VALOR TOTAL"
        )

        try:
            # Ler os dados de Orçamento e realizar pré processing
            df = transform_case(
                read_data(
                    file_path=file_path,
                    sheet_name=self.settings.get(
                        "module_validator_lpu.budget_data.sheet_name", "Tables"
                    ),
                ),
                columns_to_upper=True,
                cells_to_upper=True,
                cells_to_remove_spaces=self.settings.get(
                    "module_validator_lpu.budget_data.cells_to_remove_spaces", []
                ),
                cells_to_remove_accents=self.settings.get(
                    "module_validator_lpu.budget_data.cells_to_remove_accents", []
                ),
                cells_to_strip=True,
            )
        except Exception as e:
            raise ValidatorLPUError(f"Erro ao carregar orçamento: {e}")

        # Valida colunas obrigatórias
        empty_columns = set(required_columns.keys()) - set(df.columns)
        if empty_columns:
            raise MissingColumnsError(
                f"Colunas obrigatórias ausentes no orçamento: {', '.join(empty_columns)}"
            )

        # Garante tipos corretos usando cast_columns
        try:
            df = cast_columns(df, required_columns)
        except ValueError as e:
            raise ValidatorLPUError(f"Erro ao converter tipos de colunas: {e}")

        # Se total_orcado não existir, calcula
        df = calculate_total_item(
            df=df,
            column_total_value=column_total_value,
            column_quantity=self.settings.get(
                "module_validator_lpu.budget_data.column_quantity", "qtde"
            ),
            column_unit_price=self.settings.get(
                "module_validator_lpu.budget_data.column_unit_price", "unitario_orcado"
            ),
        )

        # Verificando se há colunas para renomear
        if self.settings.get("module_validator_lpu.budget_data.columns_to_rename"):
            df = rename_columns(
                df,
                rename_dict=self.settings.get("module_validator_lpu.budget_data.columns_to_rename"),
            )

        # Verificando se é desejado salvar os dados resultantes
        if validator_output_data:
            export_data(data=df, file_path=output_dir_file)

        return df

    def load_metadata(
        self,
        file_path: Union[str, Path] = None,
        validator_output_data: bool = False,
        output_dir_file: str = None,
    ) -> pd.DataFrame:
        """
        Carrega o arquivo de metadados.

        Args:
            file_path: Caminho para o arquivo de metadados (Excel ou CSV). Se não for fornecido, usa o caminho padrão.
            validator_output_data: Validador se é desejado salvar os dados após processamento (Boolean)
            output_dir_file: Arquivo que deve ser salvo, se o validator_output_data for True (str)

        Returns:
            DataFrame com a base de metadados carregada.

        Raises:
            FileNotFoundError: Se o arquivo não for encontrado.
            MissingColumnsError: Se colunas obrigatórias estiverem ausentes.
            ValueError: Se houver erro ao converter os tipos de colunas.
        """

        logger.info("Iniciando o carregamento da base de metadados")

        # Obtém o caminho e a aba do arquivo a partir das configurações
        file_path = file_path or self.settings.get(
            "module_validator_lpu.budget_metadados.file_path"
        )
        sheet_name = self.settings.get(
            "module_validator_lpu.budget_metadados.sheet_name", "Metadata"
        )

        # Colunas obrigatórias e seus tipos
        required_columns = self.settings.get(
            "module_validator_lpu.budget_metadados.required_columns_with_types", {}
        )

        file_path = Path(file_path)

        # Verifica se o arquivo existe
        if not file_path.exists():
            raise FileNotFoundError(f"Arquivo não encontrado: {file_path}")

        try:
            # Lê os dados e realiza o pré-processamento
            df = transform_case(
                read_data(file_path=file_path, sheet_name=sheet_name),
                columns_to_upper=True,
                cells_to_upper=True,
                cells_to_remove_spaces=self.settings.get(
                    "module_validator_lpu.budget_metadados.cells_to_remove_spaces", []
                ),
                cells_to_remove_accents=self.settings.get(
                    "module_validator_lpu.budget_metadados.cells_to_remove_accents", []
                ),
            )

            # Converte as colunas para os tipos corretos
            df = cast_columns(df, required_columns)
        except ValueError as e:
            logger.error(f"Erro ao converter tipos de colunas na base de metadados: {e}")
            raise

        # Verificando se é desejado salvar os dados resultantes
        if validator_output_data:
            export_data(data=df, file_path=output_dir_file)

        return df

    def identify_lpu_format(
        self,
        df: pd.DataFrame,
        *,
        expected_core_cols: Tuple[str, str, str] = ("CÓD ITEM", "ITEM", "UN"),
        long_required_cols: Tuple[str, str, str] = ("REGIAO", "GRUPO", "PRECO"),
        filter_columns_not_matching: bool = True,
    ) -> "LPUFormatReport":
        """
        Identifica se a base está no formato:
          - wide: colunas de preço por REGIAO/GRUPO (ex: 'NORTE-GRUPO1', ...)
          - long: colunas explícitas 'regiao', 'grupo', 'preco' (nomes flexíveis)
          - unknown: não dá pra inferir com confiança

        Args:
            df (pd.DataFrame): DataFrame a ser analisado.
            expected_core_cols (Tuple[str, str, str]): Colunas principais esperadas no DataFrame.
            long_required_cols (Tuple[str, str, str]): Colunas esperadas no formato long.
            filter_columns_not_matching (bool): Se True, filtra colunas que não correspondem ao padrão esperado.

        Returns:
            LPUFormatReport: Relatório contendo o formato identificado e as colunas encontradas.

        Observação:
            O argumento `col_to_regiao_grupo` pode ser enviado como `report.columns` para reutilizar as colunas detectadas.
        """
        # Colunas esperadas no formato "wide"
        regions = self.settings.get("module_validator_lpu.lpu_data.regions", [])
        groups = self.settings.get("module_validator_lpu.lpu_data.groups", [])
        expected_wide_cols = generate_region_group_combinations(
            regions, groups, combine_regions=False
        ) + generate_region_group_combinations(regions, groups, combine_regions=True)

        # Identifica colunas que seguem o padrão de região-grupo
        found_wide_cols = [col for col in df.columns if col in expected_wide_cols]

        # Verifica se todas as colunas principais estão presentes
        if any(col in df.columns for col in expected_core_cols):

            if filter_columns_not_matching:
                # Filtra colunas que não correspondem ao padrão esperado
                df = select_columns(df, target_columns=found_wide_cols)

            # Se as colunas de preço seguem o padrão esperado, é wide
            if found_wide_cols:
                return LPUFormatReport(format="wide", columns=found_wide_cols)

            # Se as colunas 'regiao', 'grupo' e 'preco' estão presentes, é long
            elif all(col in df.columns for col in long_required_cols):
                return LPUFormatReport(
                    format="long",
                    columns=self.settings.get(
                        "module_validator_lpu.lpu_data.long_format_columns", {}
                    ).keys(),
                )

        # Se chegou aqui, o formato é desconhecido
        return LPUFormatReport(format="unknown", columns=[])

    def wide_to_long(
        self,
        df_wide: pd.DataFrame,
        id_col: str = "CÓD ITEM",
        item_col: str = "ITEM",
        unit_col: str = "UN",
        keep_cols: Optional[List[str]] = None,
        col_to_regiao_grupo: List[str] = None,  # Agora espera uma lista de colunas já filtradas
        value_name: str = "preco",
    ) -> pd.DataFrame:
        """
        Converte uma base LPU no formato WIDE para LONG.

        No formato WIDE, os preços são organizados em colunas que representam combinações de regiões e grupos,
        como 'NORTE-GRUPO1', 'SUDESTE-GRUPO2', etc. No formato LONG, essas informações são transformadas em
        linhas, com colunas explícitas para 'regiao', 'grupo' e 'preco'.

        Args:
            df_wide (pd.DataFrame): DataFrame no formato WIDE.
            id_col (str): Nome da coluna que identifica o item (ex.: 'CÓD ITEM').
            item_col (str): Nome da coluna que descreve o item (ex.: 'ITEM').
            unit_col (str): Nome da coluna que indica a unidade (ex.: 'UN').
            keep_cols (Optional[List[str]]): Lista de colunas adicionais a serem mantidas no formato LONG.
            col_to_regiao_grupo (List[str]): Lista de colunas de região/grupo já filtradas no DataFrame.
            value_name (str): Nome da coluna que conterá os valores (ex.: 'preco').

        Returns:
            pd.DataFrame: DataFrame convertido para o formato LONG.

        Raises:
            ValueError: Se as colunas necessárias não forem encontradas ou se a conversão falhar.
        """

        # Definindo as regiões e grupos esperados
        regions = self.settings.get("module_validator_lpu.lpu_data.regions", [])
        groups = self.settings.get("module_validator_lpu.lpu_data.groups", [])

        # Copia o DataFrame para evitar alterações no original
        df_wide = df_wide.copy()

        # Verifica se col_to_regiao_grupo foi fornecido
        if not col_to_regiao_grupo:
            raise ValueError(
                "A lista de colunas de região/grupo (col_to_regiao_grupo) não foi fornecida."
            )

        # Separa as regiões em colunas de regiões individuais
        df_wide, col_to_regiao_grupo = separate_regions(
            df=df_wide, col_to_regiao_grupo=col_to_regiao_grupo, regions=regions
        )

        # Transforma o DataFrame para o formato LONG usando a função melt
        df_long = df_wide.melt(
            id_vars=[id_col, item_col, unit_col]
            + (keep_cols or []),  # Colunas que permanecem fixas
            value_vars=col_to_regiao_grupo,  # Colunas que serão transformadas em linhas
            var_name="REGIAO_GRUPO",  # Nome da coluna que conterá os nomes das colunas originais
            value_name=value_name,  # Nome da coluna que conterá os valores
        )

        # Divide regiao_grupo em 'regiao' e 'grupo' usando a função split_regiao_grupo
        df_long["REGIAO"], df_long["GRUPO"] = zip(
            *df_long["REGIAO_GRUPO"].apply(lambda col: split_regiao_grupo(col, regions, groups))
        )

        # Retorna o DataFrame no formato LONG
        return df_wide, df_long

    def long_to_wide(
        self,
        df_long: pd.DataFrame,
        *,
        id_col: str = "cod_item",
        item_col: str = "item",
        unit_col: str = "unidade",
        regiao_col: str = "regiao",
        grupo_col: str = "grupo",
        value_col: str = "preco",
        wide_col_formatter: Optional[callable] = None,
        aggfunc: str = "first",
    ) -> pd.DataFrame:
        """
        Converte LPU LONG -> WIDE.
        """
        # Cria coluna única para região-grupo se não existir
        if regiao_col in df_long.columns and grupo_col in df_long.columns:
            df_long["regiao_grupo"] = df_long[regiao_col] + "-" + df_long[grupo_col]
        else:
            df_long["regiao_grupo"] = df_long.get(regiao_col, df_long.get(grupo_col))

        # Agrega dados se necessário
        df_agg = (
            df_long.groupby([id_col, item_col, unit_col, "regiao_grupo"])
            .agg({value_col: aggfunc})
            .reset_index()
        )

        # Transforma para formato largo
        df_wide = df_agg.pivot_table(
            index=[id_col, item_col, unit_col],
            columns="regiao_grupo",
            values=value_col,
            aggfunc=aggfunc,
        ).reset_index()

        # Formata colunas largas se função fornecida
        if wide_col_formatter:
            df_wide.columns = [
                wide_col_formatter(col) if col not in [id_col, item_col, unit_col] else col
                for col in df_wide.columns
            ]

        return df_wide

    def convert_lpu(
        self,
        df: pd.DataFrame,
        target: Literal["wide", "long"],
        *,
        detect: bool = True,
        **kwargs,
    ) -> pd.DataFrame:
        """
        Converte a LPU para o formato desejado.
        """
        if detect:
            report = self.identify_lpu_format(df)
            if report.format == "wide" and target == "long":
                df_wide, df_long = self.wide_to_long(
                    df, col_to_regiao_grupo=report.columns, **kwargs
                )
            elif report.format == "long" and target == "wide":
                df_wide, df_long = self.long_to_wide(df, **kwargs)
            else:
                raise ValidatorLPUError(
                    f"Conversão de {report.format} para {target} não suportada ou formato desconhecido."
                )
        else:
            if target == "long":
                df_wide, df_long = self.wide_to_long(df, **kwargs)
            elif target == "wide":
                df_wide, df_long = self.long_to_wide(df, **kwargs)
            else:
                raise ValidatorLPUError(f"Formato alvo desconhecido: {target}")

        return df

    def load_lpu(
        self,
        file_path: Union[str, Path],
        validator_output_data: bool = False,
        output_dir_file: str = None,
    ) -> pd.DataFrame:
        """
        Carrega o arquivo base da LPU.

        Args:
            file_path: Caminho para o arquivo da LPU
            validator_output_data: Validador se é desejado salvar os dados após processamento (Boolean)
            output_dir_file: Arquivo que deve ser salvo, se o validator_output_data for True (str)

        Returns:
            DataFrame com a base da LPU carregada

        Raises:
            FileNotFoundError: Se o arquivo não for encontrado
            MissingColumnsError: Se colunas obrigatórias estiverem ausentes
        """

        logger.info("Iniciando o carregamento da base LPU")

        file_path = Path(file_path)

        if not file_path.exists():
            raise FileNotFoundError(f"Arquivo LPU não encontrado: {file_path}")

        # Colunas obrigatórias
        required_columns = self.settings.get(
            "module_validator_lpu.lpu_data.required_columns_with_types",
            {"CÓD ITEM": "object", "ITEM": "object", "UNID.": "object"},
        )

        try:
            # Ler os dados de LPU e realizar pré processing
            df = transform_case(
                read_data(
                    file_path=file_path,
                    sheet_name=self.settings.get("module_validator_lpu.lpu_data.sheet_name", "LPU"),
                ),
                columns_to_upper=True,
                cells_to_upper=True,
                cells_to_remove_spaces=self.settings.get(
                    "module_validator_lpu.lpu_data.cells_to_remove_spaces", []
                ),
                cells_to_remove_accents=self.settings.get(
                    "module_validator_lpu.lpu_data.cells_to_remove_accents", []
                ),
                cells_to_strip=True,
            )
        except Exception as e:
            raise ValidatorLPUError(f"Erro ao carregar base LPU: {e}")

        # Valida colunas obrigatórias na base de LPU
        missing_columns = set(required_columns) - set(df.columns)
        if missing_columns:
            raise MissingColumnsError(
                f"Colunas obrigatórias ausentes na LPU: {', '.join(missing_columns)}"
            )

        # Detecta formato e converte se necessário
        report = self.identify_lpu_format(df)

        if report.format == "wide":
            df_wide, df_long = self.wide_to_long(
                df,
                id_col=get_item_safe(required_columns, 0, return_key=True),
                item_col=get_item_safe(required_columns, 1, return_key=True),
                unit_col=get_item_safe(required_columns, 2, return_key=True),
                col_to_regiao_grupo=report.columns,
            )
            logger.info("Convertido LPU de WIDE para LONG.")
        elif report.format == "long":
            # df = long_to_wide(df)
            logger.info("Mantido LPU no formato LONG.")
        else:
            raise ValidatorLPUError(f"Formato desconhecido: {report.format}")

        try:
            # Adiciona as colunas detectadas ao required_columns
            required_columns.update({column: float for column in report.columns})

            # Converter as colunas do dataframe para os tipos corretos
            df_wide = cast_columns(df_wide, required_columns)
        except ValueError as e:
            raise ValidatorLPUError(f"Erro ao converter tipos de colunas: {e}")

        # Realizando as transformações finais dos dataframes
        df_wide = transform_case(df=df_wide, columns_to_upper=True)
        df_long = transform_case(df=df_long, columns_to_upper=True)

        # Verificando se há colunas para renomear
        if self.settings.get("module_validator_lpu.lpu_data.columns_to_rename"):
            df_long = rename_columns(
                df_long,
                rename_dict=self.settings.get("module_validator_lpu.lpu_data.columns_to_rename"),
            )

        # Verificando se é desejado salvar os dados resultantes
        if validator_output_data:
            export_data(data=df, file_path=output_dir_file)

        return df_wide, df_long

    def load_agencies(
        self,
        file_path: Union[str, Path],
        validator_output_data: bool = False,
        output_dir_file: str = None,
    ) -> pd.DataFrame:
        """
        Carrega o arquivo de agências.

        Args:
            file_path: Caminho para o arquivo de agências (Excel ou CSV).
            validator_output_data: Validador se é desejado salvar os dados após processamento (Boolean)
            output_dir_file: Arquivo que deve ser salvo, se o validator_output_data for True (str)

        Returns:
            DataFrame com a base de agências carregada.

        Raises:
            FileNotFoundError: Se o arquivo não for encontrado.
            MissingColumnsError: Se colunas obrigatórias estiverem ausentes.
        """

        logger.info("Iniciando o carregamento da base de agências")

        file_path = Path(file_path)

        if not file_path.exists():
            raise FileNotFoundError(f"Arquivo não encontrado: {file_path}")

        # Colunas obrigatórias
        required_columns = self.settings.get(
            "module_validator_lpu.agencies_data.required_columns_with_types", []
        )

        try:
            # Ler os dados de Agências e realizar pré processing
            df = transform_case(
                read_data(
                    file_path=file_path,
                    sheet_name=self.settings.get(
                        "module_validator_lpu.agencies_data.sheet_name", "Sheet1"
                    ),
                    header=self.settings.get("module_validator_lpu.agencies_data.header", 1),
                ),
                columns_to_upper=True,
                cells_to_upper=True,
                cells_to_remove_spaces=self.settings.get(
                    "module_validator_lpu.agencies_data.cells_to_remove_spaces", []
                ),
                cells_to_remove_accents=self.settings.get(
                    "module_validator_lpu.agencies_data.cells_to_remove_accents", []
                ),
            )
        except Exception as e:
            logger.error(f"Erro ao carregar o arquivo de agências: {e}")
            raise

        # Valida colunas obrigatórias
        missing_columns = set(required_columns.keys()) - set(df.columns)
        if missing_columns:
            raise MissingColumnsError(
                f"Colunas obrigatórias ausentes na base de agências: {missing_columns}"
            )

        # Garante tipos corretos usando cast_columns
        try:
            df = cast_columns(df, required_columns)
        except ValueError as e:
            logger.error(f"Erro ao converter tipos de colunas na base de agências: {e}")
            raise

        # Verificando se é desejado salvar os dados resultantes
        if validator_output_data:
            export_data(data=df, file_path=output_dir_file)

        return df

    def load_constructors(
        self,
        file_path: Union[str, Path],
        validator_output_data: bool = False,
        output_dir_file: str = None,
    ) -> pd.DataFrame:
        """
        Carrega o arquivo de construtoras.

        Args:
            file_path: Caminho para o arquivo de construtoras (Excel ou CSV).
            validator_output_data: Validador se é desejado salvar os dados após processamento (Boolean)
            output_dir_file: Arquivo que deve ser salvo, se o validator_output_data for True (str)

        Returns:
            DataFrame com a base de construtoras carregada.

        Raises:
            FileNotFoundError: Se o arquivo não for encontrado.
            MissingColumnsError: Se colunas obrigatórias estiverem ausentes.
        """

        logger.info("Iniciando o carregamento da base de construtoras")

        file_path = Path(file_path)

        if not file_path.exists():
            raise FileNotFoundError(f"Arquivo não encontrado: {file_path}")

        # Colunas obrigatórias
        required_columns = self.settings.get(
            "module_validator_lpu.constructors_data.required_columns_with_types", []
        )

        try:
            # Ler os dados de Fornecedores/Construtoras e realizar pré processing
            df = transform_case(
                read_data(
                    file_path=file_path,
                    sheet_name=self.settings.get(
                        "module_validator_lpu.constructors_data.sheet_name", "Sheet1"
                    ),
                ),
                columns_to_upper=True,
                cells_to_upper=True,
                columns_to_remove_accents=self.settings.get(
                    "module_validator_lpu.constructors_data.columns_to_remove_accents", []
                ),
                cells_to_remove_spaces=self.settings.get(
                    "module_validator_lpu.constructors_data.cells_to_remove_spaces", []
                ),
                cells_to_remove_accents=self.settings.get(
                    "module_validator_lpu.constructors_data.cells_to_remove_accents", []
                ),
            )
        except Exception as e:
            logger.error(f"Erro ao carregar o arquivo de construtoras: {e}")
            raise

        # Valida colunas obrigatórias
        missing_columns = set(required_columns.keys()) - set(df.columns)
        if missing_columns:
            raise MissingColumnsError(
                f"Colunas obrigatórias ausentes na base de construtoras: {missing_columns}"
            )

        # Garante tipos corretos usando cast_columns
        try:
            df = cast_columns(df, required_columns)
        except ValueError as e:
            logger.error(f"Erro ao converter tipos de colunas na base de construtoras: {e}")
            raise

        # Verificando se é desejado salvar os dados resultantes
        if validator_output_data:
            export_data(data=df, file_path=output_dir_file)

        return df

    def get_default_settings(self, key):
        """
        Retorna os valores padrão das configurações do validador LPU.

        Returns:
            Dicionário com configurações padrão
        """
        return {
            "default_budget_path": self.settings.validador_lpu.caminho_padrao_orcamento,
            "default_lpu_path": self.settings.validador_lpu.caminho_padrao_lpu,
            "output_dir": self.settings.validador_lpu.output_dir,
            "tolerance_percentual": self.settings.validador_lpu.tolerancia_percentual,
            "basic_excel_file": self.settings.validador_lpu.arquivo_excel_basico,
            "complete_excel_file": self.settings.validador_lpu.arquivo_excel_completo,
            "csv_file": self.settings.validador_lpu.arquivo_csv,
            "html_file": self.settings.validador_lpu.arquivo_html,
            "top_n_divergences": self.settings.validador_lpu.top_n_divergencias,
            "top_n_divergences_extended": self.settings.validador_lpu.top_n_divergencias_extended,
        }

    def validate_and_merge(
        df_left: pd.DataFrame,
        df_right: pd.DataFrame,
        left_on: List[str],
        right_on: List[str],
        how: str = "left",
        log_message: str = "",
    ) -> Tuple[pd.DataFrame, int, int]:
        """
        Função genérica para validar tipos, realizar merge e contar os resultados.

        Args:
            df_left (pd.DataFrame): DataFrame à esquerda.
            df_right (pd.DataFrame): DataFrame à direita.
            left_on (List[str]): Colunas do DataFrame à esquerda para o merge.
            right_on (List[str]): Colunas do DataFrame à direita para o merge.
            how (str): Tipo de merge (ex.: 'left', 'inner').
            log_message (str): Mensagem de log para identificar o merge.

        Returns:
            Tuple[pd.DataFrame, int, int]:
                - DataFrame resultante do merge.
                - Quantidade de itens que deram match.
                - Quantidade total de itens no DataFrame à esquerda.
        """
        # Valida se os tipos das colunas são compatíveis
        for col_left, col_right in zip(left_on, right_on):
            if df_left[col_left].dtype != df_right[col_right].dtype:
                logger.warning(
                    f"⚠️ Tipos diferentes nas colunas: {col_left} ({df_left[col_left].dtype}) e {col_right} ({df_right[col_right].dtype})."
                )

        # Realiza o merge
        merged_df = pd.merge(
            df_left,
            df_right,
            left_on=left_on,
            right_on=right_on,
            how=how,
            suffixes=("_orc", "_lpu"),
            indicator=True,
        )

        # Conta os itens que deram match
        matched_count = merged_df[merged_df["_merge"] == "both"].shape[0]
        total_count = df_left.shape[0]

        # Loga a informação do merge
        logger.info(
            f"{log_message} - {matched_count} dados de {total_count} ({round((matched_count / total_count) * 100, 2) if total_count > 0 else 0}%)"
        )

        return merged_df, matched_count, total_count

    def generate_format_result(
        self,
        df: pd.DataFrame,
        list_select_columns: list = None,
        dict_rename_columns: dict = None,
        vaLidator_remove_duplicate_columns: bool = False,
    ) -> pd.DataFrame:
        """
        Cria o DataFrame de resultado formatado para exportação.

        Args:
            df (pd.DataFrame): DataFrame com os resultados completos da validação.
            list_select_columns (list): Lista de colunas a serem selecionadas.
            dict_rename_columns (dict): Dicionário para renomear colunas.
            vaLidator_remove_duplicate_columns (bool): Se True, remove colunas duplicadas.

        Returns:
            pd.DataFrame: DataFrame formatado para exportação.
        """

        if list_select_columns:
            df_result = select_columns(df=df, target_columns=list_select_columns)

        if dict_rename_columns:
            df_result = rename_columns(df=df_result, rename_dict=dict_rename_columns)

        if vaLidator_remove_duplicate_columns:
            df_result = remove_duplicate_columns(df=df_result)

        return df_result

    def validate_lpu(
        self,
        file_path_budget: Union[str, Path] = None,
        file_path_metadata: Union[str, Path] = None,
        file_path_lpu: Union[str, Path] = None,
        file_path_agencies: Union[str, Path] = None,
        file_path_constructors: Union[str, Path] = None,
        base_dir: Union[str, Path] = None,
        output_dir: Union[str, Path] = None,
        output_file: str = "02_BASE_RESULTADO_VALIDADOR_LPU.xlsx",
        verbose: bool = True,
    ) -> pd.DataFrame:
        """
        Função orquestradora para validação LPU.

        Realiza todo o fluxo de validação:
        1. Carrega orçamento, LPU, agências e construtoras.
        2. Cruza os dados (INNER JOIN em cod_item + unidade).
        3. Calcula discrepâncias com tolerância configurável.
        4. Classifica itens (OK, Para ressarcimento, Abaixo LPU).
        5. Salva resultados em formatos Excel, CSV e HTML.

        Args:
            file_path_budget: Caminho para o arquivo de orçamento (padrão nas configurações).
            file_path_metadata: Caminho para o arquivo de metadados (padrão nas configurações).
            file_path_lpu: Caminho para o arquivo da LPU (padrão nas configurações).
            file_path_agencies: Caminho para o arquivo de agências (padrão nas configurações).
            file_path_constructors: Caminho para o arquivo de construtoras (padrão nas configurações).
            base_dir: Diretório raiz do projeto (padrão nas configurações).
            output_dir: Diretório para salvar resultados (padrão nas configurações).
            output_file_name: Nome base para os arquivos de saída (sem extensão).
            verbose: Se True, exibe estatísticas no console.

        Returns:
            DataFrame com os resultados completos da validação.

        Raises:
            ValidatorLPUError: Em caso de erro na validação.
        """

        if verbose:
            print("-" * 50)
            logger.info("VALIDADOR LPU - Conciliação Orçamento vs Base de Preços")
            logger.info(
                f"Tolerância configurada: {self.settings.get('module_validator_lpu.tol_percentile')}%"
            )
            print("-" * 50)

        # 1. Carrega dados
        if verbose:
            logger.info("📂 Carregando arquivos...")

        try:
            logger.info(f"Carregando orçamento de: {file_path_budget}")
            df_budget = self.load_budget(
                file_path_budget,
                validator_output_data=self.settings.get(
                    "module_validator_lpu.budget_data.validator_save_sot", True
                ),
                output_dir_file=Path(
                    base_dir,
                    self.settings.get("module_validator_lpu.budget_data.dir_path_file_sot"),
                ),
            )
            if verbose:
                logger.info(f"✅ Orçamento carregado: {len(df_budget)} itens")
        except Exception as e:
            logger.error(f"Erro ao carregar orçamento: {e}")
            raise ValidatorLPUError(f"Erro ao carregar orçamento: {e}")

        try:
            logger.info(f"Carregando metadados de orçamentos de: {file_path_metadata}")
            df_budget_metadata = select_columns(
                self.load_metadata(
                    file_path_metadata,
                    validator_output_data=self.settings.get(
                        "module_validator_lpu.budget_metadados.validator_save_sot", True
                    ),
                    output_dir_file=Path(
                        base_dir,
                        self.settings.get(
                            "module_validator_lpu.budget_metadados.dir_path_file_sot"
                        ),
                    ),
                ),
                target_columns=self.settings.get(
                    "module_validator_lpu.budget_metadados.list_columns_select", []
                ),
                keep_dataframe_original_target_columns_empty=True,
            )
            if verbose:
                logger.info(
                    f"✅ Metadados dos orçamentos carregado: {len(df_budget_metadata)} itens"
                )
        except Exception as e:
            logger.error(f"Erro ao carregar metadados dos orçamentos: {e}")
            raise ValidatorLPUError(f"Erro ao carregar metadados dos orçamentos: {e}")

        try:
            logger.info(f"Carregando LPU de: {file_path_lpu}")
            df_lpu_wide, df_lpu_long = self.load_lpu(
                file_path_lpu,
                validator_output_data=self.settings.get(
                    "module_validator_lpu.lpu_data.validator_save_sot", True
                ),
                output_dir_file=Path(
                    base_dir, self.settings.get("module_validator_lpu.lpu_data.dir_path_file_sot")
                ),
            )
            if verbose:
                logger.info(f"✅ LPU carregada: {len(df_lpu_long)} itens")
        except Exception as e:
            logger.error(f"Erro ao carregar LPU: {e}")
            raise ValidatorLPUError(f"Erro ao carregar LPU: {e}")

        try:
            logger.info(f"Carregando agências de: {file_path_agencies}")
            df_agencies = select_columns(
                self.load_agencies(
                    file_path_agencies,
                    validator_output_data=self.settings.get(
                        "module_validator_lpu.agencies_data.validator_save_sot", True
                    ),
                    output_dir_file=Path(
                        base_dir,
                        self.settings.get("module_validator_lpu.agencies_data.dir_path_file_sot"),
                    ),
                ),
                target_columns=self.settings.get(
                    "module_validator_lpu.agencies_data.list_columns_select", []
                ),
                keep_dataframe_original_target_columns_empty=True,
            )
            if verbose:
                logger.info(f"✅ Agências carregadas: {len(df_agencies)} itens")
        except Exception as e:
            logger.error(f"Erro ao carregar agências: {e}")
            raise ValidatorLPUError(f"Erro ao carregar agências: {e}")

        try:
            logger.info(f"Carregando construtoras de: {file_path_constructors}")
            df_constructors = select_columns(
                self.load_constructors(
                    file_path_constructors,
                    validator_output_data=self.settings.get(
                        "module_validator_lpu.constructors_data.validator_save_sot", True
                    ),
                    output_dir_file=Path(
                        base_dir,
                        self.settings.get(
                            "module_validator_lpu.constructors_data.dir_path_file_sot"
                        ),
                    ),
                ),
                target_columns=self.settings.get(
                    "module_validator_lpu.constructors_data.list_columns_select", []
                ),
                keep_dataframe_original_target_columns_empty=True,
            )
            if verbose:
                logger.info(f"✅ Construtoras carregadas: {len(df_constructors)} itens")
        except Exception as e:
            logger.error(f"Erro ao carregar construtoras: {e}")
            raise ValidatorLPUError(f"Erro ao carregar construtoras: {e}")

        try:
            # Realiza o merge entre budget e metadados
            logger.info(f"🔗 Cruzando orçamento com Metadados")

            indicator = self.settings.get(
                "module_validator_lpu.merge_budget_metadata.indicator", "_merge_bud_met"
            )

            df_merge_budget_metadata = merge_data_with_columns(
                df_left=df_budget,
                df_right=df_budget_metadata,
                left_on=self.settings.get("module_validator_lpu.merge_budget_metadata.left_on"),
                right_on=self.settings.get("module_validator_lpu.merge_budget_metadata.right_on"),
                how=self.settings.get("module_validator_lpu.merge_budget_metadata.how", "left"),
                suffixes=("_orc", "_meta"),
                validate=self.settings.get(
                    "module_validator_lpu.merge_budget_metadata.validate", "many_to_one"
                ),
                indicator=indicator,
                validator_output_data=self.settings.get(
                    "module_validator_lpu.merge_budget_metadata.validator_save_sot", True
                ),
                output_dir_file=Path(
                    base_dir,
                    self.settings.get(
                        "module_validator_lpu.merge_budget_metadata.dir_path_file_sot"
                    ),
                ),
            )

            if verbose:

                logger.info(
                    f"✅ Itens cruzados: {filter_by_merge_column(df=df_merge_budget_metadata, merge_column=indicator)}"
                )
                logger.info(f"✅ Qtd de linhas e colunas: {df_merge_budget_metadata.shape}")

        except Exception as e:
            logger.error(f"Erro ao cruzar dados: {e}")
            raise ValidatorLPUError(f"Erro ao cruzar dados: {e}")

        try:
            # Realiza o merge entre budget/metadados e agencias
            logger.info(f"🔗 Cruzando orçamento com Agências")

            indicator = self.settings.get(
                "module_validator_lpu.merge_budget_metadata_agencies.indicator",
                "_merge_bud_met_age",
            )

            df_merge_budget_metadata_agencias = merge_data_with_columns(
                df_left=df_merge_budget_metadata,
                df_right=df_agencies,
                left_on=self.settings.get(
                    "module_validator_lpu.merge_budget_metadata_agencies.left_on"
                ),
                right_on=self.settings.get(
                    "module_validator_lpu.merge_budget_metadata_agencies.right_on"
                ),
                how=self.settings.get(
                    "module_validator_lpu.merge_budget_metadata_agencies.how", "left"
                ),
                suffixes=("_meta", "_age"),
                validate=self.settings.get(
                    "module_validator_lpu.merge_budget_metadata_agencies.validate", "many_to_one"
                ),
                indicator=indicator,
                handle_duplicates=True,
                validator_output_data=self.settings.get(
                    "module_validator_lpu.merge_budget_metadata_agencies.validator_save_sot", True
                ),
                output_dir_file=Path(
                    base_dir,
                    self.settings.get(
                        "module_validator_lpu.merge_budget_metadata_agencies.dir_path_file_sot"
                    ),
                ),
            )

            if verbose:

                logger.info(
                    f"✅ Itens cruzados: {filter_by_merge_column(df=df_merge_budget_metadata_agencias, merge_column=indicator)}"
                )

                logger.info(
                    f"✅ Qtd de linhas e colunas: {df_merge_budget_metadata_agencias.shape}"
                )

        except Exception as e:
            logger.error(f"Erro ao cruzar dados: {e}")
            raise ValidatorLPUError(f"Erro ao cruzar dados: {e}")

        try:
            # Realiza o merge entre budget/metadados/construtoras e agencias
            logger.info(f"🔗 Cruzando orçamento com Construtoras")

            indicator = self.settings.get(
                "module_validator_lpu.merge_budget_metadata_agencies_constructors.indicator",
                "_merge_bud_met_age_constr",
            )

            validator_use_merge_fuzzy_agencies_constructors = self.settings.get(
                "module_validator_lpu.merge_budget_metadata_agencies_constructors.validator_use_merge_fuzzy"
            )

            if validator_use_merge_fuzzy_agencies_constructors:

                # Aplicando match fuzzy
                df_merge_budget_metadata_agencias = process_fuzzy_comparison_dataframes(
                    df=df_merge_budget_metadata_agencias,
                    df_choices=df_constructors,
                    df_column=self.settings.get(
                        "module_validator_lpu.merge_budget_metadata_agencies_constructors.validator_use_merge_fuzzy_column_left"
                    ),
                    df_choices_column=self.settings.get(
                        "module_validator_lpu.merge_budget_metadata_agencies_constructors.validator_use_merge_fuzzy_column_right"
                    ),
                    threshold=70,
                    replace_column=True,
                    drop_columns_result=True,
                )

            df_merge_budget_metadata_agencies_constructors = merge_data_with_columns(
                df_left=df_merge_budget_metadata_agencias,
                df_right=df_constructors,
                left_on=self.settings.get(
                    "module_validator_lpu.merge_budget_metadata_agencies_constructors.left_on"
                ),
                right_on=self.settings.get(
                    "module_validator_lpu.merge_budget_metadata_agencies_constructors.right_on"
                ),
                how=self.settings.get(
                    "module_validator_lpu.merge_budget_metadata_agencies_constructors.how", "left"
                ),
                suffixes=("_age", "_constr"),
                validate=self.settings.get(
                    "module_validator_lpu.merge_budget_metadata_agencies_constructors.validate",
                    "many_to_one",
                ),
                indicator=indicator,
                handle_duplicates=True,
                use_similarity_for_unmatched=False,
                similarity_threshold=70,
                validator_output_data=self.settings.get(
                    "module_validator_lpu.merge_budget_metadata_agencies_constructors.validator_save_sot",
                    True,
                ),
                output_dir_file=Path(
                    base_dir,
                    self.settings.get(
                        "module_validator_lpu.merge_budget_metadata_agencies_constructors.dir_path_file_sot"
                    ),
                ),
            )

            if verbose:

                logger.info(
                    f"✅ Itens cruzados: {filter_by_merge_column(df=df_merge_budget_metadata_agencies_constructors, merge_column=indicator)}"
                )

                logger.info(
                    f"✅ Qtd de linhas e colunas: {df_merge_budget_metadata_agencies_constructors.shape}"
                )

        except Exception as e:
            logger.error(f"Erro ao cruzar dados: {e}")
            raise ValidatorLPUError(f"Erro ao cruzar dados: {e}")

        try:
            # Realiza o merge entre budget/metadados/construtoras/agencias e LPU
            logger.info(f"🔗 Cruzando orçamento com LPU")
            df_merge_budget_metadata_agencias_constructors_lpu, len_merged = merge_budget_lpu(
                df_budget=df_merge_budget_metadata_agencies_constructors,
                df_lpu=df_lpu_long,
                columns_on_budget=[
                    self.settings.get(
                        "module_validator_lpu.merge_budget_lpu.columns_budget_merge_one"
                    ),
                    self.settings.get(
                        "module_validator_lpu.merge_budget_lpu.columns_budget_merge_two"
                    ),
                ],
                columns_on_lpu=[
                    self.settings.get(
                        "module_validator_lpu.merge_budget_lpu.columns_lpu_merge_one"
                    ),
                    self.settings.get(
                        "module_validator_lpu.merge_budget_lpu.columns_lpu_merge_two"
                    ),
                ],
                how=self.settings.get("module_validator_lpu.merge_budget_lpu.how", "left"),
                validate=self.settings.get(
                    "module_validator_lpu.merge_budget_lpu.validate", "many_to_one"
                ),
                use_two_stage_merge=True,
                validator_output_data=self.settings.get(
                    "module_validator_lpu.merge_budget_lpu.validator_save_sot",
                    True,
                ),
                output_dir_file=Path(
                    base_dir,
                    self.settings.get("module_validator_lpu.merge_budget_lpu.dir_path_file_sot"),
                ),
            )

            if verbose:
                logger.info(f"✅ Itens cruzados com a LPU: {len_merged}")

        except Exception as e:
            logger.error(f"Erro ao cruzar dados: {e}")
            raise ValidatorLPUError(f"Erro ao cruzar dados: {e}")

        # 3. Calcula discrepâncias
        try:
            discrepancy_config = LPUDiscrepancyConfig(
                settings=self.settings,
                column_quantity=self.settings.get("module_validator_lpu.column_quantity"),
                column_unit_price_paid=self.settings.get(
                    "module_validator_lpu.column_unit_price_paid"
                ),
                column_unit_price_lpu=self.settings.get(
                    "module_validator_lpu.column_unit_price_lpu"
                ),
                column_total_paid=self.settings.get("module_validator_lpu.column_total_paid"),
                column_total_lpu=self.settings.get("module_validator_lpu.column_total_lpu"),
                column_difference=self.settings.get("module_validator_lpu.column_difference"),
                column_discrepancy=self.settings.get("module_validator_lpu.column_discrepancy"),
                column_status=self.settings.get("module_validator_lpu.column_status"),
                tol_percentile=self.settings.get("module_validator_lpu.tol_percentile"),
                verbose=verbose,
            )

            discrepancy_calculator = LPUDiscrepancyCalculator(config=discrepancy_config)

            df_result = discrepancy_calculator.calculate(
                df=df_merge_budget_metadata_agencias_constructors_lpu
            )
        except Exception as e:
            logger.error(f"Erro ao calcular discrepâncias: {e}")
            raise ValidatorLPUError(f"Erro ao calcular discrepâncias: {e}")

        # Formatando o resultado final
        df_result = self.generate_format_result(
            df=df_result,
            list_select_columns=self.settings.get(
                "module_validator_lpu.output_settings.list_columns_result", []
            ),
            dict_rename_columns=self.settings.get(
                "module_validator_lpu.output_settings.dict_rename_result", []
            ),
            vaLidator_remove_duplicate_columns=True,
        )

        # Salvar o resultado em um arquivo Excel
        export_data(
            data=df_result,
            file_path=Path(output_dir, output_file),
            index=False,
        )

        logger.success(f"Resultado salvo em: {output_file}")

        # Estatísticas
        if self.settings.get("module_validator_lpu.get_lpu_status", False):

            # Definindo o local de salvamento do PDF de estatísticas
            output_pdf = Path(
                output_dir,
                self.settings.get(
                    "module_validator_lpu.output_settings.file_path_stats_output_pdf"
                ),
            )

            # Executando o PDF de estatísticas
            run_lpu_validation_reporting(
                df_result=df_result,
                validator_output_pdf=self.settings.get(
                    "module_validator_lpu.stats.validator_output_pdf", True
                ),
                output_pdf=output_pdf,
                verbose=verbose,
            )

        return df_result

    def orchestrate_validate_lpu(
        self,
        file_path_budget: Union[str, Path] = None,
        file_path_metadata: Union[str, Path] = None,
        file_path_lpu: Union[str, Path] = None,
        file_path_agencies: Union[str, Path] = None,
        file_path_constructors: Union[str, Path] = None,
        output_dir: Union[str, Path] = None,
        output_file: str = None,
        verbose: bool = True,
    ) -> int:
        """
        Função principal para execução direta do módulo ou chamada externa.

        Args:
            file_path_budget: Caminho para o arquivo de orçamento (padrão nas configurações se None).
            file_path_metadata: Caminho para o arquivo de metadados dos orçamentos (padrão nas configurações se None).
            file_path_lpu: Caminho para o arquivo da LPU (padrão nas configurações se None).
            file_path_agencies: Caminho para o arquivo de agências (padrão nas configurações se None).
            file_path_constructors: Caminho para o arquivo de construtoras (padrão nas configurações se None).
            output_dir: Diretório para salvar resultados (padrão nas configurações se None).
            output_file: Nome base para os arquivos de saída (padrão nas configurações se None).
            verbose: Se True, exibe estatísticas no console.

        Returns:
            int: Código de status (0 para sucesso, 1 para erro).
        """
        # Configura caminhos padrão se não fornecidos
        base_dir = Path(__file__).parents[5]

        # Define os caminhos dos arquivos com base nas configurações ou argumentos fornecidos
        # Arquivo de orçamento
        path_file_budget = Path(
            base_dir,
            file_path_budget or self.settings.get("module_validator_lpu.budget_data.file_path"),
        )

        # Arquivo de metadados
        path_file_metadata = Path(
            base_dir,
            file_path_metadata
            or self.settings.get("module_validator_lpu.budget_metadados.file_path"),
        )

        # Arquivo da LPU
        path_file_lpu = Path(
            base_dir, file_path_lpu or self.settings.get("module_validator_lpu.lpu_data.file_path")
        )

        # Arquivo de com as informações das agências
        path_file_agencies = Path(
            base_dir,
            file_path_agencies or self.settings.get("module_validator_lpu.agencies_data.file_path"),
        )

        # Arquivo com as informações das construtoras
        path_file_constructors = Path(
            base_dir,
            file_path_constructors
            or self.settings.get("module_validator_lpu.constructors_data.file_path"),
        )

        # Diretório de outputs dos resultados
        output_dir = Path(
            base_dir,
            output_dir or self.settings.get("module_validator_lpu.output_settings.output_dir"),
        )

        # Nome do arquivo de output
        output_file = output_file or self.settings.get(
            "module_validator_lpu.output_settings.file_path_output"
        )

        logger.debug(f"Orçamento: {path_file_budget}")
        logger.debug(f"LPU: {path_file_lpu}")
        logger.debug(f"Agências: {path_file_agencies}")
        logger.debug(f"Construtoras: {path_file_constructors}")
        logger.debug(f"Saída: {output_dir}")

        try:
            df_result = self.validate_lpu(
                file_path_budget=path_file_budget,
                file_path_metadata=path_file_metadata,
                file_path_lpu=path_file_lpu,
                file_path_agencies=path_file_agencies,
                file_path_constructors=path_file_constructors,
                base_dir=base_dir,
                output_dir=output_dir,
                output_file=output_file,
                verbose=verbose,
            )

            logger.success("Verificador Inteligente executado com sucesso - Modulo LPU")
            return df_result

        except ValidatorLPUError as e:
            logger.error(f"ERRO: {e}")
            return 1
        except Exception as e:
            logger.error(f"ERRO INESPERADO: {e}")
            return 1


if __name__ == "__main__":
    validator = LPUValidator()
    sys.exit(validator.orchestrate_validate_lpu())

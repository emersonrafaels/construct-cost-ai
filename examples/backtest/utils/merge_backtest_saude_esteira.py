"""
Este módulo contém funções para processar e mesclar dados de diferentes fontes relacionadas às esteiras de saúde.

Funções:
    read_data_saude_esteira: Lê e processa os dados da fonte de esteiras de saúde.
    read_data_lista_upes_documents: Lê e processa os dados da fonte de documentos UPE.
    merge_backtest_saude_esteira: Mescla e enriquece o DataFrame de entrada com dados das esteiras de saúde e documentos UPE.
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

# Adiciona o diretório src ao path
base_dir = Path(__file__).parents[3]
sys.path.insert(0, str(Path(base_dir, "src")))

from src.utils.data.data_functions import (
    read_data,
    transform_case,
    select_columns,
    filter_dataframe_dict_values,
    cast_columns,
)


def read_data_saude_esteira():
    """
    Lê e processa os dados da fonte de esteiras de saúde.

    Retorna:
        pd.DataFrame: DataFrame processado contendo os dados das esteiras de saúde.
    """

    # Diretório onde estão os dados de saúde das esteiras
    dir_data = Path(base_dir, "data/inputs/saude_esteira/BASE_SAUDE_DA_ESTEIRA.xlsx")
    sheetname = "Sheet1"
    engine = "calamine"
    list_select_columns = ["cod_upe", "ag", "pmo_dono", "sub_etapa", "fornecedor"]
    filter_dict_values = {"SUB_ETAPA": "ORÇAMENTO - CONSTRUÇÃO E OBRAS"}
    required_columns_with_types = {
        "COD_UPE": "int",
        "AG": "int",
        "PMO_DONO": "object",
        "SUB_ETAPA": "object",
        "FORNECEDOR": "object",
    }

    # Lendo os dados da base de saúde das esteiras
    df = transform_case(
        select_columns(
            read_data(file_path=dir_data, sheet_name=sheetname, engine=engine),
            target_columns=list_select_columns,
        ),
        columns_to_upper=True,
        cells_to_upper=True,
    )

    # Realizando o cast columns
    df = cast_columns(df=df, column_types=required_columns_with_types)

    # Realizando os filtros
    df = filter_dataframe_dict_values(df=df, filters=filter_dict_values)

    return df


def read_data_lista_upes_documents():
    """
    Lê e processa os dados da fonte de documentos UPE.

    Retorna:
        pd.DataFrame: DataFrame processado contendo os dados dos documentos UPE.
    """

    # Diretório onde estão os dados de saúde das esteiras
    dir_data = Path(base_dir, "data/inputs/saude_esteira/BASE_LISTA_UPES_DOCUMENTS.xlsx")
    sheetname = "Sheet1"
    engine = "openpyxl"
    list_select_columns = ["UPE", "NOME ARQUIVO"]
    filter_dict_values = {}
    required_columns_with_types = {"UPE": "int", "NOME ARQUIVO": "object"}

    # Lendo os dados da base de saúde das esteiras
    df = transform_case(
        select_columns(
            read_data(file_path=dir_data, sheet_name=sheetname, engine=engine),
            target_columns=list_select_columns,
        ),
        columns_to_upper=True,
        cells_to_upper=True,
    )

    # Realizando o cast columns
    df = cast_columns(df=df, column_types=required_columns_with_types)

    # Realizando os filtros
    df = filter_dataframe_dict_values(df=df, filters=filter_dict_values)

    return df


def merge_backtest_saude_esteira(df_result_tables, df_result_metadatas):
    """
    Mescla e enriquece o DataFrame de entrada com dados das esteiras de saúde e documentos UPE.

    Args:
        df_result_tables (pd.DataFrame): DataFrame de orçamentos a ser enriquecido.
        df_result_metadatas(pd.DataFrame): DataFrame de metadados a ser enriquecido.

    Retorna:
        pd.DataFrame: DataFrame enriquecido com dados adicionais das esteiras de saúde e documentos UPE.
    """

    # Transformando os dados de entrada para letras maiúsculas
    df_result_tables = transform_case(df_result_tables, columns_to_upper=True, cells_to_upper=True)

    # Transformando os dados de entrada para letras maiúsculas
    df_result_metadatas = transform_case(
        df_result_metadatas, columns_to_upper=True, cells_to_upper=True
    )

    # Lendo os dados das fontes externas
    df_saude_esteira = read_data_saude_esteira()
    df_lista_upes_documents = read_data_lista_upes_documents()

    # Iterando sobre as linhas do DataFrame de entrada
    for idx, value in df_result_metadatas.iterrows():
        cod_upe = value.get("CÓDIGO_UPE")

        # Obtendo o código da UPE correspondente na base da lista de documentos por upe
        value_upe = df_lista_upes_documents.loc[
            df_lista_upes_documents["NOME ARQUIVO"] == value.get("SOURCE_FILE"), "UPE"
        ].squeeze()

        if not pd.isna(value_upe):
            cod_upe = value_upe

            df_result_metadatas.at[idx, "CÓDIGO_UPE"] = cod_upe

        # Atualizando os dados com base na esteira de saúde
        match_row = df_saude_esteira.loc[df_saude_esteira["COD_UPE"] == cod_upe]

        if not match_row.empty:
            df_result_metadatas.at[idx, "NUMERO_AGENCIA"] = match_row["AG"].squeeze()
            df_result_metadatas.at[idx, "CONSTRUTORA"] = match_row["FORNECEDOR"].squeeze()
            df_result_metadatas.at[idx, "PROGRAMA_DONO"] = match_row["PMO_DONO"].squeeze()

    return df_result_metadatas

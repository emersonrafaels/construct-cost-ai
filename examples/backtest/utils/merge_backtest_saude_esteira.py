import sys
from pathlib import Path

# Adicionar src ao path
base_dir = Path(__file__).parents[3]
sys.path.insert(0, str(Path(base_dir, "src")))

from src.utils.data.data_functions import (
    read_data,
    transform_case,
    select_columns,
    filter_dataframe_dict_values,
    cast_columns
)


def read_data_saude_esteira():
    
    # Diretório onde estão os dados de saúde das esteiras
    dir_data = Path(base_dir, "data/inputs/saude_esteira/BASE_SAUDE_DA_ESTEIRA.xlsx")
    sheetname = "Sheet1"
    engine = "calamine"
    list_select_columns = ["cod_upe", "ag", "pmo_dono", "sub_etapa", "fornecedor"]
    filter_dict_values = {"SUB_ETAPA": "ORÇAMENTO - CONSTRUÇÃO E OBRAS"}
    required_columns_with_types = {'COD_UPE': 'int', 'AG': 'int', 'PMO_DONO': 'object', 'SUB_ETAPA': 'object', 'FORNECEDOR': 'object'}
    
    # Lendo os dados da base de saúde das esteiras
    df_saude_esteira = transform_case(
        select_columns(
            read_data(file_path=dir_data, sheet_name=sheetname, engine=engine),
            target_columns=list_select_columns,
        ),
        columns_to_upper=True,
        cells_to_upper=True,
    )
    
    # Realizando o cast columns
    df_saude_esteira = cast_columns(df=df_saude_esteira, column_types=required_columns_with_types)

    # Realizando os filtros
    df_saude_esteira = filter_dataframe_dict_values(df=df_saude_esteira, filters=filter_dict_values)
    
    return df_saude_esteira


def read_data_lista_upes_documents():
    
    # Diretório onde estão os dados de saúde das esteiras
    dir_data = Path(base_dir, "data/inputs/saude_esteira/BASE_LISTA_UPES_DOCUMENTS.xlsx")
    sheetname = "Sheet1"
    engine = "openpyxl"
    list_select_columns = ["UPE", "NOME ARQUIVO"]
    filter_dict_values = {}
    required_columns_with_types = {'UPE': 'int', 'NOME ARQUIVO': 'object'}
    
    # Lendo os dados da base de saúde das esteiras
    df_saude_esteira = transform_case(
        select_columns(
            read_data(file_path=dir_data, sheet_name=sheetname, engine=engine),
            target_columns=list_select_columns,
        ),
        columns_to_upper=True,
        cells_to_upper=True,
    )
    
    # Realizando o cast columns
    df_saude_esteira = cast_columns(df=df_saude_esteira, column_types=required_columns_with_types)

    # Realizando os filtros
    df_saude_esteira = filter_dataframe_dict_values(df=df_saude_esteira, filters=filter_dict_values)
    
    return df_saude_esteira

def merge_backtest_saude_esteira(df):

    # Lendo os dados de saúde das esteiras
    df_saude_esteira = read_data_saude_esteira()
    
    # Lendo os dados da lista de upes e seus documentos
    df_lista_upes_documents = read_data_lista_upes_documents()
    
    # Realizando o lookup dos dados faltantes dos dados recebidos
    for idx, value in df.iterrows():
        print(value)

    return df

import sys
from pathlib import Path

# Adicionar src ao path
base_dir = Path(__file__).parents[2]
sys.path.insert(0, str(Path(base_dir, "src")))

from src.utils.data.data_functions import (
    read_data,
    transform_case,
    select_columns,
    filter_dataframe_dict_values,
)

# Diretório onde estão os dados de saúde das esteiras
DIR_DATA_SAUDE_ESTEIRAS = Path(base_dir, "data/inputs/saude_esteira/BASE_SAUDE_DA_ESTEIRA.xlsx")
sheetname = "Sheet1"
engine = "calamine"
list_select_columns = ["id", "cod_upe", "ag", "pmo_dono", "sub_etapa", "fornecedor"]


def merge_backtest_saude_esteira(df):

    # Lendo os dados da base de saúde das esteiras
    df_saude_esteira = transform_case(
        select_columns(
            read_data(file_path=DIR_DATA_SAUDE_ESTEIRAS, sheet_name=sheetname, engine=engine),
            target_columns=list_select_columns,
        ),
        columns_to_upper=True,
        cells_to_upper=True,
    )

    # Realizando os filtros que queremos

    return df_saude_esteira

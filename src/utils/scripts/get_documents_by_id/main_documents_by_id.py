import sys
from pathlib import Path

import pandas as pd

sys.path.append(Path(__file__).parents[0])

from modules.synthetic_data import make_synthetic_upe_dataset
from modules.get_documents_by_id import orchestra_pick_row_by_date


def orchestra_generate_final_dataframe(df):

    # Parâmetros hardcoded
    strategy = ["between", "nearest", "last"]
    strict = False
    upe_col = "UPE"
    date_col = "DATA_INCLUSAO_DOC"
    start_col = "DATA_INICIO_REAL"
    end_col = "DATA_FIM_REAL"
    prefer_col = "DATA_INCLUSAO_DOC"
    between_preference = "last"

    # Gera o DataFrame final
    df_result = orchestra_pick_row_by_date(
        df,
        strategy=strategy,
        strict=strict,
        upe_col=upe_col,
        date_col=date_col,
        start_col=start_col,
        end_col=end_col,
        prefer_col=prefer_col,
        between_preference=between_preference,
    )

    return df_result


def main():
    """
    Função principal para demonstrar o uso do script.

    Esta função utiliza os módulos criados para gerar um conjunto de dados sintético,
    processar colunas de data e realizar operações adicionais conforme necessário.
    """

    # Diretório atual
    current_dir = Path(__file__).parents[0]

    # Gera o conjunto de dados sintético
    df = make_synthetic_upe_dataset(n_upe=20, rows_per_upe=(3, 6), seed=7)

    # Salva o conjunto de dados gerado para análise
    generated_file = current_dir / "dados_gerados.xlsx"
    df.to_excel(generated_file, index=False)
    print(f"Conjunto de dados gerado salvo em '{generated_file}'.")

    # Orquestra a obtenção dos dados
    df_result = orchestra_generate_final_dataframe(df=df)

    # Salva o DataFrame final para análise
    final_file = current_dir / "dados_finais.xlsx"
    df_result.to_excel(final_file, index=False)
    print(f"DataFrame final salvo em '{final_file}'.")


if __name__ == "__main__":
    main()

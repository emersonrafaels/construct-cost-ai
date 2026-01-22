import numpy as np
import pandas as pd

def make_synthetic_upe_dataset(
    n_upe: int = 8,
    rows_per_upe: tuple[int, int] = (2, 6),
    seed: int = 42,
) -> pd.DataFrame:
    """
    Gera um conjunto de dados sintético para UPEs (Unidades de Planejamento e Execução).

    Args:
        n_upe (int): Número de UPEs a serem geradas.
        rows_per_upe (tuple[int, int]): Faixa de linhas por UPE.
        seed (int): Semente aleatória para reprodutibilidade.

    Returns:
        pd.DataFrame: Conjunto de dados sintético com as colunas DOCUMENTO, UPE, DATA_INCLUSAO_DOC, etc.
    """
    rng = np.random.default_rng(seed)

    base_upe = rng.integers(190000, 199999, size=n_upe)
    fornecedores = [
        "KALFER CONSTRUÇÃO",
        "PBA ENGENHARIA",
        "JAPJ CONSTRUÇÕES",
        "CONSTRUTORA FATECRIL",
        "L MENDES CONSTRUÇÕES",
        "HBT ENGENHARIA",
        "SISTEL SISTEMAS",
        "BWT ENGENHARIA",
        "MANFER ENG MANUT",
        "EXPLORE CONSTRUTORA",
        "DR CONSTRUÇÕES",
        "ELLO COSTA LIMA",
    ]

    rows = []
    doc_id = 400000

    for upe in base_upe:
        k = int(rng.integers(rows_per_upe[0], rows_per_upe[1] + 1))
        start = pd.Timestamp("2024-01-01") + pd.Timedelta(days=int(rng.integers(0, 500)))
        duration_days = int(rng.integers(10, 120))
        end = start + pd.Timedelta(days=duration_days)

        for _ in range(k):
            inclusion_offset = int(rng.integers(-15, 45))
            inclusion = (
                start
                + pd.Timedelta(days=inclusion_offset)
                + pd.Timedelta(
                    hours=int(rng.integers(0, 24)),
                    minutes=int(rng.integers(0, 60)),
                    seconds=int(rng.integers(0, 60)),
                )
            )

            # Introduce poorly formatted dates and null values
            if rng.random() < 0.2:  # 20% chance to introduce a poorly formatted date
                inclusion = inclusion.strftime("%Y/%m/%d %H:%M:%S") if rng.random() < 0.5 else None
            elif rng.random() < 0.1:  # 10% chance to introduce a completely invalid date
                inclusion = "invalid_date"

            # Add rows for various strategies
            rows.append(
                {
                    "DOCUMENTO": doc_id,
                    "UPE": int(upe),
                    "DATA_INCLUSAO_DOC": inclusion,
                    "DATA_INICIO_REAL": start.normalize(),
                    "DATA_FIM_REAL": end.normalize(),
                    "FORNECEDOR": rng.choice(fornecedores),
                }
            )

            # Add rows outside the 'between' range for 'nearest' strategy
            if rng.random() < 0.3:  # 30% chance to add an out-of-range row
                out_of_range_date = end + pd.Timedelta(days=int(rng.integers(1, 30)))
                rows.append(
                    {
                        "DOCUMENTO": doc_id + 1,
                        "UPE": int(upe),
                        "DATA_INCLUSAO_DOC": out_of_range_date,
                        "DATA_INICIO_REAL": start.normalize(),
                        "DATA_FIM_REAL": end.normalize(),
                        "FORNECEDOR": rng.choice(fornecedores),
                    }
                )

            doc_id += int(rng.integers(1, 80))

    df = pd.DataFrame(rows)
    df = df.sort_values(["UPE", "DATA_INICIO_REAL", "DATA_INCLUSAO_DOC"], na_position="first").reset_index(drop=True)
    return df
"""
pattern: # Padrão a ser buscado
method: # Método: "iterate", "limited_iterate", ou "specific_cell"
max_rows: # Número máximo de linhas para iterar (apenas para "limited_iterate")
specific_cell: # Coordenadas da célula específica (linha, coluna) para "specific_cell"
"""


def get_metadata_keys():
    """Retorna as chaves de metadados padrão para leitura de orçamentos.

    Returns:
        dict: Dicionário contendo as chaves de metadados padrão.
    """

    # Metadados padrão ajustados
    DEFAULT_METADATA_KEYS = {
        "default01": {
            "CÓDIGO_UPE": {
                "sheet_name": "LPU",
                "pattern": "UPE",
                "method": "iterate",
                "max_rows": None,
                "specific_cell": None,
            },
            "NUMERO_AGENCIA": {
                "sheet_name": "LPU",
                "pattern": "AGÊNCIA",
                "method": "iterate",
                "max_rows": None,
                "specific_cell": None,
            },
            "NOME_AGENCIA": {
                "sheet_name": "LPU",
                "pattern": "NOME AGÊNCIA",
                "method": "iterate",
                "max_rows": None,
                "specific_cell": None,
            },
            "CONSTRUTORA": {
                "sheet_name": "LPU",
                "pattern": "CONSTRUTORA",
                "method": "specific_cell",
                "max_rows": None,
                "specific_cell": (0, 3),
            },
            "TIPO": {
                "sheet_name": "LPU",
                "pattern": "TIPO",
                "method": "iterate",
                "max_rows": None,
                "specific_cell": None,
            },
            "PROGRAMA_DONO": {
                "sheet_name": "LPU",
                "pattern": "DONO",
                "method": "iterate",
                "max_rows": None,
                "specific_cell": None,
            },
        },
        "default02": {
            "CÓDIGO_UPE": {
                "sheet_name": "Resumo",
                "pattern": "UPE",
                "method": "specific_cell",
                "max_rows": None,
                "specific_cell": (5, 12),
            },
            "NUMERO_AGENCIA": {
                "sheet_name": "Resumo",
                "pattern": "AGÊNCIA",
                "method": "specific_cell",
                "max_rows": None,
                "specific_cell": (5, 2),
            },
            "NOME_AGENCIA": {
                "sheet_name": "Resumo",
                "pattern": "NOME AGÊNCIA",
                "method": "specific_cell",
                "max_rows": None,
                "specific_cell": (6, 2),
            },
            "CONSTRUTORA": {
                "sheet_name": "Resumo",
                "pattern": "CONSTRUTORA",
                "method": None,
                "max_rows": None,
                "specific_cell": None,
            },
            "TIPO": {
                "sheet_name": "Resumo",
                "pattern": "TIPO",
                "method": "specific_cell",
                "max_rows": None,
                "specific_cell": (7, 2),
            },
            "PROGRAMA_DONO": {
                "sheet_name": "01",
                "pattern": "DONO",
                "method": "specific_cell",
                "max_rows": None,
                "specific_cell": (3, 0),
            },
        },
    }

    return DEFAULT_METADATA_KEYS

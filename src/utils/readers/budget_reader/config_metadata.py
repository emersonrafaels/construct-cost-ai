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
                "type": "int",
            },
            "NUMERO_AGENCIA": {
                "sheet_name": "LPU",
                "pattern": "AGENCIA",
                "method": "iterate",
                "max_rows": None,
                "specific_cell": None,
                "type": "int",
            },
            "NOME_AGENCIA": {
                "sheet_name": "LPU",
                "pattern": "NOME AGENCIA",
                "method": "iterate",
                "max_rows": None,
                "specific_cell": None,
                "type": "str",
            },
            "CONSTRUTORA": {
                "sheet_name": "LPU",
                "pattern": "CONSTRUTORA",
                "method": "specific_cell",
                "max_rows": None,
                "specific_cell": (1, 0),
                "type": "str",
            },
            "TIPO": {
                "sheet_name": "LPU",
                "pattern": "TIPO",
                "method": "iterate",
                "max_rows": None,
                "specific_cell": None,
                "type": "str",
            },
            "PROGRAMA_DONO": {
                "sheet_name": "LPU",
                "pattern": "DONO",
                "method": "iterate",
                "max_rows": None,
                "specific_cell": None,
                "type": "str",
            },
        },
        "default02": {
            "CÓDIGO_UPE": {
                "sheet_name": "Resumo",
                "pattern": "UPE",
                "method": "specific_cell",
                "max_rows": None,
                "specific_cell": (4, 11),
                "type": "int",
            },
            "NUMERO_AGENCIA": {
                "sheet_name": "Resumo",
                "pattern": "AGENCIA",
                "method": "specific_cell",
                "max_rows": None,
                "specific_cell": (4, 1),
                "type": "int",
            },
            "NOME_AGENCIA": {
                "sheet_name": "Resumo",
                "pattern": "NOME AGENCIA",
                "method": "specific_cell",
                "max_rows": None,
                "specific_cell": (5, 1),
                "type": "str",
            },
            "CONSTRUTORA": {
                "sheet_name": "Resumo",
                "pattern": "CONSTRUTORA",
                "method": None,
                "max_rows": None,
                "specific_cell": None,
                "type": "str",
            },
            "TIPO": {
                "sheet_name": "Resumo",
                "pattern": "TIPO",
                "method": "specific_cell",
                "max_rows": None,
                "specific_cell": (6, 1),
                "type": "str",
            },
            "PROGRAMA_DONO": {
                "sheet_name": "01",
                "pattern": "DONO",
                "method": None,
                "max_rows": None,
                "specific_cell": None,
                "type": "str",
            },
        },
        "default03": {
            "CÓDIGO_UPE": {
                "sheet_name": "Resumo",
                "pattern": "UPE",
                "method": "specific_cell",
                "max_rows": None,
                "specific_cell": None,
                "type": "str",
            },
            "NUMERO_AGENCIA": {
                "sheet_name": "Resumo",
                "pattern": "AGENCIA",
                "method": "specific_cell",
                "max_rows": None,
                "specific_cell": (4, 1),
                "type": "int",
            },
            "NOME_AGENCIA": {
                "sheet_name": "Resumo",
                "pattern": "NOME AGENCIA",
                "method": "specific_cell",
                "max_rows": None,
                "specific_cell": (5, 1),
                "type": "str",
            },
            "CONSTRUTORA": {
                "sheet_name": "Resumo",
                "pattern": "CONSTRUTORA",
                "method": None,
                "max_rows": None,
                "specific_cell": None,
                "type": "str",
            },
            "TIPO": {
                "sheet_name": "Resumo",
                "pattern": "TIPO",
                "method": "specific_cell",
                "max_rows": None,
                "specific_cell": (6, 1),
                "type": "str",
            },
            "PROGRAMA_DONO": {
                "sheet_name": "01",
                "pattern": "DONO",
                "method": None,
                "max_rows": None,
                "specific_cell": None,
                "type": "str",
            },
        },
    }

    return DEFAULT_METADATA_KEYS

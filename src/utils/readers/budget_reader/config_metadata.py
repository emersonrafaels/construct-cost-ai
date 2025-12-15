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
                "pattern": "UPE",
                "method": "iterate",
                "max_rows": None,
                "specific_cell": None,
            },
            "NUMERO_AGENCIA": {
                "pattern": "AGÊNCIA",
                "method": "iterate",
                "max_rows": None,
                "specific_cell": None,
            },
            "NOME_AGENCIA": {
                "pattern": "NOME AGÊNCIA",
                "method": "iterate",
                "max_rows": None,
                "specific_cell": None,
            },
            "CONSTRUTORA": {
                "pattern": "CONSTRUTORA",
                "method": "specific_cell",
                "max_rows": None,
                "specific_cell": (1, 0),
            },
            "TIPO": {
                "pattern": "TIPO",
                "method": "iterate",
                "max_rows": None,
                "specific_cell": None,
            },
            "QUANTIDADE_SINERGIAS": {
                "pattern": "QUANTIDADE SINERGIAS",
                "method": "iterate",
                "max_rows": None,
                "specific_cell": None,
            },
            "PROGRAMA_DONO": {
                "pattern": "DONO",
                "method": "iterate",
                "max_rows": None,
                "specific_cell": None,
            },
        },
        "default02": {
            "CÓDIGO_UPE": {
                "pattern": "UPE",
                "method": "UPE",
                "max_rows": None,
                "specific_cell": None,
            },
            "NUMERO_AGENCIA": {
                "pattern": "AGÊNCIA",
                "method": "specific_cell",
                "max_rows": None,
                "specific_cell": (1, 0),
            },
            "NOME_AGENCIA": {
                "pattern": "NOME AGÊNCIA",
                "method": "specific_cell",
                "max_rows": None,
                "specific_cell": (1, 0),
            },
            "CONSTRUTORA": {
                "pattern": "CONSTRUTORA",
                "method": None,
                "max_rows": None,
                "specific_cell": None,
            },
            "TIPO": {
                "pattern": "TIPO",
                "method": "specific_cell",
                "max_rows": None,
                "specific_cell": None,
            },
            "QUANTIDADE_SINERGIAS": {
                "pattern": "QUANTIDADE SINERGIAS",
                "method": "iterate",
                "max_rows": None,
                "specific_cell": None,
            },
            "PROGRAMA_DONO": {
                "pattern": "DONO",
                "method": "soecific_cell",
                "max_rows": None,
                "specific_cell": (3,0),
            },
        },
    }
    
    return DEFAULT_METADATA_KEYS
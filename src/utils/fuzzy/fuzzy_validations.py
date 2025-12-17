from typing import List, Tuple, Union
from fuzzywuzzy import fuzz, process


def fuzzy_match(value: str, choices: List[str], threshold: int = 80) -> bool:
    """
    Verifica se um valor tem um match fuzzy acima de um threshold em uma lista de valores.

    Args:
        value (str): O valor a ser comparado.
        choices (List[str]): A lista de valores para comparação.
        threshold (int): O percentual mínimo de match para validar como True.

    Returns:
        bool: True se o match fuzzy for maior ou igual ao threshold, caso contrário False.
    """
    best_match = process.extractOne(value, choices, scorer=fuzz.ratio)
    if best_match and best_match[1] >= threshold:
        return True
    return False


def top_n_fuzzy_matches(value: str, choices: List[str], n: int = 3) -> List[Tuple[str, int]]:
    """
    Retorna os top N maiores matches fuzzy de um valor em uma lista de valores.

    Args:
        value (str): O valor a ser comparado.
        choices (List[str]): A lista de valores para comparação.
        n (int): O número de maiores matches a retornar.

    Returns:
        List[Tuple[str, int]]: Uma lista com os top N matches e seus percentuais de similaridade.
    """
    return process.extract(value, choices, scorer=fuzz.ratio, limit=n)


def best_fuzzy_match(value: str, choices: List[str]) -> Union[Tuple[str, int], None]:
    """
    Retorna o melhor match fuzzy de um valor em uma lista de valores.

    Args:
        value (str): O valor a ser comparado.
        choices (List[str]): A lista de valores para comparação.

    Returns:
        Union[Tuple[str, int], None]: O melhor match e seu percentual de similaridade, ou None se não houver matches.
    """
    return process.extractOne(value, choices, scorer=fuzz.ratio)


def filter_fuzzy_matches(
    value: str, choices: List[str], threshold: int = 80
) -> List[Tuple[str, int]]:
    """
    Filtra os valores de uma lista que possuem um match fuzzy acima de um threshold.

    Args:
        value (str): O valor a ser comparado.
        choices (List[str]): A lista de valores para comparação.
        threshold (int): O percentual mínimo de match para incluir no resultado.

    Returns:
        List[Tuple[str, int]]: Uma lista de valores que possuem um match acima do threshold e seus percentuais.
    """
    return [
        match
        for match in process.extract(value, choices, scorer=fuzz.ratio)
        if match[1] >= threshold
    ]

import time
from functools import wraps
from typing import Any

import numpy as np


def measure_execution_time(condition=True):
    """
    Decorator para medir o tempo de execução de uma função, com comportamento condicional.

    Args:
        condition (bool): Define se o decorator será aplicado ou não. Padrão é True.

    Returns:
        callable: A função decorada com medição de tempo, ou a função original se a condição for False.
    """

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if condition:
                start_time = time.time()
                result = func(*args, **kwargs)
                end_time = time.time()
                execution_time = end_time - start_time
                print(f"Function '{func.__name__}' executed in {execution_time:.4f} seconds.")
                return result
            else:
                # Se a condição for False, executa a função diretamente sem medir o tempo
                return func(*args, **kwargs)

        return wrapper

    return decorator


def get_item_safe(obj, idx, return_key=False):
    """
    Obtém um item de forma segura de uma lista ou dicionário.

    Args:
        obj (list | dict): O objeto de onde o item será obtido. Pode ser uma lista ou um dicionário.
        idx (int | Any): O índice (para listas) ou chave/índice (para dicionários) do item a ser obtido.
        return_key (bool, opcional): Se True, retorna a chave ao invés do valor (apenas para dicionários). Padrão é False.

    Returns:
        Any: O valor correspondente ao índice ou chave, ou None se o índice/chave não existir ou ocorrer um erro.

    Explicação do código:
    1. Verifica se o objeto é uma lista:
        - Se for, tenta acessar o índice fornecido.
        - Retorna o valor correspondente se o índice for válido, ou None caso contrário.
    2. Caso o objeto não seja uma lista, assume que é um dicionário:
        - Verifica se o índice fornecido está nas chaves do dicionário.
        - Retorna a chave (se `return_key=True`) ou o valor correspondente.
    3. Se o índice não for uma chave válida, tenta acessar o dicionário como se o índice fosse um número:
        - Obtém a chave correspondente ao índice numérico.
        - Retorna a chave (se `return_key=True`) ou o valor correspondente.
        - Caso ocorra um erro (índice inválido ou tipo incorreto), retorna None.
    """

    if isinstance(obj, list):
        # Verifica se o objeto é uma lista e tenta acessar o índice fornecido.
        return obj[idx] if len(obj) > idx else None
    elif isinstance(obj, dict):
        # Verifica se o objeto é um dicionário.
        if idx in obj:
            # Verifica se o índice fornecido está nas chaves do dicionário.
            return idx if return_key else obj[idx]
        try:
            # Tenta acessar o dicionário como se o índice fosse um número.
            key = list(obj.keys())[idx]
            return key if return_key else obj[key]
        except (IndexError, TypeError):
            # Retorna None caso ocorra um erro (índice inválido ou tipo incorreto).
            return None
    return None


def to_float_resilient(value, default=None):
    """
    Converte um valor para float de forma resiliente, lidando com diferentes formatos.

    Args:
        value (Any): O valor a ser convertido.
        default (Any, opcional): Valor padrão a ser retornado em caso de falha na conversão. Padrão é None.

    Returns:
        float | Any: O valor convertido para float ou o valor padrão em caso de falha na conversão.
    """

    if value is None or isinstance(value, float) and np.isnan(value):
        return default
    try:
        if isinstance(value, str):
            value = value.replace(".", "").replace(",", ".")
        return float(value)
    except Exception:
        return default


def convert_value(value: Any, expected_type: str) -> Any:
    """
    Converte um valor para o tipo esperado, com suporte a tipos básicos.

    Tipos suportados:
        - "int"
        - "float"
        - "str"
        - "bool"

    Args:
        value (Any): O valor a ser convertido.
        expected_type (str): O tipo para o qual o valor deve ser convertido (como string).

    Returns:
        Any: O valor convertido para o tipo esperado ou o valor original em caso de erro.
    """
    try:
        if expected_type == "bool":  # Verifica se o tipo esperado é booleano
            # Conversão especial para booleanos
            if isinstance(
                value, str
            ):  # Se o valor for uma string, normaliza para lowercase e remove espaços
                value = value.strip().lower()
                if value in ("true", "1", "yes", "sim"):  # Valores que representam True
                    return True
                elif value in ("false", "0", "no", "não"):  # Valores que representam False
                    return False
                else:
                    print(f"Valor '{value}' não pode ser convertido para booleano.")
                    return value
            return bool(value)  # Converte outros tipos para booleano diretamente
        elif expected_type == "int":  # Verifica se o tipo esperado é inteiro
            # Conversão resiliente para inteiros
            if (
                isinstance(value, float) and value.is_integer()
            ):  # Se for float e inteiro, converte diretamente
                return int(value)
            return int(
                float(value)
            )  # Converte para float primeiro para lidar com strings como "188292.0"
        elif expected_type == "float":  # Verifica se o tipo esperado é float
            return float(value)  # Converte diretamente para float
        elif expected_type == "str":  # Verifica se o tipo esperado é string
            return str(value)  # Converte diretamente para string
        else:
            print(f"Tipo '{expected_type}' não é suportado para conversão.")
            return value
    except (ValueError, TypeError) as e:
        # Em caso de erro, imprime o erro e retorna o valor original
        print(f"Falha ao converter o valor '{value}' para o tipo {expected_type}: {e}")
        return value

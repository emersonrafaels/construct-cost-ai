from typing import Any

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
            if isinstance(value, str):  # Se o valor for uma string, normaliza para lowercase e remove espaços
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
            if isinstance(value, float) and value.is_integer():  # Se for float e inteiro, converte diretamente
                return int(value)
            return int(float(value))  # Converte para float primeiro para lidar com strings como "188292.0"
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
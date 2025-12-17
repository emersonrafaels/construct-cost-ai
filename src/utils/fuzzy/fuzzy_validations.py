from dataclasses import dataclass
from typing import Callable, List, Optional, Sequence, Union, Dict
import re
import unicodedata

from fuzzywuzzy import fuzz, process


# =========================
# 1) Normalização de texto
# =========================
def normalize_text(value: str) -> str:
    """
    Normaliza um texto, removendo espaços extras e convertendo para lowercase.

    Args:
        value (str): O texto a ser normalizado.

    Returns:
        str: O texto normalizado.
    """
    # Se vier None (defensivo), devolve string vazia
    if value is None:
        return ""

    # Remove espaços nas pontas e coloca tudo em lowercase
    v = value.strip().lower()

    # Decompõe caracteres unicode (ex.: "ç" vira "c"+"~") para remover acentos depois
    v = unicodedata.normalize("NFKD", v)

    # Remove marcas de acento (combining characters)
    v = "".join(ch for ch in v if not unicodedata.combining(ch))

    # Trocas úteis para unidades/símbolos recorrentes em planilhas (m² / ²)
    v = v.replace("m²", "m2").replace("²", "2")

    # Substitui qualquer caractere que não seja "letra/número/_/espaço" por espaço
    # Isso ajuda com: "-", "/", ".", "," etc.
    v = re.sub(r"[^\w\s]", " ", v)

    # Colapsa múltiplos espaços em um só e tira espaços nas bordas
    v = re.sub(r"\s+", " ", v).strip()

    # Retorna texto pronto para comparação
    return v


# =========================
# 2) Modelo do resultado
# =========================
@dataclass(frozen=True)
class MatchResult:
    """
    Resultado estruturado de um match fuzzy.
    - choice_original: texto original (não normalizado) vindo de choices
    - choice_normalized: texto normalizado do choice (o que foi comparado)
    - score: pontuação do scorer (0..100)
    - index: posição do choice dentro da lista original
    - query_original: valor original que você buscou
    - query_normalized: valor normalizado (o que foi comparado)
    """
    choice_original: str
    choice_normalized: str
    score: int
    index: int
    query_original: str
    query_normalized: str


# =========================
# 3) Função fuzzy match
# =========================
def fuzzy_match(
    value: str,
    choices: Sequence[str],
    top_matches: int = 1,
    threshold: int = 80,
    scorer: Callable = fuzz.token_set_ratio,
    normalize: bool = True,
    return_all: bool = False,
) -> Dict[str, List[Dict[str, Union[str, int]]]]:
    """
    Retorna os melhores matches fuzzy de uma lista de escolhas, com a opção de filtrar por threshold.

    Args:
        value (str): O valor a ser comparado.
        choices (List[str]): A lista de valores para comparação.
        top_matches (int): O número de melhores matches a retornar. Default é 1.
        threshold (int): O percentual mínimo de match para incluir no resultado. Default é 80.
        scorer (Callable): Função de pontuação fuzzy a ser usada. Default é fuzz.ratio.
        normalize (bool): Se True, normaliza os valores (lowercase e remove espaços). Default é True.

    Returns:
        Dict[str, List[Dict[str, Union[str, int]]]]: Um dicionário contendo os melhores matches e suas pontuações.
            - "matches": Uma lista de dicionários com "choice" e "score" para cada match.
    """

    # -------------------------
    # Validações de parâmetros
    # -------------------------

    # top_matches precisa ser >= 1 para fazer sentido
    if top_matches <= 0:
        raise ValueError("top_matches deve ser >= 1")

    # threshold deve ser um percentual válido
    if not (0 <= threshold <= 100):
        raise ValueError("threshold deve estar entre 0 e 100")

    # Se não tem value ou choices, devolve vazio/None conforme modo
    if not value or not choices:
        return {"matches": []} if top_matches == 1 else []

    # -------------------------
    # Preparação das entradas
    # -------------------------

    # Guardamos a lista original (como veio)
    original_choices = list(choices)

    # Normaliza (ou não) o value e choices
    if normalize:
        # Normaliza a query (value)
        value_n = normalize_text(value)
        # Normaliza cada choice
        choices_n = [normalize_text(c) for c in original_choices]
    else:
        # Se não normalizar, comparamos como está
        value_n = value
        choices_n = original_choices

    # -------------------------
    # Extração dos melhores
    # -------------------------

    # process.extract compara value_n contra choices_n e retorna os "top_matches" melhores
    # limit define quantos resultados você quer
    raw_matches = process.extract(
        value_n,         # query
        choices_n,       # lista comparada
        scorer=scorer,   # função de score
        limit=top_matches
    )

    # -------------------------
    # Montagem estruturada
    # -------------------------

    results: List[MatchResult] = []

    for item in raw_matches:
        # item pode ser: (match_norm, score) ou (match_norm, score, idx)
        if len(item) == 3:
            # Caso ideal: já vem o índice (idx) do match em choices_n
            match_norm, score, idx = item
        else:
            # Caso venha só (match_norm, score), precisamos "achar" o índice
            # Atenção: se houver choices_n duplicados, index pega o primeiro.
            match_norm, score = item
            idx = choices_n.index(match_norm)

        # Converte score para int (garantia de tipo)
        score_int = int(score)

        # Se return_all=False, aplicamos o filtro do threshold
        # Se return_all=True, não filtramos (útil pra debugar por que não bateu)
        if (score_int >= threshold) or return_all:
            # Monta o resultado com info completa
            results.append(
                MatchResult(
                    choice_original=original_choices[idx],  # choice original (não normalizado)
                    choice_normalized=choices_n[idx],       # choice normalizado (comparado)
                    score=score_int,                        # score final
                    index=int(idx),                         # índice na lista original
                    query_original=value,                   # query original
                    query_normalized=value_n,               # query normalizada (comparada)
                )
            )

    # -------------------------
    # Formato do retorno
    # -------------------------

    # Se top_matches == 1, devolvemos apenas o primeiro ou None
    if top_matches == 1:
        return {"matches": [results[0]]} if results else {"matches": []}

    # Se top_matches > 1, devolvemos a lista (talvez vazia)
    return {"matches": results}

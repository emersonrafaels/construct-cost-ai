import re
import sys
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, List, Literal, Optional, Sequence, Tuple, Union, overload

# Adicionar src ao path
base_dir = Path(__file__).parents[4]
sys.path.insert(0, str(Path(base_dir, "src")))

from utils.python_functions import measure_execution_time


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
    - query: valor original que você buscou
    - query_normalized: valor normalizado (o que foi comparado)
    - choice: texto original (não normalizado) vindo de choices
    - choice_normalized: texto normalizado do choice (o que foi comparado)
    - score: pontuação do scorer (0..100)
    - index: posição do choice dentro da lista original
    """

    query: str
    query_normalized: str
    choice: str
    choice_normalized: str
    score: int
    index: int


# =========================
# 3) Função fuzzy match
# =========================
@measure_execution_time
def fuzzy_match(
    value: str,
    choices: Sequence[str],
    top_matches: int = 1,
    threshold: int = 80,
    scorer: Optional[Callable] = None,
    normalize: bool = True,
    return_all: bool = False,
    library: Literal["fuzzywuzzy", "rapidfuzz"] = "rapidfuzz",
) -> Optional[Union[MatchResult, List[MatchResult]]]:
    """
    Retorna os melhores matches fuzzy de uma lista de escolhas, com a opção de filtrar por threshold.

    Args:
        value (str): O valor a ser comparado.
        choices (List[str]): A lista de valores para comparação.
        top_matches (int): O número de melhores matches a retornar. Default é 1.
        threshold (int): O percentual mínimo de match para incluir no resultado. Default é 80.
        scorer (Callable): Função de pontuação fuzzy a ser usada. Default é None.
        normalize (bool): Se True, normaliza os valores (lowercase e remove espaços). Default é True.
        return_all (bool): Se True, retorna todos os matches, mesmo abaixo do threshold. Default é False.
        library (Literal["fuzzywuzzy", "rapidfuzz"]): Biblioteca a ser usada para fuzzy matching. Default é "rapidfuzz".

    Returns:
        Optional[Union[MatchResult, List[MatchResult]]]:
            - Se top_matches=1, retorna um único objeto MatchResult ou None se não houver matches.
            - Se top_matches>1, retorna uma lista de objetos MatchResult (vazia se não houver matches).
    """

    # -------------------------
    # Validações de parâmetros
    # -------------------------

    if library not in {"fuzzywuzzy", "rapidfuzz"}:
        raise ValueError("A biblioteca deve ser 'fuzzywuzzy' ou 'rapidfuzz'.")

    if top_matches <= 0:
        raise ValueError("top_matches deve ser >= 1")

    if not (0 <= threshold <= 100):
        raise ValueError("threshold deve estar entre 0 e 100")

    if not value or not choices:
        return None if top_matches == 1 else []

    # -------------------------
    # Preparação das entradas
    # -------------------------

    original_choices = list(choices)

    if normalize:
        value_n = normalize_text(value)
        choices_n = [normalize_text(c) for c in original_choices]
    else:
        value_n = value
        choices_n = original_choices

    # -------------------------
    # Seleção da biblioteca
    # -------------------------

    if library == "fuzzywuzzy":
        from fuzzywuzzy import process, fuzz
        scorer = scorer or fuzz.token_set_ratio
        raw_matches = process.extract(
            value_n,
            choices_n,
            scorer=scorer,
            limit=top_matches,
        )
    else:  # library == "rapidfuzz"
        from rapidfuzz import process, fuzz
        scorer = scorer or fuzz.token_set_ratio
        raw_matches = process.extract(
            value_n,
            choices_n,
            scorer=scorer,
            limit=top_matches,
            score_cutoff=threshold,
        )

    # -------------------------
    # Resultado estruturado
    # -------------------------

    results = [
        MatchResult(
            query=value,
            query_normalized=value_n,
            choice=original_choices[idx],
            choice_normalized=choices_n[idx],
            score=int(score),
            index=idx,
        )
        for match_norm, score, idx in (
            (item[0], item[1], item[2] if len(item) == 3 else choices_n.index(item[0]))
            for item in raw_matches
        )
        if return_all or score >= threshold
    ]

    return results[0] if top_matches == 1 and results else results

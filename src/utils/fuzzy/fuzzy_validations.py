"""
Módulo: fuzzy_matcher
=====================

Este módulo fornece uma implementação robusta e extensível de *fuzzy matching*
para comparação de textos com ruído, variações semânticas e inconsistências
comuns em dados operacionais (ex.: orçamentos de obras, cadastros LPU,
descrições livres de fornecedores).

O foco principal é permitir:
- Comparação tolerante a erros de digitação, abreviações e ordem de palavras
- Normalização avançada de textos em português (acentos, pontuação, símbolos)
- Retorno estruturado dos resultados de matching
- Integração simples com pipelines de dados (Pandas, ETL, validações)

──────────────────────────────────────────────────────────────────────────────
Funcionalidades principais
──────────────────────────────────────────────────────────────────────────────
• Normalização de texto:
  - Lowercase e remoção de espaços extras
  - Remoção de acentuação (Unicode)
  - Padronização de símbolos comuns (ex.: m² → m2)
  - Remoção de pontuação e colapso de espaços

• Fuzzy matching com múltiplas bibliotecas:
  - Suporte a `rapidfuzz` (default, mais performático)
  - Suporte a `fuzzywuzzy` (fallback / compatibilidade)
  - Seleção dinâmica da função de scoring (ex.: token_sort_ratio)

• Resultado estruturado:
  - Uso do dataclass `MatchResult`
  - Retorna query original e normalizada
  - Retorna choice original, normalizada, score e índice
  - Facilita joins, auditoria e debug

• Modos de retorno flexíveis:
  - `top_matches=1` → melhor match único (ou None)
  - `top_matches>1` → lista ordenada de candidatos
  - `return_all=True` → inclui matches abaixo do threshold (debug)

• Tipagem avançada:
  - Uso de `@overload` para melhorar autocomplete e segurança estática
  - Retornos previsíveis conforme os parâmetros

──────────────────────────────────────────────────────────────────────────────
Casos de uso típicos
──────────────────────────────────────────────────────────────────────────────
• Mapear descrições livres de orçamentos para catálogo LPU
• Validar consistência de itens entre sistemas distintos
• Sugerir correspondências aproximadas para revisão humana
• Apoiar pipelines de Data Quality (DQ) e enriquecimento de dados
• Uso em notebooks, ETL batch ou serviços de backend

──────────────────────────────────────────────────────────────────────────────
Observações de projeto
──────────────────────────────────────────────────────────────────────────────
• O módulo não executa lógica de negócio: apenas matching textual
• A normalização é aplicada somente para comparação — os valores originais
  são sempre preservados no retorno
• A escolha da biblioteca e do scorer impacta diretamente precisão e performance
• Para grandes volumes, recomenda-se pré-processar e cachear `choices`

"""

__author__ = "Emerson V. Rafael (emervin)"
__copyright__ = "Verificador Inteligente de Orçamentos de Obras"
__credits__ = ["Emerson V. Rafael", "Lucas Ken", "Clarissa Simoyama"]
__license__ = "MIT"
__version__ = "1.0.0"
__maintainer__ = "Emerson V. Rafael (emervin), Lucas Ken (kushida), Clarissa Simoyama (simoyam)"
__squad__ = "DataCraft"
__email__ = "emersonssmile@gmail.com"
__status__ = "Development"

import re
import sys
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, List, Literal, Optional, Sequence, Tuple, Union, overload

base_dir = Path(__file__).parents[4]
sys.path.insert(0, str(Path(base_dir, "src")))

from utils.python_functions import measure_execution_time


# =========================================================
# 1) Normalização de texto
# =========================================================
def normalize_text(value: Optional[str]) -> str:
    """
    Normaliza texto para comparação:
      - strip + lower
      - remove acentos
      - normaliza símbolos comuns (m² -> m2, ² -> 2)
      - remove pontuação e normaliza espaços

    Args:
        value: Texto de entrada (pode ser None).

    Returns:
        Texto normalizado (string).
    """
    # Se vier None, devolve vazio para não quebrar normalização
    if value is None:
        return ""

    # Remove espaços nas pontas e coloca tudo em lowercase
    v = value.strip().lower()

    # Decompõe unicode (ex.: "ç" vira "c"+"~") para remover acentos depois
    v = unicodedata.normalize("NFKD", v)

    # Remove marcas de acento (combining characters)
    v = "".join(ch for ch in v if not unicodedata.combining(ch))

    # Trocas úteis para unidades/símbolos recorrentes em planilhas
    v = v.replace("m²", "m2").replace("²", "2")

    # Substitui pontuação por espaço (ajuda com: "-", "/", ".", "," etc.)
    v = re.sub(r"[^\w\s]", " ", v)

    # Colapsa múltiplos espaços em um só e tira espaços nas bordas
    v = re.sub(r"\s+", " ", v).strip()

    return v


# =========================================================
# 2) Modelo do resultado
# =========================================================
@dataclass(frozen=True)
class MatchResult:
    """
    Resultado estruturado de um match fuzzy.

    Campos:
      - query: valor original buscado
      - query_normalized: valor normalizado (comparado)
      - choice: texto original retornado (não normalizado)
      - choice_normalized: texto normalizado do choice (comparado)
      - score: pontuação do scorer (0..100)
      - index: índice do choice na lista original
    """

    query: str
    query_normalized: str
    choice: str
    choice_normalized: str
    score: int
    index: int


# =========================================================
# 3) Tipagem do retorno (overloads)
# =========================================================
@overload
def fuzzy_match(
    value: str,
    choices: Sequence[str],
    top_matches: Literal[1] = 1,
    threshold: int = 80,
    scorer: Optional[Callable] = None,
    normalize: bool = True,
    return_all: bool = False,
    library: Literal["fuzzywuzzy", "rapidfuzz"] = "rapidfuzz",
) -> Optional[MatchResult]: ...


@overload
def fuzzy_match(
    value: str,
    choices: Sequence[str],
    top_matches: int,
    threshold: int = 80,
    scorer: Optional[Callable] = None,
    normalize: bool = True,
    return_all: bool = False,
    library: Literal["fuzzywuzzy", "rapidfuzz"] = "rapidfuzz",
) -> List[MatchResult]: ...


# =========================================================
# 4) Função fuzzy match (com correções principais)
# =========================================================
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
) -> Union[Optional[MatchResult], List[MatchResult]]:
    """
    Retorna os melhores matches fuzzy.

    Regras:
      - top_matches == 1 -> MatchResult | None
      - top_matches > 1 -> List[MatchResult] (pode ser vazia)
      - return_all=False -> aplica threshold (filtra abaixo)
      - return_all=True  -> inclui também abaixo do threshold (bom pra debug)

    Obs importante (corrigido):
      - No RapidFuzz, se return_all=True, NÃO usamos score_cutoff,
        senão itens abaixo do threshold nem aparecem.
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

    # Se não tem query ou lista, devolve coerente com o modo
    if not value or not choices:
        return None if top_matches == 1 else []

    # -------------------------
    # Preparação das entradas
    # -------------------------
    original_choices: List[str] = list(choices)

    # Normaliza (ou não) query e choices
    if normalize:
        value_n = normalize_text(value)
        choices_n = [normalize_text(c) for c in original_choices]
    else:
        value_n = value
        choices_n = original_choices

    # Mapa para resolver índices de forma estável quando a lib não devolver idx
    # (e também para tratar duplicados)
    norm_to_indices: Dict[str, List[int]] = {}
    for i, c_norm in enumerate(choices_n):
        norm_to_indices.setdefault(c_norm, []).append(i)

    # -------------------------
    # Seleção da biblioteca
    # -------------------------
    raw_matches: List[Tuple[str, float, int]] = []

    if library == "fuzzywuzzy":
        # fuzzywuzzy normalmente retorna (match, score) e nem sempre inclui index
        from fuzzywuzzy import fuzz, process  # noqa: E402

        scorer = scorer or fuzz.token_sort_ratio

        extracted = process.extract(
            value_n,
            choices_n,
            scorer=scorer,
            limit=top_matches,
        )

        # Normaliza para formato comum: (match_norm, score_float, idx_int)
        # Se idx não vier, pegamos o primeiro índice mapeado (comportamento definido)
        for item in extracted:
            match_norm = item[0]
            score = float(item[1])
            if len(item) == 3:
                idx = int(item[2])
            else:
                idx = int(norm_to_indices.get(match_norm, [0])[0])
            raw_matches.append((match_norm, score, idx))

    else:
        # rapidfuzz geralmente retorna (match, score, idx)
        from rapidfuzz import fuzz, process  # noqa: E402

        scorer = scorer or fuzz.token_sort_ratio

        # Monta kwargs para permitir return_all funcionar
        extract_kwargs = dict(
            query=value_n,
            choices=choices_n,
            scorer=scorer,
            limit=top_matches,
        )

        # Só usamos score_cutoff quando NÃO queremos retornar abaixo do threshold
        if not return_all:
            extract_kwargs["score_cutoff"] = threshold

        extracted = process.extract(**extract_kwargs)

        # Normaliza para formato comum: (match_norm, score_float, idx_int)
        for item in extracted:
            match_norm, score, idx = item[0], float(item[1]), int(item[2])
            raw_matches.append((match_norm, score, idx))

    # -------------------------
    # Resultado estruturado
    # -------------------------
    results: List[MatchResult] = []

    for match_norm, score, idx in raw_matches:
        score_int = int(score)

        # Se return_all=False, filtra pelo threshold aqui (fuzzywuzzy não tem score_cutoff)
        if (score_int >= threshold) or return_all:
            results.append(
                MatchResult(
                    query=value,
                    query_normalized=value_n,
                    choice=original_choices[idx],
                    choice_normalized=choices_n[idx],
                    score=score_int,
                    index=idx,
                )
            )

    # -------------------------
    # Formato de retorno
    # -------------------------
    if top_matches == 1:
        return results[0] if results else None

    return results

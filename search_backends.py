"""
search_backends.py — Backends de búsqueda unificados para el pipeline GENIAL

Estrategia de búsqueda:
  1. Google (googlesearch-python) — primario: más fiable para site: y filetype:
  2. DuckDuckGo (ddgs/duckduckgo-search) — fallback: sin API key, cobertura amplia

Interfaz pública:
  multi_search(query, max_results, pause) → List[Dict]

Formato de retorno compatible con DDG (keys: href/url, title, body).
Cuando Google devuelve solo URLs (sin snippet), se rellena `body` con el
texto de la query para que los filtros downstream (topic_match) funcionen
correctamente, ya que la query ya contiene las palabras clave buscadas.
"""

import logging
import time
from typing import List, Dict, Optional

import urllib3
import config

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logger = logging.getLogger(__name__)


# ─── Backend: Google Search ───────────────────────────────────────────────────

def _google_search(
    query: str,
    max_results: int,
    pause: float,
    lang: str = "es",
) -> List[Dict]:
    """
    Búsqueda Google vía googlesearch-python.

    Devuelve lista de dicts {href, url, title, body} compatibles con el
    formato DDG.  body se rellena con el texto de la query para que los
    filtros temáticos downstream (topic_match) puedan operar.
    """
    try:
        from googlesearch import search as _gsearch
    except ImportError:
        logger.debug("[backends/google] googlesearch-python no instalado; omitiendo")
        return []

    try:
        urls = list(_gsearch(
            query,
            num_results=max_results,
            lang=lang,
            sleep_interval=int(pause),
            safe=None,
            ssl_verify=False,
        ))
    except Exception as e:
        logger.warning(f"[backends/google] Error en búsqueda: {e}")
        return []

    if not urls:
        logger.debug(f"[backends/google] Sin resultados: {query[:70]}")
        return []

    logger.debug(f"[backends/google] {len(urls)} URLs para: {query[:70]}")

    # Rellena title y body con la query para que los checks de AI/policy keywords
    # funcionen aun cuando Google no entrega snippet.
    return [
        {
            "href": u,
            "url": u,
            "title": "",
            "body": query,   # la query ya contiene las keywords de interés
        }
        for u in urls
    ]


# ─── Backend: DuckDuckGo ──────────────────────────────────────────────────────

def _ddg_search(
    query: str,
    max_results: int,
    retries: int = 3,
) -> List[Dict]:
    """
    Búsqueda DuckDuckGo con reintentos.

    Intenta primero `ddgs` (nueva API), luego `duckduckgo_search` (legacy).
    """
    DDGS = None
    for lib in ("ddgs", "duckduckgo_search"):
        try:
            if lib == "ddgs":
                from ddgs import DDGS as _DDGS
            else:
                from duckduckgo_search import DDGS as _DDGS
            DDGS = _DDGS
            break
        except ImportError:
            continue

    if DDGS is None:
        logger.error(
            "[backends/ddg] Ninguna librería DDG disponible. "
            "Instala: pip install 'duckduckgo-search>=4.4.3,<6.0.0'"
        )
        return []

    for attempt in range(retries):
        try:
            results = list(DDGS().text(query, max_results=max_results))
            if results:
                logger.debug(
                    f"[backends/ddg] {len(results)} resultados para: {query[:70]}"
                )
            return results
        except Exception as e:
            wait = 5 * (attempt + 1)
            logger.warning(
                f"[backends/ddg] Error (intento {attempt + 1}/{retries}): {e}. "
                f"Esperando {wait}s"
            )
            time.sleep(wait)

    logger.warning(f"[backends/ddg] Sin resultado tras {retries} intentos: {query[:70]}")
    return []


# ─── Interfaz pública ─────────────────────────────────────────────────────────

def multi_search(
    query: str,
    max_results: Optional[int] = None,
    pause: Optional[float] = None,
) -> List[Dict]:
    """
    Búsqueda con backend dual: Google primero, DDG como fallback.

    Args:
        query:       Texto de búsqueda.
        max_results: Número máximo de resultados (default: config.MAX_RESULTS_PER_QUERY).
        pause:       Pausa entre páginas Google en segundos (default: config.GOOGLE_SEARCH_PAUSE).

    Returns:
        Lista de dicts con keys href/url, title, body — compatible con el
        formato DDG usado en todo el pipeline.
    """
    if max_results is None:
        max_results = config.MAX_RESULTS_PER_QUERY

    if pause is None:
        pause = float(getattr(config, "GOOGLE_SEARCH_PAUSE", 2.5))

    use_google = getattr(config, "GOOGLE_AS_PRIMARY", True)

    if use_google:
        results = _google_search(query, max_results=max_results, pause=pause)
        if results:
            return results
        logger.debug("[backends] Google vacío → usando DDG fallback")

    return _ddg_search(query, max_results=max_results)

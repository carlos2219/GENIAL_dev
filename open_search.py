"""
open_search.py — FASE 3: Búsqueda abierta exploratoria

Ejecuta queries amplios sin restricción de dominio para detectar
documentos no indexados fácilmente en búsquedas site-specific.
"""

import logging
import time
from typing import List, Dict

import config
from url_filter import filter_and_rank, is_excluded

logger = logging.getLogger(__name__)


def _is_mexican_official_url(url: str) -> bool:
    """Verifica que la URL pertenezca a un dominio oficial mexicano (.gob.mx, .edu.mx o dominios prioritarios)."""
    url_l = url.lower()
    if ".gob.mx" in url_l or ".edu.mx" in url_l:
        return True
    return any(d and d in url_l for d in getattr(config, "GOVERNMENT_PRIORITY_DOMAINS", []))


def _topic_match(url: str, title: str, body: str) -> bool:
    """Filtro temático para reducir ruido en búsqueda abierta."""
    if not getattr(config, "STRICT_TOPIC_FILTER", False):
        return True

    combined = f"{url} {title} {body}".lower()
    ai_hits = sum(1 for kw in config.AI_KEYWORDS if kw in combined)
    policy_hits = sum(1 for kw in config.POLICY_KEYWORDS if kw in combined)

    if getattr(config, "TOPIC_MUST_INCLUDE_AI", True) and ai_hits == 0:
        return False

    min_policy = int(getattr(config, "TOPIC_MIN_POLICY_HITS", 1))
    return policy_hits >= min_policy


def _ddg_search(query: str, max_results: int = config.MAX_RESULTS_PER_QUERY) -> List[Dict]:
    try:
        from ddgs import DDGS
    except ImportError:
        try:
            from duckduckgo_search import DDGS
            logger.warning("[open_search] Usando duckduckgo_search legacy; instala 'ddgs'")
        except ImportError:
            logger.error("[open_search] ddgs no instalado. Ejecuta: pip install ddgs")
            return []

    for attempt in range(3):
        try:
            ddgs = DDGS()
            results = list(ddgs.text(query, max_results=max_results))
            return results
        except Exception as e:
            wait = 5 * (attempt + 1)
            logger.warning(f"[open_search] DDG error (intento {attempt+1}): {e}. Esperando {wait}s")
            time.sleep(wait)
    return []


def search_open() -> List[Dict]:
    """
    Ejecuta FASE 3 completa: búsquedas abiertas sin restricción de dominio.

    Retorna lista de documentos filtrados y rankeados.
    """
    logger.info("=" * 60)
    logger.info("FASE 3 — Búsqueda abierta exploratoria")
    logger.info("=" * 60)

    all_results: List[Dict] = []

    for query in config.OPEN_SEARCH_QUERIES:
        logger.info(f"[open_search] Query: {query}")
        raw = _ddg_search(query, max_results=config.MAX_RESULTS_PER_QUERY)

        for r in raw:
            url   = r.get("href", "") or r.get("url", "")
            title = r.get("title", "")
            body  = r.get("body", "")

            if not url or is_excluded(url):
                continue

            # Solo fuentes oficiales mexicanas (.gob.mx, .edu.mx o dominios prioritarios)
            if not _is_mexican_official_url(url):
                logger.debug(f"[open_search] Dominio no oficial descartado: {url[:60]}")
                continue

            if not _topic_match(url, title, body):
                continue

            all_results.append({
                "url": url,
                "title": title,
                "snippet": body[:400],
                "source_type": "open",
                "university_name": None,
                "university_domain": None,
                "query_used": query,
                "extracted_text": "",
                "extraction_error": None,
                "heuristic_score": 0.0,
                "heuristic_label": "BAJA",
                "ai_classification": None,
            })

        time.sleep(config.SEARCH_DELAY_SECONDS)

    logger.info(f"[open_search] Total crudo: {len(all_results)} resultados")

    filtered = filter_and_rank(all_results)
    logger.info(f"[open_search] Tras filtro: {len(filtered)} documentos")

    return filtered

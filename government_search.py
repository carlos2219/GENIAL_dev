"""
government_search.py — FASE 1: Búsqueda en fuentes gubernamentales

Combina:
  1. Búsqueda DDG con queries de normativa gubernamental mexicana
  2. Acceso directo a URLs semilla de portales de gobierno
"""

import logging
import time
from typing import List, Dict

import config
from url_filter import filter_and_rank, is_excluded, looks_normative

logger = logging.getLogger(__name__)


def _topic_match(url: str, title: str, body: str) -> bool:
    """Filtro temático para conservar normativa de IA y no normativa general."""
    if not getattr(config, "STRICT_TOPIC_FILTER", False):
        return True

    combined = f"{url} {title} {body}".lower()
    ai_hits = sum(1 for kw in config.AI_KEYWORDS if kw in combined)
    policy_hits = sum(1 for kw in config.POLICY_KEYWORDS if kw in combined)

    if getattr(config, "TOPIC_MUST_INCLUDE_AI", True) and ai_hits == 0:
        return False

    min_policy = int(getattr(config, "TOPIC_MIN_POLICY_HITS", 1))
    return policy_hits >= min_policy


# ─── DuckDuckGo helper ───────────────────────────────────────────────────────

def _ddg_search(query: str, max_results: int = config.MAX_RESULTS_PER_QUERY) -> List[Dict]:
    """Wrapper robusto sobre duckduckgo_search con reintentos."""
    try:
        from ddgs import DDGS
    except ImportError:
        try:
            from duckduckgo_search import DDGS
            logger.warning("[gov_search] Usando duckduckgo_search legacy; instala 'ddgs'")
        except ImportError:
            logger.error("[gov_search] ddgs no instalado. Ejecuta: pip install ddgs")
            return []

    for attempt in range(3):
        try:
            ddgs = DDGS()
            results = list(ddgs.text(query, max_results=max_results))
            return results
        except Exception as e:
            wait = 5 * (attempt + 1)
            logger.warning(f"[gov_search] DDG error (intento {attempt+1}): {e}. Esperando {wait}s")
            time.sleep(wait)
    return []


# ─── Crawl de URLs semilla gubernamentales ────────────────────────────────────

def _crawl_gov_seeds() -> List[Dict]:
    """Accede a portales gubernamentales y extrae enlaces relevantes."""
    from site_crawler import crawl_domain

    docs: List[Dict] = []
    for seed_url in config.GOVERNMENT_SEED_URLS:
        logger.info(f"[gov_search] Crawleando semilla: {seed_url}")
        results = crawl_domain(
            domain=seed_url,
            university_name="Gobierno de México",
            source_type="government",
            max_docs=8,
        )
        for d in results:
            if _topic_match(d.get("url", ""), d.get("title", ""), d.get("snippet", "")):
                docs.append(d)
        time.sleep(1.0)

    return docs


# ─── Búsquedas DDG gubernamentales ───────────────────────────────────────────

def _search_government_queries() -> List[Dict]:
    """Ejecuta queries de normativa gubernamental en DDG."""
    all_results: List[Dict] = []

    for query in config.GOVERNMENT_QUERIES:
        logger.info(f"[gov_search] Query: {query}")
        raw = _ddg_search(query)

        for r in raw:
            url   = r.get("href", "") or r.get("url", "")
            title = r.get("title", "")
            body  = r.get("body", "")

            if not url or is_excluded(url):
                continue

            # Priorizar dominios gubernamentales
            is_gov = any(dom in url.lower() for dom in config.GOVERNMENT_PRIORITY_DOMAINS)
            if not is_gov:
                # En fase gubernamental descartamos resultados fuera de dominios prioritarios
                # para evitar ruido de prensa y contenido no normativo.
                continue

            if not _topic_match(url, title, body):
                continue

            all_results.append({
                "url": url,
                "title": title,
                "snippet": body[:400],
                "source_type": "government",
                "university_name": None,
                "university_domain": None,
                "query_used": query,
                "is_gov_domain": is_gov,
                "extracted_text": "",
                "extraction_error": None,
                "heuristic_score": 0.0,
                "heuristic_label": "BAJA",
                "ai_classification": None,
            })

        time.sleep(config.SEARCH_DELAY_SECONDS)

    return all_results


# ─── Punto de entrada ─────────────────────────────────────────────────────────

def search_government_sources() -> List[Dict]:
    """
    Ejecuta la FASE 1 completa: queries DDG + crawl de semillas.

    Retorna lista de documentos filtrados y rankeados.
    """
    logger.info("=" * 60)
    logger.info("FASE 1 — Búsqueda gubernamental")
    logger.info("=" * 60)

    # Búsqueda en DDG
    query_docs = _search_government_queries()
    logger.info(f"[gov_search] DDG: {len(query_docs)} resultados crudos")

    # Crawl de semillas
    seed_docs = _crawl_gov_seeds()
    logger.info(f"[gov_search] Semillas: {len(seed_docs)} URLs de portales gov")

    all_docs = query_docs + seed_docs

    # Filtrar y rankear
    filtered = filter_and_rank(all_docs)
    logger.info(f"[gov_search] Tras filtro: {len(filtered)} documentos")

    return filtered

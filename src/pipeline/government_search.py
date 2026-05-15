"""
government_search.py — FASE 1: Búsqueda en fuentes gubernamentales

Combina:
  1. Búsqueda Google (primario) / DDG (fallback) con queries de normativa gubernamental mexicana
  2. Rastreo heurístico de URLs semilla de portales de gobierno
"""

import logging
import time
from typing import List, Dict

import config
from .url_filter import filter_and_rank, is_excluded, looks_normative
from .search_backends import multi_search

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


# ─── Búsquedas gubernamentales ───────────────────────────────────────────────

def _search_government_queries() -> List[Dict]:
    """Ejecuta queries de normativa gubernamental (Google→DDG fallback)."""
    all_results: List[Dict] = []

    for query in config.GOVERNMENT_QUERIES:
        logger.info(f"[gov_search] Query: {query}")
        raw = multi_search(query, query_type="gov")

        for r in raw:
            url   = r.get("href", "") or r.get("url", "")
            title = r.get("title", "")
            body  = r.get("body", "")

            if not url or is_excluded(url):
                continue

            # Priorizar dominios gubernamentales
            if not config._is_official_url(url):
                # En fase gubernamental descartamos resultados fuera de dominios prioritarios
                # para evitar ruido de prensa y contenido no normativo.
                continue
            is_gov = True

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


# ─── Crawl de URLs semilla gubernamentales ────────────────────────────────────


def _crawl_gov_seeds() -> List[Dict]:
    """Rastrea semillas gubernamentales y extrae enlaces relevantes."""
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
            url = d.get("url", "")
            if not url or is_excluded(url):
                continue
            # Solo filtrar por keywords normativas; NO requerir keywords de IA en este
            # punto porque el contenido aún no ha sido extraído. El clasificador
            # heurístico aplicará el gate de IA después de la extracción.
            combined = (url + " " + d.get("title", "")).lower()
            policy_hits = sum(1 for kw in config.PRIORITY_URL_KEYWORDS if kw in combined)
            if policy_hits >= 1 or url.lower().endswith(".pdf"):
                docs.append(d)
        time.sleep(1.0)

    return docs

def search_government_sources() -> List[Dict]:
    """
    Ejecuta la FASE 1 completa: queries (Google→DDG) + crawl de semillas.

    Retorna lista de documentos filtrados y rankeados.
    """
    logger.info("=" * 60)
    logger.info("FASE 1 — Búsqueda gubernamental")
    logger.info("=" * 60)

    # Búsqueda Google→DDG
    query_docs = _search_government_queries()
    logger.info(f"[gov_search] Queries: {len(query_docs)} resultados crudos")

    # Crawl de semillas
    seed_docs = _crawl_gov_seeds()
    logger.info(f"[gov_search] Semillas: {len(seed_docs)} URLs de portales gov")

    all_docs = query_docs + seed_docs

    # Filtrar y rankear
    filtered = filter_and_rank(all_docs)
    logger.info(f"[gov_search] Tras filtro: {len(filtered)} documentos")

    return filtered

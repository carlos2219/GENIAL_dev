"""
open_search.py — FASE 3: Búsqueda abierta exploratoria

Ejecuta queries amplios sin restricción de dominio para detectar
documentos no indexados fácilmente en búsquedas site-specific.

Mejoras v3:
  - Google Search (googlesearch-python) como backend primario
  - DuckDuckGo como fallback cuando Google no devuelve resultados
  - Búsqueda directa en el DOF con adaptador SSL robusto (NoVerifyAdapter)
  - Queries adicionales para repositorios universitarios de acceso abierto
  - Queries adicionales para portales de transparencia institucional
"""

import logging
import random
import time
from typing import List, Dict

import requests
from requests.adapters import HTTPAdapter
from bs4 import BeautifulSoup
import urllib3

import config
from .url_filter import filter_and_rank, is_excluded
from .search_backends import multi_search

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class _NoVerifyAdapter(HTTPAdapter):
    """HTTPAdapter que desactiva verificación TLS para dominios con cert problemático."""
    def send(self, request, **kwargs):
        kwargs["verify"] = False
        return super().send(request, **kwargs)


def _make_dof_session(headers: dict) -> requests.Session:
    """Crea una sesión requests con SSL desactivado específicamente para dof.gob.mx."""
    session = requests.Session()
    session.mount("https://dof.gob.mx", _NoVerifyAdapter())
    session.mount("http://dof.gob.mx", _NoVerifyAdapter())
    session.headers.update(headers)
    return session

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





def _dof_direct_search() -> List[Dict]:
    """
    Consulta directamente el buscador del Diario Oficial de la Federación
    para encontrar acuerdos, decretos y lineamientos sobre inteligencia artificial.

    Retorna lista de documentos en formato estándar.
    """
    if not getattr(config, "DOF_DIRECT_SEARCH_ENABLED", False):
        return []

    base_url = getattr(config, "DOF_SEARCH_BASE_URL", "https://dof.gob.mx/busqueda_detalle.php")
    terms    = getattr(config, "DOF_SEARCH_TERMS", [])
    year_start = getattr(config, "DOF_SEARCH_YEAR_START", "2018-01-01")
    max_results = int(getattr(config, "DOF_SEARCH_MAX_RESULTS", 30))

    logger.info(f"[open_search/DOF] Búsqueda directa en DOF con {len(terms)} términos")

    results: List[Dict] = []
    seen_urls: set = set()

    for term in terms:
        params = {
            "texto": term,
            "busquedaSearchButton": "Search",
            "tipo_publicacion": "0",
            "fecha_inicio": year_start,
            "fecha_fin": "2026-12-31",
            "codigo": "",
        }
        try:
            headers = {"User-Agent": random.choice(config.USER_AGENTS)}
            session = _make_dof_session(headers)
            resp = session.get(
                base_url, params=params,
                timeout=max(config.REQUEST_TIMEOUT, 20),
            )
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")

            # DOF search results: links to nota_detalle.php or direct PDF links
            for link in soup.find_all("a", href=True):
                href = str(link.get("href", "")).strip()
                if not href:
                    continue

                # Normalizar URL
                if href.startswith("http"):
                    full_url = href
                elif href.startswith("/"):
                    full_url = f"https://dof.gob.mx{href}"
                else:
                    full_url = f"https://dof.gob.mx/{href}"

                # Solo páginas del DOF
                if "dof.gob.mx" not in full_url:
                    continue

                # Solo nota_detalle o PDFs; omitir menús y anclas
                if "nota_detalle" not in full_url and not full_url.endswith(".pdf"):
                    continue

                norm_url = full_url.split("?")[0] if "nota_detalle" not in full_url else full_url
                if norm_url in seen_urls:
                    continue
                seen_urls.add(norm_url)

                title = link.get_text(strip=True) or f"DOF — {term}"
                if len(title) < 5:
                    continue

                results.append({
                    "url": full_url,
                    "title": title,
                    "snippet": f"Diario Oficial de la Federación — búsqueda: {term}",
                    "source_type": "open_dof",
                    "university_name": None,
                    "university_domain": None,
                    "query_used": f"DOF:{term}",
                    "extracted_text": "",
                    "extraction_error": None,
                    "heuristic_score": 0.0,
                    "heuristic_label": "BAJA",
                    "ai_classification": None,
                })

                if len(results) >= max_results:
                    break

            logger.info(f"[open_search/DOF] '{term}': {len(results)} docs acumulados")
            time.sleep(config.SEARCH_DELAY_SECONDS * 2)

        except requests.exceptions.RequestException as e:
            logger.warning(f"[open_search/DOF] HTTP error para '{term}': {e}")
        except Exception as e:
            logger.warning(f"[open_search/DOF] Error inesperado para '{term}': {e}")

    logger.info(f"[open_search/DOF] Total obtenido: {len(results)} documentos DOF")
    return results


def search_open() -> List[Dict]:
    """
    Ejecuta FASE 3 completa: búsquedas abiertas sin restricción de dominio.

    Incluye:
      - Queries Google (primario) + DDG (fallback) para cada query
      - Búsqueda directa en el DOF via HTTP (con adaptador SSL robusto)

    Retorna lista de documentos filtrados y rankeados.
    """
    logger.info("=" * 60)
    logger.info("FASE 3 — Búsqueda abierta exploratoria (v3: Google + DDG fallback)")
    logger.info("=" * 60)

    all_results: List[Dict] = []

    # ── 3a. Queries Google/DDG (incluye site:dof.gob.mx, repositorios, transparencia) ──
    logger.info(f"[open_search] Ejecutando {len(config.OPEN_SEARCH_QUERIES)} queries (Google→DDG fallback)")
    for query in config.OPEN_SEARCH_QUERIES:
        logger.info(f"[open_search] Query: {query}")
        raw = multi_search(query, max_results=config.MAX_RESULTS_PER_QUERY)

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

    logger.info(f"[open_search] DDG crudo: {len(all_results)} resultados")

    # ── 3b. Búsqueda directa en el DOF ─────────────────────────────────────
    dof_results = _dof_direct_search()
    # Los resultados DOF ya son dof.gob.mx → siempre pasan el filtro de dominio
    for r in dof_results:
        if not _topic_match(r["url"], r["title"], r["snippet"]):
            continue
        all_results.append(r)

    logger.info(f"[open_search] Total crudo (DDG + DOF directo): {len(all_results)} resultados")

    filtered = filter_and_rank(all_results)
    logger.info(f"[open_search] Tras filtro: {len(filtered)} documentos")

    return filtered

"""
search_backends.py — Backends de búsqueda unificados para el pipeline GENIAL

Estrategia de búsqueda (en orden de prioridad):
  1. Google Custom Search API (CSE) — funciona desde cualquier IP incluyendo GCP.
     Requiere GOOGLE_CSE_API_KEY y GOOGLE_CSE_ID en el entorno.
     100 consultas/día gratis; $5/1000 adicionales.
  2. Brave Search API — busca toda la web, funciona desde GCP, 2000 queries/mes gratis.
     Requiere BRAVE_API_KEY en el entorno.
     Obtener en: https://api.search.brave.com/
  3. googlesearch-python — scraping HTML de Google. Solo funciona en IPs locales/residenciales.
     Activado cuando GOOGLE_AS_PRIMARY=true y no hay CSE/Brave configurado.
  4. DuckDuckGo (ddgs / duckduckgo-search) — fallback sin API key.

Interfaz pública:
  multi_search(query, max_results, pause) → List[Dict]

Formato de retorno: dicts con keys href/url, title, body.
"""

import logging
import time
from typing import List, Dict, Optional

import requests
import urllib3
import config

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logger = logging.getLogger(__name__)


# ─── Backend 1: Google Custom Search API (CSE) ───────────────────────────────

def _google_cse_search(query: str, max_results: int) -> List[Dict]:
    """
    Búsqueda vía Google Custom Search JSON API.

    Funciona desde cualquier IP (incluyendo GCP). Requiere:
      - GOOGLE_CSE_API_KEY: API key de Google Cloud (con Custom Search API habilitada)
      - GOOGLE_CSE_ID:      ID del motor de búsqueda programable (cx)

    Configuración del CSE:
      1. Ir a https://programmablesearchengine.google.com/
      2. Crear motor → activar "Buscar en toda la web"
      3. Copiar el Search Engine ID (cx)
      4. En https://console.cloud.google.com/ → APIs → habilitar "Custom Search API"
      5. Credenciales → crear API Key → copiarla

    Límites: 100 consultas/día gratis. $5 por cada 1000 adicionales.
    """
    api_key = getattr(config, "GOOGLE_CSE_API_KEY", "")
    cse_id  = getattr(config, "GOOGLE_CSE_ID", "")

    if not api_key or not cse_id:
        return []

    endpoint = "https://www.googleapis.com/customsearch/v1"
    results: List[Dict] = []
    start = 1

    while len(results) < max_results:
        fetch = min(10, max_results - len(results))  # CSE devuelve máx 10 por página
        params = {
            "key": api_key,
            "cx":  cse_id,
            "q":   query,
            "num": fetch,
            "start": start,
            "lr":  "lang_es",
        }
        try:
            resp = requests.get(endpoint, params=params, timeout=15)
            if resp.status_code == 429:
                logger.warning("[backends/cse] Cuota diaria agotada (429). Cambiando a fallback.")
                break
            if resp.status_code == 400:
                logger.warning(f"[backends/cse] Error 400 — verifica GOOGLE_CSE_API_KEY y GOOGLE_CSE_ID")
                break
            resp.raise_for_status()
        except requests.RequestException as e:
            logger.warning(f"[backends/cse] HTTP error: {e}")
            break

        data  = resp.json()
        items = data.get("items", [])
        if not items:
            break

        for item in items:
            results.append({
                "href":  item.get("link", ""),
                "url":   item.get("link", ""),
                "title": item.get("title", ""),
                "body":  item.get("snippet", query),
                "_backend_tag": "cse",
            })

        start += len(items)
        if start > 91 or len(items) < fetch:  # CSE admite hasta start=91 (resultados 91-100)
            break

    if results:
        logger.info(f"[backends/cse] {len(results)} resultados para: {query[:70]}")
    return results[:max_results]


# ─── Backend 2: Brave Search API ────────────────────────────────────────────

def _brave_search(query: str, max_results: int) -> List[Dict]:
    """
    Búsqueda vía Brave Search API.

    Funciona desde cualquier IP (incluyendo GCP). Requiere:
      - BRAVE_API_KEY: token de suscripción de https://api.search.brave.com/

    Plan gratuito: 2000 queries/mes (suficiente para una sesión completa del pipeline).
    """
    api_key = getattr(config, "BRAVE_API_KEY", "")
    if not api_key:
        return []

    endpoint = "https://api.search.brave.com/res/v1/web/search"
    results: List[Dict] = []
    offset = 0

    while len(results) < max_results:
        fetch = min(20, max_results - len(results))  # Brave devuelve máx 20 por página
        params = {
            "q":           query,
            "count":       fetch,
            "offset":      offset,
            "country":     "MX",
            "search_lang": "es",
            "text_decorations": 0,
        }
        headers = {
            "Accept":             "application/json",
            "Accept-Encoding":    "gzip",
            "X-Subscription-Token": api_key,
        }
        try:
            resp = requests.get(endpoint, params=params, headers=headers, timeout=15)
            if resp.status_code == 429:
                logger.warning("[backends/brave] Cuota mensual agotada (429). Cambiando a fallback.")
                break
            if resp.status_code in (401, 403):
                logger.warning(f"[backends/brave] Error de autenticación ({resp.status_code}) — verifica BRAVE_API_KEY")
                break
            resp.raise_for_status()
        except requests.RequestException as e:
            logger.warning(f"[backends/brave] HTTP error: {e}")
            break

        web = resp.json().get("web", {})
        items = web.get("results", [])
        if not items:
            break

        for item in items:
            results.append({
                "href":  item.get("url", ""),
                "url":   item.get("url", ""),
                "title": item.get("title", ""),
                "body":  item.get("description", query),
                "_backend_tag": "brave",
            })

        offset += len(items)
        if len(items) < fetch:
            break

    if results:
        logger.info(f"[backends/brave] {len(results)} resultados para: {query[:70]}")
    return results[:max_results]


# ─── Backend 3: Serper.dev (Google proxy) ────────────────────────────────────

def _serper_search(query: str, max_results: int, country: str = "MX") -> List[Dict]:
    """
    Búsqueda vía Serper.dev — proxy de Google Search.

    Funciona desde cualquier IP (incluyendo GCP). Requiere:
      - SERPER_API_KEY: obtenida en https://serper.dev

    Plan Basic: 2500/mes gratis; $50/mes = 50k queries.
    """
    api_key = getattr(config, "SERPER_API_KEY", "")
    if not api_key:
        return []

    country_cfg = getattr(config, "LATAM_COUNTRIES", {}).get(country, {})
    gl = country_cfg.get("serper_gl", "mx")
    hl = country_cfg.get("lang", "es")

    endpoint = "https://google.serper.dev/search"
    headers = {"X-API-KEY": api_key, "Content-Type": "application/json"}
    payload = {"q": query, "num": min(max_results, 100), "gl": gl, "hl": hl}

    try:
        resp = requests.post(endpoint, json=payload, headers=headers, timeout=15)
        if resp.status_code == 401:
            logger.warning("[backends/serper] API key inválida — verifica SERPER_API_KEY")
            return []
        if resp.status_code == 429:
            logger.warning("[backends/serper] Cuota agotada (429). Cambiando a fallback.")
            return []
        resp.raise_for_status()
    except requests.RequestException as e:
        logger.warning(f"[backends/serper] HTTP error: {e}")
        return []

    results = []
    for item in resp.json().get("organic", [])[:max_results]:
        results.append({
            "href":  item.get("link", ""),
            "url":   item.get("link", ""),
            "title": item.get("title", ""),
            "body":  item.get("snippet", query),
            "_backend_tag": "serper",
        })

    if results:
        logger.info(f"[backends/serper] {len(results)} resultados para: {query[:70]}")
    return results


# ─── Backend 4: googlesearch-python (scraping HTML) ───────────────────────────

def _google_scrape_search(query: str, max_results: int, pause: float) -> List[Dict]:
    """
    Búsqueda Google vía scraping HTML (googlesearch-python).
    Solo funciona en IPs residenciales/locales. Bloqueado en GCP/AWS.
    """
    try:
        from googlesearch import search as _gsearch
    except ImportError:
        logger.debug("[backends/google-scrape] googlesearch-python no instalado; omitiendo")
        return []

    try:
        urls = list(_gsearch(
            query,
            num_results=max_results,
            lang="es",
            sleep_interval=int(pause),
            safe=None,
            ssl_verify=False,
        ))
    except Exception as e:
        logger.warning(f"[backends/google-scrape] Error en búsqueda: {e}")
        return []

    if not urls:
        return []

    logger.debug(f"[backends/google-scrape] {len(urls)} URLs para: {query[:70]}")
    return [
        {"href": u, "url": u, "title": "", "body": query, "_backend_tag": "google_scrape"}
        for u in urls
    ]


# ─── Backend 4: DuckDuckGo ───────────────────────────────────────────────────

def _ddg_search(query: str, max_results: int, retries: int = 3) -> List[Dict]:
    """Búsqueda DuckDuckGo con reintentos. Fallback final."""
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
            for r in results:
                r.setdefault("_backend_tag", "ddg")
            if results:
                logger.debug(f"[backends/ddg] {len(results)} resultados para: {query[:70]}")
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
    query_type: Optional[str] = None,
) -> List[Dict]:
    """
    Public entry point — delegates to phase-aware router when SEARCH_ROUTER_ENABLED=true,
    falls back to legacy cascade otherwise. query_type: 'gov' | 'site' | 'open' | None.
    """
    from .search_router import router_search  # lazy: avoids circular import at module load
    return router_search(query, query_type=query_type, max_results=max_results, pause=pause)


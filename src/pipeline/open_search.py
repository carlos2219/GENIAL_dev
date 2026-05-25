"""
open_search.py — FASE 3: Búsqueda normativa institucional universitaria

Para cada universidad del CSV ejecuta dos fórmulas de búsqueda:
  1. site:{domain} "inteligencia artificial" AND (lineamientos OR política OR resolución OR guía)
  2. "{nombre}" México "IA" (ética OR "uso académico" OR regulación OR "pedagógico")

Complementa con búsqueda directa en el DOF.
"""

import logging
import random
import time
from pathlib import Path
from typing import List, Dict
from urllib.parse import urlparse

import pandas as pd
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


def _is_official_url_for_active_countries(url: str) -> bool:
    """Verifica que la URL pertenezca a un dominio oficial usando config._is_official_url."""
    return config._is_official_url(url)


def _matches_site_query(url: str, query: str) -> bool:
    """Para queries site:dominio, acepta cualquier URL del dominio objetivo."""
    import re
    from urllib.parse import urlparse
    m = re.search(r'site:(\S+)', query.lower())
    if not m:
        return False
    site_domain = m.group(1).rstrip("/")
    try:
        host = urlparse(url).netloc.lower().lstrip("www.")
        return host == site_domain or host.endswith("." + site_domain)
    except Exception:
        return False


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


def _extract_domain(url_str: str) -> str:
    """Extrae dominio limpio (sin www) de una URL."""
    if not url_str or url_str in ("nan", ""):
        return ""
    if not url_str.startswith("http"):
        url_str = "https://" + url_str
    try:
        netloc = urlparse(url_str).netloc.lower().lstrip("www.")
        return netloc if len(netloc) > 4 else ""
    except Exception:
        return ""


def _load_universities() -> pd.DataFrame:
    """Carga el CSV de universidades y retorna columnas universidad + url_oficial."""
    df = pd.read_csv(config.CSV_PATH, encoding="utf-8")
    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]
    df["universidad"] = df["universidad"].fillna("").astype(str).str.strip()
    df["url_oficial"] = df.get("url_oficial", pd.Series(dtype=str)).fillna("").astype(str).str.strip()
    df.loc[df["url_oficial"] == "nan", "url_oficial"] = ""
    return df


def search_open(max_unis: int = None) -> List[Dict]:
    """
    FASE 3 — Búsqueda normativa institucional por universidad.

    Para cada universidad del CSV ejecuta:
      Fórmula 1 (site:): site:{domain} "inteligencia artificial" AND
                         (lineamientos OR política OR resolución OR guía)
      Fórmula 2 (nombre): "{nombre}" México "IA"
                          (ética OR "uso académico" OR regulación OR "pedagógico")

    Complementa con búsqueda directa en el DOF.

    Args:
        max_unis: limita el número de universidades procesadas (útil para pruebas).
    """
    logger.info("=" * 60)
    logger.info("FASE 3 — Búsqueda normativa institucional universitaria (v4)")
    logger.info("=" * 60)

    df = _load_universities()
    if max_unis:
        df = df.head(max_unis)
        logger.info(f"[open_search] Modo prueba: limitado a {max_unis} universidades")

    # Deduplicar por dominio para evitar queries redundantes
    seen_domains: set = set()
    seen_urls: set = set()
    all_results: List[Dict] = []

    total = len(df)
    logger.info(f"[open_search] {total} universidades en CSV")

    for idx, row in df.iterrows():
        name = row.get("universidad", "").strip()
        url_oficial = str(row.get("url_oficial", "") or "").strip()
        domain = _extract_domain(url_oficial)

        queries: List[tuple] = []  # (query_str, query_type, domain_for_filter)

        # ── Fórmula 1: site: search (solo si tiene URL y dominio nuevo) ────────
        if domain and domain not in seen_domains:
            seen_domains.add(domain)
            q1 = (
                f'site:{domain} "inteligencia artificial" AND '
                f'(lineamientos OR política OR resolución OR guía)'
            )
            queries.append((q1, "site", domain))

        # ── Fórmula 2: búsqueda por nombre ─────────────────────────────────────
        if name and len(name) > 3:
            q2 = (
                f'"{name}" México "IA" '
                f'(ética OR "uso académico" OR regulación OR "pedagógico")'
            )
            queries.append((q2, "open", domain))

        for query, qtype, uni_domain in queries:
            logger.debug(f"[open_search] {name[:40]} — {query[:100]}")
            raw = multi_search(
                query,
                max_results=config.MAX_RESULTS_PER_QUERY,
                query_type=qtype,
            )

            for r in raw:
                url   = r.get("href", "") or r.get("url", "")
                title = r.get("title", "")
                body  = r.get("body", "")

                if not url or is_excluded(url) or url in seen_urls:
                    continue

                # Filtro de dominio:
                #   - site: queries → aceptar solo URLs del dominio consultado
                #   - nombre queries → aceptar dominios .mx u oficiales
                if qtype == "site":
                    try:
                        result_host = urlparse(url).netloc.lower().lstrip("www.")
                        if not (uni_domain and (
                            result_host == uni_domain
                            or result_host.endswith("." + uni_domain)
                        )):
                            continue
                    except Exception:
                        continue
                else:
                    try:
                        result_host = urlparse(url).netloc.lower()
                        if not (result_host.endswith(".mx")
                                or _is_official_url_for_active_countries(url)):
                            logger.debug(f"[open_search] Dominio no .mx descartado: {url[:60]}")
                            continue
                    except Exception:
                        continue

                seen_urls.add(url)
                all_results.append({
                    "url": url,
                    "title": title,
                    "snippet": body[:400],
                    "source_type": "open",
                    "university_name": name,
                    "university_domain": uni_domain,
                    "query_used": query,
                    "extracted_text": "",
                    "extraction_error": None,
                    "heuristic_score": 0.0,
                    "heuristic_label": "BAJA",
                    "ai_classification": None,
                })

            time.sleep(config.SEARCH_DELAY_SECONDS)

        if (idx + 1) % 100 == 0 or (idx + 1) == total:
            logger.info(
                f"[open_search] Progreso: {idx + 1}/{total} universidades — "
                f"{len(all_results)} docs acumulados"
            )

    logger.info(f"[open_search] Crudo universidad: {len(all_results)} resultados")

    # ── Búsqueda directa en el DOF ──────────────────────────────────────────
    dof_results = _dof_direct_search()
    for r in dof_results:
        if r["url"] not in seen_urls:
            all_results.append(r)
            seen_urls.add(r["url"])

    logger.info(f"[open_search] Total crudo (universidades + DOF): {len(all_results)} resultados")

    filtered = filter_and_rank(all_results)
    logger.info(f"[open_search] Tras filtro: {len(filtered)} documentos")

    return filtered

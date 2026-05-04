"""
university_search.py — FASE 2: Búsqueda en universidades

Para cada universidad del CSV:
  a) Búsqueda externa DDG con site: operator
  b) Crawling interno de rutas normativas conocidas
"""

import logging
import time
from typing import List, Dict, Optional
from urllib.parse import urlparse

import pandas as pd

import config
from url_filter import filter_and_rank, is_excluded
from site_crawler import crawl_domain

logger = logging.getLogger(__name__)


# ─── Carga del CSV ────────────────────────────────────────────────────────────

def load_universities(csv_path=config.CSV_PATH) -> pd.DataFrame:
    """
    Carga y limpia el CSV de universidades.
    Deduplica por url_oficial (dominios únicos).
    """
    df = pd.read_csv(csv_path, encoding="utf-8")
    # Normalizar columnas
    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]

    # Asegurar columna url_oficial
    if "url_oficial" not in df.columns:
        df["url_oficial"] = ""

    df["url_oficial"] = df["url_oficial"].fillna("").astype(str).str.strip()
    df["universidad"]  = df["universidad"].fillna("").astype(str).str.strip()

    # Extraer dominio limpio
    df["_domain"] = df["url_oficial"].apply(_extract_domain)

    # Quitar universidades sin dominio válido
    valid = df[df["_domain"].str.len() > 4].copy()

    # Deduplicar por dominio (un dominio puede aparecer varias veces en el CSV)
    valid = valid.drop_duplicates(subset=["_domain"])

    logger.info(f"[uni_search] {len(valid)} universidades con dominio válido de {len(df)} filas")
    return valid.reset_index(drop=True)


def _extract_domain(url: str) -> str:
    """Extrae netloc limpio de una URL."""
    if not url or url in ("nan", ""):
        return ""
    if not url.startswith("http"):
        url = "https://" + url
    try:
        return urlparse(url).netloc.lower().replace("www.", "")
    except Exception:
        return ""


# ─── DDG helper ───────────────────────────────────────────────────────────────

def _ddg_search(query: str, max_results: int = config.MAX_RESULTS_PER_QUERY) -> List[Dict]:
    try:
        from ddgs import DDGS
    except ImportError:
        try:
            # Compatibilidad temporal si solo está instalado el paquete antiguo
            from duckduckgo_search import DDGS
            logger.warning("[uni_search] Usando duckduckgo_search legacy; instala 'ddgs' para evitar warnings")
        except ImportError:
            logger.error("[uni_search] ddgs no instalado. Ejecuta: pip install ddgs")
            return []

    for attempt in range(3):
        try:
            ddgs = DDGS()
            results = list(ddgs.text(query, max_results=max_results))
            return results
        except Exception as e:
            wait = 5 * (attempt + 1)
            logger.warning(f"[uni_search] DDG error (intento {attempt+1}): {e}. Esperando {wait}s")
            time.sleep(wait)
    return []


# ─── Búsqueda externa por universidad ────────────────────────────────────────

def _search_university_ddg(name: str, domain: str) -> List[Dict]:
    """Ejecuta queries DDG con site: operator para una universidad."""
    docs: List[Dict] = []

    for template in config.UNIVERSITY_QUERY_TEMPLATES:
        query = template.format(name=name, domain=domain)
        logger.debug(f"[uni_search] {name} — query: {query}")

        raw = _ddg_search(query, max_results=config.MAX_RESULTS_PER_QUERY)
        for r in raw:
            url   = r.get("href", "") or r.get("url", "")
            title = r.get("title", "")
            body  = r.get("body", "")

            if not url or is_excluded(url):
                continue

            docs.append({
                "url": url,
                "title": title,
                "snippet": body[:400],
                "source_type": "university",
                "university_name": name,
                "university_domain": domain,
                "query_used": query,
                "extracted_text": "",
                "extraction_error": None,
                "heuristic_score": 0.0,
                "heuristic_label": "BAJA",
                "ai_classification": None,
            })

        time.sleep(config.SEARCH_DELAY_SECONDS)

    return docs


# ─── Procesamiento de una universidad ────────────────────────────────────────

def _process_university(row: pd.Series) -> List[Dict]:
    """Combina búsqueda DDG + crawl para una universidad."""
    name   = row.get("universidad", "")
    url    = row.get("url_oficial", "")
    domain = row.get("_domain", "")

    if not domain:
        return []

    is_priority = bool(row.get("is_priority", False))
    max_urls    = config.MAX_URLS_PRIORITY_UNIVERSITY if is_priority else config.MAX_URLS_PER_UNIVERSITY
    priority_tag = " [PRIORITARIA]" if is_priority else ""

    logger.info(f"[uni_search] Procesando: {name} ({domain}){priority_tag}")

    # a) Búsqueda externa
    ddg_docs = _search_university_ddg(name, domain)

    # b) Crawling interno
    base_url = url if url.startswith("http") else f"https://{domain}"
    crawl_docs = crawl_domain(
        domain=base_url,
        university_name=name,
        source_type="university",
        max_docs=max_urls,
    )

    return ddg_docs + crawl_docs


# ─── Punto de entrada ─────────────────────────────────────────────────────────

def search_universities(universities_df: Optional[pd.DataFrame] = None) -> List[Dict]:
    """
    Ejecuta FASE 2 completa para todas las universidades del CSV.

    Retorna lista de documentos filtrados y rankeados.
    """
    logger.info("=" * 60)
    logger.info("FASE 2 — Búsqueda en universidades")
    logger.info("=" * 60)

    if universities_df is None:
        universities_df = load_universities()

    # ── Preponer universidades prioritarias ──────────────────────────────────
    priority_df = pd.DataFrame(config.PRIORITY_UNIVERSITIES)
    priority_df["_domain"]     = priority_df["url_oficial"].apply(_extract_domain)
    priority_df["is_priority"] = True
    priority_df = priority_df[priority_df["_domain"].str.len() > 4].copy()
    priority_domains = set(priority_df["_domain"].tolist())

    # Quitar del CSV las que ya están en la lista prioritaria (evitar duplicados)
    universities_df = universities_df[~universities_df["_domain"].isin(priority_domains)].copy()
    universities_df["is_priority"] = False

    # Combinar: prioritarias primero, luego el resto del CSV
    combined_df = pd.concat([priority_df, universities_df], ignore_index=True)
    logger.info(f"[uni_search] {len(priority_df)} universidades prioritarias + {len(universities_df)} del CSV")

    # Aplicar límite de universidades si está configurado
    if config.MAX_UNIVERSITIES:
        combined_df = combined_df.head(config.MAX_UNIVERSITIES)
        logger.info(f"[uni_search] Límite aplicado: {config.MAX_UNIVERSITIES} universidades")

    all_docs: List[Dict] = []
    total_unis = len(combined_df)
    fase2_start = time.time()
    uni_times: List[float] = []

    for i, (idx, row) in enumerate(combined_df.iterrows(), start=1):
        uni_start = time.time()
        docs = _process_university(row)
        all_docs.extend(docs)
        uni_elapsed = time.time() - uni_start
        uni_times.append(uni_elapsed)

        # ── Indicador de progreso ──────────────────────────────────────────
        pct = i / total_unis * 100
        elapsed_total = time.time() - fase2_start
        avg_per_uni = elapsed_total / i
        remaining = avg_per_uni * (total_unis - i)
        elapsed_min = int(elapsed_total // 60)
        elapsed_sec = int(elapsed_total % 60)
        eta_min = int(remaining // 60)
        eta_sec = int(remaining % 60)
        logger.info(
            f"[PROGRESO FASE 2] {i}/{total_unis} universidades ({pct:.0f}%) — "
            f"Transcurrido: {elapsed_min}m{elapsed_sec:02d}s — "
            f"ETA: ~{eta_min}m{eta_sec:02d}s — "
            f"Docs acumulados: {len(all_docs)}"
        )

        # Pausa entre universidades
        time.sleep(0.5)

    logger.info(f"[uni_search] Total crudo: {len(all_docs)} documentos")

    filtered = filter_and_rank(all_docs)
    logger.info(f"[uni_search] Tras filtro: {len(filtered)} documentos")

    return filtered

"""
university_search.py — FASE 2: Búsqueda en universidades

Para cada universidad del CSV:
  a) Búsqueda externa Google (primario) / DDG (fallback) con site: operator
  b) Rastreo heurístico de rutas normativas conocidas y página raíz
"""

import hashlib
import json
import logging
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import List, Dict, Optional
from urllib.parse import urlparse

import pandas as pd

import config
from url_filter import filter_and_rank, is_excluded
from site_crawler import crawl_domain
from search_backends import multi_search as _multi_search

logger = logging.getLogger(__name__)

# ─── DDG rate-limit y caché ───────────────────────────────────────────────────
# Semáforo: garantiza que solo un hilo hace queries DDG a la vez.
# El delay dentro del semáforo asegura el intervalo mínimo entre queries.
_DDG_SEMAPHORE = threading.Semaphore(1)

_DDG_CACHE: dict = {}
_DDG_CACHE_LOCK = threading.Lock()
_DDG_CACHE_FILE = config.CACHE_DIR / "ddg_search_cache.json"


def _load_ddg_cache() -> None:
    """Carga el caché de búsquedas DDG desde disco al iniciar."""
    global _DDG_CACHE
    if not getattr(config, "DDG_CACHE_ENABLED", True):
        return
    if _DDG_CACHE_FILE.exists():
        try:
            _DDG_CACHE = json.loads(_DDG_CACHE_FILE.read_text(encoding="utf-8"))
            logger.info(f"[ddg_cache] {len(_DDG_CACHE)} entradas cargadas desde {_DDG_CACHE_FILE.name}")
        except Exception as e:
            logger.warning(f"[ddg_cache] Error cargando caché: {e}")
            _DDG_CACHE = {}


def _persist_ddg_cache() -> None:
    """Persiste el caché a disco (thread-safe)."""
    if not getattr(config, "DDG_CACHE_ENABLED", True):
        return
    with _DDG_CACHE_LOCK:
        try:
            _DDG_CACHE_FILE.write_text(
                json.dumps(_DDG_CACHE, ensure_ascii=False), encoding="utf-8"
            )
        except Exception as e:
            logger.warning(f"[ddg_cache] Error guardando caché: {e}")


_load_ddg_cache()


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

    # Construir conjunto de dominios de universidades prioritarias (excepción)
    priority_domains = {
        _extract_domain(u["url_oficial"])
        for u in getattr(config, "PRIORITY_UNIVERSITIES", [])
    }

    # Aceptar cualquier dominio .mx (edu.mx, gob.mx, com.mx, org.mx, *.mx)
    # o dominios prioritarios conocidos.  Los dominios excluidos explícitamente
    # (facebook.com, etc.) se filtran por is_excluded() en fases posteriores.
    def _is_valid_university_domain(domain: str) -> bool:
        if domain in priority_domains:
            return True
        return domain.endswith(".mx")

    before = len(valid)
    valid = valid[valid["_domain"].apply(_is_valid_university_domain)].copy()
    skipped = before - len(valid)
    if skipped:
        logger.info(
            f"[uni_search] {skipped} universidades descartadas por dominio no .mx "
            f"y no prioritarias"
        )

    # Deduplicar por dominio (un dominio puede aparecer varias veces en el CSV)
    valid = valid.drop_duplicates(subset=["_domain"])

    # Universidades sin url_oficial: búsqueda solo por nombre
    no_url_mask = df["url_oficial"].isin(["", "nan"])
    no_url_df   = df[no_url_mask][["universidad", "estado_fuente"]].copy() if "estado_fuente" in df.columns else df[no_url_mask][["universidad"]].copy()
    no_url_df   = no_url_df[no_url_df["universidad"].str.strip().str.len() > 3].drop_duplicates(subset=["universidad"])
    no_url_df["url_oficial"] = ""
    no_url_df["_domain"]     = ""
    no_url_df["is_no_url"]   = True
    if "estado_fuente" not in no_url_df.columns:
        no_url_df["estado_fuente"] = ""
    logger.info(f"[uni_search] {len(no_url_df)} universidades sin URL (búsqueda por nombre)")

    valid["is_no_url"] = False
    combined = pd.concat([valid, no_url_df], ignore_index=True)

    logger.info(f"[uni_search] {len(valid)} universidades con dominio .mx + {len(no_url_df)} sin URL = {len(combined)} total")
    return combined.reset_index(drop=True)


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

def _ddg_search_raw(query: str, max_results: int = config.MAX_RESULTS_PER_QUERY) -> List[Dict]:
    """Query con Google (primario) → DDG (fallback). Sin rate-limit ni caché. Usar solo a través de _ddg_search."""
    return _multi_search(query, max_results=max_results)


def _ddg_search(query: str, max_results: int = config.MAX_RESULTS_PER_QUERY) -> List[Dict]:
    """
    Query DDG con:
      - Caché en disco: evita repetir queries entre re-runs.
      - Semáforo: garantiza que solo un hilo consulta DDG a la vez
        (rate-limit seguro aunque search_universities corra en paralelo).
    """
    cache_key = hashlib.md5(f"{query}|{max_results}".encode()).hexdigest()

    # Consultar caché primero (sin bloquear semáforo)
    if getattr(config, "DDG_CACHE_ENABLED", True):
        with _DDG_CACHE_LOCK:
            if cache_key in _DDG_CACHE:
                logger.debug(f"[ddg_cache] HIT: {query[:60]}")
                return _DDG_CACHE[cache_key]

    # Adquirir semáforo: serializa el acceso real a DDG
    with _DDG_SEMAPHORE:
        # Doble-check dentro del semáforo (otro hilo pudo haber cacheado)
        if getattr(config, "DDG_CACHE_ENABLED", True):
            with _DDG_CACHE_LOCK:
                if cache_key in _DDG_CACHE:
                    return _DDG_CACHE[cache_key]

        results = _ddg_search_raw(query, max_results)
        # El delay va DENTRO del semáforo para que el siguiente hilo
        # espere el intervalo completo antes de su propia query.
        time.sleep(config.SEARCH_DELAY_SECONDS)

    # Persistir en caché
    if getattr(config, "DDG_CACHE_ENABLED", True):
        with _DDG_CACHE_LOCK:
            _DDG_CACHE[cache_key] = results
        _persist_ddg_cache()

    return results


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

            # Descartar URLs fuera del dominio de la universidad consultada
            result_domain = _extract_domain(url)
            if domain not in result_domain and result_domain not in domain:
                logger.debug(
                    f"[uni_search] URL fuera de dominio descartada: {url[:60]} "
                    f"(esperado: {domain})"
                )
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

        # El delay ya ocurre dentro del semáforo en _ddg_search().
        # No añadir sleep aquí para no duplicarlo.

    return docs


# ─── Búsqueda por nombre (universidades sin URL oficial) ─────────────────────

_NAME_QUERY_TEMPLATES = [
    '"{name}" México "inteligencia artificial" lineamientos OR reglamento OR política',
    '"{name}" México "uso de IA" OR "IA generativa" académico normativa',
]


def _search_university_by_name(name: str) -> List[Dict]:
    """
    Búsqueda DDG por nombre de universidad para entradas sin url_oficial.
    No usa site: operator; acepta solo resultados con dominio .mx o .edu.mx.
    """
    docs: List[Dict] = []

    for template in _NAME_QUERY_TEMPLATES:
        query = template.format(name=name)
        logger.debug(f"[uni_search] (sin-url) {name} — query: {query}")
        raw = _ddg_search(query, max_results=5)

        for r in raw:
            url   = r.get("href", "") or r.get("url", "")
            title = r.get("title", "")
            body  = r.get("body", "")

            if not url or is_excluded(url):
                continue

            # Solo aceptar dominios .mx (o .edu.mx implícito) para evitar ruido internacional
            result_domain = _extract_domain(url)
            if not result_domain.endswith(".mx"):
                continue

            docs.append({
                "url": url,
                "title": title,
                "snippet": body[:400],
                "source_type": "university_name_search",
                "university_name": name,
                "university_domain": result_domain,
                "query_used": query,
                "extracted_text": "",
                "extraction_error": None,
                "heuristic_score": 0.0,
                "heuristic_label": "BAJA",
                "ai_classification": None,
            })

        # El delay ya ocurre dentro del semáforo en _ddg_search().

    return docs


# ─── Procesamiento de una universidad ────────────────────────────────────────

def _process_university(row: pd.Series) -> List[Dict]:
    """Combina búsqueda DDG + crawl para una universidad."""
    name   = row.get("universidad", "")
    url    = row.get("url_oficial", "")
    domain = row.get("_domain", "")

    # ── Caso sin URL: búsqueda solo por nombre ─────────────────────────────
    is_no_url = row.get("is_no_url")
    if not domain or (is_no_url is True or is_no_url == 1):
        if name.strip():
            logger.info(f"[uni_search] Procesando (sin URL): {name}")
            return _search_university_by_name(name)
        return []

    is_priority = bool(row.get("is_priority", False))
    max_urls    = config.MAX_URLS_PRIORITY_UNIVERSITY if is_priority else config.MAX_URLS_PER_UNIVERSITY
    priority_tag = " [PRIORITARIA]" if is_priority else ""

    logger.info(f"[uni_search] Procesando: {name} ({domain}){priority_tag}")

    # a) Búsqueda externa
    ddg_docs = _search_university_ddg(name, domain)

    # b) Crawling interno
    # Optimización: si DDG ya encontró suficientes URLs para una universidad
    # no-prioritaria, el crawl adiciona muy poco valor — saltarlo.
    if not is_priority and len(ddg_docs) >= max_urls:
        logger.debug(f"[uni_search] Crawl omitido para {name} (DDG trajo {len(ddg_docs)} ≥ {max_urls})")
        return ddg_docs

    base_url = url if url.startswith("http") else f"https://{domain}"
    if is_priority:
        crawl_docs = crawl_domain(
            domain=base_url,
            university_name=name,
            source_type="university",
            max_docs=max_urls,
        )
    elif getattr(config, "CRAWL_NON_PRIORITY", False):
        # Usar rutas reducidas para no-prioritarias si están configuradas
        non_priority_paths = getattr(config, "NON_PRIORITY_CRAWL_PATHS", None)
        crawl_docs = crawl_domain(
            domain=base_url,
            university_name=name,
            source_type="university",
            max_docs=getattr(config, "CRAWL_NON_PRIORITY_MAX_DOCS", 2),
            max_seconds=getattr(config, "CRAWL_NON_PRIORITY_MAX_SECONDS", 15),
            paths=non_priority_paths,
        )
    else:
        crawl_docs = []

    return ddg_docs + crawl_docs


# ─── Punto de entrada ─────────────────────────────────────────────────────────

def search_universities(
    universities_df: Optional[pd.DataFrame] = None,
    progress_checkpoint: Optional[Path] = None,
) -> List[Dict]:
    """
    Ejecuta FASE 2 completa para todas las universidades del CSV.

    Args:
        universities_df:      DataFrame de universidades (cargado desde CSV si None).
        progress_checkpoint:  Ruta al archivo JSON de progreso intra-fase.
                              Si existe, se reanudan las universidades pendientes.
                              Siempre se actualiza cada 5 universidades completadas.

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
    priority_df["is_no_url"]   = False
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

    # ── Cargar progreso previo desde checkpoint intra-fase ────────────────────
    completed_domains: set = set()
    completed_names: set = set()
    checkpoint_raw_docs: List[Dict] = []

    if progress_checkpoint and Path(progress_checkpoint).exists():
        try:
            progress_data = json.loads(Path(progress_checkpoint).read_text(encoding="utf-8"))
            completed_domains = set(progress_data.get("completed_domains", []))
            completed_names   = set(progress_data.get("completed_names", []))
            checkpoint_raw_docs = progress_data.get("raw_docs", [])
            logger.info(
                f"[uni_search] Checkpoint cargado: {len(completed_domains)} dominios + "
                f"{len(completed_names)} nombres ya procesados | "
                f"{len(checkpoint_raw_docs)} docs acumulados"
            )
        except Exception as e:
            logger.warning(f"[uni_search] Error cargando progress checkpoint: {e}")

    # Filtrar universidades ya procesadas
    if completed_domains or completed_names:
        def _already_done(row: pd.Series) -> bool:
            d = row.get("_domain", "")
            if d:
                return d in completed_domains
            return row.get("universidad", "") in completed_names

        mask = ~combined_df.apply(_already_done, axis=1)
        skipped = int((~mask).sum())
        if skipped:
            logger.info(f"[uni_search] {skipped} universidades ya procesadas — omitidas por checkpoint")
        combined_df = combined_df[mask].copy()

    all_docs: List[Dict] = list(checkpoint_raw_docs)  # iniciar con docs ya acumulados
    all_docs_lock = threading.Lock()
    total_unis = len(combined_df)
    fase2_start = time.time()
    completed_count = [0]  # lista para mutabilidad en closure

    rows = list(combined_df.iterrows())

    def _process_with_progress(args):
        _, row = args
        docs = _process_university(row)
        with all_docs_lock:
            all_docs.extend(docs)
            completed_count[0] += 1
            # Registrar como completada
            domain = row.get("_domain", "")
            name   = row.get("universidad", "")
            if domain:
                completed_domains.add(domain)
            if not domain or row.get("is_no_url"):
                completed_names.add(name)

            i = completed_count[0]
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

            # Guardar progreso cada 5 universidades completadas
            if progress_checkpoint and i % 5 == 0:
                try:
                    progress_data = {
                        "completed_domains": list(completed_domains),
                        "completed_names":   list(completed_names),
                        "raw_docs":          all_docs,
                    }
                    Path(progress_checkpoint).write_text(
                        json.dumps(progress_data, ensure_ascii=False),
                        encoding="utf-8",
                    )
                    logger.debug(f"[uni_search] Checkpoint guardado ({i} universidades)")
                except Exception as e:
                    logger.warning(f"[uni_search] Error guardando progress checkpoint: {e}")
        return docs

    # Paralelo: el semáforo _DDG_SEMAPHORE dentro de _ddg_search() garantiza
    # que las queries DDG sean secuenciales (1 a la vez con delay).
    # El crawl de cada universidad corre en paralelo sobre dominios distintos.
    workers = min(config.MAX_WORKERS, total_unis)
    logger.info(f"[uni_search] Procesando con {workers} workers paralelos")
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = [executor.submit(_process_with_progress, item) for item in rows]
        for future in as_completed(futures):
            try:
                future.result()
            except Exception as e:
                logger.error(f"[uni_search] Error en universidad: {e}")

    logger.info(f"[uni_search] Total crudo: {len(all_docs)} documentos")

    # Guardar checkpoint final de la fase 2 (todas las universidades completadas)
    if progress_checkpoint:
        try:
            progress_data = {
                "completed_domains": list(completed_domains),
                "completed_names":   list(completed_names),
                "raw_docs":          all_docs,
            }
            Path(progress_checkpoint).write_text(
                json.dumps(progress_data, ensure_ascii=False),
                encoding="utf-8",
            )
            logger.info("[uni_search] Checkpoint final FASE 2 guardado")
        except Exception as e:
            logger.warning(f"[uni_search] Error guardando checkpoint final FASE 2: {e}")

    filtered = filter_and_rank(all_docs)
    logger.info(f"[uni_search] Tras filtro: {len(filtered)} documentos")

    return filtered

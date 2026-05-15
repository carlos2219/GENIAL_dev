"""
search_router.py — Phase-aware search dispatcher with TTL cache.

query_type:
  "gov"  → Phase 1 government: CSE + Brave parallel, Serper fallback
  "site" → Phase 2 universities: Serper primary, DDG fallback
  "open" → Phase 3 open: Brave primary, Serper fallback
  None   → Legacy cascade: CSE → Brave → DDG
"""

import hashlib
import json
import logging
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from typing import Dict, List, Optional

import config

logger = logging.getLogger(__name__)

# ─── Unified TTL cache ────────────────────────────────────────────────────────

_cache_data: Dict = {}
_cache_lock = threading.Lock()
_dirty_count = 0
_FLUSH_EVERY = 20


def _cache_file():
    return config.CACHE_DIR / "search_cache.json"


def _load_cache() -> None:
    global _cache_data
    cf = _cache_file()
    if cf.exists():
        try:
            _cache_data = json.loads(cf.read_text(encoding="utf-8"))
            logger.info(f"[search_cache] {len(_cache_data)} entradas cargadas")
            return
        except Exception as e:
            logger.warning(f"[search_cache] Error cargando cache: {e}")
            _cache_data = {}

    # Migrate old DDG cache
    old = config.CACHE_DIR / "ddg_search_cache.json"
    if old.exists():
        try:
            old_data = json.loads(old.read_text(encoding="utf-8"))
            now_str = datetime.now(timezone.utc).isoformat()
            for key, results in old_data.items():
                _cache_data[key] = {
                    "key": key, "backend": "ddg", "query_type": None,
                    "results": results, "cached_at": now_str, "ttl_days": 7,
                }
            logger.info(f"[search_cache] Migradas {len(_cache_data)} entradas DDG → search_cache.json")
        except Exception as e:
            logger.warning(f"[search_cache] Error migrando DDG cache: {e}")


def _flush_cache() -> None:
    try:
        _cache_file().write_text(
            json.dumps(_cache_data, ensure_ascii=False), encoding="utf-8"
        )
    except Exception as e:
        logger.warning(f"[search_cache] Error guardando cache: {e}")


def _cache_key(backend: str, query: str, max_results: int) -> str:
    return hashlib.md5(f"{backend}|{query}|{max_results}".encode()).hexdigest()


def _cache_get(backend: str, query: str, max_results: int) -> Optional[List]:
    key = _cache_key(backend, query, max_results)
    with _cache_lock:
        entry = _cache_data.get(key)
    if not entry:
        return None
    try:
        cached_at = datetime.fromisoformat(entry["cached_at"])
        if cached_at.tzinfo is None:
            cached_at = cached_at.replace(tzinfo=timezone.utc)
        ttl = entry.get("ttl_days", 7)
        if ttl == 0 or (datetime.now(timezone.utc) - cached_at).days >= ttl:
            return None
    except Exception:
        return None
    return entry["results"]


def _cache_put(
    backend: str, query: str, max_results: int,
    query_type: Optional[str], results: List, ttl_days: int
) -> None:
    global _dirty_count
    key = _cache_key(backend, query, max_results)
    entry = {
        "key": key, "backend": backend, "query_type": query_type,
        "results": results,
        "cached_at": datetime.now(timezone.utc).isoformat(),
        "ttl_days": ttl_days,
    }
    with _cache_lock:
        _cache_data[key] = entry
        _dirty_count += 1
        if _dirty_count >= _FLUSH_EVERY:
            _flush_cache()
            _dirty_count = 0


def _ttl_for(query_type: Optional[str]) -> int:
    if query_type == "gov":
        return int(getattr(config, "CACHE_TTL_GOV_DAYS", 7))
    if query_type == "site":
        return int(getattr(config, "CACHE_TTL_SITE_DAYS", 14))
    if query_type == "open":
        return int(getattr(config, "CACHE_TTL_OPEN_DAYS", 3))
    return 7


# ─── Backend dispatch ─────────────────────────────────────────────────────────

def _call_backend_raw(backend: str, query: str, max_results: int, query_type: Optional[str]) -> List[Dict]:
    """Call backend function by name. Separated for easy mocking in tests."""
    from .search_backends import (
        _google_cse_search, _brave_search, _serper_search, _ddg_search,
    )
    fns = {
        "cse":    lambda: _google_cse_search(query, max_results),
        "brave":  lambda: _brave_search(query, max_results),
        "serper": lambda: _serper_search(query, max_results),
        "ddg":    lambda: _ddg_search(query, max_results),
    }
    fn = fns.get(backend)
    return fn() if fn else []


def _call_backend(
    backend: str, query: str, max_results: int, query_type: Optional[str]
) -> List[Dict]:
    """Cache wrapper around _call_backend_raw. Records metrics."""
    metrics_on = getattr(config, "SEARCH_METRICS_ENABLED", True)

    cached = _cache_get(backend, query, max_results)
    if cached is not None:
        if metrics_on:
            from .search_metrics import get_metrics
            get_metrics().record_cache_event("hit", query_type or "legacy")
        for r in cached:
            r.setdefault("_backend_tag", backend)
            r.setdefault("_query_type", query_type or "")
        return cached

    if metrics_on:
        from .search_metrics import get_metrics
        get_metrics().record_cache_event("miss", query_type or "legacy")

    t0 = time.time()
    results = _call_backend_raw(backend, query, max_results, query_type)
    latency_ms = (time.time() - t0) * 1000

    for r in results:
        r["_backend_tag"] = backend
        r["_query_type"] = query_type or ""

    if metrics_on:
        from .search_metrics import get_metrics
        m = get_metrics()
        urls = [r.get("url") or r.get("href", "") for r in results]
        m.record_query(backend, query_type or "legacy", latency_ms, len(results), urls)
        if backend in ("serper", "cse"):
            m.record_billed(backend)

    _cache_put(backend, query, max_results, query_type, results, _ttl_for(query_type))
    return results


# ─── Merge ────────────────────────────────────────────────────────────────────

def _merge_results(by_backend: Dict[str, List[Dict]], max_results: int) -> List[Dict]:
    """Merge results from multiple backends; deduplicate by URL; preserve first occurrence."""
    seen: Dict[str, Dict] = {}
    for results in by_backend.values():
        for r in results:
            url = r.get("url") or r.get("href", "")
            if url and url not in seen:
                seen[url] = r
    return list(seen.values())[:max_results]


# ─── Legacy cascade ───────────────────────────────────────────────────────────

def _legacy_cascade(query: str, max_results: int, pause: Optional[float]) -> List[Dict]:
    """Original cascade: CSE → Brave → DDG. Dead scraping slot removed."""
    from .search_backends import _google_cse_search, _brave_search, _ddg_search

    if getattr(config, "GOOGLE_CSE_API_KEY", "") and getattr(config, "GOOGLE_CSE_ID", ""):
        r = _google_cse_search(query, max_results)
        if r:
            return r

    if getattr(config, "BRAVE_API_KEY", ""):
        r = _brave_search(query, max_results)
        if r:
            return r

    return _ddg_search(query, max_results)


# ─── Public router ────────────────────────────────────────────────────────────

def router_search(
    query: str,
    query_type: Optional[str] = None,
    max_results: Optional[int] = None,
    pause: Optional[float] = None,
) -> List[Dict]:
    """Phase-aware dispatcher. query_type: 'gov' | 'site' | 'open' | None."""
    if max_results is None:
        max_results = int(getattr(config, "MAX_RESULTS_PER_QUERY", 10))

    if not getattr(config, "SEARCH_ROUTER_ENABLED", True):
        return _legacy_cascade(query, max_results, pause)

    table = getattr(config, "ROUTING_TABLE", {})
    route = table.get(query_type) or table.get(None) or {
        "primary": ["cse", "brave", "ddg"], "secondary": None, "parallel": False
    }

    primary   = route.get("primary", ["ddg"])
    secondary = route.get("secondary")
    parallel  = route.get("parallel", False) and getattr(config, "SEARCH_PARALLEL_GOV", True)

    results: List[Dict] = []

    if parallel and len(primary) > 1:
        by_backend: Dict[str, List] = {}
        with ThreadPoolExecutor(max_workers=len(primary)) as ex:
            futures = {
                ex.submit(_call_backend, name, query, max_results, query_type): name
                for name in primary
            }
            for fut in as_completed(futures):
                name = futures[fut]
                try:
                    by_backend[name] = fut.result()
                except Exception as e:
                    logger.warning(f"[router] Backend {name} error: {e}")
                    by_backend[name] = []
        results = _merge_results(by_backend, max_results)
    else:
        for name in primary:
            results = _call_backend(name, query, max_results, query_type)
            if results:
                break

    if not results and secondary:
        results = _call_backend(secondary, query, max_results, query_type)

    return results


# ─── Init cache on module load ────────────────────────────────────────────────
_load_cache()

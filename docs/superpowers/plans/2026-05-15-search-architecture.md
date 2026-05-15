# Search Architecture Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the single-cascade search backend with a phase-aware router (gov/site/open), add Serper.dev, TTL cache, execution profiles, and a SearchMetrics layer that tracks hit_rate, pdf_yield, official_domain_ratio, validated_document_rate, and false_positive_rate per backend×phase.

**Architecture:** `search_metrics.py` is the foundation (singleton, thread-safe); `search_router.py` holds routing logic, TTL cache, and parallel dispatcher; `search_backends.py` gains `_serper_search()` and `_backend_tag` on all results; `multi_search()` becomes a thin delegate to the router. Phase callers pass `query_type`; extractor and classifier call back into metrics.

**Tech Stack:** Python 3.10+, requests, threading.Lock, ThreadPoolExecutor, json, csv, statistics, unittest.mock

---

## File Map

| Action | Path | Responsibility |
|---|---|---|
| CREATE | `src/pipeline/search_metrics.py` | SearchMetrics singleton, record_*, export_report |
| CREATE | `src/pipeline/search_router.py` | Phase-aware router, TTL cache, parallel dispatcher |
| MODIFY | `src/pipeline/search_backends.py` | +`_serper_search`, +`_backend_tag` on all backends, delegate `multi_search` |
| MODIFY | `config.py` | +SERPER key, flags, TTL vars, profiles, LATAM config, `_is_official_url` |
| MODIFY | `src/pipeline/government_search.py` | Pass `query_type="gov"`, use `config._is_official_url` |
| MODIFY | `src/pipeline/university_search.py` | Pass `query_type="site"` |
| MODIFY | `src/pipeline/open_search.py` | Pass `query_type="open"`, use `config._is_official_url` |
| MODIFY | `main.py` | `_extract_all` calls `record_validation`; add `--profile` |
| MODIFY | `src/pipeline/document_classifier.py` | `classify()` calls `record_classification` |
| MODIFY | `.env.example` | +SERPER_API_KEY, SEARCH_PROFILE |
| CREATE | `tests/test_search_metrics.py` | Unit tests for SearchMetrics |
| CREATE | `tests/test_search_router.py` | Unit tests for router + cache |

---

## Task 1 — `search_metrics.py`: core metrics infrastructure

**Files:**
- Create: `src/pipeline/search_metrics.py`
- Create: `tests/test_search_metrics.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_search_metrics.py
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import time
import json
import csv
import tempfile
from src.pipeline.search_metrics import SearchMetrics, get_metrics


def _fresh() -> SearchMetrics:
    m = SearchMetrics()
    return m


def test_record_query_increments_queries():
    m = _fresh()
    m.record_query("cse", "gov", 120.0, 5, ["https://gob.mx/a.pdf", "https://gob.mx/b"])
    rows = m._bucket_rows()
    assert rows[0]["queries_served"] == 1
    assert rows[0]["hit_rate"] == 1.0


def test_hit_rate_zero_when_no_results():
    m = _fresh()
    m.record_query("ddg", "site", 80.0, 0, [])
    rows = m._bucket_rows()
    assert rows[0]["hit_rate"] == 0.0


def test_pdf_yield_counts_pdf_urls():
    m = _fresh()
    m.record_query("serper", "site", 100.0, 3,
                   ["https://unam.mx/doc.pdf", "https://unam.mx/page", "https://unam.mx/other.pdf"])
    rows = m._bucket_rows()
    assert rows[0]["pdf_yield"] == pytest.approx(2 / 3, abs=0.01)


def test_record_validation_updates_validated_rate():
    m = _fresh()
    m.record_query("cse", "gov", 100.0, 2, ["https://a.gob.mx/1", "https://a.gob.mx/2"])
    m.record_validation("https://a.gob.mx/1", survived=True)
    m.record_validation("https://a.gob.mx/2", survived=False)
    rows = m._bucket_rows()
    assert rows[0]["validated_document_rate"] == pytest.approx(0.5, abs=0.01)


def test_record_classification_false_positive_rate():
    m = _fresh()
    m.record_query("brave", "open", 90.0, 2, ["https://sep.gob.mx/x", "https://sep.gob.mx/y"])
    m.record_validation("https://sep.gob.mx/x", survived=True)
    m.record_validation("https://sep.gob.mx/y", survived=True)
    m.record_classification("https://sep.gob.mx/x", is_normative=True)
    m.record_classification("https://sep.gob.mx/y", is_normative=False)
    rows = m._bucket_rows()
    assert rows[0]["false_positive_rate"] == pytest.approx(0.5, abs=0.01)


def test_export_report_writes_json_and_csv(tmp_path):
    m = _fresh()
    m.record_query("cse", "gov", 110.0, 2, ["https://gob.mx/a", "https://gob.mx/b"])
    m.export_report(tmp_path)
    files = list((tmp_path / "metrics").iterdir())
    json_files = [f for f in files if f.suffix == ".json"]
    csv_files  = [f for f in files if f.suffix == ".csv"]
    assert len(json_files) == 1
    assert len(csv_files)  == 1
    report = json.loads(json_files[0].read_text())
    assert "summary" in report
    assert "by_backend_and_phase" in report
    assert len(report["by_backend_and_phase"]) == 1


def test_unknown_url_in_record_validation_is_silently_ignored():
    m = _fresh()
    m.record_validation("https://unknown.example.com/x", survived=True)  # must not raise


def test_get_metrics_returns_singleton():
    a = get_metrics()
    b = get_metrics()
    assert a is b
```

- [ ] **Step 2: Run tests — expect failures**

```
pytest tests/test_search_metrics.py -v
```
Expected: `ModuleNotFoundError` or `ImportError` for `search_metrics`.

- [ ] **Step 3: Implement `src/pipeline/search_metrics.py`**

```python
"""
search_metrics.py — Thread-safe metrics collector for the search pipeline.

Records per-backend×phase: hit_rate, pdf_yield, official_domain_ratio,
latency_p50/p95, validated_document_rate, false_positive_rate.
"""

import csv
import json
import re
import statistics
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple


# ─── Compiled official-domain patterns (lazy, thread-safe) ───────────────────

_COMPILED_PATTERNS: Optional[List[re.Pattern]] = None
_COMPILED_LOCK = threading.Lock()


def _official_patterns() -> List[re.Pattern]:
    global _COMPILED_PATTERNS
    if _COMPILED_PATTERNS is None:
        with _COMPILED_LOCK:
            if _COMPILED_PATTERNS is None:
                try:
                    import config
                    raw = getattr(config, "OFFICIAL_DOMAIN_PATTERNS", {})
                    active = getattr(config, "ACTIVE_COUNTRIES", ["MX"])
                    _COMPILED_PATTERNS = [
                        re.compile(p)
                        for country in active
                        for p in raw.get(country, [])
                    ]
                except Exception:
                    _COMPILED_PATTERNS = [
                        re.compile(r"\.gob\.mx$"),
                        re.compile(r"\.edu\.mx$"),
                    ]
    return _COMPILED_PATTERNS


def _p95(data: List[float]) -> float:
    if not data:
        return 0.0
    s = sorted(data)
    return s[min(int(len(s) * 0.95), len(s) - 1)]


# ─── Per-bucket storage ───────────────────────────────────────────────────────

@dataclass
class _Bucket:
    queries: int = 0
    hits: int = 0
    result_counts: List[int] = field(default_factory=list)
    latencies_ms: List[float] = field(default_factory=list)
    pdf_count: int = 0
    official_count: int = 0
    url_count: int = 0
    validated_survived: int = 0
    validated_failed: int = 0
    classified_normative: int = 0
    classified_non_normative: int = 0


# ─── SearchMetrics ────────────────────────────────────────────────────────────

class SearchMetrics:
    def __init__(self):
        self._lock = threading.Lock()
        self._buckets: Dict[Tuple[str, str], _Bucket] = {}
        self._url_index: Dict[str, Tuple[str, str]] = {}
        self._billed: Dict[str, int] = {}
        self._cache_stats: Dict = {"hits": 0, "misses": 0, "expired": 0, "by_query_type": {}}
        self._start_time = time.time()

    def _bucket(self, backend: str, phase: str) -> _Bucket:
        key = (backend, phase)
        if key not in self._buckets:
            self._buckets[key] = _Bucket()
        return self._buckets[key]

    def record_query(
        self,
        backend: str,
        phase: str,
        latency_ms: float,
        n_results: int,
        urls: List[str],
    ) -> None:
        patterns = _official_patterns()
        with self._lock:
            b = self._bucket(backend, phase)
            b.queries += 1
            if n_results > 0:
                b.hits += 1
            b.result_counts.append(n_results)
            b.latencies_ms.append(latency_ms)
            b.url_count += len(urls)
            for url in urls:
                u = url.lower()
                if u.endswith(".pdf") or ".pdf?" in u:
                    b.pdf_count += 1
                if any(p.search(u) for p in patterns):
                    b.official_count += 1
                self._url_index[url] = (backend, phase)

    def record_cache_event(self, event: str, query_type: str) -> None:
        """event: 'hit' | 'miss' | 'expired'"""
        key = event + "s"
        with self._lock:
            self._cache_stats[key] = self._cache_stats.get(key, 0) + 1
            qt = self._cache_stats["by_query_type"].setdefault(
                query_type or "legacy", {"hits": 0, "misses": 0, "expired": 0}
            )
            qt[key] = qt.get(key, 0) + 1

    def record_validation(self, url: str, survived: bool) -> None:
        with self._lock:
            key = self._url_index.get(url)
            if not key:
                return
            b = self._bucket(*key)
            if survived:
                b.validated_survived += 1
            else:
                b.validated_failed += 1

    def record_classification(self, url: str, is_normative: bool) -> None:
        with self._lock:
            key = self._url_index.get(url)
            if not key:
                return
            b = self._bucket(*key)
            if is_normative:
                b.classified_normative += 1
            else:
                b.classified_non_normative += 1

    def record_billed(self, backend: str, n: int = 1) -> None:
        with self._lock:
            self._billed[backend] = self._billed.get(backend, 0) + n

    def reset(self) -> None:
        with self._lock:
            self._buckets.clear()
            self._url_index.clear()
            self._billed.clear()
            self._cache_stats = {"hits": 0, "misses": 0, "expired": 0, "by_query_type": {}}
            self._start_time = time.time()
        global _COMPILED_PATTERNS
        _COMPILED_PATTERNS = None

    def _bucket_rows(self) -> List[Dict]:
        rows = []
        with self._lock:
            for (backend, phase), b in self._buckets.items():
                total_extracted = b.validated_survived + b.validated_failed
                total_classified = b.classified_normative + b.classified_non_normative
                rows.append({
                    "backend": backend,
                    "phase": phase,
                    "queries_served": b.queries,
                    "hit_rate": round(b.hits / b.queries, 4) if b.queries else 0.0,
                    "avg_results_per_query": round(
                        statistics.mean(b.result_counts), 2
                    ) if b.result_counts else 0.0,
                    "pdf_yield": round(b.pdf_count / b.url_count, 4) if b.url_count else 0.0,
                    "official_domain_ratio": round(
                        b.official_count / b.url_count, 4
                    ) if b.url_count else 0.0,
                    "latency_p50_ms": round(
                        statistics.median(b.latencies_ms), 1
                    ) if b.latencies_ms else 0.0,
                    "latency_p95_ms": round(_p95(b.latencies_ms), 1) if b.latencies_ms else 0.0,
                    "validated_document_rate": round(
                        b.validated_survived / total_extracted, 4
                    ) if total_extracted else None,
                    "false_positive_rate": round(
                        b.classified_non_normative / total_classified, 4
                    ) if total_classified else None,
                })
        return rows

    def export_report(self, output_dir) -> None:
        output_dir = Path(output_dir) / "metrics"
        output_dir.mkdir(parents=True, exist_ok=True)
        run_id = time.strftime("%Y%m%d_%H%M%S")

        rows = self._bucket_rows()
        with self._lock:
            serper_q = self._billed.get("serper", 0)
            cse_q = self._billed.get("cse", 0)
            cache_snap = dict(self._cache_stats)
            duration = round(time.time() - self._start_time, 1)
            total_queries = sum(b.queries for b in self._buckets.values())
            total_urls = sum(b.url_count for b in self._buckets.values())

        try:
            import config as _cfg
            profile = getattr(_cfg, "SEARCH_PROFILE", "balanced")
            active_countries = getattr(_cfg, "ACTIVE_COUNTRIES", ["MX"])
        except Exception:
            profile, active_countries = "balanced", ["MX"]

        report = {
            "summary": {
                "run_id": run_id,
                "profile": profile,
                "duration_seconds": duration,
                "total_queries": total_queries,
                "total_urls_found": total_urls,
                "active_countries": active_countries,
                "serper_queries_billed": serper_q,
                "cse_queries_billed": cse_q,
            },
            "by_backend_and_phase": rows,
            "cache_stats": cache_snap,
            "cost_estimate": {
                "serper_queries": serper_q,
                "serper_cost_usd": round(serper_q * 0.001, 4),
                "cse_queries": cse_q,
                "cse_cost_usd": round(max(0, cse_q - 3000) * 0.005, 4),
                "total_usd": round(
                    serper_q * 0.001 + max(0, cse_q - 3000) * 0.005, 4
                ),
            },
        }

        json_path = output_dir / f"run_{run_id}.json"
        json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

        if rows:
            csv_path = output_dir / f"run_{run_id}.csv"
            with open(csv_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
                writer.writeheader()
                writer.writerows(rows)


# ─── Singleton ────────────────────────────────────────────────────────────────

_INSTANCE: Optional[SearchMetrics] = None
_INSTANCE_LOCK = threading.Lock()


def get_metrics() -> SearchMetrics:
    global _INSTANCE
    if _INSTANCE is None:
        with _INSTANCE_LOCK:
            if _INSTANCE is None:
                _INSTANCE = SearchMetrics()
    return _INSTANCE
```

- [ ] **Step 4: Add missing import to test file**

Add `import pytest` at the top of `tests/test_search_metrics.py` (after the sys.path lines).

- [ ] **Step 5: Run tests — expect green**

```
pytest tests/test_search_metrics.py -v
```
Expected: 8 tests PASS.

- [ ] **Step 6: Commit**

```bash
git add src/pipeline/search_metrics.py tests/test_search_metrics.py
git commit -m "feat: add SearchMetrics singleton with per-backend×phase tracking"
```

---

## Task 2 — `config.py`: new variables, LATAM config, profiles

**Files:**
- Modify: `config.py`

- [ ] **Step 1: Add new variables after the existing `# ─── Búsqueda ───` block (after line 67 in config.py)**

```python
# ─── Motor de búsqueda — router y backends ───────────────────────────────────
SERPER_API_KEY         = os.getenv("SERPER_API_KEY", "")
SEARCH_ROUTER_ENABLED  = os.getenv("SEARCH_ROUTER_ENABLED", "true").strip().lower() not in ("false", "0", "no")
SEARCH_PARALLEL_GOV    = os.getenv("SEARCH_PARALLEL_GOV",   "true").strip().lower() not in ("false", "0", "no")
SEARCH_METRICS_ENABLED = os.getenv("SEARCH_METRICS_ENABLED","true").strip().lower() not in ("false", "0", "no")
SEARCH_PROFILE         = os.getenv("SEARCH_PROFILE", "balanced").strip()

# TTL del caché unificado (días) — sobrescritos por _apply_profile() si no se definen en .env
CACHE_TTL_GOV_DAYS     = int(os.getenv("CACHE_TTL_GOV_DAYS",  "7"))
CACHE_TTL_SITE_DAYS    = int(os.getenv("CACHE_TTL_SITE_DAYS", "14"))
CACHE_TTL_OPEN_DAYS    = int(os.getenv("CACHE_TTL_OPEN_DAYS",  "3"))
```

- [ ] **Step 2: Add LATAM config after the `GOVERNMENT_PRIORITY_DOMAINS` block**

```python
# ─── LATAM extensibility ─────────────────────────────────────────────────────
LATAM_COUNTRIES = {
    "MX": {"tld": ".mx",  "lang": "es", "brave_country": "MX", "serper_gl": "mx"},
    "CO": {"tld": ".co",  "lang": "es", "brave_country": "CO", "serper_gl": "co"},
    "AR": {"tld": ".ar",  "lang": "es", "brave_country": "AR", "serper_gl": "ar"},
    "PE": {"tld": ".pe",  "lang": "es", "brave_country": "PE", "serper_gl": "pe"},
    "CL": {"tld": ".cl",  "lang": "es", "brave_country": "CL", "serper_gl": "cl"},
    "EC": {"tld": ".ec",  "lang": "es", "brave_country": "EC", "serper_gl": "ec"},
    "BR": {"tld": ".br",  "lang": "pt", "brave_country": "BR", "serper_gl": "br"},
}

OFFICIAL_DOMAIN_PATTERNS = {
    "MX": [r"\.gob\.mx$", r"\.edu\.mx$"],
    "CO": [r"\.gov\.co$", r"\.edu\.co$"],
    "AR": [r"\.gob\.ar$", r"\.edu\.ar$"],
    "PE": [r"\.gob\.pe$", r"\.edu\.pe$"],
    "CL": [r"\.gob\.cl$", r"\.edu\.cl$"],
    "EC": [r"\.gob\.ec$", r"\.edu\.ec$"],
    "BR": [r"\.gov\.br$", r"\.edu\.br$"],
}

ACTIVE_COUNTRIES = [c.strip() for c in os.getenv("ACTIVE_COUNTRIES", "MX").split(",")]
```

- [ ] **Step 3: Add `_is_official_url` helper and `_apply_profile` at the very end of `config.py`**

```python
# ─── Helpers ──────────────────────────────────────────────────────────────────

import re as _re

def _is_official_url(url: str, country: str = None) -> bool:
    """Returns True if url matches OFFICIAL_DOMAIN_PATTERNS for the given or all active countries."""
    countries = [country] if country else ACTIVE_COUNTRIES
    url_lower = url.lower()
    for c in countries:
        for pat in OFFICIAL_DOMAIN_PATTERNS.get(c, []):
            if _re.search(pat, url_lower):
                return True
    return False


# ─── Execution profiles ───────────────────────────────────────────────────────

_ROUTING_TABLES = {
    "fast": {
        "gov":  {"primary": ["cse"],                  "secondary": "ddg",    "parallel": False},
        "site": {"primary": ["ddg"],                  "secondary": None,     "parallel": False},
        "open": {"primary": ["ddg"],                  "secondary": None,     "parallel": False},
        None:   {"primary": ["cse", "brave", "ddg"],  "secondary": None,     "parallel": False},
    },
    "balanced": {
        "gov":  {"primary": ["cse", "brave"],         "secondary": "serper", "parallel": True},
        "site": {"primary": ["serper"],               "secondary": "ddg",    "parallel": False},
        "open": {"primary": ["brave"],                "secondary": "serper", "parallel": False},
        None:   {"primary": ["cse", "brave", "ddg"],  "secondary": None,     "parallel": False},
    },
    "deep": {
        "gov":  {"primary": ["cse", "brave", "serper"], "secondary": None,   "parallel": True},
        "site": {"primary": ["serper", "ddg"],          "secondary": None,   "parallel": True},
        "open": {"primary": ["brave", "serper"],        "secondary": None,   "parallel": True},
        None:   {"primary": ["cse", "brave", "ddg"],    "secondary": None,   "parallel": False},
    },
}

_PROFILE_DEFAULTS = {
    "fast":     {"CACHE_TTL_GOV_DAYS": 14, "CACHE_TTL_SITE_DAYS": 7,  "CACHE_TTL_OPEN_DAYS": 7,  "MAX_RESULTS_PER_QUERY": 5,  "SEARCH_PARALLEL_GOV": False},
    "balanced": {"CACHE_TTL_GOV_DAYS": 7,  "CACHE_TTL_SITE_DAYS": 14, "CACHE_TTL_OPEN_DAYS": 3,  "MAX_RESULTS_PER_QUERY": 10, "SEARCH_PARALLEL_GOV": True},
    "deep":     {"CACHE_TTL_GOV_DAYS": 1,  "CACHE_TTL_SITE_DAYS": 3,  "CACHE_TTL_OPEN_DAYS": 1,  "MAX_RESULTS_PER_QUERY": 20, "SEARCH_PARALLEL_GOV": True},
}


def _apply_profile(profile_name: str) -> None:
    """Apply execution profile. Env-var-defined values take precedence."""
    global CACHE_TTL_GOV_DAYS, CACHE_TTL_SITE_DAYS, CACHE_TTL_OPEN_DAYS
    global MAX_RESULTS_PER_QUERY, SEARCH_PARALLEL_GOV, ROUTING_TABLE

    defaults = _PROFILE_DEFAULTS.get(profile_name, _PROFILE_DEFAULTS["balanced"])

    if not os.getenv("CACHE_TTL_GOV_DAYS"):
        CACHE_TTL_GOV_DAYS = defaults["CACHE_TTL_GOV_DAYS"]
    if not os.getenv("CACHE_TTL_SITE_DAYS"):
        CACHE_TTL_SITE_DAYS = defaults["CACHE_TTL_SITE_DAYS"]
    if not os.getenv("CACHE_TTL_OPEN_DAYS"):
        CACHE_TTL_OPEN_DAYS = defaults["CACHE_TTL_OPEN_DAYS"]
    if not os.getenv("MAX_RESULTS_PER_QUERY"):
        MAX_RESULTS_PER_QUERY = defaults["MAX_RESULTS_PER_QUERY"]
    if not os.getenv("SEARCH_PARALLEL_GOV"):
        SEARCH_PARALLEL_GOV = defaults["SEARCH_PARALLEL_GOV"]

    ROUTING_TABLE = _ROUTING_TABLES.get(profile_name, _ROUTING_TABLES["balanced"])


ROUTING_TABLE = _ROUTING_TABLES["balanced"]  # default; overwritten by _apply_profile
_apply_profile(SEARCH_PROFILE)
```

- [ ] **Step 4: Verify config imports cleanly**

```
python -c "import config; print(config.SEARCH_PROFILE, config.ROUTING_TABLE['gov'])"
```
Expected output: `balanced {'primary': ['cse', 'brave'], 'secondary': 'serper', 'parallel': True}`

- [ ] **Step 5: Commit**

```bash
git add config.py
git commit -m "feat: add LATAM config, execution profiles, OFFICIAL_DOMAIN_PATTERNS to config"
```

---

## Task 3 — `search_backends.py`: Serper + `_backend_tag`

**Files:**
- Modify: `src/pipeline/search_backends.py`

- [ ] **Step 1: Add `_serper_search` after the Brave block (after line 174)**

```python
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
```

- [ ] **Step 2: Add `_backend_tag` to all existing backends**

In `_google_cse_search`, inside the `results.append({...})` call, add:
```python
"_backend_tag": "cse",
```

In `_brave_search`, inside `results.append({...})`:
```python
"_backend_tag": "brave",
```

In `_google_scrape_search`, in the list comprehension return:
```python
[{"href": u, "url": u, "title": "", "body": query, "_backend_tag": "google_scrape"} for u in urls]
```

In `_ddg_search`, after `results = list(DDGS().text(...))`, tag each result:
```python
for r in results:
    r.setdefault("_backend_tag", "ddg")
return results
```

- [ ] **Step 3: Replace `multi_search` body with router delegation**

Replace the entire `multi_search` function body (lines 256–303) with:

```python
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
```

- [ ] **Step 4: Verify no import errors**

```
python -c "from src.pipeline.search_backends import multi_search; print('ok')"
```
Expected: `ok`

- [ ] **Step 5: Commit**

```bash
git add src/pipeline/search_backends.py
git commit -m "feat: add _serper_search, _backend_tag on all backends, delegate multi_search to router"
```

---

## Task 4 — `search_router.py`: TTL cache + phase-aware dispatcher

**Files:**
- Create: `src/pipeline/search_router.py`
- Create: `tests/test_search_router.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_search_router.py
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import json
import time
from unittest.mock import patch, MagicMock
import pytest

import config


def _fake_results(backend: str, n: int = 2):
    return [{"url": f"https://example.com/{backend}/{i}", "href": f"https://example.com/{backend}/{i}",
             "title": f"Doc {i}", "body": "snippet", "_backend_tag": backend} for i in range(n)]


def test_router_uses_serper_for_site_queries(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "SEARCH_ROUTER_ENABLED", True)
    monkeypatch.setattr(config, "SEARCH_METRICS_ENABLED", False)
    monkeypatch.setattr(config, "CACHE_DIR", tmp_path)

    from src.pipeline import search_router
    search_router._cache_data.clear()

    with patch("src.pipeline.search_router._call_backend_raw") as mock_call:
        mock_call.return_value = _fake_results("serper")
        from src.pipeline.search_router import router_search
        results = router_search("site:unam.mx inteligencia artificial", query_type="site")

    calls = [c.args[0] for c in mock_call.call_args_list]
    assert "serper" in calls
    assert len(results) > 0


def test_router_uses_cse_and_brave_in_parallel_for_gov(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "SEARCH_ROUTER_ENABLED", True)
    monkeypatch.setattr(config, "SEARCH_PARALLEL_GOV", True)
    monkeypatch.setattr(config, "SEARCH_METRICS_ENABLED", False)
    monkeypatch.setattr(config, "CACHE_DIR", tmp_path)

    from src.pipeline import search_router
    search_router._cache_data.clear()

    called_backends = []

    def fake_call(backend, query, max_results, query_type):
        called_backends.append(backend)
        return _fake_results(backend)

    with patch("src.pipeline.search_router._call_backend_raw", side_effect=fake_call):
        from src.pipeline.search_router import router_search
        results = router_search("decreto inteligencia artificial gob.mx", query_type="gov")

    assert "cse" in called_backends
    assert "brave" in called_backends


def test_router_falls_back_to_legacy_when_disabled(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "SEARCH_ROUTER_ENABLED", False)
    monkeypatch.setattr(config, "CACHE_DIR", tmp_path)

    from src.pipeline import search_router
    search_router._cache_data.clear()

    with patch("src.pipeline.search_router._legacy_cascade") as mock_legacy:
        mock_legacy.return_value = _fake_results("cse")
        from src.pipeline.search_router import router_search
        results = router_search("test query")

    mock_legacy.assert_called_once()


def test_cache_returns_stored_result_on_second_call(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "SEARCH_ROUTER_ENABLED", True)
    monkeypatch.setattr(config, "SEARCH_METRICS_ENABLED", False)
    monkeypatch.setattr(config, "CACHE_TTL_SITE_DAYS", 14)
    monkeypatch.setattr(config, "CACHE_DIR", tmp_path)

    from src.pipeline import search_router
    search_router._cache_data.clear()

    call_count = [0]

    def fake_call(backend, query, max_results, query_type):
        call_count[0] += 1
        return _fake_results(backend)

    with patch("src.pipeline.search_router._call_backend_raw", side_effect=fake_call):
        from src.pipeline.search_router import router_search, _call_backend
        _call_backend("serper", "cached query", 10, "site")
        _call_backend("serper", "cached query", 10, "site")

    assert call_count[0] == 1  # second call served from cache


def test_expired_cache_entry_triggers_new_call(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "SEARCH_METRICS_ENABLED", False)
    monkeypatch.setattr(config, "CACHE_TTL_SITE_DAYS", 0)  # 0-day TTL = always expired
    monkeypatch.setattr(config, "CACHE_DIR", tmp_path)

    from src.pipeline import search_router
    search_router._cache_data.clear()

    call_count = [0]

    def fake_call(backend, query, max_results, query_type):
        call_count[0] += 1
        return _fake_results(backend)

    with patch("src.pipeline.search_router._call_backend_raw", side_effect=fake_call):
        from src.pipeline.search_router import _call_backend
        _call_backend("serper", "stale query", 10, "site")
        _call_backend("serper", "stale query", 10, "site")

    assert call_count[0] == 2


def test_merge_deduplicates_urls():
    from src.pipeline.search_router import _merge_results
    by_backend = {
        "cse":   [{"url": "https://a.gob.mx/1", "_backend_tag": "cse"}],
        "brave": [{"url": "https://a.gob.mx/1", "_backend_tag": "brave"},
                  {"url": "https://a.gob.mx/2", "_backend_tag": "brave"}],
    }
    merged = _merge_results(by_backend, max_results=10)
    urls = [r["url"] for r in merged]
    assert len(urls) == len(set(urls))
    assert len(merged) == 2
```

- [ ] **Step 2: Run — expect failures**

```
pytest tests/test_search_router.py -v
```
Expected: `ModuleNotFoundError` for `search_router`.

- [ ] **Step 3: Implement `src/pipeline/search_router.py`**

```python
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
```

- [ ] **Step 4: Run tests — expect green**

```
pytest tests/test_search_router.py -v
```
Expected: 6 tests PASS.

- [ ] **Step 5: Run full test suite to check nothing broke**

```
pytest tests/ -v
```
Expected: all PASS.

- [ ] **Step 6: Commit**

```bash
git add src/pipeline/search_router.py tests/test_search_router.py
git commit -m "feat: add phase-aware search router with TTL cache and parallel Phase 1 dispatch"
```

---

## Task 5 — Update phase callers

**Files:**
- Modify: `src/pipeline/government_search.py`
- Modify: `src/pipeline/university_search.py`
- Modify: `src/pipeline/open_search.py`

- [ ] **Step 1: `government_search.py` — pass `query_type="gov"` and use `_is_official_url`**

In `_search_government_queries()`, change line:
```python
raw = multi_search(query)
```
to:
```python
raw = multi_search(query, query_type="gov")
```

Replace the domain check block:
```python
is_gov = any(dom in url.lower() for dom in config.GOVERNMENT_PRIORITY_DOMAINS)
if not is_gov:
    continue
```
with:
```python
is_gov = config._is_official_url(url)
if not is_gov:
    continue
```

- [ ] **Step 2: `university_search.py` — pass `query_type="site"`**

In `_ddg_search_raw()`, change:
```python
return _multi_search(query, max_results=max_results)
```
to:
```python
return _multi_search(query, max_results=max_results, query_type="site")
```

- [ ] **Step 3: `open_search.py` — pass `query_type="open"` and use `_is_official_url`**

In `search_open()`, change:
```python
raw = multi_search(query, max_results=config.MAX_RESULTS_PER_QUERY)
```
to:
```python
raw = multi_search(query, max_results=config.MAX_RESULTS_PER_QUERY, query_type="open")
```

Replace `_is_mexican_official_url` function with:
```python
def _is_official_url_for_active_countries(url: str) -> bool:
    return config._is_official_url(url)
```

Update its two call sites from `_is_mexican_official_url(url)` to `_is_official_url_for_active_countries(url)`.

- [ ] **Step 4: Verify import chain**

```
python -c "
from src.pipeline.government_search import search_government_sources
from src.pipeline.university_search import _ddg_search_raw
from src.pipeline.open_search import search_open
print('all imports ok')
"
```
Expected: `all imports ok`

- [ ] **Step 5: Commit**

```bash
git add src/pipeline/government_search.py src/pipeline/university_search.py src/pipeline/open_search.py
git commit -m "feat: pass query_type to multi_search in all phase callers; replace hardcoded domain checks"
```

---

## Task 6 — `main.py`: record_validation + `--profile`

**Files:**
- Modify: `main.py`

- [ ] **Step 1: Add `record_validation` in `_extract_all` after extraction result merging**

In `_extract_all`, after line 137 (`results.append(original_doc)` inside the `finally` block), insert:

```python
                if getattr(config, "SEARCH_METRICS_ENABLED", True):
                    from src.pipeline.search_metrics import get_metrics
                    survived = (
                        original_doc.get("extraction_error") is None
                        and len(original_doc.get("extracted_text", "")) > 0
                    )
                    get_metrics().record_validation(original_doc.get("url", ""), survived)
```

- [ ] **Step 2: Add `--profile` argument to `_parse_args`**

After the `--verbose` argument block (around line 467), add:

```python
    parser.add_argument(
        "--profile",
        type=str,
        default=None,
        choices=["fast", "balanced", "deep"],
        metavar="PROFILE",
        help="Perfil de ejecución de búsqueda: fast | balanced | deep (default: balanced)"
    )
```

- [ ] **Step 3: Apply profile in `__main__` block before `run_pipeline`**

After `if args.researcher:` block (around line 476), add:

```python
    if args.profile:
        config.SEARCH_PROFILE = args.profile
        config._apply_profile(args.profile)
        logger.info(f"[main] Perfil de búsqueda: {args.profile}")
```

- [ ] **Step 4: Add `export_report` call after `export_to_excel`**

After line `output_file = excel_exporter.export_to_excel(...)` (around line 387), add:

```python
    if getattr(config, "SEARCH_METRICS_ENABLED", True):
        from src.pipeline.search_metrics import get_metrics
        try:
            get_metrics().export_report(config.OUTPUT_DIR)
            logger.info(f"[main] Reporte de métricas guardado en {config.OUTPUT_DIR}/metrics/")
        except Exception as e:
            logger.warning(f"[main] Error exportando métricas: {e}")
```

Also flush the cache at end of run (before the elapsed log):
```python
    from src.pipeline import search_router
    search_router._flush_cache()
```

- [ ] **Step 5: Verify CLI parses new flag**

```
python main.py --help | grep profile
```
Expected: line containing `--profile PROFILE`

- [ ] **Step 6: Commit**

```bash
git add main.py
git commit -m "feat: record_validation in _extract_all, add --profile CLI flag, export metrics report"
```

---

## Task 7 — `document_classifier.py`: record_classification

**Files:**
- Modify: `src/pipeline/document_classifier.py`

- [ ] **Step 1: Add metrics call at the end of `classify()`**

In `classify()`, after line `document["heuristic_label"] = label` (line 96), add:

```python
    if getattr(config, "SEARCH_METRICS_ENABLED", True):
        is_extracted = (
            document.get("extraction_error") is None
            and len(document.get("extracted_text", "")) > 0
        )
        if is_extracted:
            from src.pipeline.search_metrics import get_metrics
            get_metrics().record_classification(
                document.get("url", ""),
                is_normative=(label != "BAJA"),
            )
```

- [ ] **Step 2: Run classifier tests to confirm no regression**

```
pytest tests/test_document_classifier.py -v
```
Expected: all PASS.

- [ ] **Step 3: Commit**

```bash
git add src/pipeline/document_classifier.py
git commit -m "feat: record_classification in document_classifier for false_positive_rate metric"
```

---

## Task 8 — `.env.example`: new keys

**Files:**
- Modify: `.env.example`

- [ ] **Step 1: Add new variables to `.env.example`**

Open `.env.example` and add after the `BRAVE_API_KEY=` line:

```
# Serper.dev — Google Search API proxy, 2500 queries/mes gratis, $50/mes = 50k
# Obtener en: https://serper.dev
SERPER_API_KEY=

# Perfil de ejecución: fast | balanced | deep  (default: balanced)
# fast: DDG+cache, sin Serper, TTL largo — para re-runs locales
# balanced: Serper bulk + CSE gov + Brave open — producción GCP
# deep: máximo recall, paralelo en todas las fases — onboarding de nuevo país
SEARCH_PROFILE=balanced

# Países activos LATAM (separados por coma). Solo MX por ahora; expandir para LATAM completo.
ACTIVE_COUNTRIES=MX

# Feature flags (true/false). Los flags individuales sobrescriben el perfil.
# SEARCH_ROUTER_ENABLED=true
# SEARCH_PARALLEL_GOV=true
# SEARCH_METRICS_ENABLED=true
```

- [ ] **Step 2: Commit**

```bash
git add .env.example
git commit -m "docs: add SERPER_API_KEY, SEARCH_PROFILE, ACTIVE_COUNTRIES to .env.example"
```

---

## Task 9 — Integration smoke test

- [ ] **Step 1: Run full test suite**

```
pytest tests/ -v
```
Expected: all tests PASS. Test count ≥ previous + 14 new tests.

- [ ] **Step 2: Smoke test config + router import chain**

```
python -c "
import config
print('profile:', config.SEARCH_PROFILE)
print('routing_table gov:', config.ROUTING_TABLE.get('gov'))
from src.pipeline.search_router import router_search
from src.pipeline.search_metrics import get_metrics
print('metrics singleton:', get_metrics())
print('all ok')
"
```
Expected output:
```
profile: balanced
routing_table gov: {'primary': ['cse', 'brave'], 'secondary': 'serper', 'parallel': True}
metrics singleton: <src.pipeline.search_metrics.SearchMetrics object at 0x...>
all ok
```

- [ ] **Step 3: Smoke test multi_search backward compat (no query_type)**

```
python -c "
import config; config.SEARCH_ROUTER_ENABLED = False  # force legacy
from src.pipeline.search_backends import multi_search
# This should run the legacy cascade without error (may return [] if no API keys)
result = multi_search('test query', max_results=1)
print('legacy cascade result type:', type(result))
"
```
Expected: `legacy cascade result type: <class 'list'>` (no exception).

- [ ] **Step 4: Final commit**

```bash
git add .
git commit -m "chore: search architecture complete — router, metrics, Serper, profiles, LATAM config"
```

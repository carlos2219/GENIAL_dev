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

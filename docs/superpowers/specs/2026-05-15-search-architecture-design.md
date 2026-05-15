# Search Architecture — Phase-Aware Router with Metrics and LATAM Extensibility

**Date:** 2026-05-15
**Status:** Approved
**Author:** Carlos Auquilla

---

## 1. Motivation

The current `search_backends.py` implements a single cascade (CSE → Brave → scraping → DDG) applied uniformly to all queries regardless of phase or importance. This produces three critical failures in GCP production:

1. **Google CSE exhausts at query 101** (100 free/day) — all Phase 2 bulk load falls to DDG.
2. **Brave API key is empty** — the second cascade slot never activates.
3. **`googlesearch-python` is blocked on GCP** — slot 3 is dead code in production.

The effective cascade on GCP today is: CSE (100 queries) → DDG (everything else).

For a full Mexico run (~50k queries) and LATAM scale (50k–100k queries/month), this is unsustainable. Different phases have fundamentally different requirements: Phase 1 government queries need maximum recall on a small volume; Phase 2 university queries need cost-efficient bulk throughput; Phase 3 open queries benefit from index diversity.

---

## 2. Goals

- **Recall** — maximize discovery of normative documents from official sources (.gob.*, .edu.*)
- **Cost** — operate within $20–80/month at 50k–100k queries/month LATAM scale
- **LATAM extensibility** — expand to new countries by editing `config.py`, zero code changes
- **Observability** — per-backend, per-phase, per-run quality metrics including post-extraction validation
- **Backward compatibility** — legacy callers (`multi_search(query)`) work unchanged

---

## 3. Module Structure

```
src/pipeline/
├── search_backends.py     # MODIFIED: +Serper.dev backend, +TTL cache, +metrics hooks
├── search_router.py       # NEW: phase-aware dispatcher, parallel Phase 1, profile logic
└── search_metrics.py      # NEW: thread-safe collector, JSON/CSV export
```

**Changes to existing files:**

| File | Change |
|---|---|
| `search_backends.py` | Add `_serper_search()`, TTL on DDG cache, `_backend_tag` on results, remove dead scraping slot from cascade |
| `search_router.py` | New — routing table, profile loader, parallel dispatcher |
| `search_metrics.py` | New — `SearchMetrics` singleton, `record_query()`, `record_validation()`, `export_report()` |
| `government_search.py` | `multi_search(q)` → `multi_search(q, query_type="gov")` |
| `university_search.py` | `multi_search(q)` → `multi_search(q, query_type="site")` |
| `open_search.py` | `multi_search(q)` → `multi_search(q, query_type="open")` |
| `document_extractor.py` | Call `SearchMetrics.record_validation(url, survived)` after each extraction |
| `document_classifier.py` | Call `SearchMetrics.record_classification(url, is_false_positive)` after heuristic scoring |
| `config.py` | Add Serper key, TTL settings, profiles, feature flags, `LATAM_COUNTRIES`, `OFFICIAL_DOMAIN_PATTERNS` |
| `.env` / `.env.example` | Add `SERPER_API_KEY=`, `SEARCH_PROFILE=balanced` |

---

## 4. Backend Inventory

| Backend | Free quota | Paid cost | GCP compatible | Index |
|---|---|---|---|---|
| Google CSE | 100/day (~3k/mo) | $5/1,000 | Yes | Google |
| Brave Search API | 2,000/mo | ~$3–5/1,000 | Yes | Independent |
| Serper.dev | 2,500/mo | $50/mo = 50k; $100/mo = 150k | Yes | Google proxy |
| DuckDuckGo (ddgs) | Unlimited (scraping) | Free | Unreliable | DDG |

**Serper.dev is added as the bulk workhorse.** It returns real Google results via a proxy layer that handles IP reputation, works from GCP without restrictions, and costs $1/1,000 at the Basic tier.

---

## 5. Phase-Aware Routing Table

```python
ROUTING_TABLE = {
    "gov":  {"primary": ["cse", "brave"],  "secondary": "serper", "parallel": True},
    "site": {"primary": ["serper"],        "secondary": "ddg",    "parallel": False},
    "open": {"primary": ["brave"],         "secondary": "serper", "parallel": False},
    None:   {"primary": ["cse", "brave", "ddg"], "secondary": None, "parallel": False},
}
```

**Phase 1 (`"gov"`) — parallel dual-engine:**
- CSE and Brave fire simultaneously via `ThreadPoolExecutor(max_workers=2)`.
- Results are merged and deduplicated by URL; duplicates keep the higher-ranked entry.
- If one backend fails, the other's results are returned alone (fault-tolerant OR).
- Fallback to Serper if both primary backends return zero results.

**Phase 2 (`"site"`) — Serper bulk:**
- Serper handles all `site:domain` queries. DDG as last-resort fallback.
- CSE quota is preserved entirely for Phase 1.

**Phase 3 (`"open"`) — Brave for diversity:**
- Brave's independent index reduces overlap with Google-dominated Phase 1/2 results.
- Serper fallback if Brave returns nothing.

**Legacy (`query_type=None`):**
- Original cascade: CSE → Brave → DDG. Dead `googlesearch-python` slot removed.
- `query_type=None`: router is active but uses the legacy cascade for that specific query (backward-compatible callers).
- `SEARCH_ROUTER_ENABLED=False`: overrides all query types — every query uses the legacy cascade regardless of what `query_type` is passed. This is the kill-switch for the entire routing layer.

---

## 6. Execution Profiles

Activated via `--profile fast|balanced|deep` (CLI) or `SEARCH_PROFILE=balanced` (.env).
Individual feature flags always override the active profile.

| Parameter | `fast` | `balanced` (default) | `deep` |
|---|---|---|---|
| Gov parallel | No (CSE only) | Yes (CSE + Brave) | Yes (CSE + Brave + Serper) |
| Phase 2 backend | DDG + cache | Serper.dev | Serper.dev + DDG merge |
| Phase 3 backend | DDG | Brave → Serper | Brave + Serper parallel |
| TTL gov (days) | 14 | 7 | 1 |
| TTL site (days) | 7 | 14 | 3 |
| TTL open (days) | 7 | 3 | 1 |
| Max results/query | 5 | 10 | 20 |
| Est. cost MX run | ~$0 | ~$5–10 | ~$20–35 |
| Est. time MX run | ~15 min | ~45 min | ~2–3 h |

`fast` is designed for development and re-runs; `balanced` for scheduled production runs; `deep` for initial country onboarding or audits.

---

## 7. Feature Flags

All flags are readable from `.env` (string → bool coercion). Profile is a preset of these flags.

```python
SEARCH_ROUTER_ENABLED   = True   # False → legacy cascade, no routing
SEARCH_PARALLEL_GOV     = True   # False → sequential CSE then Brave for Phase 1
SEARCH_METRICS_ENABLED  = True   # False → zero overhead, no report generated
SEARCH_PROFILE          = "balanced"
CACHE_TTL_GOV_DAYS      = 7
CACHE_TTL_SITE_DAYS     = 14
CACHE_TTL_OPEN_DAYS     = 3
SERPER_API_KEY          = ""     # required for site/open routes in balanced+deep
```

---

## 8. TTL-Aware Cache

The existing `ddg_search_cache.json` is extended to a unified `search_cache.json` with per-entry TTL.

**Cache key:** `MD5(f"{backend}|{query}|{max_results}")` — backend is now part of the key so CSE and Serper results for the same query are cached independently.

**Entry schema:**
```json
{
  "key": "abc123",
  "backend": "serper",
  "query_type": "site",
  "results": [...],
  "cached_at": "2026-05-15T14:00:00Z",
  "ttl_days": 14
}
```

**Expiry:** On cache read, `(now - cached_at).days > ttl_days` → cache miss, re-fetch.

**Migration:** On first run with new code, the old `ddg_search_cache.json` is read as-is (no TTL = treated as 7-day TTL legacy entries), then written to `search_cache.json` in the new format.

---

## 9. Metrics Layer

### `SearchMetrics` (singleton, thread-safe)

Three recording points in the pipeline:

```
router call          → record_query(backend, phase, latency_ms, n_results, urls)
document_extractor   → record_validation(url, survived: bool)
document_classifier  → record_classification(url, is_normative: bool)
```

### Metrics computed per backend × phase

| Metric | Definition |
|---|---|
| `queries_served` | Total queries routed to this backend |
| `hit_rate` | % queries returning ≥ 1 result |
| `avg_results_per_query` | Mean result count |
| `pdf_yield` | % URLs ending in `.pdf` or with `content_type=pdf` |
| `official_domain_ratio` | % URLs matching `OFFICIAL_DOMAIN_PATTERNS` for active countries |
| `latency_p50_ms` | Median latency across queries |
| `latency_p95_ms` | 95th-percentile latency |
| `validated_document_rate` | % URLs that survived extraction (not 404, not empty, not error) |
| `false_positive_rate` | % extracted docs discarded by heuristic as non-normative (score < BAJA threshold) |

### `false_positive_rate` integration

A doc is **successfully extracted** when `extraction_error is None` AND `len(extracted_text) > 0`.

`document_classifier.py` after scoring each doc:
- If `heuristic_score < HEURISTIC_MEDIUM_THRESHOLD` AND doc was successfully extracted → `record_classification(url, is_normative=False)`.
- Otherwise → `record_classification(url, is_normative=True)` (includes docs that failed extraction, which are excluded from the false-positive denominator).

`false_positive_rate = non_normative_extracted / total_extracted` per backend×phase.

### `_backend_tag` propagation

Every result dict from any backend includes:
```python
{"url": "...", "title": "...", "body": "...", "_backend_tag": "serper", "_query_type": "site"}
```

This tag is preserved through deduplication, extraction, and classification — it's the join key used by `SearchMetrics` to attribute validation and classification outcomes back to the originating backend.

### Report output

Generated at pipeline end (and progressively on interrupt) to:
- `output/metrics/run_YYYYMMDD_HHMMSS.json` — full structured report
- `output/metrics/run_YYYYMMDD_HHMMSS.csv` — one row per backend×phase×country, for Excel

**Report structure:**
```
summary:
  profile, run_id, duration_seconds, total_queries, total_urls_found,
  active_countries, serper_queries_billed, cse_queries_billed

by_backend_and_phase:
  [{backend, phase, country, queries_served, hit_rate, avg_results,
    pdf_yield, official_domain_ratio, latency_p50_ms, latency_p95_ms,
    validated_document_rate, false_positive_rate}]

cache_stats:
  {hits, misses, expired, by_query_type}

cost_estimate:
  {serper_queries: N, serper_cost_usd: X, cse_queries: N, cse_cost_usd: Y, total_usd: Z}
```

---

## 10. LATAM Extensibility

### `LATAM_COUNTRIES` and `OFFICIAL_DOMAIN_PATTERNS`

```python
LATAM_COUNTRIES = {
    "MX": {
        "tld": ".mx",
        "lang": "es",
        "brave_country": "MX",
        "serper_gl": "mx",
    },
    "CO": {
        "tld": ".co",
        "lang": "es",
        "brave_country": "CO",
        "serper_gl": "co",
    },
    "AR": {
        "tld": ".ar",
        "lang": "es",
        "brave_country": "AR",
        "serper_gl": "ar",
    },
}

OFFICIAL_DOMAIN_PATTERNS = {
    "MX": [r"\.gob\.mx$", r"\.edu\.mx$"],
    "CO": [r"\.gov\.co$", r"\.edu\.co$"],
    "AR": [r"\.gob\.ar$", r"\.edu\.ar$"],
    "PE": [r"\.gob\.pe$", r"\.edu\.pe$"],
    "CL": [r"\.gob\.cl$", r"\.edu\.cl$"],
}

ACTIVE_COUNTRIES = ["MX"]  # expand here to add countries
```

`official_domain_ratio` in metrics uses the patterns for the doc's country (resolved from URL TLD). Domain filters in `government_search.py`, `open_search.py`, and `university_search.py` replace hardcoded `.gob.mx`/`.edu.mx` checks with `_is_official_url(url, country)` using the compiled regex patterns.

**Adding a new country:** add entry to `LATAM_COUNTRIES`, add patterns to `OFFICIAL_DOMAIN_PATTERNS`, add country code to `ACTIVE_COUNTRIES`, and provide country-specific query lists (same structure as `GOVERNMENT_QUERIES`). No code changes required.

---

## 11. Backward Compatibility

`multi_search(query, max_results, pause)` in `search_backends.py` is preserved with the same signature. When called without `query_type`, it delegates to the legacy cascade (CSE → Brave → DDG, `SEARCH_ROUTER_ENABLED` = False behavior). This means any caller that is not updated continues to work correctly.

The three phase modules (`government_search.py`, `university_search.py`, `open_search.py`) are updated to pass `query_type` as part of this implementation, but the change is a single-argument addition per call site — no structural changes to those files.

---

## 12. Future Hook: Empirical Backend Selection

`ROUTER_TABLE` is defined as a plain dict in `config.py`. After several production runs, `output/metrics/` contains enough data to rank backends by `validated_document_rate × official_domain_ratio` per phase and country. A future `router_optimizer.py` can read those reports and rewrite `ROUTER_TABLE` automatically. This implementation does not build that optimizer — it only ensures the data and the configurable routing table exist.

---

## 13. Files Not Changed

- `site_crawler.py` — crawl logic is orthogonal to search routing
- `deduplicator.py` — URL and hash dedup are unaffected
- `ai_classifier.py` — OpenAI classification is downstream of search
- `matrix_builder.py` — matrix construction is unaffected
- `excel_exporter.py` — gets one new call: `SearchMetrics.export_report(OUTPUT_DIR)` at the end

---

## 14. Out of Scope

- Tavily / Exa integration — not needed at this volume/budget; revisit if `validated_document_rate` for Serper+CSE falls below 0.25
- SearXNG self-hosted — adds operational complexity without clear quality gain over Serper at this budget
- PDF content extraction from search snippets — separate concern from routing
- Bing Search API — redundant given Serper covers Google index at better cost

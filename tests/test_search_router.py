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
        from src.pipeline.search_router import _call_backend
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

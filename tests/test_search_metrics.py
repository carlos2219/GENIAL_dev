# tests/test_search_metrics.py
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
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

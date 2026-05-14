import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.pipeline.url_filter import is_excluded, looks_normative, filter_and_rank
from src.pipeline.deduplicator import normalize_url


def test_facebook_is_excluded():
    assert is_excluded("https://www.facebook.com/unam/posts/123") is True


def test_twitter_is_excluded():
    assert is_excluded("https://twitter.com/sep_mx/status/456") is True


def test_news_site_is_excluded():
    assert is_excluded("https://www.eluniversal.com.mx/ciencia/ia-en-educacion") is True


def test_university_normativa_not_excluded():
    assert is_excluded("https://www.unam.mx/reglamentos/uso-ia.pdf") is False


def test_gob_mx_not_excluded():
    assert is_excluded("https://www.dof.gob.mx/nota_detalle.php?codigo=123") is False


def test_looks_normative_reglamento():
    # looks_normative requires BOTH a normative keyword and an AI keyword
    assert looks_normative(
        "https://unam.mx/reglamentos/uso-ia.pdf",
        title="Reglamento de uso de inteligencia artificial"
    ) is True


def test_looks_normative_lineamiento():
    assert looks_normative(
        "https://ipn.mx/lineamientos-ia",
        snippet="lineamientos sobre inteligencia artificial y machine learning"
    ) is True


def test_looks_normative_noticia_false():
    # No AI keyword in URL/title/snippet → returns False
    assert looks_normative("https://unam.mx/noticias/evento-conferencia-2024") is False


def test_filter_and_rank_removes_excluded():
    docs = [
        {"url": "https://facebook.com/unam", "title": "", "snippet": ""},
        {"url": "https://unam.mx/reglamentos/ia.pdf", "title": "Reglamento IA", "snippet": "inteligencia artificial"},
    ]
    result = filter_and_rank(docs)
    urls = [d["url"] for d in result]
    assert "https://facebook.com/unam" not in urls
    assert any("unam.mx" in u for u in urls)


def test_normalize_url_strips_tracking_params():
    url = "https://unam.mx/reglamento?utm_source=newsletter&utm_medium=email"
    normalized = normalize_url(url)
    assert "utm_source" not in normalized
    assert "utm_medium" not in normalized


def test_normalize_url_unifies_http_https():
    url_http  = normalize_url("http://unam.mx/reglamento/")
    url_https = normalize_url("https://unam.mx/reglamento/")
    assert url_http == url_https


def test_normalize_url_strips_www():
    with_www    = normalize_url("https://www.unam.mx/reglamento")
    without_www = normalize_url("https://unam.mx/reglamento")
    assert with_www == without_www

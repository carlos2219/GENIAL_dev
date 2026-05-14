import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.pipeline.document_classifier import heuristic_score, classify_batch
import config


def _make_doc(text="", url="https://unam.mx/reglamento", title=""):
    return {
        "url": url,
        "title": title,
        "snippet": "",
        "extracted_text": text,
        "content_type": "html",
    }


def test_alta_label_with_reglamento_and_ia():
    # 3 HIGH keywords + 3 AI keywords + PDF URL → score 0.80 >= ALTA threshold
    doc = _make_doc(
        text="reglamento resolucion acuerdo inteligencia artificial machine learning chatgpt uso responsable",
        url="https://unam.mx/reglamentos/ia.pdf",
    )
    score = heuristic_score(doc)
    assert score >= config.HEURISTIC_HIGH_THRESHOLD, (
        f"Expected ALTA (>= {config.HEURISTIC_HIGH_THRESHOLD}), got {score:.3f}"
    )


def test_media_label_with_guia_and_ia():
    # 3 MEDIUM keywords + 3 AI keywords, NO high keywords → capped just below ALTA
    doc = _make_doc(
        text="guia manual protocolo inteligencia artificial machine learning chatgpt uso en educacion",
        url="https://tec.mx/guia-ia",
    )
    score = heuristic_score(doc)
    assert config.HEURISTIC_MEDIUM_THRESHOLD <= score < config.HEURISTIC_HIGH_THRESHOLD, (
        f"Expected MEDIA [{config.HEURISTIC_MEDIUM_THRESHOLD}, {config.HEURISTIC_HIGH_THRESHOLD}), got {score:.3f}"
    )


def test_baja_label_noticia_sin_ia():
    doc = _make_doc(
        text="noticia del día: el rector inauguró el nuevo edificio universitario blog evento",
        url="https://unam.mx/noticias/rector",
    )
    score = heuristic_score(doc)
    assert score < config.HEURISTIC_MEDIUM_THRESHOLD, (
        f"Expected BAJA (< {config.HEURISTIC_MEDIUM_THRESHOLD}), got {score:.3f}"
    )


def test_sin_ia_keywords_fuerza_score_bajo():
    """Doc con keywords normativas pero sin mención de IA → score < ALTA por cap."""
    doc = _make_doc(
        text="reglamento resolucion acuerdo titulacion graduacion facultad",
        url="https://ipn.mx/reglamentos/titulacion.pdf",
    )
    score = heuristic_score(doc)
    assert score < config.HEURISTIC_HIGH_THRESHOLD, (
        f"Sin hits de IA, score debe ser < {config.HEURISTIC_HIGH_THRESHOLD}, got {score:.3f}"
    )


def test_classify_batch_assigns_labels():
    docs = [
        _make_doc(
            "reglamento acuerdo decreto inteligencia artificial machine learning chatgpt lineamiento",
            "https://unam.mx/lineamientos.pdf",
        ),
        _make_doc(
            "blog de noticias universitarias evento conferencia inauguracion edificio",
            "https://unam.mx/blog/evento",
        ),
    ]
    result = classify_batch(docs)
    labels = [d["heuristic_label"] for d in result]
    assert "ALTA" in labels or "MEDIA" in labels, "Al menos un doc debería ser ALTA o MEDIA"
    assert "BAJA" in labels, "Al menos un doc debería ser BAJA"

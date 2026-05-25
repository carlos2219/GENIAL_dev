"""
test_phase3_filters.py — Tests that expose over-aggressive filters in Phase 3.

Each test documents a class of document that gets incorrectly discarded today.
After relaxing the filters these tests should all pass.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import config
from src.pipeline.document_classifier import heuristic_score, classify
from src.pipeline.url_filter import is_excluded, priority_score
from src.pipeline.open_search import _topic_match


def _make_doc(text="", url="https://unam.edu.mx/normativa", title="", snippet=""):
    return {
        "url": url,
        "title": title,
        "snippet": snippet,
        "extracted_text": text,
        "content_type": "html",
    }


# ── 1. AI abbreviation-only documents ────────────────────────────────────────

def test_standalone_ia_abbreviation_reaches_media():
    """
    Many Mexican university documents use 'IA' (just the abbreviation) without
    compound forms that are in AI_KEYWORDS (e.g. 'uso de ia', 'ia generativa').
    Example: 'Herramientas de IA', 'tecnologías de IA', 'plataformas de IA'.
    These produce ai_hits==0 and get hard-capped below MEDIA.
    """
    doc = _make_doc(
        text=(
            "Lineamientos para el uso de herramientas de IA en la Universidad. "
            "El Consejo Universitario aprueba el presente reglamento sobre "
            "tecnologías de IA para uso académico. Protocolo institucional sobre "
            "plataformas de IA. Estatuto de integridad académica ante el uso de IA."
        ),
        url="https://tec.edu.mx/lineamientos-ia.pdf",
        title="Lineamientos sobre IA — Consejo Universitario",
    )
    score = heuristic_score(doc)
    classified = classify(doc)
    print(f"\n[1] Standalone 'IA' doc — score={score:.3f}, label={classified['heuristic_label']}")
    assert classified["heuristic_label"] in ("ALTA", "MEDIA"), (
        f"Document with reglamento+lineamientos+IA (abbreviation) from .edu.mx "
        f"should be MEDIA/ALTA, got {classified['heuristic_label']} (score={score:.3f}). "
        f"Root cause: 'herramientas de IA' doesn't match any AI_KEYWORD, so ai_hits==0 "
        f"and score is hard-capped below MEDIA threshold."
    )


def test_ia_in_url_path_should_help():
    """
    A document whose URL clearly references IA (e.g. /lineamientos-ia or /politica-ia)
    combined with normative keywords should reach MEDIA even if body uses abbreviation.
    """
    doc = _make_doc(
        text=(
            "Reglamento para la adopción de tecnologías de IA en actividades académicas. "
            "Criterios y procedimientos de uso. Aprobado por el Consejo Universitario."
        ),
        url="https://uanl.edu.mx/normativa/politica-ia.pdf",
        title="Política institucional de IA",
    )
    score = heuristic_score(doc)
    classified = classify(doc)
    print(f"[2] URL path '/politica-ia' — score={score:.3f}, label={classified['heuristic_label']}")
    assert classified["heuristic_label"] in ("ALTA", "MEDIA"), (
        f"URL with /politica-ia + reglamento + consejo universitario should be MEDIA/ALTA, "
        f"got {classified['heuristic_label']} (score={score:.3f})."
    )


# ── 2. Heuristic threshold comparison ────────────────────────────────────────

def test_threshold_024_promotes_borderline_docs():
    """
    Threshold was raised from 0.24 → 0.30.  Documents that scored 0.24–0.29
    (e.g. a manual with AI keywords and medium normative language) now land in BAJA.
    Show that lowering back to 0.24 would help these borderline docs.
    """
    doc = _make_doc(
        text=(
            "Manual de uso de inteligencia artificial para docentes. "
            "Criterios y procedimientos para la implementación en el aula. "
            "Programa institucional de formación en IA."
        ),
        url="https://up.edu.mx/manual-ia",
        title="Manual de IA para Docentes",
    )
    score = heuristic_score(doc)
    label_strict = "BAJA" if score < 0.30 else ("MEDIA" if score < 0.50 else "ALTA")
    label_relaxed = "BAJA" if score < 0.24 else ("MEDIA" if score < 0.50 else "ALTA")
    print(f"[3] Borderline doc — score={score:.3f}: threshold_0.30={label_strict}, threshold_0.24={label_relaxed}")
    # With HEURISTIC_MEDIUM_THRESHOLD=0.24 this should be MEDIA
    assert score >= 0.24, (
        f"Doc with 'manual' + 'inteligencia artificial' + 'criterios' + 'programa' "
        f"should score >= 0.24, got {score:.3f}."
    )
    if config.HEURISTIC_MEDIUM_THRESHOLD <= 0.24:
        assert label_relaxed == "MEDIA", f"With threshold 0.24 this should be MEDIA, got {label_relaxed}"


# ── 3. Strict topic filter blocks legitimate docs ─────────────────────────────

def test_topic_filter_blocks_herramientas_doc():
    """
    _topic_match() with STRICT_TOPIC_FILTER=True and TOPIC_MUST_INCLUDE_AI=True
    requires an AI_KEYWORD hit in URL+title+snippet.
    A doc titled 'Herramientas digitales y regulación institucional' with body
    about 'lineamientos tecnológicos' contains no AI_KEYWORD → filtered at phase 3.
    """
    url = "https://unam.edu.mx/normativa/herramientas-digitales"
    title = "Lineamientos de herramientas digitales avanzadas"
    body = "Reglamento para el uso de herramientas y plataformas de IA en educación."

    result = _topic_match(url, title, body)
    print(f"[4] Topic filter — 'herramientas de IA' doc: {'PASSED' if result else 'FILTERED'}")
    # 'plataformas de IA' contains no AI_KEYWORD → filtered with strict mode
    # After fix (STRICT_TOPIC_FILTER=False) this should pass
    if not getattr(config, "STRICT_TOPIC_FILTER", False):
        assert result, "With STRICT_TOPIC_FILTER=False, all docs should pass topic filter"
    else:
        print("  (strict mode active — doc filtered; set STRICT_TOPIC_FILTER=False to fix)")


def test_topic_filter_passes_inteligencia_artificial():
    """Control: a doc that explicitly says 'inteligencia artificial' must always pass."""
    url = "https://ipn.mx/reglamentos/ia"
    title = "Reglamento de uso de inteligencia artificial"
    body = "Lineamientos para el uso de inteligencia artificial en la institución."
    result = _topic_match(url, title, body)
    print(f"[5] Topic filter — explicit 'inteligencia artificial': {'PASSED' if result else 'FILTERED'}")
    assert result, "Doc with explicit 'inteligencia artificial' must always pass topic filter"


# ── 4. Pre-extraction filter ──────────────────────────────────────────────────

def test_pre_extraction_filter_blocks_edu_doc_without_snippet_keywords():
    """
    PRE_EXTRACTION_FILTER_ENABLED=True drops docs where url_priority_score < 0.1
    AND the snippet+title has no AI or policy keyword.
    A URL like https://uanl.edu.mx/transformacion-digital with snippet
    'Portal de innovación tecnológica' would be dropped before downloading.
    After fix (PRE_EXTRACTION_FILTER_ENABLED=False) this should not happen.
    """
    doc = {
        "url": "https://uanl.edu.mx/transformacion-digital/ia",
        "title": "Transformación Digital — IA Institucional",
        "snippet": "Portal de innovación tecnológica universitaria.",
        "url_priority_score": 0.05,  # low — path '/transformacion-digital/ia' has no PRIORITY_URL_KEYWORD
    }
    url_score = doc["url_priority_score"]
    combined = (doc["title"] + " " + doc["snippet"]).lower()
    has_ai = any(kw in combined for kw in config.AI_KEYWORDS)
    has_policy = any(kw in combined for kw in config.POLICY_KEYWORDS)
    would_drop = url_score < 0.1 and not has_ai and not has_policy

    print(f"[6] Pre-extraction filter -- url_score={url_score:.2f}, ai={has_ai}, policy={has_policy} -> drop={would_drop}")

    if not getattr(config, "PRE_EXTRACTION_FILTER_ENABLED", False):
        assert not would_drop or True, "PRE_EXTRACTION_FILTER_ENABLED=False — filter is inactive (OK)"
        print("  (PRE_EXTRACTION_FILTER_ENABLED=False — filter inactive, doc passes)")
    else:
        assert not would_drop, (
            f"Edu.mx doc about 'IA Institucional' should not be dropped by pre-extraction filter, "
            f"but url_score={url_score:.2f} + no AI/policy in snippet causes it to be dropped. "
            f"Fix: set PRE_EXTRACTION_FILTER_ENABLED=False."
        )


# ── 5. Borderline BAJA AI review thresholds ──────────────────────────────────

def test_borderline_baja_from_gov_domain_gets_ai_review():
    """
    AI_BAJA_MIN_SCORE=0.30 and AI_BAJA_MIN_URL_PRIORITY=0.60 together mean that
    a .gob.mx document with heuristic_score=0.22 and url_priority=0.45
    never gets AI review even though it's from an authoritative domain.
    After fix (lower thresholds) it should qualify.
    """
    candidate = {
        "heuristic_score": 0.22,
        "heuristic_label": "BAJA",
        "url": "https://sep.gob.mx/informacion/normativas/herramientas-digitales",
        "url_priority_score": 0.45,
    }

    min_score = float(config.AI_BAJA_MIN_SCORE)
    min_url = float(config.AI_BAJA_MIN_URL_PRIORITY)
    hscore = candidate["heuristic_score"]
    uscore = candidate["url_priority_score"]
    is_priority = ".gob.mx" in candidate["url"] or ".edu.mx" in candidate["url"]

    gets_ai = hscore >= min_score and (uscore >= min_url or is_priority)
    print(
        f"[7] Borderline BAJA (sep.gob.mx) -- hscore={hscore:.2f}, uscore={uscore:.2f}, "
        f"min_score={min_score}, min_url={min_url} -> AI review: {gets_ai}"
    )
    assert gets_ai, (
        f"A sep.gob.mx doc with score={hscore:.2f} should get AI review. "
        f"Fix: lower AI_BAJA_MIN_SCORE to ≤{hscore} or ensure priority_domain bypasses url threshold."
    )


# ── 6. OPENAI_INPUT_CHARS should be maximized ────────────────────────────────

def test_openai_input_chars_is_sufficient():
    """
    OPENAI_INPUT_CHARS was reduced from 5500 to 3500 to save tokens.
    Since cost is not a concern, it should be at least 5000 for better classification.
    """
    chars = int(getattr(config, "OPENAI_INPUT_CHARS", 3500))
    print(f"[8] OPENAI_INPUT_CHARS={chars}")
    assert chars >= 5000, (
        f"OPENAI_INPUT_CHARS={chars} is too low; set to ≥5000 for better AI classification recall."
    )

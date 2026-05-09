"""
document_classifier.py — Clasificación heurística de documentos

Asigna un score numérico y etiqueta ALTA / MEDIA / BAJA
en función de palabras clave encontradas en el texto y la URL.
"""

import re
from typing import Dict

import config


def _count_keywords(text: str, keywords: list) -> int:
    text_l = text.lower()
    return sum(1 for kw in keywords if kw in text_l)


def heuristic_score(document: Dict) -> float:
    """
    Calcula score de relevancia en [0, 1].

    Componentes:
      - keywords de alto valor   → peso 0.4
      - keywords de medio valor  → peso 0.2
      - keywords de IA presentes → peso 0.3
      - penalización keywords bajas → -0.1 por cada hit (min 0)
      - boost PDF                → +0.1
      - boost dominio .gob/.edu  → +0.1
    """
    combined = (
        document.get("url", "") + " " +
        document.get("title", "") + " " +
        document.get("snippet", "") + " " +
        document.get("extracted_text", "")[:3000]
    ).lower()

    high_hits   = _count_keywords(combined, config.HIGH_SCORE_KEYWORDS)
    medium_hits = _count_keywords(combined, config.MEDIUM_SCORE_KEYWORDS)
    low_hits    = _count_keywords(combined, config.LOW_SCORE_KEYWORDS)
    ai_hits     = _count_keywords(combined, config.AI_KEYWORDS)

    # Normalizar hits (evitar unbounded growth)
    score = 0.0
    score += min(high_hits   / 3.0, 1.0) * 0.40
    score += min(medium_hits / 3.0, 1.0) * 0.20
    score += min(ai_hits     / 3.0, 1.0) * 0.30
    # Penalización por señales de convocatoria/noticias (hasta -0.25 para evitar FP)
    score -= min(low_hits / 3.0, 0.25)

    url = document.get("url", "").lower()
    if url.endswith(".pdf") or ".pdf?" in url:
        score += 0.10
    if ".gob.mx" in url or ".edu.mx" in url:
        score += 0.05

    # Sin mención explícita de IA el documento no puede alcanzar MEDIA ni ALTA
    if ai_hits == 0:
        score = min(score, config.HEURISTIC_MEDIUM_THRESHOLD - 0.01)

    return max(0.0, min(score, 1.0))


def classify(document: Dict) -> Dict:
    """
    Agrega al documento:
      - "heuristic_score": float [0,1]
      - "heuristic_label": "ALTA" | "MEDIA" | "BAJA"

    Retorna el documento modificado.
    """
    score = heuristic_score(document)
    document["heuristic_score"] = round(score, 4)

    high_t = float(config.HEURISTIC_HIGH_THRESHOLD)
    med_t  = float(config.HEURISTIC_MEDIUM_THRESHOLD)

    if score >= high_t:
        label = "ALTA"
    elif score >= med_t:
        label = "MEDIA"
    else:
        label = "BAJA"

    document["heuristic_label"] = label
    return document


def classify_batch(documents: list) -> list:
    """Clasifica heurísticamente una lista de documentos."""
    return [classify(doc) for doc in documents]


def filter_for_ai(documents: list) -> list:
    """Retorna sólo documentos con label ALTA o MEDIA (candidatos para IA)."""
    return [d for d in documents if d.get("heuristic_label") in ("ALTA", "MEDIA")]

"""
url_filter.py — Filtrado y puntuación de URLs

Excluye redes sociales, noticias y blogs.
Prioriza PDFs y paths con palabras clave normativas.
"""

import re
from urllib.parse import urlparse
from typing import List, Dict

import config


def _get_domain(url: str) -> str:
    try:
        return urlparse(url).netloc.lower()
    except Exception:
        return ""


def _get_path(url: str) -> str:
    try:
        return urlparse(url).path.lower()
    except Exception:
        return ""


def is_excluded(url: str) -> bool:
    """Devuelve True si la URL debe ser descartada."""
    domain = _get_domain(url)
    for excl in config.EXCLUDED_DOMAINS:
        if excl in domain:
            return True
    # Excluir redes sociales / noticias por patrones adicionales
    if re.search(r"\/(noticias?|blog|evento|podcast|webinar|taller|video|curso)\/", url, re.I):
        return True
    return False


def priority_score(url: str, title: str = "", snippet: str = "") -> float:
    """
    Puntúa la URL en [0, 1]:
      - +0.3 si es PDF
      - +0.4 si el path contiene keywords normativas
      - +0.2 si el título/snippet contiene keywords normativas
      - +0.1 si es dominio .gob.mx / .edu.mx
    """
    score = 0.0
    url_l  = url.lower()
    path   = _get_path(url)
    domain = _get_domain(url)
    text   = (title + " " + snippet).lower()

    if url_l.endswith(".pdf") or "filetype:pdf" in url_l or ".pdf?" in url_l:
        score += 0.3

    for kw in config.PRIORITY_URL_KEYWORDS:
        if kw in path:
            score += 0.4
            break

    for kw in config.PRIORITY_URL_KEYWORDS:
        if kw in text:
            score += 0.2
            break

    if ".gob.mx" in domain or ".edu.mx" in domain:
        score += 0.1

    return min(score, 1.0)


def filter_and_rank(documents: List[Dict], min_score: float = 0.0) -> List[Dict]:
    """
    Recibe lista de dicts con al menos {"url": ...}.
    - Descarta URLs excluidas.
    - Agrega campo "url_priority_score".
    - Ordena descendente por score.
    - Elimina duplicados de URL (mantiene el de mayor score).
    """
    seen_urls: set = set()
    filtered: List[Dict] = []

    for doc in documents:
        url = doc.get("url", "")
        if not url or is_excluded(url):
            continue
        norm = _normalize_url(url)
        if norm in seen_urls:
            continue
        seen_urls.add(norm)

        score = priority_score(url, doc.get("title", ""), doc.get("snippet", ""))
        doc["url_priority_score"] = score

        if score >= min_score:
            filtered.append(doc)

    filtered.sort(key=lambda d: d["url_priority_score"], reverse=True)
    return filtered


def _normalize_url(url: str) -> str:
    """Normaliza URL para comparación — delega a deduplicator.normalize_url
    para garantizar consistencia entre dedup pre y post-extracción."""
    try:
        from deduplicator import normalize_url
        return normalize_url(url)
    except Exception:
        return url.lower().strip()


def is_pdf_url(url: str) -> bool:
    url_l = url.lower().split("?")[0]
    return url_l.endswith(".pdf")


def looks_normative(url: str, title: str = "", snippet: str = "") -> bool:
    """Heurística rápida: ¿parece un documento normativo?"""
    combined = (url + " " + title + " " + snippet).lower()
    normative_hits = sum(1 for kw in config.PRIORITY_URL_KEYWORDS if kw in combined)
    ai_hits        = sum(1 for kw in config.AI_KEYWORDS if kw in combined)
    return normative_hits >= 1 and ai_hits >= 1

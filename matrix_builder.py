"""
matrix_builder.py — Construcción de la Matriz Normativa

Toma documentos clasificados (heurística + IA) y genera las filas
de la matriz final con exactamente las columnas requeridas.
"""

import logging
from typing import List, Dict, Optional

import config

logger = logging.getLogger(__name__)

# Columnas exactas del Excel final
MATRIX_COLUMNS = [
    "Investigador",
    "País",
    "Título de la Norma",
    "Tipo de norma",
    "Estado",
    "Organismo Emisor/Universidad",
    "Dominio",
    "Vínculo con Educación",
    "Dedicación del Texto",
    "Fecha de Publicación",
    "URL Oficial",
    "Observaciones",
    "Ámbito",
]

# Mapeo de valores de ai_classification al español formal
_TIPO_NORMA_MAP = {
    "ley": "Ley",
    "decreto": "Decreto",
    "reglamento": "Reglamento",
    "guía ética": "Guía ética",
    "estrategia nacional": "Estrategia nacional",
    "resolución rectoral": "Resolución rectoral",
    "lineamiento académico": "Lineamiento académico",
    "libro blanco": "Libro blanco",
    "guía pedagógica": "Guía pedagógica",
    "código de ética": "Código de ética",
    "acuerdo institucional": "Acuerdo institucional",
    "otro": "Otro",
    "no aplica": "No especificado",
}

_ESTADO_MAP = {
    "vigente": "Vigente",
    "en proyecto": "En proyecto",
    "derogada": "Derogada",
    "no especificado": "No especificado",
}

_DOMINIO_MAP = {
    "pedagógico": "Pedagógico",
    "administrativo": "Administrativo",
    "protección de datos": "Protección de datos",
    "ética": "Ética",
    "técnico": "Técnico",
    "mixto": "Mixto",
    "no aplica": "No especificado",
}

_VINCULO_MAP = {
    "directo": "Directo",
    "indirecto": "Indirecto",
    "no aplica": "No especificado",
}

_DEDICACION_MAP = {
    "articulado completo": "Articulado completo",
    "sección/capítulo": "Sección/Capítulo",
    "mención breve": "Mención breve",
    "no aplica": "No especificado",
}

_AMBITO_MAP = {
    "nacional": "Nacional",
    "institucional": "Institucional",
    "no aplica": "No especificado",
}


def _safe(value, fallback: str = "No disponible") -> str:
    """Retorna el valor como str o el fallback si está vacío."""
    if value is None:
        return fallback
    s = str(value).strip()
    return s if s and s.lower() not in ("none", "nan", "", "no aplica") else fallback


def _format_date_for_matrix(value: str) -> str:
    """Convierte YYYY-MM-DD a DD/MM/YYYY cuando sea posible."""
    raw = _safe(value, getattr(config, "NO_INDICA_LABEL", "No Indica"))
    if raw in ("No disponible", getattr(config, "NO_INDICA_LABEL", "No Indica")):
        return raw

    parts = raw.split("-")
    if len(parts) == 3 and all(p.isdigit() for p in parts):
        y, m, d = parts
        if len(y) == 4 and len(m) in (1, 2) and len(d) in (1, 2):
            return f"{d.zfill(2)}/{m.zfill(2)}/{y}"
    return raw


def _infer_organismo(document: Dict, ai: Dict) -> str:
    """Infiere el organismo emisor desde la IA o la fuente del documento."""
    organismo = ai.get("organismo_emisor", "")
    if organismo and organismo.lower() not in ("no disponible", "no aplica", ""):
        return organismo

    # Inferir desde el tipo de fuente
    source_type = document.get("source_type", "")
    uni_name    = document.get("university_name", "")

    if source_type == "government":
        url = document.get("url", "").lower()
        if "sep.gob.mx" in url:
            return "Secretaría de Educación Pública (SEP)"
        if "conahcyt" in url or "conacyt" in url:
            return "CONAHCYT"
        if "dof.gob.mx" in url:
            return "Diario Oficial de la Federación"
        if "inai.org.mx" in url:
            return "INAI"
        return "Gobierno de México"
    elif source_type == "university" and uni_name:
        return uni_name
    return "No disponible"


def _infer_titulo(document: Dict, ai: Dict) -> str:
    """Infiere el título de la norma."""
    titulo = ai.get("titulo_norma", "")
    if titulo and titulo.lower() not in ("no disponible", "no aplica", ""):
        return titulo
    # Usar título del documento
    doc_title = document.get("title", "")
    if doc_title:
        return doc_title[:300]
    return "No disponible"


def _is_ai_unavailable(ai: Dict) -> bool:
    """Detecta clasificaciones placeholder cuando IA no estuvo disponible."""
    if not ai:
        return True

    obs = str(ai.get("observaciones", "")).lower()
    if "clasificación no disponible" in obs or "clasificacion no disponible" in obs:
        return True

    return (
        str(ai.get("es_normativa", "")).lower() == "no"
        and str(ai.get("tipo_norma", "")).lower() in ("no aplica", "")
        and str(ai.get("vinculo", "")).lower() in ("no aplica", "")
    )


def _build_row(document: Dict) -> Optional[Dict]:
    """
    Construye una fila de la matriz normativa a partir de un documento clasificado.
    Retorna None si el documento no debe incluirse en la matriz.
    """
    ai = document.get("ai_classification") or {}
    heuristic_label = document.get("heuristic_label", "BAJA")
    has_reliable_ai = bool(ai) and not _is_ai_unavailable(ai)

    # ── Modo con IA ──────────────────────────────────────────────────────────
    if has_reliable_ai:
        is_normativa = ai.get("es_normativa", "no")
        if is_normativa == "no":
            return None
    # ── Modo sin IA (fallback heurístico) ────────────────────────────────────
    else:
        # Sin IA, priorizamos precisión: solo ALTA entra a matriz.
        if heuristic_label != "ALTA":
            return None
        # Poblar ai con valores heurísticos básicos
        ai = {
            "es_normativa": "si",
            "tipo_norma": "otro",
            "estado": "no especificado",
            "dominio": "no aplica",
            "vinculo": "indirecto" if heuristic_label == "MEDIA" else "directo",
            "dedicacion_texto": "no aplica",
            "titulo_norma": document.get("title", "No disponible"),
            "organismo_emisor": document.get("university_name", "") or "No disponible",
            "fecha_publicacion": "No disponible",
            "ambito": "institucional" if document.get("source_type") == "university" else "nacional",
            "observaciones": f"Clasificado heurísticamente sin IA (score={document.get('heuristic_score', 0):.2f}). Requiere validación manual.",
        }

    tipo_raw    = ai.get("tipo_norma", "otro")
    estado_raw  = ai.get("estado", "no especificado")
    dominio_raw = ai.get("dominio", "no aplica")
    vinculo_raw = ai.get("vinculo", "no aplica")
    dedic_raw   = ai.get("dedicacion_texto", "no aplica")
    ambito_raw  = ai.get("ambito", "no aplica")

    row = {
        "Investigador":              config.RESEARCHER_NAME,
        "País":                      config.COUNTRY,
        "Título de la Norma":        _infer_titulo(document, ai),
        "Tipo de norma":             _TIPO_NORMA_MAP.get(tipo_raw.lower(), _safe(tipo_raw, "No especificado")),
        "Estado":                    _ESTADO_MAP.get(estado_raw.lower(), _safe(estado_raw, "No especificado")),
        "Organismo Emisor/Universidad": _infer_organismo(document, ai),
        "Dominio":                   _DOMINIO_MAP.get(dominio_raw.lower(), _safe(dominio_raw, "No especificado")),
        "Vínculo con Educación":     _VINCULO_MAP.get(vinculo_raw.lower(), _safe(vinculo_raw, "No especificado")),
        "Dedicación del Texto":      _DEDIC_MAP_get(dedic_raw),
        "Fecha de Publicación":      _format_date_for_matrix(ai.get("fecha_publicacion")),
        "URL Oficial":               _safe(document.get("url"), "No disponible"),
        "Observaciones":             _safe(ai.get("observaciones"), getattr(config, "SIN_NORMATIVA_LABEL", "Sin normativa específica detectada")),
        "Ámbito":                    _AMBITO_MAP.get(ambito_raw.lower(), _safe(ambito_raw, "No especificado")),
    }

    # Asegurar que ningún campo esté vacío
    for col in MATRIX_COLUMNS:
        if not row.get(col, "").strip():
            row[col] = "No disponible"

    # Metadatos extra (para la hoja resumen)
    row["_source_type"]      = document.get("source_type", "")
    row["_heuristic_label"]  = document.get("heuristic_label", "")
    row["_heuristic_score"]  = document.get("heuristic_score", 0.0)
    row["_university_name"]  = document.get("university_name", "")

    return row


def _DEDIC_MAP_get(raw: str) -> str:
    return _DEDICACION_MAP.get(raw.lower(), _safe(raw, "No especificado"))


def build_matrix(documents: List[Dict]) -> List[Dict]:
    """
    Construye la matriz normativa desde todos los documentos clasificados.

    Solo incluye documentos marcados como normativa por la IA.
    Retorna lista de filas (dicts) con columnas exactas de la matriz.
    """
    logger.info(f"[matrix] Construyendo matriz desde {len(documents)} documentos")

    rows: List[Dict] = []
    for doc in documents:
        row = _build_row(doc)
        if row:
            rows.append(row)

    logger.info(f"[matrix] {len(rows)} normativas identificadas")

    # Ordenar: gobierno primero, luego universidades, luego abierto
    order = {"government": 0, "university": 1, "open": 2}
    rows.sort(key=lambda r: (order.get(r.get("_source_type", ""), 3),
                              r.get("_heuristic_score", 0) * -1))

    return rows


def build_all_documents_log(documents: List[Dict]) -> List[Dict]:
    """
    Genera log completo de TODOS los documentos procesados (para hoja de auditoría).
    """
    log_rows = []
    for doc in documents:
        ai = doc.get("ai_classification") or {}
        log_rows.append({
            "URL":               doc.get("url", ""),
            "Título":            doc.get("title", ""),
            "Fuente":            doc.get("source_type", ""),
            "Universidad":       doc.get("university_name", "") or "",
            "Query":             doc.get("query_used", "")[:100],
            "Tipo de contenido": doc.get("content_type", ""),
            "Score heurístico":  doc.get("heuristic_score", 0.0),
            "Label heurístico":  doc.get("heuristic_label", ""),
            "Es normativa (IA)": ai.get("es_normativa", ""),
            "Tipo norma (IA)":   ai.get("tipo_norma", ""),
            "Error extracción":  doc.get("extraction_error", "") or "",
        })
    return log_rows

"""
ai_classifier.py — Clasificación con IA (OpenAI)

Para documentos con label ALTA o MEDIA, genera una clasificación estructurada
usando GPT-4o-mini.  Si la API no está configurada, retorna clasificación vacía.
"""

import json
import logging
import re
import time
from pathlib import Path
from typing import Dict, List, Optional

import config

logger = logging.getLogger(__name__)

# ─── Prompt del sistema ───────────────────────────────────────────────────────

_SYSTEM_PROMPT = """Eres un experto jurídico especializado en normativa sobre Inteligencia Artificial en educación superior de México y América Latina.

Tu tarea es analizar fragmentos de documentos y determinar si constituyen normativa sobre IA, clasificarlos y extraer metadatos.

SIEMPRE responde ÚNICAMENTE con un objeto JSON válido, sin texto adicional.
"""

_USER_PROMPT_TEMPLATE = """Analiza el siguiente documento y clasifícalo.

URL: {url}
Título: {title}
Fragmento de texto:
---
{text}
---

Responde EXCLUSIVAMENTE con este JSON (sin markdown, sin comentarios):
{{
  "es_normativa": "si" | "no",
  "tipo_norma": "ley" | "decreto" | "reglamento" | "guía ética" | "estrategia nacional" | "resolución rectoral" | "lineamiento académico" | "libro blanco" | "guía pedagógica" | "código de ética" | "acuerdo institucional" | "otro" | "no aplica",
  "estado": "vigente" | "en proyecto" | "derogada" | "no especificado",
  "dominio": "pedagógico" | "administrativo" | "protección de datos" | "ética" | "técnico" | "no aplica",
  "vinculo": "directo" | "indirecto" | "no aplica",
  "dedicacion_texto": "articulado completo" | "sección/capítulo" | "mención breve" | "no aplica",
  "titulo_norma": "<título oficial del documento o 'No Indica'>",
  "organismo_emisor": "<nombre del organismo que emite la norma o 'No Indica'>",
  "fecha_publicacion": "<fecha en formato YYYY-MM-DD o 'No Indica' si no se encuentra>",
  "ambito": "nacional" | "institucional" | "no aplica",
  "observaciones": "<ver instrucciones abajo>"
}}

Instrucciones para el campo observaciones:
- Máximo 2-3 oraciones concisas.
- Si es_normativa = "si": comienza con un verbo activo que describe el contenido clave del documento. Menciona instrumentos, conceptos, principios o prohibiciones específicas que aparezcan nombradas en el texto, entre comillas cuando corresponda. Ejemplo: «Establece la creación del 'Observatorio UnADM de Cultura Digital' y prohíbe la suplantación de identidad mediante IA.» / «Introduce los 'Principios de Chepultepec'. Exige evaluación de riesgos, auditorías periódicas y mecanismos de revisión humana en decisiones automatizadas.»
- Si es_normativa = "no": identifica el tipo de documento (iniciativa, guía, comunicado, análisis doctrinal, etc.) y valora su fuerza normativa. Señala brevemente su relevancia para la gobernanza de IA en educación. Ejemplo: «Iniciativa legislativa relevante para la gobernanza general de IA en México; menciona coordinación con SEP, pero no constituye regulación educativa específica ni norma vigente.» / «Guía de la UNESCO para el uso de IA generativa en entornos educativos. Análisis doctrinal útil como marco interpretativo; no constituye instrumento normativo vinculante.»

Criterios:
- es_normativa = "si" SOLO si el documento establece reglas, lineamientos, políticas o marcos normativos relacionados con IA
- Si el documento es una noticia, artículo académico, página informativa o blog → es_normativa = "no"
- tipo_norma debe reflejar el instrumento jurídico/institucional real
- dominio = ámbito temático PRINCIPAL de la norma; elige UNO solo; si abarca varios, elige el predominante
- vinculo = "directo" si la norma trata IA de forma central; "indirecto" si IA es tema secundario
- Solo incluye documentos de organismos mexicanos (gobierno federal, estados, o universidades mexicanas)
"""


# ─── Cliente OpenAI ───────────────────────────────────────────────────────────

def _get_client():
    """Crea cliente OpenAI si la API key está disponible."""
    if not config.OPENAI_API_KEY:
        return None
    try:
        from openai import OpenAI
        return OpenAI(api_key=config.OPENAI_API_KEY)
    except ImportError:
        logger.error("[ai_classifier] openai no instalado. Ejecuta: pip install openai")
        return None
    except Exception as e:
        logger.error(f"[ai_classifier] Error creando cliente OpenAI: {e}")
        return None


_CLIENT = None


def _get_or_create_client():
    global _CLIENT
    if _CLIENT is None:
        _CLIENT = _get_client()
    return _CLIENT


# ─── Clasificación ────────────────────────────────────────────────────────────

_EMPTY_CLASSIFICATION = {
    "es_normativa": "no",
    "tipo_norma": "no aplica",
    "estado": "no especificado",
    "dominio": "no aplica",
    "vinculo": "no aplica",
    "dedicacion_texto": "no aplica",
    "titulo_norma": "No Indica",
    "organismo_emisor": "No Indica",
    "fecha_publicacion": "No Indica",
    "ambito": "no aplica",
    "observaciones": "Clasificación no disponible (API no configurada o error).",
}


def _prepare_text_for_ai(document: Dict) -> str:
    """
    Construye un extracto más representativo para IA.
    Prioriza ventanas alrededor de keywords de IA/normativa;
    si no encuentra señales, usa inicio+medio+final.
    """
    full_text = document.get("extracted_text", "") or document.get("snippet", "") or ""
    max_chars = int(getattr(config, "OPENAI_INPUT_CHARS", 5500))

    if not full_text.strip():
        return document.get("snippet", "Sin texto disponible")

    if len(full_text) <= max_chars:
        return full_text

    low = full_text.lower()
    keywords = list(dict.fromkeys(config.AI_KEYWORDS + config.HIGH_SCORE_KEYWORDS + [
        "chatgpt", "ia generativa", "inteligencia artificial", "lineamiento", "reglamento"
    ]))

    positions = []
    for kw in keywords:
        for m in re.finditer(re.escape(kw), low):
            positions.append(m.start())
            if len(positions) >= 8:
                break
        if len(positions) >= 8:
            break

    if positions:
        positions = sorted(positions)
        window = 700
        chunks = []
        for p in positions:
            start = max(0, p - window)
            end = min(len(full_text), p + window)
            chunks.append(full_text[start:end].strip())

        merged = "\n...\n".join(c for c in chunks if c)
        return merged[:max_chars]

    # Fallback: inicio + medio + final para evitar sesgo al encabezado
    part = max_chars // 3
    head = full_text[:part]
    mid_start = max(0, len(full_text) // 2 - part // 2)
    mid = full_text[mid_start:mid_start + part]
    tail = full_text[-part:]
    return (head + "\n...\n" + mid + "\n...\n" + tail)[:max_chars]


def classify_with_ai(document: Dict, retries: int = 2) -> Dict:
    """
    Clasifica un documento con OpenAI.

    Retorna dict con campos de clasificación.
    Si la API no está disponible, retorna clasificación vacía.
    """
    client = _get_or_create_client()
    if client is None:
        logger.debug("[ai_classifier] Sin cliente OpenAI, usando clasificación vacía")
        return dict(_EMPTY_CLASSIFICATION)

    # Preparar texto con extracto inteligente para mejorar recall sin disparar tokens
    text = _prepare_text_for_ai(document)

    prompt = _USER_PROMPT_TEMPLATE.format(
        url=document.get("url", ""),
        title=document.get("title", "Sin título"),
        text=text,
    )

    for attempt in range(retries + 1):
        try:
            response = client.chat.completions.create(
                model=config.OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": _SYSTEM_PROMPT},
                    {"role": "user",   "content": prompt},
                ],
                max_tokens=config.OPENAI_MAX_TOKENS,
                temperature=0.1,
                response_format={"type": "json_object"},
            )

            raw_json = response.choices[0].message.content.strip()
            classification = json.loads(raw_json)

            # Validar campos obligatorios
            required = ["es_normativa", "tipo_norma", "estado", "dominio",
                        "vinculo", "dedicacion_texto", "titulo_norma",
                        "organismo_emisor", "fecha_publicacion", "ambito",
                        "observaciones"]
            for field in required:
                if field not in classification:
                    classification[field] = _EMPTY_CLASSIFICATION.get(field, "No disponible")

            logger.debug(f"[ai_classifier] Clasificado: {document.get('url', '')[:60]} → {classification.get('es_normativa')} / {classification.get('tipo_norma')}")
            return classification

        except json.JSONDecodeError as e:
            logger.warning(f"[ai_classifier] JSON inválido (intento {attempt+1}): {e}")
            if attempt < retries:
                time.sleep(2)
                continue

        except Exception as e:
            err_str = str(e).lower()
            if "rate_limit" in err_str or "429" in err_str:
                wait = 30 * (attempt + 1)
                logger.warning(f"[ai_classifier] Rate limit. Esperando {wait}s")
                time.sleep(wait)
                continue
            elif "insufficient_quota" in err_str:
                logger.error("[ai_classifier] Quota de OpenAI agotada.")
                return dict(_EMPTY_CLASSIFICATION)
            else:
                logger.warning(f"[ai_classifier] Error (intento {attempt+1}): {e}")
                if attempt < retries:
                    time.sleep(3)
                    continue

    logger.warning(f"[ai_classifier] Fallback para: {document.get('url', '')[:60]}")
    return dict(_EMPTY_CLASSIFICATION)


def classify_batch_with_ai(
    documents: list,
    delay_between: float = 1.0,
    checkpoint_path: Optional[Path] = None,
) -> list:
    """
    Clasifica con IA solo documentos ALTA y MEDIA.
    Los BAJA reciben clasificación vacía.
    Agrega campo 'ai_classification' a cada documento.

    Args:
        documents:        Lista completa de documentos (todos los labels).
        delay_between:    Pausa entre llamadas a la API (segundos).
        checkpoint_path:  Ruta JSON para persistir progreso URL→clasificación.
                          Si existe, los documentos ya clasificados se saltean.
                          Se actualiza cada 10 documentos nuevos clasificados.
    """
    to_classify = [d for d in documents if d.get("heuristic_label") in ("ALTA", "MEDIA")]
    skip = [d for d in documents if d.get("heuristic_label") == "BAJA"]

    # ── Cargar checkpoint de clasificación IA ──────────────────────────────────
    # Mapa URL → clasificación para documentos ya procesados en ejecuciones previas
    ai_done: Dict[str, Dict] = {}
    if checkpoint_path and Path(checkpoint_path).exists():
        try:
            ai_done = json.loads(Path(checkpoint_path).read_text(encoding="utf-8"))
            logger.info(f"[ai_classifier] Checkpoint IA cargado: {len(ai_done)} docs ya clasificados")
        except Exception as e:
            logger.warning(f"[ai_classifier] Error cargando checkpoint IA: {e}")

    def _persist_ai_checkpoint() -> None:
        if not checkpoint_path:
            return
        try:
            Path(checkpoint_path).write_text(
                json.dumps(ai_done, ensure_ascii=False), encoding="utf-8"
            )
        except Exception as e:
            logger.warning(f"[ai_classifier] Error guardando checkpoint IA: {e}")

    extra_baja = []
    if getattr(config, "AI_INCLUDE_BORDERLINE_BAJA", False):
        min_score = float(config.AI_BAJA_MIN_SCORE)
        min_url_score = float(config.AI_BAJA_MIN_URL_PRIORITY)
        max_extra = int(getattr(config, "AI_MAX_EXTRA_BAJA", 20))

        candidates = []
        for d in skip:
            hscore = float(d.get("heuristic_score") or 0.0)
            uscore = float(d.get("url_priority_score") or 0.0)
            url = str(d.get("url", "")).lower()
            priority_domain = (".gob.mx" in url) or (".edu.mx" in url)
            if hscore >= min_score and (uscore >= min_url_score or priority_domain):
                candidates.append(d)

        candidates.sort(
            key=lambda x: (
                float(x.get("url_priority_score") or 0.0),
                float(x.get("heuristic_score") or 0.0),
            ),
            reverse=True,
        )
        extra_baja = candidates[:max_extra]
        extra_ids = {id(d) for d in extra_baja}
        skip = [d for d in skip if id(d) not in extra_ids]
        to_classify.extend(extra_baja)

    logger.info(
        f"[ai_classifier] Clasificando {len(to_classify)} docs con IA "
        f"(ALTA+MEDIA={len([d for d in documents if d.get('heuristic_label') in ('ALTA', 'MEDIA')])}, "
        f"BAJA extra={len(extra_baja)})"
    )

    total_to_classify = len(to_classify)
    new_classified = 0
    for idx, doc in enumerate(to_classify, 1):
        url = doc.get("url", "")
        if url and url in ai_done:
            # Documento ya clasificado en una ejecución anterior
            doc["ai_classification"] = ai_done[url]
            logger.debug(f"[ai_classifier] Checkpoint hit ({idx}/{total_to_classify}): {url[:60]}")
        else:
            doc["ai_classification"] = classify_with_ai(doc)
            if url:
                ai_done[url] = doc["ai_classification"]
            new_classified += 1
            # Persistir checkpoint cada 10 documentos nuevos
            if checkpoint_path and new_classified % 10 == 0:
                _persist_ai_checkpoint()
            time.sleep(delay_between)

        if idx % 10 == 0 or idx == total_to_classify:
            logger.info(f"[ai_classifier] Progreso IA: {idx}/{total_to_classify} docs clasificados")

    # Persistir checkpoint final
    if checkpoint_path and new_classified > 0:
        _persist_ai_checkpoint()
        logger.info(f"[ai_classifier] Checkpoint IA final guardado ({len(ai_done)} docs)")

    for doc in skip:
        doc["ai_classification"] = dict(_EMPTY_CLASSIFICATION)

    return to_classify + skip

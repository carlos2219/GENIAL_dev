"""
main.py — Orquestador del pipeline completo GENIAL

Fases:
  1. Búsqueda gubernamental (government_search)
  2. Búsqueda universitaria (university_search)
  3. Búsqueda abierta (open_search)
  4. Deduplicación pre-extracción
  5. Extracción de contenido (document_extractor) — paralela
  6. Clasificación heurística (document_classifier)
  7. Deduplicación post-extracción
  8. Clasificación con IA (ai_classifier) — solo ALTA y MEDIA
  9. Construcción de matriz (matrix_builder)
 10. Exportación a Excel (excel_exporter)
"""

import argparse
import json
import logging
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import List, Dict

# ─── Configuración de logging ─────────────────────────────────────────────────

def _setup_logging(verbose: bool = False):
    level = logging.DEBUG if verbose else logging.INFO
    log_file = Path(__file__).parent / "logs" / f"pipeline_{int(time.time())}.log"
    log_file.parent.mkdir(exist_ok=True)

    handlers = [
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(log_file, encoding="utf-8"),
    ]
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
        datefmt="%H:%M:%S",
        handlers=handlers,
    )
    return logging.getLogger(__name__)


# ─── Módulos del sistema ──────────────────────────────────────────────────────

import config
import government_search
import university_search
import open_search
import document_extractor
import document_classifier
import deduplicator
import ai_classifier
import matrix_builder
import excel_exporter


# ─── Extracción paralela ──────────────────────────────────────────────────────

def _extract_all(documents: List[Dict], max_workers: int = config.MAX_WORKERS) -> List[Dict]:
    """Extrae contenido de todos los documentos en paralelo."""
    logger = logging.getLogger(__name__)
    logger.info(f"[main] Extrayendo contenido de {len(documents)} documentos ({max_workers} hilos)...")

    results: List[Dict] = []

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_doc = {
            executor.submit(document_extractor.extract_document, doc["url"]): doc
            for doc in documents
        }

        completed = 0
        for future in as_completed(future_to_doc):
            original_doc = future_to_doc[future]
            try:
                extraction = future.result()
                # Combinar resultados de extracción con el documento original
                original_doc["extracted_text"]   = extraction.get("extracted_text", "")
                original_doc["extraction_error"] = extraction.get("extraction_error")
                original_doc["content_type"]     = extraction.get("content_type", "unknown")
                # Actualizar título si estaba vacío y la extracción lo encontró
                if not original_doc.get("title") and extraction.get("title"):
                    original_doc["title"] = extraction["title"]
                # Actualizar URL con la URL final (tras redirecciones)
                if extraction.get("response_url") and extraction["response_url"] != original_doc["url"]:
                    original_doc["final_url"] = extraction["response_url"]
            except Exception as e:
                original_doc["extraction_error"] = str(e)[:200]
                original_doc["extracted_text"]   = ""
                original_doc["content_type"]     = "unknown"
            finally:
                results.append(original_doc)
                completed += 1
                if completed % 10 == 0:
                    logger.info(f"[main] Extraídos {completed}/{len(documents)}")

    logger.info(f"[main] Extracción completa: {len(results)} documentos")
    errors = sum(1 for d in results if d.get("extraction_error"))
    logger.info(f"[main] Errores de extracción: {errors}")
    return results


# ─── Pipeline principal ───────────────────────────────────────────────────────

def run_pipeline(
    skip_government: bool = False,
    skip_universities: bool = False,
    skip_open: bool = False,
    skip_ai: bool = False,
    max_universities: int = None,
    output_path: Path = None,
    verbose: bool = False,
) -> Path:
    """
    Ejecuta el pipeline completo.

    Args:
        skip_government:   Omitir FASE 1
        skip_universities: Omitir FASE 2
        skip_open:         Omitir FASE 3
        skip_ai:           Omitir clasificación con IA (usar solo heurística)
        max_universities:  Límite de universidades a procesar
        output_path:       Ruta del Excel de salida
        verbose:           Logging detallado

    Returns:
        Path del Excel generado.
    """
    logger = logging.getLogger(__name__)

    if max_universities is not None:
        config.MAX_UNIVERSITIES = max_universities

    if output_path:
        config.OUTPUT_EXCEL = Path(output_path)

    logger.info("=" * 70)
    logger.info("  GENIAL — Sistema de Levantamiento Normativo IA en Educación México")
    logger.info("=" * 70)
    logger.info(f"  Investigador: {config.RESEARCHER_NAME}")
    logger.info(f"  Modelo IA:    {config.OPENAI_MODEL}")
    logger.info(f"  API OpenAI:   {'Configurada' if config.OPENAI_API_KEY else 'NO configurada (solo heurística)'}")
    logger.info("=" * 70)

    start_time = time.time()
    all_raw: List[Dict] = []

    def _elapsed() -> str:
        secs = int(time.time() - start_time)
        return f"{secs // 60}m{secs % 60:02d}s"

    # ─── FASE 1: Gobierno ──────────────────────────────────────────────────────
    if not skip_government:
        logger.info(f"[PROGRESO] >> FASE 1/3 - Busqueda gubernamental | Tiempo: {_elapsed()}")
        gov_docs = government_search.search_government_sources()
        all_raw.extend(gov_docs)
        logger.info(f"[PROGRESO] FASE 1 completada: {len(gov_docs)} docs | Tiempo: {_elapsed()}")
    else:
        logger.info("[FASE 1] Omitida")

    # ─── FASE 2: Universidades ─────────────────────────────────────────────────
    if not skip_universities:
        logger.info(f"[PROGRESO] >> FASE 2/3 - Busqueda universitaria | Tiempo: {_elapsed()}")
        uni_df  = university_search.load_universities()
        uni_docs = university_search.search_universities(uni_df)
        all_raw.extend(uni_docs)
        logger.info(f"[PROGRESO] FASE 2 completada: {len(uni_docs)} docs | Tiempo: {_elapsed()}")
    else:
        logger.info("[FASE 2] Omitida")

    # ─── FASE 3: Búsqueda abierta ──────────────────────────────────────────────
    if not skip_open:
        logger.info(f"[PROGRESO] >> FASE 3/3 - Busqueda abierta | Tiempo: {_elapsed()}")
        open_docs = open_search.search_open()
        all_raw.extend(open_docs)
        logger.info(f"[PROGRESO] FASE 3 completada: {len(open_docs)} docs | Tiempo: {_elapsed()}")
    else:
        logger.info("[FASE 3] Omitida")

    logger.info(f"[main] Total crudo acumulado: {len(all_raw)} URLs | Tiempo: {_elapsed()}")

    if not all_raw:
        logger.warning("[main] Sin documentos para procesar. Verifica configuración de búsqueda.")
        return None

    # ─── DEDUPLICACIÓN PRE-EXTRACCIÓN ─────────────────────────────────────────
    all_raw = deduplicator.remove_url_duplicates_only(all_raw)
    logger.info(f"[main] Tras dedup URL: {len(all_raw)} documentos únicos | Tiempo: {_elapsed()}")

    # Filtrar URLs ya presentes en la matriz definitiva (skip-list del Excel)
    known_excel = Path(config.KNOWN_MATRIX_EXCEL)
    if known_excel.exists():
        known_urls = deduplicator.load_known_urls_from_excel(str(known_excel))
        all_raw = deduplicator.filter_known_urls(all_raw, known_urls)
        logger.info(f"[main] Tras skip-list Excel: {len(all_raw)} documentos | Tiempo: {_elapsed()}")
    else:
        logger.info("[main] Sin Excel de skip-list (KNOWN_MATRIX_EXCEL no encontrado)")

    # ─── EXTRACCIÓN DE CONTENIDO ───────────────────────────────────────────────
    logger.info(f"[PROGRESO] >> Extraccion de contenido ({len(all_raw)} docs) | Tiempo: {_elapsed()}")
    all_extracted = _extract_all(all_raw)
    logger.info(f"[PROGRESO] Extraccion completada | Tiempo: {_elapsed()}")

    # ─── CLASIFICACIÓN HEURÍSTICA ──────────────────────────────────────────────
    logger.info(f"[PROGRESO] >> Clasificacion heuristica | Tiempo: {_elapsed()}")
    all_classified = document_classifier.classify_batch(all_extracted)

    alta  = sum(1 for d in all_classified if d.get("heuristic_label") == "ALTA")
    media = sum(1 for d in all_classified if d.get("heuristic_label") == "MEDIA")
    baja  = sum(1 for d in all_classified if d.get("heuristic_label") == "BAJA")
    logger.info(f"[main] Heurística → ALTA: {alta} | MEDIA: {media} | BAJA: {baja}")

    # ─── DEDUPLICACIÓN POST-EXTRACCIÓN ────────────────────────────────────────
    all_classified = deduplicator.deduplicate(all_classified)
    logger.info(f"[main] Tras dedup contenido: {len(all_classified)} documentos")

    # ─── CLASIFICACIÓN CON IA ──────────────────────────────────────────────────
    if not skip_ai and config.OPENAI_API_KEY:
        ai_candidates = sum(1 for d in all_classified if d.get("heuristic_label") in ("ALTA", "MEDIA"))
        logger.info(f"[PROGRESO] >> Clasificacion IA ({ai_candidates} candidatos) | Tiempo: {_elapsed()}")
        all_classified = ai_classifier.classify_batch_with_ai(all_classified)
        logger.info(f"[PROGRESO] Clasificacion IA completada | Tiempo: {_elapsed()}")
    else:
        reason = "desactivada por flag" if skip_ai else "API key no configurada"
        logger.info(f"[main] Clasificación IA omitida ({reason})")
        for doc in all_classified:
            doc["ai_classification"] = None

    # ─── CONSTRUCCIÓN DE MATRIZ ────────────────────────────────────────────────
    logger.info("[main] Construyendo matriz normativa...")
    matrix_rows = matrix_builder.build_matrix(all_classified)
    log_rows    = matrix_builder.build_all_documents_log(all_classified)

    logger.info(f"[main] Normativas confirmadas: {len(matrix_rows)}")

    # ─── EXPORTACIÓN A EXCEL ───────────────────────────────────────────────────
    output_file = excel_exporter.export_to_excel(
        matrix_rows=matrix_rows,
        all_documents=all_classified,
        log_rows=log_rows,
    )

    # ─── Guardar JSON de respaldo ──────────────────────────────────────────────
    json_path = config.OUTPUT_DIR / "documentos_procesados.json"
    try:
        with open(json_path, "w", encoding="utf-8") as f:
            # Serializar solo campos básicos (evitar objetos no serializables)
            safe_docs = [
                {k: v for k, v in d.items() if k not in ("_session",)}
                for d in all_classified
            ]
            json.dump(safe_docs, f, ensure_ascii=False, indent=2)
        logger.info(f"[main] JSON de respaldo: {json_path}")
    except Exception as e:
        logger.warning(f"[main] No se pudo guardar JSON: {e}")

    elapsed = time.time() - start_time
    logger.info("=" * 70)
    logger.info(f"  Pipeline completado en {elapsed:.1f}s")
    logger.info(f"  Excel generado: {output_file}")
    logger.info(f"  Normativas en matriz: {len(matrix_rows)}")
    logger.info("=" * 70)

    return output_file


# ─── CLI ─────────────────────────────────────────────────────────────────────

def _parse_args():
    parser = argparse.ArgumentParser(
        description="GENIAL — Levantamiento normativo de IA en educación (México)",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument(
        "--skip-government", action="store_true",
        help="Omitir FASE 1 (búsqueda gubernamental)"
    )
    parser.add_argument(
        "--skip-universities", action="store_true",
        help="Omitir FASE 2 (búsqueda en universidades)"
    )
    parser.add_argument(
        "--skip-open", action="store_true",
        help="Omitir FASE 3 (búsqueda abierta)"
    )
    parser.add_argument(
        "--skip-ai", action="store_true",
        help="Omitir clasificación con IA (usar solo heurística)"
    )
    parser.add_argument(
        "--max-universities", type=int, default=None,
        metavar="N",
        help="Procesar solo las primeras N universidades del CSV"
    )
    parser.add_argument(
        "--all-universities", action="store_true",
        help="Procesar TODAS las universidades del CSV (ignora el límite seguro definido en config.DEFINITIVE_RUN_MAX_UNIVERSITIES)"
    )
    parser.add_argument(
        "--output", type=str, default=None,
        metavar="RUTA",
        help="Ruta del archivo Excel de salida"
    )
    parser.add_argument(
        "--researcher", type=str, default=None,
        metavar="NOMBRE",
        help="Nombre del investigador (sobrescribe config.py)"
    )
    parser.add_argument(
        "--verbose", action="store_true",
        help="Logging detallado (DEBUG)"
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    logger = _setup_logging(verbose=args.verbose)

    if args.researcher:
        config.RESEARCHER_NAME = args.researcher

    # Determinar límite de universidades:
    # 1. --max-universities N  → usa N explícitamente
    # 2. --all-universities    → sin límite (None)
    # 3. ninguno               → usa el límite seguro definido en config
    if args.max_universities is not None:
        effective_max = args.max_universities
    elif getattr(args, "all_universities", False):
        effective_max = None
    else:
        effective_max = getattr(config, "DEFINITIVE_RUN_MAX_UNIVERSITIES", None)
        if effective_max:
            logger.info(f"[main] Límite seguro aplicado: {effective_max} universidades (usa --all-universities para el listado completo)")

    output = run_pipeline(
        skip_government=args.skip_government,
        skip_universities=args.skip_universities,
        skip_open=args.skip_open,
        skip_ai=args.skip_ai,
        max_universities=effective_max,
        output_path=args.output,
        verbose=args.verbose,
    )

    if output:
        print(f"\nProceso completado. Resultado: {output}")
    else:
        print("\nSin resultado. Revisa los logs.")
        sys.exit(1)

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
from typing import List, Dict, Optional

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
from src.pipeline import government_search
from src.pipeline import university_search
from src.pipeline import open_search
from src.pipeline import document_extractor
from src.pipeline import document_classifier
from src.pipeline import deduplicator
from src.pipeline import ai_classifier
from src.pipeline import matrix_builder
from src.pipeline import excel_exporter


# ─── Checkpoint helpers ───────────────────────────────────────────────────────

def _get_checkpoint_dir() -> Path:
    """Retorna y crea el directorio de checkpoints de sesión."""
    d = config.OUTPUT_DIR / "checkpoints"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _save_checkpoint(name: str, data: List[Dict], ckpt_dir: Path) -> None:
    """Persiste una lista de documentos como checkpoint JSON."""
    logger = logging.getLogger(__name__)
    path = ckpt_dir / f"{name}.json"
    try:
        safe = [{k: v for k, v in d.items() if k != "_session"} for d in data]
        with open(path, "w", encoding="utf-8") as f:
            json.dump(safe, f, ensure_ascii=False)
        logger.info(f"[checkpoint] Guardado '{name}': {len(data)} docs -> {path.name}")
    except Exception as e:
        logger.warning(f"[checkpoint] Error guardando '{name}': {e}")


def _load_checkpoint(name: str, ckpt_dir: Path) -> Optional[List[Dict]]:
    """Carga un checkpoint JSON. Retorna None si no existe o hay error."""
    logger = logging.getLogger(__name__)
    path = ckpt_dir / f"{name}.json"
    if not path.exists():
        return None
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        logger.info(f"[checkpoint] Cargado '{name}': {len(data)} docs ← {path.name}")
        return data
    except Exception as e:
        logger.warning(f"[checkpoint] Error cargando '{name}': {e}")
        return None


def _ckpt_exists(name: str, ckpt_dir: Path) -> bool:
    return (ckpt_dir / f"{name}.json").exists()


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
                if getattr(config, "SEARCH_METRICS_ENABLED", True):
                    from src.pipeline.search_metrics import get_metrics
                    survived = (
                        original_doc.get("extraction_error") is None
                        and len(original_doc.get("extracted_text", "")) > 0
                    )
                    get_metrics().record_validation(original_doc.get("url", ""), survived)
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
    max_unis_phase3: int = None,
    output_path: Path = None,
    verbose: bool = False,
    resume: bool = False,
    consolidate_with_matrix: str = None,
) -> Path:
    """
    Ejecuta el pipeline completo.

    Args:
        skip_government:   Omitir FASE 1
        skip_universities: Omitir FASE 2
        skip_open:         Omitir FASE 3
        skip_ai:           Omitir clasificación con IA (usar solo heurística)
        max_universities:  Límite de universidades a procesar en FASE 2
        max_unis_phase3:   Límite de universidades a procesar en FASE 3
        output_path:       Ruta del Excel de salida
        verbose:           Logging detallado
        resume:            Reanudar desde el último checkpoint disponible
        consolidate_with_matrix: Ruta de matriz maestra para consolidar

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

    # ─── Configuración de checkpoints ─────────────────────────────────────────
    ckpt_dir = _get_checkpoint_dir()

    # Detectar el punto de reanudación disponible más avanzado
    _resume_from = "search"
    if resume:
        if _ckpt_exists("classified_heuristic", ckpt_dir):
            _resume_from = "ai"
            logger.info("[resume] Checkpoint detectado -> reanudando desde: Clasificación IA")
        elif _ckpt_exists("extracted", ckpt_dir):
            _resume_from = "heuristic"
            logger.info("[resume] Checkpoint detectado -> reanudando desde: Clasificación heurística")
        elif _ckpt_exists("search_complete", ckpt_dir):
            _resume_from = "extraction"
            logger.info("[resume] Checkpoint detectado -> reanudando desde: Extracción de contenido")
        else:
            _resume_from = "search"
            logger.info("[resume] Sin checkpoint de etapa — cargando fases de búsqueda si existen")
    # _resume_from ∈ {"search", "extraction", "heuristic", "ai"}

    _run_searches = _resume_from == "search"

    all_raw: List[Dict] = []

    def _elapsed() -> str:
        secs = int(time.time() - start_time)
        return f"{secs // 60}m{secs % 60:02d}s"

    # ─── FASE 1: Gobierno ──────────────────────────────────────────────────────
    if not skip_government and _run_searches:
        _cached = _load_checkpoint("phase1_gov", ckpt_dir) if resume else None
        if _cached is not None:
            logger.info("[FASE 1] Cargada desde checkpoint — búsqueda omitida")
            gov_docs = _cached
        else:
            logger.info(f"[PROGRESO] >> FASE 1/3 - Busqueda gubernamental | Tiempo: {_elapsed()}")
            gov_docs = government_search.search_government_sources()
            logger.info(f"[PROGRESO] FASE 1 completada: {len(gov_docs)} docs | Tiempo: {_elapsed()}")
            _save_checkpoint("phase1_gov", gov_docs, ckpt_dir)
        all_raw.extend(gov_docs)
    else:
        logger.info("[FASE 1] Omitida")

    # ─── FASE 3: Búsqueda abierta (ANTES de Fase 2) ────────────────────────────
    # Se ejecuta antes de Fase 2 porque Fase 2 agota las queries DDG durante horas.
    # Fase 3 tiene solo 10 queries fijas; ejecutarlas con DDG fresco garantiza resultados.
    if not skip_open and _run_searches:
        _cached = _load_checkpoint("phase3_open", ckpt_dir) if resume else None
        if _cached is not None:
            logger.info("[FASE 3] Cargada desde checkpoint — búsqueda omitida")
            open_docs = _cached
        else:
            logger.info(f"[PROGRESO] >> FASE 3/3 - Busqueda abierta (pre-Fase2) | Tiempo: {_elapsed()}")
            open_docs = open_search.search_open(max_unis=max_unis_phase3)
            logger.info(f"[PROGRESO] FASE 3 completada: {len(open_docs)} docs | Tiempo: {_elapsed()}")
            _save_checkpoint("phase3_open", open_docs, ckpt_dir)
        all_raw.extend(open_docs)
    else:
        logger.info("[FASE 3] Omitida")

    # ─── FASE 2: Universidades ─────────────────────────────────────────────────
    if not skip_universities and _run_searches:
        _cached = _load_checkpoint("phase2_uni", ckpt_dir) if resume else None
        if _cached is not None:
            logger.info("[FASE 2] Cargada desde checkpoint completo — búsqueda omitida")
            uni_docs = _cached
        else:
            logger.info(f"[PROGRESO] >> FASE 2/3 - Busqueda universitaria | Tiempo: {_elapsed()}")
            uni_df   = university_search.load_universities()
            uni_docs = university_search.search_universities(
                uni_df,
                progress_checkpoint=ckpt_dir / "phase2_progress.json",
            )
            logger.info(f"[PROGRESO] FASE 2 completada: {len(uni_docs)} docs | Tiempo: {_elapsed()}")
            _save_checkpoint("phase2_uni", uni_docs, ckpt_dir)
        all_raw.extend(uni_docs)
    else:
        logger.info("[FASE 2] Omitida")

    # ─── DEDUPLICACIÓN PRE-EXTRACCIÓN + FILTROS ────────────────────────────────
    if _resume_from in ("search", "extraction"):
        if _resume_from == "extraction":
            # Búsquedas ya completadas — cargar search_complete
            _sc = _load_checkpoint("search_complete", ckpt_dir)
            if _sc is not None:
                all_raw = _sc
                logger.info(f"[main] Search_complete cargado: {len(all_raw)} docs | Tiempo: {_elapsed()}")
        else:
            logger.info(f"[main] Total crudo acumulado: {len(all_raw)} URLs | Tiempo: {_elapsed()}")

            if not all_raw:
                logger.warning("[main] Sin documentos para procesar. Verifica configuración de búsqueda.")
                return None

            # Deduplicación por URL
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

            # Filtro pre-extracción: descartar docs sin señal de IA ni normativa en snippet/URL.
            if getattr(config, "PRE_EXTRACTION_FILTER_ENABLED", False):
                before_filter = len(all_raw)
                kept, dropped = [], []
                for doc in all_raw:
                    url_score = doc.get("url_priority_score", 0.0)
                    combined = (doc.get("title", "") + " " + doc.get("snippet", "")).lower()
                    has_ai_signal = any(kw in combined for kw in config.AI_KEYWORDS)
                    has_policy_signal = any(kw in combined for kw in config.POLICY_KEYWORDS)
                    if url_score < 0.1 and not has_ai_signal and not has_policy_signal:
                        dropped.append(doc)
                    else:
                        kept.append(doc)
                all_raw = kept
                logger.info(
                    f"[main] Filtro pre-extracción: {len(kept)} conservados, "
                    f"{len(dropped)} descartados (sin señal IA/normativa en snippet+URL) | "
                    f"Tiempo: {_elapsed()}"
                )

            _save_checkpoint("search_complete", all_raw, ckpt_dir)

    # ─── EXTRACCIÓN DE CONTENIDO ───────────────────────────────────────────────
    if _resume_from in ("search", "extraction"):
        logger.info(f"[PROGRESO] >> Extraccion de contenido ({len(all_raw)} docs) | Tiempo: {_elapsed()}")
        all_extracted = _extract_all(all_raw)
        logger.info(f"[PROGRESO] Extraccion completada | Tiempo: {_elapsed()}")
        _save_checkpoint("extracted", all_extracted, ckpt_dir)
    elif _resume_from == "heuristic":
        all_extracted = _load_checkpoint("extracted", ckpt_dir) or []
        logger.info(f"[main] Extracción cargada desde checkpoint: {len(all_extracted)} docs")
    else:
        all_extracted = []  # no se necesita; clasificación heurística ya está en checkpoint

    # ─── CLASIFICACIÓN HEURÍSTICA ──────────────────────────────────────────────
    if _resume_from in ("search", "extraction", "heuristic"):
        logger.info(f"[PROGRESO] >> Clasificacion heuristica | Tiempo: {_elapsed()}")
        all_classified = document_classifier.classify_batch(all_extracted)

        alta  = sum(1 for d in all_classified if d.get("heuristic_label") == "ALTA")
        media = sum(1 for d in all_classified if d.get("heuristic_label") == "MEDIA")
        baja  = sum(1 for d in all_classified if d.get("heuristic_label") == "BAJA")
        logger.info(f"[main] Heurística -> ALTA: {alta} | MEDIA: {media} | BAJA: {baja}")

        # ─── DEDUPLICACIÓN POST-EXTRACCIÓN ────────────────────────────────────────
        all_classified = deduplicator.deduplicate(all_classified)
        logger.info(f"[main] Tras dedup contenido: {len(all_classified)} documentos")

        _save_checkpoint("classified_heuristic", all_classified, ckpt_dir)
    else:
        # _resume_from == "ai": cargar clasificación heurística desde checkpoint
        all_classified = _load_checkpoint("classified_heuristic", ckpt_dir) or []
        logger.info(f"[main] Clasificación heurística cargada desde checkpoint: {len(all_classified)} docs")
        alta  = sum(1 for d in all_classified if d.get("heuristic_label") == "ALTA")
        media = sum(1 for d in all_classified if d.get("heuristic_label") == "MEDIA")
        baja  = sum(1 for d in all_classified if d.get("heuristic_label") == "BAJA")
        logger.info(f"[main] Heurística (checkpoint) -> ALTA: {alta} | MEDIA: {media} | BAJA: {baja}")

    # ─── CLASIFICACIÓN CON IA ──────────────────────────────────────────────────
    if not skip_ai and config.OPENAI_API_KEY:
        ai_candidates = sum(1 for d in all_classified if d.get("heuristic_label") in ("ALTA", "MEDIA"))
        logger.info(f"[PROGRESO] >> Clasificacion IA ({ai_candidates} candidatos) | Tiempo: {_elapsed()}")
        ai_ckpt = ckpt_dir / "ai_progress.json"
        all_classified = ai_classifier.classify_batch_with_ai(
            all_classified,
            checkpoint_path=ai_ckpt,
        )
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

    # Consolidate if requested
    if getattr(args, 'consolidate_with_matrix', None):
        from src.pipeline.consolidator import consolidate_excel_file
        try:
            nuevos, duplicados = consolidate_excel_file(
                Path(output_file),
                Path(args.consolidate_with_matrix)
            )
            print("\n" + "=" * 50)
            print("  CONSOLIDACIÓN DE REGISTROS")
            print("=" * 50)
            print(f"Archivo de entrada:     {output_file}")
            print(f"Matriz maestra:         {args.consolidate_with_matrix}")
            print(f"\nRegistros procesados:   {nuevos + duplicados}")
            print(f"Duplicados encontrados: {duplicados}")
            print(f"Registros nuevos:       {nuevos}")
            print(f"\nArchivo consolidado guardado: {output_file}")
            print("=" * 50)
        except Exception as e:
            logger.error(f"Error durante consolidación: {e}")
            sys.exit(1)

    if getattr(config, "SEARCH_METRICS_ENABLED", True):
        from src.pipeline.search_metrics import get_metrics
        try:
            get_metrics().export_report(config.OUTPUT_DIR)
            logger.info(f"[main] Reporte de métricas guardado en {config.OUTPUT_DIR}/metrics/")
        except Exception as e:
            logger.warning(f"[main] Error exportando métricas: {e}")

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

    from src.pipeline import search_router
    search_router._flush_cache()

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
        "--phase3-only", action="store_true",
        help="Ejecutar solo Fase 3 (búsqueda abierta) + extracción + clasificación + Excel. "
             "Equivale a --skip-government --skip-universities."
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
        "--max-unis-phase3", type=int, default=None,
        metavar="N",
        help="Procesar solo las primeras N universidades en FASE 3 (útil para pruebas)"
    )
    parser.add_argument(
        "--resume", action="store_true",
        help="Reanudar desde el último checkpoint disponible (output/checkpoints/)"
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
    parser.add_argument(
        "--profile",
        type=str,
        default=None,
        choices=["fast", "balanced", "deep"],
        metavar="PROFILE",
        help="Perfil de ejecución de búsqueda: fast | balanced | deep (default: balanced)"
    )
    parser.add_argument(
        '--consolidate-with-matrix',
        type=str,
        default=None,
        help='Path to master matrix file (.xlsx) to consolidate against. If provided, '
             'filters output Excel to contain only new records (not duplicates).'
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    logger = _setup_logging(verbose=args.verbose)

    if args.researcher:
        config.RESEARCHER_NAME = args.researcher

    if args.profile:
        config.SEARCH_PROFILE = args.profile
        config._apply_profile(args.profile)
        logger.info(f"[main] Perfil de búsqueda: {args.profile}")

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

    if getattr(args, "phase3_only", False):
        args.skip_government = True
        args.skip_universities = True

    output = run_pipeline(
        skip_government=args.skip_government,
        skip_universities=args.skip_universities,
        skip_open=args.skip_open,
        skip_ai=args.skip_ai,
        max_universities=effective_max,
        max_unis_phase3=args.max_unis_phase3,
        output_path=args.output,
        verbose=args.verbose,
        resume=args.resume,
        consolidate_with_matrix=getattr(args, 'consolidate_with_matrix', None),
    )

    if output:
        print(f"\nProceso completado. Resultado: {output}")
    else:
        print("\nSin resultado. Revisa los logs.")
        sys.exit(1)

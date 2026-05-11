"""
run_phase3.py — Ejecutor aislado de FASE 3 (búsqueda abierta mejorada)

Ejecuta únicamente la Fase 3 del pipeline GENIAL (búsqueda abierta en DOF,
repositorios universitarios y portales de transparencia), seguida de extracción,
clasificación heurística, clasificación IA, construcción de matriz y exportación Excel.

Variables de entorno requeridas:
    OPENAI_API_KEY   — clave de API de OpenAI (sin esto, se usa solo heurística)

Variables de entorno opcionales:
    RESEARCHER_NAME  — nombre del investigador (default: Carlos Auquilla)
    OPENAI_MODEL     — modelo OpenAI a usar (default: gpt-4o-mini)

Uso:
    python run_phase3.py [opciones]

Opciones:
    --output RUTA    Ruta del Excel de salida
                     (default: output/fase3_YYYYMMDD_HHMM.xlsx)
    --skip-ai        Omitir clasificación con IA (usar solo heurística)
    --fresh          Eliminar checkpoint existente de Fase 3 para reiniciar búsqueda
    --resume         Reanudar desde checkpoint existente de Fase 3 o downstream
    --verbose        Logging detallado (DEBUG)
    --researcher N   Nombre del investigador (sobrescribe config.py y variable de entorno)

Notas para ejecución en Google Cloud VM:
    1. git pull origin main          # actualizar código
    2. export OPENAI_API_KEY=sk-...  # configurar API key
    3. python run_phase3.py --fresh  # correr Fase 3 limpia
"""

import argparse
import logging
import sys
import time
from datetime import datetime
from pathlib import Path


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="GENIAL — Fase 3 aislada (búsqueda abierta mejorada: DOF + repos + transparencia)",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument(
        "--output", type=str, default=None, metavar="RUTA",
        help="Ruta del Excel de salida (default: output/fase3_<timestamp>.xlsx)",
    )
    parser.add_argument(
        "--skip-ai", action="store_true",
        help="Omitir clasificación con IA (usar solo heurística)",
    )
    parser.add_argument(
        "--fresh", action="store_true",
        help="Eliminar checkpoints de Fase 3 y downstream para forzar re-búsqueda",
    )
    parser.add_argument(
        "--resume", action="store_true",
        help="Reanudar desde el checkpoint más avanzado disponible",
    )
    parser.add_argument(
        "--verbose", action="store_true",
        help="Logging detallado (DEBUG)",
    )
    parser.add_argument(
        "--researcher", type=str, default=None, metavar="NOMBRE",
        help="Nombre del investigador (sobrescribe config.py)",
    )
    return parser.parse_args()


def _setup_logging(verbose: bool, ts: str) -> logging.Logger:
    level = logging.DEBUG if verbose else logging.INFO
    log_path = Path("logs") / f"fase3_{ts}.log"
    log_path.parent.mkdir(exist_ok=True)

    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
        datefmt="%H:%M:%S",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(log_path, encoding="utf-8"),
        ],
    )
    return logging.getLogger(__name__)


def _clear_phase3_checkpoints(ckpt_dir: Path, logger: logging.Logger) -> None:
    """
    Elimina los checkpoints de Fase 3 y los pasos downstream para forzar
    una ejecución limpia completa. Los checkpoints de Fase 1 y 2 se conservan.
    """
    targets = [
        "phase3_open.json",
        "search_complete.json",
        "extracted.json",
        "classified_heuristic.json",
        "ai_progress.json",
    ]
    for name in targets:
        path = ckpt_dir / name
        if path.exists():
            path.unlink()
            logger.info(f"[fase3] Checkpoint eliminado: {name}")


if __name__ == "__main__":
    args = _parse_args()
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    logger = _setup_logging(args.verbose, ts)

    logger.info("=" * 70)
    logger.info("  GENIAL — Fase 3 aislada (DOF + repositorios + transparencia)")
    logger.info("=" * 70)

    # ─── Importar config (después de logging para capturar mensajes) ──────────
    import config

    if args.researcher:
        config.RESEARCHER_NAME = args.researcher

    output_path = Path(args.output) if args.output else (
        config.OUTPUT_DIR / f"fase3_{ts}.xlsx"
    )

    logger.info(f"  Investigador  : {config.RESEARCHER_NAME}")
    logger.info(f"  Modelo IA     : {config.OPENAI_MODEL}")
    logger.info(f"  API OpenAI    : {'Configurada' if config.OPENAI_API_KEY else 'NO configurada (solo heurística)'}")
    logger.info(f"  Salida Excel  : {output_path}")
    logger.info(f"  Clasificación : {'solo heurística' if args.skip_ai else 'heurística + IA'}")
    logger.info(f"  Modo          : {'FRESH (checkpoints borrados)' if args.fresh else 'RESUME' if args.resume else 'normal'}")
    logger.info("=" * 70)

    # ─── Limpiar checkpoints si --fresh ───────────────────────────────────────
    ckpt_dir = config.OUTPUT_DIR / "checkpoints"
    ckpt_dir.mkdir(parents=True, exist_ok=True)

    if args.fresh:
        _clear_phase3_checkpoints(ckpt_dir, logger)
    elif not args.resume:
        # Modo normal (ni fresh ni resume): borrar solo phase3_open para re-buscar,
        # pero conservar search_complete y downstream si existen.
        p3 = ckpt_dir / "phase3_open.json"
        if p3.exists():
            p3.unlink()
            logger.info("[fase3] Checkpoint phase3_open eliminado (re-búsqueda Fase 3)")

    # ─── Ejecutar pipeline solo-Fase3 ─────────────────────────────────────────
    from main import run_pipeline

    start = time.time()
    output_file = run_pipeline(
        skip_government=True,
        skip_universities=True,
        skip_open=False,
        skip_ai=args.skip_ai,
        output_path=output_path,
        verbose=args.verbose,
        resume=args.resume or args.fresh,  # con --fresh, los ckpts ya están borrados → resume seguro
    )

    elapsed = time.time() - start
    logger.info("=" * 70)
    if output_file:
        logger.info(f"  Fase 3 completada en {elapsed:.1f}s")
        logger.info(f"  Excel: {output_file}")
        logger.info(f"  Log  : logs/fase3_{ts}.log")
        logger.info("=" * 70)
        print(f"\nFase 3 completada. Excel: {output_file}")
    else:
        logger.warning("  Sin resultado. Revisa los logs.")
        logger.info("=" * 70)
        print("\nSin resultado. Revisa los logs.")
        sys.exit(1)

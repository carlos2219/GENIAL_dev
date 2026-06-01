import pandas as pd
from pathlib import Path
import argparse
import sys

from src.pipeline.consolidator import (
    consolidate_excel_file,
    load_excel
)


def main():
    """Función principal del CLI"""
    parser = argparse.ArgumentParser(
        description='Consolida registros eliminando duplicados de archivo de entrada'
    )
    parser.add_argument(
        '--entrada',
        required=True,
        help='Ruta al archivo de entrada (.xlsx)'
    )
    parser.add_argument(
        '--matriz',
        required=True,
        help='Ruta a la matriz maestra (.xlsx)'
    )
    parser.add_argument(
        '--output',
        default=None,
        help='Ruta de salida (por defecto: {entrada_sin_extensión}_cleaned.xlsx)'
    )

    args = parser.parse_args()

    # Validar que archivos existan
    entrada_path = Path(args.entrada)
    matriz_path = Path(args.matriz)

    if not entrada_path.exists():
        print(f"ERROR: Archivo de entrada no encontrado: {entrada_path}")
        sys.exit(1)

    if not matriz_path.exists():
        print(f"ERROR: Matriz maestra no encontrada: {matriz_path}")
        sys.exit(1)

    try:
        # Determine output path first
        if args.output:
            output_path = Path(args.output)
        else:
            stem = entrada_path.stem
            output_path = entrada_path.parent / f"{stem}_cleaned.xlsx"

        # Copy entrada to output first if different
        if output_path != entrada_path:
            import shutil
            shutil.copy2(entrada_path, output_path)
            consolidation_input = output_path
        else:
            consolidation_input = entrada_path

        # Consolidate
        print(f"Cargando archivo de entrada: {entrada_path}")
        print(f"Cargando matriz maestra: {matriz_path}")
        print("Detectando duplicados...")

        nuevos, duplicados = consolidate_excel_file(consolidation_input, matriz_path)

        # Show stats
        total_entrada = nuevos + duplicados
        total_matriz = len(load_excel(matriz_path))

        print("\n" + "=" * 50)
        print("  CONSOLIDACIÓN DE REGISTROS")
        print("=" * 50)
        print(f"Archivo de entrada:     {entrada_path}")
        print(f"Matriz maestra:         {matriz_path}")
        print(f"\nRegistros en entrada:   {total_entrada}")
        print(f"Registros en matriz:    {total_matriz}")
        print(f"Duplicados encontrados: {duplicados}")
        print(f"Registros únicos (nuevos): {nuevos}")
        print(f"\nArchivo limpio guardado: {output_path}")
        print("=" * 50)

    except Exception as e:
        print(f"ERROR: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()

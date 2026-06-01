# Integración de Consolidación en Pipeline GENIAL — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Integrate record consolidation into the GENIAL pipeline so users can filter duplicates automatically with `python main.py --consolidate-with-matrix <ruta>`.

**Architecture:** Extract consolidation logic from `consolidate_records.py` into a new `src/pipeline/consolidator.py` module. Modify `main.py` to add the `--consolidate-with-matrix` parameter and call consolidation after Excel export. Refactor `consolidate_records.py` to use the shared consolidator module.

**Tech Stack:** Python 3.10+, pandas, openpyxl, pytest

---

## File Structure

**Files to create:**
- `src/pipeline/consolidator.py` — Consolidation logic (detect sheet, filter duplicates, save)
- `tests/test_consolidator.py` — 5 unit tests for consolidation

**Files to modify:**
- `main.py` — Add `--consolidate-with-matrix` argument, call consolidation post-export
- `consolidate_records.py` — Refactor to import from consolidator module

---

## Implementation Tasks

### Task 1: Create `src/pipeline/consolidator.py` — Core Functions

**Files:**
- Create: `src/pipeline/consolidator.py`
- Test: `tests/test_consolidator.py` (test file structure only)

- [ ] **Step 1: Write failing test for `detect_data_sheet()`**

Create `tests/test_consolidator.py` with first test:

```python
import pytest
from pathlib import Path
import pandas as pd
import tempfile
from src.pipeline.consolidator import detect_data_sheet

def test_detect_data_sheet_standard_name():
    """Test detection of standard 'Matriz Normativa' sheet."""
    # Create temp Excel with standard sheet name
    with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as tmp:
        df = pd.DataFrame({'Título de la Norma': ['Test'], 'Fecha de Publicación': ['2026-01-01']})
        df.to_excel(tmp.name, sheet_name='Matriz Normativa', index=False)
        
        result = detect_data_sheet(Path(tmp.name))
        assert result == 'Matriz Normativa'
        
        Path(tmp.name).unlink()
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd c:\Users\carlo\OneDrive\ -\ Instituto\ Tecnologico\ y\ de\ Estudios\ Superiores\ de\ Monterrey\Desktop\Carlos\ Auquilla\Proyectos\GENIAL\GENIAL_dev
pytest tests/test_consolidator.py::test_detect_data_sheet_standard_name -v
```

Expected: `ModuleNotFoundError: No module named 'src.pipeline.consolidator'`

- [ ] **Step 3: Create consolidator.py with minimal `detect_data_sheet()` implementation**

```python
# src/pipeline/consolidator.py

import logging
from pathlib import Path
from typing import Tuple
import pandas as pd

logger = logging.getLogger(__name__)

def detect_data_sheet(filepath: Path) -> str:
    """
    Auto-detects the sheet containing normative data.
    
    Strategy:
    1. Look for sheets named 'Matriz Normativa' or 'Registro de Normativa'
    2. Look for sheets with keywords: 'matriz', 'normativa', 'registro' (case-insensitive)
    3. Fallback: Return sheet with most rows
    
    Args:
        filepath: Path to Excel file
        
    Returns:
        Sheet name (str)
        
    Raises:
        ValueError: If no suitable sheet found
    """
    xls = pd.ExcelFile(filepath)
    sheets = xls.sheet_names
    
    # Strategy 1: Exact name match
    for sheet in sheets:
        if sheet in ['Matriz Normativa', 'Registro de Normativa']:
            return sheet
    
    # Strategy 2: Keyword match
    keywords = ['matriz', 'normativa', 'registro']
    for sheet in sheets:
        if any(kw in sheet.lower() for kw in keywords):
            return sheet
    
    # Strategy 3: Largest sheet
    sheet_sizes = {sheet: len(pd.read_excel(filepath, sheet_name=sheet)) for sheet in sheets}
    return max(sheet_sizes, key=sheet_sizes.get)
```

- [ ] **Step 4: Run test to verify it passes**

```bash
pytest tests/test_consolidator.py::test_detect_data_sheet_standard_name -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/pipeline/consolidator.py tests/test_consolidator.py
git commit -m "feat: add detect_data_sheet() function with auto-detection logic"
```

---

### Task 2: Add Consolidation Core Functions to `consolidator.py`

**Files:**
- Modify: `src/pipeline/consolidator.py`

- [ ] **Step 1: Write failing tests for helper functions**

Add to `tests/test_consolidator.py`:

```python
def test_consolidate_basic():
    """Test basic consolidation: 10 entrada, 5 duplicates, 5 new."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        
        # Create entrada with 10 records (5 will be duplicates)
        entrada_data = {
            'Título de la Norma': ['Ley A', 'Ley B', 'Ley C', 'Ley D', 'Ley E', 
                                   'Ley F', 'Ley G', 'Ley H', 'Ley I', 'Ley J'],
            'Fecha de Publicación': ['2026-01-01', '2026-01-02', '2026-01-03', '2026-01-04', '2026-01-05',
                                     '2026-01-06', '2026-01-07', '2026-01-08', '2026-01-09', '2026-01-10'],
            'País': ['México'] * 10
        }
        entrada_file = tmpdir / 'entrada.xlsx'
        pd.DataFrame(entrada_data).to_excel(entrada_file, sheet_name='Matriz Normativa', index=False)
        
        # Create matriz with 5 records (matching first 5 of entrada)
        matriz_data = {
            'Título de la Norma': ['Ley A', 'Ley B', 'Ley C', 'Ley D', 'Ley E'],
            'Fecha de Publicación': ['2026-01-01', '2026-01-02', '2026-01-03', '2026-01-04', '2026-01-05'],
            'País': ['México'] * 5
        }
        matriz_file = tmpdir / 'matriz.xlsx'
        pd.DataFrame(matriz_data).to_excel(matriz_file, sheet_name='Registro de Normativa', index=False)
        
        # Consolidate
        from src.pipeline.consolidator import consolidate_excel_file
        nuevos, duplicados = consolidate_excel_file(entrada_file, matriz_file)
        
        assert nuevos == 5
        assert duplicados == 5
        
        # Verify entrada was modified to contain only new records
        resultado = pd.read_excel(entrada_file)
        assert len(resultado) == 5
        assert 'Ley F' in resultado['Título de la Norma'].values
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_consolidator.py::test_consolidate_basic -v
```

Expected: `AttributeError: module 'consolidator' has no attribute 'consolidate_excel_file'`

- [ ] **Step 3: Implement consolidation functions in consolidator.py**

Add to `src/pipeline/consolidator.py`:

```python
def load_excel(filepath: Path, sheet_name: str = 'Registro de Normativa', 
               auto_detect: bool = True) -> pd.DataFrame:
    """Load Excel sheet with auto-detection fallback."""
    try:
        return pd.read_excel(filepath, sheet_name=sheet_name)
    except ValueError:
        if auto_detect:
            detected = detect_data_sheet(filepath)
            logger.info(f"Sheet '{sheet_name}' not found, using detected sheet '{detected}'")
            return pd.read_excel(filepath, sheet_name=detected)
        raise


def find_column_index(df: pd.DataFrame, column_name: str, fallback_index: int = None) -> int:
    """Find column index by name or fallback to index."""
    if column_name in df.columns:
        return list(df.columns).index(column_name)
    if fallback_index is not None:
        return fallback_index
    raise ValueError(f"Column '{column_name}' not found. Available: {list(df.columns)}")


def get_unique_pairs(df: pd.DataFrame, titulo_col: int, fecha_col: int) -> set:
    """Create set of (titulo, fecha) tuples, normalizing whitespace."""
    pairs = set()
    for _, row in df.iterrows():
        titulo = str(row.iloc[titulo_col]).strip() if pd.notna(row.iloc[titulo_col]) else ''
        fecha = str(row.iloc[fecha_col]).strip() if pd.notna(row.iloc[fecha_col]) else ''
        if titulo and fecha:  # Only include non-empty pairs
            pairs.add((titulo, fecha))
    return pairs


def filter_duplicates(entrada_df: pd.DataFrame, matriz_df: pd.DataFrame, 
                     titulo_col: int, fecha_col: int) -> pd.DataFrame:
    """Filter entrada DataFrame, removing rows that exist in matriz."""
    matriz_pairs = get_unique_pairs(matriz_df, titulo_col, fecha_col)
    
    filtered_rows = []
    for idx, row in entrada_df.iterrows():
        titulo = str(row.iloc[titulo_col]).strip() if pd.notna(row.iloc[titulo_col]) else ''
        fecha = str(row.iloc[fecha_col]).strip() if pd.notna(row.iloc[fecha_col]) else ''
        if not titulo or not fecha:
            continue
        if (titulo, fecha) not in matriz_pairs:
            filtered_rows.append(row)
    
    if not filtered_rows:
        return entrada_df.iloc[0:0]  # Return empty DataFrame with same schema
    return pd.DataFrame(filtered_rows)


def consolidate_excel_file(entrada_path: Path, matriz_path: Path) -> Tuple[int, int]:
    """
    Consolidate entrada against matriz, filter duplicates, overwrite entrada file.
    
    Returns:
        (nuevos_count, duplicados_count)
    """
    entrada_path = Path(entrada_path)
    matriz_path = Path(matriz_path)
    
    # Load files with auto-detection
    entrada_df = load_excel(entrada_path, auto_detect=True)
    matriz_df = load_excel(matriz_path, auto_detect=True)
    
    # Find columns
    titulo_col = find_column_index(entrada_df, 'Título de la Norma')
    fecha_col = find_column_index(entrada_df, 'Fecha de Publicación')
    
    # Filter
    entrada_filtrada = filter_duplicates(entrada_df, matriz_df, titulo_col, fecha_col)
    
    # Calculate stats
    total_entrada = len(entrada_df)
    nuevos = len(entrada_filtrada)
    duplicados = total_entrada - nuevos
    
    # Save
    entrada_filtrada.to_excel(entrada_path, sheet_name='Matriz Normativa', index=False)
    
    return nuevos, duplicados
```

- [ ] **Step 4: Run test to verify it passes**

```bash
pytest tests/test_consolidator.py::test_consolidate_basic -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/pipeline/consolidator.py tests/test_consolidator.py
git commit -m "feat: implement consolidate_excel_file() with filtering logic"
```

---

### Task 3: Add Remaining Tests

**Files:**
- Modify: `tests/test_consolidator.py`

- [ ] **Step 1: Write tests for edge cases**

Add to `tests/test_consolidator.py`:

```python
def test_detect_data_sheet_keyword_match():
    """Test detection using keyword 'Registro'."""
    with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as tmp:
        df = pd.DataFrame({'Título de la Norma': ['Test'], 'Fecha de Publicación': ['2026-01-01']})
        df.to_excel(tmp.name, sheet_name='Registro de Normativa', index=False)
        
        result = detect_data_sheet(Path(tmp.name))
        assert result == 'Registro de Normativa'
        
        Path(tmp.name).unlink()


def test_consolidate_all_duplicates():
    """Test when all entrada records are duplicates."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        
        entrada_data = {
            'Título de la Norma': ['Ley A', 'Ley B'],
            'Fecha de Publicación': ['2026-01-01', '2026-01-02'],
            'País': ['México'] * 2
        }
        entrada_file = tmpdir / 'entrada.xlsx'
        pd.DataFrame(entrada_data).to_excel(entrada_file, sheet_name='Matriz Normativa', index=False)
        
        matriz_data = entrada_data.copy()
        matriz_file = tmpdir / 'matriz.xlsx'
        pd.DataFrame(matriz_data).to_excel(matriz_file, sheet_name='Registro de Normativa', index=False)
        
        from src.pipeline.consolidator import consolidate_excel_file
        nuevos, duplicados = consolidate_excel_file(entrada_file, matriz_file)
        
        assert nuevos == 0
        assert duplicados == 2
        
        # Verify entrada is now empty (only headers)
        resultado = pd.read_excel(entrada_file)
        assert len(resultado) == 0


def test_consolidate_no_duplicates():
    """Test when no entrada records are duplicates."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        
        entrada_data = {
            'Título de la Norma': ['Ley C', 'Ley D'],
            'Fecha de Publicación': ['2026-01-03', '2026-01-04'],
            'País': ['México'] * 2
        }
        entrada_file = tmpdir / 'entrada.xlsx'
        pd.DataFrame(entrada_data).to_excel(entrada_file, sheet_name='Matriz Normativa', index=False)
        
        matriz_data = {
            'Título de la Norma': ['Ley A', 'Ley B'],
            'Fecha de Publicación': ['2026-01-01', '2026-01-02'],
            'País': ['México'] * 2
        }
        matriz_file = tmpdir / 'matriz.xlsx'
        pd.DataFrame(matriz_data).to_excel(matriz_file, sheet_name='Registro de Normativa', index=False)
        
        from src.pipeline.consolidator import consolidate_excel_file
        nuevos, duplicados = consolidate_excel_file(entrada_file, matriz_file)
        
        assert nuevos == 2
        assert duplicados == 0
```

- [ ] **Step 2: Run all tests to verify they pass**

```bash
pytest tests/test_consolidator.py -v
```

Expected: 5 PASSED

- [ ] **Step 3: Commit**

```bash
git add tests/test_consolidator.py
git commit -m "test: add remaining consolidation tests (edge cases)"
```

---

### Task 4: Modify `main.py` to Add CLI Parameter

**Files:**
- Modify: `main.py`

- [ ] **Step 1: Add argument parser entry**

In `main.py`, find the `argparse` section (around line 300-350) and add:

```python
parser.add_argument(
    '--consolidate-with-matrix',
    type=str,
    default=None,
    help='Path to master matrix file (.xlsx) to consolidate against. If provided, '
         'filters output Excel to contain only new records (not duplicates).'
)
```

- [ ] **Step 2: Add consolidation call after export**

Find where `excel_exporter.export_to_excel()` is called (around line 390) and add after it:

```python
# Consolidate if requested
if args.consolidate_with_matrix:
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
```

- [ ] **Step 3: Test that parameter is accepted**

```bash
python main.py --help | grep consolidate-with-matrix
```

Expected: See the new parameter in help text

- [ ] **Step 4: Commit**

```bash
git add main.py
git commit -m "feat: add --consolidate-with-matrix parameter to pipeline"
```

---

### Task 5: Refactor `consolidate_records.py` to Use Shared Consolidator

**Files:**
- Modify: `consolidate_records.py`

- [ ] **Step 1: Replace functions with imports**

Refactor the top of `consolidate_records.py` to import from consolidator:

```python
import pandas as pd
from pathlib import Path
import argparse
import sys

from src.pipeline.consolidator import (
    consolidate_excel_file,
    detect_data_sheet,
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
        # Consolidate
        print(f"Cargando archivo de entrada: {entrada_path}")
        print(f"Cargando matriz maestra: {matriz_path}")
        print("Detectando duplicados...")
        
        nuevos, duplicados = consolidate_excel_file(entrada_path, matriz_path)
        
        # Calcular ruta de salida (si se especificó, copiar archivo consolidado)
        if args.output:
            entrada_path.rename(args.output)
            output_file = args.output
        else:
            stem = entrada_path.stem
            output_file = entrada_path.parent / f"{stem}_cleaned.xlsx"
            entrada_path.rename(output_file)
        
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
        print(f"\nArchivo limpio guardado: {output_file}")
        print("=" * 50)
        
    except Exception as e:
        print(f"ERROR: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
```

- [ ] **Step 2: Remove old function definitions**

Delete the old `load_excel()`, `find_column_index()`, `get_unique_pairs()`, `filter_duplicates()`, `save_excel()` functions from `consolidate_records.py` (keep only `main()` and imports).

- [ ] **Step 3: Test that CLI still works**

```bash
python consolidate_records.py --entrada output/normativa_ia_mexico_20260531_1911.xlsx --matriz data/Matriz_Normativa_IA_Educacion_LATAM.xlsx
```

Expected: Works as before, consolidates correctly

- [ ] **Step 4: Commit**

```bash
git add consolidate_records.py
git commit -m "refactor: consolidate_records.py now uses shared consolidator module"
```

---

### Task 6: Manual Test with Pipeline

**Files:**
- No new files

- [ ] **Step 1: Run pipeline with consolidation flag**

```bash
python main.py --max-universities 3 --consolidate-with-matrix data/Matriz_Normativa_IA_Educacion_LATAM.xlsx
```

- [ ] **Step 2: Verify output**

Expected output:
- Pipeline runs normally
- After export, shows consolidation stats:
  ```
  CONSOLIDACIÓN DE REGISTROS
  Registros procesados: X
  Duplicados encontrados: Y
  Registros nuevos: Z
  ```
- Generated Excel contains only Z rows (new records)

- [ ] **Step 3: Verify pipeline without flag still works**

```bash
python main.py --max-universities 3
```

Expected: Works exactly as before, no consolidation

- [ ] **Step 4: Commit**

```bash
git add -A
git commit -m "test: manual verification of consolidated pipeline output"
```

---

## Summary

**Tasks completed:**
1. Create `consolidator.py` with core consolidation functions
2. Implement `consolidate_excel_file()` with tests
3. Add edge case tests (all duplicates, no duplicates, detection)
4. Integrate `--consolidate-with-matrix` parameter into `main.py`
5. Refactor `consolidate_records.py` to use shared module
6. Manual testing to verify end-to-end functionality

**Total tests:** 5 unit tests passing ✓  
**Total files modified:** 3 (main.py, consolidate_records.py)  
**Total files created:** 2 (consolidator.py, test_consolidator.py)  
**Backward compatibility:** ✓ (pipeline without flag works exactly as before)

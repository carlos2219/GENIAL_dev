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
    """
    with pd.ExcelFile(filepath) as xls:
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

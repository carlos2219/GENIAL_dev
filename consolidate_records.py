import pandas as pd
from pathlib import Path


def load_excel(filepath, sheet_name='Matriz Normativa'):
    """
    Carga un archivo Excel y retorna DataFrame.

    Args:
        filepath: Ruta al archivo .xlsx
        sheet_name: Nombre de la hoja (por defecto: 'Matriz Normativa')

    Returns:
        pd.DataFrame con los datos del Excel

    Raises:
        FileNotFoundError: Si el archivo no existe
        ValueError: Si la hoja no existe
    """
    filepath = Path(filepath)

    if not filepath.exists():
        raise FileNotFoundError(f"Archivo no encontrado: {filepath}")

    try:
        df = pd.read_excel(filepath, sheet_name=sheet_name)
        return df
    except ValueError as e:
        if "Worksheet named" in str(e):
            raise ValueError(f"Hoja '{sheet_name}' no encontrada en {filepath}") from e
        raise


def find_column_index(df, column_name, fallback_index=None):
    """
    Encuentra el índice de una columna por nombre.
    Si no encuentra por nombre, usa fallback_index.

    Args:
        df: DataFrame de pandas
        column_name: Nombre de la columna a buscar
        fallback_index: Índice como respaldo (0-based)

    Returns:
        Índice de la columna (0-based)

    Raises:
        ValueError: Si columna no existe y no hay fallback
    """
    if column_name in df.columns:
        return df.columns.get_loc(column_name)

    if fallback_index is not None and fallback_index < len(df.columns):
        return fallback_index

    raise ValueError(f"Columna '{column_name}' no encontrada en {list(df.columns)}")

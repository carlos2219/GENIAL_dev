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

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


def get_unique_pairs(df, titulo_col, fecha_col):
    """
    Extrae tuplas únicas (título, fecha) de un DataFrame.
    Ignora filas con valores nulos.

    Args:
        df: DataFrame con datos
        titulo_col: Índice de columna de título
        fecha_col: Índice de columna de fecha

    Returns:
        set de tuplas (titulo, fecha)
    """
    pairs = set()
    for idx, row in df.iterrows():
        titulo = row.iloc[titulo_col]
        fecha = row.iloc[fecha_col]

        # Ignorar si alguno es nulo
        if pd.notna(titulo) and pd.notna(fecha):
            pairs.add((str(titulo).strip(), str(fecha).strip()))

    return pairs


def filter_duplicates(entrada_df, matriz_df, titulo_col, fecha_col):
    """
    Filtra entrada_df para eliminar registros que existen en matriz_df.
    Compara por (título, fecha).

    Args:
        entrada_df: DataFrame de entrada
        matriz_df: DataFrame de matriz maestra
        titulo_col: Índice de columna de título
        fecha_col: Índice de columna de fecha

    Returns:
        DataFrame de entrada sin duplicados (nuevos registros)
    """
    matriz_pairs = get_unique_pairs(matriz_df, titulo_col, fecha_col)

    # Filtrar: mantener solo filas que NO están en matriz
    filtered_rows = []
    for idx, row in entrada_df.iterrows():
        titulo = row.iloc[titulo_col]
        fecha = row.iloc[fecha_col]

        if pd.notna(titulo) and pd.notna(fecha):
            pair = (str(titulo).strip(), str(fecha).strip())
            if pair not in matriz_pairs:
                filtered_rows.append(row)
        else:
            # Registros con nulos: se incluyen en salida pero con advertencia
            filtered_rows.append(row)

    if filtered_rows:
        return pd.DataFrame(filtered_rows).reset_index(drop=True)
    else:
        return entrada_df.iloc[0:0]  # DataFrame vacío con mismas columnas


def save_excel(df, filepath, sheet_name='Matriz Normativa'):
    """
    Guarda DataFrame a archivo Excel.

    Args:
        df: DataFrame a guardar
        filepath: Ruta de destino (.xlsx)
        sheet_name: Nombre de la hoja
    """
    filepath = Path(filepath)
    filepath.parent.mkdir(parents=True, exist_ok=True)

    df.to_excel(filepath, sheet_name=sheet_name, index=False)

import pandas as pd
from pathlib import Path
import argparse
import sys


def load_excel(filepath, sheet_name='Registro de Normativa', auto_detect=True):
    """
    Carga un archivo Excel y retorna DataFrame.

    Args:
        filepath: Ruta al archivo .xlsx
        sheet_name: Nombre de la hoja (por defecto: 'Registro de Normativa')
        auto_detect: Si True, detecta automáticamente la hoja con más filas si la especificada no existe

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
        if "Worksheet named" in str(e) and auto_detect:
            xls = pd.ExcelFile(filepath)
            sheets = xls.sheet_names
            # Auto-detect: buscar la hoja con más filas (presumiblemente la matriz de datos)
            sheet_sizes = {sheet: len(pd.read_excel(filepath, sheet_name=sheet)) for sheet in sheets}
            best_sheet = max(sheet_sizes, key=sheet_sizes.get)
            print(f"Detectado automáticamente: usando hoja '{best_sheet}' ({sheet_sizes[best_sheet]} filas)")
            df = pd.read_excel(filepath, sheet_name=best_sheet)
            return df
        elif "Worksheet named" in str(e):
            xls = pd.ExcelFile(filepath)
            sheets = xls.sheet_names
            raise ValueError(
                f"Hoja '{sheet_name}' no encontrada en {filepath.name}.\n"
                f"Hojas disponibles: {', '.join(sheets)}"
            ) from e
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
    parser.add_argument(
        '--sheet',
        default='Registro de Normativa',
        help='Nombre de la hoja a procesar (por defecto: Registro de Normativa)'
    )
    parser.add_argument(
        '--sheet-matriz',
        default='Registro de Normativa',
        help='Nombre de la hoja en la matriz maestra (por defecto: Registro de Normativa)'
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
        # Cargar archivos
        print(f"Cargando archivo de entrada: {entrada_path}")
        entrada_df = load_excel(str(entrada_path), sheet_name=args.sheet)

        print(f"Cargando matriz maestra: {matriz_path}")
        matriz_df = load_excel(str(matriz_path), sheet_name=args.sheet_matriz)

        # Encontrar columnas
        try:
            titulo_col = find_column_index(entrada_df, 'Título de la Norma')
            fecha_col = find_column_index(entrada_df, 'Fecha de Publicación')
        except ValueError as e:
            print(f"ERROR: {e}")
            print(f"Columnas disponibles: {list(entrada_df.columns)}")
            sys.exit(1)

        # Filtrar duplicados
        print("Detectando duplicados...")
        entrada_filtrada = filter_duplicates(entrada_df, matriz_df, titulo_col, fecha_col)

        # Calcular estadísticas
        total_entrada = len(entrada_df)
        total_matriz = len(matriz_df)
        duplicados = total_entrada - len(entrada_filtrada)
        nuevos = len(entrada_filtrada)

        # Determinar ruta de salida
        if args.output is None:
            stem = entrada_path.stem
            output_path = entrada_path.parent / f"{stem}_cleaned.xlsx"
        else:
            output_path = Path(args.output)

        # Guardar archivo limpio
        print(f"Guardando archivo limpio: {output_path}")
        save_excel(entrada_filtrada, str(output_path), sheet_name=args.sheet)

        # Mostrar estadísticas
        print("\n" + "="*50)
        print("  CONSOLIDACIÓN DE REGISTROS")
        print("="*50)
        print(f"Archivo de entrada:     {entrada_path}")
        print(f"Matriz maestra:         {matriz_path}")
        print()
        print(f"Registros en entrada:   {total_entrada}")
        print(f"Registros en matriz:    {total_matriz}")
        print(f"Duplicados encontrados: {duplicados}")
        print(f"Registros únicos (nuevos): {nuevos}")
        print()
        print(f"Archivo limpio guardado: {output_path}")
        print("="*50 + "\n")

    except Exception as e:
        print(f"ERROR: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()

import pytest
import pandas as pd
import tempfile
import os
from pathlib import Path

def test_load_excel_basic():
    """Test que carga un archivo Excel válido"""
    # Crear archivo temporal de prueba
    with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as tmp:
        tmp_path = tmp.name

    try:
        # Crear DataFrame de prueba y guardarlo
        df = pd.DataFrame({
            'Título de la Norma': ['Ley 1', 'Ley 2'],
            'Fecha de Publicación': ['01/01/2024', '02/01/2024'],
            'Otra Columna': ['valor1', 'valor2']
        })
        df.to_excel(tmp_path, sheet_name='Matriz Normativa', index=False)

        # Importar y usar función (aún no existe)
        from consolidate_records import load_excel

        result = load_excel(tmp_path, sheet_name='Matriz Normativa')

        assert isinstance(result, pd.DataFrame)
        assert len(result) == 2
        assert 'Título de la Norma' in result.columns
        assert 'Fecha de Publicación' in result.columns
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


def test_load_excel_file_not_found():
    """Test que lanza excepción si archivo no existe"""
    from consolidate_records import load_excel

    with pytest.raises(FileNotFoundError):
        load_excel('/ruta/inexistente.xlsx')


def test_load_excel_sheet_not_found():
    """Test que lanza excepción si hoja no existe"""
    with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as tmp:
        tmp_path = tmp.name

    try:
        df = pd.DataFrame({'Col': [1, 2]})
        df.to_excel(tmp_path, sheet_name='Hoja1', index=False)

        from consolidate_records import load_excel

        with pytest.raises(ValueError, match="Hoja"):
            load_excel(tmp_path, sheet_name='HojaInexistente')
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


def test_find_column_by_name():
    """Test que encuentra columna por nombre exacto"""
    from consolidate_records import find_column_index

    df = pd.DataFrame({
        'Título de la Norma': [1, 2],
        'Fecha de Publicación': [3, 4]
    })

    idx = find_column_index(df, 'Título de la Norma')
    assert idx == 0

    idx = find_column_index(df, 'Fecha de Publicación')
    assert idx == 1


def test_find_column_by_number():
    """Test que usa número de columna como respaldo"""
    from consolidate_records import find_column_index

    df = pd.DataFrame({
        'Col A': [1, 2],
        'Col B': [3, 4]
    })

    # Si nombre no existe, usar número
    idx = find_column_index(df, 'NoExiste', fallback_index=1)
    assert idx == 1


def test_find_column_not_found():
    """Test que lanza excepción si columna no existe"""
    from consolidate_records import find_column_index

    df = pd.DataFrame({'Col': [1, 2]})

    with pytest.raises(ValueError, match="no encontrada"):
        find_column_index(df, 'NoExiste')


def test_get_unique_pairs():
    """Test que extrae tuplas únicas (título, fecha) de un DataFrame"""
    from consolidate_records import get_unique_pairs

    df = pd.DataFrame({
        'Título de la Norma': ['Ley 1', 'Ley 2', 'Ley 1'],
        'Fecha de Publicación': ['01/01/2024', '02/01/2024', '01/01/2024']
    })

    pairs = get_unique_pairs(df, titulo_col=0, fecha_col=1)

    assert isinstance(pairs, set)
    assert len(pairs) == 2
    assert ('Ley 1', '01/01/2024') in pairs
    assert ('Ley 2', '02/01/2024') in pairs


def test_filter_duplicates():
    """Test que filtra filas duplicadas"""
    from consolidate_records import filter_duplicates

    entrada = pd.DataFrame({
        'Título de la Norma': ['Ley A', 'Ley B', 'Ley C'],
        'Fecha de Publicación': ['01/01/2024', '02/01/2024', '03/01/2024'],
        'Extra': ['x', 'y', 'z']
    })

    matriz = pd.DataFrame({
        'Título de la Norma': ['Ley A', 'Ley X'],
        'Fecha de Publicación': ['01/01/2024', '04/01/2024']
    })

    result = filter_duplicates(
        entrada,
        matriz,
        titulo_col=0,
        fecha_col=1
    )

    assert len(result) == 2  # Solo Ley B y Ley C (sin duplicados)
    assert 'Ley A' not in result['Título de la Norma'].values
    assert 'Ley B' in result['Título de la Norma'].values
    assert 'Ley C' in result['Título de la Norma'].values


def test_filter_duplicates_empty():
    """Test cuando entrada está vacía"""
    from consolidate_records import filter_duplicates

    entrada = pd.DataFrame({
        'Título de la Norma': [],
        'Fecha de Publicación': []
    })

    matriz = pd.DataFrame({
        'Título de la Norma': ['Ley A'],
        'Fecha de Publicación': ['01/01/2024']
    })

    result = filter_duplicates(entrada, matriz, titulo_col=0, fecha_col=1)
    assert len(result) == 0


def test_save_excel():
    """Test que guarda DataFrame a Excel"""
    from consolidate_records import save_excel

    df = pd.DataFrame({
        'Título de la Norma': ['Ley 1'],
        'Fecha de Publicación': ['01/01/2024']
    })

    with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as tmp:
        tmp_path = tmp.name

    try:
        save_excel(df, tmp_path, sheet_name='Matriz Normativa')

        # Verificar que se creó y se puede leer
        assert os.path.exists(tmp_path)
        df_read = pd.read_excel(tmp_path, sheet_name='Matriz Normativa')
        assert len(df_read) == 1
        assert df_read.iloc[0, 0] == 'Ley 1'
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


def test_integration_end_to_end():
    """Test de integración: archivo completo entrada → salida"""
    from consolidate_records import (
        load_excel, find_column_index, filter_duplicates, save_excel
    )

    with tempfile.TemporaryDirectory() as tmpdir:
        # Crear archivo de entrada
        entrada_df = pd.DataFrame({
            'Título de la Norma': [
                'Ley Federal de Educación',
                'Ley de IA en Escuelas',
                'Decreto sobre Datos',
                'Reglamento Interno'
            ],
            'Fecha de Publicación': [
                '01/01/2023',
                '15/03/2024',
                '20/05/2024',
                '10/06/2024'
            ],
            'Tipo de norma': ['Ley', 'Ley', 'Decreto', 'Reglamento'],
            'País': ['México', 'México', 'México', 'México']
        })

        entrada_path = Path(tmpdir) / 'entrada.xlsx'
        entrada_df.to_excel(entrada_path, sheet_name='Matriz Normativa', index=False)

        # Crear matriz maestra (con algunos duplicados)
        matriz_df = pd.DataFrame({
            'Título de la Norma': [
                'Ley Federal de Educación',
                'Decreto sobre Datos'
            ],
            'Fecha de Publicación': [
                '01/01/2023',
                '20/05/2024'
            ],
            'Tipo de norma': ['Ley', 'Decreto']
        })

        matriz_path = Path(tmpdir) / 'matriz.xlsx'
        matriz_df.to_excel(matriz_path, sheet_name='Matriz Normativa', index=False)

        # Procesar
        entrada_loaded = load_excel(str(entrada_path), sheet_name='Matriz Normativa')
        matriz_loaded = load_excel(str(matriz_path), sheet_name='Matriz Normativa')

        titulo_col = find_column_index(entrada_loaded, 'Título de la Norma')
        fecha_col = find_column_index(entrada_loaded, 'Fecha de Publicación')

        resultado = filter_duplicates(entrada_loaded, matriz_loaded, titulo_col, fecha_col)

        # Validaciones
        assert len(resultado) == 2  # Solo nuevos registros
        assert 'Ley de IA en Escuelas' in resultado['Título de la Norma'].values
        assert 'Reglamento Interno' in resultado['Título de la Norma'].values
        assert 'Ley Federal de Educación' not in resultado['Título de la Norma'].values

        # Guardar y verificar
        output_path = Path(tmpdir) / 'salida.xlsx'
        save_excel(resultado, str(output_path), sheet_name='Matriz Normativa')

        # Leer de nuevo para validar
        resultado_leido = pd.read_excel(output_path, sheet_name='Matriz Normativa')
        assert len(resultado_leido) == 2
        assert list(resultado_leido.columns) == list(entrada_loaded.columns)

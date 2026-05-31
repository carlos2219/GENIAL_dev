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

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

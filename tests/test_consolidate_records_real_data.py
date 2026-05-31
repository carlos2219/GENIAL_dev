"""
Test de integración con datos REALES del proyecto GENIAL.
Verifica que el script funciona con los archivos actuales.
"""
import pytest
import pandas as pd
from pathlib import Path
from consolidate_records import (
    load_excel, find_column_index, filter_duplicates, save_excel
)


@pytest.mark.integration
def test_with_real_project_files():
    """
    Test con archivos reales del proyecto.
    Requiere que existan:
    - output/normativa_ia_mexico_20260531_1702.xlsx (entrada)
    - data/Matriz_Normativa_IA_Educacion_LATAM.xlsx (matriz)
    """
    # Rutas de proyecto
    project_root = Path(__file__).parent.parent
    entrada_path = project_root / 'output' / 'normativa_ia_mexico_20260531_1702.xlsx'
    matriz_path = project_root / 'data' / 'Matriz_Normativa_IA_Educacion_LATAM.xlsx'

    # Skip si archivos no existen
    if not entrada_path.exists() or not matriz_path.exists():
        pytest.skip(f"Archivos reales no encontrados")

    # Cargar con sus respectivas hojas
    entrada_df = load_excel(str(entrada_path), sheet_name='Matriz Normativa')
    matriz_df = load_excel(str(matriz_path), sheet_name='Registro de Normativa')

    # Encontrar columnas
    titulo_col = find_column_index(entrada_df, 'Título de la Norma')
    fecha_col = find_column_index(entrada_df, 'Fecha de Publicación')

    # Filtrar
    resultado = filter_duplicates(entrada_df, matriz_df, titulo_col, fecha_col)

    # Validaciones básicas
    assert isinstance(resultado, pd.DataFrame)
    assert len(resultado) <= len(entrada_df)
    assert all(col in resultado.columns for col in entrada_df.columns)

    # Mostrar estadísticas para debugging
    print(f"\nDatos reales:")
    print(f"  Entrada total: {len(entrada_df)}")
    print(f"  Matriz: {len(matriz_df)}")
    print(f"  Resultado (nuevos): {len(resultado)}")
    print(f"  Duplicados eliminados: {len(entrada_df) - len(resultado)}")

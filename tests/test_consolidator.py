import pytest
from pathlib import Path
import pandas as pd
import tempfile
import gc
from src.pipeline.consolidator import detect_data_sheet, consolidate_excel_file

def test_detect_data_sheet_standard_name():
    """Test detection of standard 'Matriz Normativa' sheet."""
    # Create temp Excel with standard sheet name
    with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as tmp:
        tmp_path = Path(tmp.name)

    try:
        df = pd.DataFrame({'Título de la Norma': ['Test'], 'Fecha de Publicación': ['2026-01-01']})
        df.to_excel(tmp_path, sheet_name='Matriz Normativa', index=False)

        result = detect_data_sheet(tmp_path)
        assert result == 'Matriz Normativa'
    finally:
        gc.collect()  # Force garbage collection to release file handles
        tmp_path.unlink(missing_ok=True)


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
        nuevos, duplicados = consolidate_excel_file(entrada_file, matriz_file)

        assert nuevos == 5
        assert duplicados == 5

        # Verify entrada was modified to contain only new records
        resultado = pd.read_excel(entrada_file)
        assert len(resultado) == 5
        assert 'Ley F' in resultado['Título de la Norma'].values

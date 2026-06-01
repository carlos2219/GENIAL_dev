import pytest
from pathlib import Path
import pandas as pd
import tempfile
import gc
from src.pipeline.consolidator import detect_data_sheet

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

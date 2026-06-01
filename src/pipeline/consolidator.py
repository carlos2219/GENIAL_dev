# src/pipeline/consolidator.py

import logging
from pathlib import Path
from typing import Tuple
import pandas as pd

logger = logging.getLogger(__name__)

def detect_data_sheet(filepath: Path) -> str:
    """
    Auto-detects the sheet containing normative data.

    Strategy:
    1. Look for sheets named 'Matriz Normativa' or 'Registro de Normativa'
    2. Look for sheets with keywords: 'matriz', 'normativa', 'registro' (case-insensitive)
    3. Fallback: Return sheet with most rows

    Args:
        filepath: Path to Excel file

    Returns:
        Sheet name (str)

    Raises:
        ValueError: If no suitable sheet found
    """
    with pd.ExcelFile(filepath) as xls:
        sheets = xls.sheet_names

        # Strategy 1: Exact name match
        for sheet in sheets:
            if sheet in ['Matriz Normativa', 'Registro de Normativa']:
                return sheet

        # Strategy 2: Keyword match
        keywords = ['matriz', 'normativa', 'registro']
        for sheet in sheets:
            if any(kw in sheet.lower() for kw in keywords):
                return sheet

        # Strategy 3: Largest sheet
        sheet_sizes = {sheet: len(pd.read_excel(filepath, sheet_name=sheet)) for sheet in sheets}
        return max(sheet_sizes, key=sheet_sizes.get)

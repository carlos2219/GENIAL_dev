# Consolidación de Registros Normativos — Plan de Implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implementar script CLI `consolidate_records.py` que elimine registros duplicados del archivo de entrada comparando por título+fecha contra la matriz maestra, generando una copia limpia con estadísticas.

**Architecture:** Script modular con funciones independientes para carga de datos, identificación de columnas, filtrado de duplicados y exportación. Tests unitarios + test de integración con datos reales del proyecto.

**Tech Stack:** Python 3.10+, pandas, openpyxl, pytest

---

## Estructura de Archivos

```
GENIAL_dev/
├── consolidate_records.py          # Script principal CLI
├── tests/
│   ├── __init__.py
│   └── test_consolidate_records.py # Tests unitarios + integración
└── docs/superpowers/
    └── plans/
        └── 2026-05-31-consolidacion-registros.md (este archivo)
```

---

## Task 1: Preparar Estructura Base y Tests

**Files:**
- Create: `consolidate_records.py`
- Create: `tests/test_consolidate_records.py`

- [ ] **Step 1: Crear archivo principal vacío**

```bash
# En PowerShell desde raíz del proyecto
New-Item -Path consolidate_records.py -ItemType File -Force
```

- [ ] **Step 2: Crear directorio y archivo de tests**

```bash
# Si no existe
if (-not (Test-Path tests)) { New-Item -ItemType Directory -Path tests }
New-Item -Path tests/__init__.py -ItemType File -Force
New-Item -Path tests/test_consolidate_records.py -ItemType File -Force
```

- [ ] **Step 3: Escribir test skeleton en `tests/test_consolidate_records.py`**

```python
import pytest
import pandas as pd
import tempfile
import os
from pathlib import Path

# Tests serán agregados en siguientes tareas
```

- [ ] **Step 4: Ejecutar pytest para verificar que se descubre el archivo**

```bash
pytest tests/test_consolidate_records.py -v
```

Expected: `collected 0 items` (sin errores)

- [ ] **Step 5: Commit**

```bash
git add consolidate_records.py tests/
git commit -m "feat: init consolidate_records script structure"
```

---

## Task 2: Implementar Función de Carga de Archivos Excel

**Files:**
- Modify: `consolidate_records.py`
- Modify: `tests/test_consolidate_records.py`

- [ ] **Step 1: Escribir test para carga de archivo**

Agrega al final de `tests/test_consolidate_records.py`:

```python
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
```

- [ ] **Step 2: Ejecutar tests para verificar que fallan**

```bash
pytest tests/test_consolidate_records.py::test_load_excel_basic -v
```

Expected: FAIL - `ImportError: cannot import name 'load_excel'`

- [ ] **Step 3: Implementar función `load_excel` en `consolidate_records.py`**

```python
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
```

- [ ] **Step 4: Ejecutar todos los tests de carga**

```bash
pytest tests/test_consolidate_records.py::test_load_excel_basic tests/test_consolidate_records.py::test_load_excel_file_not_found tests/test_consolidate_records.py::test_load_excel_sheet_not_found -v
```

Expected: `3 passed`

- [ ] **Step 5: Commit**

```bash
git add consolidate_records.py tests/test_consolidate_records.py
git commit -m "feat: implement load_excel function with tests"
```

---

## Task 3: Implementar Identificación de Columnas

**Files:**
- Modify: `consolidate_records.py`
- Modify: `tests/test_consolidate_records.py`

- [ ] **Step 1: Escribir tests para identificación de columnas**

Agrega al final de `tests/test_consolidate_records.py`:

```python
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
```

- [ ] **Step 2: Ejecutar tests para verificar que fallan**

```bash
pytest tests/test_consolidate_records.py::test_find_column_by_name -v
```

Expected: FAIL - `ImportError: cannot import name 'find_column_index'`

- [ ] **Step 3: Implementar función `find_column_index` en `consolidate_records.py`**

```python
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
```

- [ ] **Step 4: Ejecutar todos los tests de columnas**

```bash
pytest tests/test_consolidate_records.py::test_find_column_by_name tests/test_consolidate_records.py::test_find_column_by_number tests/test_consolidate_records.py::test_find_column_not_found -v
```

Expected: `3 passed`

- [ ] **Step 5: Commit**

```bash
git add consolidate_records.py tests/test_consolidate_records.py
git commit -m "feat: implement column identification with fallback"
```

---

## Task 4: Implementar Comparación y Filtrado de Duplicados

**Files:**
- Modify: `consolidate_records.py`
- Modify: `tests/test_consolidate_records.py`

- [ ] **Step 1: Escribir tests para detección de duplicados**

Agrega al final de `tests/test_consolidate_records.py`:

```python
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
```

- [ ] **Step 2: Ejecutar tests para verificar que fallan**

```bash
pytest tests/test_consolidate_records.py::test_get_unique_pairs -v
```

Expected: FAIL - `ImportError`

- [ ] **Step 3: Implementar funciones de filtrado**

Agrega a `consolidate_records.py`:

```python
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
```

- [ ] **Step 4: Ejecutar todos los tests de filtrado**

```bash
pytest tests/test_consolidate_records.py::test_get_unique_pairs tests/test_consolidate_records.py::test_filter_duplicates tests/test_consolidate_records.py::test_filter_duplicates_empty -v
```

Expected: `3 passed`

- [ ] **Step 5: Commit**

```bash
git add consolidate_records.py tests/test_consolidate_records.py
git commit -m "feat: implement duplicate detection and filtering"
```

---

## Task 5: Implementar Exportación de Archivo Limpio

**Files:**
- Modify: `consolidate_records.py`
- Modify: `tests/test_consolidate_records.py`

- [ ] **Step 1: Escribir test para guardar archivo**

Agrega al final de `tests/test_consolidate_records.py`:

```python
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
```

- [ ] **Step 2: Ejecutar test para verificar que falla**

```bash
pytest tests/test_consolidate_records.py::test_save_excel -v
```

Expected: FAIL - `ImportError`

- [ ] **Step 3: Implementar función `save_excel`**

Agrega a `consolidate_records.py`:

```python
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
```

- [ ] **Step 4: Ejecutar test de guardado**

```bash
pytest tests/test_consolidate_records.py::test_save_excel -v
```

Expected: `1 passed`

- [ ] **Step 5: Commit**

```bash
git add consolidate_records.py tests/test_consolidate_records.py
git commit -m "feat: implement Excel export function"
```

---

## Task 6: Implementar CLI con Argumentos

**Files:**
- Modify: `consolidate_records.py`

- [ ] **Step 1: Agregar imports y función CLI**

Agrega al inicio de `consolidate_records.py`:

```python
import argparse
import sys
```

Agrega al final:

```python
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
        default='Matriz Normativa',
        help='Nombre de la hoja a procesar (por defecto: Matriz Normativa)'
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
        matriz_df = load_excel(str(matriz_path), sheet_name=args.sheet)
        
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
```

- [ ] **Step 2: Probar CLI con --help**

```bash
python consolidate_records.py --help
```

Expected: Muestra opciones de argumentos

- [ ] **Step 3: Commit**

```bash
git add consolidate_records.py
git commit -m "feat: implement CLI with argument parsing"
```

---

## Task 7: Test de Integración con Datos Reales

**Files:**
- Modify: `tests/test_consolidate_records.py`

- [ ] **Step 1: Crear test de integración end-to-end**

Agrega al final de `tests/test_consolidate_records.py`:

```python
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
```

- [ ] **Step 2: Ejecutar test de integración**

```bash
pytest tests/test_consolidate_records.py::test_integration_end_to_end -v
```

Expected: `1 passed`

- [ ] **Step 3: Commit**

```bash
git add tests/test_consolidate_records.py
git commit -m "test: add end-to-end integration test"
```

---

## Task 8: Test con Datos Reales del Proyecto

**Files:**
- Create: `tests/test_consolidate_records_real_data.py`

- [ ] **Step 1: Crear archivo de test con datos reales**

```bash
New-Item -Path tests/test_consolidate_records_real_data.py -ItemType File -Force
```

Contenido de `tests/test_consolidate_records_real_data.py`:

```python
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
    
    # Cargar
    entrada_df = load_excel(str(entrada_path))
    matriz_df = load_excel(str(matriz_path))
    
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
```

- [ ] **Step 2: Ejecutar test con datos reales**

```bash
pytest tests/test_consolidate_records_real_data.py::test_with_real_project_files -v -s
```

Expected: Muestra estadísticas reales del proyecto, test PASS o SKIP

- [ ] **Step 3: Commit**

```bash
git add tests/test_consolidate_records_real_data.py
git commit -m "test: add integration test with real project data"
```

---

## Task 9: Ejecutar Suite Completa de Tests

**Files:**
- No new files

- [ ] **Step 1: Ejecutar todos los tests unitarios**

```bash
pytest tests/test_consolidate_records.py -v
```

Expected: Todos los tests PASS

- [ ] **Step 2: Ejecutar todos los tests incluyendo integración**

```bash
pytest tests/ -v
```

Expected: Todos los tests PASS

- [ ] **Step 3: Ejecutar test de cobertura (opcional)**

```bash
pytest tests/test_consolidate_records.py --cov=consolidate_records --cov-report=term-missing
```

Expected: Alta cobertura (>90%)

- [ ] **Step 4: Commit final**

```bash
git add -A
git commit -m "test: all tests passing, integration verified"
```

---

## Task 10: Prueba Manual con CLI

**Files:**
- No new files

- [ ] **Step 1: Probar CLI con archivos reales del proyecto**

```bash
python consolidate_records.py `
  --entrada output/normativa_ia_mexico_20260531_1702.xlsx `
  --matriz data/Matriz_Normativa_IA_Educacion_LATAM.xlsx
```

Expected: 
- Carga ambos archivos sin error
- Muestra estadísticas de duplicados/nuevos
- Crea archivo `output/normativa_ia_mexico_20260531_1702_cleaned.xlsx`

- [ ] **Step 2: Verificar archivo de salida**

```bash
# Listar archivo generado
Get-ChildItem output/ -Filter "*cleaned.xlsx" -Recurse
```

Expected: `normativa_ia_mexico_20260531_1702_cleaned.xlsx` existe

- [ ] **Step 3: Verificar contenido del archivo**

```python
import pandas as pd
df = pd.read_excel('output/normativa_ia_mexico_20260531_1702_cleaned.xlsx', sheet_name='Matriz Normativa')
print(f"Registros en archivo limpio: {len(df)}")
print(df.head())
```

Expected: DataFrame con registros nuevos (sin duplicados)

- [ ] **Step 4: Commit**

```bash
git add -A
git commit -m "test: manual CLI verification with real data passed"
```

---

## Checklist de Aceptación

- [ ] Script `consolidate_records.py` creado y funcional
- [ ] Todos los tests unitarios PASS
- [ ] Test de integración PASS
- [ ] CLI con argumentos funciona correctamente
- [ ] Archivo limpio se genera correctamente
- [ ] Estadísticas mostradas son correctas
- [ ] Manejo de errores es claro e informativo
- [ ] Documentación interna (docstrings) presente
- [ ] Todos los commits limpios y con mensajes descriptivos

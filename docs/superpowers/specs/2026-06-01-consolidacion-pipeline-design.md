# Diseño: Integración de Consolidación de Registros en Pipeline GENIAL

**Fecha:** 2026-06-01  
**Proyecto:** GENIAL — Levantamiento Normativo de IA en Educación  
**Objetivo:** Integrar el sistema de consolidación de registros directamente en el pipeline para filtrar automáticamente duplicados contra la matriz maestra antes de exportar a Excel.

---

## 1. Descripción General

Actualmente, el investigador ejecuta el pipeline GENIAL para generar un archivo Excel con registros normativos. Luego, manualmente ejecuta `consolidate_records.py` para filtrar duplicados contra la matriz maestra.

**Solución:** Integrar esta consolidación como parámetro opcional del pipeline. Si el usuario especifica `--consolidate-with-matrix <ruta>`, el pipeline generará un Excel que contiene SOLO registros nuevos (no duplicados).

### Flujo Actual vs. Nuevo

**Actual:**
```
python main.py
  → genera normativa_ia_mexico_*.xlsx (150 registros)
  
python consolidate_records.py --entrada ... --matriz ...
  → genera normativa_ia_mexico_*_cleaned.xlsx (61 registros nuevos)
```

**Nuevo:**
```
python main.py --consolidate-with-matrix data/Matriz_Normativa_IA_Educacion_LATAM.xlsx
  → genera normativa_ia_mexico_*.xlsx (61 registros nuevos, sin duplicados)
```

---

## 2. Especificación Funcional

### 2.1 Parámetro CLI

**Nuevo argumento en main.py:**
```
--consolidate-with-matrix RUTA
    Ruta a la matriz maestra (archivo .xlsx)
    Tipo: str (ruta relativa o absoluta)
    Requerido: No
    Por defecto: None (sin consolidación)
    Ejemplo: python main.py --consolidate-with-matrix data/Matriz_Normativa_IA_Educacion_LATAM.xlsx
```

Si no se especifica, el pipeline funciona exactamente como hoy (sin cambios).

### 2.2 Cuando se Activa

El parámetro es procesado DESPUÉS de que `excel_exporter.export_to_excel()` genera el archivo. Flujo:

```
1. Pipeline ejecuta fases 1-10 normalmente
2. excel_exporter genera: output/normativa_ia_mexico_*.xlsx
3. SI --consolidate-with-matrix está presente:
   a. Cargar el Excel generado (hoja auto-detectada)
   b. Cargar matriz maestra (hoja auto-detectada)
   c. Filtrar duplicados por (título, fecha)
   d. Sobrescribir el Excel con solo registros nuevos
   e. Mostrar estadísticas en consola
4. Pipeline termina
```

### 2.3 Auto-detección de Hojas

Ambos archivos (entrada y matriz) tienen auto-detección inteligente:

1. **Buscar por nombre:** "Matriz Normativa", "Registro de Normativa"
2. **Buscar por palabras clave:** "matriz", "normativa", "registro" (case-insensitive)
3. **Fallback:** Usar la hoja con más filas

Ver `consolidator.py:detect_data_sheet()` para implementación.

### 2.4 Definición de Duplicado

Un registro se considera **duplicado** si existe en ambos archivos con:
- **Título idéntico** (columna "Título de la Norma")
- **Fecha idéntica** (columna "Fecha de Publicación")

Comparación es case-sensitive, con `.strip()` de espacios en blanco.

### 2.5 Estadísticas en Consola

Después de consolidar, mostrar:
```
Consolidando contra matriz maestra...
  Archivo de entrada:     output/normativa_ia_mexico_20260601_1421.xlsx
  Matriz maestra:         data/Matriz_Normativa_IA_Educacion_LATAM.xlsx
  
  Registros procesados:   70
  Duplicados encontrados: 59
  Registros nuevos:       11
  
Archivo consolidado guardado: output/normativa_ia_mexico_20260601_1421.xlsx
```

---

## 3. Especificación Técnica

### 3.1 Arquitectura

**Nuevo módulo:** `src/pipeline/consolidator.py`

```python
def detect_data_sheet(filepath: Path) -> str:
    """Detecta automáticamente el nombre de la hoja de datos."""
    # Retorna nombre de hoja

def consolidate_excel_file(entrada_path: Path, matriz_path: Path) -> tuple[int, int]:
    """
    Consolida entrada contra matriz.
    Retorna: (registros_nuevos, duplicados_encontrados)
    """
    # Implementación
```

**Modificación:** `main.py`

- Agregar argumento: `parser.add_argument('--consolidate-with-matrix', ...)`
- Después de exportar: `consolidate_if_needed(output_file, args.consolidate_with_matrix)`

### 3.2 Reutilización de Código

La lógica de filtrado ya existe en `consolidate_records.py`:
- `load_excel()`
- `find_column_index()`
- `get_unique_pairs()`
- `filter_duplicates()`

Se extraerá a `consolidator.py` para reutilización desde ambos lugares (CLI y pipeline).

### 3.3 Manejo de Errores

| Escenario | Acción |
|-----------|--------|
| `--consolidate-with-matrix` especificado pero archivo no existe | Error claro, pipeline termina |
| Columnas requeridas no encontradas en entrada | Error claro, listar disponibles |
| Columnas requeridas no encontradas en matriz | Error claro, listar disponibles |
| No hay registros nuevos (todos duplicados) | Información, Excel vacío pero válido |
| 0 duplicados encontrados (todos nuevos) | Información, archivo sin cambios |

---

## 4. Especificación de Tests

### 4.1 Tests Unitarios

**Archivo:** `tests/test_consolidator.py`

1. **test_detect_data_sheet_standard_name**
   - Input: Excel con hoja "Matriz Normativa"
   - Output: "Matriz Normativa"

2. **test_detect_data_sheet_keyword_match**
   - Input: Excel con hoja "Registro de Normativa"
   - Output: "Registro de Normativa"

3. **test_consolidate_basic**
   - Input: 10 registros en entrada, 5 iguales en matriz
   - Output: 5 nuevos, 5 duplicados
   - Verifica: Excel sobrescrito contiene solo 5 filas

4. **test_consolidate_all_duplicates**
   - Input: 10 registros, todos en matriz
   - Output: 0 nuevos, 10 duplicados
   - Verifica: Excel sobrescrito está vacío (solo headers)

5. **test_consolidate_no_duplicates**
   - Input: 10 registros, ninguno en matriz
   - Output: 10 nuevos, 0 duplicados
   - Verifica: Excel sobrescrito sin cambios

### 4.2 Prueba Manual

Después de integrar en `main.py`:
```bash
python main.py --max-universities 5 --consolidate-with-matrix data/Matriz_Normativa_IA_Educacion_LATAM.xlsx
# Verificar: Excel generado contiene solo registros nuevos
```

---

## 5. Cambios de Archivo

| Archivo | Acción | Detalles |
|---------|--------|----------|
| `src/pipeline/consolidator.py` | Crear | Nueva función `consolidate_excel_file()` |
| `main.py` | Modificar | Agregar argumento `--consolidate-with-matrix` y lógica post-exportación |
| `consolidate_records.py` | Refactorizar | Importar `consolidate_excel_file()` de `consolidator.py` |
| `tests/test_consolidator.py` | Crear | 5 tests de consolidación |

---

## 6. Restricciones y Supuestos

1. **Matriz maestra:** No se modifica, solo se lee
2. **Archivo de entrada:** Se sobrescribe con datos consolidados
3. **Columnas requeridas:** "Título de la Norma" y "Fecha de Publicación" deben existir en AMBOS archivos
4. **Deduplicación interna:** Duplicados internos dentro del archivo de entrada se preservan (no se eliminan)
5. **Whitespace:** Se normaliza con `.strip()` antes de comparar
6. **Permisos:** Usuario debe tener permisos de lectura en matriz y escritura en output/

---

## 7. Aceptación

El sistema se considera completo cuando:
- ✓ `main.py` acepta `--consolidate-with-matrix` sin errores
- ✓ Pipeline sin flag funciona igual que antes (sin cambios)
- ✓ Pipeline con flag filtra correctamente duplicados
- ✓ Estadísticas mostradas en consola son correctas
- ✓ 5 tests unitarios pasan
- ✓ Prueba manual genera Excel con solo registros nuevos
- ✓ `consolidate_records.py` continúa funcionando como CLI independiente

---

## 8. Notas de Implementación

- Reutilizar lógica existente de `consolidate_records.py`
- TDD: escribir tests ANTES de implementación
- Mantener `consolidate_records.py` como herramienta independiente (no deprecated)
- Auto-detección de hojas ya está probada y funciona bien
- Considerar logging detallado si `--verbose` está activo

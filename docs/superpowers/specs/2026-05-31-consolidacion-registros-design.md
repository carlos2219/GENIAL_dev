# Diseño: Sistema de Consolidación de Registros Normativos

**Fecha:** 2026-05-31  
**Proyecto:** GENIAL — Levantamiento Normativo de IA en Educación  
**Objetivo:** Implementar un script CLI que elimine registros duplicados del archivo de entrada comparándolos contra la matriz maestra, generando una copia limpia lista para integración manual.

---

## 1. Descripción General

El investigador actualmente:
- Ejecuta el pipeline GENIAL generando archivos de entrada con nuevos registros (ej: `output/normativa_ia_mexico_20260531_1702.xlsx`)
- Mantiene una matriz maestra consolidada (`data/Matriz_Normativa_IA_Educacion_LATAM.xlsx`)
- Agrega manualmente los registros nuevos a la matriz

**Problema:** Sin un sistema de consolidación, es difícil distinguir visualmente qué registros ya existen en la matriz y cuáles son nuevos.

**Solución:** Script que compare automáticamente y elimine duplicados, dejando solo registros nuevos para revisión e integración manual.

---

## 2. Especificación Funcional

### 2.1 Definición de Duplicado

Un registro se considera **duplicado** si existe en ambos archivos con:
- **Título idéntico** (campo "Título de la Norma")
- **Fecha idéntica** (campo "Fecha de Publicación")

La comparación es case-sensitive y requiere coincidencia exacta.

### 2.2 Flujo de Ejecución

```
┌─────────────────────────────────────┐
│ Usuario: python consolidate_records │
│ --entrada INPUT.xlsx --matriz MATRIZ│
└─────────────────────────────────────┘
              ↓
┌─────────────────────────────────────┐
│ Cargar ambos archivos con pandas    │
│ (hoja "Matriz Normativa" por defect)│
└─────────────────────────────────────┘
              ↓
┌─────────────────────────────────────┐
│ Identificar columnas por:           │
│ 1. Nombre (ej: "Título de la Norma")│
│ 2. Número de columna (respaldo)     │
└─────────────────────────────────────┘
              ↓
┌─────────────────────────────────────┐
│ Crear tuples (título, fecha) para   │
│ matriz → conjunto de tuplas únicas  │
└─────────────────────────────────────┘
              ↓
┌─────────────────────────────────────┐
│ Filtrar entrada: mantener solo      │
│ tuplas que NO están en matriz       │
└─────────────────────────────────────┘
              ↓
┌─────────────────────────────────────┐
│ Guardar copia limpia:               │
│ INPUT_cleaned.xlsx                  │
└─────────────────────────────────────┘
              ↓
┌─────────────────────────────────────┐
│ Mostrar estadísticas:               │
│ "X registros → Y únicos, Z eliminad"│
└─────────────────────────────────────┘
```

### 2.3 Interfaz de Línea de Comandos

**Uso básico:**
```bash
python consolidate_records.py --entrada output/normativa_ia_mexico_20260531_1702.xlsx --matriz data/Matriz_Normativa_IA_Educacion_LATAM.xlsx
```

**Con salida personalizada:**
```bash
python consolidate_records.py \
  --entrada output/normativa_ia_mexico_20260531_1702.xlsx \
  --matriz data/Matriz_Normativa_IA_Educacion_LATAM.xlsx \
  --output output/normativa_limpia_custom.xlsx
```

**Parámetros:**
- `--entrada` (obligatorio): ruta al archivo de entrada
- `--matriz` (obligatorio): ruta a la matriz maestra
- `--output` (opcional): ruta de salida. Por defecto: `{entrada_sin_extension}_cleaned.xlsx`
- `--sheet` (opcional): nombre de la hoja de trabajo. Por defecto: "Matriz Normativa"

---

## 3. Especificación Técnica

### 3.1 Stack Tecnológico

- **Lenguaje:** Python 3.10+
- **Librerías:** `pandas`, `openpyxl` (ya presentes en requirements.txt del proyecto)
- **Ubicación:** `consolidate_records.py` en raíz del proyecto

### 3.2 Estrategia de Identificación de Columnas

Para robustez ante posibles cambios en nombres de columnas:

1. **Primero:** Buscar por nombre exacto ("Título de la Norma", "Fecha de Publicación")
2. **Si no encuentra:** Usar número de columna (ej: columna 1 para título, columna 9 para fecha)
3. **Si tampoco:** Lanzar excepción clara indicando qué columnas se necesitan

### 3.3 Manejo de Valores Nulos

- Títulos o fechas **vacías/nulas:** considerar como registros **inválidos** y **omitir de la comparación** (mostrar advertencia)
- No se eliminan automáticamente; solo se avisa

### 3.4 Comparación Case-Sensitive

- "Ley Federal" ≠ "ley federal" (diferentes)
- Espacios en blanco son significativos ("Ley " ≠ "Ley")

---

## 4. Especificación de Errores

| Escenario | Acción |
|-----------|--------|
| Archivo de entrada no existe | Excepción clara, proponer ruta relativa |
| Matriz no existe | Excepción clara, proponer ruta relativa |
| Columnas no encontradas | Listar columnas disponibles, solicitar por nombre o número |
| No hay registros en entrada | Advertencia, crear archivo vacío |
| 0 duplicados encontrados | Información, la copia es idéntica a la entrada |

---

## 5. Salida y Reportería

### 5.1 Archivo Generado

- **Nombre:** `{nombre_entrada}_cleaned.xlsx`
- **Contenido:** Todas las columnas del archivo de entrada, solo filas sin duplicados
- **Formato:** XLSX, compatible con Excel

### 5.2 Estadísticas en Consola

```
═══════════════════════════════════════
  CONSOLIDACIÓN DE REGISTROS
═══════════════════════════════════════
Archivo de entrada: output/normativa_ia_mexico_20260531_1702.xlsx
Matriz maestra:     data/Matriz_Normativa_IA_Educacion_LATAM.xlsx

Registros en entrada:     100
Registros en matriz:      250
Duplicados encontrados:   15
Registros únicos (nuevos): 85

Archivo limpio guardado: output/normativa_ia_mexico_20260531_1702_cleaned.xlsx
═══════════════════════════════════════
```

---

## 6. Restricciones y Supuestos

1. **Una sola hoja:** Solo procesa la hoja "Matriz Normativa" (configurable con `--sheet`)
2. **Orden de columnas:** No es crítico; busca por nombre
3. **Permisos:** Usuario tiene permisos de lectura en ambos archivos y escritura en `output/`
4. **Encoding:** UTF-8 (estándar XLSX)
5. **Duplicados internos dentro de entrada:** No se eliminan (ej: si entrada tiene 2 filas idénticas, ambas permanecen)
6. **No modifica la matriz:** Solo se modifica el archivo de entrada (creando copia limpia)

---

## 7. Casos de Uso

### Caso 1: Consolidación Estándar
```bash
python consolidate_records.py \
  --entrada output/normativa_ia_mexico_20260531_1702.xlsx \
  --matriz data/Matriz_Normativa_IA_Educacion_LATAM.xlsx
# → Genera normativa_ia_mexico_20260531_1702_cleaned.xlsx
```

### Caso 2: Con Ruta Personalizada
```bash
python consolidate_records.py \
  --entrada output/temp.xlsx \
  --matriz data/Matriz_Normativa_IA_Educacion_LATAM.xlsx \
  --output output/revisados.xlsx
# → Genera revisados.xlsx
```

### Caso 3: Hoja Alternativa
```bash
python consolidate_records.py \
  --entrada output/normativa.xlsx \
  --matriz data/matriz_respaldo.xlsx \
  --sheet "Datos Alternativos"
# → Procesa hoja "Datos Alternativos" en ambos archivos
```

---

## 8. Futuras Extensiones (Out of Scope)

- Comparación por otros campos (URL, emisor, etc.)
- Merge automático a la matriz maestra
- Interfaz gráfica
- Sincronización bidireccional

---

## 9. Aceptación

El sistema se considera completo cuando:
- ✓ Script CLI funciona sin errores con archivos reales
- ✓ Identifica correctamente duplicados por título+fecha
- ✓ Genera archivo limpio sin corrupción
- ✓ Estadísticas mostradas son correctas
- ✓ Maneja gracefully archivos con valores nulos
- ✓ Mensaje de error es claro si faltan columnas

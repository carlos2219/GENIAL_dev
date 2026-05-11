# Arquitectura del Pipeline GENIAL

Este documento describe en detalle las fases del pipeline, las decisiones de diseño y el flujo de datos entre módulos.

---

## Visión general

```
[Fase 1] government_search  ──┐
[Fase 3] open_search        ──┼──→ all_raw (List[Dict])
[Fase 2] university_search  ──┘
                               ↓
               deduplicator.deduplicate_urls()      ← dedup pre-extracción
                               ↓
               document_extractor.extract_document()  ← paralela (ThreadPoolExecutor)
                               ↓
               document_classifier.classify()         ← heurística
                               ↓
               deduplicator.deduplicate()             ← dedup post-extracción (hash)
                               ↓
               ai_classifier.classify_batch_with_ai() ← solo ALTA + MEDIA
                               ↓
               matrix_builder.build_matrix()
                               ↓
               excel_exporter.export_to_excel()       → .xlsx
```

---

## Módulos por fase

### Fase 1 — `government_search.py`

Búsqueda en fuentes gubernamentales mexicanas.

**Estrategia dual:**
1. Queries DDG (`GOVERNMENT_QUERIES` de `config.py`) con restricción a dominios `.gob.mx`.
2. Rastreo heurístico de `GOVERNMENT_SEED_URLS` usando `site_crawler.py`.

**Filtros aplicados:**
- `url_filter.is_excluded()` — descarta redes sociales, noticias, blogs.
- `url_filter.looks_normative()` — prioriza URLs con palabras clave normativas.
- `_topic_match()` — requiere mención explícita de IA y al menos un hit de política.

**Salida:** `List[Dict]` con campos `url`, `title`, `snippet`, `source`.

---

### Fase 2 — `university_search.py` + `site_crawler.py`

Búsqueda en universidades mexicanas (fuente: `listado_universidades_altillo.csv`).

**Estrategia por universidad:**
1. Query DDG con operador `site:dominio_universidad "inteligencia artificial"`.
2. Rastreo heurístico del dominio vía `crawl_domain()`:
   - Prueba rutas conocidas: `/normativa`, `/reglamentos`, `/lineamientos`, etc.
   - Extrae enlaces desde el HTML de esas rutas y de la página raíz.
   - Filtra enlaces por palabras clave normativas.

**Concurrencia:** `ThreadPoolExecutor` con semáforo DDG para respetar el rate limit.

**Caché DDG:** Activada por defecto (`DDG_CACHE_ENABLED`). Se persiste en `cache/ddg_search_cache.json` entre ejecuciones.

**Filtro de dominio:** Los resultados DDG se validan contra el dominio de la universidad consultada para evitar resultados cross-site.

**Nota:** Esta fase usa `site:` operator externamente — no usa el buscador interno de cada universidad.

---

### Fase 3 — `open_search.py`

Búsqueda abierta exploratoria sin restricción de dominio inicial.

**Queries:** 10 queries fijas que cubren variaciones de normativa IA en México.

**Filtro de dominio aplicado post-búsqueda:** Solo se retienen URLs de `.gob.mx`, `.edu.mx` o dominios en `GOVERNMENT_PRIORITY_DOMAINS`.

**Orden de ejecución:** Fase 3 corre **antes** de Fase 2 en el pipeline. Razón: Fase 2 puede agotar el rate limit de DDG durante horas; Fase 3 tiene pocas queries y debe aprovechar el estado fresco de la API.

---

### Deduplicación pre-extracción — `deduplicator.py`

Opera sobre la lista `all_raw` combinada de las tres fases.

**Método:** Normalización de URL (`normalize_url()`):
- Unifica `http`/`https`.
- Elimina `www.` del dominio.
- Elimina parámetros de tracking (`utm_*`, `fbclid`, etc.).
- Elimina fragmentos `#...`.
- Elimina trailing slashes.

**Propósito:** Evitar descargar el mismo documento múltiples veces.

---

### Extracción de contenido — `document_extractor.py`

Descarga cada URL y extrae texto limpio.

**Tipos soportados:**
- **HTML:** BeautifulSoup, elimina nav/footer/scripts, limita a `MAX_TEXT_CHARS_HTML`.
- **PDF digital:** pdfplumber (preferido) o PyPDF2/pypdf como fallback.
- **PDF escaneado:** Detectado, marcado con `content_type=pdf_scanned`.

**Configuración:**
- `REQUEST_TIMEOUT = 10s`
- `MAX_PDF_SIZE_MB = 15` — PDFs más grandes se saltan.
- Rotación aleatoria de `User-Agent`.

**Concurrencia:** `ThreadPoolExecutor(max_workers=MAX_WORKERS)`.

---

### Clasificación heurística — `document_classifier.py`

Asigna un score `[0, 1]` y una etiqueta `ALTA / MEDIA / BAJA`.

**Componentes del score:**

| Componente | Peso |
|---|---|
| Keywords de alto valor (reglamento, decreto, lineamiento…) | 0.40 |
| Keywords de medio valor (guía, protocolo, estrategia…) | 0.20 |
| Keywords de IA (inteligencia artificial, machine learning…) | 0.30 |
| Penalización por keywords bajas (noticias, blog, convocatoria…) | −hasta 0.25 |
| Boost PDF | +0.10 |
| Boost dominio `.gob.mx` / `.edu.mx` | +0.10 |

**Regla adicional:** Si `ai_hits == 0`, el score se limita a `HEURISTIC_MEDIUM_THRESHOLD - 0.01` (fuerza etiqueta MEDIA o BAJA).

**Umbrales:**
- `score >= HEURISTIC_HIGH_THRESHOLD (0.50)` → ALTA
- `score >= HEURISTIC_MEDIUM_THRESHOLD (0.24)` → MEDIA
- `score < 0.24` → BAJA

---

### Deduplicación post-extracción — `deduplicator.py`

Opera después de la extracción.

**Método:** Hash SHA-256 de los primeros 2000 caracteres del texto extraído.

**Propósito:** Eliminar documentos distintos que resuelven al mismo contenido (mirrors, redirecciones, versiones HTML y PDF del mismo texto).

---

### Clasificación con IA — `ai_classifier.py`

Usa OpenAI GPT-4o-mini para clasificar documentos con etiqueta ALTA o MEDIA (y opcionalmente BAJA borderline).

**Flujo:**
1. Construye prompt con URL, título y fragmento de texto (`OPENAI_INPUT_CHARS = 3500` chars).
2. Llama a `openai.ChatCompletion` con reintentos (`tenacity`).
3. Parsea respuesta JSON estructurada.
4. Valida que los valores estén en los rangos permitidos por la taxonomía.

**Fallback:** Si la API no está configurada o falla, `ai_classification = None` para todos los documentos. La matriz en modo fallback solo incluye documentos ALTA.

**BAJA borderline:** Con `AI_INCLUDE_BORDERLINE_BAJA = True`, documentos BAJA con `heuristic_score >= AI_BAJA_MIN_SCORE (0.30)` y `url_priority >= AI_BAJA_MIN_URL_PRIORITY (0.60)` también se envían a clasificación IA (máximo `AI_MAX_EXTRA_BAJA = 20`).

**Checkpoint IA:** `output/checkpoints/ai_progress.json` — permite reanudar clasificaciones IA largas sin repetir llamadas a la API.

---

### Construcción de matriz — `matrix_builder.py`

Filtra documentos clasificados y genera las filas del Excel final.

**Criterios de inclusión:**
1. `ai_classification.es_normativa == "si"` (si hay clasificación IA).
2. O `heuristic_label == "ALTA"` en modo heurístico puro.
3. La URL debe pertenecer a `.gob.mx`, `.edu.mx` o dominios en `PRIORITY_UNIVERSITIES`.

**Normalización de valores:**
- `tipo_norma` → mapeado a forma canónica (e.g. `"ley"` → `"Ley"`).
- `dominio` → nunca puede ser `"mixto"` (documentos con ese valor son rechazados).
- `fecha_publicacion` → años fuera de `[2015, año_actual]` se convierten a `"No Indica"`.
- Valores desconocidos → `"No especificado"`.

---

### Exportación a Excel — `excel_exporter.py`

Genera un `.xlsx` con tres hojas:

| Hoja | Contenido |
|---|---|
| Matriz Normativa | Filas de la matriz (documentos confirmados) |
| Resumen | Estadísticas por tipo de norma, dominio, ámbito |
| Log Completo | Todos los documentos procesados con sus scores |

---

## Checkpoints

| Archivo | Fase guardada |
|---|---|
| `output/checkpoints/phase1_gov.json` | Resultados Fase 1 |
| `output/checkpoints/phase3_open.json` | Resultados Fase 3 |
| `output/checkpoints/phase2_uni.json` | Resultados Fase 2 |
| `output/checkpoints/search_complete.json` | Todos los resultados de búsqueda |
| `output/checkpoints/extracted.json` | Documentos con texto extraído |
| `output/checkpoints/classified_heuristic.json` | Documentos clasificados heurísticamente |
| `output/checkpoints/ai_progress.json` | Progreso de clasificación IA |

Con `--resume`, el pipeline detecta el checkpoint más avanzado y salta las fases ya completadas.

---

## Decisiones de diseño

### ¿Por qué dos etapas de deduplicación?

- **Pre-extracción (URL):** Evita descargar el mismo recurso múltiples veces desde fases distintas.
- **Post-extracción (hash):** Elimina mirrors o páginas de redirección que llegaron con URLs distintas pero contienen el mismo texto.

Consolidar ambas en una sola perdería precisión en uno de los dos casos.

### ¿Por qué Fase 3 antes de Fase 2?

Fase 2 realiza una query DDG por cada universidad (potencialmente cientos). DuckDuckGo impone rate limits agresivos y puede bloquear el cliente durante horas tras una ráfaga grande. Ejecutar Fase 3 (solo ~10 queries) antes garantiza que esas búsquedas abiertas de alto valor no queden bloqueadas.

### ¿Por qué `gpt-4o-mini` y no GPT-4o?

Relación costo/calidad favorable para este caso de uso. Los prompts son cortos (< 600 tokens de salida) y las decisiones de clasificación no requieren el razonamiento extendido de modelos mayores. El modelo puede cambiarse en `config.OPENAI_MODEL`.

### ¿Por qué no se usa el buscador interno de cada universidad?

El buscador interno de cada universidad tiene interfaces distintas, puede requerir JavaScript o formularios POST, y no es programáticamente estable. El enfoque con `site:` operator + rastreo heurístico de rutas conocidas cubre la mayoría de los casos con menor complejidad y mayor fiabilidad.

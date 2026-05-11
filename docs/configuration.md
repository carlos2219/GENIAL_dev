# Referencia de Configuración — `config.py`

Todos los parámetros del sistema están centralizados en `config.py`. Este documento describe cada uno con su valor por defecto, tipo y efecto.

---

## Rutas

| Variable | Valor por defecto | Descripción |
|---|---|---|
| `BASE_DIR` | Directorio de `config.py` | Raíz del proyecto |
| `CSV_PATH` | `listado_universidades_altillo.csv` | Lista de universidades mexicanas |
| `OUTPUT_DIR` | `output/` | Directorio de salidas (Excel, JSON, checkpoints) |
| `CACHE_DIR` | `cache/` | Directorio de caché DDG |
| `LOG_DIR` | `logs/` | Directorio de logs |
| `OUTPUT_EXCEL` | `output/normativa_ia_mexico_YYYYMMDD_HHMM.xlsx` | Ruta del Excel generado |
| `KNOWN_MATRIX_EXCEL` | `Matriz_Normativa_IA_Educacion_LATAM.xlsx` | Excel existente — sus URLs se excluyen del reprocesamiento |

---

## Investigador

| Variable | Valor por defecto | Descripción |
|---|---|---|
| `RESEARCHER_NAME` | `"Carlos Auquilla"` (env: `RESEARCHER_NAME`) | Nombre en columna A de la matriz |
| `COUNTRY` | `"México"` | País del levantamiento — no cambiar sin revisión completa del pipeline |
| `NO_INDICA_LABEL` | `"No Indica"` | Texto para campos de fecha/valor desconocido |
| `SIN_NORMATIVA_LABEL` | `"Sin normativa específica detectada"` | Texto para documentos sin normativa |

---

## OpenAI

| Variable | Valor por defecto | Descripción |
|---|---|---|
| `OPENAI_API_KEY` | `""` (env: `OPENAI_API_KEY`) | Clave de API. **Nunca hardcodear.** |
| `OPENAI_MODEL` | `"gpt-4o-mini"` (env: `OPENAI_MODEL`) | Modelo de clasificación |
| `OPENAI_MAX_TOKENS` | `600` | Tokens máximos en la respuesta IA |
| `OPENAI_INPUT_CHARS` | `3500` | Caracteres del fragmento de texto enviado al modelo |

### Clasificación BAJA borderline

| Variable | Valor | Descripción |
|---|---|---|
| `AI_INCLUDE_BORDERLINE_BAJA` | `True` | Enviar a IA documentos BAJA con señal suficiente |
| `AI_BAJA_MIN_SCORE` | `0.30` | Score heurístico mínimo para enviar un BAJA a IA |
| `AI_BAJA_MIN_URL_PRIORITY` | `0.60` | Score URL mínimo para enviar un BAJA a IA |
| `AI_MAX_EXTRA_BAJA` | `20` | Máximo de documentos BAJA borderline enviados a IA por ejecución |

---

## Búsqueda

| Variable | Valor por defecto | Descripción |
|---|---|---|
| `MAX_RESULTS_PER_QUERY` | `10` | Resultados por query DuckDuckGo |
| `MAX_URLS_PER_UNIVERSITY` | `6` | URLs máximas aceptadas por universidad |
| `MAX_UNIVERSITIES` | `None` (todas) | Límite de universidades — `None` = run completo |
| `SEARCH_DELAY_SECONDS` | `0.5` | Pausa entre búsquedas DDG (evita bloqueos) |
| `MAX_WORKERS` | `16` | Hilos para extracción paralela |
| `DDG_CACHE_ENABLED` | `True` | Activa caché de búsquedas DDG entre ejecuciones |
| `INTER_PHASE_PAUSE_SECONDS` | `0` | Pausa entre fases (reservado) |
| `DEFINITIVE_RUN_MAX_UNIVERSITIES` | `None` | Límite seguro para runs de producción |

### Crawling de universidades no prioritarias

| Variable | Valor | Descripción |
|---|---|---|
| `CRAWL_NON_PRIORITY` | `True` | Hacer crawl también en universidades no prioritarias |
| `CRAWL_NON_PRIORITY_MAX_DOCS` | `2` | URLs máximas para universidades no prioritarias |
| `CRAWL_NON_PRIORITY_MAX_SECONDS` | `8` | Timeout de crawl para universidades no prioritarias |

### Filtro pre-extracción

| Variable | Valor | Descripción |
|---|---|---|
| `PRE_EXTRACTION_FILTER_ENABLED` | `True` | Descarta documentos sin señal de IA/normativa en snippet/URL antes de extraer |

---

## Filtros temáticos

| Variable | Valor | Descripción |
|---|---|---|
| `STRICT_TOPIC_FILTER` | `True` | Activa filtro temático en fases 1 y 3 |
| `TOPIC_MUST_INCLUDE_AI` | `True` | Requiere al menos un hit de keyword IA |
| `TOPIC_MIN_POLICY_HITS` | `1` | Mínimo de hits de keywords de política para pasar el filtro |

---

## HTTP

| Variable | Valor | Descripción |
|---|---|---|
| `REQUEST_TIMEOUT` | `10` | Timeout de requests HTTP en segundos |
| `MAX_PDF_SIZE_MB` | `15` | PDFs más grandes se saltan |
| `MAX_TEXT_CHARS_HTML` | `12,000` | Caracteres máximos de texto extraído de HTML |
| `MAX_TEXT_CHARS_PDF` | `10,000` | Caracteres máximos de texto extraído de PDF |
| `USER_AGENTS` | Lista de 3 | User-Agents rotativos para requests |

---

## Clasificación heurística

### Umbrales de score

| Variable | Valor | Descripción |
|---|---|---|
| `HEURISTIC_HIGH_THRESHOLD` | `0.50` | Score mínimo para etiqueta ALTA |
| `HEURISTIC_MEDIUM_THRESHOLD` | `0.24` | Score mínimo para etiqueta MEDIA |

### Listas de keywords

| Lista | Peso en score | Palabras clave |
|---|---|---|
| `HIGH_SCORE_KEYWORDS` | +0.40 | reglamento, decreto, lineamiento, estatuto, resolución rectoral, estrategia nacional… |
| `MEDIUM_SCORE_KEYWORDS` | +0.20 | guía, manual, protocolo, política, criterios, código de ética… |
| `LOW_SCORE_KEYWORDS` | −hasta 0.25 | noticia, blog, convocatoria, evento, taller, podcast… |
| `AI_KEYWORDS` | +0.30 | inteligencia artificial, machine learning, gpt-, modelo de lenguaje… |
| `EDU_KEYWORDS` | referencial | universidad, docente, estudiante, plan de estudios… |
| `POLICY_KEYWORDS` | referencial | normativa, lineamiento, reglamento, decreto, política… |

---

## Filtro de URLs

### Dominios excluidos (`EXCLUDED_DOMAINS`)

Incluye: redes sociales, medios de comunicación nacionales, blogs, plataformas genéricas, journals académicos (scielo, redalyc), y similares.

### Keywords de URL prioritaria (`PRIORITY_URL_KEYWORDS`)

URLs que contienen estas palabras reciben boost de score: `normativa`, `reglamento`, `lineamiento`, `politica`, `acuerdo`, `resolucion`, `guia`, `marco-juridico`, `estatuto`, `decreto`, `legislacion`, `disposicion`, `normatividad`.

---

## Fuentes gubernamentales

### `GOVERNMENT_QUERIES`

17 queries predefinidas que cubren: ley, decreto, guía ética, estrategia nacional, lineamientos SEP, CONAHCYT, DOF, ENIA, etc.

### `GOVERNMENT_SEED_URLS`

URLs semilla para rastreo heurístico: `gob.mx/agenda-digital`, `sep.gob.mx`, `conahcyt.mx`, `dof.gob.mx`, `inai.org.mx`, `ift.org.mx`, `economia.gob.mx`, `presidencia.gob.mx`, normateca SEP, CEIDE UNAM.

### `GOVERNMENT_PRIORITY_DOMAINS`

Dominios gubernamentales priorizados: `.gob.mx`, `dof.gob.mx`, `sep.gob.mx`, `conahcyt.mx`, `conacyt.gob.mx`, `ift.org.mx`.

---

## Universidades prioritarias (`PRIORITY_UNIVERSITIES`)

Lista de dominios de universidades mexicanas de alta relevancia que reciben mayor profundidad de búsqueda. Incluye UNAM, IPN, ITESM, UAM, UABC, UG, BUAP, UAdeC, UDG, IBERO, UP, ANÁHUAC, ITAM, CIDE y otras.

---

## Variables de entorno

| Variable | Descripción |
|---|---|
| `OPENAI_API_KEY` | Clave de API OpenAI. Requerida para clasificación IA. |
| `OPENAI_MODEL` | Modelo OpenAI a usar (default: `gpt-4o-mini`). |
| `RESEARCHER_NAME` | Nombre del investigador (default: `Carlos Auquilla`). |

Configura estas variables antes de ejecutar el pipeline. Nunca las pongas directamente en `config.py`.

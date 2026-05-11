# GENIAL — Sistema de Levantamiento Normativo de IA en Educación (México)

**GENIAL** es un pipeline automatizado de búsqueda, extracción y clasificación de normativa sobre Inteligencia Artificial en el sistema educativo mexicano. Produce una matriz Excel estructurada lista para análisis de investigación.

> Proyecto asignado al investigador: **Carlos Auquilla**  
> Alcance exclusivo: **México** (fuentes `.gob.mx` y `.edu.mx`)

---

## Índice

- [Descripción general](#descripción-general)
- [Estructura de archivos](#estructura-de-archivos)
- [Instalación](#instalación)
- [Configuración](#configuración)
- [Uso](#uso)
- [Pipeline](#pipeline)
- [Salidas](#salidas)
- [Documentación adicional](#documentación-adicional)

---

## Descripción general

El sistema realiza tres tipos de búsqueda (gobierno, universidades, abierta), extrae el contenido de los documentos encontrados, los clasifica con heurística y opcionalmente con GPT-4o-mini, y exporta los resultados a un archivo Excel con la matriz normativa final.

Solo se incluyen fuentes oficiales mexicanas. Documentos que no mencionen explícitamente inteligencia artificial son excluidos.

---

## Estructura de archivos

```
GENIAL_dev/
│
├── main.py                          # Orquestador del pipeline completo
├── config.py                        # Toda la configuración (umbrales, queries, dominios)
│
├── government_search.py             # Fase 1: búsqueda en portales gubernamentales
├── university_search.py             # Fase 2: búsqueda por dominio en universidades
├── open_search.py                   # Fase 3: búsqueda abierta exploratoria
├── site_crawler.py                  # Rastreo heurístico de sitios web
│
├── document_extractor.py            # Extracción de texto desde HTML y PDF
├── document_classifier.py           # Clasificación heurística (score + etiqueta)
├── ai_classifier.py                 # Clasificación con OpenAI GPT-4o-mini
├── deduplicator.py                  # Deduplicación por URL y por contenido
├── url_filter.py                    # Filtrado y puntuación de URLs
│
├── matrix_builder.py                # Construcción de filas de la matriz final
├── excel_exporter.py                # Exportación a Excel (.xlsx)
│
├── listado_universidades_altillo.csv # Lista de universidades mexicanas (fuente: Altillo)
├── requirements.txt                 # Dependencias Python
├── PROPOSITO_PROYECTO_MANUAL.md     # Resumen del manual del investigador
│
├── docs/
│   ├── architecture.md              # Arquitectura detallada del pipeline
│   ├── configuration.md             # Referencia completa de config.py
│   └── taxonomy.md                  # Taxonomía válida para la matriz
│
├── output/
│   ├── normativa_ia_mexico_*.xlsx   # Excel generado por cada ejecución
│   ├── documentos_procesados.json   # Respaldo JSON de todos los documentos
│   └── checkpoints/                 # Puntos de reanudación por fase
│
├── cache/
│   └── ddg_search_cache.json        # Caché de búsquedas DuckDuckGo
│
└── logs/
    └── pipeline_*.log               # Log de cada ejecución
```

---

## Instalación

**Requisitos:** Python 3.10+

```bash
# 1. Crear entorno virtual
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # Linux/macOS

# 2. Instalar dependencias
pip install -r requirements.txt
```

**Variable de entorno para clasificación con IA (opcional):**

```bash
# Windows (PowerShell)
$env:OPENAI_API_KEY = "sk-..."

# Linux/macOS
export OPENAI_API_KEY="sk-..."
```

Sin `OPENAI_API_KEY`, el pipeline funciona en modo heurístico (solo documentos ALTA entran a la matriz).

---

## Configuración

Los parámetros principales están en `config.py`. Ver [docs/configuration.md](docs/configuration.md) para la referencia completa.

| Parámetro | Valor por defecto | Descripción |
|---|---|---|
| `OPENAI_MODEL` | `gpt-4o-mini` | Modelo de clasificación IA |
| `MAX_RESULTS_PER_QUERY` | `10` | Resultados por búsqueda DDG |
| `MAX_UNIVERSITIES` | `None` (todas) | Límite de universidades a procesar |
| `MAX_WORKERS` | `16` | Hilos para extracción paralela |
| `HEURISTIC_HIGH_THRESHOLD` | `0.50` | Score mínimo para etiqueta ALTA |
| `HEURISTIC_MEDIUM_THRESHOLD` | `0.24` | Score mínimo para etiqueta MEDIA |
| `DDG_CACHE_ENABLED` | `True` | Activa caché entre ejecuciones |

---

## Uso

### Ejecución completa

```bash
python main.py
```

### Opciones de CLI

```
--skip-government      Omitir Fase 1 (búsqueda gubernamental)
--skip-universities    Omitir Fase 2 (búsqueda en universidades)
--skip-open            Omitir Fase 3 (búsqueda abierta)
--skip-ai              Usar solo clasificación heurística (sin API)
--max-universities N   Procesar solo las primeras N universidades
--all-universities     Procesar todas las universidades del CSV
--resume               Reanudar desde el último checkpoint disponible
--output RUTA          Ruta personalizada para el Excel de salida
--researcher NOMBRE    Nombre del investigador (sobrescribe config.py)
--verbose              Logging detallado (nivel DEBUG)
```

### Ejemplos

```bash
# Solo gobierno + búsqueda abierta, sin IA
python main.py --skip-universities --skip-ai

# Prueba rápida con 5 universidades
python main.py --max-universities 5

# Reanudar una ejecución interrumpida
python main.py --resume

# Ejecución completa de producción con todas las universidades
python main.py --all-universities --output output/matriz_final.xlsx
```

---

## Pipeline

El pipeline ejecuta 10 fases en secuencia. Ver [docs/architecture.md](docs/architecture.md) para la descripción detallada.

```
Fase 1  →  Búsqueda gubernamental (DDG + rastreo de URLs semilla)
Fase 3* →  Búsqueda abierta (ejecutada antes de Fase 2 para aprovechar DDG fresco)
Fase 2  →  Búsqueda universitaria (site: operator + rastreo heurístico)
         ↓
       Deduplicación pre-extracción (por URL)
         ↓
       Extracción de contenido (HTML + PDF, paralela)
         ↓
       Clasificación heurística (score + etiqueta ALTA/MEDIA/BAJA)
         ↓
       Deduplicación post-extracción (por hash de contenido)
         ↓
       Clasificación IA (solo ALTA y MEDIA, requiere API key)
         ↓
       Construcción de matriz
         ↓
       Exportación a Excel (.xlsx)
```

*Fase 3 se ejecuta antes de Fase 2 porque Fase 2 agota el rate limit de DDG durante horas.

### Checkpoints

El sistema guarda checkpoints en `output/checkpoints/` al final de cada fase costosa. Con `--resume`, detecta el checkpoint más avanzado disponible y evita repetir trabajo.

---

## Salidas

### Excel (hoja principal: "Matriz Normativa")

| Columna | Descripción |
|---|---|
| Investigador | Nombre del investigador asignado |
| País | México |
| Título de la Norma | Título oficial del documento |
| Tipo de norma | Ley, Decreto, Reglamento, Guía ética, etc. |
| Estado | Vigente / En Proyecto / Derogada |
| Organismo Emisor/Universidad | Institución que emite la norma |
| Dominio | Pedagógico / Administrativo / Ética / etc. |
| Vínculo con Educación | Directo / Indirecto |
| Dedicación del Texto | Articulado completo / Sección / Mención breve |
| Fecha de Publicación | DD/MM/AAAA o "No Indica" |
| URL Oficial | Enlace al documento fuente |
| Observaciones | Notas adicionales del clasificador |
| Ámbito | Nacional / Institucional |

Hojas adicionales: **Resumen** (estadísticas) y **Log Completo** (todos los documentos procesados).

### JSON de respaldo

`output/documentos_procesados.json` contiene todos los documentos con sus scores heurísticos, clasificación IA y metadatos de extracción.

---

## Documentación adicional

| Documento | Contenido |
|---|---|
| [docs/architecture.md](docs/architecture.md) | Arquitectura de fases, decisiones de diseño, flujo de datos |
| [docs/configuration.md](docs/configuration.md) | Referencia completa de todos los parámetros de `config.py` |
| [docs/taxonomy.md](docs/taxonomy.md) | Valores válidos para cada campo de la matriz |
| [PROPOSITO_PROYECTO_MANUAL.md](PROPOSITO_PROYECTO_MANUAL.md) | Resumen del manual del investigador y reglas del proyecto |

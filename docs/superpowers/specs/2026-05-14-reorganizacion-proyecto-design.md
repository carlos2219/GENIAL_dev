# GENIAL — Reorganización y Mejoras del Proyecto

**Fecha:** 2026-05-14  
**Aprobado por:** Carlos Auquilla

---

## Objetivo

Reorganizar la estructura del proyecto GENIAL aplicando una arquitectura Python estándar (`src/pipeline/`), limpiar archivos temporales de la raíz, integrar `run_phase3.py` en `main.py`, completar `.env.example`, agregar tests unitarios, y añadir soporte explícito para ejecución en GCP Compute Engine.

---

## Nueva estructura de directorios

```
GENIAL_dev/
├── main.py                          # Orquestador (actualizado)
├── config.py                        # Configuración global (rutas actualizadas)
│
├── src/
│   └── pipeline/
│       ├── __init__.py
│       ├── government_search.py
│       ├── university_search.py
│       ├── open_search.py
│       ├── site_crawler.py
│       ├── document_extractor.py
│       ├── document_classifier.py
│       ├── ai_classifier.py
│       ├── deduplicator.py
│       ├── url_filter.py
│       ├── matrix_builder.py
│       ├── excel_exporter.py
│       └── search_backends.py
│
├── data/
│   ├── listado_universidades_altillo.csv
│   └── Matriz_Normativa_IA_Educacion_LATAM.xlsx
│
├── reference/
│   ├── Manual-Investigadores.pdf
│   ├── Distribucioìn final.pdf
│   └── observaciones.pdf
│
├── tests/
│   ├── __init__.py
│   ├── test_document_classifier.py
│   └── test_url_filter.py
│
├── scripts/
│   └── run_vm.sh
│
├── docs/
│   ├── architecture.md
│   ├── configuration.md
│   └── taxonomy.md
│
├── reportes/
├── output/
├── cache/
├── logs/
├── .env.example
├── requirements.txt
├── README.md
└── PROPOSITO_PROYECTO_MANUAL.md
```

---

## Cambios por componente

### 1. Movimiento de archivos

| Archivo actual (raíz) | Destino |
|---|---|
| `government_search.py` | `src/pipeline/` |
| `university_search.py` | `src/pipeline/` |
| `open_search.py` | `src/pipeline/` |
| `site_crawler.py` | `src/pipeline/` |
| `document_extractor.py` | `src/pipeline/` |
| `document_classifier.py` | `src/pipeline/` |
| `ai_classifier.py` | `src/pipeline/` |
| `deduplicator.py` | `src/pipeline/` |
| `url_filter.py` | `src/pipeline/` |
| `matrix_builder.py` | `src/pipeline/` |
| `excel_exporter.py` | `src/pipeline/` |
| `search_backends.py` | `src/pipeline/` |
| `listado_universidades_altillo.csv` | `data/` |
| `Matriz_Normativa_IA_Educacion_LATAM.xlsx` | `data/` |
| `Manual-Investigadores.pdf` | `reference/` |
| `Distribucioìn final.pdf` | `reference/` |
| `observaciones.pdf` | `reference/` |
| `documentos_pdfs.zip` | `reference/` |
| `run_phase3.py` | eliminado (integrado en `main.py`) |
| `copia_segundo_webscrapper.xlsx` | eliminado (temporal sin uso) |

`main.py` y `config.py` permanecen en la raíz.

---

### 2. Imports en `src/pipeline/`

Todos los módulos dentro del paquete usan imports relativos entre sí:

```python
# Antes (en university_search.py):
import config
from url_filter import filter_and_rank, is_excluded
from site_crawler import crawl_domain
from search_backends import multi_search as _multi_search

# Después:
import config
from .url_filter import filter_and_rank, is_excluded
from .site_crawler import crawl_domain
from .search_backends import multi_search as _multi_search
```

`config.py` permanece en la raíz y se importa directamente (sin prefijo de paquete) desde todos los módulos.

---

### 3. `config.py` — rutas actualizadas

```python
BASE_DIR   = Path(__file__).parent
CSV_PATH   = BASE_DIR / "data" / "listado_universidades_altillo.csv"
KNOWN_MATRIX_EXCEL = BASE_DIR / "data" / "Matriz_Normativa_IA_Educacion_LATAM.xlsx"
```

---

### 4. `main.py` — imports y flag `--phase3-only`

```python
# Imports del paquete
from src.pipeline import (
    government_search, university_search, open_search,
    document_extractor, document_classifier, deduplicator,
    ai_classifier, matrix_builder, excel_exporter,
)

# Nuevo flag CLI
--phase3-only   # setea skip_government=True, skip_universities=True automáticamente
```

---

### 5. `.env.example` completado

```bash
# OpenAI
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini

# Investigador
RESEARCHER_NAME=Carlos Auquilla

# Backends de búsqueda
GOOGLE_CSE_API_KEY=
GOOGLE_CSE_ID=
BRAVE_API_KEY=
GOOGLE_AS_PRIMARY=true
SEARCH_DELAY_SECONDS=0.5

# GCP Secret Manager (alternativa a .env en producción):
# export OPENAI_API_KEY=$(gcloud secrets versions access latest --secret="openai-api-key")
```

---

### 6. Tests unitarios

**`tests/test_document_classifier.py`**
- Doc con "reglamento" + "inteligencia artificial" → label ALTA
- Doc con "guía" + "inteligencia artificial" → label MEDIA  
- Doc con "noticia" sin AI keywords → label BAJA
- Doc sin hits de IA → score forzado por debajo de HEURISTIC_MEDIUM_THRESHOLD

**`tests/test_url_filter.py`**
- `facebook.com/...` → excluida por `is_excluded()`
- `unam.mx/reglamento-ia.pdf` → no excluida, normativa
- Normalización de URL: http/https, www., trailing slash

Ejecutar con: `pytest tests/ -v`

---

### 7. `scripts/run_vm.sh` — GCP Compute Engine

```bash
#!/bin/bash
# Lanza el pipeline en background, guarda PID, muestra log en vivo
nohup python main.py "$@" >> logs/nohup.out 2>&1 &
echo $! > logs/pipeline.pid
echo "Pipeline iniciado (PID $(cat logs/pipeline.pid))"
echo "Ver log: tail -f logs/nohup.out"
```

---

## Criterios de éxito

1. `python main.py --help` funciona desde la raíz sin errores de import
2. `python main.py --phase3-only --skip-ai` completa sin errores
3. `pytest tests/ -v` pasa todos los tests
4. La raíz solo contiene: `main.py`, `config.py`, `.env.example`, `requirements.txt`, `README.md`, `PROPOSITO_PROYECTO_MANUAL.md`, `LICENSE`, y las carpetas de organización

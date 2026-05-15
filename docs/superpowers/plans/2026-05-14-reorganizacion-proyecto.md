# GENIAL — Reorganización del Proyecto

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Migrar los 13 módulos Python a `src/pipeline/`, reorganizar archivos de datos y referencia, integrar `run_phase3.py` en `main.py` como `--phase3-only`, completar `.env.example`, agregar tests unitarios para los clasificadores, y añadir soporte explícito para GCP Compute Engine.

**Architecture:** Los módulos del pipeline viven en `src/pipeline/` como un paquete Python con imports relativos entre sí. `config.py` y `main.py` permanecen en la raíz. Las pruebas viven en `tests/` y se ejecutan con `pytest` sin red ni APIs externas.

**Tech Stack:** Python 3.10+, pytest, openpyxl, openai, requests, beautifulsoup4, duckduckgo-search

---

## Mapa de archivos

| Acción | Ruta |
|---|---|
| Crear | `src/__init__.py` |
| Crear | `src/pipeline/__init__.py` |
| Mover + editar | `src/pipeline/government_search.py` |
| Mover + editar | `src/pipeline/university_search.py` |
| Mover + editar | `src/pipeline/open_search.py` |
| Mover + editar | `src/pipeline/site_crawler.py` |
| Mover + editar | `src/pipeline/excel_exporter.py` |
| Mover (sin editar) | `src/pipeline/document_extractor.py` |
| Mover (sin editar) | `src/pipeline/document_classifier.py` |
| Mover (sin editar) | `src/pipeline/ai_classifier.py` |
| Mover (sin editar) | `src/pipeline/deduplicator.py` |
| Mover (sin editar) | `src/pipeline/url_filter.py` |
| Mover (sin editar) | `src/pipeline/matrix_builder.py` |
| Mover (sin editar) | `src/pipeline/search_backends.py` |
| Editar | `config.py` |
| Editar | `main.py` |
| Editar | `.env.example` |
| Crear | `tests/__init__.py` |
| Crear | `tests/test_document_classifier.py` |
| Crear | `tests/test_url_filter.py` |
| Crear | `scripts/run_vm.sh` |
| Mover | `data/listado_universidades_altillo.csv` |
| Mover | `data/Matriz_Normativa_IA_Educacion_LATAM.xlsx` |
| Mover | `reference/Manual-Investigadores.pdf` |
| Mover | `reference/Distribucioìn final.pdf` |
| Mover | `reference/observaciones.pdf` |
| Mover | `reference/documentos_pdfs.zip` |
| Eliminar | `run_phase3.py` |
| Eliminar | `copia_segundo_webscrapper.xlsx` |

---

## Task 1: Crear estructura de directorios e `__init__.py`

**Files:**
- Create: `src/__init__.py`
- Create: `src/pipeline/__init__.py`
- Create: `tests/__init__.py`
- Create: `data/` (directorio)
- Create: `reference/` (directorio)
- Create: `scripts/` (directorio)

- [ ] **Step 1: Crear directorios**

```bash
mkdir -p src/pipeline data reference scripts tests
```

- [ ] **Step 2: Crear archivos `__init__.py` vacíos**

Crear `src/__init__.py` con contenido vacío.

Crear `src/pipeline/__init__.py` con contenido vacío.

Crear `tests/__init__.py` con contenido vacío.

- [ ] **Step 3: Verificar estructura**

```bash
ls src/pipeline/ tests/ data/ reference/ scripts/
```

Expected: directorios existen, `src/pipeline/` y `tests/` contienen `__init__.py`.

- [ ] **Step 4: Commit**

```bash
git add src/ tests/__init__.py data/ reference/ scripts/
git commit -m "chore: create src/pipeline, data, reference, scripts, tests directory structure"
```

---

## Task 2: Mover módulos sin imports locales a `src/pipeline/`

Los siguientes módulos solo importan `config` (que permanece en la raíz y siempre estará en `sys.path` al correr desde la raíz). No requieren cambios en sus imports.

**Módulos a mover:** `document_extractor.py`, `document_classifier.py`, `ai_classifier.py`, `deduplicator.py`, `url_filter.py`, `matrix_builder.py`, `search_backends.py`

**Files:**
- Create: `src/pipeline/document_extractor.py`
- Create: `src/pipeline/document_classifier.py`
- Create: `src/pipeline/ai_classifier.py`
- Create: `src/pipeline/deduplicator.py`
- Create: `src/pipeline/url_filter.py`
- Create: `src/pipeline/matrix_builder.py`
- Create: `src/pipeline/search_backends.py`

- [ ] **Step 1: Copiar los siete módulos a `src/pipeline/`**

```bash
cp document_extractor.py src/pipeline/document_extractor.py
cp document_classifier.py src/pipeline/document_classifier.py
cp ai_classifier.py src/pipeline/ai_classifier.py
cp deduplicator.py src/pipeline/deduplicator.py
cp url_filter.py src/pipeline/url_filter.py
cp matrix_builder.py src/pipeline/matrix_builder.py
cp search_backends.py src/pipeline/search_backends.py
```

- [ ] **Step 2: Verificar que los imports funcionan desde la raíz**

```bash
python -c "from src.pipeline import document_classifier, url_filter, matrix_builder, search_backends, deduplicator, ai_classifier, document_extractor; print('OK')"
```

Expected output: `OK`

- [ ] **Step 3: Commit**

```bash
git add src/pipeline/document_extractor.py src/pipeline/document_classifier.py src/pipeline/ai_classifier.py src/pipeline/deduplicator.py src/pipeline/url_filter.py src/pipeline/matrix_builder.py src/pipeline/search_backends.py
git commit -m "refactor: copy 7 pipeline modules (no local deps) to src/pipeline/"
```

---

## Task 3: Mover `site_crawler.py` con import relativo

`site_crawler.py` importa `url_filter` localmente: `from url_filter import is_excluded, looks_normative, is_pdf_url`. Debe cambiar a import relativo.

**Files:**
- Create: `src/pipeline/site_crawler.py`

- [ ] **Step 1: Copiar `site_crawler.py` a `src/pipeline/`**

```bash
cp site_crawler.py src/pipeline/site_crawler.py
```

- [ ] **Step 2: Editar el import local en `src/pipeline/site_crawler.py`**

Buscar la línea:
```python
from url_filter import is_excluded, looks_normative, is_pdf_url
```

Reemplazar con:
```python
from .url_filter import is_excluded, looks_normative, is_pdf_url
```

- [ ] **Step 3: Verificar import**

```bash
python -c "from src.pipeline import site_crawler; print('OK')"
```

Expected output: `OK`

- [ ] **Step 4: Commit**

```bash
git add src/pipeline/site_crawler.py
git commit -m "refactor: copy site_crawler to src/pipeline/ with relative import"
```

---

## Task 4: Mover `government_search.py` con imports relativos

`government_search.py` tiene dos imports locales que deben cambiar a relativos:
- `from url_filter import filter_and_rank, is_excluded, looks_normative`
- `from search_backends import multi_search`

**Files:**
- Create: `src/pipeline/government_search.py`

- [ ] **Step 1: Copiar `government_search.py` a `src/pipeline/`**

```bash
cp government_search.py src/pipeline/government_search.py
```

- [ ] **Step 2: Editar imports locales en `src/pipeline/government_search.py`**

Buscar:
```python
from url_filter import filter_and_rank, is_excluded, looks_normative
from search_backends import multi_search
```

Reemplazar con:
```python
from .url_filter import filter_and_rank, is_excluded, looks_normative
from .search_backends import multi_search
```

- [ ] **Step 3: Verificar import**

```bash
python -c "from src.pipeline import government_search; print('OK')"
```

Expected output: `OK`

- [ ] **Step 4: Commit**

```bash
git add src/pipeline/government_search.py
git commit -m "refactor: copy government_search to src/pipeline/ with relative imports"
```

---

## Task 5: Mover `open_search.py` con imports relativos

`open_search.py` tiene dos imports locales:
- `from url_filter import filter_and_rank, is_excluded`
- `from search_backends import multi_search`

**Files:**
- Create: `src/pipeline/open_search.py`

- [ ] **Step 1: Copiar `open_search.py` a `src/pipeline/`**

```bash
cp open_search.py src/pipeline/open_search.py
```

- [ ] **Step 2: Editar imports locales en `src/pipeline/open_search.py`**

Buscar:
```python
from url_filter import filter_and_rank, is_excluded
from search_backends import multi_search
```

Reemplazar con:
```python
from .url_filter import filter_and_rank, is_excluded
from .search_backends import multi_search
```

- [ ] **Step 3: Verificar import**

```bash
python -c "from src.pipeline import open_search; print('OK')"
```

Expected output: `OK`

- [ ] **Step 4: Commit**

```bash
git add src/pipeline/open_search.py
git commit -m "refactor: copy open_search to src/pipeline/ with relative imports"
```

---

## Task 6: Mover `university_search.py` con imports relativos

`university_search.py` tiene tres imports locales:
- `from url_filter import filter_and_rank, is_excluded`
- `from site_crawler import crawl_domain`
- `from search_backends import multi_search as _multi_search`

**Files:**
- Create: `src/pipeline/university_search.py`

- [ ] **Step 1: Copiar `university_search.py` a `src/pipeline/`**

```bash
cp university_search.py src/pipeline/university_search.py
```

- [ ] **Step 2: Editar imports locales en `src/pipeline/university_search.py`**

Buscar:
```python
from url_filter import filter_and_rank, is_excluded
from site_crawler import crawl_domain
from search_backends import multi_search as _multi_search
```

Reemplazar con:
```python
from .url_filter import filter_and_rank, is_excluded
from .site_crawler import crawl_domain
from .search_backends import multi_search as _multi_search
```

- [ ] **Step 3: Verificar import**

```bash
python -c "from src.pipeline import university_search; print('OK')"
```

Expected output: `OK`

- [ ] **Step 4: Commit**

```bash
git add src/pipeline/university_search.py
git commit -m "refactor: copy university_search to src/pipeline/ with relative imports"
```

---

## Task 7: Mover `excel_exporter.py` con import relativo

`excel_exporter.py` tiene un import local:
- `from matrix_builder import MATRIX_COLUMNS`

**Files:**
- Create: `src/pipeline/excel_exporter.py`

- [ ] **Step 1: Copiar `excel_exporter.py` a `src/pipeline/`**

```bash
cp excel_exporter.py src/pipeline/excel_exporter.py
```

- [ ] **Step 2: Editar import local en `src/pipeline/excel_exporter.py`**

Buscar:
```python
from matrix_builder import MATRIX_COLUMNS
```

Reemplazar con:
```python
from .matrix_builder import MATRIX_COLUMNS
```

- [ ] **Step 3: Verificar import**

```bash
python -c "from src.pipeline import excel_exporter; print('OK')"
```

Expected output: `OK`

- [ ] **Step 4: Commit**

```bash
git add src/pipeline/excel_exporter.py
git commit -m "refactor: copy excel_exporter to src/pipeline/ with relative import"
```

---

## Task 8: Actualizar `config.py` con nuevas rutas

Las rutas `CSV_PATH` y `KNOWN_MATRIX_EXCEL` deben apuntar a `data/` en lugar de la raíz.

**Files:**
- Modify: `config.py`

- [ ] **Step 1: Editar `config.py`**

Buscar:
```python
CSV_PATH   = BASE_DIR / "listado_universidades_altillo.csv"
```

Reemplazar con:
```python
CSV_PATH   = BASE_DIR / "data" / "listado_universidades_altillo.csv"
```

Buscar:
```python
KNOWN_MATRIX_EXCEL = BASE_DIR / "Matriz_Normativa_IA_Educacion_LATAM.xlsx"
```

Reemplazar con:
```python
KNOWN_MATRIX_EXCEL = BASE_DIR / "data" / "Matriz_Normativa_IA_Educacion_LATAM.xlsx"
```

- [ ] **Step 2: Verificar config**

```bash
python -c "import config; print(config.CSV_PATH); print(config.KNOWN_MATRIX_EXCEL)"
```

Expected output (paths relativas a la raíz del proyecto):
```
.../data/listado_universidades_altillo.csv
.../data/Matriz_Normativa_IA_Educacion_LATAM.xlsx
```

- [ ] **Step 3: Commit**

```bash
git add config.py
git commit -m "refactor: update config.py paths to data/ subdirectory"
```

---

## Task 9: Mover archivos de datos a `data/`

**Files:**
- Move: `listado_universidades_altillo.csv` → `data/`
- Move: `Matriz_Normativa_IA_Educacion_LATAM.xlsx` → `data/`

- [ ] **Step 1: Mover archivos con git mv**

```bash
git mv listado_universidades_altillo.csv data/listado_universidades_altillo.csv
git mv "Matriz_Normativa_IA_Educacion_LATAM.xlsx" "data/Matriz_Normativa_IA_Educacion_LATAM.xlsx"
```

- [ ] **Step 2: Verificar que config los encuentra**

```bash
python -c "import config; print(config.CSV_PATH.exists(), config.KNOWN_MATRIX_EXCEL.exists())"
```

Expected output: `True True`

> Si `Matriz_Normativa_IA_Educacion_LATAM.xlsx` no existe en la raíz, el resultado para esa ruta será `False` — es aceptable, la skip-list es opcional.

- [ ] **Step 3: Commit**

```bash
git commit -m "refactor: move CSV and skip-list Excel to data/"
```

---

## Task 10: Actualizar `main.py` — imports y flag `--phase3-only`

**Files:**
- Modify: `main.py`

- [ ] **Step 1: Reemplazar bloque de imports del pipeline en `main.py`**

Buscar el bloque (líneas 49-57 del `main.py` original):
```python
import config
import government_search
import university_search
import open_search
import document_extractor
import document_classifier
import deduplicator
import ai_classifier
import matrix_builder
import excel_exporter
```

Reemplazar con:
```python
import config
from src.pipeline import government_search
from src.pipeline import university_search
from src.pipeline import open_search
from src.pipeline import document_extractor
from src.pipeline import document_classifier
from src.pipeline import deduplicator
from src.pipeline import ai_classifier
from src.pipeline import matrix_builder
from src.pipeline import excel_exporter
```

- [ ] **Step 2: Agregar flag `--phase3-only` en `_parse_args()`**

Localizar el bloque de argumentos en `_parse_args()`. Agregar después de `--skip-open`:

```python
parser.add_argument(
    "--phase3-only", action="store_true",
    help="Ejecutar solo Fase 3 (búsqueda abierta) + extracción + clasificación + Excel. "
         "Equivale a --skip-government --skip-universities."
)
```

- [ ] **Step 3: Aplicar `--phase3-only` en el bloque `if __name__ == "__main__"`**

Localizar en `__main__` donde se llama a `run_pipeline(...)`. Agregar ANTES de esa llamada:

```python
if getattr(args, "phase3_only", False):
    args.skip_government = True
    args.skip_universities = True
```

- [ ] **Step 4: Verificar que `--help` funciona**

```bash
python main.py --help
```

Expected: muestra `--phase3-only` en la lista de opciones sin errores de import.

- [ ] **Step 5: Commit**

```bash
git add main.py
git commit -m "refactor: update main.py imports to src.pipeline and add --phase3-only flag"
```

---

## Task 11: Mover archivos de referencia y eliminar temporales

**Files:**
- Move: PDFs de referencia → `reference/`
- Move: `documentos_pdfs.zip` → `reference/`
- Delete: `run_phase3.py`
- Delete: `copia_segundo_webscrapper.xlsx`

- [ ] **Step 1: Mover PDFs y zip a `reference/`**

```bash
git mv "Manual-Investigadores.pdf" "reference/Manual-Investigadores.pdf"
git mv "Distribucioìn final.pdf" "reference/Distribucioìn final.pdf"
git mv observaciones.pdf reference/observaciones.pdf
git mv documentos_pdfs.zip reference/documentos_pdfs.zip
```

- [ ] **Step 2: Eliminar archivos temporales**

```bash
git rm run_phase3.py
git rm "copia_segundo_webscrapper.xlsx"
```

- [ ] **Step 3: Verificar raíz limpia**

```bash
ls *.py *.xlsx *.pdf *.zip 2>/dev/null || echo "Raíz limpia"
```

Expected: solo `main.py` y `config.py` como `.py`. No debe haber `.xlsx`, `.pdf` ni `.zip`.

- [ ] **Step 4: Commit**

```bash
git commit -m "chore: move reference files to reference/, delete run_phase3.py and temp xlsx"
```

---

## Task 12: Eliminar módulos originales de la raíz

Solo eliminar los archivos `.py` del pipeline que ya fueron copiados a `src/pipeline/`.

**Files:** eliminar de raíz: `government_search.py`, `university_search.py`, `open_search.py`, `site_crawler.py`, `document_extractor.py`, `document_classifier.py`, `ai_classifier.py`, `deduplicator.py`, `url_filter.py`, `matrix_builder.py`, `excel_exporter.py`, `search_backends.py`

- [ ] **Step 1: Eliminar módulos originales de la raíz**

```bash
git rm government_search.py university_search.py open_search.py site_crawler.py
git rm document_extractor.py document_classifier.py ai_classifier.py deduplicator.py
git rm url_filter.py matrix_builder.py excel_exporter.py search_backends.py
```

- [ ] **Step 2: Smoke test de imports desde la raíz**

```bash
python -c "
from src.pipeline import (
    government_search, university_search, open_search, site_crawler,
    document_extractor, document_classifier, ai_classifier, deduplicator,
    url_filter, matrix_builder, excel_exporter, search_backends,
)
print('Todos los imports OK')
"
```

Expected output: `Todos los imports OK`

- [ ] **Step 3: Verificar `--help` del pipeline**

```bash
python main.py --help
```

Expected: muestra ayuda completa sin errores de import.

- [ ] **Step 4: Commit**

```bash
git commit -m "refactor: remove original pipeline modules from root — all now in src/pipeline/"
```

---

## Task 13: Tests unitarios para `document_classifier`

**Files:**
- Create: `tests/test_document_classifier.py`

- [ ] **Step 1: Crear `tests/test_document_classifier.py`**

```python
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.pipeline.document_classifier import heuristic_score, classify_batch
import config


def _make_doc(text="", url="https://unam.mx/reglamento", title=""):
    return {
        "url": url,
        "title": title,
        "snippet": "",
        "extracted_text": text,
        "content_type": "html",
    }


def test_alta_label_with_reglamento_and_ia():
    doc = _make_doc(
        text="reglamento de uso de inteligencia artificial en la universidad",
        url="https://unam.mx/reglamentos/ia.pdf",
    )
    doc["heuristic_score"] = heuristic_score(doc)
    assert doc["heuristic_score"] >= config.HEURISTIC_HIGH_THRESHOLD, (
        f"Expected ALTA (>= {config.HEURISTIC_HIGH_THRESHOLD}), got {doc['heuristic_score']:.3f}"
    )


def test_media_label_with_guia_and_ia():
    doc = _make_doc(
        text="guía de uso responsable de inteligencia artificial para docentes",
        url="https://tec.mx/guia-ia",
    )
    score = heuristic_score(doc)
    assert config.HEURISTIC_MEDIUM_THRESHOLD <= score < config.HEURISTIC_HIGH_THRESHOLD, (
        f"Expected MEDIA [{config.HEURISTIC_MEDIUM_THRESHOLD}, {config.HEURISTIC_HIGH_THRESHOLD}), got {score:.3f}"
    )


def test_baja_label_noticia_sin_ia():
    doc = _make_doc(
        text="noticia del día: el rector inauguró el nuevo edificio universitario",
        url="https://unam.mx/noticias/rector",
    )
    score = heuristic_score(doc)
    assert score < config.HEURISTIC_MEDIUM_THRESHOLD, (
        f"Expected BAJA (< {config.HEURISTIC_MEDIUM_THRESHOLD}), got {score:.3f}"
    )


def test_sin_ia_keywords_fuerza_score_bajo():
    """Doc con keywords normativas pero sin mención de IA → score limitado."""
    doc = _make_doc(
        text="reglamento de titulación y graduación de la facultad",
        url="https://ipn.mx/reglamentos/titulacion.pdf",
    )
    score = heuristic_score(doc)
    assert score < config.HEURISTIC_HIGH_THRESHOLD, (
        f"Sin hits de IA, score debe ser < {config.HEURISTIC_HIGH_THRESHOLD}, got {score:.3f}"
    )


def test_classify_batch_assigns_labels():
    docs = [
        _make_doc("lineamiento inteligencia artificial universidad consejo universitario", "https://unam.mx/lineamientos.pdf"),
        _make_doc("blog de noticias universitarias evento conferencia", "https://unam.mx/blog/evento"),
    ]
    result = classify_batch(docs)
    labels = [d["heuristic_label"] for d in result]
    assert "ALTA" in labels or "MEDIA" in labels, "Al menos un doc debería ser ALTA o MEDIA"
    assert "BAJA" in labels, "Al menos un doc debería ser BAJA"
```

- [ ] **Step 2: Ejecutar tests**

```bash
pytest tests/test_document_classifier.py -v
```

Expected: todos los tests pasan (`5 passed`).

- [ ] **Step 3: Commit**

```bash
git add tests/test_document_classifier.py
git commit -m "test: add unit tests for document_classifier heuristic scoring"
```

---

## Task 14: Tests unitarios para `url_filter`

**Files:**
- Create: `tests/test_url_filter.py`

- [ ] **Step 1: Crear `tests/test_url_filter.py`**

```python
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.pipeline.url_filter import is_excluded, looks_normative, filter_and_rank
from src.pipeline.deduplicator import normalize_url


def test_facebook_is_excluded():
    assert is_excluded("https://www.facebook.com/unam/posts/123") is True


def test_twitter_is_excluded():
    assert is_excluded("https://twitter.com/sep_mx/status/456") is True


def test_news_site_is_excluded():
    assert is_excluded("https://www.eluniversal.com.mx/ciencia/ia-en-educacion") is True


def test_university_normativa_not_excluded():
    assert is_excluded("https://www.unam.mx/reglamentos/uso-ia.pdf") is False


def test_gob_mx_not_excluded():
    assert is_excluded("https://www.dof.gob.mx/nota_detalle.php?codigo=123") is False


def test_looks_normative_reglamento():
    assert looks_normative("https://unam.mx/reglamentos/ia") is True


def test_looks_normative_lineamiento():
    assert looks_normative("https://ipn.mx/lineamientos-institucionales") is True


def test_looks_normative_noticia_false():
    assert looks_normative("https://unam.mx/noticias/evento-ia-2024") is False


def test_filter_and_rank_removes_excluded():
    docs = [
        {"url": "https://facebook.com/unam", "title": "", "snippet": ""},
        {"url": "https://unam.mx/reglamentos/ia.pdf", "title": "Reglamento IA", "snippet": "inteligencia artificial"},
    ]
    result = filter_and_rank(docs)
    urls = [d["url"] for d in result]
    assert "https://facebook.com/unam" not in urls
    assert any("unam.mx" in u for u in urls)


def test_normalize_url_strips_tracking_params():
    url = "https://unam.mx/reglamento?utm_source=newsletter&utm_medium=email"
    normalized = normalize_url(url)
    assert "utm_source" not in normalized
    assert "utm_medium" not in normalized


def test_normalize_url_unifies_http_https():
    url_http  = normalize_url("http://unam.mx/reglamento/")
    url_https = normalize_url("https://unam.mx/reglamento/")
    assert url_http == url_https


def test_normalize_url_strips_www():
    with_www    = normalize_url("https://www.unam.mx/reglamento")
    without_www = normalize_url("https://unam.mx/reglamento")
    assert with_www == without_www
```

- [ ] **Step 2: Ejecutar tests**

```bash
pytest tests/test_url_filter.py -v
```

Expected: todos los tests pasan (`12 passed`).

- [ ] **Step 3: Commit**

```bash
git add tests/test_url_filter.py
git commit -m "test: add unit tests for url_filter exclusions and normalization"
```

---

## Task 15: Completar `.env.example`

**Files:**
- Modify: `.env.example`

- [ ] **Step 1: Reemplazar el contenido de `.env.example`**

Reemplazar el contenido completo con:

```bash
# Variables de entorno para el sistema GENIAL
# Copia este archivo como .env y completa los valores
# En GCP Compute Engine usa Secret Manager (ver abajo) en lugar de .env

# ── OpenAI ────────────────────────────────────────────────────────────────────
# Requerido para clasificación con IA. Sin esto, solo clasificación heurística.
OPENAI_API_KEY=sk-...
# Modelo a usar (default: gpt-4o-mini — equilibrio costo/calidad)
OPENAI_MODEL=gpt-4o-mini

# ── Investigador ──────────────────────────────────────────────────────────────
RESEARCHER_NAME=Carlos Auquilla

# ── Backends de búsqueda ─────────────────────────────────────────────────────
# Google Custom Search API — 100 queries/día gratis, funciona en GCP
# Obtener en: https://programmablesearchengine.google.com/
GOOGLE_CSE_API_KEY=
GOOGLE_CSE_ID=

# Brave Search API — 2000 queries/mes gratis, funciona en GCP
# Obtener en: https://api.search.brave.com/
BRAVE_API_KEY=

# Usar Google scraping HTML (solo funciona fuera de GCP/AWS)
GOOGLE_AS_PRIMARY=true

# Pausa entre búsquedas (segundos) — aumentar si hay rate-limit
SEARCH_DELAY_SECONDS=0.5

# ── GCP Secret Manager (alternativa a .env en producción) ────────────────────
# Cargar secrets desde GCP en lugar de un archivo .env:
#   export OPENAI_API_KEY=$(gcloud secrets versions access latest --secret="openai-api-key")
#   export BRAVE_API_KEY=$(gcloud secrets versions access latest --secret="brave-api-key")
#   export GOOGLE_CSE_API_KEY=$(gcloud secrets versions access latest --secret="google-cse-api-key")
#   export GOOGLE_CSE_ID=$(gcloud secrets versions access latest --secret="google-cse-id")
```

- [ ] **Step 2: Verificar que las variables se cargan correctamente**

```bash
python -c "
import os
from pathlib import Path

env_vars = ['OPENAI_API_KEY', 'OPENAI_MODEL', 'RESEARCHER_NAME',
            'GOOGLE_CSE_API_KEY', 'GOOGLE_CSE_ID', 'BRAVE_API_KEY',
            'GOOGLE_AS_PRIMARY', 'SEARCH_DELAY_SECONDS']
print('Variables en .env.example:')
for line in Path('.env.example').read_text().splitlines():
    if '=' in line and not line.startswith('#'):
        key = line.split('=')[0]
        if key in env_vars:
            print(f'  OK: {key}')
"
```

Expected: lista todas las variables esperadas.

- [ ] **Step 3: Commit**

```bash
git add .env.example
git commit -m "chore: complete .env.example with all backend variables and GCP Secret Manager instructions"
```

---

## Task 16: Crear `scripts/run_vm.sh` para GCP Compute Engine

**Files:**
- Create: `scripts/run_vm.sh`

- [ ] **Step 1: Crear `scripts/run_vm.sh`**

```bash
#!/usr/bin/env bash
# scripts/run_vm.sh — Lanza el pipeline GENIAL en background (GCP Compute Engine)
#
# Uso:
#   ./scripts/run_vm.sh [opciones de main.py]
#
# Ejemplos:
#   ./scripts/run_vm.sh --all-universities --resume
#   ./scripts/run_vm.sh --phase3-only --skip-ai
#   ./scripts/run_vm.sh --max-universities 10 --verbose
#
# Requiere: python en PATH, .env cargado o variables de entorno exportadas

set -euo pipefail

LOG_FILE="logs/nohup.out"
PID_FILE="logs/pipeline.pid"

mkdir -p logs

echo "Iniciando pipeline GENIAL..."
echo "Argumentos: $*"

nohup python main.py "$@" >> "$LOG_FILE" 2>&1 &
echo $! > "$PID_FILE"

echo "Pipeline iniciado (PID $(cat "$PID_FILE"))"
echo "Ver log en tiempo real: tail -f $LOG_FILE"
echo "Detener pipeline: kill \$(cat $PID_FILE)"
```

- [ ] **Step 2: Dar permisos de ejecución**

```bash
chmod +x scripts/run_vm.sh
```

- [ ] **Step 3: Verificar sintaxis del script**

```bash
bash -n scripts/run_vm.sh && echo "Sintaxis OK"
```

Expected output: `Sintaxis OK`

- [ ] **Step 4: Commit**

```bash
git add scripts/run_vm.sh
git commit -m "feat: add scripts/run_vm.sh for nohup execution on GCP Compute Engine"
```

---

## Task 17: Smoke test final y verificación de la raíz

- [ ] **Step 1: Verificar contenido de la raíz**

```bash
ls -1 *.py *.md *.txt *.example 2>/dev/null
```

Expected: solo `main.py`, `config.py`, `README.md`, `PROPOSITO_PROYECTO_MANUAL.md`, `requirements.txt`, `.env.example`, `LICENSE`.

- [ ] **Step 2: Ejecutar suite de tests completa**

```bash
pytest tests/ -v
```

Expected: todos los tests pasan.

- [ ] **Step 3: Verificar `--help`**

```bash
python main.py --help
```

Expected: muestra todos los flags incluyendo `--phase3-only`, sin errores de import.

- [ ] **Step 4: Verificar `--phase3-only --skip-ai` en dry-run (sin red)**

```bash
python -c "
import config
config.OPEN_SEARCH_QUERIES = []  # sin queries para que no haga requests
from src.pipeline import open_search
print('Phase3 module importable:', open_search.__file__)
"
```

Expected: imprime el path del módulo en `src/pipeline/`.

- [ ] **Step 5: Commit final**

```bash
git add -A
git commit -m "chore: final cleanup and verification — GENIAL reorganization complete"
```

---

## Self-Review

**Spec coverage:**
- [x] Estructura `src/pipeline/` — Tasks 1-12
- [x] Imports relativos — Tasks 3-7
- [x] `config.py` rutas a `data/` — Task 8
- [x] Datos a `data/` — Task 9
- [x] `main.py` imports + `--phase3-only` — Task 10
- [x] Referencias a `reference/`, eliminar temporales — Task 11
- [x] Eliminar módulos de raíz — Task 12
- [x] Tests `document_classifier` — Task 13
- [x] Tests `url_filter` — Task 14
- [x] `.env.example` completo — Task 15
- [x] `scripts/run_vm.sh` — Task 16
- [x] Smoke test final — Task 17

**Placeholder scan:** Sin TBDs, TODOs ni pasos sin código.

**Type consistency:** `heuristic_score()` definida en Task 13 Step 1 y usada consistentemente. `normalize_url()` importada de `deduplicator` en Task 14 Step 1.

# GENIAL — Mejoras pre-run largo (2026-05-25)

## Contexto

Evaluación del run `normativa_ia_mexico_20260525_1513.xlsx` reveló 5 problemas:
1. Métricas rotas (`official_domain_ratio=0`, `pdf_yield=0`, typo `misss`)
2. Falsos positivos: Fermatta (planes de estudio con IA como materia clasificados como normativa)
3. Falsos negativos: SEV PDF de taller docente sobre IA (score 0.73 ALTA, clasificado "otro")
4. Cobertura baja: nombres de universidad abreviados como `(UPV)` generan queries inútiles
5. Resultados de caché obsoleta: test con UNAM/Tec/UANL requiere búsquedas frescas

Approach elegido: **B — Targeted fixes + query quality + fresh cache**

---

## Sección 1: Métricas (`src/pipeline/search_metrics.py`)

### Bug 1 — `official_domain_ratio = 0`

**Causa:** `record_query()` aplica `p.search(url)` a la URL completa. Los patrones `r"\.gob\.mx$"` usan ancla `$` que requiere fin de cadena; una URL con path nunca termina en `.gob.mx`.

**Fix:** Antes del loop de URLs en `record_query()`, extraer el `netloc` con `urlparse` y aplicar el regex solo al host (igual que `config._is_official_url` ya lo hace).

```python
# Antes (buggy):
if any(p.search(u) for p in patterns):
    b.official_count += 1

# Después:
try:
    host = urlparse(u).netloc or u
except Exception:
    host = u
if any(p.search(host) for p in patterns):
    b.official_count += 1
```

### Bug 2 — `pdf_yield = 0` para cache hits

**Causa:** Cache hits retornan early sin llamar `record_query()`, por lo que las URLs de resultados cacheados nunca se inventarían en el bucket.

**Fix:** En `_call_backend()`, cuando se sirve desde caché, llamar `record_query()` con `latency_ms=0` para registrar el inventario de URLs.

```python
if cached is not None:
    if metrics_on:
        get_metrics().record_cache_event("hit", query_type or "legacy")
        urls = [r.get("url") or r.get("href", "") for r in cached]
        get_metrics().record_query(backend, query_type or "legacy", 0.0, len(cached), urls)
    ...
    return cached
```

### Bug 3 — typo `misss` en JSON

**Causa:** `record_cache_event("miss", ...)` hace `"miss" + "s" = "misss"`.

**Fix:** Mapear explícitamente el nombre del evento a la clave correcta:

```python
_EVENT_KEY = {"hit": "hits", "miss": "misses", "expired": "expired"}

def record_cache_event(self, event: str, query_type: str) -> None:
    key = _EVENT_KEY.get(event, event + "s")
    ...
```

---

## Sección 2: AI Classifier (`src/pipeline/ai_classifier.py`)

### Cambio 1 — Incluir materiales pedagógicos oficiales de gobierno

Añadir al bloque de criterios de `_USER_PROMPT_TEMPLATE`:

> `es_normativa = "si"` también aplica si el documento es un **material oficial de formación docente, guía pedagógica o taller** emitido por SEP, SEV, CONAHCYT u otro organismo gubernamental mexicano que establezca orientaciones, lineamientos o criterios sobre el uso de IA en la enseñanza o en contextos educativos institucionales. La procedencia gubernamental oficial es suficiente para considerar el documento normativa cuando regula o guía activamente el uso de IA en educación.

### Cambio 2 — Excluir catálogos de materias / planes de estudio

Añadir al bloque de criterios negativos:

> `es_normativa = "no"` si el documento es principalmente un **catálogo de materias, plan de estudios, descripción de programa académico o pensum** que *menciona* IA como asignatura o herramienta curricular sin establecer reglas, políticas ni lineamientos sobre su uso. La presencia de una materia llamada "Herramientas de IA" en un plan de estudios no convierte al documento en normativa sobre IA.

### Cambio 3 — Nuevo valor en `tipo_norma`

Añadir `"material de formación docente"` a los valores válidos de `tipo_norma` en el JSON schema del prompt, para que talleres y guías oficiales de SEP/SEV no caigan en `"otro"`.

---

## Sección 3: Heurística (`config.py`)

Añadir al final de `LOW_SCORE_KEYWORDS` los siguientes indicadores de currículo académico:

```python
# curriculum — listing AI as a subject ≠ policy on AI use
"plan de estudios", "oferta académica", "oferta educativa",
"programa de posgrado", "licenciatura en", "maestría en",
"certificación en", "créditos", "semestres",
```

Efecto: cada hit suma `−0.025` al score (cap `−0.25`). Un documento tipo Fermatta con score 0.35 queda en ~0.25, por debajo de MEDIA. Documentos de política legítimos no contienen estos términos en contexto curricular, por lo que no se penalizan significativamente.

---

## Sección 4: Filtro de nombres de universidad (`src/pipeline/open_search.py`)

Añadir una función `_is_valid_university_name(name: str) -> bool` que retorna `False` si:
- La longitud del nombre (stripped) es < 6 caracteres
- El nombre empieza con `(` y termina con `)` — es un código interno
- El nombre contiene solo dígitos, paréntesis o guiones

Aplicar el filtro antes de construir la Fórmula 2 (query por nombre):

```python
if name and len(name) > 3 and _is_valid_university_name(name):
    q2 = f'"{name}" México "IA" ...'
    queries.append((q2, "open", domain))
```

Esto evita queries como `"(UPV)" México "IA" (ética OR ...)` que generan ruido.

---

## Sección 5: Limpieza de caché (`main.py` + `src/pipeline/search_router.py`)

### Flag CLI

Añadir argumento `--clear-cache-domains` a `main.py`:

```
--clear-cache-domains DOMINIO1,DOMINIO2,...
```

### Función de limpieza en `search_router.py`

```python
def clear_cache_for_domains(domains: list[str]) -> int:
    """Elimina entradas de caché cuya query contenga alguno de los dominios dados.
    Retorna el número de entradas eliminadas."""
    ...
```

Itera sobre `_cache_data`, elimina entradas donde `entry.get("results", [])` contiene URLs de esos dominios O donde la query contiene el dominio, y persiste el caché.

### Uso para el test run

```bash
python main.py --phase3-only --max-unis-phase3 3 \
  --clear-cache-domains unam.mx,tec.mx,uanl.mx \
  --profile balanced --verbose
```

El CSV deberá tener UNAM, Tec de Monterrey y UANL en las primeras 3 filas, o se usará `--max-unis-phase3` sobre un subconjunto específico.

---

## Archivos a modificar

| Archivo | Cambios |
|---|---|
| `src/pipeline/search_metrics.py` | Bugs 1, 2, 3 |
| `src/pipeline/search_router.py` | Bug 2 (cache hit → record_query), función `clear_cache_for_domains` |
| `src/pipeline/ai_classifier.py` | Prompt: incluir guías gov, excluir catálogos, nuevo tipo_norma |
| `config.py` | LOW_SCORE_KEYWORDS: añadir términos curriculares |
| `src/pipeline/open_search.py` | Filtro `_is_valid_university_name` |
| `main.py` | Flag `--clear-cache-domains`, llamada a `clear_cache_for_domains` |

## Archivos NO modificados

- `src/pipeline/document_classifier.py` — lógica heurística no cambia, solo los keywords en config
- `src/pipeline/matrix_builder.py` — sin cambios
- `src/pipeline/excel_exporter.py` — sin cambios

---

## Criterios de éxito del test run (3 universidades)

1. `official_domain_ratio > 0` para cualquier backend que haya servido URLs de `.gob.mx` o `.edu.mx`
2. `pdf_yield > 0` si algún resultado es PDF
3. JSON de métricas sin campo `misss`
4. Fermatta (si aparece) NO entra en la Matriz Normativa
5. Guías pedagógicas de SEV/SEP (si aparecen) SÍ entran en la Matriz Normativa
6. Sin queries del tipo `"(XXX)" México "IA"` en los logs

# Taxonomía de la Matriz Normativa

Este documento define los valores válidos para cada campo de la matriz. Solo estos valores deben aparecer en el Excel final. El pipeline los aplica automáticamente; esta referencia es útil para validación manual y para entender los criterios de clasificación IA.

> **Regla de oro:** Si un valor no está en esta lista, se mapea a `"No especificado"`. El valor `"mixto"` está explícitamente prohibido.

---

## Columnas de la matriz

### A — Investigador
Nombre del investigador asignado. Configurado en `config.RESEARCHER_NAME`.

Valor actual: **Carlos Auquilla**

---

### B — País
Siempre `México`. El pipeline está restringido a fuentes mexicanas.

---

### C — Título de la Norma
Título oficial del documento tal como aparece en el texto o en la URL.

- Si no se puede determinar: `"No Indica"`
- No inventar ni parafrasear el título.

---

### D — Tipo de norma

| Valor en matriz | Valor IA (prompt) | Descripción |
|---|---|---|
| Ley | `ley` | Ley formal emitida por el Congreso |
| Decreto | `decreto` | Decreto presidencial o del ejecutivo |
| Reglamento | `reglamento` | Reglamento institucional o gubernamental |
| Guía ética | `guía ética` | Guía de principios éticos para IA |
| Estrategia nacional | `estrategia nacional` | Política pública a nivel nacional |
| Resolución rectoral | `resolución rectoral` | Resolución emitida por un rector universitario |
| Lineamiento académico | `lineamiento académico` | Lineamiento de uso académico de IA |
| Libro blanco | `libro blanco` | Documento de posición o recomendaciones |
| Guía pedagógica | `guía pedagógica` | Guía para uso didáctico de IA |
| Código de ética | `código de ética` | Código ético institucional |
| Acuerdo institucional | `acuerdo institucional` | Acuerdo formal de una institución |
| Otro | `otro` | Tipo normativo no categorizado |
| No especificado | `no aplica` / `no indica` | Tipo no determinado |

---

### E — Estado

| Valor en matriz | Valor IA (prompt) | Descripción |
|---|---|---|
| Vigente | `vigente` | Norma actualmente en vigor |
| En proyecto | `en proyecto` | Borrador o propuesta no aprobada |
| Derogada | `derogada` | Norma que fue reemplazada o abrogada |
| No especificado | `no especificado` | Estado no determinado |

---

### F — Organismo Emisor/Universidad
Nombre del organismo o universidad que emite la norma.

- Ejemplos: `SEP`, `CONAHCYT`, `Universidad Nacional Autónoma de México`, `Instituto Politécnico Nacional`
- Si no se puede determinar: `"No Indica"`

---

### G — Dominio

| Valor en matriz | Valor IA (prompt) | Descripción |
|---|---|---|
| Pedagógico | `pedagógico` | Relacionado con enseñanza-aprendizaje, currículo, metodología |
| Administrativo | `administrativo` | Gobierno institucional, gestión, procesos |
| Protección de datos | `protección de datos` | Privacidad, datos personales, LFPDPPP |
| Ética | `ética` | Principios éticos, valores, deontología |
| Técnico | `técnico` | Infraestructura, sistemas, desarrollo tecnológico |
| No especificado | `no aplica` | Dominio no determinado |

> **Prohibido:** `"mixto"` no es un valor válido. Si un documento abarca múltiples dominios, se elige el dominio **predominante** del texto.

---

### H — Vínculo con Educación

| Valor en matriz | Valor IA (prompt) | Descripción |
|---|---|---|
| Directo | `directo` | El documento regula explícitamente algo de educación |
| Indirecto | `indirecto` | Aplica a educación pero no es su objeto central |
| No especificado | `no aplica` | Vínculo no determinado |

---

### I — Dedicación del Texto

Qué proporción del documento está dedicada a IA.

| Valor en matriz | Valor IA (prompt) | Descripción |
|---|---|---|
| Articulado completo | `articulado completo` | Todo el documento trata sobre IA |
| Sección/Capítulo | `sección/capítulo` | Una sección o capítulo específico |
| Mención breve | `mención breve` | Solo se menciona IA tangencialmente |
| No especificado | `no aplica` | No determinado |

---

### J — Fecha de Publicación

Formato: `DD/MM/AAAA`

- Si la fecha no puede verificarse con certeza: `"No Indica"`
- Años fuera del rango `[2015, año actual]` se reemplazan automáticamente por `"No Indica"`.
- **No inferir ni adivinar fechas** sin evidencia en el texto del documento.

---

### K — URL Oficial

URL directa al documento fuente.

- Debe ser un dominio `.gob.mx` o `.edu.mx` (o dominio prioritario verificado).
- No usar URLs de redes sociales, noticias ni repositorios no oficiales.

---

### L — Observaciones

Notas adicionales del clasificador sobre el documento. Campo libre.

Ejemplos de uso:
- `"Documento en proceso de aprobación según nota al pie"`
- `"Solo menciona IA en el contexto de protección de datos"`
- `"PDF escaneado; extracción de texto parcial"`

---

### M — Ámbito

| Valor en matriz | Valor IA (prompt) | Descripción |
|---|---|---|
| Nacional | `nacional` | Aplica a todo el territorio mexicano |
| Institucional | `institucional` | Aplica solo a una institución específica |
| No especificado | `no aplica` | Ámbito no determinado |

---

## Reglas de validación

1. **Fuente oficial obligatoria:** La URL debe pertenecer a `.gob.mx`, `.edu.mx` o un dominio en `PRIORITY_UNIVERSITIES`.
2. **IA explícita:** El documento debe mencionar `inteligencia artificial`, `IA`, `machine learning`, `algoritmo` u otro término de IA directamente. No se aceptan documentos que solo se relacionen indirectamente.
3. **`dominio` ≠ `"mixto"`:** Documentos donde la IA asigna `dominio = "mixto"` son rechazados automáticamente.
4. **Fecha validada:** Solo años `[2015, año_actual]` son aceptados. Cualquier otra fecha se convierte a `"No Indica"`.
5. **`tipo_norma` y `dominio` no reconocidos → `"No especificado"`:** Nunca pasan valores crudos del modelo al Excel.
6. **`es_normativa = "si"` requerido:** El campo `es_normativa` de la clasificación IA debe ser `"si"` para que el documento entre a la matriz.

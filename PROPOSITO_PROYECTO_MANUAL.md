# Propósito del Proyecto (según Manual del Investigador)

Este documento resume exclusivamente la información del archivo `Manual-Investigadores.pdf` para que un agente entienda el propósito y las reglas del proyecto.

## 1) Objetivo general
Analizar la adopción normativa, legal y ética de la Inteligencia Artificial en los sistemas educativos de Latinoamérica y el Caribe, en el caso de este proyecto nos centraremos en México exclusivamente.

## 2) Observaciones adicionales del investigador asignado
- El investigador asignado es Carlos Auquilla.
- La investigación en este proyecto está asignada de forma exclusiva a México.
- Todo el levantamiento, clasificación, registro y entregables deben limitarse únicamente a normativa de México.
- No se deben incluir hallazgos de otros países en la matriz final de este proyecto.

## 3) Alcance del levantamiento
- El levantamiento se realiza por país asignado al investigador.
- Se debe identificar normativa publicada por:
  - Universidades.
  - Instituciones gubernamentales.
- La base de universidades parte de Altillo:
  - https://www.altillo.com/universidades/index.asp
- Si un país no aparece en Altillo, el investigador debe construir su propia lista de universidades.

## 4) Flujo metodológico obligatorio

### Fase 1: Búsqueda en portales + Google
Fuentes objetivo:
- Portales gubernamentales (gacetas oficiales, ministerios de educación, ministerios de ciencia/tecnología).
- Organismos internacionales y redes (UNESCO, CEPAL, redes nacionales de investigación).

Palabras clave base sugeridas:
- [País] + "Ley de Inteligencia Artificial"
- [País] + "Decreto Inteligencia Artificial"
- [País] + "Guía ética de Inteligencia Artificial"
- [País] + "Estrategia Nacional de Inteligencia Artificial"
- [País] + "Resolución rectoral de Inteligencia Artificial"
- [País] + "Lineamiento académico de Inteligencia Artificial"
- [País] + "Ética de Inteligencia Artificial"
- [País] + "Guía Pedagógica de Inteligencia Artificial"

### Fase 2: Búsqueda en universidades (externa + rastreo heurístico)
- Ejecutar consultas externas por dominio (`site:`) para ubicar normativa relevante.
- Probar rutas conocidas en el sitio (normativa, reglamentos, lineamientos, IA).
- Extraer enlaces de esas rutas y de la página principal usando heurísticas.
- Verificar documentos normativos, legales y éticos de IA o equivalentes.

### Fase 3: Búsqueda genérica adicional (Google)
Uso de operadores avanzados:
- Fórmula general:
  - site:[URL_Universidad] "inteligencia artificial" AND (lineamientos OR política OR resolución OR guía)
- Búsqueda por país + universidad:
  - "[Nombre de la Universidad]" + [País] + "IA" + (ética OR "uso académico" OR regulación OR "pedagógico")

Palabras clave adicionales:
- "Integridad académica"
- "Uso de IA generativa"
- "Consejo Universitario"
- "Reglamento de evaluación"

### Fase 4: Levantamiento y registro en matriz
Se debe registrar cada hallazgo en la matriz con columnas obligatorias A-M.

## 5) Estructura de datos obligatoria (matriz)
Columnas obligatorias:
- A: Investigador
- B: País
- C: Título de la Norma
- D: Tipo de Norma
- E: Estado
- F: Organismo Emisor/Universidad
- G: Dominio
- H: Vínculo con Educación
- I: Dedicación del Texto
- J: Fecha de Publicación (DD/MM/AAAA)
- K: URL Oficial
- L: Observaciones
- M: Ámbito (nacional o institucional)

Valores controlados relevantes:
- Tipo de norma: Ley, Decreto, Reglamento, Guía Ética, Estrategia Nacional.
- Estado: Vigente, En Proyecto (Borrador), Derogada.
- Dominio: Pedagógico, Administrativo, Protección de Datos, Ética, Técnico.
- Vínculo con educación:
  - Directo: norma específica IA-educación.
  - Indirecto: norma general de IA o datos aplicable al sector educativo.
- Dedicación del texto: Articulado completo, Sección/Capítulo, Mención breve.

## 6) Criterios de clasificación de dominio
- Pedagógico: regula enseñanza-aprendizaje mediado por IA.
- Protección de datos y privacidad: tratamiento de datos personales en educación.
- Ético: principios, sesgos, transparencia, equidad.
- Administrativo y de gestión: procesos institucionales y servicios educativos.
- Técnico e infraestructura: hardware, software, conectividad e interoperabilidad.

## 7) Entregables finales obligatorios
- Matriz de datos consolidada (Excel).

## 8) Regla de ausencia de evidencia
Si no se encuentra normativa específica, se debe registrar explícitamente como:
- "No Indica" o
- "Sin normativa específica detectada"

Esta regla evita sesgos en el conteo final.

## 9) Instrucción operativa para agentes
Un agente que ejecute este proyecto debe priorizar:
- Cobertura sistemática por fases (1 a 4).
- Registro estructurado y consistente en la matriz.
- Trazabilidad de fuentes oficiales.
- Clasificación homogénea (tipo, estado, dominio, vínculo, ámbito).
- Registro explícito de ausencia de normativa para no sesgar resultados.
- Restricción geográfica explícita: investigar y registrar únicamente normativa de México.

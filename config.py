"""
config.py — Configuración global del sistema GENIAL
Modifica este archivo para ajustar comportamiento, límites y credenciales.
"""

import os
from pathlib import Path
from datetime import datetime

# ─── Rutas ───────────────────────────────────────────────────────────────────
BASE_DIR   = Path(__file__).parent
CSV_PATH   = BASE_DIR / "listado_universidades_altillo.csv"
OUTPUT_DIR = BASE_DIR / "output"
CACHE_DIR  = BASE_DIR / "cache"
LOG_DIR    = BASE_DIR / "logs"

# Excel con los registros definitivos ya clasificados.
# Si existe, sus URLs se usan como skip-list para no reprocesar documentos.
KNOWN_MATRIX_EXCEL = BASE_DIR / "Matriz_Normativa_IA_Educacion_LATAM.xlsx"

for _d in [OUTPUT_DIR, CACHE_DIR, LOG_DIR]:
    _d.mkdir(exist_ok=True)

OUTPUT_EXCEL = OUTPUT_DIR / f"normativa_ia_mexico_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"

# ─── Investigador ─────────────────────────────────────────────────────────────
RESEARCHER_NAME = os.getenv("RESEARCHER_NAME", "Carlos Auquilla")
COUNTRY         = "México"
NO_INDICA_LABEL = "No Indica"
SIN_NORMATIVA_LABEL = "Sin normativa específica detectada"

# ─── OpenAI ───────────────────────────────────────────────────────────────────
OPENAI_API_KEY   = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL     = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
OPENAI_MAX_TOKENS = 600      # JSON estructurado; respuestas típicas 300-450 tokens
OPENAI_INPUT_CHARS = 3500    # Reducido de 5500 para ahorrar ~30% en tokens de entrada

# Ampliación controlada de cobertura IA para documentos borderline
AI_INCLUDE_BORDERLINE_BAJA = True
AI_BAJA_MIN_SCORE = 0.30          # Umbral mínimo elevado para reducir falsos positivos
AI_BAJA_MIN_URL_PRIORITY = 0.60   # Umbral URL elevado para exigir más señal normativa
AI_MAX_EXTRA_BAJA = 20

# ─── Búsqueda ─────────────────────────────────────────────────────────────────
MAX_RESULTS_PER_QUERY    = 10   # resultados por query DDG
MAX_URLS_PER_UNIVERSITY  = 6    # URLs máx por universidad
MAX_UNIVERSITIES         = None  # None = todas las universidades (run completo)
SEARCH_DELAY_SECONDS     = 0.5  # pausa entre búsquedas (evita bloqueos DDG)
CRAWL_NON_PRIORITY       = True   # crawl para todas; no-prioritarias usan límites reducidos
CRAWL_NON_PRIORITY_MAX_DOCS    = 2   # URLs máx por universidad no prioritaria
CRAWL_NON_PRIORITY_MAX_SECONDS = 8   # timeout de crawl para no-prioritarias
MAX_WORKERS              = 16   # seguro con ≥8GB RAM; subir a 20-24 si tienes más

# Cache de búsquedas DDG entre runs (evita repetir queries ya hechas)
DDG_CACHE_ENABLED        = True   # False para deshabilitar en producción limpia

# Pausa entre Fase 2 y Fase 3 (segundos) — actualmente Fase 3 corre antes de Fase 2
INTER_PHASE_PAUSE_SECONDS = 0    # reservado para ajustes futuros

# Filtro pre-extracción: descartar docs sin señal de IA ni normativa en snippet/URL
PRE_EXTRACTION_FILTER_ENABLED = True  # False para deshabilitar

# Perfil de sesión larga (enfocado a normativa de IA en México)
DEFINITIVE_RUN_MAX_UNIVERSITIES = None  # sin límite en producción

# Filtros temáticos para priorizar normativa real y reducir ruido
STRICT_TOPIC_FILTER = True
TOPIC_MUST_INCLUDE_AI = True
TOPIC_MIN_POLICY_HITS = 1

# ─── HTTP ─────────────────────────────────────────────────────────────────────
REQUEST_TIMEOUT   = 10          # segundos
MAX_PDF_SIZE_MB   = 15
MAX_TEXT_CHARS_HTML = 12_000    # chars de texto a retener de HTML
MAX_TEXT_CHARS_PDF  = 10_000    # chars de texto a retener de PDF
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 "
    "(KHTML, like Gecko) Version/17.3 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64; rv:125.0) Gecko/20100101 Firefox/125.0",
]

# ─── Clasificación heurística ─────────────────────────────────────────────────
HEURISTIC_HIGH_THRESHOLD = 0.50
HEURISTIC_MEDIUM_THRESHOLD = 0.30  # subido de 0.24 → exige más señal normativa

HIGH_SCORE_KEYWORDS = [
    "reglamento", "resolución", "resolucion", "acuerdo", "decreto",
    "ley ", "lineamiento", "lineamientos", "normativa", "norma ",
    "política institucional", "politica institucional",
    "consejo universitario", "disposiciones", "estatuto",
    "marco normativo", "marco regulatorio", "circular", "directriz", "directrices",
    "resolución rectoral", "resolucion rectoral", "estrategia nacional",
]
MEDIUM_SCORE_KEYWORDS = [
    "guía", "guia", "manual", "protocolo", "política", "politica",
    "criterios", "procedimiento", "estrategia", "programa", "plan",
    "código de ética", "codigo de etica", "libro blanco",
    "integridad académica", "integridad academica", "uso de ia generativa",
    "reglamento de evaluación", "reglamento de evaluacion",
]
LOW_SCORE_KEYWORDS = [
    "noticia", "blog", "evento", "curso", "taller", "seminario",
    "conferencia", "artículo", "articulo", "opinión", "opinion",
    "entrevista", "podcast",
    # Convocatorias / bases de eventos académicos (no son normativa)
    "convocatoria", "bases de participación", "bases de participacion",
    "presentar propuestas", "propuesta de ponencia", "registro de participantes",
    "ficha de inscripción", "ficha de inscripcion", "inscripción al evento",
]
AI_KEYWORDS = [
    "inteligencia artificial", "aprendizaje automático",
    "aprendizaje automatico", "machine learning", "chatgpt",
    "chat gpt", "gpt-", "modelo de lenguaje", "modelo de ia",
    "llm", "deep learning", "minería de datos",
    "ia generativa", "sistema de ia", "sistemas de ia",
    "ia en educación", "ia en educacion", "uso de ia",
]
# NOTA: ' ia ' (sola, con espacios) fue removida — produce falsos positivos por OCR
# ('la' leído como 'ia'). 'algoritmo' fue removida — demasiado genérica.

EDU_KEYWORDS = [
    "educación superior", "educacion superior", "universidad", "universidades",
    "docente", "docentes", "estudiante", "estudiantes", "enseñanza", "aprendizaje",
    "plan de estudios", "curricular", "campus", "institución educativa", "ies",
]

POLICY_KEYWORDS = [
    "normativa", "lineamiento", "lineamientos", "reglamento", "reglamentos",
    "acuerdo", "decreto", "ley", "resolución", "resolucion", "directriz",
    "protocolo", "código", "codigo", "estatuto", "marco regulatorio", "política",
    "politica", "guía", "guia",
]

# ─── Filtro de URLs ───────────────────────────────────────────────────────────
EXCLUDED_DOMAINS = {
    "facebook.com", "twitter.com", "x.com", "instagram.com",
    "linkedin.com", "youtube.com", "tiktok.com", "reddit.com",
    "wikipedia.org", "wikimedia.org",
    # Medios de comunicación nacionales
    "eluniversal.com.mx", "excelsior.com.mx", "milenio.com",
    "reforma.com", "jornada.com.mx", "infobae.com",
    "expansion.mx", "forbes.com.mx", "animalpolitico.com",
    "elfinanciero.com.mx", "eleconomista.com.mx", "oem.com.mx",
    "mundoejecutivo.com.mx", "posta.com.mx", "notipress.mx",
    "rotativodigital.com.mx", "suracapulco.mx", "dognews.mx",
    "onedigital.mx", "estilouniversitario.mx", "mexico.quadratin.com.mx",
    "fastcompany.mx",
    # Blogs y plataformas genéricas
    "blogspot.com", "wordpress.com", "medium.com", "substack.com",
    "slideshare.net", "scribd.com", "academia.edu",
    "researchgate.net", "semanticscholar.org",
    # Journals y repositorios académicos (no son normativa gubernamental)
    "scielo.org.mx", "ride.org.mx", "redalyc.org",
}
PRIORITY_URL_KEYWORDS = [
    "normativa", "reglamento", "lineamiento", "politica", "acuerdo",
    "resolucion", "guia", "marco-juridico", "marco_juridico",
    "estatuto", "decreto", "legislacion", "disposicion", "normatividad",
]
# NOTA: 'transparencia', 'documentos', 'consejo' fueron removidas —
# capturaban contratos, licitaciones y actas administrativas sin relación con IA.

# ─── Fuentes gubernamentales ──────────────────────────────────────────────────
GOVERNMENT_QUERIES = [
    "México ley de inteligencia artificial",
    "México decreto inteligencia artificial",
    "México guía ética de inteligencia artificial",
    "México estrategia nacional de inteligencia artificial",
    "México resolución rectoral inteligencia artificial",
    "México lineamiento académico inteligencia artificial",
    "México ética de inteligencia artificial educación",
    "México guía pedagógica de inteligencia artificial",
    "política pública inteligencia artificial educación México gob.mx",
    "ley inteligencia artificial México decreto congreso",
    "SEP secretaría educación inteligencia artificial lineamientos México",
    "CONAHCYT inteligencia artificial programa estrategia México",
    "regulación inteligencia artificial universidades México gobierno",
    "DOF inteligencia artificial acuerdo decreto México",
    "marco regulatorio IA educación superior México",
    "ENIA estrategia nacional inteligencia artificial",
    "acuerdo ministerial inteligencia artificial educación México",
]
GOVERNMENT_SEED_URLS = [
    "https://www.gob.mx/agenda-digital",
    "https://www.gob.mx/sep",
    "https://conahcyt.mx",
    "https://www.dof.gob.mx",
    "https://www.inai.org.mx",
    "https://www.ift.org.mx",
    "https://www.economia.gob.mx",
    "https://www.sesna.gob.mx",
    "https://www.presidencia.gob.mx",
    "https://ceide.unam.mx",            # UNAM CEIDE — recomendaciones IA generativa
    "https://www.sep.gob.mx/en/sep1/normateca",  # Normateca SEP
]
GOVERNMENT_PRIORITY_DOMAINS = [
    ".gob.mx", "dof.gob.mx", "sep.gob.mx", "conahcyt.mx",
    "conacyt.gob.mx", "ift.org.mx",
]

# Dominios de universidades mexicanas reconocidas que no usan .edu.mx
EXTRA_ALLOWED_UNIVERSITY_DOMAINS = [
    "uqroo.mx", "buap.mx", "ujat.mx", "uadec.mx", "unison.mx",
    "uaz.edu.mx", "uabc.mx", "colmex.mx", "cide.edu",
]

# ─── Universidades prioritarias ───────────────────────────────────────────────
PRIORITY_UNIVERSITIES = [
    {"universidad": "Tecnológico de Monterrey",   "url_oficial": "https://tec.mx/"},
    {"universidad": "UNAM",                        "url_oficial": "https://www.unam.mx/"},
    {"universidad": "IPN",                         "url_oficial": "https://www.ipn.mx/"},
    {"universidad": "Universidad Panamericana",    "url_oficial": "https://www.up.edu.mx/"},
    {"universidad": "ITAM",                        "url_oficial": "https://www.itam.mx/"},
    {"universidad": "Universidad Anáhuac",         "url_oficial": "https://www.anahuac.mx/"},
    {"universidad": "El Colegio de México",        "url_oficial": "https://www.colmex.mx/"},
    {"universidad": "Universidad Iberoamericana",  "url_oficial": "https://ibero.mx/"},
    {"universidad": "UAM",                         "url_oficial": "https://www.uam.mx/"},
    {"universidad": "Universidad de Guadalajara",  "url_oficial": "https://udg.mx/"},
    {"universidad": "UDLAP",                       "url_oficial": "https://www.udlap.mx/"},
    {"universidad": "BUAP",                        "url_oficial": "https://www.buap.mx/"},
    {"universidad": "UQROO",                       "url_oficial": "https://www.uqroo.mx/"},
]
MAX_URLS_PRIORITY_UNIVERSITY = 12  # más profundidad para universidades de alta prioridad

# ─── Crawling de universidades ────────────────────────────────────────────────
UNIVERSITY_CRAWL_PATHS = [
    # Normativa general
    "/normativa", "/normativa/", "/reglamentos", "/reglamentos/",
    "/transparencia", "/transparencia/",
    "/marco-juridico", "/marco_juridico",
    "/documentos", "/documentos-institucionales",
    "/consejo-universitario", "/consejo_universitario",
    "/legislacion", "/politicas", "/lineamientos",
    "/acuerdos", "/estatutos",
    "/gobierno/normatividad", "/gobierno/reglamentos",
    "/about/normativa", "/normatividad", "/reglamentacion",
    # Inteligencia Artificial
    "/inteligencia-artificial", "/inteligencia-artificial/",
    "/ia", "/uso-ia", "/uso-responsable-ia",
    "/politica-ia", "/lineamientos-ia", "/guia-ia",
    "/ai", "/ai-policy", "/artificial-intelligence",
    "/noticias/inteligencia-artificial",
    # Innovación / transformación digital
    "/innovacion-educativa", "/transformacion-digital",
    "/educacion-digital", "/modelo-educativo",
    "/investigacion/ia", "/investigacion/inteligencia-artificial",
]

# Rutas reducidas para universidades NO prioritarias.
# Más cortas que UNIVERSITY_CRAWL_PATHS para respetar el timeout de 15s.
# Cubre los paths más productivos histórica y heurísticamente.
NON_PRIORITY_CRAWL_PATHS = [
    "/normativa", "/normativa/",
    "/reglamentos", "/reglamentos/",
    "/transparencia", "/transparencia/",
    "/lineamientos", "/lineamientos/",
    "/politicas", "/politicas-institucionales",
    "/marco-juridico",
]

UNIVERSITY_QUERY_TEMPLATES = [
    'site:{domain} "inteligencia artificial" lineamientos OR reglamento OR política OR guía',
    'site:{domain} "uso de IA" OR "IA generativa" académico normativa OR protocolo OR estatuto',
    'site:{domain} "Integridad académica" OR "Consejo Universitario" OR "Reglamento de evaluación" inteligencia artificial',
]

# ─── Búsqueda abierta ─────────────────────────────────────────────────────────
OPEN_SEARCH_QUERIES = [
    # Normativa universitaria general
    "México lineamientos inteligencia artificial educación superior universidad filetype:pdf",
    "México reglamento uso de inteligencia artificial universidad estudiantes docentes filetype:pdf",
    "México acuerdo institucional inteligencia artificial universidad consejo universitario",
    "México política académica IA generativa institución educativa",
    "México guía institucional inteligencia artificial docencia investigación universidad",
    "México código de ética inteligencia artificial universidad",
    "México protocolo uso responsable de inteligencia artificial educación superior",
    "México marco regulatorio inteligencia artificial educación superior",
    # Diario Oficial de la Federación — queries específicas
    "site:dof.gob.mx \"inteligencia artificial\" acuerdo decreto lineamiento educación",
    "site:dof.gob.mx \"inteligencia artificial\" estrategia nacional ENIA 2023 2024 2025",
    "DOF México \"inteligencia artificial\" educación norma acuerdo secretaría",
    "dof.gob.mx SEP inteligencia artificial lineamientos educación superior México",
    # Repositorios universitarios de acceso abierto
    "site:repositorio.unam.mx \"inteligencia artificial\" política lineamiento reglamento",
    "site:repositoriodigital.ipn.mx \"inteligencia artificial\" normativa protocolo",
    "repositorio universitario México \"inteligencia artificial\" lineamiento política institucional filetype:pdf",
    # Transparencia institucional
    "site:inai.org.mx \"inteligencia artificial\" lineamientos transparencia normativa",
    "site:portaltransparencia.gob.mx \"inteligencia artificial\" acuerdo norma",
    "site:sep.gob.mx \"inteligencia artificial\" acuerdo lineamiento normateca",
    "site:conahcyt.mx \"inteligencia artificial\" programa estrategia normativa decreto",
    # Organismos reguladores y policy
    "site:ift.org.mx \"inteligencia artificial\" regulación lineamiento acuerdo",
    "site:inegi.org.mx \"inteligencia artificial\" lineamiento normativa estadística",
    "México ENIA estrategia nacional inteligencia artificial educación superior lineamientos",
    "México iniciativa ley inteligencia artificial educación superior congreso",
]

# ─── DOF búsqueda directa ─────────────────────────────────────────────────────
# Búsqueda directa al buscador del Diario Oficial de la Federación vía HTTP
DOF_DIRECT_SEARCH_ENABLED = True
DOF_SEARCH_BASE_URL = "https://dof.gob.mx/busqueda_detalle.php"
DOF_SEARCH_TERMS = [
    "inteligencia artificial educación",
    "inteligencia artificial lineamiento",
    "inteligencia artificial decreto",
    "inteligencia artificial estrategia",
    "ENIA inteligencia artificial",
    "inteligencia artificial universidades",
]
DOF_SEARCH_YEAR_START = "2018-01-01"
DOF_SEARCH_MAX_RESULTS = 30

# ─── Repositorios universitarios de acceso abierto ──────────────────────────
UNIVERSITY_REPOSITORIES = [
    "https://repositorio.unam.mx",
    "https://repositoriodigital.ipn.mx",
    "https://repositorio.tec.mx",
    "https://repositorio.udg.mx",
]
UNIVERSITY_REPO_DDG_QUERIES = [
    'site:repositorio.unam.mx "inteligencia artificial" lineamiento OR reglamento OR política',
    'site:repositoriodigital.ipn.mx "inteligencia artificial" normativa OR protocolo',
]

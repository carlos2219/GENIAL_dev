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
OPENAI_MAX_TOKENS = 900
OPENAI_INPUT_CHARS = 5500

# Ampliación controlada de cobertura IA para documentos borderline
AI_INCLUDE_BORDERLINE_BAJA = True
AI_BAJA_MIN_SCORE = 0.30          # Umbral mínimo elevado para reducir falsos positivos
AI_BAJA_MIN_URL_PRIORITY = 0.60   # Umbral URL elevado para exigir más señal normativa
AI_MAX_EXTRA_BAJA = 20

# ─── Búsqueda ─────────────────────────────────────────────────────────────────
MAX_RESULTS_PER_QUERY    = 10   # resultados por query DDG
MAX_URLS_PER_UNIVERSITY  = 6    # URLs máx por universidad
MAX_UNIVERSITIES         = None # None = todas; int = límite (útil para testing)
SEARCH_DELAY_SECONDS     = 2.5  # pausa entre búsquedas (evita bloqueos DDG)
MAX_WORKERS              = 4    # hilos paralelos para extracción

# Perfil de sesión larga (enfocado a normativa de IA en México)
DEFINITIVE_RUN_MAX_UNIVERSITIES = 45

# Filtros temáticos para priorizar normativa real y reducir ruido
STRICT_TOPIC_FILTER = True
TOPIC_MUST_INCLUDE_AI = True
TOPIC_MIN_POLICY_HITS = 1

# ─── HTTP ─────────────────────────────────────────────────────────────────────
REQUEST_TIMEOUT   = 20          # segundos
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
HEURISTIC_MEDIUM_THRESHOLD = 0.24

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
]
AI_KEYWORDS = [
    "inteligencia artificial", " ia ", "aprendizaje automático",
    "aprendizaje automatico", "machine learning", "chatgpt",
    "chat gpt", "gpt-", "algoritmo", "modelo de lenguaje",
    "llm", "deep learning", "minería de datos",
    "ia generativa", "sistema de ia", "sistemas de ia",
]

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
    "eluniversal.com.mx", "excelsior.com.mx", "milenio.com",
    "reforma.com", "jornada.com.mx", "infobae.com",
    "expansion.mx", "forbes.com.mx", "animalpolitico.com",
    "blogspot.com", "wordpress.com", "medium.com", "substack.com",
    "slideshare.net", "scribd.com", "academia.edu",
    "researchgate.net", "semanticscholar.org",
}
PRIORITY_URL_KEYWORDS = [
    "normativa", "reglamento", "lineamiento", "politica", "acuerdo",
    "resolucion", "guia", "transparencia", "marco-juridico",
    "marco_juridico", "documentos", "consejo", "estatuto", "decreto",
    "legislacion", "disposicion",
]

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
]
GOVERNMENT_PRIORITY_DOMAINS = [
    ".gob.mx", "dof.gob.mx", "sep.gob.mx", "conahcyt.mx",
    "conacyt.gob.mx",
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
UNIVERSITY_QUERY_TEMPLATES = [
    'site:{domain} "inteligencia artificial" lineamientos OR reglamento OR política OR guía',
    'site:{domain} "uso de IA" OR "uso de inteligencia artificial" académico normativa',
    'site:{domain} inteligencia artificial lineamientos estudiantes docentes',
    'site:{domain} política OR lineamientos "IA generativa" OR "ChatGPT" OR "inteligencia artificial" 2024 2025',
    'site:{domain} "inteligencia artificial" AND (lineamientos OR política OR resolución OR guía)',
    'site:{domain} "IA" (ética OR "uso académico" OR regulación OR pedagógico)',
    'site:{domain} "Integridad académica" OR "Uso de IA generativa" OR "Consejo Universitario" OR "Reglamento de evaluación"',
]

# ─── Búsqueda abierta ─────────────────────────────────────────────────────────
OPEN_SEARCH_QUERIES = [
    "México lineamientos inteligencia artificial educación superior universidad filetype:pdf",
    "México reglamento uso de inteligencia artificial universidad estudiantes docentes filetype:pdf",
    "México acuerdo institucional inteligencia artificial universidad consejo universitario",
    "México política académica IA generativa institución educativa",
    "México guía institucional inteligencia artificial docencia investigación universidad",
    "México código de ética inteligencia artificial universidad",
    "México protocolo uso responsable de inteligencia artificial educación superior",
    "México marco regulatorio inteligencia artificial educación superior",
    "México DOF inteligencia artificial educación lineamientos",
    "México iniciativa ley inteligencia artificial educación superior",
]

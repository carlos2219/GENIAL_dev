"""
config.py — Configuración global del sistema GENIAL
Modifica este archivo para ajustar comportamiento, límites y credenciales.
"""

import os
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

# ─── Rutas ───────────────────────────────────────────────────────────────────
BASE_DIR   = Path(__file__).parent
CSV_PATH   = BASE_DIR / "data" / "listado_universidades_altillo.csv"
OUTPUT_DIR = BASE_DIR / "output"
CACHE_DIR  = BASE_DIR / "cache"
LOG_DIR    = BASE_DIR / "logs"

# Excel con los registros definitivos ya clasificados.
# Si existe, sus URLs se usan como skip-list para no reprocesar documentos.
KNOWN_MATRIX_EXCEL = BASE_DIR / "data" / "Matriz_Normativa_IA_Educacion_LATAM.xlsx"

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
MAX_RESULTS_PER_QUERY    = 10   # resultados por query
MAX_URLS_PER_UNIVERSITY  = 6    # URLs máx por universidad
MAX_UNIVERSITIES         = None  # None = todas las universidades (run completo)
SEARCH_DELAY_SECONDS     = float(os.getenv("SEARCH_DELAY_SECONDS", "0.5"))  # pausa entre búsquedas
GOOGLE_SEARCH_PAUSE      = 2.5  # pausa entre páginas Google scraping (evita rate-limit)
# En VMs de GCP, Google bloquea scraping HTML. Usar GOOGLE_CSE_API_KEY+ID en su lugar,
# o bien poner GOOGLE_AS_PRIMARY=false para forzar DDG-only.
_google_env = os.getenv("GOOGLE_AS_PRIMARY", "true").strip().lower()
GOOGLE_AS_PRIMARY        = _google_env not in ("false", "0", "no")
# Google Custom Search API — funciona desde cualquier IP incluyendo GCP
# Obtener en: https://programmablesearchengine.google.com/ + https://console.cloud.google.com/
GOOGLE_CSE_API_KEY       = os.getenv("GOOGLE_CSE_API_KEY", "")
GOOGLE_CSE_ID            = os.getenv("GOOGLE_CSE_ID", "")
# Brave Search API — busca toda la web, funciona desde GCP, 2000 queries/mes gratis
# Obtener API key en: https://api.search.brave.com/
BRAVE_API_KEY            = os.getenv("BRAVE_API_KEY", "")

# ─── Motor de búsqueda — router y backends ───────────────────────────────────
SERPER_API_KEY         = os.getenv("SERPER_API_KEY", "")
SEARCH_ROUTER_ENABLED  = os.getenv("SEARCH_ROUTER_ENABLED", "true").strip().lower() not in ("false", "0", "no")
SEARCH_PARALLEL_GOV    = os.getenv("SEARCH_PARALLEL_GOV",   "true").strip().lower() not in ("false", "0", "no")
SEARCH_METRICS_ENABLED = os.getenv("SEARCH_METRICS_ENABLED","true").strip().lower() not in ("false", "0", "no")
SEARCH_PROFILE         = os.getenv("SEARCH_PROFILE", "balanced").strip()

# TTL del caché unificado (días) — sobrescritos por _apply_profile() si no se definen en .env
CACHE_TTL_GOV_DAYS     = int(os.getenv("CACHE_TTL_GOV_DAYS",  "7"))
CACHE_TTL_SITE_DAYS    = int(os.getenv("CACHE_TTL_SITE_DAYS", "14"))
CACHE_TTL_OPEN_DAYS    = int(os.getenv("CACHE_TTL_OPEN_DAYS",  "3"))

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

# ─── LATAM extensibility ─────────────────────────────────────────────────────
LATAM_COUNTRIES = {
    "MX": {"tld": ".mx",  "lang": "es", "brave_country": "MX", "serper_gl": "mx"},
    "CO": {"tld": ".co",  "lang": "es", "brave_country": "CO", "serper_gl": "co"},
    "AR": {"tld": ".ar",  "lang": "es", "brave_country": "AR", "serper_gl": "ar"},
    "PE": {"tld": ".pe",  "lang": "es", "brave_country": "PE", "serper_gl": "pe"},
    "CL": {"tld": ".cl",  "lang": "es", "brave_country": "CL", "serper_gl": "cl"},
    "EC": {"tld": ".ec",  "lang": "es", "brave_country": "EC", "serper_gl": "ec"},
    "BR": {"tld": ".br",  "lang": "pt", "brave_country": "BR", "serper_gl": "br"},
}

OFFICIAL_DOMAIN_PATTERNS = {
    "MX": [r"\.gob\.mx$", r"\.edu\.mx$"],
    "CO": [r"\.gov\.co$", r"\.edu\.co$"],
    "AR": [r"\.gob\.ar$", r"\.edu\.ar$"],
    "PE": [r"\.gob\.pe$", r"\.edu\.pe$"],
    "CL": [r"\.gob\.cl$", r"\.edu\.cl$"],
    "EC": [r"\.gob\.ec$", r"\.edu\.ec$"],
    "BR": [r"\.gov\.br$", r"\.edu\.br$"],
}

ACTIVE_COUNTRIES = [c.strip() for c in os.getenv("ACTIVE_COUNTRIES", "MX").split(",")]

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
    # Palabras clave adicionales obligatorias del manual (Fase 3)
    "México \"integridad académica\" \"inteligencia artificial\" universidad lineamiento política",
    "México \"uso de IA generativa\" universidad lineamiento política académica educación superior",
    "México \"reglamento de evaluación\" \"inteligencia artificial\" universidad",
    "México \"uso de IA generativa\" educación superior normativa acuerdo institucional",
    "México \"inteligencia artificial\" \"consejo universitario\" acuerdo resolución reglamento",
    # Diario Oficial de la Federación — queries específicas
    "site:dof.gob.mx \"inteligencia artificial\" acuerdo decreto lineamiento educación",
    "site:dof.gob.mx \"inteligencia artificial\" estrategia nacional ENIA 2023 2024 2025",
    "DOF México \"inteligencia artificial\" educación norma acuerdo secretaría",
    "dof.gob.mx SEP inteligencia artificial lineamientos educación superior México",
    # site: queries para universidades principales — fórmula directa del manual
    "site:unam.mx \"inteligencia artificial\" lineamientos política resolución guía",
    "site:ipn.mx \"inteligencia artificial\" lineamientos política resolución guía",
    "site:tec.mx \"inteligencia artificial\" lineamientos política resolución guía",
    "site:uam.mx \"inteligencia artificial\" lineamientos política resolución guía",
    "site:udg.mx \"inteligencia artificial\" lineamientos política resolución guía",
    "site:uanl.mx \"inteligencia artificial\" lineamientos política resolución guía",
    "site:buap.mx \"inteligencia artificial\" lineamientos política resolución guía",
    "site:uv.mx \"inteligencia artificial\" lineamientos política resolución guía",
    "site:uaslp.mx \"inteligencia artificial\" lineamientos política resolución guía",
    "site:ibero.mx \"inteligencia artificial\" lineamientos política resolución guía",
    "site:uady.mx \"inteligencia artificial\" lineamientos política resolución guía",
    "site:uach.mx \"inteligencia artificial\" lineamientos política resolución guía",
    "site:unison.mx \"inteligencia artificial\" lineamientos política resolución guía",
    "site:colmex.mx \"inteligencia artificial\" lineamientos política resolución guía",
    "site:uaq.mx \"inteligencia artificial\" lineamientos política resolución guía",
    # Búsqueda por nombre de universidad — patrón del manual
    "\"Universidad Nacional Autónoma de México\" México IA ética \"uso académico\" regulación pedagógico",
    "\"Instituto Politécnico Nacional\" México IA ética \"uso académico\" regulación pedagógico",
    "\"Instituto Tecnológico de Monterrey\" México IA ética \"uso académico\" regulación pedagógico",
    "\"Universidad Autónoma Metropolitana\" México IA ética \"uso académico\" regulación pedagógico",
    "\"Universidad de Guadalajara\" México IA ética \"uso académico\" regulación pedagógico",
    "\"Universidad Autónoma de Nuevo León\" México IA ética \"uso académico\" regulación pedagógico",
    "\"Benemérita Universidad Autónoma de Puebla\" México IA ética \"uso académico\" regulación pedagógico",
    "\"Universidad Veracruzana\" México IA ética \"uso académico\" regulación pedagógico",
    "\"Universidad Iberoamericana\" México IA ética \"uso académico\" regulación pedagógico",
    "\"El Colegio de México\" México IA ética \"uso académico\" regulación pedagógico",
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

# ─── Helpers ──────────────────────────────────────────────────────────────────

import re as _re
from urllib.parse import urlparse as _urlparse


def _is_official_url(url: str, country: str = None) -> bool:
    """Returns True if url matches OFFICIAL_DOMAIN_PATTERNS for the given or all active countries."""
    countries = [country] if country else ACTIVE_COUNTRIES
    # Match only against the netloc (host) portion so path doesn't break $-anchored patterns
    try:
        netloc = _urlparse(url).netloc.lower()
    except Exception:
        netloc = url.lower()
    host = netloc or url.lower()
    for c in countries:
        for pat in OFFICIAL_DOMAIN_PATTERNS.get(c, []):
            if _re.search(pat, host):
                return True
    return False


# ─── Execution profiles ───────────────────────────────────────────────────────

_ROUTING_TABLES = {
    "fast": {
        "gov":  {"primary": ["cse"],                  "secondary": "ddg",    "parallel": False},
        "site": {"primary": ["ddg"],                  "secondary": None,     "parallel": False},
        "open": {"primary": ["ddg"],                  "secondary": None,     "parallel": False},
        None:   {"primary": ["cse", "brave", "ddg"],  "secondary": None,     "parallel": False},
    },
    "balanced": {
        "gov":  {"primary": ["cse", "brave"],         "secondary": "serper", "parallel": True},
        "site": {"primary": ["serper"],               "secondary": "ddg",    "parallel": False},
        "open": {"primary": ["brave"],                "secondary": "serper", "parallel": False},
        None:   {"primary": ["cse", "brave", "ddg"],  "secondary": None,     "parallel": False},
    },
    "deep": {
        "gov":  {"primary": ["cse", "brave", "serper"], "secondary": None,   "parallel": True},
        "site": {"primary": ["serper", "ddg"],          "secondary": None,   "parallel": True},
        "open": {"primary": ["brave", "serper"],        "secondary": None,   "parallel": True},
        None:   {"primary": ["cse", "brave", "ddg"],    "secondary": None,   "parallel": False},
    },
}

_PROFILE_DEFAULTS = {
    "fast":     {"CACHE_TTL_GOV_DAYS": 14, "CACHE_TTL_SITE_DAYS": 7,  "CACHE_TTL_OPEN_DAYS": 7,  "MAX_RESULTS_PER_QUERY": 5,  "SEARCH_PARALLEL_GOV": False},
    "balanced": {"CACHE_TTL_GOV_DAYS": 7,  "CACHE_TTL_SITE_DAYS": 14, "CACHE_TTL_OPEN_DAYS": 3,  "MAX_RESULTS_PER_QUERY": 10, "SEARCH_PARALLEL_GOV": True},
    "deep":     {"CACHE_TTL_GOV_DAYS": 1,  "CACHE_TTL_SITE_DAYS": 3,  "CACHE_TTL_OPEN_DAYS": 1,  "MAX_RESULTS_PER_QUERY": 20, "SEARCH_PARALLEL_GOV": True},
}


def _apply_profile(profile_name: str) -> None:
    """Apply execution profile. Env-var-defined values take precedence."""
    global CACHE_TTL_GOV_DAYS, CACHE_TTL_SITE_DAYS, CACHE_TTL_OPEN_DAYS
    global MAX_RESULTS_PER_QUERY, SEARCH_PARALLEL_GOV, ROUTING_TABLE

    defaults = _PROFILE_DEFAULTS.get(profile_name, _PROFILE_DEFAULTS["balanced"])

    if not os.getenv("CACHE_TTL_GOV_DAYS"):
        CACHE_TTL_GOV_DAYS = defaults["CACHE_TTL_GOV_DAYS"]
    if not os.getenv("CACHE_TTL_SITE_DAYS"):
        CACHE_TTL_SITE_DAYS = defaults["CACHE_TTL_SITE_DAYS"]
    if not os.getenv("CACHE_TTL_OPEN_DAYS"):
        CACHE_TTL_OPEN_DAYS = defaults["CACHE_TTL_OPEN_DAYS"]
    if not os.getenv("MAX_RESULTS_PER_QUERY"):
        MAX_RESULTS_PER_QUERY = defaults["MAX_RESULTS_PER_QUERY"]
    if not os.getenv("SEARCH_PARALLEL_GOV"):
        SEARCH_PARALLEL_GOV = defaults["SEARCH_PARALLEL_GOV"]

    ROUTING_TABLE = _ROUTING_TABLES.get(profile_name, _ROUTING_TABLES["balanced"])


ROUTING_TABLE = _ROUTING_TABLES["balanced"]  # default; overwritten by _apply_profile
_apply_profile(SEARCH_PROFILE)

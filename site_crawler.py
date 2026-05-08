"""
site_crawler.py — Crawling interno de sitios universitarios y gubernamentales

Para cada dominio:
  1. Prueba rutas conocidas (/normativa, /reglamentos, etc.)
    2. Parsea el HTML de esas rutas (y de la raíz) en busca de enlaces relevantes
    3. No usa buscador interno del sitio ni recorre múltiples niveles de navegación
"""

import logging
import random
import time
import warnings
from typing import List, Dict, Set, Optional
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from urllib3.exceptions import InsecureRequestWarning

import config
from url_filter import is_excluded, looks_normative, is_pdf_url

logger = logging.getLogger(__name__)

_LINK_KEYWORDS = (
    config.PRIORITY_URL_KEYWORDS +
    ["inteligencia artificial", " ia ", "lineamiento", "reglamento",
     "normativa", "politica", "acuerdo", "resolucion", "guia", "estatuto"]
)


def _make_headers() -> dict:
    return {
        "User-Agent": random.choice(config.USER_AGENTS),
        "Accept-Language": "es-MX,es;q=0.9,en;q=0.8",
        "Accept": "text/html,application/pdf,*/*;q=0.8",
    }


def _fetch_html(url: str, timeout: int = config.REQUEST_TIMEOUT) -> Optional[bytes]:
    """Descarga HTML con manejo de errores y SSL flexible."""
    for verify in [True, False]:
        try:
            if verify:
                resp = requests.get(
                    url,
                    headers=_make_headers(),
                    timeout=timeout,
                    allow_redirects=True,
                    verify=True,
                )
            else:
                # Solo en fallback SSL: ocultar warning de certificado no verificado
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore", InsecureRequestWarning)
                    resp = requests.get(
                        url,
                        headers=_make_headers(),
                        timeout=timeout,
                        allow_redirects=True,
                        verify=False,
                    )
            if resp.status_code == 200:
                ct = resp.headers.get("Content-Type", "")
                if "html" in ct or not ct:
                    return resp.content
                return None
        except requests.exceptions.SSLError:
            if not verify:
                return None
            continue
        except Exception as e:
            logger.debug(f"[crawler] fetch error {url}: {e}")
            return None
    return None


def _extract_links(html: bytes, base_url: str) -> List[Dict]:
    """
    Extrae enlaces relevantes de una página HTML.
    Retorna lista de dicts {url, title, is_pdf}.
    """
    links: List[Dict] = []
    try:
        soup = BeautifulSoup(html, "html.parser")
        for a in soup.find_all("a", href=True):
            href = a["href"].strip()
            if not href or href.startswith("#") or href.startswith("mailto:"):
                continue
            full_url = urljoin(base_url, href)
            # Solo mismo dominio o subdominios
            if urlparse(full_url).netloc != urlparse(base_url).netloc:
                # Permitir PDFs externos en el mismo dominio raíz
                base_root = ".".join(urlparse(base_url).netloc.split(".")[-2:])
                link_root = ".".join(urlparse(full_url).netloc.split(".")[-2:])
                if base_root != link_root:
                    continue
            if is_excluded(full_url):
                continue
            title = a.get_text(strip=True)[:200] or ""
            links.append({
                "url": full_url,
                "title": title,
                "is_pdf": is_pdf_url(full_url),
            })
    except Exception as e:
        logger.debug(f"[crawler] parse error {base_url}: {e}")
    return links


def _is_relevant_link(link: Dict) -> bool:
    """¿El enlace parece ser un documento normativo o de IA?"""
    combined = (link.get("url", "") + " " + link.get("title", "")).lower()
    has_normative = any(kw in combined for kw in _LINK_KEYWORDS)
    has_ai = any(kw in combined for kw in config.AI_KEYWORDS)
    return link.get("is_pdf") or has_normative or has_ai


def crawl_domain(
    domain: str,
    university_name: str = "",
    source_type: str = "university",
    max_docs: int = config.MAX_URLS_PER_UNIVERSITY,
    max_seconds: int = 60,
    paths: Optional[List[str]] = None,
) -> List[Dict]:
    """
    Rastrea un dominio universitario/gubernamental con heurísticas acotadas.

    1. Prueba rutas conocidas de UNIVERSITY_CRAWL_PATHS
    2. Por cada ruta accesible, extrae enlaces relevantes
    3. Revisa también la página raíz para extraer enlaces relevantes

    Retorna lista de documentos pre-poblados (sin texto extraído aún).
    No utiliza buscador interno ni exploración exhaustiva del sitio.
    El crawl se detiene si supera max_seconds (default 60s).
    """
    found: List[Dict] = []
    seen_urls: Set[str] = set()
    crawl_start = time.time()

    # Normalizar dominio; preservar la ruta semilla si viene en el URL
    if not domain.startswith("http"):
        base_url = f"https://{domain}"
        seed_path = "/"
    else:
        parsed = urlparse(domain)
        base_url = f"{parsed.scheme}://{parsed.netloc}"
        seed_path = parsed.path.rstrip("/") or "/"

    logger.info(f"[crawler] Crawleando {base_url} ({university_name})")

    def _add_doc(url: str, title: str, source_path: str):
        nonlocal found
        if url in seen_urls or len(found) >= max_docs * 3:
            return
        seen_urls.add(url)
        found.append({
            "url": url,
            "title": title,
            "snippet": f"Encontrado en crawl de {source_path}",
            "source_type": source_type,
            "university_name": university_name,
            "university_domain": domain,
            "query_used": f"crawl:{source_path}",
            "extracted_text": "",
            "extraction_error": None,
            "heuristic_score": 0.0,
            "heuristic_label": "BAJA",
            "ai_classification": None,
        })

    # Si la URL semilla tenía una ruta específica, anteponerla a las rutas a probar
    # Si se pasan paths explícitos (ej: NON_PRIORITY_CRAWL_PATHS), usarlos en lugar del default.
    base_paths = paths if paths is not None else list(config.UNIVERSITY_CRAWL_PATHS)
    extra_paths = [seed_path] if seed_path and seed_path != "/" and seed_path not in base_paths else []
    crawl_paths = extra_paths + base_paths

    # Fase 1: Intentar rutas conocidas
    for path in crawl_paths:
        if len(found) >= max_docs * 3:
            break

        # Timeout global del crawl
        if time.time() - crawl_start > max_seconds:
            logger.warning(f"[crawler] Timeout ({max_seconds}s) alcanzado para {university_name} — abortando crawl")
            break

        candidate = base_url.rstrip("/") + path
        logger.debug(f"[crawler] Probando ruta: {candidate}")

        html = _fetch_html(candidate)
        if not html:
            time.sleep(0.3)
            continue

        # Agregar la propia página si contiene palabras normativas
        if looks_normative(candidate, path):
            _add_doc(candidate, f"Normativa — {path}", path)

        # Extraer enlaces de la página
        links = _extract_links(html, candidate)
        for link in links:
            if _is_relevant_link(link):
                _add_doc(link["url"], link["title"], path)

        time.sleep(0.5)

    # Fase 2: Página raíz y página semilla (buscar sección de normativa)
    pages_to_scan = [base_url]
    if seed_path and seed_path != "/":
        seed_full_url = base_url.rstrip("/") + seed_path
        if seed_full_url not in seen_urls:
            pages_to_scan.append(seed_full_url)

    for scan_url in pages_to_scan:
        if len(found) >= max_docs or (time.time() - crawl_start) >= max_seconds:
            break
        root_html = _fetch_html(scan_url)
        if root_html:
            root_links = _extract_links(root_html, scan_url)
            for link in root_links:
                if _is_relevant_link(link) and len(found) < max_docs * 3:
                    _add_doc(link["url"], link["title"], scan_url)

    logger.info(f"[crawler] {university_name}: {len(found)} URLs encontradas")
    return found[:max_docs * 3]


def crawl_multiple_domains(
    university_records: List[Dict],
    max_workers: int = config.MAX_WORKERS,
) -> List[Dict]:
    """
    Crawlea múltiples universidades en paralelo.
    university_records: lista de dicts con "url_oficial" y "universidad".
    """
    from concurrent.futures import ThreadPoolExecutor, as_completed

    all_docs: List[Dict] = []

    def _crawl_one(record: Dict) -> List[Dict]:
        url = record.get("url_oficial", "")
        name = record.get("universidad", "")
        if not url:
            return []
        try:
            parsed = urlparse(url)
            domain = f"{parsed.scheme}://{parsed.netloc}"
            return crawl_domain(domain, name)
        except Exception as e:
            logger.warning(f"[crawler] Error crawleando {name}: {e}")
            return []

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(_crawl_one, r): r for r in university_records}
        for future in as_completed(futures):
            try:
                docs = future.result()
                all_docs.extend(docs)
            except Exception as e:
                logger.error(f"[crawler] Excepción: {e}")

    return all_docs

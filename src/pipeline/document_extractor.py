"""
document_extractor.py — Extracción de contenido desde HTML y PDF

Descarga el documento en la URL dada y extrae texto limpio.
Maneja PDFs (digitales y escaneados), HTML y errores de red.
"""

import io
import logging
import random
import re
import time
from typing import Dict, Optional
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

import config

logger = logging.getLogger(__name__)

# pdfplumber es opcional (mejor para PDFs complejos)
try:
    import pdfplumber
    _HAS_PDFPLUMBER = True
except ImportError:
    _HAS_PDFPLUMBER = False

# PyPDF2 como fallback
try:
    from PyPDF2 import PdfReader
    _HAS_PYPDF2 = True
except ImportError:
    try:
        from pypdf import PdfReader
        _HAS_PYPDF2 = True
    except ImportError:
        _HAS_PYPDF2 = False


# ─── Sesión HTTP ──────────────────────────────────────────────────────────────

def _make_session() -> requests.Session:
    session = requests.Session()
    session.headers.update({
        "User-Agent": random.choice(config.USER_AGENTS),
        "Accept-Language": "es-MX,es;q=0.9,en;q=0.8",
        "Accept": "text/html,application/xhtml+xml,application/pdf,*/*;q=0.8",
    })
    return session


import threading
_thread_local = threading.local()


def _get_session() -> requests.Session:
    """Retorna una sesión HTTP por hilo (thread-safe)."""
    if not hasattr(_thread_local, "session"):
        _thread_local.session = _make_session()
    return _thread_local.session


def _reset_session():
    _thread_local.session = _make_session()


# ─── Extracción HTML ──────────────────────────────────────────────────────────

def _extract_html(content: bytes, url: str) -> str:
    """Extrae texto limpio de contenido HTML."""
    try:
        soup = BeautifulSoup(content, "html.parser")
        # Eliminar scripts, estilos, nav, footer
        for tag in soup(["script", "style", "nav", "footer", "header",
                          "aside", "form", "iframe", "noscript"]):
            tag.decompose()

        # Intentar extraer contenido principal
        main = (
            soup.find("main") or
            soup.find("article") or
            soup.find(id=re.compile(r"(content|main|body|article)", re.I)) or
            soup.find(class_=re.compile(r"(content|main|body|article)", re.I)) or
            soup.body or
            soup
        )
        text = main.get_text(separator="\n", strip=True) if main else soup.get_text(separator="\n", strip=True)

        # Limpiar líneas vacías múltiples
        import re
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text[:config.MAX_TEXT_CHARS_HTML]
    except Exception as e:
        logger.debug(f"[extract_html] error parsing {url}: {e}")
        return ""


# ─── Extracción PDF ───────────────────────────────────────────────────────────

def _extract_pdf_bytes(pdf_bytes: bytes, url: str) -> str:
    """Extrae texto de bytes de PDF. Intenta pdfplumber primero, luego PyPDF2."""
    text = ""

    if _HAS_PDFPLUMBER:
        try:
            with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
                pages_text = []
                for page in pdf.pages[:40]:  # máx 40 páginas
                    t = page.extract_text()
                    if t:
                        pages_text.append(t)
                text = "\n".join(pages_text)
        except Exception as e:
            logger.debug(f"[pdfplumber] error {url}: {e}")

    if not text and _HAS_PYPDF2:
        try:
            reader = PdfReader(io.BytesIO(pdf_bytes))
            pages_text = []
            for page in reader.pages[:40]:
                t = page.extract_text()
                if t:
                    pages_text.append(t)
            text = "\n".join(pages_text)
        except Exception as e:
            logger.debug(f"[pypdf2] error {url}: {e}")

    if not text:
        # PDF escaneado o sin texto extraíble
        logger.debug(f"[pdf] sin texto extraíble (posible escaneado): {url}")
        return "[PDF escaneado o sin texto extraíble]"

    import re
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text[:config.MAX_TEXT_CHARS_PDF]


# ─── Extractor principal ──────────────────────────────────────────────────────

def extract_document(url: str, retries: int = 2) -> Dict:
    """
    Descarga y extrae contenido de una URL.

    Retorna dict con:
      - url
      - content_type: "html" | "pdf" | "unknown"
      - extracted_text: str (vacío si error)
      - extraction_error: str | None
      - title: str (de la página si es HTML)
      - response_url: URL final (tras redirecciones)
    """
    result: Dict = {
        "url": url,
        "content_type": "unknown",
        "extracted_text": "",
        "extraction_error": None,
        "title": "",
        "response_url": url,
    }

    import re

    for attempt in range(retries + 1):
        try:
            # Detectar PDF por URL antes de descargar
            url_lower = url.lower().split("?")[0]
            is_pdf_url = url_lower.endswith(".pdf")

            response = _get_session().get(
                url,
                timeout=config.REQUEST_TIMEOUT,
                stream=True,
                allow_redirects=True,
            )
            response.raise_for_status()
            result["response_url"] = response.url

            content_type_header = response.headers.get("Content-Type", "").lower()
            is_pdf = is_pdf_url or "pdf" in content_type_header

            # Verificar tamaño antes de descargar todo
            content_length = response.headers.get("Content-Length")
            if content_length:
                size_mb = int(content_length) / (1024 * 1024)
                if size_mb > config.MAX_PDF_SIZE_MB:
                    result["extraction_error"] = f"Archivo demasiado grande ({size_mb:.1f} MB)"
                    return result

            content = response.content

            if is_pdf:
                result["content_type"] = "pdf"
                result["extracted_text"] = _extract_pdf_bytes(content, url)
                result["title"] = _guess_title_from_url(url)
            else:
                result["content_type"] = "html"
                result["extracted_text"] = _extract_html(content, url)
                # Intentar obtener título de la página
                try:
                    soup = BeautifulSoup(content, "html.parser")
                    if soup.title:
                        result["title"] = soup.title.get_text(strip=True)[:300]
                except Exception:
                    result["title"] = _guess_title_from_url(url)

            return result

        except requests.exceptions.Timeout:
            if attempt < retries:
                time.sleep(1.5 * (attempt + 1))
                _reset_session()
                continue
            result["extraction_error"] = "Timeout"
            return result

        except requests.exceptions.TooManyRedirects:
            result["extraction_error"] = "Demasiadas redirecciones"
            return result

        except requests.exceptions.SSLError:
            # Reintentar sin verificación SSL (solo para dominios .edu.mx)
            try:
                import warnings
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore")
                    response = requests.get(
                        url, timeout=config.REQUEST_TIMEOUT,
                        verify=False, allow_redirects=True,
                        headers={"User-Agent": random.choice(config.USER_AGENTS)},
                    )
                    response.raise_for_status()
                    result["response_url"] = response.url
                    content = response.content
                    ct = response.headers.get("Content-Type", "").lower()
                    if "pdf" in ct or url.lower().endswith(".pdf"):
                        result["content_type"] = "pdf"
                        result["extracted_text"] = _extract_pdf_bytes(content, url)
                        result["title"] = _guess_title_from_url(url)
                    else:
                        result["content_type"] = "html"
                        result["extracted_text"] = _extract_html(content, url)
                        try:
                            soup = BeautifulSoup(content, "html.parser")
                            if soup.title:
                                result["title"] = soup.title.get_text(strip=True)[:300]
                        except Exception:
                            result["title"] = _guess_title_from_url(url)
                    return result
            except Exception as ssl_e:
                result["extraction_error"] = f"SSL error: {ssl_e}"
                return result

        except requests.exceptions.RequestException as e:
            if attempt < retries:
                time.sleep(1.5 * (attempt + 1))
                _reset_session()
                continue
            result["extraction_error"] = str(e)[:200]
            return result

        except Exception as e:
            result["extraction_error"] = f"Error inesperado: {str(e)[:200]}"
            return result

    return result


def _guess_title_from_url(url: str) -> str:
    """Infiere un título desde la URL cuando no hay otra fuente."""
    try:
        path = urlparse(url).path
        parts = [p for p in path.split("/") if p]
        if parts:
            name = parts[-1]
            name = name.replace("-", " ").replace("_", " ")
            name = name.replace(".pdf", "").replace(".html", "")
            return name[:200].title()
    except Exception:
        pass
    return url[:100]

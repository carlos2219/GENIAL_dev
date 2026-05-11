"""
download_pdfs.py
----------------
Lee la columna "URL Oficial" del archivo Matriz_Normativa_IA_Educacion_LATAM.xlsx,
descarga los PDFs disponibles y los empaqueta en documentos_pdfs.zip.

Uso:
    python download_pdfs.py [--xlsx ruta/al/archivo.xlsx] [--output documentos_pdfs.zip]
"""

import argparse
import io
import re
import shutil
import sys
import time
import zipfile
from pathlib import Path
from urllib.parse import unquote, urlparse

import urllib3

import pandas as pd
import requests

# Forzar UTF-8 en stdout para soportar caracteres fuera de cp1252 (Windows)
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# Sitios del gobierno MX usan cadenas de certificados no incluidas en certifi.
# Se desactiva la verificación SSL solo para esta herramienta de descarga offline.
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ---------------------------------------------------------------------------
# Configuración
# ---------------------------------------------------------------------------
DEFAULT_XLSX = "Matriz_Normativa_IA_Educacion_LATAM.xlsx"
DEFAULT_ZIP  = "documentos_pdfs.zip"
URL_COLUMN   = "URL Oficial"
TITLE_COLUMN = "Título de la Norma"
TIMEOUT      = 20          # segundos por solicitud
DELAY        = 1.0         # segundos entre descargas (evita rate-limiting)
MAX_RETRIES  = 2

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; GENIAL-PDF-Downloader/1.0; "
        "+https://github.com/GENIAL-project)"
    )
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def slugify(text: str, max_len: int = 80) -> str:
    """Convierte texto a nombre de archivo seguro."""
    text = unquote(str(text))
    text = re.sub(r"[^\w\s\-]", "", text, flags=re.UNICODE)
    text = re.sub(r"[\s]+", "_", text.strip())
    return text[:max_len] if text else "documento"


def is_pdf_url(url: str) -> bool:
    """Heurística rápida: el path de la URL termina en .pdf."""
    path = urlparse(url).path.lower()
    return path.endswith(".pdf")


def fetch_pdf(url: str) -> bytes | None:
    """
    Descarga una URL. Devuelve bytes si el Content-Type es application/pdf,
    None en caso contrario o ante error.
    """
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = requests.get(
                url, headers=HEADERS, timeout=TIMEOUT,
                allow_redirects=True, stream=True, verify=False
            )
            resp.raise_for_status()
            ct = resp.headers.get("Content-Type", "")
            if "pdf" not in ct.lower():
                return None
            buf = io.BytesIO()
            for chunk in resp.iter_content(chunk_size=8192):
                buf.write(chunk)
            return buf.getvalue()
        except requests.exceptions.RequestException as exc:
            if attempt < MAX_RETRIES:
                time.sleep(DELAY * attempt)
            else:
                print(f"      X Error tras {MAX_RETRIES} intentos: {exc}")
                return None
    return None


def unique_name(used: set[str], base: str) -> str:
    """Garantiza nombres únicos dentro del ZIP."""
    name = f"{base}.pdf"
    if name not in used:
        used.add(name)
        return name
    i = 2
    while True:
        name = f"{base}_{i}.pdf"
        if name not in used:
            used.add(name)
            return name
        i += 1


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Descarga PDFs desde la columna URL Oficial.")
    parser.add_argument("--xlsx",   default=DEFAULT_XLSX, help="Ruta al archivo Excel de la matriz.")
    parser.add_argument("--output", default=DEFAULT_ZIP,  help="Ruta del ZIP de salida.")
    args = parser.parse_args()

    xlsx_path = Path(args.xlsx)
    zip_path  = Path(args.output)

    if not xlsx_path.exists():
        sys.exit(f"ERROR: No se encontró el archivo '{xlsx_path}'.")

    # Leer matriz
    print(f"Leyendo: {xlsx_path}")
    df = pd.read_excel(xlsx_path)

    if URL_COLUMN not in df.columns:
        sys.exit(f"ERROR: No existe la columna '{URL_COLUMN}' en el Excel.")

    rows = df[[URL_COLUMN, TITLE_COLUMN]].dropna(subset=[URL_COLUMN]).copy()
    rows[URL_COLUMN]   = rows[URL_COLUMN].astype(str).str.strip()
    rows[TITLE_COLUMN] = rows[TITLE_COLUMN].fillna("").astype(str).str.strip()

    total = len(rows)
    print(f"URLs encontradas: {total}\n")

    downloaded = 0
    skipped    = 0
    failed     = 0
    used_names: set[str] = set()

    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for idx, (_, row) in enumerate(rows.iterrows(), start=1):
            url   = str(row[URL_COLUMN]).strip()
            title = str(row[TITLE_COLUMN]).strip()

            print(f"[{idx}/{total}] {url[:90]}")

            # Saltar si no parece PDF ni siquiera por heurística
            if not is_pdf_url(url):
                # Intentar igualmente via HEAD para detectar PDFs sin extensión
                try:
                    head = requests.head(
                        url, headers=HEADERS, timeout=TIMEOUT,
                        allow_redirects=True, verify=False
                    )
                    ct = head.headers.get("Content-Type", "")
                    if "pdf" not in ct.lower():
                        print("      -> No es PDF, omitido.")
                        skipped += 1
                        time.sleep(0.2)
                        continue
                except requests.exceptions.RequestException:
                    print("      -> No accesible, omitido.")
                    skipped += 1
                    continue

            data = fetch_pdf(url)
            if data is None:
                failed += 1
                time.sleep(DELAY)
                continue

            base = slugify(title) if title else slugify(urlparse(url).path.split("/")[-1])
            arc_name = unique_name(used_names, base)
            zf.writestr(arc_name, data)
            print(f"      OK Guardado como '{arc_name}' ({len(data)//1024} KB)")
            downloaded += 1
            time.sleep(DELAY)

    print(f"\n{'='*60}")
    print(f"Descargados : {downloaded}")
    print(f"Omitidos    : {skipped}  (no son PDF)")
    print(f"Fallidos    : {failed}")
    print(f"ZIP creado  : {zip_path.resolve()}")


if __name__ == "__main__":
    main()

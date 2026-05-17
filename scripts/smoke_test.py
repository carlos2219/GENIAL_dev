"""smoke_test.py — Quick backend validation before extended session."""
import sys
sys.path.insert(0, ".")

import config
from src.pipeline.search_backends import _google_cse_search, _brave_search, _ddg_search

query = "Mexico inteligencia artificial educacion lineamientos"

def test_backend(name, fn, q, n=3):
    try:
        r = fn(q, n)
        url = (r[0].get("url") or r[0].get("href", "")) if r else ""
        print(f"  {name}: OK — {len(r)} resultados | {url[:70]}")
    except Exception as e:
        print(f"  {name}: ERROR — {e}")

from src.pipeline.search_backends import _serper_search

print("=== Smoke Test de Backends ===")
test_backend("CSE",    _google_cse_search, query)
test_backend("Brave",  _brave_search, query)
test_backend("Serper", _serper_search, query)
test_backend("DDG",    _ddg_search, query)

print()
print(f"  SERPER_API_KEY: {'OK - configurada' if config.SERPER_API_KEY else 'FALTA — no configurada'}")
print(f"  SEARCH_PROFILE activo: {config.SEARCH_PROFILE}")
print(f"  ROUTING_TABLE[site]: {config.ROUTING_TABLE.get('site')}")

---
name: project-cleanup
description: Remove stale tracked artifacts and reorganize utility scripts for a clean repo state
metadata:
  type: project
---

# Project Cleanup Design

**Date:** 2026-05-15  
**Goal:** Remove files that should never have been committed, untrack run artifacts already covered by `.gitignore`, and move a misplaced utility script.

---

## Problem

Three categories of files are incorrectly tracked in git:

1. **Run-time logs** (`logs/`) — 21 pipeline log files committed before `logs/` was added to `.gitignore`. They are ephemeral run artifacts with no value in version history.

2. **Output spreadsheets** (`output/normativa_ia_mexico_*.xlsx`) — 11 dated pipeline output files committed before `output/` and `*.xlsx` were added to `.gitignore`. They are regenerable run artifacts.

3. **Stale root `__pycache__/`** — 13 compiled `.pyc` files pointing to module paths that no longer exist at the project root. These were left behind after commit `b4e2fbf` moved all pipeline modules from root to `src/pipeline/`. They are dead weight and already covered by `__pycache__/` in `.gitignore`.

Additionally, `download_pdfs.py` lives at the project root despite being a standalone utility with no connection to `main.py`. The `scripts/` directory exists specifically for this kind of file.

---

## Changes

### Category 1 — Untrack from git, keep on disk

| Path | Count | Reason |
|------|-------|--------|
| `logs/*.log` | 20 files | Run artifacts, already in `.gitignore` |
| `logs/sesion_completa.txt` | 1 file | Run artifact, already in `.gitignore` |
| `output/normativa_ia_mexico_*.xlsx` | 11 files | Run artifacts, already in `.gitignore` |

**Mechanism:** `git rm --cached` — removes from git index, leaves files on disk.

### Category 2 — Untrack from git AND delete from disk

| Path | Count | Reason |
|------|-------|--------|
| `__pycache__/*.pyc` | 13 files | Stale bytecode from deleted root modules, already in `.gitignore` |

**Mechanism:** `git rm -rf __pycache__/` — removes from git index and deletes files from disk.

### Category 3 — Move file

| From | To |
|------|----|
| `download_pdfs.py` | `scripts/download_pdfs.py` |

**Mechanism:** `git mv download_pdfs.py scripts/download_pdfs.py` — preserves git history for the file.

---

## What Stays Untouched

- All `src/pipeline/` source modules
- `main.py`, `config.py`, `requirements.txt`
- `data/`, `docs/`, `tests/`, `reference/`, `reportes/`
- `.gitignore`, `.env.example`, `LICENSE`, `README.md`, `PROPOSITO_PROYECTO_MANUAL.md`
- `scripts/run_vm.sh`, `.github/` agents and skills
- `output/checkpoints/`, `output/documentos_procesados.json` (untracked, stay untracked)
- `cache/` directory (untracked, stays untracked)

---

## Success Criteria

- `git ls-files` shows no files under `logs/`, `output/*.xlsx`, or root `__pycache__/`
- `download_pdfs.py` no longer exists at root; `scripts/download_pdfs.py` does
- `git status` is clean after the commit
- All `src/pipeline/` modules, `main.py`, and `config.py` remain intact and importable

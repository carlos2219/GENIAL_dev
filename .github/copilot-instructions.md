# GENIAL Project Guidelines

## Scope & Restrictions

**This project is restricted to Mexico only.**
- Only include regulations, policies, lineamientos, decretos, leyes, guías éticas, estrategias, or equivalent institutional instruments.
- Emit from Mexican government entities or Mexican universities only.
- Do not include results from other countries in the final matrix.
- Do not include companies, private vendors, consultants, blogs, news sites, media articles, opinion pages, or non-official informational pages.

## Quality & Classification Priorities

- **Precision over recall**: Stricter filtering reduces manual cleanup.
- **Fix root causes, not symptoms**: Detect which pipeline stage introduces noise and fix there, not in post-processing.
- **Explicit AI evidence required**: A document must mention inteligencia artificial, IA, máquina learning, algoritmo or closely related concept explicitly.
  - Do not include documents that only indirectly resemble AI governance.
  - Do not justify inclusion with phrases like "aunque no menciona IA directamente".
- **Taxonomy strictly from the manual**: Only use norm types, domains, states, vinculos and ámbitos defined in the investigator's manual.
  - Never introduce "mixto" as a final domain category.
  - Never use categories outside the approved list.
- **Dates: prefer absence over uncertainty**: If a date cannot be validated with confidence, use "No Indica".
  - Do not guess, infer, or allow AI to hallucinate dates without evidence.

## Pipeline Architecture

The current pipeline has 10 phases (see main.py):
1. Government search (Fase 1)
2. University search (Fase 2) — currently external domain queries + heuristic crawling, not true internal-site search
3. Open search (Fase 3)
4. Pre-extraction deduplication
5. Content extraction (parallel)
6. Heuristic classification
7. Post-extraction deduplication
8. AI classification (ALTA/MEDIA only, or BAJA with high URL/heuristic scores if configured)
9. Matrix building
10. Excel export

**Do not describe Fase 2 as implementing a real internal site searcher unless you have actually implemented one.** The current approach is external queries with site: operators plus heuristic URL/link extraction. This is valid for efficiency but not equivalent to filling a form on each university's internal search box.

## Critical Patterns to Preserve

- **Dual-classification fallback**: If API is unavailable, system falls back to heuristic-only mode with matrix restricted to ALTA documents. Do not simplify this logic.
- **Two-phase deduplication**: Pre-extraction deduplication works on URLs; post-extraction deduplication works on content. Both serve distinct purposes. Do not consolidate them.
- **Researcher/Country coupling**: The researcher name and country are coupled in config.py and must remain Mexico-exclusive. Do not introduce dynamic country selection without explicit architecture changes and validation.
- **No hardcoded credentials**: The OPENAI_API_KEY is environment-based. Never hardcode, cache, or log it.

## Validation Rules

Before documents enter the final matrix:
1. Source must be official (government .gob.mx domain or verified Mexican university .edu.mx).
2. Document must mention IA/AI explicitly and centrally (not tangentially).
3. Taxonomy values must match the manual exactly.
4. Date must be validated or left as "No Indica".
5. Dominio must resolve to a single valid category, never "mixto".

## When Working on This Project

- Cite the project manual and PROPOSITO_PROYECTO_MANUAL.md when establishing rules.
- Reference main.py, config.py, and actual module implementations—do not invent behaviors that don't exist.
- When fixing issues, trace the problem to its origin stage and fix the root cause.
- Test focused changes; validate against the pipeline end-to-end only when integration matters.

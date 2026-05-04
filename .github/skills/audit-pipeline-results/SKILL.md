---
name: audit-pipeline-results
description: "Audit GENIAL pipeline outputs and identify false positives, noisy stages, weak filters, and poor classification decisions. Use when reviewing output Excel, processed JSON, logs, heuristic performance issues, AI misclassification, post-run quality problems, or understanding why cleanup was needed."
---

# Audit Pipeline Results

## When to Use

- The Excel output needs significant manual cleanup.
- You want to know which pipeline stage is introducing the most false positives.
- Heuristic classification seems ineffective or misleading.
- AI classification is allowing weak or irrelevant results.
- A completed run produced too much noise.
- You need to diagnose why official-source or country filtering failed.
- You want to understand the distribution of data quality issues.

## Objectives

- Trace false positives back to the pipeline stage that should have caught them.
- Distinguish root-cause systematic issues from isolated examples.
- Identify the highest-leverage fixes first (biggest impact for effort).
- Group errors by pattern to recommend prioritized improvements.

## Procedure

1. **Collect the run outputs**:
   - Final matrix (Excel)
   - Processed-documents.json (if available)
   - Latest pipeline log file in logs/

2. **Sample false positives from the matrix** (10-20 examples):
   - Pick documents that should not be there.
   - Check whether they violate Mexico-only scope, official-source requirement, explicit-AI requirement, or taxonomy rules.

3. **Categorize errors by pattern**:
   - **Non-Mexico**: document from .co, .ve, .pe, .es, .gt or other non-Mexico domain; foreign university; or content not about Mexico.
   - **Unofficial source**: company, vendor, consultant, blog, media, news site, or non-institutional page.
   - **No explicit IA mention**: document is about education policy or general governance but doesn't mention IA/AI/machine-learning/algoritmo explicitly.
   - **Invalid taxonomy**: norm type, domain, state, vínculo, or ámbito not in the manual; or "mixto" appearing as final domain.
   - **Unreliable or guessed date**: date appears invented, inferred, or obtained from a weak signal.
   - **Off-topic or stale**: document predates the AI era (pre-2020) or is tangentially related but not about AI governance in education.

4. **Map each error pattern to responsible pipeline stage**:
   - Non-Mexico leakage → likely government_search, university_search, open_search query/seed design or url_filter.
   - Unofficial sources → likely is_excluded() or document_classifier heuristics.
   - No explicit IA → likely heuristic or AI classification thresholds.
   - Invalid taxonomy → likely ai_classifier schema or matrix_builder mapping.
   - Bad dates → likely ai_classifier or matrix_builder date extraction.

5. **Count frequency**: How many errors fall into each pattern? Which pattern affects the most records?

6. **Estimate impact**: Which fixes would reduce manual cleanup the most?
   - A single filter fix affecting 30% of errors > a complex AI prompt fix affecting 5%.

7. **Recommend fixes in priority order**:
   - Highest volume + highest leverage first.
   - Include brief justification for each recommendation.

## Output Format

Return:
- **Error patterns** (category, description, example URLs/titles)
- **Frequency** (count and percentage of total false positives)
- **Responsible stages** (which pipeline stage is responsible)
- **Recommended fixes** (prioritized by impact)
  - What to fix
  - Which files/functions
  - Expected impact
- **Residual risks** (errors that may persist even after recommended fixes)
- **Next steps** (if fixes are implemented, suggest re-audit to validate)

## References

- PROPOSITO_PROYECTO_MANUAL.md: project scope and manual taxonomy.
- output/documentos_procesados.json: full document metadata for cross-reference.
- logs/ directory: pipeline execution logs.
- main.py: pipeline architecture and stage sequence.

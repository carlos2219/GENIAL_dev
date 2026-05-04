---
name: validate-mexico-sources
description: "Validate whether pipeline results come from official Mexican sources. Use when filtering non-Mexico domains, excluding private companies, filtering news/media sites, validating government-source status, validating university-source status, implementing country gating, hardening source validation, or reducing noisy results from searches."
---

# Validate Mexico Sources

## When to Use

- Results from other countries (.co, .ve, .pe, .es, .gt, .org, etc.) are appearing in the matrix.
- Private companies or unofficial sites are being included.
- News articles, media pages, or blog-like content survive filtering.
- The pipeline needs stricter official-source validation.
- A search phase (government, university, or open) is too noisy and needs country or issuer gating.
- Documents from non-Mexican universities or government entities are leaking into results.

## Objectives

- Keep only Mexican official sources relevant to the project.
- Exclude non-Mexico pages unless explicitly justified and restricted from the final matrix.
- Exclude private companies, vendors, media, and blog-like content early.
- Prioritize .gob.mx, .edu.mx and curated official institutional Mexican domains.
- Apply validation both early in search phases and late in matrix gating.

## Procedure

1. **Inspect source entry points**: Review queries, seed URLs, and initial filtering in government_search.py, university_search.py, and open_search.py.
2. **Check country inference**: Determine if country is inferred from domain, issuer name, URL path, or text content. Strengthen weak signals.
3. **Add source validation early**: Tighten domain filters, issuer checks, and non-Mexico exclusion patterns before documents reach extraction.
4. **Add source validation late**: Ensure official-source validation exists in matrix_builder.py before rows are finalized—reject low-trust sources even if keyword-rich.
5. **Validate excluded domains**: Review EXCLUDED_DOMAINS in config.py and add patterns for .co, .ve, .pe, .es, .gt and common non-Mexico or private TLDs.
6. **Test edge cases**: Verify that UNESCO.org or CEPAL.org results are only included if they are officially applicable to Mexico and do not contaminate Mexico-only reporting.

## Review Focus

- Search queries and government seed URLs
- Domain allowlist or denylist logic in url_filter.py
- Official issuer inference in matrix_builder.py
- News and private-content exclusion patterns in document_classifier.py and is_excluded()
- Final matrix gating before Excel export
- Edge cases where international organizations are cited but should not appear as a primary source

## References

- See PROPOSITO_PROYECTO_MANUAL.md for country scope and official-source requirements.
- See config.py GOVERNMENT_PRIORITY_DOMAINS and EXCLUDED_DOMAINS.
- See url_filter.py is_excluded() for domain filtering logic.

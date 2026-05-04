---
name: enforce-manual-taxonomy
description: "Enforce the investigator manual taxonomy for the matrix. Use when fixing invalid norm types, removing mixed-domain outputs, normalizing matrix values, validating state/status values, improving date reliability, resolving domain mapping conflicts, or ensuring the final Excel strictly respects the manual."
---

# Enforce Manual Taxonomy

## When to Use

- Output includes categories not allowed by the investigator manual.
- Domain classification uses invalid values (e.g., "mixto" in final output).
- Matrix values drift from the controlled vocabulary defined in PROPOSITO_PROYECTO_MANUAL.md.
- Date extraction is unreliable or filled with guesses.
- AI classification schema allows unsupported types or values.
- Mapping tables in matrix_builder.py use values not in the manual.

## Objectives

- Restrict outputs to manual-approved values only.
- Normalize all final matrix values to controlled vocabulary.
- Map each document to one final domain (no "mixto").
- Prefer "No Indica" over low-confidence dates or guessed values.
- Ensure AI classification schema constraints are enforced.

## Procedure

1. **Review the manual taxonomy**: Reference PROPOSITO_PROYECTO_MANUAL.md sections 5 and 6 for approved values:
   - Tipo de norma: Ley, Decreto, Reglamento, Guía Ética, Estrategia Nacional.
   - Estado: Vigente, En Proyecto, Derogada.
   - Dominio: Pedagógico, Administrativo, Protección de Datos, Ética, Técnico.
   - Vínculo con Educación: Directo, Indirecto.
   - Dedicación del Texto: Articulado completo, Sección/Capítulo, Mención breve.
   - Ámbito: Nacional, Institucional.

2. **Inspect AI classification schema**: Review ai_classifier.py _USER_PROMPT_TEMPLATE for allowed values. Ensure it restricts output to the manual.

3. **Review mapping tables**: Check matrix_builder.py _TIPO_NORMA_MAP, _DOMINIO_MAP, _ESTADO_MAP, etc. Remove unsupported entries (e.g., "libro blanco", "código de ética", "mixto").

4. **Add normalization or rejection logic**: If a document arrives with an unsupported value, either:
   - Map it to a valid fallback (e.g., "mixto" → most relevant domain).
   - Reject it with justification.

5. **Validate date confidence**: Ensure dates either come from reliable sources or are set to "No Indica". Check matrix_builder.py _format_date_for_matrix().

6. **Final matrix row validation**: Before rows are exported, verify every column uses only approved values or explicit absence markers ("No disponible", "No Indica").

## Review Focus

- AI classification schema in ai_classifier.py
- Matrix mapping tables in matrix_builder.py
- Final row validation logic before Excel export
- Date extraction confidence and fallback behavior
- Reject unsupported taxonomy categories at matrix-build time

## References

- PROPOSITO_PROYECTO_MANUAL.md sections 5 and 6: controlled vocabulary definitions.
- ai_classifier.py: _USER_PROMPT_TEMPLATE for AI schema.
- matrix_builder.py: mapping tables and row-building logic.

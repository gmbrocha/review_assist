# Review Policy

Generated artifacts are not final until reviewed by a human professional.

The system may eventually draft findings, surface evidence, prepare maps/tables, create source notes, generate caveats, and draft editable report materials. Human reviewers remain responsible for interpretation, correction, acceptance, rejection, verification, inclusion, and release.

Generated sections should not be blank simply because evidence is limited. The system may draft "no mapped conflict identified," "source unavailable," or "manual review required" items, but those are still reviewable draft records.

## Review Queue Rule

The review queue is the core workflow boundary.

Every generated artifact should become a review queue item before export:

- Findings.
- Report paragraphs.
- Comparison tables.
- Figures/maps.
- Caveats.
- Source notes.
- Implication notes.
- Missing-data placeholders.
- Reviewer-created notes.

Nothing generated should be compiled into an export package unless it has been accepted, edited and approved, or explicitly included by a reviewer with caveat language.

## Future Review Item Statuses

### draft

The item has been generated or entered but has not yet been reviewed.

### needs_review

The item requires human review before it can be used.

### accepted

A human reviewer has accepted the item for use in the review package.

### rejected

A human reviewer has rejected the item. Rejected items remain in the review record but should not export.

### edited

A human reviewer has modified the item. Edited content should be treated as reviewer-approved only when the reviewer marks it eligible for export.

### needs_verification

The item identifies a condition, source gap, imagery observation, or implication that needs reviewer or field/agency verification before it can be treated as accepted.

### unable_to_verify

A human reviewer could not verify the item with available information. It may export only if explicitly included with caveat language.

## Conceptual Review Item Fields

Future review queue items should support:

- `id`
- `type`
- `title`
- `generated_content`
- `edited_content`
- `assumptions`
- `provenance`
- `source_refs`
- `status`
- `reviewer_notes`
- `export_eligible`
- `export_section`

## Policy Notes

- Review items should preserve source provenance.
- Review items should preserve uncertainty and missing-data flags.
- Imagery-observed features should be treated as review items, not authoritative facts.
- Restricted cultural resource status should be visible without exposing sensitive details in inappropriate outputs.
- LLM-generated narrative should be traceable to structured findings and remain editable.
- Draft report language should not imply final approval or final conclusions.
- Review status should be visible wherever items are displayed or exported.
- Export should compile accepted or explicitly included reviewed content only.

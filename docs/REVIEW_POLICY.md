# Review Policy

Generated artifacts are not final until reviewed by a human professional.

The system may draft findings, surface evidence, prepare source notes, and eventually prepare maps/tables, caveats, and editable report materials. Human reviewers remain responsible for interpretation, correction, acceptance, rejection, verification, inclusion, and release.

Generated sections should not be blank simply because evidence is limited. The system may draft "no mapped conflict identified," "source unavailable," or "manual review required" items, but those are still reviewable draft records.

## Review Queue Rule

The review queue is the core workflow boundary.

Every generated report-facing artifact should become a review queue item before export:

- Findings.
- Report paragraphs.
- Comparison tables.
- Figures/maps.
- Caveats.
- Source notes.
- Source inventory/provenance notes when included for audit review.
- Implication notes.
- Missing-data placeholders.
- Reviewer-created notes.

Nothing generated should be compiled into an export package unless it has been accepted, edited and approved, or explicitly included by a reviewer with caveat language.

## Review Item Statuses

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

## Implemented Baseline Review Item Fields

Current JSON-backed review queue items support:

- `id`
- `project_id`
- `type`
- `title`
- `generated_content`
- `edited_content`
- `status`
- `export_eligible`
- `export_section`
- `assumptions`
- `provenance`
- `source_refs`
- `uncertainty_flags`
- `reviewer_notes`
- `created_at`
- `updated_at`

## Current Baseline

The current CLI baseline writes review queue state to:

- `projects/<project_id>/review_queue/review_queue.json`

Current commands:

- `review-assist generate-review-queue <project_dir>`
- `review-assist list-review-queue <project_dir>`
- `review-assist update-review-item <project_dir> <item_id> --status <status> [--note "..."] [--export-eligible true|false]`

The current generator defaults to a lean review queue. It creates review items from deterministic draft findings, comparison tables, draft map figures, deterministic draft report sections, report-relevant missing-data placeholders, no-mapped-relationship checks, and validation issues, including constraint-analysis warnings. Source inventory/provenance records can be included explicitly with `--include-source-inventory`; source status records and generic inventory notes are not default readiness signals.

Deterministic draft findings are generated at:

- `projects/<project_id>/findings/draft_findings.json`

Current finding generation is template-driven and cautious. It prefers source-backed constraint results when present, can fall back to legacy spatial relationship records, and can produce draft finding cards for report-relevant source-unavailable/deferred categories and no-mapped-relationship checks. These findings are not final and are not exportable unless they pass through review queue status and export-eligibility rules.

Draft map figures are generated at:

- `projects/<project_id>/maps/map_manifest.json`
- `projects/<project_id>/maps/figures/*.png`

Current map generation is vector-only. It can produce a project overview and source-context figures for analyzed local clipped source layers. These figures are not final report maps and are not exportable unless they pass through review queue status and export-eligibility rules. Map-generation warnings, such as skipped source-context figures, become validation items in the review queue.

Deterministic draft report sections are generated at:

- `projects/<project_id>/drafts/report_sections.json`

Current section generation creates no-blank-page draft sections from structured workflow artifacts through a deterministic section-drafting provider. These sections are not final report prose and are not exportable unless they pass through review queue status and export-eligibility rules.

The current baseline does not generate basemap/imagery-backed maps, final report tables, or exports. It does generate descriptive comparison table artifacts, draft PNG map figures, and deterministic draft section artifacts, but it does not compile them into an export package.

## Policy Notes

- Review items should preserve source provenance.
- Review items should preserve uncertainty and missing-data flags.
- Imagery-observed features should be treated as review items, not authoritative facts.
- Restricted cultural resource status should be visible without exposing sensitive details in inappropriate outputs.
- LLM-generated narrative should be traceable to structured findings and remain editable.
- Draft report language should not imply final approval or final conclusions.
- Review status should be visible wherever items are displayed or exported.
- Export should compile accepted or explicitly included reviewed content only.

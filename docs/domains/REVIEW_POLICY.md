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
- Matrix-backed deliverable section/table/figure/attachment items.
- Caveats.
- Source notes.
- Source inventory/provenance notes when included for audit review.
- Implication notes.
- Missing-data placeholders.
- Reviewer-created notes.

Nothing generated should be compiled into an export package unless it has been accepted, edited and approved, or explicitly included by a reviewer with caveat language.

Default reviewed-content export is now blocked by a review-complete gate over the standard matrix-backed deliverable queue. Internal preview remains available with `--include-draft`, but preview output is labeled pre-review and does not mutate item status.

## Review Item Statuses

### draft

The item has been generated or entered but has not yet been reviewed.

### needs_review

The item requires human review before it can be used.

### accepted

A human reviewer has accepted the item for use in the review package.

### declined

A human reviewer has declined the item. Declined items remain in the review record but should not export.

Legacy queue files may still contain `rejected`; loading normalizes that status to `declined`.

### edited

A human reviewer has modified the item. Edited content should be treated as reviewer-approved only when the reviewer marks it eligible for export.

### replaced

A human reviewer has replaced the generated item with replacement content. Replaced items should export only when replacement content exists and the item is export eligible.

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
- `replacement_content`
- `status`
- `export_eligible`
- `export_section`
- `deliverable_item_id`
- `target_id`
- `section_order`
- `heading_level`
- `table_id`
- `figure_id`
- `attachment_id`
- `comparison_unit_ids`
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

- `review-assist generate-deliverable-items <project_dir>`
- `review-assist generate-review-queue <project_dir>`
- `review-assist list-review-queue <project_dir>`
- `review-assist update-review-item <project_dir> <item_id> --status <status> [--note "..."] [--edited-content "..."] [--replacement-content "..."] [--export-eligible true|false]`

The current generator defaults to a bounded review queue with one item per matrix-backed deliverable item from `projects/<project_id>/deliverable/deliverable_items.json`. It preserves reviewer state by stable `deliverable_item_id` / `target_id`, normalizes legacy `rejected` status to `declined`, and records validation issues when `replaced` lacks replacement content.

Raw draft findings, broad comparison tables, legacy source-context map figures, spatial relationship items, no-mapped relationship checks, validation/source audit items, and source inventory/provenance records remain reachable only through explicit audit mode, including `--include-legacy-artifacts`; `--include-source-inventory` is an audit-mode add-on.

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

The current baseline does not generate template-grade DOCX layout or PDF exports. It does generate descriptive comparison table artifacts, matrix-backed deliverable tables/figures/items, deterministic or GPT-assisted draft section artifacts, bounded review queue items, and Markdown/DOCX export packages. Default reviewed export is blocked until every standard deliverable item is terminal or explicitly export-includable. `--include-draft` remains an internal preview bypass and exported preview content remains pre-review.

## Policy Notes

- Review items should preserve source provenance.
- Review items should preserve uncertainty and missing-data flags.
- Imagery-observed features should be treated as review items, not authoritative facts.
- Restricted cultural resource status should be visible without exposing sensitive details in inappropriate outputs.
- LLM-generated narrative should be traceable to structured findings and remain editable.
- Draft report language should not imply final approval or final conclusions.
- Review status should be visible wherever items are displayed or exported.
- Export should compile accepted or explicitly included reviewed content only.

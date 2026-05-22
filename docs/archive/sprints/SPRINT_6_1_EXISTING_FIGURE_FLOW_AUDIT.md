# Sprint 6.1: Existing Figure Flow Audit

## Status

Completed on `sprint-6`.

## Purpose

Inspect the current Review Assist figure flow and document the safest integration points for reviewer style overrides, figure recipes, render jobs, figure versions, and export resolution.

This subunit is intentionally audit-first. Do not blindly bolt on a new editor.

## Scope

Inspect and document:

- where figures are generated
- where figure outputs are stored
- how figures are referenced in deliverable items, review queue items, evidence, and exports
- what map/layer rendering tools are currently used
- whether a figure/artifact model already exists
- where approval state currently lives
- whether any snapshot/version concepts already exist
- which generated artifact chain becomes stale when figures are regenerated

Likely code paths:

- `src/review_assist/deliverable_figures.py`
- `src/review_assist/deliverable_figure_specs.py`
- `src/review_assist/deliverable_figure_rendering.py`
- `src/review_assist/deliverable_figure_contract.py`
- `src/review_assist/deliverable_items.py`
- `src/review_assist/review_queue.py`
- `src/review_assist/web/adapter.py`
- `src/review_assist/web/templates/review_detail.html`
- export/report assembly modules that resolve figure paths

## Required Notes

Produce short implementation notes that answer:

- What is the current canonical generated figure artifact?
- What is the current canonical figure image path?
- How does the web UI choose the image shown in review detail?
- How does export choose the image it packages?
- What metadata currently exists in `shown_layers` and `render_style`?
- Which fields could become a figure recipe without changing analysis semantics?
- Which artifacts must remain immutable during style edits?
- What exact regeneration chain is needed after style-only figure rendering?

## Boundary Checks

Confirm that Sprint 6 implementation must not mutate:

- source layers
- source registry
- source status
- source materialization outputs
- comparison unit geometry
- constraint results
- comparison-unit constraints
- deliverable table metrics
- evidence metrics
- review queue semantics outside figure-version targeting

## Deliverable

A short audit note, either in this file or a linked implementation note, with recommended integration points for:

- figure recipe data
- style override data
- render job data
- figure version data
- approval state
- export resolver
- web route/UI placement

## Tests

No product tests are required for this audit-only subunit unless small inspection helpers are added. If helper code is added, run focused tests for that helper only.

## Definition Of Done

- Current figure generation and export flow is mapped.
- Existing artifact contracts and review state locations are identified.
- Recommended integration points are documented.
- No source truth or generated artifacts are changed by the audit itself.

## Implementation Notes

### Current Canonical Figure Flow

- Generated figure metadata is stored in `projects/<project_id>/deliverable/figures.json`.
- Generated figure PNGs are stored under `projects/<project_id>/maps/figures/`.
- Main report figure targets are matrix-backed and remain fixed at 15 main figures. Attachment A panel figures are separate supporting records.
- `deliverable/figures.json` records figure IDs, numbers, titles, captions, source notes, method notes, image paths, source refs, layer refs, shown layers, extent metadata, figure policy metadata, provenance, uncertainty flags, stub state, review status, and validation issues.
- `shown_layers` is the current best seed for a figure recipe. It already records comparison-unit layers, source layers, basemap/provenance layers, feature counts, geometry type counts, labels, legend labels, and render styles.

### Review Queue And UI Flow

- Standard review queue figure items are created from deliverable figure items and preserve `figure_id`, `image_path`, caption/source/method notes, source refs, related figure refs, and policy metadata.
- The Review Detail page uses the web adapter to resolve the effective figure preview image from reviewed figure metadata, replacement image metadata, or generated image metadata.
- Existing figure review actions support edited captions and safe replacement image uploads only. They update queue-local `figure_review`, `caption`, `image_path`, `edited_content`, and `replacement_content` fields.
- Reviewer notes remain internal. Existing replacement/caption review behavior should remain untouched by Sprint 6.2.

### Export Flow

- Export includes figure review items selected by the standard review gate.
- Export resolves each figure image from the included queue item and/or figure lookup, copies the selected image into `exports/assets/figures/`, and annotates exported items with package-local asset paths.
- DOCX and Markdown export use the resolved figure asset path and queue/export item caption/source/method metadata.
- Sprint 6.7 is the right place to change export resolution to prefer approved figure versions. Sprint 6.1/6.2 must not change export behavior.

### Recipe And Override Integration Points

- Figure recipes should be derived from `deliverable/figures.json` records, especially `shown_layers`, `figure_policy`, extent metadata, source refs, layer refs, image path, and provenance.
- Analysis snapshots should reference existing immutable artifacts rather than copying large data: source status, project area, comparison units, comparison-unit constraints, figure extent plan, deliverable figures, and source layer paths.
- Sparse style overrides should live in project-local map metadata and should only record changed presentation fields.
- Render jobs should be project-local metadata records until the regeneration subunit wires execution.
- Version records can represent existing generated figures as implicit `v1` without copying image files.
- Version approval should remain separate from current review queue acceptance until the approval subunit.

### Immutable Boundaries For Sprint 6

Style edits and model initialization must not mutate:

- source layers or source warehouse records
- source status or source materialization outputs
- project geometry or comparison-unit geometry
- constraint results or comparison-unit constraints
- deliverable table metrics or evidence metrics
- report policy, matrix counts, GPT behavior, or export gate semantics
- existing generated figure PNGs, except future regeneration creating separate version outputs

### Stale Artifact Chain

When a styled figure is regenerated in later subunits, the minimum stale chain is:

`figure recipe + analysis snapshot + style override -> render job -> figure version -> review queue figure targeting -> export figure assets/manifests`

Sprint 6.2 only initializes metadata and should not require regenerating figures, deliverable items, review queue, evidence, or export outputs.

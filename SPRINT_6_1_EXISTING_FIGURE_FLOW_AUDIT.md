# Sprint 6.1: Existing Figure Flow Audit

## Status

Parked draft for review. This is the first Sprint 6 subunit and should be completed before any model, UI, regeneration, versioning, or export code changes.

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

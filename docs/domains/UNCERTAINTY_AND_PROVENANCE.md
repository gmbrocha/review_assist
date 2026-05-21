# Uncertainty and Provenance

This document defines the project approach to source traceability, uncertainty, and review status.

## Core Rule

Every generated review item should eventually be traceable to:

- Source.
- Method.
- Geometry assumptions.
- Review status.
- Uncertainty flags.
- Data authenticity.

Generated findings, maps, tables, narrative, caveats, source notes, and reports are pre-review drafts until a human reviewer accepts, edits, rejects, marks them for verification, or marks them unable to verify.

MVP/client-facing deliverables must distinguish real source-backed evidence from stubs and test fixtures. Mock or test fixture source records must not be included as client-facing evidence.

## Source Reliability Tiers

### Authoritative Public GIS Baseline

Examples:

- FEMA flood layers.
- USFWS NWI wetlands.
- USGS hydrography/elevation/transportation.
- NRCS soils.
- MARIS or Mississippi Geospatial Clearinghouse layers.
- Public agency infrastructure data.

Treatment:

- Generally reliable for screening-level baseline review.
- Preserve source date, access date, and metadata.
- Do not treat as field-verified project findings.

### Restricted or Reviewer-Supplied Source

Examples:

- MDAH archaeological/HSMT data.
- Consultant-supplied cultural resource KMZ/GIS exports.
- Agency letters.
- Internal hazardous materials reports.

Treatment:

- Preserve restricted/public distinction.
- Do not automate access without approval.
- Avoid exposing sensitive locations in public outputs.
- Mark findings as based on reviewer-supplied or restricted source.

### Derived Spatial Measurement

Examples:

- Crossing counts.
- Overlap acreage.
- Length through resource.
- Distance to nearest feature.
- Buffer intersection.
- Comparison-unit wetland, stream-crossing, flood-zone, and demographic deliverable table values derived from source records.
- Matrix-backed deliverable figure records derived from comparison-unit geometry, public/allowed source layers, and optional selected basemap sidecars.

Treatment:

- Store method and parameters.
- Store CRS and measurement units.
- Store buffer/corridor assumptions.
- Keep measurements as screening-level unless independently verified.

### Imagery-Observed Review Item

Examples:

- Possible pond visible in imagery.
- Recent clearing.
- New road not reflected in source layer.
- Disturbed corridor.
- Possible structure or access concern.

Treatment:

- Not authoritative by default.
- Requires reviewer validation.
- Preserve imagery source/date if known.
- Use cautious language.

### AI-Assisted Narrative

Examples:

- Draft report paragraph.
- Finding summary.
- Implication phrasing.
- Section synthesis.

Treatment:

- Must be grounded in structured findings.
- Must remain editable.
- Must not create unsupported conclusions.
- Should preserve uncertainty and citations.

## Suggested Provenance Fields

Future source records may include:

- `source_id`
- `source_name`
- `publisher`
- `source_type`
- `public_or_restricted`
- `source_url`
- `local_path`
- `access_date`
- `published_date`
- `metadata_date`
- `license_or_terms`
- `attribution`
- `crs`
- `geometry_type`
- `coverage_area`
- `known_limitations`
- `data_authenticity`: `real`, `stub`, `test_fixture`, or `unknown`

Future method records may include:

- `method_id`
- `method_name`
- `operation`
- `input_source_ids`
- `input_geometry_ids`
- `buffer_distance`
- `buffer_units`
- `measurement_crs`
- `output_units`
- `software_library`
- `software_version`
- `run_date`

## Uncertainty Flags

Suggested flags:

- `desktop_screening_only`
- `field_verification_needed`
- `source_date_unknown`
- `source_may_be_stale`
- `source_unavailable`
- `source_unimplemented`
- `source_download_failed`
- `source_selected_not_renderable`
- `renderable_sidecar_missing`
- `missing_census_api_key`
- `restricted_source_required`
- `geometry_uncertain`
- `buffer_assumption`
- `imagery_observation`
- `imagery_date_unknown`
- `manual_review_required`
- `agency_coordination_required`
- `unable_to_verify`

## Source Status and Uncertainty

The workflow should distinguish source status from finding uncertainty.

Suggested source statuses:

- `provided_locally`
- `downloadable`
- `downloaded`
- `local_materialized`
- `failed`
- `gated`
- `restricted`
- `manual`
- `unimplemented`
- `stubbed`
- `selected_not_renderable`
- `missing`
- `optional`
- `needs_review`

Missing, failed, gated/restricted, manual, unimplemented, selected-not-renderable, and stubbed source categories should create reviewable placeholders and caveat items rather than causing the workflow to fail by default. Source status artifacts and source inventory records include per-source detail status, source need class, source need reason, and detail notes so a mixed category can remain stable at the category level while still exposing the exact unavailable, restricted, manual, warehouse-present, public/coarse, or nonrenderable source.

Sprint 5.3 source need classes are report-facing provenance labels, not confidence scores. `available_materialized` means current project-local/downloaded/materialized source truth can support report-facing caveat suppression. `warehouse_available_not_materialized`, `acquisition_candidate`, and `deferred` mean the source need remains visible for reviewer or future workflow action. `manual_reviewer_supplied` and `restricted_authorized_reviewer_supplied` preserve human/restricted-source boundaries. `public_coarse_screening_context` marks public cultural or visual context that can support screening context but must not substitute for restricted records, field verification, or reviewer-supplied authority.

Sprint 5.7 adds item-level manual-material provenance for review/export decisions. The current statuses are `source_backed_generated`, `manual_required`, `reviewer_supplied`, `restricted_reviewer_supplied_required`, `optional_absent`, `not_used`, `unable_to_verify`, and `deferred_source`. These statuses describe how an item should be reviewed and exported; they are not source confidence scores and do not authorize restricted-source interpretation.

## Data Authenticity and Lineage

Export and deliverable manifests include a `data_lineage` summary and item-level manual-material metadata. The lineage summary counts project inputs, registered local source layers, provided-in-input source layers, downloaded public source layers, manual/gated/missing stubs, and test/mock records.

The current convention is:

- `real`: project inputs, reviewer-registered local sources, provided-in-input source layers, and live downloaded public sources.
- `stub`: source-gap caveats, manual/restricted placeholders, unimplemented source placeholders, failed downloads, selected-not-renderable basemap context, missing Census API key setup, and missing-source placeholders.
- `test_fixture`: mocked downloader responses or test-only source records.
- `unknown`: legacy or malformed provenance that cannot be classified.

The real-data MVP command fails by default if no real source layer is available and always fails if included export content contains `test_fixture` provenance. Stubs may remain in an MVP package only when clearly labeled as unavailable, manual, gated, failed, or reviewer-needed.

## Evidence Package

The workflow now writes `projects/<project_id>/evidence/evidence_package.json`. This artifact packages the confidence context used for report drafting:

- Data lineage.
- Source acquisition provenance.
- Real source records and stubs.
- Constraint counts.
- Source-backed constraint counts.
- Finding/table/figure references.
- Deliverable table/figure references, row summaries, figure availability/stub status, comparison-unit summaries, compact source-backed constraint summaries, source-gap status, and raw artifact paths.
- Per-section evidence bundles.
- Validation issues.

Section evidence uses only these classes:

- `source_backed`
- `source_available_no_overlap`
- `stub_or_manual`
- `failed_or_missing`
- `test_fixture_blocked`

The evidence package is not a final report. It exists to keep deterministic hard data separate from narrative drafting while preserving traceability.

Deliverable figures add validation issue codes such as `figure_source_missing`, `figure_source_unimplemented`, `basemap_selected_not_renderable`, `basemap_render_failed`, `restricted_source_not_mapped`, `figure_created_as_stub`, and `panel_map_generation_skipped`. These issues are evidence for reviewer attention, not conclusions.

## GPT Drafting Provenance

GPT-assisted section drafting is allowed only after deterministic evidence exists. It must preserve:

- Provider and model.
- Prompt version.
- Response schema version.
- Generated timestamp.
- Input digest.
- Output digest.
- Evidence package path.
- Cited finding/table/figure/source IDs.
- Validation warnings.

GPT-drafted text remains draft/pre-review content. It must enter the review queue as a `report_section` item and must not be exported as reviewed content unless the reviewer accepts, edits, or explicitly includes it under the existing export rules.

If GPT cites unknown IDs or uses prohibited framing, the output is rejected or flagged and deterministic baseline copy is retained.

## Confidence Language

Use cautious language for draft outputs.

Preferred:

- "The reviewed source layer indicates..."
- "Desktop review identified..."
- "Available data suggest..."
- "This should be verified by the reviewer."
- "Agency coordination may be needed."
- "Field verification may be required."

Avoid:

- "This is definitively..."
- "This proves..."
- "This area is jurisdictional..."
- "This alternative is best..."
- "This impact is final..."

## Buffer and Geometry Assumptions

Buffer widths should be configurable.

Early trail discussions suggest likely corridor assumptions in the 50 to 100 foot range, but this is not a fixed product rule.

Findings should record:

- Whether the original geometry or a buffered corridor was used.
- Buffer width and units.
- CRS used for buffering.
- Whether the buffer represents feature width, study corridor, review distance, or another project-specific assumption.

Sprint 2.2 comparison-unit constraints record `analysis_geometry_kind`, `buffer_feet`, `measurement_crs`, source refs, raw feature IDs, and uncertainty flags before exact deliverable table rows are generated. Raw project-feature constraints remain evidence and should not become standard report rows by default.

Sprint 2.3 deliverable figures carry comparison-unit IDs, source refs, related constraint IDs, shown-layer summaries, method notes, and source notes. Stubbed figures preserve the same matrix target identity and canonical stub text so missing or unsupported figure content remains visible during review.

## MDAH and Cultural Resource Uncertainty

MDAH integration is currently a placeholder.

Public context:

- Historic Resources Inventory can support public historic resource context.
- Rural property locations may be approximate due to privacy concerns.

Restricted context:

- Archaeological records and MDAH GIS/HSMT access may require qualified users, subscriptions, appointments, and approvals.
- Restricted data should not be treated as available public data.

Future workflow assumptions:

- The system may allow a qualified reviewer to upload restricted-source exports.
- The system may represent restricted review as a status without storing sensitive details in public report outputs.
- The system should never attempt to bypass access controls.
- Matrix-backed deliverable figures do not render or expose `mdah_restricted_archaeology` locations. When restricted cultural source status is present, the figure artifact records `restricted_source_not_mapped`.

## Review Status Relationship

Uncertainty is separate from review status.

Example:

- A finding can be `accepted` and still include `desktop_screening_only`.
- A finding can be `edited` and still require agency coordination.
- A finding can be `unable_to_verify` because a restricted source was unavailable.

Review statuses are defined in `docs/domains/REVIEW_POLICY.md`. Source status categories are defined in `docs/domains/WORKFLOW_MODEL.md`.

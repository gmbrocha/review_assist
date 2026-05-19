# Deferred Work

This file is mandatory tracked project state for deferred review-assist work. Every sprint planning pass must review it and update it when implementation needs, risks, unresolved questions, or follow-up work are postponed.

Every new sprint planning pass must review:

- this registry
- unresolved review methodology concerns
- known source limitations
- known uncertainty propagation gaps

## How To Record Deferred Items

Each deferred item should include:

- `Deferred item`: short name.
- `Why postponed`: reason it is not handled now.
- `Affected sections/workflows`: report sections, source workflows, review queue behavior, map/export behavior, or methodology affected.
- `Risk if forgotten`: what could become misleading, stale, unsupported, or operationally blocked.
- `Temporary simplification`: whether current outputs are simplified or incomplete because of the deferral.
- `Target sprint/subunit`: future sprint/subunit when known.
- `Status`: open, in progress, resolved, or superseded.

## Active Deferred Items

### Census Live Acquisition And MOE Handling

- `Deferred item`: Add live Census TIGER/ACS acquisition and fuller margin-of-error handling beyond registered local Census-like source tables.
- `Why postponed`: Sprint 2.2 implemented demographic deliverable table generation from registered local `census_tiger_acs` source rows and honest stubs when Census data/API setup is unavailable. It did not add a TIGER downloader, live ACS API client, or complete MOE presentation rules.
- `Affected sections/workflows`: Community/socioeconomic source status, source acquisition, source inventory, income demographics table, demographic composition table, report sections that cite demographic tables.
- `Risk if forgotten`: A project without a registered local Census source will correctly show table stubs, but future users may expect `CENSUS_API_KEY` alone to populate ACS rows or may later add ACS values without source year/geography/MOE caveats.
- `Temporary simplification`: Local/mock-ready Census source rows can populate the two demographic deliverable tables; otherwise the tables are explicit review-needed stubs.
- `Target sprint/subunit`: Future source acquisition/data-quality hardening.
- `Status`: open.

### EPA FRS State CSV Secondary Materialization

- `Deferred item`: Add optional CSV-to-point materialization for the EPA `state_single_ms` FRS extract preserved under the `epa_frs_facilities_ms` warehouse raw paths.
- `Why postponed`: The seeded MARIS EPA Facility Registry shapefile is analysis-ready and now materializes as `epa_frs_facilities_ms`; the broader EPA CSV is retained as raw provenance/supplemental context but is not needed to avoid losing the current GIS pipeline shape.
- `Affected sections/workflows`: Regulated facilities source materialization, source inventory/provenance, hazardous materials context.
- `Risk if forgotten`: Reviewers may expect the supplementary CSV to contribute additional FRS rows beyond the materialized shapefile.
- `Temporary simplification`: Default materialization uses the GIS-ready MARIS/EPA FRS shapefile. The CSV remains preserved under `raw/state_single_ms` with manifest notes.
- `Target sprint/subunit`: Future source warehouse/data-quality hardening.
- `Status`: open.

## Resolved Deferred Items

### Sprint 1.2 Project Intake Artifacts

- `Deferred item`: Implement the Sprint 1.2 project intake artifacts: `context/input_package.json`, `context/project_area.json`, input classification CLI, project area CLI, NAIP/MARIS basemap provenance, and populate integration.
- `Resolution`: Implemented as service-layer artifacts and CLI commands; `populate-for-review` now records input package and project area artifact paths, detected counties, basemap renderability status, and related warnings.
- `Remaining limitation`: Sprint 2.1 added the source catalog entry, example profile requirement, source status detail, and standalone basemap service for MARIS/NAIP 2025 provenance/renderability. Raster-backed map/figure rendering remains deferred.
- `Target sprint/subunit`: Sprint 1.2.
- `Status`: resolved.

### Sprint 2.1 Source Profile And Basemaps

- `Deferred item`: Implement the Sprint 2.1 source/profile/basemap setup for the example-report-shaped workflow.
- `Resolution`: Implemented `environmental_constraints_example` as the default alternatives-review profile; added Sprint 2.1 source catalog entries and attachment/manual stubs; exposed per-source status details; represented missing Census API key as a visible stub; cataloged `maris_naip_2025_imagery`; added service-level MARIS/NAIP basemap indexing and `.tif`/`.tiff`/`.png` sidecar detection.
- `Remaining limitation`: Sprint 2.2 resolved comparison-unit deliverable tables and Census table stubs/local-source rows. Raster-backed figures, panel maps, exact deliverable evidence wiring, and live Census acquisition remain deferred to their owning future work.
- `Target sprint/subunit`: Sprint 2.1.
- `Status`: resolved.

### Sprint 2.2 Comparison Constraints And Tables

- `Deferred item`: Implement the Sprint 2.2 comparison-unit constraints and exact deliverable table targets.
- `Resolution`: Implemented `constraints/comparison_unit_constraints.json`, source-specific normalization for NWI wetland classes, hydrography crossing de-duplication, FEMA flood-zone acreage aggregation, local Census-like ACS table rows, four exact matrix-backed deliverable tables at `deliverable/tables.json`, required stubs for unavailable sources, CLI commands, populate manifest wiring, docs, and focused tests.
- `Remaining limitation`: Review queue deliverable item expansion and export gating are resolved by Sprint 3.1 and Sprint 3.2. Live Census acquisition remains deferred to its owning future work item.
- `Target sprint/subunit`: Sprint 2.2.
- `Status`: resolved.

### Sprint 2.3 Figures, Evidence, And Validation

- `Deferred item`: Implement matrix-backed deliverable figures and align them with evidence package refs.
- `Resolution`: Implemented `deliverable/figures.json`, 13 exact main figure records in matrix order, explicit source/implementation stubs, selected-sidecar basemap rendering/fallbacks, restricted cultural exclusion, Attachment A supporting panel maps outside the main figure count, CLI/populate wiring, evidence package table/figure refs, compact row/figure/constraint summaries, GPT-safe payload handling, docs, and focused tests.
- `Remaining limitation`: Export gates and reviewed-package manifest enforcement are resolved by Sprint 3.2. Local NAIP warehouses that are `.sid`-only remain provenance-only and produce vector-only figures or stubs; GeoTIFF rendering depends on optional `rasterio`.
- `Target sprint/subunit`: Sprint 2.3.
- `Status`: resolved.

### Sprint 3.1 Deliverable Items And Review Queue

- `Deferred item`: Implement matrix-backed deliverable item generation, prompt-contract section drafting payloads, dynamic wetlands/waterbodies comparison-unit child sections, and bounded default review queue generation.
- `Resolution`: Implemented `deliverable/deliverable_items.json`, generation/loading/validation service and CLI, dynamic wetlands/waterbodies children from comparison units, deliverable table/figure/attachment item refs, prompt-contract metadata in section drafting requests, compact validation summaries, default review queue generation from deliverable items, legacy/audit queue opt-in with `include_legacy_artifacts` / `--include-legacy-artifacts`, terminal statuses `accepted`, `edited`, `replaced`, and `declined`, legacy `rejected` normalization to `declined`, replacement-content validation, populate manifest wiring, docs, and focused tests.
- `Remaining limitation`: Sprint 3.3 resolved DOCX fidelity/final verification. Legacy `drafts/report_sections.json`, raw findings, raw comparison tables, and legacy `maps/map_manifest.json` remain available as compatibility/audit artifacts, not the standard queue source.
- `Target sprint/subunit`: Sprint 3.1.
- `Status`: resolved.

### Sprint 3.2 Export Gate And Package Commands

- `Deferred item`: Wire the Sprint 1.1 deliverable matrix into review-complete export gating and package manifests.
- `Resolution`: Implemented default export gating from the standard bounded `deliverable_items` review queue. Reviewed-content export now blocks until every standard deliverable item is terminal or explicitly export-includable; internal preview requires `--include-draft`. Export content selection now handles accepted, edited, replaced, declined, legacy rejected, and explicitly export-eligible unable-to-verify items. Export and deliverable package manifests record review gate status, review counts, matrix item counts, included table/figure/attachment IDs, stub counts, preview state, and unreviewed-item previews. Demo packages remain preview-only and do not mutate review state; MVP packages keep real-data guardrails and fall back to preview unless the queue is already review-complete.
- `Remaining limitation`: Sprint 3.3 resolved baseline DOCX formatting fidelity and final verification docs. Exact/pixel Word-template fidelity, page-number fields, PDF export, web/UI review behavior, and new deliverable targets remain outside Sprint 3.2.
- `Target sprint/subunit`: Sprint 3.2.
- `Status`: resolved.

### Sprint 3.3 DOCX Fidelity Docs And Final Verification

- `Deferred item`: Improve editable DOCX fidelity and add final verification status over the compact, reviewed export path.
- `Resolution`: Implemented Sprint 3.3 baseline DOCX page setup, core Word styles, title metadata, matrix-ordered headings, front matter lists, bounded editable table previews with truncation notices, figure placeholders/captions/source/method notes, attachment ordering, DOCX readability checks, manifest-level `final_verification`, package-manifest propagation, docs, focused tests, full pytest, and verify-script smoke checks.
- `Remaining limitation`: Exact/pixel Word-template fidelity and page-number fields remain later polish. PDF export and UI/web wiring remain out of scope. The UI should consume existing backend contracts rather than adding report/review/export logic.
- `Target sprint/subunit`: Sprint 3.3.
- `Status`: resolved.

### Canonical Prompt Contract Wiring

- `Deferred item`: Wire `config/report_generation_prompts.json` into GPT-assisted and deterministic section generation.
- `Resolution`: Sprint 3.1 wires prompt-config metadata into standard deliverable item section drafting requests, including matrix target metadata, prompt key, global/section constraints, allowed inputs, citation policy, and structured evidence only. GPT-safe evidence payload safeguards remain in place.
- `Remaining limitation`: Legacy `generate-report-sections` remains available for compatibility/audit context and may still use its existing report-section pathways. Future prompt tuning and reviewer-controlled rewrite flows remain outside Sprint 3.1.
- `Target sprint/subunit`: Sprint 3.1.
- `Status`: resolved.

### Dynamic Wetlands/Waterbodies Comparison-Unit Sections

- `Deferred item`: Expand the dynamic 3.1.1.x wetlands/waterbodies section template into one reviewable subsection per comparison unit.
- `Resolution`: Sprint 3.1 expands the matrix dynamic template into stable `wetlands-waterbodies-{comparison_unit_id}` deliverable items, with section numbers/titles derived from matrix patterns and comparison-unit IDs preserved for review/export context.
- `Remaining limitation`: Export completeness gating for these dynamic items is resolved by Sprint 3.2.
- `Target sprint/subunit`: Sprint 3.1.
- `Status`: resolved.

### Raster-Backed NAIP Figure Rendering

- `Deferred item`: Render NAIP/MARIS basemaps into deliverable figures only when renderable sidecars are available.
- `Resolution`: Sprint 2.3 deliverable figures can render selected `.png`, `.tif`, or `.tiff` sidecars when project-area metadata/georeference is usable. `.sid` files remain provenance only, and failures are preserved through `basemap_selected_not_renderable` or `basemap_render_failed`.
- `Remaining limitation`: No MrSID decoding, paid basemap API, or hard `rasterio` dependency. The current local NAIP warehouse may be `.sid`-only, so normal local runs may remain vector-only.
- `Target sprint/subunit`: Sprint 2.3.
- `Status`: resolved.

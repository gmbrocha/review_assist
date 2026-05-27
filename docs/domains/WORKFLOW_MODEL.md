# Workflow Model

This document is the aligned workflow model for the Alternatives Review Assistant. The canonical planning source is `../../CANONICAL_PLAN.md`.

The application is a local, workspace-oriented, human-supervised workflow accelerator. It is a source-aware report compiler and contextual review assistant. It is not a recommendation engine, black-box AI reviewer, autonomous environmental analyst, or final decision-maker.

The core product shape is a constraint overlap engine feeding a review queue. The system first extracts project geometry from KMZ/KML or other supported inputs, classifies it as point/site, line/corridor, polygon/area, or mixed context, derives raw normalized project features and report-facing comparison units, derives the analysis bounds, crops/loads relevant source material, and identifies objective constraints by project feature and resource category. The review queue then presents the resulting findings, maps, tables, caveats, source notes, and draft report sections as small editable items for human review and accepted-content export.

The review queue is not an end in itself. A large number of generic review items does not mean the workflow is useful. The workflow should prefer source-backed, report-relevant constraint findings and draft sections over noisy placeholder volume.

## Canonical Workflow

### 1. Open or Create Workspace

The user opens the web app and creates or opens a workspace/project.

The workspace is the persistent container for:

- Project metadata.
- Project-specific context.
- Input files.
- Source status tracking.
- Downloaded or locally provided datasets.
- Generated intermediates.
- Generated review items.
- Reviewer edits and decisions.
- Accepted outputs.
- Export artifacts.

The workspace should be designed for a low-friction web app workflow over local/project workspace services. Archived desktop GUI and PyInstaller references are historical unless a later decision reopens that path.

### 2. User Adds Project Inputs

The user drops project material into the workspace.

Examples:

- KMZ/KML alternatives.
- KMZ/KML project locations or service points.
- GIS layers, shapefiles, GeoPackages, or GeoJSON.
- Prior reports.
- Imagery.
- Context notes.
- PDFs.
- Maps.
- Study documents.

The app should attempt to:

- Parse project geometry.
- Classify geometry as point/site, line/corridor, polygon/area, or mixed context.
- Reconstruct full alternatives, routes, service areas, or project features from segmented line-string/polyline pieces where needed.
- Generate comparison units for report-facing grouping while preserving raw input features as evidence.
- Determine bounding box and project extent.
- Detect alternatives, project locations, service points, service areas, corridors, routes, or contextual layers.
- Identify provided local resources.
- Surface validation issues and missing context.

Project workspaces are created under `projects/<project_id>/`. Historical sample workspaces were removed from the active repo; current local trial workspaces should be treated as machine-local state unless explicitly committed.

The example report at `docs/reference/env_constraints_report_20260511_EXAMPLE_ONLY.docx` is a structural reference for report deliverables, not authoritative project data.

The workflow should act as a blank project machine that can accept a new project KMZ/KML, infer or request the geometry role, apply appropriate bounds/buffer logic, and run source-backed constraint checks.

### 3. Project Context Generation

The system generates and maintains project-specific context as a persistent project artifact.

Examples:

- Project name.
- Study area.
- Project extent.
- Assumptions and buffer/corridor defaults.
- Detected alternatives.
- Likely report profile.
- Provided source categories.
- Known missing source categories.
- User instructions.
- Special reviewer notes.

This context should be editable because automated detection will not always infer intent correctly.

### 4. Needed Data Set Resolution

The system determines which source categories are needed for the selected report profile.

Examples:

- Wetlands.
- Hydrography.
- Flood zones.
- Listed species.
- Cultural resources.
- Utilities.
- Demographics.
- Hazardous materials.
- Imagery/basemaps.

The system compares required categories against:

- Locally provided data.
- Locally materialized warehouse data.
- Downloadable public data.
- Gated or restricted data.
- Stubbed/manual data.
- Missing or optional data.

The result is a `SOURCE_STATUS_SET`.

The companion source acquisition workflow writes `projects/<project_id>/source_acquisition/source_acquisition_manifest.json`. It compares the project input package and project registry against the catalog, marks source gaps as provided, registered local, local materialized, downloaded, downloadable, unsupported, gated/restricted, manual, stubbed, optional, missing, or failed, and can explicitly acquire supported public sources. Implemented public downloaders include USFWS NWI wetlands, USGS NHD hydrography, USFWS Critical Habitat, EPA/ECHO regulated facilities, and FEMA NFHL flood hazard where the selected profile requires or explicitly includes it. Downloads are opt-in through `download-source`, `prepare-sources`, or `populate-for-review --prepare-sources`; optional downloads through `populate-for-review` require pairing `--include-optional-sources` with `--prepare-sources`.

The companion local source materialization workflow writes `projects/<project_id>/source_materialization/local_source_materialization_manifest.json`. It reads configured Mississippi warehouse datasets from ignored root `sources/`, clips them to the normalized project analysis bounds, writes small project-ready GeoJSON layers under `projects/<project_id>/layers/<source_id>/`, and registers those layers as real `local_file` sources with `status: local_materialized`. Implemented materializers cover NWI wetlands, USFWS Critical Habitat line/polygon layers, SSURGO soils, aggregated MDOT/rail transportation context, utilities, administrative/boundary context, public cultural context, community facilities, and conservation/recreation lands. Materialized county boundaries are also summarized into project context so the study-area section can name intersecting Mississippi counties. When `populate-for-review --materialize-local-sources --prepare-sources` is used, materialization runs before public download attempts so local warehouse data can satisfy source gaps first.

## Source Status Set

Source status tracking is first-class workflow state. Missing data should not stop the workflow by default.

Suggested statuses:

- `provided_locally`: user supplied a local source file or document.
- `downloadable`: public data appears available but is not downloaded yet.
- `downloaded`: public data has been acquired for the workspace.
- `local_materialized`: local warehouse data has been clipped/materialized into the workspace.
- `failed`: a supported source acquisition attempt failed and should create caveat/review handling.
- `gated`: access requires credentials, qualified access, agency request, or restricted handling.
- `restricted`: source requires restricted, sensitive, or qualified-access handling.
- `manual`: source requires manual lookup, download, document attachment, or reviewer-supplied material.
- `unimplemented`: source appears feasible but no downloader/materializer is implemented yet.
- `stubbed`: a placeholder exists so reports can include a review requirement or caveat.
- `render_asset_missing`: a project-local renderable basemap asset is expected but has not been produced or found.
- `missing`: expected source material is not available.
- `optional`: useful context but not required for the selected report profile.
- `needs_review`: source status or fitness for use needs reviewer confirmation.

Missing, failed, gated/restricted, manual, unimplemented, missing-render-asset, and stubbed datasets should generate placeholders, uncertainty flags, and review requirements rather than causing the workflow to fail. The goal is useful pre-review report generation, not perfect data completeness.

## Populate for Review

The user action is conceptually:

```text
Populate for Review
```

This stage may:

- Materialize configured local warehouse datasets into project-ready source layers.
- Download or acquire approved public datasets where possible.
- Load locally provided source layers.
- Crop or clip data to the project extent.
- Prepare imagery/basemaps.
- Run deterministic constraint overlap analysis by project feature, service location, service area, route, corridor, site, alternative, and resource category as appropriate.
- Support overlap/proximity analysis by geometry type, including line/corridor crossings, point/site buffers, polygon/area overlaps, and mixed project contexts.
- Generate source-backed constraint findings.
- Generate tables.
- Generate figures/maps.
- Generate draft narrative sections.
- Generate caveats and uncertainty notes.
- Generate source/provenance notes.

Deterministic GIS analysis must remain separate from AI narrative synthesis.

GPT/LLM calls are acceptable here for draft narrative generation, summarization, implication drafting, and review-oriented synthesis, but AI output must remain editable, traceable, and reviewable. AI must not make final recommendations.

Current baseline:

- `classify-input-package <project_dir>` writes `projects/<project_id>/context/input_package.json` with per-input classification, required-KMZ state, and reviewer-confirmation warnings for ambiguous inputs.
- `build-project-area <project_dir>` writes `projects/<project_id>/context/project_area.json` with analysis bboxes, county detection, NAIP/MARIS basemap candidates, selected source paths, renderable sidecars, renderability status, warnings, and provenance. Basemap indexing is service-level behavior in `src/review_assist/basemaps.py`; legacy MrSID references are unsupported/stale provenance only, and active rendering uses project-local NAIP assets or supported `.tif`, `.tiff`, `.png`, `.jpg`, or `.jpeg` render assets.
- `build-comparison-units <project_dir>` writes `projects/<project_id>/intermediate/comparison_units.geojson` and `comparison_units.json`. These artifacts group segmented lines, point-heavy inputs, polygons, and mixed geometry into pre-review report-facing units without deleting or repurposing `project_features.geojson`.
- `populate-for-review` runs input package classification, project geometry normalization, project area generation, comparison-unit generation, context generation, optional local source materialization, optional source acquisition, source status resolution, source inventory generation, tolerant constraint analysis, deterministic draft finding generation, comparison table generation, vector-only map generation, matrix-backed deliverable table/figure generation, evidence package generation, legacy report section generation, matrix-backed deliverable item generation, and bounded review queue generation.
- It writes `projects/<project_id>/populate_for_review/populate_for_review_run.json`.
- It records `projects/<project_id>/context/input_package.json` and `projects/<project_id>/context/project_area.json` in the run manifest when those steps succeed.
- It records `projects/<project_id>/intermediate/project_geometry.json`, `project_features.geojson`, and `project_analysis_bounds.geojson` in the run manifest when project geometry generation succeeds.
- It records `projects/<project_id>/intermediate/comparison_units.geojson`, `comparison_units.json`, generated comparison-unit count, expected comparison-unit count, and expected-count status in the run manifest when comparison-unit generation succeeds.
- It records project county names and basemap renderability status in the run manifest when project area generation succeeds.
- It records source status and source inventory with per-source detail states so required manual, restricted, unimplemented, failed, stubbed, Census-key-missing, and selected-not-renderable sources remain visible to reviewers.
- It records `projects/<project_id>/constraints/constraint_results.json` in the run manifest when constraint analysis succeeds.
- It can record `projects/<project_id>/source_materialization/local_source_materialization_manifest.json` in the run manifest when `--materialize-local-sources` is used.
- It can record `projects/<project_id>/source_acquisition/source_acquisition_manifest.json` in the run manifest when `--prepare-sources` is used.
- It records `projects/<project_id>/source_inventory/source_inventory.json` and `projects/<project_id>/tables/comparison_tables.json` in the run manifest when those steps succeed.
- It records `projects/<project_id>/constraints/comparison_unit_constraints.json` in the run manifest when report-facing comparison-unit constraint analysis succeeds. Raw project-feature constraints remain in `constraint_results.json` as evidence/backward-compatible context.
- It records `projects/<project_id>/deliverable/tables.json` in the run manifest when the matrix-backed deliverable table targets generate or stub. The broad comparison tables remain evidence artifacts rather than exact standard deliverable rows.
- It records `projects/<project_id>/deliverable/figures.json` in the run manifest when the matrix-backed deliverable figure targets generate or stub. Legacy source-context `maps/map_manifest.json` remains an audit/evidence artifact.
- It records `projects/<project_id>/findings/draft_findings.json` in the run manifest when finding generation succeeds.
- It records `projects/<project_id>/maps/map_manifest.json` in the run manifest when map generation succeeds.
- It records `projects/<project_id>/drafts/report_sections.json` in the run manifest when report section generation succeeds.
- It records `projects/<project_id>/deliverable/deliverable_items.json` in the run manifest when the matrix-backed deliverable item targets generate or stub. The standard review queue consumes these items by default.
- Missing or unreadable local source layers become warnings and reviewable validation/caveat items rather than blocking review queue generation.
- It downloads only explicitly requested supported sources. It records NAIP/MARIS source-path provenance and renderability status but does not render basemap/imagery-backed maps or create exports itself. GPT section drafting may run when `GPT_DRAFTING=1`, but only after structured evidence exists and only for reviewable section copy.

## Review Queue

The review queue is the core workflow object.

Every generated report-facing deliverable item becomes a reviewable item. Raw evidence artifacts remain available for audit and provenance, but they do not flood the standard queue by default.

Review queue items should be small enough for a reviewer to accept, decline, replace, or edit independently. For report generation, that generally means matrix-backed section, table, figure, attachment, caveat, and provenance items rather than one monolithic report draft.

Reviewable item examples:

- Finding.
- Report paragraph.
- Comparison table.
- Figure/map.
- Caveat.
- Source note.
- Implication note.
- Missing-data placeholder.
- Reviewer-created note.

Conceptual review item fields:

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
- `export_group`
- `deliverable_item_id`
- `target_id`
- `replacement_content`
- `table_id`
- `figure_id`
- `attachment_id`
- `comparison_unit_ids`

Suggested statuses:

- `draft`
- `needs_review`
- `accepted`
- `edited`
- `replaced`
- `declined`
- `needs_verification`
- `unable_to_verify`

Legacy `rejected` status is accepted on load and normalized to `declined`.

Reviewer actions:

- Edit.
- Accept.
- Decline.
- Replace.
- Request rewrite.
- Mark for verification.
- Mark unable to verify.
- Add notes.

The review queue is the human-in-the-loop control boundary. It is not a side panel or optional feature.

Current baseline:

- `generate-deliverable-items` creates `projects/<project_id>/deliverable/deliverable_items.json` from the canonical deliverable matrix, comparison units, deliverable tables, deliverable figures, attachment targets, evidence refs, source-gap status, and prompt contract metadata.
- `generate-review-queue` creates a bounded JSON review queue with one item per deliverable item by default. Raw findings, broad comparison tables, legacy map figures, spatial relationships, source inventory notes, and validation/source audit items remain available only through explicit legacy/audit mode.
- `list-review-queue` summarizes item status/type counts and item eligibility.
- `update-review-item` supports status changes, reviewer notes, edited content, replacement content, and export eligibility flags.
- The local web UI consumes the bounded standard review queue by default. Reviewer pages show human-facing item type labels, separate review workflow status and generated-content readiness status, full reviewable generated content, table/figure previews, warnings, review actions, and export gate state without exposing raw internal IDs, source refs, artifact paths, hashes, prompt/cache fingerprints, or low-level validation codes by default.
- Existing reviewer routes accept `?advanced=1` for inline advanced/debug diagnostics on the same page. Advanced/debug mode persists in the local session until hidden, exposes the raw item/source/layer/version IDs, source/evidence refs, artifact paths, prompt/version/hash/cache fields, and QA/validation codes needed for development or audit troubleshooting, and remains read-only. This is display filtering only; canonical queue artifacts and review/export gates are unchanged.

## Export Compilation

Accepted and reviewer-approved items are queued for export.

The export stage compiles:

- Accepted report sections.
- Accepted findings.
- Accepted maps/figures.
- Accepted tables.
- Appendices.
- Source/provenance references.
- Assumptions and caveats.

Target exports may eventually include:

- DOCX.
- PDF.
- Appendix packages.
- Map packages.

The system should compile accepted content only. Declined items remain in the review record but do not export. Items needing verification or unable to verify may export only if the reviewer explicitly includes them with caveat language.

Current baseline:

- `export-report <project_dir>` writes Markdown and/or DOCX report packages plus `projects/<project_id>/exports/export_manifest.json`.
- `build-demo-deliverable <project_dir>` runs populate-for-review and preview export into an internal demo package manifest without accepting review items.
- `build-mvp-deliverable <project_dir>` runs `populate-for-review --prepare-sources`, keeps real-data guardrails, attempts reviewed export when the queue is review-complete, and otherwise falls back to preview export without accepting review items.
- Default exports are blocked by the standard bounded review queue until every matrix-backed deliverable item is terminal or explicitly export-includable.
- When the gate passes, default exports include accepted, edited, or replaced queue items only when export eligible, plus `unable_to_verify` items only when explicitly export eligible and backed by usable generated, edited, or replacement content.
- `--include-draft` creates an internal preview export that includes non-declined draft/unaccepted items and marks the Markdown/DOCX as non-final/pre-review.
- Export and package manifests record review gate status, preview state, review item counts, unreviewed previews, deliverable matrix item counts, included table/figure/attachment IDs, and stub counts.
- DOCX export renders referenced tables and figures inline inside report sections when those table/figure review items are included, avoids duplicate standalone rendering for those artifacts, and keeps missing visuals/tables as explicit placeholders.
- Export and deliverable manifests include `data_lineage` so reviewers can distinguish real project inputs, registered/provided/downloaded source layers, manual/gated/missing stubs, and test/mock records.
- Export and deliverable manifests include `mvp_quality` so reviewers can inspect real-source counts, source-backed constraints, included sections/tables/figures, inline-rendered evidence, placeholders, unresolved source categories, GPT section counts, and warning counts.
- MVP deliverable builds fail by default when no real source layer is available and always fail when included content contains test fixture/mock source evidence.

## Conceptual Service Boundaries

The future web app UI should remain thin over services.

Conceptual modules:

- Workspace/project service.
- Ingestion service.
- Geometry normalization service.
- Project context service.
- Source acquisition service.
- Source status tracking service.
- Spatial analysis service.
- Imagery/basemap service.
- Map/figure generation service.
- Findings generation service.
- Report drafting service.
- Review queue service.
- Export/compilation service.

The current CLI services are early building blocks. `generate-context` and `resolve-sources` now produce the first workflow-native JSON artifacts. They should evolve toward this workflow rather than becoming the final product shape.

## Non-Negotiable Boundaries

- Do not select or recommend a preferred alternative.
- Do not implement autonomous ranking/scoring.
- Do not frame objective constraint presentation as project-feature selection or rejection, including trail, route, corridor, site, service-area, or other alternatives.
- Do not treat desktop review as field verification.
- Do not let AI create unsupported facts.
- Do not export unreviewed generated content as final.
- Do not include mock or test fixture source records in MVP/client-facing deliverables.
- Do not automate restricted access workflows without explicit approval.

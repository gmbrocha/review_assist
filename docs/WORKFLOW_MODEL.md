# Workflow Model

This document is the canonical workflow truth model for the Alternatives Review Assistant.

The application is a local, workspace-oriented, human-supervised workflow accelerator. It is a source-aware report compiler and contextual review assistant. It is not a recommendation engine, black-box AI reviewer, autonomous environmental analyst, or final decision-maker.

The core product shape is a constraint overlap engine feeding a review queue. The system first extracts project geometry from KMZ/KML or other supported inputs, classifies it as point/site, line/corridor, polygon/area, or mixed context, derives the analysis bounds, crops/loads relevant source material, and identifies objective constraints by project feature and resource category. The review queue then presents the resulting findings, maps, tables, caveats, source notes, and draft report sections as small editable items for human review and accepted-content export.

The review queue is not an end in itself. A large number of generic review items does not mean the workflow is useful. The workflow should prefer source-backed, report-relevant constraint findings and draft sections over noisy placeholder volume.

## Canonical Workflow

### 1. Open or Create Workspace

The user opens the desktop app and creates or opens a workspace/project.

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

The workspace should be designed for a low-friction local desktop workflow and eventual PyInstaller packaging.

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
- Determine bounding box and project extent.
- Detect alternatives, project locations, service points, service areas, corridors, routes, or contextual layers.
- Identify provided local resources.
- Surface validation issues and missing context.

Current examples:

- `projects/trails` contains line-based trail-alternative KMZ geometry.
- `projects/conexon_projects` contains broad point-based broadband location KMZ geometry.
- `env_constraints_report_20260511_EXAMPLE_ONLY.docx` is a structural reference for report deliverables, not authoritative project data.

These examples are not product boundaries. The workflow should act as a blank project machine that can accept a new project KMZ/KML, infer or request the geometry role, apply appropriate bounds/buffer logic, and run source-backed constraint checks.

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
- Downloadable public data.
- Gated or restricted data.
- Stubbed/manual data.
- Missing or optional data.

The result is a `SOURCE_STATUS_SET`.

The companion source acquisition workflow writes `projects/<project_id>/source_acquisition/source_acquisition_manifest.json`. It compares the project input package and project registry against the catalog, marks source gaps as provided, registered local, downloaded, downloadable, unsupported, gated, manual, optional, missing, or failed, and can explicitly acquire supported public sources. Implemented public downloaders include USFWS NWI wetlands, USGS NHD hydrography, USFWS Critical Habitat, EPA/ECHO regulated facilities, and optional FEMA NFHL flood hazard. Downloads are opt-in through `download-source`, `prepare-sources`, or `populate-for-review --prepare-sources`; optional downloads through `populate-for-review` require pairing `--include-optional-sources` with `--prepare-sources`.

The companion local source materialization workflow writes `projects/<project_id>/source_materialization/local_source_materialization_manifest.json`. It reads configured Mississippi warehouse datasets from ignored root `sources/`, clips them to the normalized project analysis bounds, writes small project-ready GeoJSON layers under `projects/<project_id>/layers/<source_id>/`, and registers those layers as real `local_file` sources with `status: local_materialized`. Implemented materializers cover NWI wetlands, USFWS Critical Habitat line/polygon layers, SSURGO soils, aggregated MDOT/rail transportation context, utilities, administrative/boundary context, public cultural context, community facilities, and conservation/recreation lands. Materialized county boundaries are also summarized into project context so the study-area section can name intersecting Mississippi counties. When `populate-for-review --materialize-local-sources --prepare-sources` is used, materialization runs before public download attempts so local warehouse data can satisfy source gaps first.

## Source Status Set

Source status tracking is first-class workflow state. Missing data should not stop the workflow by default.

Suggested statuses:

- `provided_locally`: user supplied a local source file or document.
- `downloadable`: public data appears available but is not downloaded yet.
- `downloaded`: public data has been acquired for the workspace.
- `failed`: a supported source acquisition attempt failed and should create caveat/review handling.
- `gated`: access requires credentials, qualified access, agency request, or restricted handling.
- `stubbed`: a placeholder exists so reports can include a review requirement or caveat.
- `missing`: expected source material is not available.
- `optional`: useful context but not required for the selected report profile.
- `needs_review`: source status or fitness for use needs reviewer confirmation.

Missing, failed, gated, and stubbed datasets should generate placeholders, uncertainty flags, and review requirements rather than causing the workflow to fail. The goal is useful pre-review report generation, not perfect data completeness.

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

- `populate-for-review` runs context generation, project geometry normalization, optional local source materialization, optional source acquisition, source status resolution, source inventory generation, tolerant constraint analysis, deterministic draft finding generation, comparison table generation, vector-only map generation, evidence package generation, report section generation, and lean review queue generation.
- It writes `projects/<project_id>/populate_for_review/populate_for_review_run.json`.
- It records `projects/<project_id>/intermediate/project_geometry.json`, `project_features.geojson`, and `project_analysis_bounds.geojson` in the run manifest when project geometry generation succeeds.
- It records `projects/<project_id>/constraints/constraint_results.json` in the run manifest when constraint analysis succeeds.
- It can record `projects/<project_id>/source_materialization/local_source_materialization_manifest.json` in the run manifest when `--materialize-local-sources` is used.
- It can record `projects/<project_id>/source_acquisition/source_acquisition_manifest.json` in the run manifest when `--prepare-sources` is used.
- It records `projects/<project_id>/source_inventory/source_inventory.json` and `projects/<project_id>/tables/comparison_tables.json` in the run manifest when those steps succeed.
- It records `projects/<project_id>/findings/draft_findings.json` in the run manifest when finding generation succeeds.
- It records `projects/<project_id>/maps/map_manifest.json` in the run manifest when map generation succeeds.
- It records `projects/<project_id>/drafts/report_sections.json` in the run manifest when report section generation succeeds.
- Missing or unreadable local source layers become warnings and reviewable validation/caveat items rather than blocking review queue generation.
- It downloads only explicitly requested supported sources. It does not render basemap/imagery-backed maps or create exports itself. GPT section drafting may run when `GPT_DRAFTING=1`, but only after structured evidence exists and only for reviewable section copy.

## Review Queue

The review queue is the core workflow object.

Every generated artifact becomes a reviewable item. Nothing should skip the review queue.

Review queue items should be small enough for a reviewer to accept, reject, or edit independently. For report generation, that generally means resource-specific findings, subsection drafts, map/table previews, caveats, and provenance notes rather than one monolithic report draft.

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

Suggested statuses:

- `draft`
- `needs_review`
- `accepted`
- `edited`
- `rejected`
- `needs_verification`
- `unable_to_verify`

Reviewer actions:

- Edit.
- Accept.
- Reject.
- Request rewrite.
- Mark for verification.
- Mark unable to verify.
- Add notes.

The review queue is the human-in-the-loop control boundary. It is not a side panel or optional feature.

Current baseline:

- `generate-review-queue` creates a lean JSON review queue from deterministic draft findings, comparison tables, map figures, report sections, report-relevant missing-data placeholders, and validation issues. Source inventory notes can still be included explicitly for audit/review workflows.
- `list-review-queue` summarizes item status/type counts and item eligibility.
- `update-review-item` supports status changes, reviewer notes, and export eligibility flags.
- The baseline is still service/CLI only; GUI review screens, basemap/imagery maps, PDF export, reviewer-facing GPT controls, and final template-grade DOCX layout remain future work.

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

The system should compile accepted content only. Rejected items remain in the review record but do not export. Items needing verification or unable to verify may export only if the reviewer explicitly includes them with caveat language.

Current baseline:

- `export-report <project_dir>` writes Markdown and/or DOCX report packages plus `projects/<project_id>/exports/export_manifest.json`.
- `build-demo-deliverable <project_dir>` runs populate-for-review and preview export into an internal demo package manifest without accepting review items.
- `build-mvp-deliverable <project_dir>` runs `populate-for-review --prepare-sources` and preview export into a real-data guarded MVP package manifest without accepting review items.
- Default exports include accepted or edited queue items only, plus `unable_to_verify` items only when explicitly export eligible.
- `--include-draft` creates an internal preview export that includes non-rejected draft/unaccepted items and marks the Markdown/DOCX as non-final/pre-review.
- DOCX export renders referenced tables and figures inline inside report sections when those table/figure review items are included, avoids duplicate standalone rendering for those artifacts, and keeps missing visuals/tables as explicit placeholders.
- Export and deliverable manifests include `data_lineage` so reviewers can distinguish real project inputs, registered/provided/downloaded source layers, manual/gated/missing stubs, and test/mock records.
- Export and deliverable manifests include `mvp_quality` so reviewers can inspect real-source counts, source-backed constraints, included sections/tables/figures, inline-rendered evidence, placeholders, unresolved source categories, GPT section counts, and warning counts.
- MVP deliverable builds fail by default when no real source layer is available and always fail when included content contains test fixture/mock source evidence.

## Conceptual Service Boundaries

The desktop GUI should remain thin over services.

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
- Do not frame objective constraint presentation as trail selection or rejection.
- Do not treat desktop review as field verification.
- Do not let AI create unsupported facts.
- Do not export unreviewed generated content as final.
- Do not include mock or test fixture source records in MVP/client-facing deliverables.
- Do not automate restricted access workflows without explicit approval.

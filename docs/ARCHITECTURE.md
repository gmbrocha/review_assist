# Architecture

This document captures the current architecture direction. Prototype service and CLI implementations exist for ingestion, project geometry normalization, source catalog/registry handling, local source registration, opt-in source acquisition, legacy spatial relationship checks, constraint overlap/proximity analysis, project context/source status artifacts, source inventory/provenance artifacts, deterministic draft finding generation, comparison table artifacts, vector-only map artifacts, deterministic draft report section artifacts, JSON-backed review queue items, Markdown/DOCX export packages, internal demo deliverable packages, real-data MVP deliverable guardrails, and populate-for-review orchestration. No production web app, final PDF export, template-grade DOCX layout, or production workflow exists yet.

The canonical planning source is `../PLAN_REDIRECT_NEW.md`. `docs/WORKFLOW_MODEL.md` should remain aligned to that plan without over-engineering the architecture.

The system should stay modular enough to support multiple project types while avoiding premature complexity. The likely shape is a thin web app over small services that pass structured workspace, project context, source status, geometry, review item, map, table, narrative, and export artifacts between each other.

## Canonical Workflow Architecture

The application workflow is stateful and workspace-driven:

1. Open or create a workspace.
2. Add project inputs.
3. Generate persistent project context.
4. Resolve needed data categories into a source status set.
5. Resolve source gaps and optionally acquire supported public sources.
6. Populate for review.
7. Review every generated item in the review queue.
8. Compile accepted content into export packages.

The review queue is the primary workflow boundary. Generated findings, draft paragraphs, maps, tables, caveats, source notes, and implication notes should become review queue items before they are eligible for export.

## Core State Objects

Conceptual state objects:

- Workspace/project manifest.
- Project context artifact.
- Source catalog.
- Source acquisition manifest.
- Source status set.
- Source inventory/provenance records.
- Normalized project geometry.
- Constraint result records.
- Legacy spatial relationship records.
- Draft finding records.
- Comparison table records.
- Map/figure records.
- Draft report section records.
- Review queue items.
- Export manifest.
- Data lineage records.

The current code implements early versions of project manifests, report profiles, source catalog entries, project source registries, source acquisition manifests, project context artifacts, source status sets, source inventory records, normalized project geometry artifacts, constraint result artifacts, legacy spatial relationship records, deterministic draft finding records, comparison table records, vector-only map manifests/PNG figures, deterministic draft report section records, review queue persistence, Markdown/DOCX export manifests/reports, demo/MVP deliverable package manifests, data lineage summaries, and populate run manifests.

## Project Workspace Layer

Project workspaces should isolate project-specific inputs, generated intermediates, reviewer notes, maps, draft reports, and exports.

Current workspaces:

- `projects/trails`
- `projects/conexon_projects`

Phase 1 workspaces include `config/project.json` manifests and copied KMZ inputs under `inputs/`. Phase 2A workspaces include `config/sources.json` source registries.

Project folders may contain:

- `inputs/`
- `layers/`
- `intermediate/`
- `constraints/`
- `context/`
- `source_acquisition/`
- `source_status/`
- `review_queue/`
- `findings/`
- `maps/`
- `drafts/`
- `exports/`
- `review/`

Some folders are current, while others remain future placeholders. `inputs/`, `config/`, generated `intermediate/`, generated `constraints/`, generated `context/`, generated `source_acquisition/`, generated `source_status/`, generated `source_inventory/`, generated `findings/`, generated `tables/`, generated `maps/`, generated `drafts/`, generated `review_queue/`, generated `exports/`, and generated `populate_for_review/` outputs are currently used. `layers/` is reserved for local source layers and is ignored by Git. `review/` remains a future workflow area.

`populate_for_review/` is also currently used for orchestration run manifests. It is generated workflow state and ignored by Git.

Phase 1 currently writes generated GeoJSON and geometry summary artifacts under `intermediate/`. Project geometry normalization writes `project_geometry.json`, `project_features.geojson`, and `project_analysis_bounds.geojson` under `intermediate/`. Constraint analysis writes `constraint_results.json` and clipped source GeoJSON files under `constraints/`. Legacy Phase 2B spatial analysis still writes `spatial_relationships.json` under `intermediate/`.

## Ingestion Service

Purpose:

- Read KMZ, KML, shapefile, GeoPackage, GeoJSON, or other project inputs.
- Identify project footprint, alternatives, and contextual layers.
- Extract metadata, source filenames, geometry counts, and naming clues.
- Surface validation issues.

Likely early stack:

- GeoPandas/Fiona/pyogrio for geospatial file reads where supported.
- Python standard library ZIP/XML parsing for lightweight KMZ inspection where useful.

Phase 1 standardizes on GeoPandas data structures and GeoJSON intermediates. The KML/KMZ XML parsing layer exists to avoid depending on optional GDAL KML driver support.

Open questions:

- How should KMZ layers be classified as footprint, alternative, or context?
- Should users manually label layers after ingestion?
- Which formats are required for v1 beyond KMZ/KML?

## Project Context Service

Purpose:

- Maintain project-specific context as a persistent artifact.
- Store detected alternatives, project extent, assumptions, likely report profile, provided categories, missing categories, user instructions, and special reviewer notes.
- Allow reviewer correction when automated detection is wrong or incomplete.

Current implementation writes `projects/<project_id>/context/project_context.json` through the `generate-context` CLI command. Current project manifests and geometry summaries are inputs to it.

## Geometry Normalization Service

Purpose:

- Normalize geometries into a consistent project coordinate system.
- Validate geometry types and repair simple invalid geometries where safe.
- Preserve original geometry and source metadata.
- Generate corridor/buffer geometries from configurable assumptions.

Current buffer assumption:

- V1 should support configurable corridor/buffer widths.
- Early trail discussions suggest likely defaults in the 50 to 100 foot range.
- The default must remain configurable and visible in findings/provenance.

Current implementation:

- CLI command: `review-assist build-project-geometry <project_dir>`.
- Writes `projects/<project_id>/intermediate/project_geometry.json`.
- Writes `projects/<project_id>/intermediate/project_features.geojson`.
- Writes `projects/<project_id>/intermediate/project_analysis_bounds.geojson`.
- Classifies inputs as `point_site`, `line_corridor`, `polygon_area`, or `mixed`.
- Groups segmented line features by placemark name, style URL, then candidate label, and merges only connected line pieces.
- Preserves disconnected line pieces as multipart geometry instead of inventing connections.
- Keeps point-heavy projects as individual point features while preserving style/color grouping metadata.
- Derives analysis bounds from normalized project features plus the configured default buffer.

Open questions:

- What CRS should be used for Mississippi project measurements?
- How should multipart alternatives be represented?
- Should buffer widths vary by project type, alternative, or resource category?

## Source/Layer Acquisition Service

Purpose:

- Load local source layers.
- Later, download or query candidate public sources.
- Track source version, access date, metadata, and licensing.
- Distinguish public sources from restricted or reviewer-supplied sources.

Current implementation:

- A global JSON source catalog lives at `config/source_catalog.json`.
- Project JSON source registries live at `projects/<project_id>/config/sources.json`.
- The CLI can list catalog entries and register a local source layer for a project.
- Local-file registration remains the default Phase 2 path; live downloads are explicit and opt-in.
- The source acquisition service writes `projects/<project_id>/source_acquisition/source_acquisition_manifest.json`.
- Implemented public downloaders include `usfws_nwi_wetlands`, `usgs_nhd_hydrography`, `usfws_critical_habitat`, `epa_envirofacts_echo`, and optional `fema_nfhl_flood_hazard`; successful downloads are stored under ignored `source_acquisition/downloads/` and registered as normal local-file sources.
- Registry loading validates project IDs, duplicate source IDs, boolean enabled flags, and non-negative source buffer overrides.

This service should not silently call paid services, use credentials, or access restricted systems without explicit approval.

Open questions:

- Which sources are required for the first real prototype?
- Should source layers be cached per project or globally?
- How should stale source layers be flagged?

## Source Status Tracking Service

Purpose:

- Compare required source categories for the report profile against local, downloadable, downloaded, failed, restricted, missing, stubbed, and optional sources.
- Produce and maintain the `SOURCE_STATUS_SET`.
- Create placeholders and review requirements for missing/failed/gated data instead of failing the workflow.

Suggested statuses are defined in `docs/WORKFLOW_MODEL.md`:

- `provided_locally`
- `downloadable`
- `downloaded`
- `failed`
- `gated`
- `stubbed`
- `missing`
- `optional`
- `needs_review`

Current implementation writes `projects/<project_id>/source_status/source_status_set.json` through the `resolve-sources` CLI command. Current project source registries are an early foundation. When a source acquisition manifest records a failed supported download, the matching required source category remains visible as `failed` instead of reverting to generic `downloadable`.

## Source Inventory Service

Purpose:

- Merge source catalog, project registry, source status, project-provided metadata, and local file metadata into an inspectable source inventory.
- Preserve citation, attribution, licensing/terms, URL, access date, publication/metadata date, reviewer notes, and missing metadata gaps.
- Inspect local geospatial source files for CRS, bounds, feature count, geometry types, and validation issues.

Current implementation:

- Writes `projects/<project_id>/source_inventory/source_inventory.json`.
- CLI command: `review-assist generate-source-inventory <project_dir>`.
- Project source registry entries support an optional `metadata` object for citation/provenance fields.
- Missing or unreadable local source files create validation issues instead of invented provenance.

## Constraint Analysis Service

Purpose:

- Run deterministic GIS checks such as intersections, overlays, buffers, nearest-neighbor checks, crossing counts, and length/area summaries.
- Return structured objective constraint results, not narrative.

Examples:

- Alternative intersects NWI wetland polygon.
- Alternative crosses NHD stream line.
- Corridor buffer overlaps FEMA floodway.
- Alternative is within configured distance of a community facility.
- Alternative overlaps an existing disturbed corridor.

Current implementation:

- CLI command: `review-assist analyze-constraints <project_dir>`.
- Loads normalized project features and analysis bounds, building them first when needed.
- Loads enabled registered local source layers, including downloaded public sources that source acquisition registered as local files.
- Crops source layers to project analysis bounds and writes clipped layers under `projects/<project_id>/constraints/clipped_layers/`.
- Emits `intersects`, `crosses`, `contains`, `overlaps`, and `nearest_within_buffer` relationship records.
- Preserves project feature id/name/group/geometry role, source id/name/category, source feature labels, provenance, and length/area/distance measurements where available.
- Writes `projects/<project_id>/constraints/constraint_results.json`.
- Does not rank, score, recommend, choose, or reject project features.

## Legacy Spatial Analysis Service

Purpose:

- Keep the earlier raw spatial relationship command available for backward-compatible checks.
- Return structured spatial relationships, not narrative.

Current implementation:

- Loads enabled project-local source layers.
- Clips/filter-checks sources against project geometry plus configurable buffer.
- Emits `intersects`, `crosses`, and `within_buffer` relationship records.
- Preserves source id, source category, method, CRS, buffer, feature labels, and basic length/area/distance measurements where available.
- Validates non-negative project default buffers before analysis.

The service currently produces spatial relationship records only. It does not generate findings or report language, and it is no longer the primary populate-for-review path.

The standalone `analyze-project` command remains strict for missing local source files. The populate-for-review orchestration uses a tolerant analysis mode that records missing or unreadable local source layers as validation issues and continues when possible.

Open questions:

- Which checks are highest value for v1?
- What distance thresholds should be project defaults?
- Which checks require geometry cleaning before execution?

## Findings Generation Service

Purpose:

- Convert deterministic constraint results, legacy spatial relationships, source status records, and reviewer-supplied context into structured draft findings.
- Attach implication candidates such as permitting coordination, field verification, or utility coordination.
- Preserve evidence type, source, method, geometry assumptions, and uncertainty.

This service should not rank alternatives or choose a preferred alternative.

See `docs/FINDING_TYPES.md` and `docs/UNCERTAINTY_AND_PROVENANCE.md`.

Current implementation:

- Template config lives at `config/finding_templates.json`.
- The service reads project context, source status, optional constraint results, optional legacy spatial relationships, and finding templates.
- It writes `projects/<project_id>/findings/draft_findings.json`.
- It creates deterministic draft finding records for report-relevant source-unavailable/deferred categories, source-backed constraint results when present, legacy spatial relationships when needed, and analyzed local sources with no mapped relationships.
- The CLI command is `review-assist generate-findings <project_dir>`.
- Finding IDs are deterministic so review queue regeneration can preserve reviewer status and notes.

Findings are emitted as review queue items, not direct report content.

## Comparison Table Service

Purpose:

- Convert source status, constraint result, legacy spatial relationship, and draft finding artifacts into descriptive table artifacts.
- Prepare structured table data for future maps, report exports, and UI previews without producing final report content.
- Avoid ranking, scoring, or preferred-alternative language.

Current implementation:

- Writes `projects/<project_id>/tables/comparison_tables.json`.
- CLI command: `review-assist generate-tables <project_dir>`.
- Generates source status, constraint result, legacy spatial relationship, and draft finding summary tables.
- Tables become review queue items with preview metadata before export.

## Imagery/Context Service

Purpose:

- Manage aerial imagery, basemaps, and visual review context.
- Generate or store cropped imagery for project areas.
- Support overlays for reviewer inspection.
- Capture imagery-observed review items.

Imagery-observed features should remain review items unless a reviewer validates and documents them.

See `docs/IMAGERY_REVIEW.md` and `docs/MAP_GENERATION.md`.

## Map/Figure Generation Service

Purpose:

- Generate report-ready static figures.
- Create overall maps, resource maps, and panel maps.
- Render legends, scale/context, figure titles, source notes, and draft labels.
- Export PNG/PDF/SVG or other figure formats.

Current implementation:

- Writes `projects/<project_id>/maps/map_manifest.json`.
- Writes PNG draft figures under `projects/<project_id>/maps/figures/`.
- CLI command: `review-assist generate-maps <project_dir>`.
- Renders a project overview from normalized project geometry.
- Renders source-context maps for analyzed local source clipped layers from constraint results when available, with legacy spatial relationship artifacts as fallback.
- Uses GeoPandas and Matplotlib only; no basemap, raster, imagery, Contextily, or Rasterio path exists yet.
- Map figures become review queue items with preview metadata before export.

Likely future stack:

- GeoPandas for vector layers.
- Matplotlib for static figure rendering.
- Contextily or rasterio for basemap tiles or local raster basemaps.
- Later, ArcGIS/QGIS integration may be considered if needed.

See `docs/MAP_GENERATION.md`.

Generated maps and figure previews should become review queue items before export. The current baseline implements this for vector-only PNG figures.

## Report Drafting Service

Purpose:

- Create draft narrative from structured findings and report taxonomy.
- Keep deterministic finding data separate from generated prose.
- Preserve citations, uncertainty, review status, and editable output.

LLM-assisted drafting is now available for report sections only, and the input is structured evidence, deterministic baseline copy, section metadata, IDs, and explicit source notes.

See `docs/REPORT_ASSEMBLY.md` and `docs/LLM_ASSISTED_SYNTHESIS.md`.

Generated narrative sections should become review queue items before export.

Current implementation:

- Template config lives at `config/report_section_templates.json`.
- The service reads project context, source status, source inventory, deterministic draft findings, comparison tables, optional map manifests, evidence packages, and validation issues.
- It writes `projects/<project_id>/drafts/report_sections.json`.
- It creates deterministic no-blank-page draft sections for project overview, methodology/data sources, limitations/missing data, resource categories, comparison summary, maps/figures, and reviewer follow-up.
- It writes `projects/<project_id>/evidence/evidence_package.json` through the evidence package service.
- It uses a section-drafting provider interface with deterministic and optional OpenAI GPT providers.
- GPT drafting is controlled by root `.env` (`OPENAI_API_KEY`, `OPENAI_INTERPRETER_MODEL`, `GPT_DRAFTING`) and can be disabled per run with `--no-gpt-drafting`.
- The CLI command is `review-assist generate-report-sections <project_dir>`.
- The evidence CLI command is `review-assist build-evidence-package <project_dir>`.
- Report section IDs are deterministic so review queue regeneration can preserve reviewer status, notes, edits, and export eligibility.

The current report drafting baseline feeds the export compiler but does not produce final conclusions or bypass review. GPT, when enabled, drafts pre-review section copy only from structured evidence and stores provider/model/prompt/schema/digest provenance.

## Compilation/Export Service

Purpose:

- Compile accepted or explicitly included reviewed findings, maps, tables, narrative, appendices, source notes, assumptions, and caveats into one editable package.
- Track what files were generated and what source evidence supports them.

Current implementation:

- The CLI command is `review-assist export-report <project_dir>`.
- The preview command is `review-assist export-report <project_dir> --include-draft`.
- The service writes `projects/<project_id>/exports/environmental_constraints_report.md` when Markdown output is requested.
- The service writes `projects/<project_id>/exports/environmental_constraints_report.docx` when DOCX output is requested.
- The service writes `projects/<project_id>/exports/export_manifest.json`.
- The demo package command writes `projects/<project_id>/exports/deliverable_package_manifest.json`.
- The MVP package command writes `projects/<project_id>/exports/deliverable_package_manifest.json` with a real-data package status and `data_lineage`.
- Default exports include accepted or edited queue items only, plus explicitly export-eligible `unable_to_verify` items.
- Preview exports include non-rejected draft/unaccepted items and mark the Markdown/DOCX as internal/pre-review.
- DOCX export embeds map figures when files are present, renders table previews where practical, and leaves explicit placeholders when visual/table artifacts are missing.
- Data lineage distinguishes project inputs, registered/provided/downloaded real source layers, manual/gated/missing stubs, and test/mock records. MVP deliverables fail by default when no real source layer is available and always fail when test fixture source records are included.

Future outputs:

- PDF report packages.
- Template-grade DOCX layout refinement.
- Excel/CSV comparison tables.
- PNG/PDF figures.
- GeoPackage or GeoJSON review layers.
- Reviewer audit log.

Open questions:

- How should the current DOCX compiler evolve toward the example report template?
- How should map figures be embedded and refreshed?
- Which companion table/map files should be copied into a final export bundle instead of referenced in place?

## Review Workflow Service

Purpose:

- Let human reviewers accept, reject, edit, annotate, or mark findings as unable to verify.
- Keep generated draft findings separate from reviewer-approved content.
- Preserve review history.
- Control export eligibility.

Review queue item types should include findings, report paragraphs, comparison tables, figures/maps, caveats, source notes, implication notes, missing-data placeholders, and reviewer notes.

Review statuses are defined in `docs/REVIEW_POLICY.md`.

Current implementation:

- Writes `projects/<project_id>/review_queue/review_queue.json`.
- Converts deterministic draft findings, comparison tables, map figures, report sections, report-relevant missing-data placeholders, no-mapped checks, and validation issues into a lean review queue by default.
- Source inventory/provenance records can be included explicitly for audit workflows with the `--include-source-inventory` flag.
- Supports CLI listing and status/note/export-eligibility updates.
- Supports downstream Markdown/DOCX export through review status and export eligibility.
- Does not yet provide web app review screens or reviewer-facing GPT controls.

## Populate For Review Service

Purpose:

- Provide the service-level backend for the future web app `Create Review Queue` action.
- Run current workflow steps in order: project context, project geometry normalization, optional local source materialization, optional source preparation, source status, source inventory, tolerant constraint analysis, deterministic draft finding generation, comparison table generation, map generation, evidence package generation, report section generation, and lean review queue generation.
- Write a run manifest with step statuses, artifact paths, warning records, constraint count, review queue item count for traceability only, and critical error text when a run fails.

Current implementation writes `projects/<project_id>/populate_for_review/populate_for_review_run.json` through the `populate-for-review` CLI command. It records context, project geometry, project features, analysis bounds, optional source materialization, optional source acquisition, source status, source inventory, constraint results, draft findings, comparison table, map manifest, evidence package, report section, and review queue artifact paths. It materializes local warehouse data only when `--materialize-local-sources` is used and downloads supported public sources only when `--prepare-sources` is used; it does not render basemap/imagery-backed maps, create exports itself, or make recommendations.

## LLM Boundary

LLM calls may be used for narrative drafting, summarization, implication phrasing, finding normalization, or sanity checks.

LLM calls must not:

- Run or replace deterministic GIS checks.
- Invent unsupported facts.
- Hide missing data.
- Produce unreviewable final conclusions.
- Recommend or select a preferred alternative.

## Open Architecture Questions

- Should review queue items be stored as JSON files, SQLite rows, or another local format?
- When should source status, review queue, and draft artifacts move from JSON files to SQLite or another local workspace database?
- Which deterministic source checks should be prioritized after the current baseline?
- How should large source layers and generated raster outputs be stored outside Git?
- What review UI is needed before report export is useful?
- What exact rules make an item export eligible?
- What final PDF/export package format should follow the current DOCX package?
- How should restricted cultural resource information be represented without exposing sensitive data?

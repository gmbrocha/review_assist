# Architecture

This document captures the current architecture direction. Prototype service and CLI implementations exist for ingestion, source catalog/registry handling, local source registration, and early spatial relationship checks. No production desktop app, review queue, or report workflow exists yet.

The canonical workflow model is `docs/WORKFLOW_MODEL.md`. This architecture should support that model without over-engineering it.

The system should stay modular enough to support multiple project types while avoiding premature complexity. The likely shape is a thin desktop shell over small services that pass structured workspace, project context, source status, geometry, review item, map, table, narrative, and export artifacts between each other.

## Canonical Workflow Architecture

The application workflow is stateful and workspace-driven:

1. Open or create a workspace.
2. Add project inputs.
3. Generate persistent project context.
4. Resolve needed data categories into a source status set.
5. Populate for review.
6. Review every generated item in the review queue.
7. Compile accepted content into export packages.

The review queue is the primary workflow boundary. Generated findings, draft paragraphs, maps, tables, caveats, source notes, and implication notes should become review queue items before they are eligible for export.

## Core State Objects

Conceptual state objects:

- Workspace/project manifest.
- Project context artifact.
- Source catalog.
- Source status set.
- Normalized project geometry.
- Spatial relationship records.
- Review queue items.
- Export manifest.

The current code implements early versions of project manifests, report profiles, source catalog entries, project source registries, project context artifacts, source status sets, normalized GeoJSON intermediates, and spatial relationship records. Review queue persistence and export manifests remain future work.

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
- `context/`
- `source_status/`
- `review_queue/`
- `findings/`
- `maps/`
- `drafts/`
- `exports/`
- `review/`

Some folders are current, while others remain future placeholders. `inputs/`, `config/`, generated `intermediate/`, generated `context/`, and generated `source_status/` outputs are currently used. `layers/` is reserved for local source layers and is ignored by Git. `review_queue/`, `findings/`, `maps/`, `drafts/`, `exports/`, and `review/` remain future workflow areas.

Phase 1 currently writes generated GeoJSON and geometry summary artifacts under `intermediate/`. Phase 2B writes clipped source GeoJSON files and `spatial_relationships.json` under `intermediate/`.

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
- Local-file registration is the default Phase 2 path; live downloads are deferred.
- Registry loading validates project IDs, duplicate source IDs, boolean enabled flags, and non-negative source buffer overrides.

This service should not silently call paid services, use credentials, or access restricted systems without explicit approval.

Open questions:

- Which sources are required for the first real prototype?
- Should source layers be cached per project or globally?
- How should stale source layers be flagged?

## Source Status Tracking Service

Purpose:

- Compare required source categories for the report profile against local, downloadable, restricted, missing, stubbed, and optional sources.
- Produce and maintain the `SOURCE_STATUS_SET`.
- Create placeholders and review requirements for missing/gated data instead of failing the workflow.

Suggested statuses are defined in `docs/WORKFLOW_MODEL.md`:

- `provided_locally`
- `downloadable`
- `downloaded`
- `gated`
- `stubbed`
- `missing`
- `optional`
- `needs_review`

Current implementation writes `projects/<project_id>/source_status/source_status_set.json` through the `resolve-sources` CLI command. Current project source registries are an early foundation.

## Spatial Analysis Service

Purpose:

- Run deterministic GIS checks such as intersections, overlays, buffers, nearest-neighbor checks, crossing counts, and length/area summaries.
- Return structured spatial relationships, not narrative.

Examples:

- Alternative intersects NWI wetland polygon.
- Alternative crosses NHD stream line.
- Corridor buffer overlaps FEMA floodway.
- Alternative is within configured distance of a community facility.
- Alternative overlaps an existing disturbed corridor.

Current implementation:

- Loads enabled project-local source layers.
- Clips/filter-checks sources against project geometry plus configurable buffer.
- Emits `intersects`, `crosses`, and `within_buffer` relationship records.
- Preserves source id, source category, method, CRS, buffer, feature labels, and basic length/area/distance measurements where available.
- Validates non-negative project default buffers before analysis.

The service currently produces spatial relationship records only. It does not generate findings or report language.

Open questions:

- Which checks are highest value for v1?
- What distance thresholds should be project defaults?
- Which checks require geometry cleaning before execution?

## Findings Generation Service

Purpose:

- Convert deterministic spatial relationships and reviewer-supplied context into structured draft findings.
- Attach implication candidates such as permitting coordination, field verification, or utility coordination.
- Preserve evidence type, source, method, geometry assumptions, and uncertainty.

This service should not rank alternatives or choose a preferred alternative.

See `docs/FINDING_TYPES.md` and `docs/UNCERTAINTY_AND_PROVENANCE.md`.

Findings should be emitted as review queue items, not direct report content.

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

Likely future stack:

- GeoPandas for vector layers.
- Matplotlib for static figure rendering.
- Contextily or rasterio for basemap tiles or local raster basemaps.
- Later, ArcGIS/QGIS integration may be considered if needed.

See `docs/MAP_GENERATION.md`.

Generated maps and figure previews should become review queue items before export.

## Report Drafting Service

Purpose:

- Create draft narrative from structured findings and report taxonomy.
- Keep deterministic finding data separate from generated prose.
- Preserve citations, uncertainty, review status, and editable output.

LLM-assisted drafting may be useful here, but the input should be structured findings and explicit source notes.

See `docs/REPORT_ASSEMBLY.md` and `docs/LLM_ASSISTED_SYNTHESIS.md`.

Generated narrative sections should become review queue items before export.

## Compilation/Export Service

Purpose:

- Compile accepted or explicitly included reviewed findings, maps, tables, narrative, appendices, source notes, assumptions, and caveats into one editable package.
- Track what files were generated and what source evidence supports them.

Possible future outputs:

- DOCX draft report.
- Markdown review package.
- Excel/CSV comparison tables.
- PNG/PDF figures.
- GeoPackage or GeoJSON review layers.
- Reviewer audit log.

Open questions:

- Should DOCX be the first formal export?
- How should map figures be embedded and refreshed?
- What package manifest is needed for traceability?

## Review Workflow Service

Purpose:

- Let human reviewers accept, reject, edit, annotate, or mark findings as unable to verify.
- Keep generated draft findings separate from reviewer-approved content.
- Preserve review history.
- Control export eligibility.

Review queue item types should include findings, report paragraphs, comparison tables, figures/maps, caveats, source notes, implication notes, missing-data placeholders, and reviewer notes.

Review statuses are defined in `docs/REVIEW_POLICY.md`.

## LLM Boundary

LLM calls may be used for narrative drafting, summarization, implication phrasing, finding normalization, or sanity checks.

LLM calls must not:

- Run or replace deterministic GIS checks.
- Invent unsupported facts.
- Hide missing data.
- Produce unreviewable final conclusions.
- Recommend or select a preferred alternative.

## Open Architecture Questions

- What project context artifact should sit alongside the current project manifest?
- Should source status sets be JSON, SQLite records, or part of a larger workspace database?
- Should review queue items be stored as JSON files, SQLite rows, or another local format?
- Which geospatial dependency stack should be standardized for Windows development?
- How should large source layers and generated raster outputs be stored outside Git?
- What review UI is needed before report export is useful?
- What exact rules make an item export eligible?
- How should restricted cultural resource information be represented without exposing sensitive data?

# Architecture

This document captures the current conceptual architecture direction. No production implementation exists yet.

The system should stay modular enough to support multiple project types while avoiding premature complexity. The likely shape is a set of small services or modules that pass structured project, source, geometry, finding, map, and report artifacts between each other.

## High-Level Pipeline

1. Ingest project files.
2. Normalize project footprint and alternative geometries.
3. Acquire or load source layers.
4. Run deterministic spatial checks.
5. Convert spatial relationships into draft findings.
6. Generate maps, tables, and contextual implications.
7. Draft narrative from structured findings.
8. Compile an editable pre-review package.
9. Support human review, edits, acceptance, rejection, and export.

## Project Workspace Layer

Project workspaces should isolate project-specific inputs, generated intermediates, reviewer notes, maps, draft reports, and exports.

Current workspaces:

- `projects/trails`
- `projects/conexon_projects`

Phase 1 workspaces include `config/project.json` manifests and copied KMZ inputs under `inputs/`. Phase 2A workspaces include `config/sources.json` source registries.

Future project folders may contain:

- `inputs/`
- `layers/`
- `intermediate/`
- `findings/`
- `maps/`
- `drafts/`
- `exports/`
- `review/`

This structure is not implemented yet.

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

This service should not silently call paid services, use credentials, or access restricted systems without explicit approval.

Open questions:

- Which sources are required for the first real prototype?
- Should source layers be cached per project or globally?
- How should stale source layers be flagged?

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

## Report Drafting Service

Purpose:

- Create draft narrative from structured findings and report taxonomy.
- Keep deterministic finding data separate from generated prose.
- Preserve citations, uncertainty, review status, and editable output.

LLM-assisted drafting may be useful here, but the input should be structured findings and explicit source notes.

See `docs/REPORT_ASSEMBLY.md` and `docs/LLM_ASSISTED_SYNTHESIS.md`.

## Compilation/Export Service

Purpose:

- Compile findings, maps, tables, narrative, appendices, source notes, and review status into one editable pre-review package.
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

- What project manifest format should define inputs, defaults, sources, and outputs?
- Which geospatial dependency stack should be standardized for Windows development?
- How should large source layers and generated raster outputs be stored outside Git?
- What review UI is needed before report export is useful?
- How should restricted cultural resource information be represented without exposing sensitive data?

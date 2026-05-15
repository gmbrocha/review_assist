# Roadmap

This roadmap is intentionally rough and may change as requirements are clarified.

Before large implementation work, read `../PLAN_REDIRECT.md`. That document is the drift-control destination for the app: use the example environmental constraints report as the structural template and build the system to fill that template with source-backed constraints, visuals, reviewable copy, tables, caveats, and accepted export content.

## Core Product Shape: Constraint Engine Plus Review Queue

The product is not a generic report-item generator. The durable workflow is:

1. Parse project geometry from KMZ/KML or later supported GIS inputs.
2. Classify and normalize the input geometry as point/site, line/corridor, polygon/area, or mixed project context.
3. Reconstruct meaningful project alternatives or service areas from the input geometry, including joining line-string/polyline pieces into full alternatives where needed.
4. Derive the project analysis bounds from the normalized geometry plus configurable buffer assumptions.
5. Load, acquire, or register relevant source layers and documents.
6. Crop source layers to the project analysis bounds.
7. Run objective constraint overlap/proximity checks by project feature, alternative, site, service area, and resource category as appropriate for the geometry type.
8. Convert source-backed results into structured constraint findings.
9. Draft small report sections from those findings, source notes, and uncertainty records.
10. Send findings, draft sections, tables, maps, caveats, and source notes into the review queue.
11. Export only reviewer-accepted or explicitly included items.

The review queue remains central, but it is downstream of the constraint engine. Review queue item count is not a readiness metric. A useful run is one that correctly parses the alternatives, crops/loads relevant sources, identifies objective constraints, preserves no-conflict and missing-source context where report-relevant, and creates editable report sections that a human can review independently.

The tool presents objective constraints for each project feature, service location, service area, route, corridor, site, or alternative. It does not choose, recommend, rank, or reject a trail, broadband service location, project area, or other alternative.

The current `trails` and `conexon_projects` workspaces are examples, not product boundaries. The constraint engine should be a blank project machine that accepts a project KMZ/KML, infers or asks for the intended geometry role, applies appropriate bounds/buffer logic, and runs the same source-backed constraint workflow.

## Phase 0: Scaffold and Clarify Requirements

Status: complete.

- Establish repository structure.
- Document product boundaries.
- Confirm initial input and output expectations.
- Identify first candidate data sources.
- Create project workspaces for current example projects.
- Document report taxonomy, finding types, uncertainty, provenance, map-generation direction, and report assembly direction.
- Record first-version desktop direction, with the review queue as the spine.
- Record source stack, archive conventions, and Phase 1 implementation defaults.

## Phase 1: Parse KMZ/KML and Inspect Geometries

Status: complete for the current prototype baseline.

Implementation defaults:

- Services plus CLI first; no GUI work in this phase.
- GeoPandas is the standard geospatial dependency path.
- Real KMZ inputs are copied into project `inputs/` folders while root originals remain as reference files.
- Project manifests use JSON.
- Normalized geometry outputs use GeoJSON.
- Geometry summaries use JSON.

- Parse KMZ and KML files.
- Identify project footprints and alternatives.
- Display or summarize geometry metadata.
- Report validation issues.
- Move or reference real KMZ inputs from project workspaces.
- Standardize a geospatial Python dependency plan, likely including GeoPandas.

Phase 1 remains limited to ingestion and geometry inspection. It does not generate findings, run source-layer spatial analysis, generate reports, implement a GUI, query external APIs, or decide preferred alternatives.

## Phase 2A: Source Catalog and Source Population

Status: initial baseline complete.

- Define a broad source catalog covering water, land, species, cultural, regulated facilities, community, infrastructure, parcel, imagery, and flood context.
- Create project source registries that can enable or disable candidate sources per project.
- Support local source-layer registration before implementing fragile live downloads.
- Treat restricted, manual, and reviewer-supplied sources as explicit placeholders.
- Track source category, publisher, access method, public/restricted status, limitations, and intended spatial relationships.

Flood hazard is cataloged as a secondary optional source. It is not a core first-pass driver for every project.

## Phase 2B: Local Layer Clipping and Spatial Relationship Checks

Status: initial baseline complete; retained as a legacy/raw spatial analysis path.

- Load enabled project-local source layers.
- Clip or filter layers to the project geometry and configured review buffer.
- Run deterministic spatial checks for `intersects`, `crosses`, and `within_buffer`.
- Preserve source, method, CRS, buffer, and measurement metadata.
- Produce `spatial_relationships.json` before findings, narrative, maps, or report drafting.

Phase 2B still does not create findings, review queue records, maps, reports, rankings, recommendations, or final conclusions. The main workflow now routes through project geometry normalization and `analyze-constraints`; `analyze-project` remains available for backward-compatible raw spatial relationship checks.

## Phase 2C: Catalog-Driven Source Acquisition

Status: NWI plus USGS NHD hydrography downloader baseline complete; FEMA NFHL effective flood hazard downloader implemented as optional context.

- Compare project inputs, project source registries, and report-profile source needs against the source catalog.
- Treat project inputs tagged with `source_id` or unambiguous `source_category` as provided source layers and register them for analysis.
- Write a first-class source acquisition manifest at `projects/<project_id>/source_acquisition/source_acquisition_manifest.json`.
- Store downloaded public source layers under ignored `projects/<project_id>/source_acquisition/downloads/`.
- Preserve local/reviewer-supplied source layers; downloads do not overwrite them.
- Download USFWS National Wetlands Inventory wetlands through the public Wetlands REST MapServer layer when explicitly requested.
- Download USGS National Hydrography Dataset hydrography through The National Map NHD MapServer large-scale flowline and area layers when explicitly requested.
- Download FEMA National Flood Hazard Layer effective Flood Hazard Zones through public NFHL MapServer layer 28 when explicitly requested.
- Record source URL, service URL/layer, access date, requested bounds, output path, feature count, checksum, limitations, warnings, per-layer provenance, and failures.
- Add normalized Review Assist source/layer/label/type/subtype/original-id/date/quality/source-citation fields to downloaded layers where available while preserving original source attributes.
- Register successful downloads as normal project `local_file` sources with `status: downloaded` so the constraint engine consumes them without a special case.

Current baseline:

- `review-assist resolve-source-gaps <project_dir>`
- `review-assist download-source <project_dir> usfws_nwi_wetlands`
- `review-assist download-source <project_dir> usgs_nhd_hydrography`
- `review-assist download-source <project_dir> fema_nfhl_flood_hazard`
- `review-assist prepare-sources <project_dir>`
- `review-assist prepare-sources <project_dir> --include-optional-sources`
- `review-assist populate-for-review <project_dir> --prepare-sources`
- `review-assist populate-for-review <project_dir> --prepare-sources --include-optional-sources`

Live downloads remain opt-in. Running `populate-for-review` without `--prepare-sources` preserves the previous no-live-download behavior. FEMA flood hazard remains optional unless directly downloaded or optional-source acquisition is requested with `--include-optional-sources`.

## Phase 3: Workspace Context and Source Status Model

Status: initial baseline complete.

- Create a persistent project context artifact derived from project inputs, geometry summaries, assumptions, report profile, source inventory, and reviewer instructions.
- Define the source status set for required report categories.
- Compare needed sources against locally provided, downloadable, downloaded, failed, gated, stubbed, missing, optional, and needs-review sources.
- Generate placeholders and uncertainty flags for missing/gated data instead of failing the workflow.
- Keep buffer/corridor assumptions configurable and visible.

Current baseline:

- `review-assist generate-context <project_dir>`
- `review-assist resolve-sources <project_dir>`
- JSON artifacts under project `context/` and `source_status/` directories.

## Phase 4: Review Queue Domain Model

Status: initial baseline complete.

- Define review queue item fields.
- Add review statuses and reviewer actions.
- Support reviewer notes and edits.
- Track assumptions, provenance, uncertainty, and export eligibility.
- Convert constraint-backed findings, no-conflict checks, report-relevant source flags, maps, tables, caveats, and draft narrative sections into reviewable items.

The review queue is the spine: every generated artifact must become a reviewable item before export.

Current baseline:

- `review-assist generate-review-queue <project_dir>`
- `review-assist list-review-queue <project_dir>`
- `review-assist update-review-item <project_dir> <item_id> --status <status>`
- JSON artifact at `projects/<project_id>/review_queue/review_queue.json`.

The baseline defaults to a lean queue from deterministic draft findings, comparison tables, map figures, deterministic report sections, report-relevant missing-data placeholders, no-mapped-relationship checks, and validation issues. Source inventory/provenance notes are opt-in for audit workflows. Queue items now carry export-group metadata for report assembly. It does not yet provide GUI review screens or use LLM-assisted narrative.

## Phase 5: Populate for Review

Status: initial orchestration baseline complete.

- Create the service-level workflow behind the future `Populate for Review` action.
- Acquire or load approved sources where possible.
- Clip/crop sources to project extent.
- Build normalized project geometry and run deterministic constraint checks.
- Generate findings, caveats, implication notes, source notes, tables, maps, and draft narrative as review queue items.
- Keep deterministic GIS/source checks separate from LLM-assisted narrative synthesis.

Current baseline:

- `review-assist populate-for-review <project_dir>`
- JSON run manifest at `projects/<project_id>/populate_for_review/populate_for_review_run.json`.
- Runs project context generation, project geometry normalization, source status resolution, source inventory generation, tolerant constraint analysis, deterministic draft finding generation, comparison table generation, map generation, report section generation, and lean review queue generation.
- Missing or unreadable local source layers are recorded as warnings/review items in populate mode while the standalone `analyze-project` command remains strict for the legacy raw spatial check path.
- `--prepare-sources` resolves catalog gaps and runs supported required public downloaders before source status, source inventory, constraints, findings, tables, maps, sections, and review queue generation.
- `--include-optional-sources`, when paired with `--prepare-sources`, also downloads supported optional sources such as FEMA NFHL flood hazard.

This baseline now includes vector-only map generation through Phase 6C, deterministic report section generation through Phase 6D, and explicit NWI plus USGS NHD hydrography source acquisition through Phase 2C, but `populate-for-review` does not create exports itself, implement GUI review screens, render basemap/imagery-backed maps, or use LLM-assisted narrative.

## Phase 6A: Deterministic Finding Templates

Status: initial baseline complete.

- Convert source status records, first-class constraint result records, and legacy deterministic spatial relationship records into report-shaped draft finding records.
- Preserve cautious implication language, evidence class, provenance, assumptions, source ids, uncertainty flags, and review status.
- Generate missing/gated/stubbed/downloadable source findings instead of blocking the workflow.
- Generate no-mapped-relationship findings where an analyzed local source produces no relationships.
- Feed draft findings into the review queue while preserving reviewer state through deterministic IDs.

Current baseline:

- Template config at `config/finding_templates.json`.
- `review-assist generate-findings <project_dir>`
- JSON artifact at `projects/<project_id>/findings/draft_findings.json`.
- `populate-for-review` runs finding generation before review queue generation and records the artifact path in the run manifest.

This baseline does not rank, score, recommend, produce final conclusions, generate final report tables, draft report prose, call LLMs, or compile exports.

## Phase 6B: Source Provenance and Comparison Tables

Status: initial baseline complete.

- Generate a source inventory artifact with catalog, registry, source status, local file metadata, optional project-supplied source metadata, and validation issues.
- Support optional per-source registry metadata for citations, attribution, source URL, access date, publication/metadata dates, license/terms, and reviewer notes.
- Generate descriptive comparison table artifacts for source status, constraint results, grouped feature/category constraints, hydrography crossings, FEMA flood hazard, spatial relationships, and draft findings.
- Feed comparison tables into the review queue with deterministic item IDs, with source inventory records available as opt-in audit review items.

Current baseline:

- `review-assist generate-source-inventory <project_dir>`
- `review-assist generate-tables <project_dir>`
- JSON source inventory at `projects/<project_id>/source_inventory/source_inventory.json`.
- JSON comparison tables at `projects/<project_id>/tables/comparison_tables.json`.
- `populate-for-review` records both artifact paths and sends generated records/tables into the review queue.

This baseline now records source acquisition provenance when present and includes report-ready grouped, hydrography, and flood hazard summary tables when source-backed constraints exist. It does not render final map images, draft GPT report prose, compile exports, rank alternatives, or recommend preferred options.

## Phase 6C: Map/Figure and Imagery Generation

Status: initial vector-only map baseline complete.

- Generate overall project maps.
- Generate resource-specific maps.
- Generate panel maps where useful.
- Preserve legends, source notes, draft labels, and map provenance.
- Prepare basemap/imagery review overlays where source terms allow.
- Store map, figure, and imagery observations as review queue items.

Current baseline:

- `review-assist generate-maps <project_dir>`
- JSON map manifest at `projects/<project_id>/maps/map_manifest.json`.
- PNG draft figures under `projects/<project_id>/maps/figures/`.
- Generates a project overview figure from normalized project geometry.
- Generates source-context figures for analyzed local source clipped layers when available.
- Uses GeoPandas and Matplotlib only; maps are vector-only and contain no basemap or imagery.
- `populate-for-review` runs map generation after comparison table generation and before review queue generation.
- Review queue generation converts map figures into `map_figure` items with deterministic IDs and preview metadata.

This baseline does not implement basemap tiles, local raster imagery, NAIP/Google/ArcGIS acquisition, panel map sheets, PDF/SVG exports, final cartographic styling, or map package compilation.

## Phase 6D: Deterministic Draft Report Sections

Status: initial baseline complete.

- Generate no-blank-page draft report section artifacts from existing workflow artifacts.
- Keep deterministic section drafting separate from LLM-assisted synthesis and export compilation.
- Preserve source refs, related finding/table/figure IDs, assumptions, provenance, uncertainty flags, validation issues, and review status.
- Feed report sections into the review queue with deterministic IDs so reviewer status and notes survive regeneration.

Current baseline:

- Template config at `config/report_section_templates.json`.
- `review-assist generate-report-sections <project_dir>`
- JSON section artifact at `projects/<project_id>/drafts/report_sections.json`.
- Generates project overview, methodology/data sources, limitations/missing data, resource sections, comparison summary, maps/figures, and reviewer follow-up sections.
- `populate-for-review` runs report section generation after map generation and before review queue generation.
- Review queue generation converts report sections into `report_section` items with section metadata and related artifact IDs.

This baseline now mirrors the example environmental constraints report more closely with front matter, executive summary, introduction/study area, methodology subsections, environmental constraints inventory, resource sections, conclusion/next steps, attachments, visual slots, and table slots.

This baseline does not create DOCX/PDF exports, call LLMs, generate final conclusions, rank alternatives, or bypass review queue acceptance.

## Constraint Core Slice: Geometry, Constraint Results, and Lean Queue

Status: initial baseline complete.

- `review-assist build-project-geometry <project_dir>` writes normalized project geometry artifacts under `intermediate/`.
- Geometry is classified as point/site, line/corridor, polygon/area, or mixed.
- Segmented line strings are grouped by placemark name, style URL, and candidate label, then connected pieces are merged without inventing missing connections.
- Point-heavy projects preserve individual point features and style/color grouping metadata.
- `review-assist analyze-constraints <project_dir>` uses registered local source layers only, crops them to project analysis bounds, and writes `projects/<project_id>/constraints/constraint_results.json`.
- Constraint results preserve project feature identity, source identity/category, relationship type, source feature labels, provenance, and available length/area/distance measurements.
- `generate-findings` prefers constraint results when present.
- `generate-tables` adds constraint summary, grouped constraint summary, hydrography crossing summary, and FEMA flood hazard summary tables when relevant constraint results exist.
- `populate-for-review` now routes through constraint analysis before findings/tables/maps/sections/queue generation.
- `generate-review-queue` defaults to useful report-facing items instead of source-inventory/source-status volume; source inventory notes are available with `--include-source-inventory`.

This slice uses deterministic drafting only. The section-drafting provider interface exists for future GenAI, but no live OpenAI/GenAI calls are made.

## Phase 7: Export Compilation

Status: first Markdown export baseline complete.

- Compile accepted and edited review queue items by default.
- Include `unable_to_verify` items only when explicitly export eligible.
- Exclude draft, needs-review, needs-verification, and rejected items from default exports.
- Generate editable Markdown report packages.
- Generate an export manifest with included/skipped items, status/type counts, warnings, and source-gap caveats.
- Preserve section order from report section artifacts.
- Reference accepted/edited maps and tables by artifact path rather than embedding binaries.
- Provide `--include-draft` only for internal preview exports, clearly labeled as not ready for external use.

Current baseline:

- `review-assist export-report <project_dir>`
- `review-assist export-report <project_dir> --include-draft`
- JSON manifest at `projects/<project_id>/exports/export_manifest.json`
- Markdown report at `projects/<project_id>/exports/environmental_constraints_report.md`

Next export milestone:

- Add DOCX export after Markdown proves accepted-content assembly, ordering, provenance, figure/table references, caveat handling, and reviewer-state behavior.

## Phase 8: Optional AI-Assisted Narrative Synthesis

- Explore AI-assisted drafting after deterministic checks and review workflow are defined.
- Keep narrative synthesis traceable to source findings.
- Preserve uncertainty and human review requirements.
- Use LLMs for draft language, implication phrasing, summary checks, and structured normalization without replacing source-backed analysis.

## Still Out of Scope

- Production GIS pipelines.
- Paid service integrations.
- MDAH restricted access integration.
- Autonomous ranking or recommendation logic.
- Field-verified conclusions.
- Black-box report generation.

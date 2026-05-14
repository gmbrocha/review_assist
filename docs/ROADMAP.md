# Roadmap

This roadmap is intentionally rough and may change as requirements are clarified.

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

Status: initial baseline complete.

- Load enabled project-local source layers.
- Clip or filter layers to the project geometry and configured review buffer.
- Run deterministic spatial checks for `intersects`, `crosses`, and `within_buffer`.
- Preserve source, method, CRS, buffer, and measurement metadata.
- Produce `spatial_relationships.json` before findings, narrative, maps, or report drafting.

Phase 2B still does not create findings, review queue records, maps, reports, rankings, recommendations, or final conclusions.

## Phase 3: Workspace Context and Source Status Model

Status: initial baseline complete.

- Create a persistent project context artifact derived from project inputs, geometry summaries, assumptions, report profile, source inventory, and reviewer instructions.
- Define the source status set for required report categories.
- Compare needed sources against locally provided, downloadable, downloaded, gated, stubbed, missing, optional, and needs-review sources.
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
- Convert spatial relationships, no-conflict checks, source status flags, maps, tables, caveats, and draft narrative into reviewable items.

The review queue is the spine: every generated artifact must become a reviewable item before export.

Current baseline:

- `review-assist generate-review-queue <project_dir>`
- `review-assist list-review-queue <project_dir>`
- `review-assist update-review-item <project_dir> <item_id> --status <status>`
- JSON artifact at `projects/<project_id>/review_queue/review_queue.json`.

The baseline converts current source inventory records, deterministic draft findings, comparison tables, source status records, deterministic spatial relationships, no-mapped-relationship checks, and validation issues into review queue items. It does not yet generate report prose, rendered maps, exports, GUI review screens, or LLM-assisted narrative.

## Phase 5: Populate for Review

Status: initial orchestration baseline complete.

- Create the service-level workflow behind the future `Populate for Review` action.
- Acquire or load approved sources where possible.
- Clip/crop sources to project extent.
- Run deterministic spatial checks.
- Generate findings, caveats, implication notes, source notes, tables, maps, and draft narrative as review queue items.
- Keep deterministic GIS/source checks separate from LLM-assisted narrative synthesis.

Current baseline:

- `review-assist populate-for-review <project_dir>`
- JSON run manifest at `projects/<project_id>/populate_for_review/populate_for_review_run.json`.
- Runs project context generation, source status resolution, source inventory generation, tolerant local spatial analysis, deterministic draft finding generation, comparison table generation, and review queue generation.
- Missing or unreadable local source layers are recorded as warnings/review items in populate mode while the standalone `analyze-project` command remains strict.

This baseline does not yet render maps, generate report prose, compile exports, implement GUI review screens, download sources, or use LLM-assisted narrative.

## Phase 6A: Deterministic Finding Templates

Status: initial baseline complete.

- Convert source status records and deterministic spatial relationship records into report-shaped draft finding records.
- Preserve cautious implication language, evidence class, provenance, assumptions, source ids, uncertainty flags, and review status.
- Generate missing/gated/stubbed/downloadable source findings instead of blocking the workflow.
- Generate no-mapped-relationship findings where an analyzed local source produces no relationships.
- Feed draft findings into the review queue while preserving reviewer state through deterministic IDs.

Current baseline:

- Template config at `config/finding_templates.json`.
- `review-assist generate-findings <project_dir>`
- JSON artifact at `projects/<project_id>/findings/draft_findings.json`.
- `populate-for-review` runs finding generation before review queue generation and records the artifact path in the run manifest.

This baseline does not rank, score, recommend, produce final conclusions, render maps, generate final report tables, draft report prose, call LLMs, or compile exports.

## Phase 6B: Source Provenance and Comparison Tables

Status: initial baseline complete.

- Generate a source inventory artifact with catalog, registry, source status, local file metadata, optional project-supplied source metadata, and validation issues.
- Support optional per-source registry metadata for citations, attribution, source URL, access date, publication/metadata dates, license/terms, and reviewer notes.
- Generate descriptive comparison table artifacts for source status, spatial relationships, and draft findings.
- Feed source inventory records and comparison tables into the review queue with deterministic item IDs.

Current baseline:

- `review-assist generate-source-inventory <project_dir>`
- `review-assist generate-tables <project_dir>`
- JSON source inventory at `projects/<project_id>/source_inventory/source_inventory.json`.
- JSON comparison tables at `projects/<project_id>/tables/comparison_tables.json`.
- `populate-for-review` records both artifact paths and sends generated records/tables into the review queue.

This baseline does not download sources, render map images, draft report prose, compile exports, rank alternatives, or recommend preferred options.

## Phase 6C: Map/Figure and Imagery Generation

Status: next likely implementation area.

- Generate overall project maps.
- Generate resource-specific maps.
- Generate panel maps where useful.
- Preserve legends, source notes, draft labels, and map provenance.
- Prepare basemap/imagery review overlays where source terms allow.
- Store map, figure, and imagery observations as review queue items.

## Phase 7: Export Compilation

- Compile accepted and explicitly included reviewed items only.
- Generate editable draft report packages.
- Include maps, tables, findings, source notes, review status, assumptions, and caveats.
- Keep generated reports clearly labeled as pre-review drafts.
- Compile appendices/reference materials where available.
- Generate a package manifest for traceability.

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

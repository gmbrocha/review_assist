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

Status: initial implementation in progress.

- Define a broad source catalog covering water, land, species, cultural, regulated facilities, community, infrastructure, parcel, imagery, and flood context.
- Create project source registries that can enable or disable candidate sources per project.
- Support local source-layer registration before implementing fragile live downloads.
- Treat restricted, manual, and reviewer-supplied sources as explicit placeholders.
- Track source category, publisher, access method, public/restricted status, limitations, and intended spatial relationships.

Flood hazard is cataloged as a secondary optional source. It is not a core first-pass driver for every project.

## Phase 2B: Local Layer Clipping and Spatial Relationship Checks

Status: initial implementation in progress.

- Load enabled project-local source layers.
- Clip or filter layers to the project geometry and configured review buffer.
- Run deterministic spatial checks for `intersects`, `crosses`, and `within_buffer`.
- Preserve source, method, CRS, buffer, and measurement metadata.
- Produce `spatial_relationships.json` before findings, narrative, maps, or report drafting.

Phase 2B still does not create findings, review queue records, maps, reports, rankings, recommendations, or final conclusions.

## Phase 3: Finding Model and Review Statuses

- Define structured finding fields.
- Add review statuses.
- Support reviewer notes and edits.
- Track uncertainty and unable-to-verify cases.
- Map spatial relationship types to reviewable contextual implications.
- Distinguish source-backed findings from imagery-observed review items.

## Phase 4: Map/Figure and Table Generation

- Generate overall project maps.
- Generate resource-specific maps.
- Generate panel maps where useful.
- Generate comparison tables by resource and alternative.
- Preserve legends, source notes, draft labels, and map provenance.

## Phase 5: Report Draft Generation and Assembly

- Generate editable draft report packages.
- Include maps, tables, findings, source notes, and review status.
- Keep generated reports clearly labeled as pre-review drafts.
- Compile appendices/reference materials where available.
- Generate a package manifest for traceability.

## Phase 6: Imagery Observation Workflow

- Support imagery-based review observations.
- Distinguish observed features from authoritative source-backed facts.
- Capture reviewer confirmation or rejection.
- Support cropped imagery and overlay review.
- Preserve imagery source/date/attribution where available.

## Phase 7: Optional AI-Assisted Narrative Synthesis

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

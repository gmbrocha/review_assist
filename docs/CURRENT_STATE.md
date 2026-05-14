# Current State

## Phase

Phase 0 scaffold/planning is complete. Phase 1 KMZ/KML ingestion and geometry inspection is implemented for the current prototype baseline. The first Phase 2A/2B baseline is also implemented: source catalog, project source registries, local source registration, and local spatial relationship checks. Phase 3 project context/source status artifacts, the first Phase 4 JSON-backed review queue baseline, Phase 5 populate-for-review orchestration, Phase 6A deterministic finding generation, Phase 6B source provenance/comparison tables, Phase 6C vector-only map/figure generation, and Phase 6D deterministic draft report section generation are implemented.

The repository currently contains documentation, project workspaces, sample KMZ/KML preview utilities, project manifests, project-local input copies, Python service/CLI implementation for Phase 1 inspection, Phase 2 source catalog/spatial check services, workflow-native project context/source status services, source inventory/provenance artifacts, deterministic draft finding generation, comparison table artifacts, vector-only map artifacts, deterministic draft report section artifacts, JSON review queue services, and populate-for-review orchestration. No production workflow has been implemented.

The current direction is clearer than the initial scaffold: the system should eventually create a comprehensive pre-review draft package so the reviewer does not start from a blank page. The canonical workflow is now workspace driven: open/create workspace, add inputs, generate project context, resolve source status, populate for review, review every generated item, and export accepted content.

## Known Input Expectation

Initial inputs may include KMZ or KML files containing:

- A project footprint or study area.
- Multiple proposed alternatives.
- Alternative geometries that may represent trails, corridors, sites, alignments, access routes, infrastructure options, or other project options.

The exact input schema, naming conventions, and validation requirements are not yet defined.

Current real example inputs in the repository include:

- `trail_route_alternatives.kmz`, representing the trail alternatives context.
- `conexon_projects_color_coded.kmz`, representing broadband installation spot context.
- `env_constraints_report_20260511_EXAMPLE_ONLY.docx`, an example environmental constraints report used for deliverable structure research only.

Project-local copies are now expected under:

- `projects/trails/inputs/trail_route_alternatives.kmz`
- `projects/conexon_projects/inputs/conexon_projects_color_coded.kmz`

## Known Future Output Goal

The future goal is an editable pre-review report package that may include:

- Structured findings for each alternative.
- Maps and tables.
- Draft narrative.
- Contextual implications.
- Appendices or reference material.
- Source provenance for each finding.
- Method notes.
- Uncertainty and missing-data flags.
- Reviewer status for each finding.
- Reviewer edits and acceptance or rejection history.

All outputs are pre-review drafts until reviewed by a human professional.

The review queue is the required control point before export. Findings, paragraphs, maps, tables, caveats, source notes, and missing-data placeholders should all become review queue items.

## Not Implemented

- Production GIS pipelines or full environmental analysis.
- External API integrations.
- Basemap or imagery acquisition workflows.
- Export assembly pipelines.
- Public source downloads or live source querying.
- Desktop GUI.
- LLM-assisted narrative synthesis.
- Basemap-backed, raster, panel-sheet, or final cartographic map rendering.
- ML or computer vision detection.
- Scoring, ranking, or preferred alternative selection.
- Final report export generation.
- Authentication or production deployment workflows.

## Current Project Workspaces

- `projects/trails`: trail alternative review context.
- `projects/conexon_projects`: broadband installation spot review context.

The root-level KMZ files are retained as reference originals. Phase 1 project manifests point to copied project-local inputs.

## Phase 1 Implementation Defaults

- Implementation surface: reusable services plus CLI.
- Geospatial stack: GeoPandas with Shapely, PyProj, Pyogrio, and Pandas.
- Project manifest format: JSON.
- Intermediate geometry format: GeoJSON.
- Geometry summary format: JSON.
- Generated project intermediates are ignored by Git.

## Phase 2A/2B Implementation Defaults

- Source catalog format: JSON at `config/source_catalog.json`.
- Project source registry format: JSON at `projects/<project_id>/config/sources.json`.
- Source population strategy: local source-layer registration first; live downloads are deferred unless a simple public source can be implemented safely.
- First spatial-check priority: wetlands/waterbodies, hydrography/crossings, land cover/disturbance, and soils.
- Flood hazard is retained as a secondary optional source category, not a first-pass driver for every project.
- Generated spatial relationship outputs are JSON and GeoJSON under ignored project `intermediate/` directories.
- Source layers under `projects/<project_id>/layers/` are ignored by Git because they may be large, licensed, or project-specific.

Current CLI commands:

- `review-assist inspect-project <project_dir>`
- `review-assist list-sources [project_dir]`
- `review-assist import-source <project_dir> <source_id> <path>`
- `review-assist analyze-project <project_dir>`
- `review-assist generate-context <project_dir>`
- `review-assist resolve-sources <project_dir>`
- `review-assist generate-source-inventory <project_dir>`
- `review-assist generate-findings <project_dir>`
- `review-assist generate-tables <project_dir>`
- `review-assist generate-maps <project_dir>`
- `review-assist generate-report-sections <project_dir>`
- `review-assist generate-review-queue <project_dir>`
- `review-assist list-review-queue <project_dir>`
- `review-assist update-review-item <project_dir> <item_id> --status <status>`
- `review-assist populate-for-review <project_dir>`

## Workflow Artifact Defaults

- Report profile config: JSON at `config/report_profiles.json`.
- Finding template config: JSON at `config/finding_templates.json`.
- Report section template config: JSON at `config/report_section_templates.json`.
- Project context output: JSON at `projects/<project_id>/context/project_context.json`.
- Source status output: JSON at `projects/<project_id>/source_status/source_status_set.json`.
- Source inventory output: JSON at `projects/<project_id>/source_inventory/source_inventory.json`.
- Draft findings output: JSON at `projects/<project_id>/findings/draft_findings.json`.
- Comparison tables output: JSON at `projects/<project_id>/tables/comparison_tables.json`.
- Map manifest output: JSON at `projects/<project_id>/maps/map_manifest.json`.
- Draft map figures output: PNG files under `projects/<project_id>/maps/figures/`.
- Draft report sections output: JSON at `projects/<project_id>/drafts/report_sections.json`.
- Review queue output: JSON at `projects/<project_id>/review_queue/review_queue.json`.
- Populate run manifest: JSON at `projects/<project_id>/populate_for_review/populate_for_review_run.json`.
- Generated context, source status, source inventory, draft findings, comparison tables, draft maps, draft report sections, review queue, and populate artifacts are ignored by Git.
- The current implementation creates deterministic draft findings from source status records, spatial relationships, and no-mapped-relationship checks.
- The current implementation creates descriptive comparison tables from source status, spatial relationship, and draft finding artifacts.
- The current implementation creates vector-only draft map figures from normalized project geometry and analyzed local source clipped layers.
- The current implementation creates deterministic draft report sections from project context, source status, source inventory, draft findings, comparison tables, map manifests, and validation issues.
- The current implementation creates review queue items from source inventory records, deterministic draft findings, comparison tables, map figures, report sections, source status records, spatial relationships, no-mapped-relationship checks, map-generation/report-section warnings, and validation issues.
- `populate-for-review` runs context generation, source status resolution, source inventory generation, tolerant local spatial analysis, deterministic draft finding generation, comparison table generation, map generation, report section generation, and review queue generation into one inspectable run manifest.

Current audit status:

- The codebase has passing tests for ingestion, source registry validation, local source registration, synthetic spatial checks, project context/source status artifacts, source inventory/provenance artifacts, draft finding generation, comparison table artifacts, vector-only map artifacts, draft report section artifacts, render-error handling, review queue generation/update behavior, malformed optional artifact handling, and populate-for-review orchestration.
- The implementation validates source registry booleans, duplicate source IDs, project/source registry ID mismatches, non-object manifest entries, optional source metadata, source inventory record counts, comparison table counts/statuses, and negative buffer values.
- See `docs/CODE_AUDIT.md` for latest audit notes.

## Archive Directories

- `archive/`: general archive for retained but inactive project-level files.
- `docs/archive/`: archive for superseded or historical documentation.

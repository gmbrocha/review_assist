# Current State

## Phase

Phase 0 scaffold/planning is complete. Phase 1 KMZ/KML ingestion and geometry inspection is implemented for the current prototype baseline. The first Phase 2A/2B baseline is also implemented: source catalog, project source registries, local source registration, and local spatial relationship checks. Phase 3 project context/source status artifacts and the first Phase 4 JSON-backed review queue baseline are implemented.

The repository currently contains documentation, project workspaces, sample KMZ/KML preview utilities, project manifests, project-local input copies, Python service/CLI implementation for Phase 1 inspection, Phase 2 source catalog/spatial check services, workflow-native project context/source status services, and JSON review queue services. No production workflow has been implemented.

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
- Report assembly pipelines.
- Finding generation.
- Public source downloads or live source querying.
- Desktop GUI.
- LLM-assisted narrative synthesis.
- ML or computer vision detection.
- Scoring, ranking, or preferred alternative selection.
- Report generation.
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
- `review-assist generate-review-queue <project_dir>`
- `review-assist list-review-queue <project_dir>`
- `review-assist update-review-item <project_dir> <item_id> --status <status>`

## Workflow Artifact Defaults

- Report profile config: JSON at `config/report_profiles.json`.
- Project context output: JSON at `projects/<project_id>/context/project_context.json`.
- Source status output: JSON at `projects/<project_id>/source_status/source_status_set.json`.
- Review queue output: JSON at `projects/<project_id>/review_queue/review_queue.json`.
- Generated context, source status, and review queue artifacts are ignored by Git.
- The current implementation creates review queue items from source status records, spatial relationships, no-mapped-relationship checks, and validation issues.

Current audit status:

- The codebase has passing tests for ingestion, source registry validation, local source registration, synthetic spatial checks, project context/source status artifacts, and review queue generation/update behavior.
- The implementation validates source registry booleans, duplicate source IDs, project/source registry ID mismatches, non-object manifest entries, and negative buffer values.
- See `docs/CODE_AUDIT.md` for latest audit notes.

## Archive Directories

- `archive/`: general archive for retained but inactive project-level files.
- `docs/archive/`: archive for superseded or historical documentation.

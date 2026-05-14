# Current State

## Phase

Phase 0 scaffold/planning is complete. Phase 1 KMZ/KML ingestion and geometry inspection is implemented for the current prototype baseline. The project is now entering Phase 2A/2B source catalog, local source registration, and local spatial relationship checks.

The repository currently contains documentation, project workspaces, sample KMZ/KML preview utilities, project manifests, project-local input copies, an initial Python service/CLI implementation for Phase 1 inspection, and early Phase 2 source catalog/spatial check services. No production workflow has been implemented.

The current direction is clearer than the initial scaffold: the system should eventually create a comprehensive pre-review draft package so the reviewer does not start from a blank page.

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

## Not Implemented

- Full GIS analysis.
- External API integrations.
- Basemap or imagery acquisition workflows.
- Report assembly pipelines.
- Finding generation.
- Review queue persistence.
- Public source downloads.
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

## Archive Directories

- `archive/`: general archive for retained but inactive project-level files.
- `docs/archive/`: archive for superseded or historical documentation.

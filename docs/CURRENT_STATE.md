# Current State

## Phase

This project is in scaffold and planning phase only.

The repository currently contains documentation, project workspaces, sample KMZ/KML preview utilities, and directory structure for a future alternatives review assistant. No production workflow has been implemented.

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
- LLM-assisted narrative synthesis.
- ML or computer vision detection.
- Scoring, ranking, or preferred alternative selection.
- Report generation.
- Authentication or production deployment workflows.

## Current Project Workspaces

- `projects/trails`: trail alternative review context.
- `projects/conexon_projects`: broadband installation spot review context.

The root-level KMZ files have not yet been moved into project-specific input folders.

## Archive Directories

- `archive/`: general archive for retained but inactive project-level files.
- `docs/archive/`: archive for superseded or historical documentation.

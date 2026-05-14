# Decision Log

This document records product and architecture decisions as the project evolves.

## Decisions

### 2026-05-14: The tool will not select or recommend a preferred alternative

The tool supports human review and should not choose a preferred alternative.

### 2026-05-14: The tool will avoid hard scoring

Alternatives should be described through impact profiles and source-backed findings rather than hard scores.

### 2026-05-14: Findings should distinguish source-backed GIS facts from imagery-observed review items

Deterministic source checks and imagery observations have different certainty levels and should be represented differently.

### 2026-05-14: Generated reports are pre-review drafts only

Generated report packages are drafts for human review and should not be labeled final.

### 2026-05-14: The product direction is no blank page

The system should eventually attempt to generate a comprehensive first-pass package, including findings, draft narrative, maps, tables, implications, and appendices/reference material where useful.

### 2026-05-14: Public authoritative GIS is a reliable baseline but still screening-level

Government, educational, and authoritative public infrastructure GIS sources can support baseline desktop screening, but findings must preserve provenance, source dates, uncertainty, and field-verification caveats.

### 2026-05-14: Buffer assumptions must remain configurable

Early trail context suggests review corridors in the 50 to 100 foot range, but v1 architecture should treat corridor and buffer widths as configurable project assumptions.

### 2026-05-14: MDAH restricted cultural resource integration is deferred

The system may document future integration points and reviewer-supplied workflows, but it should not implement restricted MDAH access or authentication until explicitly approved.

### 2026-05-14: LLM synthesis is allowed only as reviewable draft synthesis

Future GPT/LLM calls may assist with narrative, summaries, implications, uncertainty phrasing, and sanity checks, but deterministic GIS/source analysis must remain separate and source-backed.

### 2026-05-14: The desktop app review queue is the spine

The first GUI version should treat the review queue as the core domain model. Generated findings, section drafts, maps, tables, provenance notes, assumptions, and caveats must become reviewable items before export.

### 2026-05-14: The desktop GUI must stay thin over services

The PyInstaller desktop app should use a modular service architecture underneath the GUI so pipeline, GIS, findings, review, and export logic does not become trapped in callbacks.

### 2026-05-14: Phase 1 starts with services plus CLI

Phase 1 implementation should build reusable ingestion/inspection services and a command-line entrypoint before GUI work, so the later desktop shell can sit on top of stable workflow logic.

### 2026-05-14: Phase 1 project inputs are copied into project workspaces

Root KMZ files are retained as reference originals, while project manifests reference copies under `projects/<project_id>/inputs/`.

### 2026-05-14: Phase 1 standardizes on GeoPandas

GeoPandas, Shapely, PyProj, Pyogrio, and Pandas are the standard geospatial dependency path for Phase 1. The earlier dependency-free KMZ preview utility remains a reference/compatibility tool, not the primary ingestion path.

### 2026-05-14: Phase 1 uses JSON manifests and JSON/GeoJSON intermediates

Project manifests are JSON. Geometry inspection summaries are JSON. Normalized geometry outputs are GeoJSON under ignored project `intermediate/` directories.

### 2026-05-14: Phase 2 starts with a broad source catalog and local source registration

The source stack should cover the major review categories now, while implementation begins with local-file registration and deterministic spatial checks. Live public downloads are deferred until specific sources are validated.

### 2026-05-14: Water and land context drive the first Phase 2 spatial checks

The first useful automated checks prioritize wetlands/waterbodies, hydrography/crossings, land cover/disturbance, and soils. Flood hazard remains cataloged as a secondary optional category rather than a first-pass driver for every project.

### 2026-05-14: Phase 2 outputs spatial relationships, not findings

Phase 2B produces reviewable spatial relationship records with source and method metadata. It does not generate findings, recommendations, report text, review queue decisions, or final conclusions.

### 2026-05-14: The canonical workflow is workspace driven

The product workflow is now defined as workspace creation/opening, user-added inputs, project context generation, needed source resolution, populate for review, review queue, and accepted-content export. `docs/WORKFLOW_MODEL.md` is the canonical truth model for this workflow.

### 2026-05-14: Project context is a persistent artifact

Detected project extent, alternatives, assumptions, likely report profile, provided source categories, missing categories, user instructions, and reviewer notes should be maintained as editable workspace state rather than transient pipeline output.

### 2026-05-14: Source status is first-class workflow state

Needed data categories should resolve to explicit statuses such as provided locally, downloadable, downloaded, gated, stubbed, missing, optional, or needs review. Missing/gated data should create placeholders, uncertainty flags, and review requirements rather than failing the workflow by default.

### 2026-05-14: Populate for Review is the main generation action

The future desktop workflow should expose a `Populate for Review` action that loads/acquires sources, clips data, runs deterministic checks, prepares imagery/basemaps, and generates findings, maps, tables, narrative drafts, caveats, and provenance notes as review queue items.

### 2026-05-14: Exports compile reviewed content only

Export packages should compile accepted or explicitly included reviewed items. Rejected items remain in the review record but are not exported. Items needing verification or unable to verify may export only with explicit reviewer inclusion and caveat language.

### 2026-05-14: Workflow artifacts use JSON for the current baseline

Project context and source status set artifacts are stored as project-local JSON files. This keeps the workflow state inspectable while the review queue and desktop GUI requirements are still being clarified.

### 2026-05-14: Existing CLI commands remain backward-compatible

The workflow model is added through new commands rather than renaming existing inspection and analysis commands. Current commands remain stable while `generate-context` and `resolve-sources` introduce workflow-native artifacts.

### 2026-05-14: Implementation phases require tests as they go

Each behavior-changing implementation phase should add or update tests for the services, CLI commands, validation rules, data artifacts, and workflow behavior it introduces. The expected local test command is `.\.venv\Scripts\python.exe -m pytest`. If tests cannot be run, the task summary should explain why and identify residual risk.

### 2026-05-14: Review queue persistence uses JSON for the current baseline

The first review queue implementation stores project-local review state at `projects/<project_id>/review_queue/review_queue.json`. This keeps generated review items inspectable while the GUI and export workflow are still deferred. The baseline converts source inventory records, deterministic draft findings when present, comparison tables, source status records, spatial relationships, no-mapped checks, and validation issues into reviewable items, but it does not generate final findings or reports.

### 2026-05-14: Populate for Review starts as orchestration, not generation

The first `populate-for-review` implementation coordinates current services and writes a project-local run manifest. It originally ran through review queue generation without maps or report sections; Phase 6C added vector-only map generation and Phase 6D adds deterministic report section generation to that orchestration. It deliberately does not download public sources, render basemap/imagery-backed maps, call LLMs, compile exports, or create recommendations.

### 2026-05-14: Deterministic draft findings come before maps, reports, GUI, and LLM work

Phase 6A converts source status records and spatial relationship records into cautious, template-driven draft finding records at `projects/<project_id>/findings/draft_findings.json`. Findings use deterministic IDs so review queue regeneration can preserve reviewer status and notes. These findings are review queue inputs, not final conclusions or report text.

### 2026-05-14: Source provenance and comparison tables are backend artifacts before maps/exports

Phase 6B adds source inventory/provenance records at `projects/<project_id>/source_inventory/source_inventory.json` and descriptive comparison tables at `projects/<project_id>/tables/comparison_tables.json`. These artifacts feed the review queue and future map/export workflows, but they do not download sources, render final report tables, rank alternatives, or compile report packages.

### 2026-05-14: Phase 6C map generation starts vector-only

The first map-generation baseline writes `projects/<project_id>/maps/map_manifest.json` and PNG draft figures under `projects/<project_id>/maps/figures/`. It uses GeoPandas and Matplotlib only, creates project-overview and local source-context figures, and feeds `map_figure` items into the review queue. Basemaps, imagery, raster handling, panel sheets, and final map exports remain deferred.

### 2026-05-14: Phase 6D report section drafting starts deterministic

The first report section baseline writes `projects/<project_id>/drafts/report_sections.json` using templates from `config/report_section_templates.json`. It creates no-blank-page draft sections from structured workflow artifacts and feeds `report_section` items into the review queue. LLM synthesis, DOCX/PDF export, final report compilation, ranking, recommendations, and unreviewed report output remain deferred.

## Future Decision Template

### YYYY-MM-DD: Decision title

Context:

Decision:

Consequences:

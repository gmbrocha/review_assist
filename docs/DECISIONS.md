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

GPT/LLM calls may assist with narrative, summaries, implications, uncertainty phrasing, and sanity checks, but deterministic GIS/source analysis must remain separate and source-backed. The first implemented use is report-section draft copy from structured evidence only.

### 2026-05-14: The product review queue is the spine

The UI should treat the review queue as the core domain model. Generated findings, section drafts, maps, tables, provenance notes, assumptions, and caveats must become reviewable items before export.

### 2026-05-14: The UI must stay thin over services

The future web app should use a modular service architecture underneath the UI so pipeline, GIS, findings, review, and export logic does not become trapped in route handlers or view callbacks.

### 2026-05-14: Phase 1 starts with services plus CLI

Phase 1 implementation should build reusable ingestion/inspection services and a command-line entrypoint before UI work, so the later web app can sit on top of stable workflow logic.

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

The product workflow is now defined as workspace creation/opening, user-added inputs, project context generation, needed source resolution, populate for review, review queue, and accepted-content export. `CANONICAL_PLAN.md` is the canonical planning source, and `docs/WORKFLOW_MODEL.md` should stay aligned to it.

### 2026-05-14: Project context is a persistent artifact

Detected project extent, alternatives, assumptions, likely report profile, provided source categories, missing categories, user instructions, and reviewer notes should be maintained as editable workspace state rather than transient pipeline output.

### 2026-05-14: Source status is first-class workflow state

Needed data categories should resolve to explicit statuses such as provided locally, downloadable, downloaded, failed, gated, stubbed, missing, optional, or needs review. Missing, failed, gated, and stubbed data should create placeholders, uncertainty flags, and review requirements rather than failing the workflow by default.

### 2026-05-14: Populate for Review is the main generation action

The future web app workflow should expose a `Create Review Queue` action that loads/acquires sources, clips data, runs deterministic checks, prepares imagery/basemaps, and generates findings, maps, tables, narrative drafts, caveats, and provenance notes as review queue items.

### 2026-05-14: Exports compile reviewed content only

Export packages should compile accepted or explicitly included reviewed items. Rejected items remain in the review record but are not exported. Items needing verification or unable to verify may export only with explicit reviewer inclusion and caveat language.

### 2026-05-14: Workflow artifacts use JSON for the current baseline

Project context and source status set artifacts are stored as project-local JSON files. This keeps the workflow state inspectable while the review queue and web app requirements are still being clarified.

### 2026-05-14: Existing CLI commands remain backward-compatible

The workflow model is added through new commands rather than renaming existing inspection and analysis commands. Current commands remain stable while `generate-context` and `resolve-sources` introduce workflow-native artifacts.

### 2026-05-14: Implementation phases require tests as they go

Each behavior-changing implementation phase should add or update tests for the services, CLI commands, validation rules, data artifacts, and workflow behavior it introduces. The expected local test command is `.\.venv\Scripts\python.exe -m pytest`. If tests cannot be run, the task summary should explain why and identify residual risk.

### 2026-05-14: Review queue persistence uses JSON for the current baseline

The first review queue implementation stores project-local review state at `projects/<project_id>/review_queue/review_queue.json`. This keeps generated review items inspectable while the web app UI is still deferred. The baseline now defaults to a lean queue from deterministic draft findings, comparison tables, maps, report sections, report-relevant missing-data placeholders, no-mapped checks, and validation issues. Source inventory notes are opt-in for audit workflows. Queue items now carry export grouping metadata for Markdown assembly, but the queue itself does not generate final findings or reports.

### 2026-05-14: Populate for Review starts as orchestration, not generation

The first `populate-for-review` implementation coordinates current services and writes a project-local run manifest. It originally ran through review queue generation without maps or report sections; Phase 6C added vector-only map generation, Phase 6D added report section generation, the constraint-core slice added project geometry normalization plus first-class constraint analysis, the source-acquisition slice added opt-in NWI, USGS NHD hydrography, USFWS Critical Habitat, EPA/ECHO regulated facilities, and optional FEMA NFHL downloads, and the GPT/evidence slice added evidence packages plus optional GPT section drafting. It deliberately does not download public sources unless explicitly requested, render basemap/imagery-backed maps, create exports itself, or create recommendations.

### 2026-05-14: Deterministic draft findings come before maps, reports, UI, and LLM work

Phase 6A converts source status records, first-class constraint result records when present, and legacy spatial relationship records when needed into cautious, template-driven draft finding records at `projects/<project_id>/findings/draft_findings.json`. Findings use deterministic IDs so review queue regeneration can preserve reviewer status and notes. These findings are review queue inputs, not final conclusions or report text.

### 2026-05-14: Source provenance and comparison tables are backend artifacts before maps/exports

Phase 6B adds source inventory/provenance records at `projects/<project_id>/source_inventory/source_inventory.json` and descriptive comparison tables at `projects/<project_id>/tables/comparison_tables.json`. These artifacts feed the review queue and map/export workflows. Source inventory now includes source acquisition provenance when present, but it does not render final report tables, rank alternatives, or compile report packages.

### 2026-05-14: Phase 6C map generation starts vector-only

The first map-generation baseline writes `projects/<project_id>/maps/map_manifest.json` and PNG draft figures under `projects/<project_id>/maps/figures/`. It uses GeoPandas and Matplotlib only, creates project-overview and local source-context figures, and feeds `map_figure` items into the review queue. Basemaps, imagery, raster handling, panel sheets, and final map exports remain deferred.

### 2026-05-14: Phase 6D report section drafting starts deterministic

The first report section baseline writes `projects/<project_id>/drafts/report_sections.json` using templates from `config/report_section_templates.json`. It creates no-blank-page draft sections from structured workflow artifacts and feeds `report_section` items into the review queue. Final PDF/report compilation, ranking, recommendations, and unreviewed external-ready report output remain deferred.

### 2026-05-15: Markdown export proves accepted-content assembly before DOCX

The first export compiler writes `projects/<project_id>/exports/environmental_constraints_report.md` and `projects/<project_id>/exports/export_manifest.json` through `review-assist export-report`. It compiles accepted or edited review queue items by default, includes `unable_to_verify` items only when explicitly export eligible, and provides `--include-draft` only for internal preview exports. This decision established the Markdown proof before adding DOCX/PDF layout concerns.

### 2026-05-15: MVP demo deliverable moves export from Markdown to DOCX package assembly

The MVP export slice adds DOCX generation through `review-assist export-report --format docx|both` and an internal preview package command through `review-assist build-demo-deliverable`. Default export remains review-gated. The demo command uses `--include-draft` preview semantics, visibly labels output as not reviewed, and does not auto-accept or mutate review item statuses. PDF export, final template fidelity, and web app review screens remain deferred.

### 2026-05-15: MVP deliverables must prove real-data lineage

The real-data MVP path adds `review-assist build-mvp-deliverable`, which runs source preparation before preview export and records `data_lineage` in export/deliverable manifests. MVP packages may contain clearly labeled stubs for missing, manual, gated, failed, or reviewer-needed categories, but they must not present mock/test fixture source records as evidence. The command fails by default when no real downloaded, provided, or registered source layer is available and fails when included content contains test fixture provenance.

### 2026-05-15: MVP packages should render evidence inside the report body

The MVP report package now treats tables and figures as report evidence, not only attachments. Export builds table/figure lookups from included review items and upstream artifacts, renders referenced tables and figures inline in their related report sections, tracks which artifacts were rendered to avoid duplicate full renderings, and records `mvp_quality` counts in export and deliverable manifests. Missing or unreadable table/map artifacts must create visible placeholders or validation warnings instead of silent omissions. This improves the client-showable preview package while leaving final template-grade DOCX layout, basemaps, PDF export, and web app review screens deferred.

### 2026-05-15: Failed source downloads must remain visible downstream

Supported public downloader failures are nonfatal, but they must not disappear as generic `downloadable` source gaps. Source status, draft findings, report sections, and review queue missing-data/caveat items should carry `failed` and `source_download_failed` when the acquisition manifest records a failed latest attempt.

### 2026-05-15: GPT drafting must be evidence-grounded and review-gated

The first GPT slice adds `projects/<project_id>/evidence/evidence_package.json` and optional OpenAI report-section drafting controlled by `GPT_DRAFTING`, `OPENAI_INTERPRETER_MODEL`, and `OPENAI_API_KEY`. GPT receives structured section requests only and must return structured output with cited IDs. Unknown citations or prohibited recommendation/ranking/selection/final-determination/field-verification language are rejected or flagged. GPT output remains a `report_section` review item and is never auto-accepted.

### 2026-05-14: The product is a constraint overlap engine plus review queue

The core workflow first parses project geometry, derives analysis bounds, crops/loads relevant sources, and identifies objective constraints by project feature and resource category. The review queue is downstream of that engine: findings, maps, tables, caveats, source notes, and draft report sections become small editable review items that a user can accept, edit, reject, or queue for export. Review queue item count is not a readiness metric.

### 2026-05-14: Current projects are examples, not product boundaries

`projects/trails` and `projects/conexon_projects` represent two input shapes: line/corridor alternatives and point-heavy broadband service locations. The system should remain a blank project machine that can accept a new KMZ/KML, infer or ask for the intended geometry role, apply geometry-appropriate buffer/bounds logic, and run the same objective constraint workflow for trails, service points, service areas, routes, corridors, sites, polygons, or mixed project contexts.

### 2026-05-14: The system presents constraints, not choices

The system may compare objective constraints across alternatives, routes, sites, service areas, or project features. It must not choose, reject, recommend, or rank them. The human/client/planning process uses the constraint information to make decisions outside the tool.

## Future Decision Template

### YYYY-MM-DD: Decision title

Context:

Decision:

Consequences:

# Alternatives Review Assistant

This project is an internal prototype for assisting with environmental and contextual review of proposed project alternatives.

The tool is intended to generate source-backed pre-review report packages for human professionals. It should operate as a local, workspace-oriented workflow: users add project inputs, the system resolves needed source data and generates a draft review queue, humans accept/edit/reject items, and accepted content is compiled into export packages.

This is not a recommendation engine and not an automated decision-maker. It does not choose a preferred alternative, rank alternatives, or replace professional judgment.

Human review is mandatory before any output is used outside the draft review process. Generated reports and findings are pre-review drafts until a human reviewer validates, edits, accepts, or rejects them.

The review queue is the core workflow object. Every generated artifact should become a reviewable item before export.

## Current Status

The project has completed Phase 0 scaffold/planning, Phase 1 KMZ/KML ingestion, the first Phase 2A/2B source-context baseline, the Phase 2C catalog-driven source acquisition baseline with explicit NWI, USGS NHD hydrography, USFWS Critical Habitat, EPA/ECHO regulated facilities, and optional FEMA NFHL flood hazard downloaders, local Mississippi source warehouse materialization for NWI wetlands, USFWS Critical Habitat, SSURGO soils, MDOT/rail transportation, utility infrastructure, county/boundary context, public cultural context, community facilities, and conservation/recreation lands, Phase 3 project context/source status artifacts, an initial Phase 4 JSON-backed review queue baseline, Phase 5 populate-for-review orchestration, Phase 6A deterministic finding generation, Phase 6B source provenance/comparison tables, Phase 6C vector-only map/figure generation with report-ready metadata and export-local PNG assets, Phase 6D report sections with deterministic and optional GPT drafting, evidence package generation, the first Markdown/DOCX export compiler, internal demo/MVP deliverable package commands, real-data guarded MVP deliverable quality metadata, and the first constraint-engine baseline. The current CLI can inspect project KMZ/KML inputs, normalize project geometry into point/site, line/corridor, polygon/area, or mixed feature artifacts, list the source catalog, register local source layers, materialize ignored Mississippi warehouse layers into project-ready GeoJSON, resolve source gaps, explicitly download NWI wetlands, USGS NHD hydrography, USFWS Critical Habitat, EPA/ECHO regulated facilities, and FEMA NFHL flood hazard, run legacy spatial relationship checks, run constraint overlap/proximity checks, generate workflow artifacts, generate deterministic draft findings, generate source inventory/table/map/section/evidence artifacts, optionally use GPT for source-grounded report section drafting, populate a lean review queue, create/update review queue items, export accepted/edited review items to Markdown/DOCX plus an export manifest, create an internal preview demo deliverable package, and create a real-data guarded MVP deliverable package.

The implementation surface is reusable Python services plus a CLI. No web app UI, broad external API integration, source downloads beyond opt-in NWI, USGS NHD hydrography, USFWS Critical Habitat, EPA/ECHO regulated facilities, and optional FEMA NFHL flood hazard, scoring, PDF export, basemap/imagery acquisition, or production workflow has been implemented. GPT is limited to report-section copy from structured evidence and never replaces geometry, local source materialization, source acquisition, constraint analysis, measurements, review decisions, or export acceptance.

## Planning Docs

Key planning documents live at the repo root and under `docs/`:

- `CANONICAL_PLAN.md`: canonical root drift-control plan; read before large implementation work. It defines the destination as filling the example environmental constraints report template with source-backed constraints, visuals, reviewable copy, tables, caveats, reviewed export content, and the future web app direction.
- `SPRINT_1_FOUNDATION_AND_CONTRACT.md`, `SPRINT_2_CONSTRAINTS_TABLES_AND_FIGURES.md`, and `SPRINT_3_REVIEW_EXPORT_AND_DOCX.md`: non-UI implementation sprints for the redirected backend/report pipeline.
- `SPRINT_4_WEB_APP_AND_WIRING.md`: future web app and wiring sprint after the non-UI pipeline is complete.
- `OVERALL_CONTEXT.md`: product philosophy and anti-drift context.
- `WORKFLOW_MODEL.md`: canonical workspace, source-status, review-queue, and export workflow.
- `ARCHITECTURE.md`: conceptual service/module boundaries.
- `DATA_SOURCES.md`: practical source stack, candidate sources, and source-registry planning.
- `CODE_AUDIT.md`: latest implementation audit notes, fixes, and known limits.
- `REPORT_TAXONOMY.md`: expected report structure.
- `FINDING_TYPES.md`: implemented baseline and future finding/implication types.
- `UNCERTAINTY_AND_PROVENANCE.md`: source traceability and uncertainty policy.
- `MAP_GENERATION.md`: current vector-only map baseline and future map/figure direction.
- `REPORT_ASSEMBLY.md`: findings-to-report workflow and current Markdown/DOCX export baseline.
- `IMAGERY_REVIEW.md`: imagery observation philosophy.
- `LLM_ASSISTED_SYNTHESIS.md`: GPT/LLM section-drafting insertion point and boundaries.
- `docs/archive/FIRST_VERSION_PLAN.md`: superseded desktop GUI first-version plan retained for history; web app work is deferred behind the backend deliverable pipeline and captured as Sprint 4.
- `docs/archive/PLAN_REDIRECT.md`, `docs/archive/DELIVERABLE_OUTLINE.md`, and `docs/archive/REPORT_GEN_SYSTEM_PROMPT.md`: superseded planning references retained for history; active planning has been consolidated into `CANONICAL_PLAN.md`.

## Directory Notes

- `projects/`: active project workspaces.
- `archive/`: general project archive for retained but inactive files.
- `docs/archive/`: archive for superseded or historical documentation.
- `outputs/`: generated outputs; ignored except for `.gitkeep`.
- `sources/`: local bulk data warehouse for Mississippi-wide source downloads such as SSURGO, NLCD, MARIS, or agency exports; ignored by Git and never sent directly to GPT.

## Local Setup

Install the package and development dependencies into the local virtual environment:

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
```

Inspect a project workspace:

```powershell
.\.venv\Scripts\review-assist.exe inspect-project projects/trails
.\.venv\Scripts\review-assist.exe inspect-project projects/conexon_projects
```

List the source catalog, register a local source layer, and run local spatial checks:

```powershell
.\.venv\Scripts\review-assist.exe list-sources projects/trails
.\.venv\Scripts\review-assist.exe import-source projects/trails usfws_nwi_wetlands C:\path\to\nwi_export.geojson
.\.venv\Scripts\review-assist.exe import-source projects/trails usda_nrcs_ssurgo_soils .\sources\wss_gsmsoil_MS_10_13_2016\spatial\gsmsoilmu_a_ms.shp --copy
.\.venv\Scripts\review-assist.exe analyze-project projects/trails
```

Use `--copy` for file-based local source layers that should be copied into the ignored project workspace under `projects/<id>/layers/<source_id>/` before registration. For shapefiles, the CLI copies required sidecars such as `.shp`, `.shx`, `.dbf`, and `.prj`; the original source package under `sources/` is not mutated. Use `--replace` with `--copy` only when intentionally refreshing an existing project-local copy.

Materialize project-ready GeoJSON from the ignored local Mississippi source warehouse:

```powershell
.\.venv\Scripts\review-assist.exe materialize-local-source projects/trails usfws_nwi_wetlands
.\.venv\Scripts\review-assist.exe materialize-local-source projects/trails usfws_critical_habitat
.\.venv\Scripts\review-assist.exe materialize-local-source projects/trails usda_nrcs_ssurgo_soils
.\.venv\Scripts\review-assist.exe materialize-local-source projects/trails mdot_transportation_context
.\.venv\Scripts\review-assist.exe materialize-local-source projects/trails maris_boundary_context
.\.venv\Scripts\review-assist.exe materialize-local-source projects/trails maris_public_cultural_context
.\.venv\Scripts\review-assist.exe materialize-local-source projects/trails maris_community_facilities
.\.venv\Scripts\review-assist.exe materialize-local-source projects/trails maris_conservation_recreation_lands
.\.venv\Scripts\review-assist.exe materialize-local-source projects/trails local_utility_infrastructure
.\.venv\Scripts\review-assist.exe materialize-local-sources projects/trails
```

Materialization reads configured statewide/local datasets from `sources/`, clips them to `project_analysis_bounds.geojson`, writes small project-ready GeoJSON files under `projects/<id>/layers/<source_id>/`, and registers those files as real `local_file` sources with `status: local_materialized`. Current materializers include NWI wetlands, USFWS Critical Habitat, SSURGO soils, MDOT/rail transportation context, utility infrastructure, county/state/coastline boundary context, public cemetery/National Register/tribal land context, community facilities, and conservation/recreation lands. The county-boundary materializer also feeds project context so study-area sections can cite intersecting Mississippi county names when available. Existing reviewer-supplied local sources are preserved unless `--replace` is explicitly used.

Build normalized project geometry and run the current constraint engine:

```powershell
.\.venv\Scripts\review-assist.exe build-project-geometry projects/trails
.\.venv\Scripts\review-assist.exe analyze-constraints projects/trails
```

Generate workflow-native project context and source status artifacts:

```powershell
.\.venv\Scripts\review-assist.exe generate-context projects/trails
.\.venv\Scripts\review-assist.exe resolve-sources projects/trails
.\.venv\Scripts\review-assist.exe generate-source-inventory projects/trails
```

Resolve source gaps and explicitly acquire supported public sources:

```powershell
.\.venv\Scripts\review-assist.exe resolve-source-gaps projects/trails
.\.venv\Scripts\review-assist.exe download-source projects/trails usfws_nwi_wetlands
.\.venv\Scripts\review-assist.exe download-source projects/trails usgs_nhd_hydrography
.\.venv\Scripts\review-assist.exe download-source projects/trails usfws_critical_habitat
.\.venv\Scripts\review-assist.exe download-source projects/trails epa_envirofacts_echo
.\.venv\Scripts\review-assist.exe download-source projects/trails fema_nfhl_flood_hazard
.\.venv\Scripts\review-assist.exe prepare-sources projects/trails
.\.venv\Scripts\review-assist.exe prepare-sources projects/trails --include-optional-sources
```

Generate deterministic draft findings, comparison tables, vector-only draft maps, an evidence package, and draft report sections:

```powershell
.\.venv\Scripts\review-assist.exe generate-findings projects/trails
.\.venv\Scripts\review-assist.exe generate-tables projects/trails
.\.venv\Scripts\review-assist.exe generate-maps projects/trails
.\.venv\Scripts\review-assist.exe build-evidence-package projects/trails
.\.venv\Scripts\review-assist.exe generate-report-sections projects/trails
```

Optional GPT report-section drafting is controlled by root `.env` values. Copy `.env.example` to `.env` and set placeholders locally; `.env` is ignored by Git and must not be committed:

```powershell
OPENAI_API_KEY=
OPENAI_INTERPRETER_MODEL=gpt-5.5
GPT_DRAFTING=0
GPT_DRAFTING_WORKERS=2
GPT_DRAFT_MAX_PAYLOAD_BYTES=60000
```

`GPT_DRAFTING=1`, `true`, `yes`, or `on` enables GPT drafting. `0`, `false`, `no`, `off`, empty, or missing disables it. When enabled, report-section generation uses `OPENAI_API_KEY` and `OPENAI_INTERPRETER_MODEL`; if the key is missing the command fails clearly. GPT section calls default to two workers through `GPT_DRAFTING_WORKERS=2`. GPT receives bounded evidence summaries only; raw source files, geometries, GeoJSON feature dumps, shapefile paths, and root `sources/` paths are withheld. Use `--no-gpt-drafting` to force deterministic sections for a run:

```powershell
.\.venv\Scripts\review-assist.exe generate-report-sections projects/trails --no-gpt-drafting
.\.venv\Scripts\review-assist.exe populate-for-review projects/trails --prepare-sources --no-gpt-drafting
.\.venv\Scripts\review-assist.exe build-mvp-deliverable projects/trails --include-optional-sources --no-gpt-drafting
```

Generate and update review queue items:

```powershell
.\.venv\Scripts\review-assist.exe generate-review-queue projects/trails
.\.venv\Scripts\review-assist.exe list-review-queue projects/trails
.\.venv\Scripts\review-assist.exe update-review-item projects/trails report-section-wetlands-and-waterbodies --status accepted --note "Reviewed."
```

Export accepted/edited review queue content into editable Markdown and DOCX packages:

```powershell
.\.venv\Scripts\review-assist.exe export-report projects/trails
.\.venv\Scripts\review-assist.exe export-report projects/trails --include-draft
.\.venv\Scripts\review-assist.exe export-report projects/trails --include-draft --format both
```

Create an internal preview demo deliverable package without changing review item statuses:

```powershell
.\.venv\Scripts\review-assist.exe build-demo-deliverable projects/trails
.\.venv\Scripts\review-assist.exe build-demo-deliverable projects/trails --format both
.\.venv\Scripts\review-assist.exe build-demo-deliverable projects/trails --materialize-local-sources --format both
```

Create a real-data guarded MVP deliverable package. This runs source preparation first and fails by default if no downloaded, provided, or registered source layer is available, or if test fixture/mock source records are detected. Export and deliverable manifests include `data_lineage` and `mvp_quality` so real source evidence, source-backed constraints, copied figure assets, inline tables/figures, placeholders, and warnings are visible:

```powershell
.\.venv\Scripts\review-assist.exe build-mvp-deliverable projects/trails
.\.venv\Scripts\review-assist.exe build-mvp-deliverable projects/trails --include-optional-sources
.\.venv\Scripts\review-assist.exe build-mvp-deliverable projects/trails --materialize-local-sources --include-optional-sources
```

Run the current orchestration behind the future desktop `Populate for Review` action:

```powershell
.\.venv\Scripts\review-assist.exe populate-for-review projects/trails
.\.venv\Scripts\review-assist.exe populate-for-review projects/trails --materialize-local-sources
.\.venv\Scripts\review-assist.exe populate-for-review projects/trails --prepare-sources
.\.venv\Scripts\review-assist.exe populate-for-review projects/trails --materialize-local-sources --prepare-sources
.\.venv\Scripts\review-assist.exe populate-for-review projects/trails --prepare-sources --include-optional-sources
```

For `populate-for-review`, `--include-optional-sources` is valid only with `--prepare-sources`; optional source acquisition must be explicit. When `--materialize-local-sources` and `--prepare-sources` are both present, local warehouse materialization runs first so project-ready local layers satisfy source gaps before public downloads are attempted.

The CLI writes `geometry_summary.json`, normalized input GeoJSON files, `project_geometry.json`, `project_features.geojson`, and `project_analysis_bounds.geojson` under each project's `intermediate/` directory. Constraint artifacts are written under `constraints`, including `constraint_results.json` and clipped source GeoJSON files. Source acquisition manifests and downloads are written under `source_acquisition` when source gap resolution/downloads run. Local source materialization manifests are written under `source_materialization`, and locally copied or materialized source layers are written under `layers`. Evidence packages are written under `evidence`. Markdown/DOCX exports, export manifests, demo/MVP deliverable manifests, copied figure assets under `exports/assets/figures/`, `data_lineage`, and `mvp_quality` summaries are written under `exports`. Workflow artifacts are written under project `context`, `source_status`, `source_inventory`, `findings`, `tables`, `maps`, `drafts`, `review_queue`, and `populate_for_review` directories. Project intermediate outputs, source acquisition artifacts/downloads, source materialization artifacts, evidence packages, constraint artifacts, workflow artifacts, source inventories, draft findings, comparison tables, draft maps, draft report sections, exports, and local project layers are generated/project-specific artifacts and are ignored by Git.

## Testing

Run the current suite with:

```powershell
.\.venv\Scripts\python.exe -m pytest
```

Run the full local readiness check with:

```powershell
.\scripts\verify.ps1
```

The readiness script creates `.venv` when needed, installs the package with development dependencies, runs pytest, and smoke-checks the active sample project CLI workflows.

Implementation phases should add or update tests with the behavior they introduce. New service logic, CLI commands, validation rules, geospatial workflows, source status behavior, review queue behavior, and export behavior should not be left untested unless that tradeoff is explicitly approved and documented.

## Canonical Workflow

1. Open or create a local workspace.
2. Add project inputs such as KMZ/KML alternatives, GIS layers, reports, imagery, PDFs, maps, notes, or study documents.
3. Generate persistent project context: extent, assumptions, detected alternatives, likely report profile, provided sources, missing categories, and reviewer instructions.
4. Resolve needed source categories into a source status set: provided locally, downloadable, downloaded, failed, gated, stubbed, missing, optional, or needs review.
5. Resolve source gaps against the source catalog and, when explicitly requested, materialize available local warehouse sources or acquire supported public sources such as NWI wetlands, USGS NHD hydrography, USFWS Critical Habitat, EPA/ECHO regulated facilities, and optional FEMA NFHL flood hazard.
6. Populate for review by normalizing project geometry, materializing/acquiring/loading registered sources, cropping data to analysis bounds, generating constraint results, findings, tables, maps, evidence packages, narrative drafts, caveats, and provenance notes.
7. Send every generated artifact into the review queue for human edit/accept/reject/verification.
8. Compile accepted or explicitly included reviewed content into editable Markdown/DOCX export packages, create a clearly labeled internal preview demo package, or create a real-data guarded MVP package that blocks mock/test fixture source records.

## Core Principles

- The system drafts; humans decide.
- No hard scoring or automatic preferred alternative.
- Uncertainty and missing data must be preserved.
- Generated findings should be traceable to a source, method, and review status.
- Deterministic GIS checks should remain separate from AI narrative synthesis.
- Imagery-observed features should be treated as review items, not authoritative facts.
- Final reports must be editable and reviewable.

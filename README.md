# Review Assist

This project is an internal prototype for assisting with environmental and contextual review of submitted project geometry, project features, comparison units, and alternatives. It is feature-neutral: routes, corridors, sites, polygons, parcels, study areas, and other submitted features should all flow through the same source-backed review workflow.

The tool is intended to generate source-backed pre-review report packages for human professionals. It should operate as a local, workspace-oriented workflow: users add project inputs, the system resolves needed source data and generates a draft review queue, humans accept/edit/reject items, and accepted content is compiled into export packages.

This is not a recommendation engine and not an automated decision-maker. It does not choose a preferred alternative, rank alternatives, or replace professional judgment.

Human review is mandatory before any output is used outside the draft review process. Generated reports and findings are pre-review drafts until a human reviewer validates, edits, accepts, or rejects them.

The review queue is the core workflow object. Every generated artifact should become a reviewable item before export.

## Current Status

The project has completed Phase 0 scaffold/planning, Phase 1 KMZ/KML ingestion, the first Phase 2A/2B source-context baseline, the Phase 2C catalog-driven source acquisition baseline with explicit NWI, USGS NHD hydrography, USFWS Critical Habitat, EPA/ECHO regulated facilities, and optional FEMA NFHL flood hazard downloaders, local Mississippi source warehouse materialization for NWI wetlands, USFWS Critical Habitat, SSURGO soils, FEMA flood hazard, specific seeded NHD layers, EPA FRS/MARIS regulated facility layers, oil/gas wells, MDOT/rail transportation, utility infrastructure, county/boundary context, public cultural context, community facilities, and conservation/recreation/public land layers, optional AOI-bounded NAIP basemap sidecar materialization, Phase 3 project context/source status artifacts, an initial Phase 4 JSON-backed review queue baseline, Phase 5 populate-for-review orchestration, Phase 6A deterministic finding generation, Phase 6B source provenance/comparison tables, Phase 6C vector-only map/figure generation with matrix-backed deliverable figures, Phase 6D report sections with deterministic and optional GPT drafting, evidence package generation, the first Markdown/DOCX export compiler, internal demo/MVP deliverable package commands, real-data guarded MVP deliverable quality metadata, the first constraint-engine baseline, and the Sprint 1.1 deliverable/prompt contract validators. The current CLI can inspect project KMZ/KML inputs, normalize project geometry into point/site, line/corridor, polygon/area, or mixed feature artifacts, list the source catalog, register local source layers, materialize ignored Mississippi warehouse layers into project-ready GeoJSON, materialize project-local NAIP GeoTIFF basemap sidecars through an explicit command, resolve source gaps, explicitly download NWI wetlands, USGS NHD hydrography, USFWS Critical Habitat, EPA/ECHO regulated facilities, and FEMA NFHL flood hazard, run legacy spatial relationship checks, run constraint overlap/proximity checks, validate the canonical deliverable matrix and report prompt contracts, generate workflow artifacts, generate deterministic draft findings, generate source inventory/table/map/section/evidence artifacts, generate exact matrix-backed deliverable table and figure artifacts, optionally use GPT for source-grounded report section drafting, populate a lean review queue, create/update review queue items, export accepted/edited review items to Markdown/DOCX plus an export manifest, create an internal preview demo deliverable package, and create a real-data guarded MVP deliverable package.

The implementation surface is reusable Python services plus a CLI and a local-first Sprint 4 Flask/Jinja web UI shell. The web UI creates/selects local project workspaces, stages/uploads and commits project inputs into the existing manifest convention, classifies committed inputs through backend services, shows setup/readiness/latest-run status, displays the bounded standard review queue, updates review item state through backend services, shows export readiness/final verification/compactness budget, runs preview or reviewed export through the existing export service, and exposes only manifest-listed output artifacts. No authentication, hosted deployment, broad external API integration beyond explicit source commands, scoring, PDF export, raw/audit artifact review workflow, or production workflow has been implemented. NAIP basemap acquisition is explicit and optional; normal populate does not acquire imagery unless `--materialize-naip-basemap` is used. GPT Interpretive Assist is explicit, opt-in, cached, source-backed, and review-gated; normal Create Review Queue/regenerate paths remain deterministic unless a GPT-specific command/action is invoked.

## Documentation Map

Use the documentation hierarchy to avoid loading the whole repo context:

- `AGENTS.md`: minimal always-loaded agent operating contract.
- `docs/core/CURRENT_STATE.md`: concise current implementation state.
- `docs/core/ARCHITECTURE.md`: current service/artifact architecture summary.
- `docs/core/DECISIONS.md`: durable decisions only.
- `docs/governance/`: truth stabilization, deferred work, and sprint-resolution workflows.
- `docs/domains/README.md`: routing index for subsystem/domain docs.
- `docs/sprints/README.md`: active, planned, and completed sprint index.
- `docs/archive/README.md`: cold historical context and superseded planning docs.
- `CANONICAL_PLAN.md`: active high-level canonical plan; read when a planning decision, deliverable-shape decision, or workflow direction is ambiguous.

## Implementation Closeout

Implementation passes must distinguish code correctness from sample-project artifact freshness. A passing code test does not prove the local UI is showing fresh generated artifacts.

After changes to source/materialization/status/caveat logic, constraints, deliverable tables or figures, evidence, deliverable items, review queue/reset behavior, GPT payloads/cache, export/report assembly, UI adapter paths, review detail display, or canonical artifact paths, identify the minimum affected artifact chain and regenerate only the necessary artifacts from current code with CLI commands. Do not rely on a Flask server that was started before the code change; restart it before using UI actions to regenerate or verify outputs.

Canonical generated artifacts use nested project paths, including `source_status/source_status_set.json`, `deliverable/tables.json`, `deliverable/figures.json`, `evidence/evidence_package.json`, `deliverable/deliverable_items.json`, `review_queue/review_queue.json`, `exports/export_manifest.json`, and `exports/deliverable_package_manifest.json`. Do not commit generated project artifacts unless explicitly approved, and state which generated artifacts were intentionally left uncommitted.

## Directory Notes

- `projects/`: active project workspaces.
- `archive/`: general project archive for retained but inactive files.
- `docs/archive/`: archive for superseded or historical documentation.
- `outputs/`: generated outputs; ignored except for `.gitkeep`.
- `sources/`: local bulk data warehouse for Mississippi-wide source downloads; bulk raw data is ignored by Git, while `source_warehouse_manifest.json` and per-source `source_manifest.json` files describe the expected stable layout. Raw source files are never sent directly to GPT.

## Local Setup

Install the package and development dependencies into the local virtual environment:

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
```

Optional NAIP basemap materialization requires imagery dependencies:

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[dev,imagery]"
```

Inspect a project workspace. The commands below use `projects/trails` as a sample/diagnostic fixture only; replace it with any project workspace path. Review Assist is not a trails app.

```powershell
.\.venv\Scripts\review-assist.exe inspect-project projects/trails
.\.venv\Scripts\review-assist.exe inspect-project projects/conexon_projects
```

Launch the local web UI shell:

```powershell
.\.venv\Scripts\review-assist-web.exe
```

The UI runs at `http://127.0.0.1:8766` by default. Set `REVIEW_ASSIST_PROJECT_ROOT`, `REVIEW_ASSIST_WEB_HOST`, or `REVIEW_ASSIST_WEB_PORT` to override the project root or bind address for local development.

Validate the static Sprint 1.1 deliverable and prompt contracts:

```powershell
.\.venv\Scripts\review-assist.exe validate-deliverable-matrix
.\.venv\Scripts\review-assist.exe validate-report-prompts --json
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
.\.venv\Scripts\review-assist.exe materialize-local-source projects/trails fema_nfhl_flood_hazard
.\.venv\Scripts\review-assist.exe materialize-local-source projects/trails usgs_nhd_flowlines
.\.venv\Scripts\review-assist.exe materialize-local-source projects/trails usgs_nhd_waterbodies
.\.venv\Scripts\review-assist.exe materialize-local-source projects/trails usgs_nhd_other_areas
.\.venv\Scripts\review-assist.exe materialize-local-source projects/trails epa_frs_facilities_ms
.\.venv\Scripts\review-assist.exe materialize-local-source projects/trails maris_brownfields
.\.venv\Scripts\review-assist.exe materialize-local-source projects/trails maris_npdes_facilities
.\.venv\Scripts\review-assist.exe materialize-local-source projects/trails maris_underground_storage_tanks
.\.venv\Scripts\review-assist.exe materialize-local-source projects/trails mdot_transportation_context
.\.venv\Scripts\review-assist.exe materialize-local-source projects/trails maris_boundary_context
.\.venv\Scripts\review-assist.exe materialize-local-source projects/trails maris_public_cultural_context
.\.venv\Scripts\review-assist.exe materialize-local-source projects/trails maris_community_facilities
.\.venv\Scripts\review-assist.exe materialize-local-source projects/trails maris_conservation_recreation_lands
.\.venv\Scripts\review-assist.exe materialize-local-source projects/trails local_utility_infrastructure
.\.venv\Scripts\review-assist.exe materialize-local-sources projects/trails
```

Materialization reads configured statewide/local datasets from the stable source warehouse, clips them to `project_analysis_bounds.geojson`, writes small project-ready GeoJSON files under `projects/<id>/layers/<source_id>/`, and registers those files as real `local_file` sources with `status: local_materialized`. Current materializers include NWI wetlands, USFWS Critical Habitat, SSURGO soils, FEMA flood hazard, specific NHD flowlines/waterbodies/other areas, EPA FRS and MARIS regulated facility layers, oil/gas wells, MDOT/rail transportation context, utility infrastructure, county/state/coastline boundary context, public cemetery/National Register/tribal land context, community facilities, and conservation/recreation/public land layers. The county-boundary materializer also feeds project context so study-area sections can cite intersecting Mississippi county names when available. Existing reviewer-supplied local sources are preserved unless `--replace` is explicitly used.

Optionally materialize an AOI-bounded renderable NAIP basemap sidecar from Microsoft Planetary Computer NAIP COGs:

```powershell
.\.venv\Scripts\review-assist.exe plan-figure-extents projects/trails --json
.\.venv\Scripts\review-assist.exe materialize-naip-basemap projects/trails --json
.\.venv\Scripts\review-assist.exe materialize-naip-basemap projects/trails --for-figure-extents --json
.\.venv\Scripts\review-assist.exe materialize-naip-basemap projects/trails --year 2023 --max-pixels 25000000 --max-tiles 12
.\.venv\Scripts\review-assist.exe materialize-naip-basemap projects/trails --refresh
```

`plan-figure-extents` writes a non-network `maps/figure_extent_plan.json` artifact with core bounds, full render bounds, collar metadata, and grouped NAIP materialization needs. `materialize-naip-basemap` without extra flags keeps the legacy project-analysis-bounds behavior and writes `projects/<id>/basemaps/naip/<year>/naip_project_basemap.tif`. With `--for-figure-extents`, it materializes grouped full-render sidecars such as `projects/<id>/basemaps/naip/small_direct/<year>/naip_project_basemap.tif`. Existing sidecars are reused unless `--refresh` or `--force` is supplied. If optional imagery dependencies or network access are unavailable, the command records a controlled failure and figures can still use vector-only fallback.

Generated report-ready figure PNGs are map panels only. Captions, report-facing titles, source notes, and method notes remain editable artifact/review/export text rather than being baked into the image canvas.

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

`usgs_nhd_hydrography` and `epa_envirofacts_echo` are live public download rollups. They are not required physical warehouse folders when specific seeded or reviewer-supplied local layers already satisfy the relevant source category. `mdeq_environmental_context` remains a manual residual context bucket, not an automated physical source layer.

Generate deterministic draft findings, comparison tables, matrix deliverable tables/figures, draft maps, an evidence package, and draft report sections:

```powershell
.\.venv\Scripts\review-assist.exe generate-findings projects/trails
.\.venv\Scripts\review-assist.exe generate-tables projects/trails
.\.venv\Scripts\review-assist.exe generate-deliverable-tables projects/trails
.\.venv\Scripts\review-assist.exe generate-deliverable-figures projects/trails
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

`GPT_DRAFTING=1`, `true`, `yes`, or `on` permits explicit GPT calls. `0`, `false`, `no`, `off`, empty, or missing disables them. When enabled, GPT uses `OPENAI_API_KEY` and `OPENAI_INTERPRETER_MODEL`; if the key is missing, the GPT command/action fails clearly. GPT receives bounded evidence summaries only; raw source files, geometries, GeoJSON feature dumps, shapefile paths, and root `sources/` paths are withheld. Normal `populate-for-review`, web Create Review Queue, developer reset, and legacy section/item generation remain deterministic unless a GPT-specific command/action or `--gpt-drafting` is used.

GPT Interpretive Assist for the standard review queue is explicit and cached:

```powershell
.\.venv\Scripts\review-assist.exe draft-section-candidates projects/trails --provider gpt --dry-run --max-calls 3
.\.venv\Scripts\review-assist.exe draft-section-candidates projects/trails --provider gpt --sections wetlands-and-waterbodies,hazardous-materials-sites --max-calls 2
```

The command drafts only eligible source-backed `section_text` review candidates by default. It uses `config/report_section_policy.json`, bounded evidence, extent metadata, validation guardrails, and the curated non-evidence style file at `config/report_style_context/environmental_constraints_report_style.md`. Drafts are cached by evidence/policy/prompt-contract/style/model fingerprint, skipped when current by default, and written back as unaccepted review candidates that still block export until reviewed. GPT run metadata records token usage when the provider reports it, and rejected outputs are kept in rejected-cache metadata without replacing the last accepted cache entry.

Legacy report-section/package commands are deterministic by default. Use `--gpt-drafting` only when intentionally testing the older artifact-level GPT path:

```powershell
.\.venv\Scripts\review-assist.exe generate-report-sections projects/trails --no-gpt-drafting
.\.venv\Scripts\review-assist.exe generate-report-sections projects/trails --gpt-drafting
.\.venv\Scripts\review-assist.exe build-mvp-deliverable projects/trails --include-optional-sources --gpt-drafting
```

Generate and update review queue items:

```powershell
.\.venv\Scripts\review-assist.exe generate-review-queue projects/trails
.\.venv\Scripts\review-assist.exe list-review-queue projects/trails
.\.venv\Scripts\review-assist.exe update-review-item projects/trails report-section-wetlands-and-waterbodies --status accepted --note "Reviewed."
```

For local POC testing only, refresh deterministic review artifacts and rebuild the standard queue from current local inputs and registered source layers:

```powershell
.\.venv\Scripts\review-assist.exe reset-review-queue projects/trails --dry-run
.\.venv\Scripts\review-assist.exe reset-review-queue projects/trails --yes
```

The reset refreshes source status, constraints, tables, figures, maps, evidence, deterministic draft sections, deliverable items, and review queue. It does not acquire sources, materialize local warehouse sources, materialize NAIP basemaps, run GPT drafting, delete source data, or change project setup. Use `--include-exports` when stale Markdown/DOCX/package outputs should also be removed.

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

Run the current orchestration behind the future web app `Create Review Queue` action:

```powershell
.\.venv\Scripts\review-assist.exe populate-for-review projects/trails
.\.venv\Scripts\review-assist.exe populate-for-review projects/trails --materialize-local-sources
.\.venv\Scripts\review-assist.exe populate-for-review projects/trails --materialize-naip-basemap
.\.venv\Scripts\review-assist.exe populate-for-review projects/trails --prepare-sources
.\.venv\Scripts\review-assist.exe populate-for-review projects/trails --materialize-local-sources --prepare-sources
.\.venv\Scripts\review-assist.exe populate-for-review projects/trails --prepare-sources --include-optional-sources
```

For `populate-for-review`, `--include-optional-sources` is valid only with `--prepare-sources`; optional source acquisition must be explicit. `--materialize-naip-basemap` is also explicit and failure-tolerant: it plans figure extents, materializes grouped full-render NAIP sidecars before deliverable figure generation, records warnings for failures, and continues with vector-only fallback when imagery cannot be used. Plain populate does not acquire imagery. When `--materialize-local-sources` and `--prepare-sources` are both present, local warehouse materialization runs first so project-ready local layers satisfy source gaps before public downloads are attempted.

The CLI writes `geometry_summary.json`, normalized input GeoJSON files, `project_geometry.json`, `project_features.geojson`, and `project_analysis_bounds.geojson` under each project's `intermediate/` directory. Constraint artifacts are written under `constraints`, including `constraint_results.json`, `comparison_unit_constraints.json`, and clipped source GeoJSON files. Source acquisition manifests and downloads are written under `source_acquisition` when source gap resolution/downloads run. Local source materialization manifests are written under `source_materialization`, and locally copied or materialized source layers are written under `layers`. NAIP basemap sidecars and provenance are written under `basemaps/naip`. Matrix deliverable artifacts are written under `deliverable`. Evidence packages are written under `evidence`. Markdown/DOCX exports, export manifests, demo/MVP deliverable manifests, copied figure assets under `exports/assets/figures/`, `data_lineage`, and `mvp_quality` summaries are written under `exports`. Workflow artifacts are written under project `context`, `source_status`, `source_inventory`, `findings`, `tables`, `maps`, `drafts`, `review_queue`, and `populate_for_review` directories. Project intermediate outputs, source acquisition artifacts/downloads, source materialization artifacts, basemap sidecars, deliverable artifacts, evidence packages, constraint artifacts, workflow artifacts, source inventories, draft findings, comparison tables, draft maps, draft report sections, exports, and local project layers are generated/project-specific artifacts and are ignored by Git.

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
- The workflow remains feature-neutral; `projects/trails` is only a sample fixture.
- No hard scoring or automatic preferred alternative.
- Uncertainty and missing data must be preserved.
- Generated findings should be traceable to a source, method, and review status.
- Deterministic GIS checks should remain separate from AI narrative synthesis.
- Imagery-observed features should be treated as review items, not authoritative facts.
- Final reports must be editable and reviewable.

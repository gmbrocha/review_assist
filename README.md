# Alternatives Review Assistant

This project is an internal prototype for assisting with environmental and contextual review of proposed project alternatives.

The tool is intended to generate source-backed pre-review report packages for human professionals. It should operate as a local, workspace-oriented workflow: users add project inputs, the system resolves needed source data and generates a draft review queue, humans accept/edit/reject items, and accepted content is compiled into export packages.

This is not a recommendation engine and not an automated decision-maker. It does not choose a preferred alternative, rank alternatives, or replace professional judgment.

Human review is mandatory before any output is used outside the draft review process. Generated reports and findings are pre-review drafts until a human reviewer validates, edits, accepts, or rejects them.

The review queue is the core workflow object. Every generated artifact should become a reviewable item before export.

## Current Status

The project has completed Phase 0 scaffold/planning, Phase 1 KMZ/KML ingestion, the first Phase 2A/2B source-context baseline, the Phase 2C catalog-driven source acquisition baseline with explicit NWI, USGS NHD hydrography, USFWS Critical Habitat, and optional FEMA NFHL flood hazard downloaders, Phase 3 project context/source status artifacts, an initial Phase 4 JSON-backed review queue baseline, Phase 5 populate-for-review orchestration, Phase 6A deterministic finding generation, Phase 6B source provenance/comparison tables, Phase 6C vector-only map/figure generation, Phase 6D deterministic draft report sections, the first Markdown export compiler, and the first constraint-engine baseline. The current CLI can inspect project KMZ/KML inputs, normalize project geometry into point/site, line/corridor, polygon/area, or mixed feature artifacts, list the source catalog, register local source layers, resolve source gaps, explicitly download NWI wetlands, USGS NHD hydrography, USFWS Critical Habitat, and FEMA NFHL flood hazard, run legacy spatial relationship checks, run constraint overlap/proximity checks, generate workflow artifacts, generate deterministic draft findings, generate source inventory/table/map/section artifacts, populate a lean review queue, create/update review queue items, and export accepted/edited review items to Markdown plus an export manifest.

The implementation surface is reusable Python services plus a CLI. No GUI, broad external API integration, source downloads beyond opt-in NWI, USGS NHD hydrography, USFWS Critical Habitat, and optional FEMA NFHL flood hazard, AI narrative generation, scoring, DOCX export, basemap/imagery acquisition, or production workflow has been implemented.

## Planning Docs

Key planning documents live at the repo root and under `docs/`:

- `PLAN_REDIRECT.md`: root drift-control plan; read before large implementation work. It defines the destination as filling the example environmental constraints report template with source-backed constraints, visuals, reviewable copy, tables, caveats, and accepted export content.
- `OVERALL_CONTEXT.md`: product philosophy and anti-drift context.
- `WORKFLOW_MODEL.md`: canonical workspace, source-status, review-queue, and export workflow.
- `ARCHITECTURE.md`: conceptual service/module boundaries.
- `FIRST_VERSION_PLAN.md`: desktop GUI first-version plan centered on the review queue.
- `DATA_SOURCES.md`: practical source stack, candidate sources, and source-registry planning.
- `CODE_AUDIT.md`: latest implementation audit notes, fixes, and known limits.
- `REPORT_TAXONOMY.md`: expected report structure.
- `FINDING_TYPES.md`: implemented baseline and future finding/implication types.
- `UNCERTAINTY_AND_PROVENANCE.md`: source traceability and uncertainty policy.
- `MAP_GENERATION.md`: current vector-only map baseline and future map/figure direction.
- `REPORT_ASSEMBLY.md`: findings-to-report workflow and current Markdown export baseline.
- `IMAGERY_REVIEW.md`: imagery observation philosophy.
- `LLM_ASSISTED_SYNTHESIS.md`: future GPT/LLM insertion points and boundaries.

## Directory Notes

- `projects/`: active project workspaces.
- `archive/`: general project archive for retained but inactive files.
- `docs/archive/`: archive for superseded or historical documentation.
- `outputs/`: generated outputs; ignored except for `.gitkeep`.

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
.\.venv\Scripts\review-assist.exe analyze-project projects/trails
```

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
.\.venv\Scripts\review-assist.exe download-source projects/trails fema_nfhl_flood_hazard
.\.venv\Scripts\review-assist.exe prepare-sources projects/trails
.\.venv\Scripts\review-assist.exe prepare-sources projects/trails --include-optional-sources
```

Generate deterministic draft findings, comparison tables, vector-only draft maps, and deterministic draft report sections:

```powershell
.\.venv\Scripts\review-assist.exe generate-findings projects/trails
.\.venv\Scripts\review-assist.exe generate-tables projects/trails
.\.venv\Scripts\review-assist.exe generate-maps projects/trails
.\.venv\Scripts\review-assist.exe generate-report-sections projects/trails
```

Generate and update review queue items:

```powershell
.\.venv\Scripts\review-assist.exe generate-review-queue projects/trails
.\.venv\Scripts\review-assist.exe list-review-queue projects/trails
.\.venv\Scripts\review-assist.exe update-review-item projects/trails report-section-wetlands-and-waterbodies --status accepted --note "Reviewed."
```

Export accepted/edited review queue content into the first editable Markdown package:

```powershell
.\.venv\Scripts\review-assist.exe export-report projects/trails
.\.venv\Scripts\review-assist.exe export-report projects/trails --include-draft
```

Run the current orchestration behind the future desktop `Populate for Review` action:

```powershell
.\.venv\Scripts\review-assist.exe populate-for-review projects/trails
.\.venv\Scripts\review-assist.exe populate-for-review projects/trails --prepare-sources
.\.venv\Scripts\review-assist.exe populate-for-review projects/trails --prepare-sources --include-optional-sources
```

For `populate-for-review`, `--include-optional-sources` is valid only with `--prepare-sources`; optional source acquisition must be explicit.

The CLI writes `geometry_summary.json`, normalized input GeoJSON files, `project_geometry.json`, `project_features.geojson`, and `project_analysis_bounds.geojson` under each project's `intermediate/` directory. Constraint artifacts are written under `constraints/`, including `constraint_results.json` and clipped source GeoJSON files. Source acquisition manifests and downloads are written under `source_acquisition/` when source gap resolution/downloads run. Markdown exports and export manifests are written under `exports/`. Workflow artifacts are written under project `context/`, `source_status/`, `source_inventory/`, `findings/`, `tables/`, `maps/`, `drafts/`, `review_queue/`, and `populate_for_review/` directories. Project intermediate outputs, source acquisition artifacts/downloads, constraint artifacts, workflow artifacts, source inventories, draft findings, comparison tables, draft maps, draft report sections, exports, and local project layers are generated/project-specific artifacts and are ignored by Git.

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
5. Resolve source gaps against the source catalog and, when explicitly requested, acquire supported public sources such as NWI wetlands, USGS NHD hydrography, USFWS Critical Habitat, and optional FEMA NFHL flood hazard.
6. Populate for review by normalizing project geometry, acquiring/loading registered sources, cropping data to analysis bounds, generating constraint results, findings, tables, maps, narrative drafts, caveats, and provenance notes.
7. Send every generated artifact into the review queue for human edit/accept/reject/verification.
8. Compile accepted or explicitly included reviewed content into an editable Markdown export package; DOCX export remains a later target.

## Core Principles

- The system drafts; humans decide.
- No hard scoring or automatic preferred alternative.
- Uncertainty and missing data must be preserved.
- Generated findings should be traceable to a source, method, and review status.
- Deterministic GIS checks should remain separate from AI narrative synthesis.
- Imagery-observed features should be treated as review items, not authoritative facts.
- Final reports must be editable and reviewable.

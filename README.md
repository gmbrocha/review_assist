# Alternatives Review Assistant

This project is an internal prototype for assisting with environmental and contextual review of proposed project alternatives.

The tool is intended to generate source-backed pre-review report packages for human professionals. It should operate as a local, workspace-oriented workflow: users add project inputs, the system resolves needed source data and generates a draft review queue, humans accept/edit/reject items, and accepted content is compiled into export packages.

This is not a recommendation engine and not an automated decision-maker. It does not choose a preferred alternative, rank alternatives, or replace professional judgment.

Human review is mandatory before any output is used outside the draft review process. Generated reports and findings are pre-review drafts until a human reviewer validates, edits, accepts, or rejects them.

The review queue is the core workflow object. Every generated artifact should become a reviewable item before export.

## Current Status

The project has completed Phase 0 scaffold/planning, Phase 1 KMZ/KML ingestion, and the first Phase 2A/2B source-context baseline. The current CLI can inspect project KMZ/KML inputs, list the source catalog, register local source layers, and run early local spatial relationship checks.

The implementation surface is reusable Python services plus a CLI. No GUI, external API integration, source downloads, AI narrative generation, scoring, report generation, review queue persistence, or production workflow has been implemented.

## Planning Docs

Key planning documents live under `docs/`:

- `OVERALL_CONTEXT.md`: product philosophy and anti-drift context.
- `WORKFLOW_MODEL.md`: canonical workspace, source-status, review-queue, and export workflow.
- `ARCHITECTURE.md`: conceptual service/module boundaries.
- `FIRST_VERSION_PLAN.md`: desktop GUI first-version plan centered on the review queue.
- `DATA_SOURCES.md`: practical source stack, candidate sources, and source-registry planning.
- `CODE_AUDIT.md`: latest implementation audit notes, fixes, and known limits.
- `REPORT_TAXONOMY.md`: expected report structure.
- `FINDING_TYPES.md`: future finding and implication types.
- `UNCERTAINTY_AND_PROVENANCE.md`: source traceability and uncertainty policy.
- `MAP_GENERATION.md`: future map/figure generation direction.
- `REPORT_ASSEMBLY.md`: future findings-to-report workflow.
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

Generate workflow-native project context and source status artifacts:

```powershell
.\.venv\Scripts\review-assist.exe generate-context projects/trails
.\.venv\Scripts\review-assist.exe resolve-sources projects/trails
```

The CLI writes `geometry_summary.json`, normalized GeoJSON files, clipped source GeoJSON files, and `spatial_relationships.json` under each project's `intermediate/` directory. Workflow artifacts are written under project `context/` and `source_status/` directories. Project intermediate outputs, workflow artifacts, and local project layers are generated/project-specific artifacts and are ignored by Git.

## Canonical Workflow

1. Open or create a local workspace.
2. Add project inputs such as KMZ/KML alternatives, GIS layers, reports, imagery, PDFs, maps, notes, or study documents.
3. Generate persistent project context: extent, assumptions, detected alternatives, likely report profile, provided sources, missing categories, and reviewer instructions.
4. Resolve needed source categories into a source status set: provided locally, downloadable, downloaded, gated, stubbed, missing, optional, or needs review.
5. Populate for review by acquiring/loading sources, clipping data, generating spatial relationships, findings, tables, maps, narrative drafts, caveats, and provenance notes.
6. Send every generated artifact into the review queue for human edit/accept/reject/verification.
7. Compile accepted or explicitly included reviewed content into an editable export package.

## Core Principles

- The system drafts; humans decide.
- No hard scoring or automatic preferred alternative.
- Uncertainty and missing data must be preserved.
- Generated findings should be traceable to a source, method, and review status.
- Deterministic GIS checks should remain separate from AI narrative synthesis.
- Imagery-observed features should be treated as review items, not authoritative facts.
- Final reports must be editable and reviewable.

# Alternatives Review Assistant

This project is an internal prototype for assisting with environmental and contextual review of proposed project alternatives.

The tool is intended to generate source-backed pre-review report packages for human professionals. It may eventually ingest a project footprint and multiple proposed alternatives, gather or crop relevant GIS and contextual layers, run repeatable checks, and draft structured findings.

This is not a recommendation engine and not an automated decision-maker. It does not choose a preferred alternative, rank alternatives, or replace professional judgment.

Human review is mandatory before any output is used outside the draft review process. Generated reports and findings are pre-review drafts until a human reviewer validates, edits, accepts, or rejects them.

## Current Status

The project is currently in scaffold and planning phase only.

No GIS processing, external API integration, AI narrative generation, scoring, report generation, or production workflow has been implemented.

## Planning Docs

Key planning documents live under `docs/`:

- `OVERALL_CONTEXT.md`: product philosophy and anti-drift context.
- `ARCHITECTURE.md`: conceptual service/module boundaries.
- `FIRST_VERSION_PLAN.md`: desktop GUI first-version plan centered on the review queue.
- `DATA_SOURCES.md`: practical source stack, candidate sources, and source-registry planning.
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

## Intended Workflow

1. A user provides a project footprint and proposed alternatives, likely as KMZ or KML initially.
2. The system normalizes geometries.
3. The system gathers or clips relevant source layers for the project area.
4. The system creates draft findings for each alternative.
5. The system generates an editable pre-review report package.
6. A human reviewer validates and edits all findings before release.

## Core Principles

- The system drafts; humans decide.
- No hard scoring or automatic preferred alternative.
- Uncertainty and missing data must be preserved.
- Generated findings should be traceable to a source, method, and review status.
- Deterministic GIS checks should remain separate from AI narrative synthesis.
- Imagery-observed features should be treated as review items, not authoritative facts.
- Final reports must be editable and reviewable.

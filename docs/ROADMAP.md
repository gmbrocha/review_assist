# Roadmap

This roadmap is intentionally rough and may change as requirements are clarified.

## Phase 0: Scaffold and Clarify Requirements

- Establish repository structure.
- Document product boundaries.
- Confirm initial input and output expectations.
- Identify first candidate data sources.
- Create project workspaces for current example projects.
- Document report taxonomy, finding types, uncertainty, provenance, map-generation direction, and report assembly direction.

## Phase 1: Parse KMZ/KML and Inspect Geometries

- Parse KMZ and KML files.
- Identify project footprints and alternatives.
- Display or summarize geometry metadata.
- Report validation issues.
- Move or reference real KMZ inputs from project workspaces.
- Standardize a geospatial Python dependency plan, likely including GeoPandas.

## Phase 2: Local/Source-Layer Clipping and Spatial Checks

- Define initial source/layer registry.
- Clip or filter local layers to the project area.
- Run deterministic spatial checks.
- Preserve source and method metadata.
- Support configurable corridor/buffer assumptions.
- Produce spatial relationship records before narrative drafting.

## Phase 3: Finding Model and Review Statuses

- Define structured finding fields.
- Add review statuses.
- Support reviewer notes and edits.
- Track uncertainty and unable-to-verify cases.
- Map spatial relationship types to reviewable contextual implications.
- Distinguish source-backed findings from imagery-observed review items.

## Phase 4: Map/Figure and Table Generation

- Generate overall project maps.
- Generate resource-specific maps.
- Generate panel maps where useful.
- Generate comparison tables by resource and alternative.
- Preserve legends, source notes, draft labels, and map provenance.

## Phase 5: Report Draft Generation and Assembly

- Generate editable draft report packages.
- Include maps, tables, findings, source notes, and review status.
- Keep generated reports clearly labeled as pre-review drafts.
- Compile appendices/reference materials where available.
- Generate a package manifest for traceability.

## Phase 6: Imagery Observation Workflow

- Support imagery-based review observations.
- Distinguish observed features from authoritative source-backed facts.
- Capture reviewer confirmation or rejection.
- Support cropped imagery and overlay review.
- Preserve imagery source/date/attribution where available.

## Phase 7: Optional AI-Assisted Narrative Synthesis

- Explore AI-assisted drafting after deterministic checks and review workflow are defined.
- Keep narrative synthesis traceable to source findings.
- Preserve uncertainty and human review requirements.
- Use LLMs for draft language, implication phrasing, summary checks, and structured normalization without replacing source-backed analysis.

## Still Out of Scope

- Production GIS pipelines.
- Paid service integrations.
- MDAH restricted access integration.
- Autonomous ranking or recommendation logic.
- Field-verified conclusions.
- Black-box report generation.

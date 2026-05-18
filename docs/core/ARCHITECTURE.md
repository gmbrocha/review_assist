# Architecture

Review Assist is a service-first, workspace-oriented pipeline. The future web app should remain a thin operator surface over these services.

## Current Shape

The active backend is Python service modules plus CLI commands. Project-specific generated state is stored as JSON/GeoJSON/PNG/DOCX artifacts under ignored `projects/<project_id>/` folders. Root `sources/` may contain large local source warehouses and is not treated as report evidence unless materialized/registered with provenance.

## Primary Flow

1. Project workspace and manifest.
2. Input inspection and project geometry normalization.
3. Project context and source status resolution.
4. Optional local source materialization and explicit public source acquisition.
5. Source inventory and deterministic constraint analysis.
6. Draft findings, tables, maps, evidence package, and report sections.
7. Review queue generation.
8. Reviewed-content export.

Sprint 1.2 will add explicit input package and project area artifacts before deeper analysis. Sprint 1.3 will add comparison units as the report-facing geometry layer.

## Service Boundaries

- Project/input/geometry: workspace manifests, KMZ/KML parsing, normalized project features, analysis bounds.
- Source management: source catalog, project registries, materialization, acquisition, status, inventory.
- Constraint engine: deterministic spatial overlays, buffers, crossings, proximity, measurements.
- Evidence generation: findings, comparison tables, maps, evidence package, section drafts.
- Review: JSON-backed review queue, reviewer statuses, notes, export eligibility.
- Export: Markdown/DOCX report assembly from reviewed or explicit preview items.
- Governance: truth stabilization, deferred work, sprint resolution, documentation routing.

## Current Non-Goals

- No production web app yet.
- No final PDF export.
- No ranking, scoring, preferred-alternative logic, approval, clearance, or final determinations.
- No restricted-source automation without explicit approval.
- No basemap/raster-backed cartographic output yet.

## Deeper Domain Docs

Use `docs/domains/README.md` to route subsystem reading. Common paths:

- Workflow model: `docs/domains/WORKFLOW_MODEL.md`
- Data sources: `docs/domains/DATA_SOURCES.md`
- Review policy: `docs/domains/REVIEW_POLICY.md`
- Report assembly: `docs/domains/REPORT_ASSEMBLY.md`
- Map generation: `docs/domains/MAP_GENERATION.md`
- LLM-assisted synthesis: `docs/domains/LLM_ASSISTED_SYNTHESIS.md`
- Uncertainty/provenance: `docs/domains/UNCERTAINTY_AND_PROVENANCE.md`

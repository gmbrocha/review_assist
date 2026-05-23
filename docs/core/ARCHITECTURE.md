# Architecture

Review Assist is a service-first, workspace-oriented pipeline. The future web app should remain a thin operator surface over these services.

## Current Shape

The active backend is Python service modules plus CLI commands. Project-specific generated state is stored as JSON/GeoJSON/PNG/DOCX artifacts under ignored `projects/<project_id>/` folders. Root `sources/` may contain large local source warehouses and is not treated as report evidence unless materialized/registered with provenance.

## Primary Flow

1. Project workspace and manifest.
2. Input package classification.
3. Project geometry normalization, project area context, and comparison-unit generation.
4. Project context and source status resolution.
5. Optional local source materialization and explicit public source acquisition.
6. Source inventory and deterministic constraint analysis.
7. Draft findings, comparison tables, matrix deliverable tables/figures, maps, evidence package, and report sections.
8. Review queue generation.
9. Reviewed-content export.

Sprint 1.2 added explicit input package and project area artifacts before deeper analysis. Sprint 1.3 added comparison units as a report-facing geometry layer while preserving raw normalized project features.

## Service Boundaries

- Project/input/geometry: workspace manifests, input package classification, KMZ/KML parsing, normalized project features, analysis bounds, project area context, comparison units.
- Source management: source catalog, project registries, materialization, acquisition, status, inventory.
- Constraint engine: deterministic spatial overlays, buffers, crossings, proximity, measurements.
- Evidence generation: findings, comparison tables, matrix deliverable tables/figures, legacy audit maps, evidence package, section drafts.
- Review: JSON-backed review queue, reviewer statuses, notes, export eligibility.
- Export: Markdown/DOCX report assembly from reviewed or explicit preview items.
- Governance: truth stabilization, deferred work, sprint resolution, documentation routing.

## Current Non-Goals

- No production web app yet.
- No final PDF export.
- No ranking, scoring, preferred-alternative logic, approval, clearance, or final determinations.
- No restricted-source automation without explicit approval.
- No MrSID decoding, paid basemap APIs, restricted-source automation, or final cartographic export. Deliverable figures may use selected renderable MARIS/NAIP sidecars or project-local NAIP render assets when available; otherwise they preserve the limitation as provenance, warning, or stub status.

## Deeper Domain Docs

Use `docs/domains/README.md` to route subsystem reading. Common paths:

- Workflow model: `docs/domains/WORKFLOW_MODEL.md`
- Data sources: `docs/domains/DATA_SOURCES.md`
- Review policy: `docs/domains/REVIEW_POLICY.md`
- Report assembly: `docs/domains/REPORT_ASSEMBLY.md`
- Map generation: `docs/domains/MAP_GENERATION.md`
- LLM-assisted synthesis: `docs/domains/LLM_ASSISTED_SYNTHESIS.md`
- Uncertainty/provenance: `docs/domains/UNCERTAINTY_AND_PROVENANCE.md`

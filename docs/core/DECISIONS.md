# Decision Log

This file contains durable current decisions only. Historical planning detail belongs in `docs/archive/`; subsystem detail belongs in `docs/domains/`.

| Date | Decision | Rationale | Affected Areas | Superseded By |
| --- | --- | --- | --- | --- |
| 2026-05-14 | The tool will not select or recommend a preferred alternative. | The system supports human review and objective constraint presentation. | Findings, reports, review queue, export, prompts. | |
| 2026-05-14 | Avoid hard scoring unless explicitly requested and documented as non-decisional support. | Scores can imply a recommendation or selection. | Comparison, tables, narrative, UI. | |
| 2026-05-14 | Deterministic GIS/source facts must remain separate from imagery-observed review context. | Imagery observations require human validation and are not authoritative facts by default. | Source modeling, maps, review items. | |
| 2026-05-14 | Generated reports are pre-review drafts only. | Human review remains mandatory before external use. | Report generation, export, labels, manifests. | |
| 2026-05-14 | Product direction is "no blank page." | The system should generate comprehensive first-pass review packages without pretending they are final. | Populate for review, report sections, maps, tables, queue. | |
| 2026-05-14 | Public authoritative GIS can support screening but remains screening-level. | Provenance, source age, uncertainty, and field-verification caveats must remain visible. | Source status, findings, report text. | |
| 2026-05-14 | Buffer assumptions must remain configurable and auditable. | Corridor assumptions affect measurements and must not become hidden methodology. | Geometry, constraints, tables, maps. | |
| 2026-05-14 | MDAH/restricted cultural resource integration is deferred unless explicitly approved. | Restricted/sensitive data requires controlled access and handling. | Cultural resources, source acquisition, maps, reports. | |
| 2026-05-14 | LLM synthesis is allowed only as reviewable draft synthesis from structured evidence. | AI must not replace deterministic checks or invent facts. | Evidence package, section drafting, prompts, review queue. | |
| 2026-05-14 | The review queue is the product spine. | Generated findings, sections, maps, tables, caveats, and provenance need human decisions before export. | Review, export, web app, artifacts. | |
| 2026-05-14 | The future UI must stay thin over service-layer workflow logic. | Pipeline, GIS, review, and export behavior should remain testable outside UI handlers. | Architecture, web app, services. | |
| 2026-05-14 | Early implementation is services plus CLI. | Stable services make the later web app easier to wire without burying workflow logic. | CLI, tests, architecture. | |
| 2026-05-14 | Project inputs are copied into project workspaces. | Workspaces should be self-contained and auditable while root originals remain references. | Projects, manifests, ingestion. | |
| 2026-05-14 | GeoPandas/Shapely/PyProj/Pyogrio/Pandas are the geospatial baseline. | This stack supports repeatable local vector GIS workflows. | Ingestion, geometry, constraints, maps. | |
| 2026-05-14 | Workflow artifacts use JSON/GeoJSON for the current baseline. | Inspectable files are adequate while workflow state and UI needs are evolving. | Project context, source status, queue, manifests. | |
| 2026-05-14 | Source status is first-class workflow state. | Missing, failed, gated, manual, optional, and provided sources must be visible. | Source status, findings, report sections, review queue. | |
| 2026-05-14 | Populate for Review is the main generation action. | The future UI action should prepare sources, run analysis, and create reviewable items. | Populate, source workflow, review queue. | |
| 2026-05-14 | Exports compile reviewed content only by default. | Unreviewed generated content must not be treated as user-facing final output. | Export, review queue, package commands. | |
| 2026-05-14 | Existing CLI commands should remain backward-compatible where practical. | New workflow-native commands should not break current inspection/analysis workflows. | CLI, tests, docs. | |
| 2026-05-14 | Each behavior-changing implementation phase requires tests. | Validation and regressions matter because workflow artifacts are interdependent. | Services, CLI, docs. | |
| 2026-05-14 | Review queue persistence uses JSON for the current baseline. | JSON keeps queue state inspectable before a production UI/storage decision. | Review queue, export. | |
| 2026-05-14 | Populate for Review starts as orchestration, not recommendations or automatic export. | It should create inspectable artifacts and review items, not final decisions. | Populate, source acquisition, queue. | |
| 2026-05-14 | Deterministic draft findings come before maps, reports, UI, and LLM work. | Structured facts should precede visual/narrative synthesis. | Findings, maps, reports. | |
| 2026-05-14 | Source provenance and comparison tables are backend artifacts before maps/exports. | Evidence should be inspectable and reusable downstream. | Source inventory, tables, report. | |
| 2026-05-14 | Map generation starts vector-only. | Basemap/raster support requires separate handling and provenance. | Maps, figures, imagery. | |
| 2026-05-14 | Report section drafting starts deterministic. | A deterministic fallback keeps drafting available without LLM calls. | Report sections, evidence, review queue. | |
| 2026-05-15 | Markdown export proved accepted-content assembly before DOCX. | Markdown made review-gated assembly easier to validate before layout fidelity. | Export. | |
| 2026-05-15 | DOCX package assembly is part of MVP preview, not final template fidelity. | DOCX helps client review while final formatting and PDF remain later work. | Export, package commands. | |
| 2026-05-15 | MVP deliverables must prove real-data lineage. | Client-facing previews must not rely on mock/test fixture evidence. | Source lineage, MVP package, export. | |
| 2026-05-15 | MVP packages should render evidence inside the report body. | Tables and figures should support section review rather than only appear as attachments. | Export, tables, figures, report sections. | |
| 2026-05-15 | Failed source downloads must remain visible downstream. | Failed attempts must not collapse back into generic missing/downloadable states. | Source acquisition, source status, findings, reports, queue. | |
| 2026-05-15 | GPT drafting must be evidence-grounded and review-gated. | GPT output is draft section copy from structured evidence, not authoritative analysis. | Evidence package, LLM provider, prompts, queue. | |
| 2026-05-14 | Current projects are examples, not product boundaries. | Trails and Conexon examples represent input shapes, not hard-coded workflows. | Geometry, comparison units, tests. | |
| 2026-05-14 | The system presents constraints, not choices. | Human/client/planning processes make decisions outside the tool. | Reports, UI, review policy. | |
| 2026-05-17 | `CANONICAL_PLAN.md` is the active high-level planning source. | Prior planning docs were consolidated; duplicates should defer to the canonical plan unless a later decision supersedes it. | Planning, sprints, docs. | |

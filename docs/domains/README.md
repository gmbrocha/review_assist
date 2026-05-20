# Domain Documentation Index

Use this index to load only the docs relevant to the subsystem being touched.

| Domain Area | Owning Doc | Read When Touching |
| --- | --- | --- |
| Workflow model and end-to-end product flow | `docs/domains/WORKFLOW_MODEL.md` | Populate-for-review, source status, review queue, export flow, or workflow state changes. |
| Data/source catalog and source acquisition | `docs/domains/DATA_SOURCES.md` | Source catalog entries, materializers, downloads, source status semantics, provenance. |
| Local source warehouse layout | `docs/domains/SOURCE_WAREHOUSE.md` | Stable source warehouse folders, raw source provenance layout, source manifests, seeded-source materialization. |
| Review policy and reviewer states | `docs/domains/REVIEW_POLICY.md` | Review queue states, reviewer actions, export eligibility, human review boundaries. |
| Report assembly and exports | `docs/domains/REPORT_ASSEMBLY.md` | Markdown/DOCX exports, report sections, package manifests, export behavior. |
| Report policy and extent semantics | `docs/domains/REPORT_POLICY.md` | Section extent scope, visual extent class, comparison-unit expansion policy, GPT readiness, and report wording boundaries. |
| Report taxonomy and deliverable shape | `docs/domains/REPORT_TAXONOMY.md` | Section taxonomy, report categories, deliverable organization. |
| Findings and finding types | `docs/domains/FINDING_TYPES.md` | Draft findings, finding templates, finding semantics, implication phrasing. |
| Uncertainty and provenance | `docs/domains/UNCERTAINTY_AND_PROVENANCE.md` | Source confidence, uncertainty flags, provenance, caveats, assumptions. |
| Map and figure generation | `docs/domains/MAP_GENERATION.md` | Static maps, figures, legends, map artifacts, figure exports. |
| Imagery/basemap review | `docs/domains/IMAGERY_REVIEW.md` | NAIP/MARIS imagery, basemap context, imagery-observed review items. |
| LLM-assisted synthesis | `docs/domains/LLM_ASSISTED_SYNTHESIS.md` | GPT drafting, prompt guardrails, structured evidence payloads. |
| Deliverable/client context | `docs/domains/DELIVERABLE_CONTEXT.md` | Example-report structure, client-facing deliverable assumptions. |
| Product framing | `docs/domains/PRODUCT_BRIEF.md` | Product scope, audience, high-level use case. |
| Overall project context | `docs/domains/OVERALL_CONTEXT.md` | Broad historical/product background when needed. |
| Client context summary | `docs/domains/CLIENT_CONTEXT_SUMMARY.md` | Client-specific framing or shorthand context. |
| Audit notes | `docs/domains/CODE_AUDIT.md` | Existing audit findings, verification notes, quality review. |

Do not load every domain doc by default. Pick the owning doc for the subsystem in the task.

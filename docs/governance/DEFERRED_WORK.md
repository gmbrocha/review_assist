# Deferred Work

This file is mandatory tracked project state for deferred review-assist work. Every sprint planning pass must review it and update it when implementation needs, risks, unresolved questions, or follow-up work are postponed.

Every new sprint planning pass must review:

- this registry
- unresolved review methodology concerns
- known source limitations
- known uncertainty propagation gaps

## How To Record Deferred Items

Each deferred item should include:

- `Deferred item`: short name.
- `Why postponed`: reason it is not handled now.
- `Affected sections/workflows`: report sections, source workflows, review queue behavior, map/export behavior, or methodology affected.
- `Risk if forgotten`: what could become misleading, stale, unsupported, or operationally blocked.
- `Temporary simplification`: whether current outputs are simplified or incomplete because of the deferral.
- `Target sprint/subunit`: future sprint/subunit when known.
- `Status`: open, in progress, resolved, or superseded.

## Active Deferred Items

### Canonical Deliverable Contract Wiring

- `Deferred item`: Wire the Sprint 1.1 deliverable matrix into report-facing generation.
- `Why postponed`: Sprint 1.1 intentionally added static config, loaders, validators, tests, and CLI validation only. It did not change report generation, review queue generation, table generation, figure generation, or export behavior.
- `Affected sections/workflows`: Report section generation, deliverable tables, deliverable figures, deliverable items, review queue generation, export assembly, GPT-assisted section drafting.
- `Risk if forgotten`: The legacy report profile/templates can continue to drive output while the canonical matrix only validates on the side, allowing output volume, section coverage, stub policy, and table/figure inventory to drift away from the redirected workflow.
- `Temporary simplification`: Sprint 2.2 now generates exact matrix-backed deliverable tables, but report sections, figures, review queue deliverable items, and export gates can still use legacy artifacts until their owning sprints wire the matrix into those paths.
- `Target sprint/subunit`: Sprint 2.3 for deliverable figures and evidence refs; Sprint 3.1 for deliverable items/review queue; Sprint 3.2 for export gate/package manifests.
- `Status`: open.

### Canonical Prompt Contract Wiring

- `Deferred item`: Wire `config/report_generation_prompts.json` into GPT-assisted and deterministic section generation.
- `Why postponed`: Sprint 1.1 created and validated the prompt contract but did not replace the existing section drafting prompt flow.
- `Affected sections/workflows`: GPT-assisted report sections, deterministic section fallback, evidence package inputs, review queue section items.
- `Risk if forgotten`: Prompt guardrails may remain validated but inactive, increasing the chance that section drafting behavior diverges from the canonical no-ranking, no-selection, no-final-determination, source-backed-only contract.
- `Temporary simplification`: The prompt contract is machine-readable and test-covered, but current report drafting still uses existing implementation pathways.
- `Target sprint/subunit`: Sprint 3.1.
- `Status`: open.

### Dynamic Wetlands/Waterbodies Comparison-Unit Sections

- `Deferred item`: Expand the dynamic 3.1.1.x wetlands/waterbodies section template into one reviewable subsection per comparison unit.
- `Why postponed`: Sprint 1.1 represented the template in the matrix only. Sprint 1.3 now generates comparison-unit artifacts, but deliverable item expansion remains planned for Sprint 3.1.
- `Affected sections/workflows`: Section 3.1.1 Wetlands and Waterbodies, dynamic 3.1.1.x subsections, Table 1, Figure 1, review queue item count control.
- `Risk if forgotten`: Raw segments or individual hits could continue to appear as report/review units, reintroducing the oversized-report failure mode the redirect is meant to prevent.
- `Temporary simplification`: Comparison units exist as pre-review artifacts and are recorded in populate manifests, but the dynamic target is not expanded into runtime section items yet.
- `Target sprint/subunit`: Sprint 3.1.
- `Status`: open.

### Census Live Acquisition And MOE Handling

- `Deferred item`: Add live Census TIGER/ACS acquisition and fuller margin-of-error handling beyond registered local Census-like source tables.
- `Why postponed`: Sprint 2.2 implemented demographic deliverable table generation from registered local `census_tiger_acs` source rows and honest stubs when Census data/API setup is unavailable. It did not add a TIGER downloader, live ACS API client, or complete MOE presentation rules.
- `Affected sections/workflows`: Community/socioeconomic source status, source acquisition, source inventory, income demographics table, demographic composition table, report sections that cite demographic tables.
- `Risk if forgotten`: A project without a registered local Census source will correctly show table stubs, but future users may expect `CENSUS_API_KEY` alone to populate ACS rows or may later add ACS values without source year/geography/MOE caveats.
- `Temporary simplification`: Local/mock-ready Census source rows can populate the two demographic deliverable tables; otherwise the tables are explicit review-needed stubs.
- `Target sprint/subunit`: Future source acquisition/data-quality hardening.
- `Status`: open.

### Raster-Backed NAIP Figure Rendering

- `Deferred item`: Render NAIP/MARIS basemaps into deliverable figures only when renderable sidecars are available.
- `Why postponed`: Sprint 2.1 implemented catalog/profile/status behavior plus basemap indexing and sidecar detection, but intentionally avoided rasterio, GDAL, MrSID decoding, paid basemap APIs, and figure rendering.
- `Affected sections/workflows`: Map generation, deliverable figures, figure validation issues, Attachment A panel maps, source/provenance notes for imagery-backed figures.
- `Risk if forgotten`: The workflow may correctly record selected NAIP provenance but still produce vector-only or stubbed figures without making the rendering limitation obvious.
- `Temporary simplification`: `.sid` files remain provenance only; `.tif`, `.tiff`, and `.png` sidecars are detected but not yet rendered by deliverable figure generation.
- `Target sprint/subunit`: Sprint 2.3.
- `Status`: open.

## Resolved Deferred Items

### Sprint 1.2 Project Intake Artifacts

- `Deferred item`: Implement the Sprint 1.2 project intake artifacts: `context/input_package.json`, `context/project_area.json`, input classification CLI, project area CLI, NAIP/MARIS basemap provenance, and populate integration.
- `Resolution`: Implemented as service-layer artifacts and CLI commands; `populate-for-review` now records input package and project area artifact paths, detected counties, basemap renderability status, and related warnings.
- `Remaining limitation`: Sprint 2.1 added the source catalog entry, example profile requirement, source status detail, and standalone basemap service for MARIS/NAIP 2025 provenance/renderability. Raster-backed map/figure rendering remains deferred.
- `Target sprint/subunit`: Sprint 1.2.
- `Status`: resolved.

### Sprint 2.1 Source Profile And Basemaps

- `Deferred item`: Implement the Sprint 2.1 source/profile/basemap setup for the example-report-shaped workflow.
- `Resolution`: Implemented `environmental_constraints_example` as the default alternatives-review profile; added Sprint 2.1 source catalog entries and attachment/manual stubs; exposed per-source status details; represented missing Census API key as a visible stub; cataloged `maris_naip_2025_imagery`; added service-level MARIS/NAIP basemap indexing and `.tif`/`.tiff`/`.png` sidecar detection.
- `Remaining limitation`: Sprint 2.2 resolved comparison-unit deliverable tables and Census table stubs/local-source rows. Raster-backed figures, panel maps, exact deliverable evidence wiring, and live Census acquisition remain deferred to their owning future work.
- `Target sprint/subunit`: Sprint 2.1.
- `Status`: resolved.

### Sprint 2.2 Comparison Constraints And Tables

- `Deferred item`: Implement the Sprint 2.2 comparison-unit constraints and exact deliverable table targets.
- `Resolution`: Implemented `constraints/comparison_unit_constraints.json`, source-specific normalization for NWI wetland classes, hydrography crossing de-duplication, FEMA flood-zone acreage aggregation, local Census-like ACS table rows, four exact matrix-backed deliverable tables at `deliverable/tables.json`, required stubs for unavailable sources, CLI commands, populate manifest wiring, docs, and focused tests.
- `Remaining limitation`: Deliverable figures, raster-backed NAIP/MARIS rendering, panel maps, evidence package refs, review queue deliverable item expansion, export gating, and live Census acquisition remain deferred to their owning future work items.
- `Target sprint/subunit`: Sprint 2.2.
- `Status`: resolved.

# Source Directory

This directory contains the Python package for local project ingestion, geometry inspection, project geometry normalization, source registry handling, source gap/acquisition handling, project context/source status artifacts, source inventory/provenance artifacts, legacy spatial relationship checks, constraint overlap/proximity analysis, deterministic draft finding generation, comparison table artifacts, vector-only map artifacts, deterministic draft report section artifacts, static deliverable/prompt contract validation, JSON-backed review queue items, Markdown/DOCX export package generation, internal demo deliverable package orchestration, real-data MVP deliverable guardrails, and populate-for-review orchestration.

Current implementation scope:

- Project manifest loading.
- KMZ/KML geometry ingestion.
- Geometry summaries and validation issues.
- Report profile loading.
- Deliverable matrix and report prompt contract loading/validation.
- Project context artifact generation.
- Global source catalog loading.
- Project source registry loading and local source registration.
- Local source warehouse materialization into project-ready GeoJSON layers.
- Source gap resolution and opt-in public source acquisition.
- USFWS NWI wetlands, USGS NHD hydrography, USFWS Critical Habitat, EPA/ECHO regulated facilities, and optional FEMA NFHL flood hazard downloaders with project-local acquisition provenance.
- Source status set resolution, including failed supported-download caveats.
- Source inventory and provenance artifact generation.
- Local source-layer clipping and legacy spatial relationship checks.
- Project geometry normalization for point/site, line/corridor, polygon/area, and mixed inputs.
- Constraint overlap/proximity analysis from registered local source layers.
- Deterministic draft finding generation from source status, constraint result, and legacy spatial relationship artifacts.
- Descriptive comparison table artifact generation.
- Vector-only PNG map/figure generation and map manifest validation.
- Deterministic draft report section generation and report section artifact validation.
- Lean review queue generation, listing, and item status updates.
- Editable Markdown/DOCX report export and export manifest generation.
- Internal demo deliverable package generation.
- Data lineage classification for real project/source data, stubs, and test fixture/mock records.
- Real-data MVP deliverable package generation.
- Populate-for-review orchestration and run manifest generation.
- CLI entrypoints for project inspection and workflow artifact generation.

Do not put UI callback logic here. Future web app UI code should call service modules rather than owning workflow logic directly.

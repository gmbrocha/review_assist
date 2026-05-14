# Source Directory

This directory contains the Python package for local project ingestion, geometry inspection, source registry handling, project context/source status artifacts, source inventory/provenance artifacts, early spatial relationship checks, deterministic draft finding generation, comparison table artifacts, vector-only map artifacts, JSON-backed review queue items, and populate-for-review orchestration.

Current implementation scope:

- Project manifest loading.
- KMZ/KML geometry ingestion.
- Geometry summaries and validation issues.
- Report profile loading.
- Project context artifact generation.
- Global source catalog loading.
- Project source registry loading and local source registration.
- Source status set resolution.
- Source inventory and provenance artifact generation.
- Local source-layer clipping and spatial relationship checks.
- Deterministic draft finding generation from source status and spatial relationship artifacts.
- Descriptive comparison table artifact generation.
- Vector-only PNG map/figure generation and map manifest validation.
- Review queue generation, listing, and item status updates.
- Populate-for-review orchestration and run manifest generation.
- CLI entrypoints for project inspection and workflow artifact generation.

Do not put GUI callback logic here. Future desktop UI code should call service modules rather than owning workflow logic directly.

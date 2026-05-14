# Source Directory

This directory contains the Python package for local project ingestion, geometry inspection, source registry handling, project context/source status artifacts, early spatial relationship checks, and JSON-backed review queue items.

Current implementation scope:

- Project manifest loading.
- KMZ/KML geometry ingestion.
- Geometry summaries and validation issues.
- Report profile loading.
- Project context artifact generation.
- Global source catalog loading.
- Project source registry loading and local source registration.
- Source status set resolution.
- Local source-layer clipping and spatial relationship checks.
- Review queue generation, listing, and item status updates.
- CLI entrypoints for project inspection and workflow artifact generation.

Do not put GUI callback logic here. Future desktop UI code should call service modules rather than owning workflow logic directly.

# Source Directory

This directory contains the Python package for local project ingestion, geometry inspection, source registry handling, and early spatial relationship checks.

Current implementation scope:

- Project manifest loading.
- KMZ/KML geometry ingestion.
- Geometry summaries and validation issues.
- Global source catalog loading.
- Project source registry loading and local source registration.
- Local source-layer clipping and spatial relationship checks.
- CLI entrypoint for project inspection.

Do not put GUI callback logic here. Future desktop UI code should call service modules rather than owning workflow logic directly.

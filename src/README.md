# Source Directory

This directory contains the Phase 1 Python package for local project ingestion and geometry inspection.

Current implementation scope:

- Project manifest loading.
- KMZ/KML geometry ingestion.
- Geometry summaries and validation issues.
- CLI entrypoint for project inspection.

Do not put GUI callback logic here. Future desktop UI code should call service modules rather than owning workflow logic directly.

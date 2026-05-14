# Tests Directory

This directory contains tests for ingestion, inspection, source registry, project context/source status artifacts, source inventory/provenance artifacts, local spatial analysis services, deterministic finding generation, comparison table generation, vector-only map generation, review queue behavior, and populate-for-review orchestration.

Current focus:

- KMZ/KML parsing.
- Geometry summary generation.
- Validation and CLI error handling.
- Source catalog and project source registry handling.
- Local source registration.
- Report profile loading.
- Project context generation.
- Source status set resolution.
- Source inventory/provenance generation and source registry metadata validation.
- Synthetic local source-layer spatial checks.
- Finding template validation, deterministic draft finding generation, and finding-to-review-queue integration.
- Comparison table generation and table-to-review-queue integration.
- Vector-only map manifest/PNG generation and map-to-review-queue integration.
- Review queue generation, item status updates, reviewer notes, export eligibility, and CLI commands.
- Populate-for-review run manifests, tolerant missing-source handling, and CLI commands.

Future tests should add coverage for basemap/imagery rendering, report draft safety boundaries, and export compilation as those features are implemented.

## Test Discipline

Every implementation phase should add or update tests for the behavior introduced in that phase.

Use the local virtual environment:

```powershell
.\.venv\Scripts\python.exe -m pytest
```

Minimum expectations:

- Service changes get unit tests for normal behavior, validation, and error paths.
- CLI changes get command-level tests for output and nonzero failure cases.
- Geospatial changes use small synthetic fixtures where possible, plus smoke checks against real project workspaces when practical.
- Documentation-only changes do not require a test run, but the final task summary should say so.

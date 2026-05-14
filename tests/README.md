# Tests Directory

This directory contains tests for ingestion, inspection, source registry, project context/source status artifacts, and local spatial analysis services.

Current focus:

- KMZ/KML parsing.
- Geometry summary generation.
- Validation and CLI error handling.
- Source catalog and project source registry handling.
- Local source registration.
- Report profile loading.
- Project context generation.
- Source status set resolution.
- Synthetic local source-layer spatial checks.

Future tests should add coverage for source provenance, finding status transitions, review queue behavior, map generation, and report draft safety boundaries as those features are implemented.

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

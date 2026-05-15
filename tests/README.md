# Tests Directory

This directory contains tests for ingestion, inspection, source registry, project context/source status artifacts, source inventory/provenance artifacts, local spatial analysis services, deterministic finding generation, comparison table generation, vector-only map generation, deterministic report section generation, review queue behavior, Markdown export compilation, and populate-for-review orchestration.

Current focus:

- KMZ/KML parsing.
- Geometry summary generation.
- Project geometry normalization.
- Constraint overlap/proximity analysis.
- Smoke coverage for active sample project workspaces.
- Validation and CLI error handling.
- Source catalog and project source registry handling.
- Local source registration.
- Report profile loading.
- Project context generation.
- Source status set resolution.
- Source inventory/provenance generation and source registry metadata validation.
- Source acquisition failure propagation into source status, findings, and review queue caveats.
- Synthetic local source-layer spatial checks.
- Finding template validation, deterministic draft finding generation, and finding-to-review-queue integration.
- Comparison table generation and table-to-review-queue integration.
- Vector-only map manifest/PNG generation and map-to-review-queue integration.
- Report section template validation, deterministic draft report section generation, and section-to-review-queue integration.
- Review queue generation, item status updates, reviewer notes, export eligibility, and CLI commands.
- Markdown export filtering, manifest generation, edited-content precedence, preview mode, and export CLI commands.
- Populate-for-review run manifests, tolerant missing-source handling, and CLI commands.

Future tests should add coverage for basemap/imagery rendering, richer report draft safety boundaries, DOCX export, and final map package assembly as those features are implemented.

## Test Discipline

Every implementation phase should add or update tests for the behavior introduced in that phase.

Use the local virtual environment:

```powershell
.\.venv\Scripts\python.exe -m pytest
```

For full local readiness verification, including environment setup and CLI smoke checks, run:

```powershell
.\scripts\verify.ps1
```

Minimum expectations:

- Service changes get unit tests for normal behavior, validation, and error paths.
- CLI changes get command-level tests for output and nonzero failure cases.
- Geospatial changes use small synthetic fixtures where possible, plus smoke checks against real project workspaces when practical.
- Documentation-only changes do not require a test run, but the final task summary should say so.

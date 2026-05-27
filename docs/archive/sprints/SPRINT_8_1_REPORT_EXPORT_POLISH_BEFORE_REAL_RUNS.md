# Sprint 8.1 Report Export Polish Before Real Runs

## Classification

SAFE LAYER CHANGE.

## Summary

Sprint 8.1 cleaned reviewer-facing report/export presentation before broader real-project runs. The changes keep source truth, review gates, GPT behavior, figure rendering, export eligibility, and artifact schemas unchanged while making Markdown/DOCX output less like an implementation manifest.

## Implemented

- Removed the `Generated Package Contents` appendix from Markdown/DOCX report bodies. Package paths and internals remain available in export manifests.
- Removed raw table/figure IDs from report table and figure captions, removed `Map file:` / `Figure file:` body lines, and stopped printing raw source refs and raw uncertainty flag lines in normal report prose.
- Added clearer internal-preview status text showing that preview exports include unreviewed content and still require reviewer action before reviewed export.
- Prevented repeated inline rendering of shared support tables and figures. All wetlands/waterbodies comparison-unit child sections still render individually, but the shared wetlands table and figure embed once and later sections point back to the already-provided support.
- Reworded deterministic deliverable item prose to avoid evidence-manifest language such as `mapped-source evidence`, `evidence package`, `bounded rows`, `artifact limitations`, raw `source refs`, and `render decision`.
- Improved manual/status placeholder wording so reviewer-needed items explain the needed action without exposing raw policy enums in report-facing content.

## Verification

- `.\.venv\Scripts\python.exe -m pytest tests\test_export_report.py -q`
- `.\.venv\Scripts\python.exe -m pytest tests\test_deliverable_items.py tests\test_deliverable_compactness.py -q`
- `.\.venv\Scripts\python.exe -m pytest tests\test_web_app.py -q`
- `git diff --check`

## Artifact Freshness

Generated artifacts are affected when report/export artifacts or deliverable item prose are regenerated. No generated project artifacts were committed as part of this sprint.

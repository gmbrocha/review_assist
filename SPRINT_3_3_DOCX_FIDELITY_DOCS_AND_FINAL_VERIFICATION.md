# Sprint 3.3: DOCX Fidelity, Docs, And Final Verification

## Purpose

Improve the editable DOCX export to match the example report formatting target and finish documentation/test alignment for the non-UI redirected pipeline.

`CANONICAL_PLAN.md` is the canonical planning source for duplicated or conflicting workflow decisions.

## Outcome

By the end of Sprint 3.3:

- DOCX export follows the example report style targets materially better.
- Front matter, headings, captions, tables, figures, attachments, and footer behavior align with the canonical deliverable and style contract in `CANONICAL_PLAN.md`.
- Documentation reflects the new non-UI pipeline behavior.
- Full test suite and trails smoke workflow pass or any residual risks are documented.

## Dependencies

Sprint 3.1:

- deliverable items.
- bounded review queue.

Sprint 3.2:

- review-gated export.
- preview mode behavior.

Existing code:

- `export_report.py`
- python-docx dependency.
- map figure asset copying.

## Implementation Tasks

### 1. DOCX Page Setup

Match:

- Letter page, 8.5 x 11 inches.
- 1 inch top margin.
- 1 inch bottom margin.
- 1 inch left margin.
- 1 inch right margin.
- header distance 0.5 inch.
- footer distance 0.5 inch.
- usable content width about 6.5 inches.

### 2. Word Styles

Create or update styles:

- Body paragraph:
  - Calibri.
  - 12 pt.
  - 8 pt space after.
  - roughly 1.16 line spacing.
- Heading 1:
  - Lato.
  - 20 pt.
  - color `#0F4761`.
  - keep with next.
- Heading 2:
  - Lato.
  - 14 pt.
  - color `#0F4761`.
  - keep with next.
- Heading 3:
  - Lato.
  - italic.
  - color `#0F4761`.
  - keep with next.
- Heading 4:
  - italic.
  - color `#4C94D8`.
  - keep with next.
- Caption:
  - Calibri Light.
  - 11 pt.
  - italic.
  - centered.
  - color `#0E2841`.
- Attachment Title:
  - centered.
  - color `#0F4761`.

### 3. Title Page

Generate from project metadata:

- report/study title.
- project name.
- route/location descriptor when available.
- Appendix/report title.
- report date.
- project identifiers when available.
- county/state context from project area.
- internal/pre-review label only in preview mode.

Formatting:

- right-aligned title block.
- Calibri Light title.
- 20 pt main title.
- 16 pt subtitle, bold/italic where appropriate.

### 4. Front Matter Lists

Generate:

- List of figures.
- List of tables.
- List of attachments.

Rules:

- Use included/reviewed items in matrix order.
- Use generated matrix numbering.
- Do not copy inconsistent example numbering.
- Do not invent page numbers unless Word fields are implemented safely.

### 5. Headings And Section Order

- Use matrix section order.
- Use matrix section numbers.
- Use heading levels from matrix.
- Start major sections on new pages where appropriate.
- Keep section headings with following paragraph.
- Avoid duplicate leading headings inside generated content.
- Dynamic comparison-unit subsections use Heading 4 where appropriate.

### 6. Tables

- Render accepted/included deliverable tables only.
- Use `Table Grid`.
- Apply header row emphasis.
- Add caption before or after table consistently with example styling.
- Keep tables within page width.
- Wrap text in cells.
- Avoid rendering raw comparison/evidence tables in standard report.
- Render accepted stub table as stub text, not empty table.

### 7. Figures

- Copy included figure assets to export assets folder.
- Embed PNG figures at 6.5 inch width.
- Add figure caption with caption style.
- Add source note and method note below figure where available.
- Render accepted figure stubs as stub text/placeholders.
- Do not embed missing images without clear placeholder text.

### 8. Attachments

- Render Attachment A/B/C in order.
- Attachment A should reference accepted project maps/panel maps.
- Attachment B should reference hazardous materials support if supplied/reviewed; otherwise stub.
- Attachment C should reference agency consultation letters if supplied/reviewed; otherwise stub.
- Do not invent consultation outcomes.

### 9. Footer

Footer should include:

- project name.
- report title.
- page number field where practical.
- preview/internal label when preview mode.

Do not spend excessive time on fragile Word field mechanics if it threatens the sprint; include a documented fallback.

### 10. Markdown Parity

- Keep Markdown export structurally consistent with DOCX.
- Markdown should use matrix order.
- Markdown should include front matter lists.
- Markdown should omit declined items.
- Markdown should show preview labels in preview mode.

### 11. Documentation Updates

Update affected docs:

- `CANONICAL_PLAN.md`
- `docs/domains/WORKFLOW_MODEL.md`
- `docs/core/CURRENT_STATE.md`
- `docs/core/ARCHITECTURE.md`
- `docs/sprints/ROADMAP.md`
- `docs/domains/REPORT_ASSEMBLY.md`
- `docs/domains/REVIEW_POLICY.md`
- `docs/domains/MAP_GENERATION.md`
- `docs/domains/DATA_SOURCES.md`
- `docs/domains/LLM_ASSISTED_SYNTHESIS.md`

Docs must state:

- no UI/webapp implemented.
- `CANONICAL_PLAN.md` controlled duplicated near-term decisions for this phase.
- matrix-driven deliverable items bound review volume.
- default export requires terminal review statuses.
- draft preview is internal/pre-review only.
- missing required targets become exact stubs.
- raw evidence remains available but is not standard report volume.
- MrSID imagery requires renderable sidecars for basemap rendering.

### 12. Smoke Workflow

Run on trails workspace:

```powershell
.\.venv\Scripts\review-assist.exe populate-for-review projects/trails --materialize-local-sources --prepare-sources --include-optional-sources --no-gpt-drafting
```

Then verify:

- deliverable matrix loaded.
- input package exists.
- project area exists.
- comparison units exist.
- deliverable tables exist.
- deliverable figures exist.
- evidence package exists.
- deliverable items exist.
- review queue exists.
- default export fails before review completion.

Then mark all review items accepted using existing CLI or a test helper path and verify:

- Markdown export succeeds.
- DOCX export succeeds.
- manifest records review gate complete.
- expected table/figure/attachment lists are present.

### 13. Full Test Run

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest
```

If tests cannot run:

- record exact reason.
- record residual risk.
- do not claim verification passed.

## Tests

Add or update tests for:

- DOCX file creation.
- page setup where python-docx exposes values.
- expected styles exist.
- title page content exists.
- front matter lists exist.
- accepted tables render inline.
- accepted figures render inline.
- accepted stubs render exact stub text.
- declined items are absent.
- preview label exists in preview DOCX.
- Markdown and DOCX include the same deliverable item set.
- export manifest includes expected gate and deliverable counts.

Suggested command:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_export_report.py
```

Then run full suite.

## Acceptance Checklist

- DOCX formatting is materially aligned with the canonical deliverable and style contract in `CANONICAL_PLAN.md`.
- Front matter lists are generated from included deliverable items.
- Tables and figures render inline in matrix order.
- Attachments render in order.
- Preview labels are visible only in preview mode.
- Docs are aligned with implemented behavior.
- Trails smoke workflow is run.
- Full tests pass or residual risk is documented.

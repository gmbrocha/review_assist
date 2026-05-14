# Decision Log

This document records product and architecture decisions as the project evolves.

## Decisions

### 2026-05-14: The tool will not select or recommend a preferred alternative

The tool supports human review and should not choose a preferred alternative.

### 2026-05-14: The tool will avoid hard scoring

Alternatives should be described through impact profiles and source-backed findings rather than hard scores.

### 2026-05-14: Findings should distinguish source-backed GIS facts from imagery-observed review items

Deterministic source checks and imagery observations have different certainty levels and should be represented differently.

### 2026-05-14: Generated reports are pre-review drafts only

Generated report packages are drafts for human review and should not be labeled final.

### 2026-05-14: The product direction is no blank page

The system should eventually attempt to generate a comprehensive first-pass package, including findings, draft narrative, maps, tables, implications, and appendices/reference material where useful.

### 2026-05-14: Public authoritative GIS is a reliable baseline but still screening-level

Government, educational, and authoritative public infrastructure GIS sources can support baseline desktop screening, but findings must preserve provenance, source dates, uncertainty, and field-verification caveats.

### 2026-05-14: Buffer assumptions must remain configurable

Early trail context suggests review corridors in the 50 to 100 foot range, but v1 architecture should treat corridor and buffer widths as configurable project assumptions.

### 2026-05-14: MDAH restricted cultural resource integration is deferred

The system may document future integration points and reviewer-supplied workflows, but it should not implement restricted MDAH access or authentication until explicitly approved.

### 2026-05-14: LLM synthesis is allowed only as reviewable draft synthesis

Future GPT/LLM calls may assist with narrative, summaries, implications, uncertainty phrasing, and sanity checks, but deterministic GIS/source analysis must remain separate and source-backed.

### 2026-05-14: The desktop app review queue is the spine

The first GUI version should treat the review queue as the core domain model. Generated findings, section drafts, maps, tables, provenance notes, assumptions, and caveats must become reviewable items before export.

### 2026-05-14: The desktop GUI must stay thin over services

The PyInstaller desktop app should use a modular service architecture underneath the GUI so pipeline, GIS, findings, review, and export logic does not become trapped in callbacks.

## Future Decision Template

### YYYY-MM-DD: Decision title

Context:

Decision:

Consequences:

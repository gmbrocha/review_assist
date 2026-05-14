# Workflow Model

This document is the canonical workflow truth model for the Alternatives Review Assistant.

The application is a local, workspace-oriented, human-supervised workflow accelerator. It is a source-aware report compiler and contextual review assistant. It is not a recommendation engine, black-box AI reviewer, autonomous environmental analyst, or final decision-maker.

## Canonical Workflow

### 1. Open or Create Workspace

The user opens the desktop app and creates or opens a workspace/project.

The workspace is the persistent container for:

- Project metadata.
- Project-specific context.
- Input files.
- Source status tracking.
- Downloaded or locally provided datasets.
- Generated intermediates.
- Generated review items.
- Reviewer edits and decisions.
- Accepted outputs.
- Export artifacts.

The workspace should be designed for a low-friction local desktop workflow and eventual PyInstaller packaging.

### 2. User Adds Project Inputs

The user drops project material into the workspace.

Examples:

- KMZ/KML alternatives.
- GIS layers, shapefiles, GeoPackages, or GeoJSON.
- Prior reports.
- Imagery.
- Context notes.
- PDFs.
- Maps.
- Study documents.

The app should attempt to:

- Parse project geometry.
- Determine bounding box and project extent.
- Detect alternatives or project locations.
- Identify provided local resources.
- Surface validation issues and missing context.

Current examples:

- `projects/trails` contains line-based trail-alternative KMZ geometry.
- `projects/conexon_projects` contains broad point-based broadband location KMZ geometry.
- `env_constraints_report_20260511_EXAMPLE_ONLY.docx` is a structural reference for report deliverables, not authoritative project data.

### 3. Project Context Generation

The system generates and maintains project-specific context as a persistent project artifact.

Examples:

- Project name.
- Study area.
- Project extent.
- Assumptions and buffer/corridor defaults.
- Detected alternatives.
- Likely report profile.
- Provided source categories.
- Known missing source categories.
- User instructions.
- Special reviewer notes.

This context should be editable because automated detection will not always infer intent correctly.

### 4. Needed Data Set Resolution

The system determines which source categories are needed for the selected report profile.

Examples:

- Wetlands.
- Hydrography.
- Flood zones.
- Listed species.
- Cultural resources.
- Utilities.
- Demographics.
- Hazardous materials.
- Imagery/basemaps.

The system compares required categories against:

- Locally provided data.
- Downloadable public data.
- Gated or restricted data.
- Stubbed/manual data.
- Missing or optional data.

The result is a `SOURCE_STATUS_SET`.

## Source Status Set

Source status tracking is first-class workflow state. Missing data should not stop the workflow by default.

Suggested statuses:

- `provided_locally`: user supplied a local source file or document.
- `downloadable`: public data appears available but is not downloaded yet.
- `downloaded`: public data has been acquired for the workspace.
- `gated`: access requires credentials, qualified access, agency request, or restricted handling.
- `stubbed`: a placeholder exists so reports can include a review requirement or caveat.
- `missing`: expected source material is not available.
- `optional`: useful context but not required for the selected report profile.
- `needs_review`: source status or fitness for use needs reviewer confirmation.

Missing, gated, and stubbed datasets should generate placeholders, uncertainty flags, and review requirements rather than causing the workflow to fail. The goal is useful pre-review report generation, not perfect data completeness.

## Populate for Review

The user action is conceptually:

```text
Populate for Review
```

This stage may:

- Download or acquire approved public datasets where possible.
- Load locally provided source layers.
- Crop or clip data to the project extent.
- Prepare imagery/basemaps.
- Run deterministic spatial analysis.
- Generate findings.
- Generate tables.
- Generate figures/maps.
- Generate draft narrative sections.
- Generate caveats and uncertainty notes.
- Generate source/provenance notes.

Deterministic GIS analysis must remain separate from AI narrative synthesis.

GPT/LLM calls are acceptable here for draft narrative generation, summarization, implication drafting, and review-oriented synthesis, but AI output must remain editable, traceable, and reviewable. AI must not make final recommendations.

## Review Queue

The review queue is the core workflow object.

Every generated artifact becomes a reviewable item. Nothing should skip the review queue.

Reviewable item examples:

- Finding.
- Report paragraph.
- Comparison table.
- Figure/map.
- Caveat.
- Source note.
- Implication note.
- Missing-data placeholder.
- Reviewer-created note.

Conceptual review item fields:

- `id`
- `type`
- `title`
- `generated_content`
- `edited_content`
- `assumptions`
- `provenance`
- `source_refs`
- `status`
- `reviewer_notes`
- `export_eligible`
- `export_section`

Suggested statuses:

- `draft`
- `needs_review`
- `accepted`
- `edited`
- `rejected`
- `needs_verification`
- `unable_to_verify`

Reviewer actions:

- Edit.
- Accept.
- Reject.
- Request rewrite.
- Mark for verification.
- Mark unable to verify.
- Add notes.

The review queue is the human-in-the-loop control boundary. It is not a side panel or optional feature.

## Export Compilation

Accepted and reviewer-approved items are queued for export.

The export stage compiles:

- Accepted report sections.
- Accepted findings.
- Accepted maps/figures.
- Accepted tables.
- Appendices.
- Source/provenance references.
- Assumptions and caveats.

Target exports may eventually include:

- DOCX.
- PDF.
- Appendix packages.
- Map packages.

The system should compile accepted content only. Rejected items remain in the review record but do not export. Items needing verification or unable to verify may export only if the reviewer explicitly includes them with caveat language.

## Conceptual Service Boundaries

The desktop GUI should remain thin over services.

Conceptual modules:

- Workspace/project service.
- Ingestion service.
- Geometry normalization service.
- Project context service.
- Source acquisition service.
- Source status tracking service.
- Spatial analysis service.
- Imagery/basemap service.
- Findings generation service.
- Review queue service.
- Report drafting service.
- Export/compilation service.

The current CLI services are early building blocks. `generate-context` and `resolve-sources` now produce the first workflow-native JSON artifacts. They should evolve toward this workflow rather than becoming the final product shape.

## Non-Negotiable Boundaries

- Do not select or recommend a preferred alternative.
- Do not implement autonomous ranking/scoring.
- Do not treat desktop review as field verification.
- Do not let AI create unsupported facts.
- Do not export unreviewed generated content as final.
- Do not automate restricted access workflows without explicit approval.

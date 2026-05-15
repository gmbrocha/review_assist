# First Version Plan

This document captures the first-version direction for the desktop GUI application.

The first version should remain focused: a local desktop app that creates/opens a workspace, accepts a project input package, resolves needed source status, generates a draft review queue, lets a human reviewer accept/edit/reject items, and compiles accepted content into an export package.

## Product Shape

The app is a local GUI desktop application packaged with PyInstaller.

Target feel:

- Sleek.
- Dark mode by default.
- Minimalist.
- Informative.
- Lightweight.
- Enterprise, but visually current and "cool."

The GUI is not decoration over a script. It is the human review surface for a structured workflow.

## Core Rule

The review queue is the spine.

Everything feeds the review queue. Nothing skips it.

Every generated artifact must become a reviewable item before export:

- Findings.
- Draft narrative sections.
- Table previews.
- Map/visual previews.
- Source/provenance notes.
- Assumptions and caveats.
- Generated implications.

Each reviewable item needs:

- Status.
- Provenance.
- Assumptions.
- Editable content.
- Reviewer notes.
- Export eligibility.

## First-Version Workflow

```text
input package
  -> project context + source status set
  -> populate for review
  -> generate draft review queue
  -> human accepts / edits / rejects / marks needs verification
  -> compile accepted content into export package
```

The system should generate as much useful first-pass material as possible, but no generated content becomes final without reviewer action.

## Core Modules

### Project Setup

Purpose:

- Create or open a project.
- Capture project metadata and assumptions.
- Attach input packages.

First-version fields:

- Project name.
- Project location or study area description.
- KMZ/KML alternatives.
- Resource/layer folder.
- Assumptions/config.
- Special reviewer instructions.
- Source status summary.

Likely future project folder structure:

```text
projects/<project_id>/
  inputs/
  layers/
  config/
  intermediate/
  review_queue/
  maps/
  tables/
  drafts/
  exports/
```

The current initial example project should be `trails`. The app itself should remain general-purpose and able to create and manage other projects.

### Pipeline

Purpose:

- Convert project inputs into draft review items.
- Keep deterministic processing separate from GUI callbacks and LLM drafting.

Pipeline responsibilities:

- Parse geometry.
- Normalize project and alternative geometries.
- Crop/query source layers.
- Generate maps.
- Generate tables.
- Generate source-backed findings.
- Generate contextual implications.
- Optionally use GPT for draft narrative.

Pipeline outputs should be structured artifacts, not direct final-report content.

Every pipeline output should be converted into one or more review queue items.

The user-facing generation action should be `Populate for Review`.

### Source Status Resolution

Purpose:

- Determine the source categories needed for the selected report profile.
- Compare needed categories against provided local data, downloadable public data, downloaded data, gated/restricted data, stubs, missing data, optional categories, and items needing review.
- Create placeholders and caveat items for missing or gated data instead of failing the workflow.

### Review Queue

Purpose:

- Serve as the core domain model and primary reviewer workspace.
- Hold all generated and reviewer-created items before export.

Review queue item types:

- Finding cards.
- Draft section cards.
- Table preview cards.
- Map/visual preview cards.
- Source/provenance cards.
- Assumption/caveat cards.
- Reviewer-created note cards.

Review actions:

- Edit.
- Rewrite.
- Accept.
- Reject.
- Mark needs verification.
- Mark unable to verify.
- Add reviewer note.
- Link or unlink from export section.

Review statuses:

- `draft`
- `needs_review`
- `accepted`
- `rejected`
- `edited`
- `needs_verification`
- `unable_to_verify`

Export rule:

- Only accepted or reviewer-approved edited content should be eligible for final export.
- Rejected items should remain in the review record but should not export.
- Needs-verification or unable-to-verify items may export only if the reviewer explicitly marks them as included with caveat language.

### Export

Purpose:

- Compile reviewer-approved content into an editable deliverable package.

Expected first-version export targets:

- Word document.
- Figures/maps.
- Tables.
- Provenance/source log.
- Assumptions/caveats appendix.

Export should include accepted content only, plus explicitly included caveats or unresolved items.

Generated reports should remain editable and should not be labeled final by the system.

## Review Queue Domain Model

The review queue should be modeled as structured data, not just UI state.

Conceptual fields:

- `item_id`
- `project_id`
- `item_type`
- `resource_category`
- `alternative_id`
- `title`
- `summary`
- `editable_content`
- `source_ids`
- `method_ids`
- `assumptions`
- `uncertainty_flags`
- `provenance`
- `review_status`
- `reviewer_notes`
- `export_section`
- `export_eligible`
- `created_by`
- `created_at`
- `updated_at`

The exact schema is not implemented yet, but future code should treat this as a core model.

## GUI Direction

The GUI should make the review queue central.

Likely layout:

- Left rail: project navigation and pipeline stages.
- Main center: review queue cards or selected review item.
- Right panel: provenance, assumptions, source details, reviewer notes, and export eligibility.
- Top bar: project name, pipeline status, export readiness.
- Bottom/status area: warnings, missing data, validation messages.

Primary screens:

- Project dashboard.
- Project setup/input configuration.
- Pipeline run/progress.
- Review queue.
- Map/table preview.
- Export builder.
- Settings/assumptions.

The visual style should be restrained and functional:

- Dark neutral background.
- Clear accent color for active review state.
- Compact cards.
- Strong typography hierarchy.
- Status chips.
- Minimal but readable icons.
- No decorative clutter.

## Modularity Rule

Keep the desktop shell thin.

Do not trap business logic inside buttons, widgets, and callbacks.

Preferred layering:

```text
desktop GUI
  -> application services
    -> pipeline services
      -> ingestion / geometry / source / analysis / findings / maps / report assembly
  -> review queue domain model
  -> project storage
```

The GUI should call services and render state. It should not own the workflow logic.

## Likely Service Boundaries

### Project Service

- Creates projects.
- Loads/saves project manifests.
- Stores project paths, metadata, and assumptions.

### Ingestion Service

- Reads KMZ/KML and future geospatial inputs.
- Extracts alternatives, footprints, and layer metadata.

### Geometry Service

- Normalizes CRS.
- Validates geometries.
- Builds configurable buffers/corridors.

### Source/Layer Service

- Loads local resource/layer folders.
- Tracks source metadata and provenance.
- Later may support approved source acquisition.

### Spatial Analysis Service

- Runs deterministic intersections, crossings, buffers, overlaps, lengths, and areas.
- Emits spatial relationship records.

### Findings Service

- Converts spatial relationships into structured findings and implication candidates.
- Preserves source, method, assumptions, and uncertainty.

### Map/Table Service

- Generates static maps, visual previews, and comparison tables.
- Sends previews into the review queue.

### Narrative Service

- Optionally uses GPT to draft narrative from structured findings.
- Keeps AI output editable and traceable.

### Review Queue Service

- Creates and updates review items.
- Manages statuses, edits, notes, and export eligibility.
- Acts as the central workflow state.

### Export Service

- Compiles accepted review queue items into Word/report outputs.
- Exports figures/maps, tables, source log, and assumptions/caveats appendix.

## First Example Project

The first implementation target should use the trails project as the working example.

First practical goal:

- Ingest the trail alternatives KMZ.
- Let the reviewer see the alternatives.
- Generate initial review queue items from available geometry and any supplied layers.
- Create simple map/table/finding previews.
- Let a human accept/edit/reject.
- Compile accepted content into a draft export.

The app should still remain general-purpose and not hardcoded to trails.

## Design Constraints

Do not implement:

- Recommendation logic.
- Automatic preferred alternative selection.
- Autonomous ranking/scoring.
- Final determinations.
- Unreviewed export content.
- MDAH restricted integration.
- Paid services or credentials without approval.
- Black-box report generation.

Do implement future work around:

- Reviewable artifacts.
- Human-in-the-loop workflow.
- Source-backed findings.
- Traceable assumptions.
- Editable draft content.
- Accepted-content-only export.

## Open Questions Before Implementation

- Which GUI toolkit should be used for the first desktop shell?
- What project manifest format should store project setup and assumptions?
- Should review queue items be stored as JSON, SQLite, or another local format?
- Which GeoPandas/GDAL installation path is preferred for Windows packaging?
- Should PyInstaller package all GIS dependencies locally, or should development use a managed environment first?
- What should be the first minimal export: DOCX only, folder package, or DOCX plus figures/tables?
- What status rules should allow caveated unresolved items into export?
- Which default dark-mode design tokens should be used?
- How should large source layers and generated maps be stored outside Git?

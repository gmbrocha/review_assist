# Sprint 6.3: Reviewer Figure Editor UI

## Status

Parked draft for review. Do not implement until Sprint 6.2 model records exist or the integration approach is accepted.

## Purpose

Create a lightweight browser-based figure styling/editor panel for generated figures.

This is a constrained reviewer styling workflow, not a browser GIS editor.

## Minimum UI

The reviewer can open a generated figure and see:

- current figure preview
- loading state
- regeneration state
- updated preview after style changes are saved/regenerated
- layer list
- selected layer controls
- figure action buttons
- version/approval summary if available

Live preview is optional for v1.

## Layer List

Expose layers used in the selected figure.

Per-layer controls:

- visibility toggle
- layer ordering
- active layer selection
- display name

Optional later support:

- layer grouping
- source grouping
- comparison-unit grouping

## Layer Styling Controls

Initial v1 controls:

- fill color
- fill opacity
- stroke color
- stroke width
- point size, where applicable
- label visibility
- optional label field selection

Controls should be intentionally limited. Do not implement advanced GIS/cartography tools.

## Figure Actions

Required actions:

- Reset to Default
- Save Draft Style
- Save and Regenerate Figure
- Approve Figure

Action behavior:

- Reset to Default clears reviewer style overrides for the figure.
- Save Draft Style persists sparse override metadata only.
- Save and Regenerate Figure persists overrides, creates a render job, and creates a new version on success.
- Approve Figure approves one exact figure version.

## Integration Placement

Prefer extending the existing figure review detail flow rather than creating a broad new app surface.

Possible UI shapes:

- figure detail page with an editor panel below the existing preview
- separate route such as `/review/<item_id>/figure-style`
- tabbed figure review detail if the existing template pattern supports it cleanly

Keep the web layer thin. Route handlers should call adapter/service functions and should not parse raw GIS files or mutate render internals directly.

## Safety Requirements

The UI must not expose:

- geometry editing
- source record editing
- source file editing
- analysis metrics editing
- report determination controls disguised as style controls

The UI should clearly act on presentation metadata.

## Tests

Add or update tests for:

- figure editor route/page renders for figure review items
- non-figure review items do not expose figure editor controls
- layer list is derived from figure recipe/shown layers
- style form contains only allowed v1 controls
- reset, save draft, regenerate, and approve actions are wired to service/adapter functions
- invalid item IDs and non-figure item IDs are rejected

## Definition Of Done

- Reviewers can open a figure styling UI from a generated figure review item.
- The page shows preview, layers, constrained controls, and required actions.
- UI actions call service/adapter functions rather than mutating artifacts inline.
- No source/geometry/analysis editing controls are present.

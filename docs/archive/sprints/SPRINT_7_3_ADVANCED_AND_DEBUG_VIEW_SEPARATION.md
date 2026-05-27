# Sprint 7.3: Advanced And Debug View Separation

## Status

Parked draft for review. Do not implement until Sprint 7.1 and 7.2 are accepted.

## Purpose

Create a clean, persistent separation between the normal reviewer workflow surface and the debug/audit detail surface.

This subunit builds on the hiding work from 7.1 by providing a deliberate access path to internal details rather than simply removing them.

## Default Reviewer View

The default view should show only what a reviewer needs to make a decision:

- Proposed content (text, figure preview, table)
- Source summary (what backed this, how confident)
- Table or figure availability status
- Reviewer action controls
- Missing material guidance and next-step prompt
- Export readiness indicator

The default view must not require the reviewer to understand the internal warehouse, source registry, or artifact graph.

## Advanced View

The advanced view is an opt-in surface for power users, auditors, and developers. It may show:

- Source IDs and source registry keys
- Artifact paths and generated file paths
- Validation issue codes
- Source status internals
- GPT provenance and prompt version
- Hashes and cache details
- Raw evidence metadata
- Full generated artifact paths

## Access Pattern

Preferred access patterns for the advanced view:

- A clearly labeled "Advanced / Debug" toggle or disclosure on the review detail page
- An optional query parameter such as `?debug=1` or `?advanced=1` for direct linking
- A persistent session preference if the reviewer or developer needs it across items

The advanced view toggle must not change any canonical state. It is display-only.

## Safety Requirements

The advanced view must not expose:

- Controls that mutate source truth
- Controls that bypass review gating
- Controls that look like review actions but operate on internal artifacts

Advanced view content is read-only display of internal detail, not an editing surface.

## Scope

This subunit covers display routing and template structure only. It does not change:

- Source truth
- Canonical artifact schemas
- Review queue semantics
- Generated artifact content

## Tests

Add or update tests for:

- Default review detail page does not contain source IDs, artifact paths, or hash values
- Advanced view route or toggle reveals source IDs, artifact paths, and evidence metadata
- Advanced view toggle does not alter any canonical review state
- Advanced view is accessible from every review item detail page
- Session or query-parameter-based advanced mode persists across page loads without mutating review state

## Definition Of Done

- Default reviewer view shows only decision-relevant content.
- Advanced view is accessible from every review item and exposes full internal detail.
- The separation is implemented without removing any underlying data.
- No source truth, canonical artifact schemas, or review state is changed by toggling the view.

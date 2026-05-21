# Sprint 7.2: Review Status And Badge Cleanup

## Status

Parked draft for review. Do not implement until Sprint 7.1 is accepted.

## Purpose

Clarify confusing review item statuses so a reviewer immediately understands what action they need to take.

## Problem

Current statuses such as `draft`, `needs_review`, and `needs_verification` are not expressive enough to distinguish workflow state from content readiness state. A reviewer cannot tell at a glance whether an item is waiting for their action, waiting for a source, or waiting for a method determination.

## Desired Direction

Separate workflow state from content/readiness state. Each review item should surface both dimensions clearly.

### Workflow/Review Status

Indicates what the reviewer has done with this item:

| Status | Meaning |
|---|---|
| Needs review | Awaiting reviewer action |
| Accepted | Reviewer accepted as-is |
| Edited | Reviewer made edits to content |
| Replaced | Reviewer supplied replacement material |
| Declined | Reviewer declined or excluded this item |
| Unable to verify | Reviewer marked as unverifiable |

### Candidate/Readiness Status

Indicates the state of the underlying generated content:

| Status | Meaning |
|---|---|
| Source-backed generated | Content produced from verified source data |
| Draft placeholder | Content placeholder, no source available |
| Missing source | Required source could not be acquired |
| Rendering deferred | Figure or table render is pending |
| Manual required | Reviewer must supply this content |
| Needs method verification | Source or method requires expert confirmation |

## UI Goal

The UI should make it obvious what the reviewer needs to do next. Each review item badge or status line should communicate:

1. What this item is (readiness)
2. What still needs to happen (workflow action)

Avoid combining the two into a single ambiguous status field.

## Scope

This subunit covers status labeling, badge display, and UI semantics only. It does not change:

- Review queue data schemas unless a minimal schema field addition is needed to support the split
- Source truth
- Canonical generated artifact content

If a schema addition is required to store the split status, document it clearly and keep it additive only.

## Tests

Add or update tests for:

- Review item list renders workflow status and readiness status as distinct UI elements
- Each defined workflow status maps to a distinct badge or label
- Each defined readiness status maps to a distinct badge or label
- No single-field status conflates workflow state and content state
- Status badges for a fully accepted item differ visibly from a needs-review item

## Definition Of Done

- Workflow status and readiness status are visually distinct in the default reviewer view.
- All defined workflow and readiness statuses map to clear, reviewer-facing UI labels.
- A reviewer can scan the review queue and immediately identify what action is needed for each item.
- No source truth or generated artifact content is changed.

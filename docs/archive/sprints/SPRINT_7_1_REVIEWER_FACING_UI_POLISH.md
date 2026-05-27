# Sprint 7.1: Reviewer-Facing UI Polish

## Status

Completed and archived after implementation.

## Purpose

Remove or hide developer-facing noise from the default UI so a real reviewer can use the app without encountering internal machinery.

The reviewer should not have to see internal diagnostics unless they intentionally open an advanced or debug view.

## What To Hide Or Move

The following should be hidden, collapsed, or moved to an advanced view by default:

- Raw source IDs
- Artifact paths and generated file paths
- Hashes and fingerprints
- Cache keys
- Prompt versions
- Low-level validation codes
- Raw provenance blobs
- Stale or debug run details
- Internal statuses such as `local materialized` or `logical rollup satisfied`

The underlying truth must remain accessible, but not as the default surface.

## Desired Default UI Language

Prefer reviewer-facing labels over internal status codes. Examples:

| Internal | Reviewer-facing |
|---|---|
| `local materialized` | Ready for review |
| `logical rollup satisfied` | Source-backed draft |
| `manual_required` | Manual material needed |
| `source_unavailable` | Source unavailable |
| `reviewer_supplied_required` | Reviewer-supplied material required |
| `figure_generated` | Figure generated |
| `table_generated` | Table generated |
| `export_blocked` | Export blocked by review items |
| `unable_to_verify` | Unable to verify |

## Scope

This subunit covers UI language and display filtering only. It does not change:

- Source truth
- Canonical artifact schemas
- Review queue semantics
- Any generated artifact content

## Tests

Add or update tests for:

- Default review item list does not expose raw source IDs, artifact paths, or hash values
- Reviewer-facing label strings are present in rendered templates for each mapped internal status
- Hidden fields are not present in the default view HTML
- Advanced view route or toggle exposes the previously hidden fields

## Definition Of Done

- Default reviewer view shows clean, reviewer-facing labels for all review item statuses.
- Internal artifact paths, hashes, source IDs, cache keys, and low-level codes are not shown in the default view.
- The underlying detail is accessible via advanced view or explicit toggle, not removed.
- No source truth, canonical artifact schemas, or generated artifact content is changed.

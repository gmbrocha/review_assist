# Sprint 5.2: Extent Semantics And Wording Enforcement

## Status

Parked for implementation after Sprint 5.1 policy reconciliation is accepted.

## Goal

Tighten existing extent metadata and wording enforcement so Review Assist does not turn map extent, context extent, watershed extent, or county/regional context into direct project impact language.

The current app already has `src/review_assist/extent_policy.py` and extent-policy metadata on tables, figures, evidence, deliverable items, review queue items, and GPT payloads. This subunit should refine and test that layer, not create a new spatial-query system.

## Scope

This subunit may update:

- `src/review_assist/extent_policy.py`
- deterministic section wording helpers
- evidence/deliverable/review queue extent metadata propagation
- GPT output validation for extent language
- policy/docs/tests that explain extent semantics

## Required Semantics

- `within`: direct intersection with named analysis extent, or a named buffer stated in the sentence.
- `near`: outside direct extent but within configured screening/context extent.
- `adjacent`: touches or is explicitly tagged adjoining; not generic nearby.
- `downstream`: hydrologic network or reviewer-confirmed relationship.
- `watershed/subwatershed`: contextual hydrologic geography, not direct footprint.
- `county/regional`: context only, not project impact.
- `APE`: reviewer-defined cultural extent only.
- `corridor`: use only when project geometry supports corridor/route language.
- `shown on map`: presentation support only.

## Non-Goals

- No new buffers or query extents.
- No watershed implementation.
- No source acquisition.
- No figure cartographic redesign.
- No trail/corridor default behavior.

## Acceptance Criteria

- Analysis/query extent and visual/render extent remain distinguishable in generated artifacts.
- Render extent and legend/collar extent are always presentation-only.
- Watershed and county/regional sections do not use direct-project wording.
- Context-only evidence cannot be drafted or exported as direct impact language.
- Documentation says current named context extents may be policy labels until separately implemented as source queries.

## Required Tests

- Existing extent tests in `tests/test_deliverable_matrix.py`, `tests/test_deliverable_items.py`, `tests/test_deliverable_figures.py`, `tests/test_deliverable_tables.py`, `tests/test_review_queue.py`, and `tests/test_evidence_and_gpt.py`.
- Add or update tests preventing:
  - watershed context described as direct intersection
  - visual map extent described as analysis extent
  - county/regional context described as project-area impact
  - APE inferred from generic buffer
  - context-only GPT output using direct-impact language

## Documentation Updates

- `docs/domains/REPORT_POLICY.md`
- `docs/domains/REPORT_ASSEMBLY.md`
- `docs/governance/DEFERRED_WORK.md` if query implementation remains deferred

# Sprint 5.3: Source Needs And Effective Truth Mapping

## Status

Parked for implementation after Sprint 5.1 policy reconciliation and Sprint 5.2 extent semantics are accepted.

## Goal

Reconcile report policy with the source catalog, report profiles, source warehouse, and source status resolver so source needs are explainable and report-facing caveats reflect effective current truth.

This subunit should stop broad source names, logical rollups, manual buckets, and physical warehouse source IDs from drifting through the pipeline interchangeably.

## Scope

This subunit may update:

- `config/report_profiles.json`
- `config/source_catalog.json`
- `config/local_source_materializers.json`
- source status/effective truth logic
- source inventory/source warehouse docs
- focused source status/materialization tests

## Source Status Categories

Each needed source should resolve to one of:

- available/materialized
- warehouse available but not materialized
- acquisition candidate
- optional
- manual/reviewer-supplied
- restricted/authorized reviewer-supplied
- public/coarse screening context
- deferred
- deprecated/legacy

## Required Distinctions

- `usgs_nhd_hydrography` remains a logical live-download rollup, not a required physical warehouse source when specific NHD layers satisfy the category.
- `epa_envirofacts_echo` remains a logical/acquisition concept, not a blocker when specific regulated facility layers satisfy the category.
- `mdeq_environmental_context` must not become a magic junk drawer.
- Public/coarse cultural context and restricted MDAH/SHPO records stay separate.
- Google Earth or imagery-observed context is reviewer context, not an authoritative missing source.
- Manual/reviewer-supplied attachments such as agency letters and hazardous materials reports are not failed downloads.

## Non-Goals

- No new live source acquisition by default.
- No new source classes unless needed to prevent misleading current behavior.
- No PEL/trail/corridor assumptions.
- No treating public cultural data as a substitute for restricted records.

## Acceptance Criteria

- Report/GPT-facing source caveats use effective current status, not stale acquisition history.
- Logical rollups do not appear as missing physical layers in report-facing output when specific child layers satisfy the category.
- Restricted/manual/public-coarse source distinctions are visible to the reviewer.
- Source needs can be traced from section policy to source catalog/profile status.
- Missing/deferred/manual sources remain honest review states, not hidden failures.

## Required Tests

- Source status tests for logical rollup satisfaction.
- Source materialization tests for warehouse-present versus materialized states.
- Cultural source split tests: public/coarse context is not restricted/authorized review.
- Manual attachment tests: agency letters and hazardous materials reports do not appear as download failures.
- Effective status caveat tests for stale failed acquisition plus current local/materialized source.

## Documentation Updates

- `docs/domains/DATA_SOURCES.md`
- `docs/domains/SOURCE_WAREHOUSE.md`
- `docs/domains/UNCERTAINTY_AND_PROVENANCE.md`
- `docs/governance/DEFERRED_WORK.md` for deferred source acquisition

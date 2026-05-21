# Sprint 5.3: Source Needs Manifest And Warehouse Alignment

## Status

Parked draft for review. Do not implement until Sprint 5.2 section policy is accepted.

## Goal

Reconcile report policy with the source warehouse so source needs are explainable and stable.

This subunit should stop random source names from floating through the pipeline.

## Outputs

- Source needs manifest by report section.
- Mapping from logical rollups to physical sources.
- Clear status for every needed source.
- Tests that stop old broad source IDs from becoming missing physical-source caveats.

## Source Status Categories

Each needed source should resolve to one of:

- Available/materialized.
- Warehouse available but not wired.
- Acquisition candidate.
- Optional.
- Manual/reviewer-supplied.
- Restricted/authorized reviewer supplied.
- Public/coarse POC context.
- Deferred.
- Deprecated/legacy.

## Important Decisions

- `usgs_nhd_hydrography` is a logical rollup, not a physical source.
- `epa_envirofacts_echo` is a logical/acquisition concept, not a blocker if specific EPA/MARIS sources exist.
- `mdeq_environmental_context` should not be a magic junk drawer.
- Public cultural context and restricted MDAH records stay separate.
- Google Earth visual context is not an authoritative missing source.

## Definition Of Done

- Report/GPT-facing source caveats reflect effective current source truth.
- Acquisition history remains diagnostic unless it is still relevant.
- The source warehouse is explainable from app-facing source IDs to raw agency/source folders.
- Logical rollups do not appear as missing physical layers in report-facing outputs.

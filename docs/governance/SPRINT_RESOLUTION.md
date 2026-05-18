# Sprint Resolution And Knowledge Migration

Sprint subunits are temporary implementation workspaces. After implementation, migrate finalized workflow behavior into permanent docs and propagate deferred work forward intentionally.

## Resolution Pass

The sprint resolution pass must document:

- what was actually implemented
- what reviewer behavior changed
- what assumptions changed
- what uncertainty handling changed
- what source/provenance handling changed
- what report outputs changed
- what limitations remain explicit
- what remains deferred

## Permanent Documentation Targets

Update as applicable:

- `docs/core/CURRENT_STATE.md`
- `docs/core/DECISIONS.md` when durable assumptions changed
- `docs/core/ARCHITECTURE.md` when service boundaries or artifact flow changed
- domain docs under `docs/domains/` when a subsystem changed
- `docs/governance/DEFERRED_WORK.md` when any concern is postponed
- `docs/sprints/README.md` when sprint status changes

## Failure Modes To Avoid

- stale planning assumptions
- hidden simplifications
- accidental implied authority
- drift between report behavior and documented methodology
- forgotten deferred review concerns

Reports, exports, and findings must remain aligned with documented methodology and operational limits.

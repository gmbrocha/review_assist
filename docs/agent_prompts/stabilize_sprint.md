Please perform a focused stabilization/audit/checkpoint pass for Review Assist at the current sprint midpoint.

This is a stabilization pass, not a redesign sprint and not a feature-expansion sprint. The goal is to reduce drift, improve reliability, tighten consistency, and leave the repo in a trustworthy state before continuing deeper sprint work.

Primary goals:
stabilize current behavior
reduce UI and logic drift
identify fragile areas
fix obvious regressions and inconsistencies
improve maintainability
confirm systems still align with architecture and product philosophy

Focus areas:
review queue flow
artifact generation flow
GPT draft generation flow
figure editor stability and usability
state synchronization
review item rendering consistency
queue rebuild/refresh behavior
logging visibility/usability
layout consistency and rails
mobile containment/overflow issues
validation consistency
save/update persistence correctness
type safety and runtime safety
dead code or remnants from pivots
naming consistency and terminology drift
loading/error/empty states
review gating behavior
human-in-the-loop safety expectations

Specific instructions:
Do not introduce broad redesigns.
Do not aggressively refactor working systems without strong justification.
Prefer targeted cleanup over architecture churn.
If something appears architecturally questionable but currently stable, document it rather than rewriting it unless the risk is meaningful.
Preserve existing workflow assumptions unless clearly broken.
Watch carefully for duplicated logic, stale state paths, hidden coupling, and UI inconsistencies from rapid iteration.

Deliverables:
Produce a concise stabilization report covering:
critical issues
high-risk areas
medium-risk cleanup opportunities
obvious UI inconsistencies
state-management concerns
validation inconsistencies
dead/stale code candidates
places where current sprint work has drifted from architecture intentions
recommended next stabilization tasks before continuing feature expansion

Then:
Fix small/high-confidence issues directly where appropriate.
For larger or riskier issues, document recommendations first before broad implementation.

Important:
Do not let this become a redesign spiral.
Avoid recursive cleanup expansion.
Bias toward operational stability and trustworthy behavior over polish.

Project philosophy reminders:
human-supervised review remains authoritative
automation assists rather than silently decides
outputs should be reviewable and auditable
the system should absorb operational complexity rather than exposing it
UI should reduce friction without hiding uncertainty
avoid fake certainty/confidence
keep evaluation/review flows trustworthy and inspectable

Engineering expectations:
use the local .venv only
run lint/typecheck/tests where appropriate
identify regressions introduced during current sprint work
check console/runtime errors
check mobile responsiveness/containment
check layout rail consistency
check for loading-state flicker or stale renders
check save/update/reload correctness
check figure editor interactions carefully
avoid introducing unnecessary dependencies

Acceptance criteria:
Repo ends in a cleaner, more stable, more understandable state than it began.
No major workflow regressions introduced.
Known risks and weak points are clearly documented.
Small/high-confidence fixes are completed.
Architecture drift is identified before continuing sprint expansion.

# CK5 conditional composition result (research record, not manuscript)

## State and assumptions
The executed transition function is `runtime/src/revtrace/composed_kernel.py::step`.
It contains C (installed selected state), D (durable identities and bound facts),
V (actual applied certified root plus provisional view), I (accepted input and
original arrival origin), J (frozen jobs/results) and independent worker leases.
C may lead V. P/Y strings are revisable; only installed versions/frontiers and
accepted obligations are monotone. Recovery never interprets a private suffix
as certified text. Full history identities are reconstructed, not just the last
frontier. Runtime has no switch to disable these checks.

Assumptions: single trusted owner; intact framed WAL/fsync semantics; immutable
available accepted audio; trustworthy selection/adapter/transport boundary;
actual consumer receipts; process-group death fences old workers. No Byzantine
host protection, hardware attestation, power-failure test or unbounded liveness.
The broker prevents field-only and duplicate receipt reuse inside its declared
API; arbitrary trusted host Python can still invoke trusted wrapper functions.

## Conditional induction, not a blanket implementation theorem
Base: validated recovery installs exactly durable facts and identities; V is
initially empty, and no execution is permitted before input restoration, actual
application of the recovered roots, and worker readiness.

Step preservation:
- Input sync prepares a nonregressing snapshot and can advance eligible A only
  after its concrete journal checkpoint succeeds. Failed sync leaves A/debt.
- Dispatch requires released/accepted input, current parent, correct authority
  P, a ready unleased worker, and positive causal interval.
- Row completion supplies complete selected Z and trusted render P/Y under the
  frozen job; this does not release a lease and never installs state.
- Canonical sync can only record a current authority successor with bound
  content and unique transaction identity. Installation separately requires the
  exact durable receipt; publication requires installation.
- View application is evaluated privately, checked against the durable root and
  an actual compatible chain, then applied and receipted. Publication is not
  application. A withdrawal does not grant new coverage.
- Batch drain alone releases a physical lease, after all complete rows.
- Recovery reconstructs C/D/I and resets volatile J/V. Cold executor failure
  cannot erase I or turn an old queue receipt into a new selected result.

Thus any finite sequence of admitted abstract transitions preserves these
invariants under the assumptions. The Python finite product search is a check
of this executable abstract specification, not a mechanized proof of the prose
induction and not a refinement proof for arbitrary CUDA/OS/filesystem behavior.
Reject-all is excluded by reachable legal progress states and real service runs.

## Wrapper correspondence
| Actual boundary | Kernel request before effect | Concrete completion receipt |
|---|---|---|
| InputJournal checkpoint | input-sync-request | input-synced after real fsync |
| frozen executor submit | dispatch | row-complete after inbox and Render |
| Canonical WAL group | admission-request | canonical-synced after real sync |
| owner state replacement | install | existing commit event/publication |
| publication FIFO | publish | apply-request; view-applied after view swap |
| physical worker | independent row events | batch-drained; then reuse |
| restart | validated-WAL-replay/input-replay | recovered actual consumer application; worker-ready separately |

Inherited A/B/C/D, D1, WAL replay and native ContinuityView checks remain active.
Some gates are redundant defenses; dropping one need not violate the property.
We characterize sufficient information and alternatives, not universal
minimality of individual source guards. Same-kernel sharing alone is a refactor;
new scientific evidence must come from composition/interleaving and full-path
measured behavior, not from renaming the interface.

# Closed-loop planner implementation and boundaries

Evidence tier: CPU implementation and explicit constructed scheduling controls.
This file does not report a new GPU result. Historical 48-cell evidence is
unchanged. The module changes scheduling only; no admission, certificate,
Trusted Render, WAL, or Worker lease predicate is modified.

## Implemented interface

`runtime/src/revtrace/ces_closed_loop.py` defines:

- `Identity`: actual Session, epoch, Parent version/digest, input/output audio
  frontiers and execution-contract digest. Audio frontiers are sample indices.
- `TargetContext`: actual currently executable target identity, released
  successor obligations, current legal Private path, remaining row-completion
  CDF, and declared Direct/Fallback compatibility estimates (possibly unknown).
- `SuccessorObligation`: released audio only, cumulative remaining-service
  estimate, deadlines, audio weight, optional historical prompt-*length*
  estimate and Private path. It contains no tokens, actual future Parent,
  executable Job or certificate.
- `ClosedLoopState`: owner-local service record and symbolic continuation
  intention. `record_dispatch` is called once after real enqueue success;
  `admitted` retires obligations only after actual WAL installation. Polling the
  planner does not advance a deferral counter. `reset` is required on a fresh
  run/restart scope. `to_audit` is JSON serializable.
- `choose_closed_loop`: returns only the first currently executable homogeneous
  physical batch plus a fully costed prediction suffix. The owner retains
  exclusive responsibility for constructing actual jobs and executing checks.

## Four comparisons, not four new mechanisms

All modes share Row-complete capability, physical risk calibration, the same
bounded action family, complete-cut work accounting, and service protection.

1. `service_cost`: low complete-cut physical wall, current-credit tie-break.
2. `reserved_progress`: finite-prefix current-credit objective, no successor
   reward/backpropagation and no Private-path prediction.
3. `inherit`: adds released-successor canonical completion value and predecessor
   deadline propagation.
4. `causal`: additionally integrates actual Private completion CDFs and
   conditionally legal continuations. With no usable Private path it degenerates
   exactly to `inherit`; without successors `inherit` degenerates to
   `reserved_progress`.

The separation isolates cost/service protection, objective change, released
dependency value and conditional two-path value. A simpler baseline may win.

## Service protection

Each actual unchanged identity retains first observation, actual physical-batch
deferrals, and the earliest previously selected suffix completion promise. A
first decision does **not** inherit a hard Commit-first ordering. Only the
previously chosen unfinished suffix creates a promise. A two-dispatch deferral
budget prevents perpetual replacement of that suffix while the target remains
eligible. Promise breach and least-violation choices remain visible when cost
predictions make the promise infeasible.

`promise_quantile=.9` is the empirical quantile of each physical outcome's row
time envelope plus the shared Owner delivery allowance. It is deliberately
not called a single-current-row P90, a probabilistic deadline guarantee or a
10% Commit-late constraint. Commit lateness remains a performance observation
and secondary tie-break; it never changes state-write permission.

Temporarily disappearing from an eligible list does not imply completion.
Observing a new *actual* identity for that Session replaces the old binding;
actual WAL installation explicitly retires service debt. A symbolic child
intention may carry a predicted service promise, but it can bind a child only
after the owner supplies its real newly observed Parent identity.

## Finite-prefix and two-path objective

For an actual audio atom q, the original metric is unchanged:

`Q_q = audio_q * 1(first_legal_Consumer_D_q <= release_q+2)
                 * 1(durable_C_q <= release_q+8)`.

Each bounded scenario evaluates `(actual_Q_prefix + predicted_new_Q) /
(actual_T_prefix + predicted_complete_cut_wall)`. It does not divide expected
credit by expected time and call that an exact expected ratio. Current targets
and up to two already-released successor layers enter the declared paid cut;
overdue zero-immediate-credit parents are not deleted. Predicted future
Generation batches use the same calibrated homogeneous physical-batch model,
with explicitly historical feature estimates rather than unknown future
tokens. All additional batches, fallback and lease time are charged.

The CDF of an actual pending Private row is integrated at the deadline; its mean
is not substituted inside a deadline indicator. Authority and Private CDFs are
independence approximations where joint data are absent. In the extra current
target credit mass, `Private_D <= deadline < Canonical_C`: a currently legal
Private observation necessarily precedes the late Canonical result and does
not require post-commit retention. Canonical-first timely observations are
already counted, so they cannot earn another display credit.

For successors, legality is integrated through **every** possibly invalidating
ancestor transition at each Private completion-CDF time t. It is not reset at a
later symbolic child. A Generate transition has forecast survival
`1 - F_row(t)*(1-p_direct)`. Verify retains the accepted-early versus
fallback-late joint structure:

`(1-r)*(1-F_early(t)*(1-p_accept))
 + r*(1-F_late(t)*(1-p_fallback))`.

These factors are multiplied through the ancestry as an explicitly independent-
transition approximation. For a path not currently legal, the first factor
includes **only** already-installed-and-compatible mass: an old result is not
assumed to be cached and revived after a later Parent appears. The row envelope
still conservatively controls a future batch's Parent/resource availability,
but cannot enlarge a free-of-retention Private interval. An early-parent-row /
envelope counterexample is tested separately.

Direct and Fallback use distinct declared rates; a failed verification cannot
collapse to the Direct rate. The first successor may use the actual current
transition's calibration. A subsequent symbolic Generation creates another
unknown Parent class: depth-two unknown rates do not silently inherit the root
Verify witness. The old single-rate field remains only for declared equal-rate
CPU fixtures and is forbidden in real-stage audit input.

If Direct/Fallback compatibility is uncalibrated (`None`), it is **not** set to
false and Verify receives no asymmetrically invented Private reward. Current
legal Private progress can still count independently of such post-commit
compatibility. Existing cached/withdrawn text is not an automatic future
Consumer publication path; the owner must establish actual publishability.

Private clocks also explicitly name whether delivery is included. Fixtures can
use terminal-row time plus the common allowance; the production owner supplies
remaining-to-Consumer CDFs conditioned on an **observed Worker start** and no
received result, and the planner does not add the allowance twice. Missing
Worker-start telemetry means age zero, not fictitious GPU progress since
enqueue. Finite upper-endpoint CDF bins retain all empirical mass and report
their one-sided approximation error; they do not create a distribution-free
prediction or a new safety guarantee.

## Frozen bounded CPU search

Default bounds: candidate beam 8, at most 16 scenario combinations, at most two
released successor layers. All-Generation, cheapest physical work, service
promise and inherited/current-credit seeds remain in the bounded family.
Current-cut filtering is a heuristic, not safe global-optimality pruning.
The final search always pays the complete declared cut. Only the first actual
batch is dispatched; symbolic Parent values never enter execution.

Products within the scenario budget are exact within the empirical model.
Larger products use fixed-seed weighted stratified quadrature, not a Monte
Carlo confidence interval or a complete temporal-correlation model. Every
decision logs per-step marginal total variation, fallback-mass discrepancy and
omitted largest-lease outcome mass. This is additional approximation on top of
the original eight-medoid calibration compression, whose old error report is
retained separately.

On one local Windows CPU fixture using the existing calibration_v3, 16 current
targets and two released successor layers, an initial 51-forecast implementation
took 303.7 ms. Restricting only the declared search/scene budget (not the safety
contract or owed work) yielded the following four-repeat scoped timings:

| Current targets | CPU planner seconds | Full forecasts |
|---:|---|---:|
| 1 | .001086, .000957, .001068, .001094 | 2 |
| 4 | .016406, .016876, .015844, .015156 | 15 |
| 8 | .025784, .036864, .030533, .027738 | 15 |
| 16 | .051562, .062815, .060720, .060299 | 15 |

These are CPU constructed-feature timings, not GPU savings. The final added
Private CDF and Owner integration require fresh measured end-to-end CPU timing.

## Safety and remaining obligations

The planning module creates no execution permissions. Conditional safety rests
on unchanged owner-side validation of actual Parent, epoch, released interval,
execution contract, complete output/stop, Trusted Render and WAL. A symbolic
history is never installed; actual unknown Generation outcomes form their own
independently audited history. Row-complete does not release an occupied lease.

CPU tests retain the real 2s/8s Commit-first counterexample, finite actual
service of repeatedly deferred old targets, identity replacement/reset,
unreleased successors, no missing cut work, duplicate dispatch refusal,
actual-display residual credit, both GPU timelines, CDF half-mass deadlines,
unknown compatibility, and root-vs-grandchild conditional identity.

Not implemented or claimed here: global GPU optimum, unknown-token oracle,
token preemption, KV reuse, Grafting, Elastic rho, online descendant identity
inheritance without actual admission, a Worker/IPC restart protocol, or a full
GPU0/GPU1 joint planner. Any shared GPU0 dispatch extension and its net
contribution require separately integrated and measured controls.

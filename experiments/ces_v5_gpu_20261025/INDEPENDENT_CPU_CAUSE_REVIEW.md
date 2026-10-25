# Independent CPU cause review of the executable V5 pilot

Review date: 2026-10-25. Evidence: frozen source inspection and constructed CPU
scheduling probes. The GPU pilot is running under the root coordinator. This
review neither starts remote work nor changes its runtime, parameters or paper.
Intermediate Commit P99 observations supplied to the reviewer are unverified
diagnostic signals and are not adopted as final measurements below.

## Judgment

The executable V5 contains real corrections to progress accounting, row-time
expectations and batch action choice. It does not yet implement a closed-loop
Commit-service protection rule or the successor deadline propagation proposed
in the earlier CPU research. Its row completion model also remains exchangeable
within a physical batch. These are three concrete, falsifiable ways in which a
mathematically valid local score can produce poor end-to-end service.

The strongest source-level finding is: **a target appearing in every scored
common-cut suffix has no reservation that makes that suffix execute.** A new
decision can repeatedly put the same target behind another first batch. This
is a limitation of the current receding-horizon controller, not an admission
safety violation and not yet the established cause of any actual GPU tail.

## Source identity and material read

Frozen runtime commit: `126dc815962e8f726b0cbdf214a19318b28a3629`.

| Source | SHA256 |
|---|---|
| `ces_v5_policy.py` | `57d0b8920a30277261741fb161afcdb7bbdfa49b98b7a3d753235aa4ff47e157` |
| `ces_runtime.py` | `51314925ec236c2e2483482dfa9725b0821510e0d31eb8d75a8d2712e2267d68` |

The review read AGENTS.md, RESEARCH_DECISION.zh.md, MATH_REVIEW.md,
MATH_AND_FAIRNESS_REVIEW.md and MODEL_MECHANISM_REVIEW.md, then checked current
function bodies rather than relying on the documents' historical line numbers.
Relevant anchors are `choose_v5`, `_plans`, `_plan_metrics`, `_mixture_cdf`,
`CESScheduler._features/_dispatch/_commit_ready/_order_proposals`, and
`LiveQwenScheduler._ready/run/_begin_segment`.

## 1. The common cut is an evaluation set, not an executed commitment

`_plans` accounts for all selected current targets and `choose_v5` returns both
the full scored plan and only `plan[0]` as the operation to issue. The owner
uses `decision['operation']` and `decision['sids']`; it logs the plan but does
not retain a pending suffix, latest-service reservation or Authority aging
state. On the next physical availability it constructs a fresh ready set and
calls the selector again. Completing one Session can introduce that Session's
next released target while an older target from another Session is still
waiting. The aging rule in `_order_proposals` applies to GPU0 ordering, not
GPU1 evidence service.

The common-cut rule fixes an unfair *one-decision comparison* that would omit
remaining work. It does not by itself bound postponement across decisions.
Nor does scoring prospective credit repeatedly constitute double-counting
the actual measured Goodput: only real D/C observations determine that metric.
The issue is the controller's future-service assumption.

### Reproducible closed-loop CPU counterexample

`cpu_cause_probe.py` imports the frozen `choose_v5` read-only. Its output is
`CPU_CAUSE_COUNTEREXAMPLES_v2.json`; it records source commit/SHA, all constructed
service parameters and the six complete decisions. The earlier JSON is retained.

All targets obey the actual temporal contract: `D_due=release+2`,
`C_due=release+8`, and audio weight = 2 seconds. All audio is released before
selection; positive run clocks permit nonnegative Session arrival offsets.
No candidate or injected-fault label enters the decision.

The old target A releases at t=2, so its Display deadline is 4 and Commit
deadline is 10. The first decision is at t=5. Six new independent targets are
then released 1.2 seconds apart. Constructed physical service is 1.2 seconds
for a singleton Generate, 3 seconds for the two-row batch, and 0.08 seconds for
Owner delivery. Each new target has attainable immediate credit; A has already
missed Display. Every scored plan includes A as the second singleton, but only
the first singleton executes before the next decision.

| Decision time | Executed target | Predicted A finish in the scored suffix | A Commit due |
|---:|---|---:|---:|
| 5.0 | B1 | 7.48 | 10.0 |
| 6.2 | B2 | 8.68 | 10.0 |
| 7.4 | B3 | 9.88 | 10.0 |
| 8.6 | B4 | 11.08 | 10.0 |
| 9.8 | B5 | 12.28 | 10.0 |
| 11.0 | B6 | 13.48 | 10.0 |

A finally completes at 13.48 under the declared fixture. A second variant
sets row completion to 90% of the physical lease: the row and its entire
0.08-second Owner delivery finish before the next dispatch. It still defers A
six times and completes A at 13.36. Thus the possibility does not depend on
overlapping an unfinished Owner action with the next selection.

This proves possibility with a finite set of seven Sessions. It does not prove
that a particular GPU target was deferred six times, that the constructed
batch costs occur on RTX3090, or that reserving A would improve measured
Goodput. Indeed, preserving a zero-own-credit target's Commit deadline can
trade off attainable Display credit elsewhere; the earlier Commit-first
counterexample remains valid. A service-risk constraint must be explicit,
not introduced as if it guaranteed a Pareto improvement.

### Minimal actual-log test

For each `(session, end_window, Parent)` target, reconstruct every decision at
which it was ready, its position in the recorded full plan, whether it entered
the executed first batch, and its eventual enqueue/commit. Count suffix
replacement and measure ready-to-enqueue time. Join that trace to actual
Worker start/drain, row-result, WAL install and Consumer clocks.

Partition the actual Commit latency into non-overlapping intervals:

`release -> legal Parent/target eligibility -> enqueue -> Worker start -> row result -> durable install`.

Do not sum overlapping per-row GPU service. Separate first two causes:
unavailable Parent vs an already eligible target repeatedly passed over. The
replanning hypothesis loses force if late targets were selected immediately
once eligible and the extra time lies in physical service or WAL instead.

The smallest repair worth testing, only if repeated postponement is observed,
is a persistent per-target service obligation with a model-based latest-start
check or a revalidated completion suffix. It must carry `(session, Parent,
frontier, contract)` identity and revalidate before execution. First test that
it eliminates this CPU counterexample; next quantify the actual tradeoff for
already-displayed Commit credit and released successors. It must not blindly
restore Commit-first priority, reuse a stale planned job, or claim that a P90
service estimate guarantees an actual deadline. Shared controls get the same
service-protection capability.

## 2. Correct row CDF arithmetic does not establish exchangeability

The frozen implementation correctly integrates deadline indicators over a
row-time distribution and keeps physical lease time separate. The vectorized
implementation is algebraically equivalent under its model assumptions.
However, the same marginal row CDF is queried for every target in a batch;
`row_predictions` also assigns the same batch-conditional mean finish to each
row. Historical failed-row identity is exchangeable, with `K/n` assigned to
each target. Known birth/rejection/candidate-length information can affect
partition enumeration, but it does not turn this into a calibrated per-target
failure/completion model.

The CPU probe gives two row times 5.2 and 6.8, with targets released at 3.5 and
5.0. Their Display deadlines are 5.5 and 7.0 and their Commit deadlines are
11.5 and 13.0. If the fast row is the tight-deadline target, actual constructed
credit is 4 audio-seconds. If it is the slow row, credit is 2. Both assignments
have exactly the same marginal row CDF; the implemented exchangeable forecast
returns 3 in both cases. The CDF is not arithmetically wrong. The missing
information is the dependence of row identity, completion and deadline.

Minimal check: on actual selected batches, calibrate per-row deadline coverage
and residuals by pre-dispatch observable features (input duration/width,
candidate length when known, row position, prior verified rejection, deadline
slack). Cluster uncertainty by physical batch and source/run. Actual failure
labels may be used to diagnose afterward but not supplied to the scheduler.
Good mean or overall P90 coverage does not establish coverage for the rows
the scheduler preferentially selects near a deadline.

If this conditional miscalibration is observed, compare one simple conditional
CDF or conservative residual group against the exchangeable model using the
same selected-batch records. Unchosen Verify/Generate costs remain unknown;
offline prediction accuracy alone cannot establish an online policy gain.

## 3. Successor deadlines were discussed and tested in CPU models, but are absent online

The executable Target describes one current Authority target per Session.
`_features` does not construct released successor obligations; `choose_v5`
does not import or call `deadline_backprop.py`. The CPU backpropagation/oracle
modules therefore do not currently influence real GPU dispatch. In-flight
Private descendant counts are retained in common feature structures, but
Progress's credit computation does not convert them into legal successor
deadline value. Nor should raw descendant age be treated as saved work.

A current target whose own Display has expired gets zero immediate credit,
even if its actual Canonical completion is needed to unlock a later released
frontier that could still meet D or C. This is precisely the complementarity
identified in the earlier CPU reports. The finite-prefix score does not price
it merely by charging the old target's remaining service in its suffix.

Minimal check: count actual decision states where (a) the current target has
zero own credit; (b) later audio has already released; (c) a later D/C deadline
is still potentially attainable after paid remaining work; and (d) that
deadline is not already satisfied through the actual legal Private lane.
Use observed Parent availability and bounded service estimates. A hypothetical
new Parent must never become an executable job before actual admission.

Only if those opportunities recur in actual late chains should a single-step
deadline-backpropagation rule be connected. Give it the same legal subbatch
family and cost model as a strong EDF/risk control. Conditional Verify-success
projection may support a precise compatibility branch; unknown Direct or
Fallback output does not imply incompatibility. No new Grafting is needed.

## 4. Additional checks before attributing the real result

- Splitting can add model invocations, change padding/input realization and
  increase physical occupancy. Inspect actual call counts, sizes, fallback,
  energy and queue decomposition before crediting a schedule-only explanation.
- The 80.294-ms historical delivery allowance is an empirical shared constant.
  It does not model serial Owner/WAL contention or dispatch delays. Compare
  actual row-to-install and row-to-Consumer distributions across methods.
- The planner evaluates at a pre-planning `now`, then constructs jobs. Actual
  feature/planner CPU time belongs in the wall clock and can consume small
  slack. Measure it from each decision rather than transferring Windows CPU
  benchmark timings to Linux GPU serving.
- `progress_joint` still only changes GPU0 ordering. With at most 16 single-
  flight Sessions and microbatch limit 16, it normally cannot change the ready
  dispatch set; numerical/input changes from row order require their own
  audit. A better/worse result alone does not show joint resource scheduling.
- First legal Display and uninterrupted-visible-until-certification metrics
  must both be retained. Later Commit cannot retroactively repair a Display
  deadline, and an early view later withdrawn is not stable display quality.

## What can be concluded now

The executable controller has identifiable incomplete assumptions beyond the
CPU bugs already fixed. The two new probes verify a closed-loop postponement
possibility and a per-target forecasting ambiguity under the frozen policy.
They justify targeted diagnosis of the running pilot, not a claim that any
one cause explains its current rough Commit P99 or that the proposed check
will improve GPU performance.

The next decision should use the complete, independently audited 48-cell
matrix and the target-level timing decomposition. A fix is justified by an
observed dominant cause and a legal paid-work opportunity; extra score weights
or a weaker Fine/Standard baseline would not supply that evidence. If simple
risk scheduling or an executor-level improvement wins, it remains a useful
combination, with its actual source of benefit stated explicitly.

## Reproduction and immutable evidence

Run from this directory:

`python cpu_cause_probe.py --output <new-output-name>.json`

The probe refuses to overwrite an existing output. It loads no neural model,
uses no SSH, and does not edit the runtime. The final retained output is
`CPU_CAUSE_COUNTEREXAMPLES_v2.json`; it embeds the exact source and script
hashes, all six decisions for each variant, frozen constructed costs and the
deadline-contract checks. Version 1 is retained to document the earlier
relative-clock CDF presentation; v2 presents positive absolute clocks for all
targets without changing the mathematical conclusion.

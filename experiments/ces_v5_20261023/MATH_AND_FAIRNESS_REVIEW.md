# V5 mathematical and fairness review

Date: 2026-10-23. Scope: CPU mathematics, source inspection and historical
calibration. No GPU inference or real serving gain was measured here.

## Recommendation

The initial V5 implementation improves observability, but two objective-model
mismatches should be repaired before the next GPU pilot. Retain the shared
physical risk model and actual Consumer ACKs. Use the declared dual-deadline
audio objective directly, and preserve a distribution of row completion times
inside each physical-batch scenario. Avoid adding a new algorithm family.

## 1. Commit-first lexicographic ordering can defeat dual-deadline Goodput

`choose_v5` currently ranks predicted Commit-late audio before every other
quantity. This is stronger than the declared dual-deadline Goodput objective.
An already missed Display deadline makes a frontier's own Goodput credit zero,
whether its later Commit arrives at 7.9 or 8.1 seconds. Such a predecessor must
still execute to preserve forward progress, but preserving its own Commit
deadline need not outweigh an attainable Display+Commit deadline elsewhere.

The executable `math_counterexamples_v5.py` uses deterministic legal operation
costs and two pending targets. At decision time zero:

| Target | Display state | Commit deadline | Available operation |
|---|---|---:|---|
| A | Already irreversibly late | 1.5 s | Generate: 1.4 s |
| B | Display deadline 0.5 s | 6.5 s | Verify: 0.2 s, no fallback |

Both plans execute both targets exactly once and pay the same 1.6 seconds.
The implemented lexicographic rule chooses Generate(A) then Verify(B): zero
Commit-late audio, but zero dual-deadline credit. Verify(B) then Generate(A)
earns two audio-seconds of credit; A commits 0.1 seconds late. This is an actual
CPU execution of the present policy, not an imagined branch of a GPU trace.

Recommended minimal repair: maximize expected residual dual-deadline credit
per common-cut physical time, use shared tail/Commit risk as explicit bounded
constraints or secondary costs, and retain a declared aging/forward-progress
rule for zero-credit predecessors. A universal lexicographic prohibition on
any extra Commit risk is not equivalent to maximizing Goodput. When no plan
satisfies a predeclared risk budget, use an explicit least-violation fallback
rather than concealing the tradeoff in a huge weight.

This recommendation does not drop overdue work. A common-cut plan contains
all current targets, but because only its first action executes before
replanning, a finite-window/aging condition is still needed to discuss
starvation under continually arriving workloads. The present finite 16-source
pilot does not establish unconditional infinite-load liveness.

## 2. A mean row completion time is not enough for a deadline objective

`calibrate_risk.py` initially replaces a physical batch's real row completion
times with a mean `row_fraction`; verification similarly averages accepted
rows and fallback rows. The objective then applies a deadline indicator to
that mean. In general:

\[
\mathbf 1\{\mathbb E[T]\le d\}\ne
\mathbb E[\mathbf 1\{T\le d\}].
\]

The CPU counterexample has row completions 0.1 and 0.9 seconds and a shared
0.5-second deadline. The actual batch has one on-time row. Its mean is 0.5
seconds, so the current surrogate predicts both rows on time. Moving the
deadline slightly below 0.5 reverses the error: it predicts zero although one
row still completes on time. Better mean lease calibration cannot fix this.

Recommended minimal repair: each weighted physical-batch scenario carries a
small empirical row-completion CDF, separated into accepted/fallback groups
where available. Integrate each target's deadline credit over this CDF. Keep
the scenario's single physical lease for the start of the next batch. A row's
early completion never releases the Worker. Unknown row identity may remain
exchangeable; do not claim candidate-specific completion predictions until
they are calibrated.

Exact row distributions have at most the microbatch size in the current
study. If online CPU cost requires compression, preserve weighted CDF support
near the deadline rather than silently replacing it with its mean. Report
compressed-versus-uncompressed deadline-credit error and planner CPU time.

## 3. Calibrate and validate the function actually used for decisions

The initial producer writes all scenarios in a bucket while the consumer
rejects more than eight. This integration failure was detected before GPU
execution. The raw v1 history should remain unchanged; a v2 producer should
freeze representative scenarios, original sample support and nonuniform
weights before policy tests.

The initial reported P90 coverage is based on `old_global_prediction * ratio`
and not the complete `predict_batch` scenario distribution. It cannot be
quoted as final-model coverage. Validation must call the final predictor with
each held cell's actual observable input features and compare:

- physical lease expectation and P90/P95 coverage;
- accepted and fallback row-completion CDF calibration near 2/8-second slack;
- weighted fallback-count mass and tail preservation after compression;
- the decision-relevant probability of meeting each remaining deadline.

Use a cell-level calibration split, shared preprocessing and the same costs
for Risk-cost and Progress. This remains a historical cell-held check on
reused acoustic sources. It is neither a new-source validation nor a bound on
future SLO violations.

## Correct accounting that should be retained

For frontier i, let D_i be its first actual legal Consumer observation, C_i its
durable installation (and separately its certified Consumer application),
w_i its newly covered audio, and dD_i/dC_i its frozen deadlines. Its eventual
credit is exactly:

\[
g_i=w_i\mathbf1\{D_i\le dD_i\}\mathbf1\{C_i\le dC_i\}.
\]

An already displayed but uncommitted frontier still has pending Commit value.
A fully committed frontier leaves the pending set. An already missed Display
deadline cannot be repaired retroactively. A zero-own-credit predecessor can
still have value through future descendants, but that value requires an
explicit released dependency/cost model; it is not the number or age of
already issued Private jobs. Do not count sunk GPU work as future savings.

The present minimal V5 forecasts uncovered Display through Canonical row
completion plus delivery overhead. It does not yet predict actual pending
Proposer completion and compatibility. That is a declared approximation,
not an exact joint GPU0/GPU1 optimizer.

First legal visibility and uninterrupted visibility until certification are
different metrics. Both must be delivered along with retractions. No ready
commit may be held to manufacture first-visible credit. Full-run Goodput uses
actual arrival-to-drain/Consumer wall time; common-cut credit/time is only an
online heuristic for this global metric. Energy includes all executed old
work, both GPUs and paid fallback, independently of which rows earned credit.

## Fair attribution

All arms retain the same immutable evidence, D1, admission, WAL and physical
lease checks. Shared ACK/row-completion/IPC costs are present in each arm.
The new risk calibration is identical for the new cost and progress policies.
Fine and Standard receive the same proposer ordering in dedicated controls.

A gain shared by simple risk scheduling is a useful system result. Progress
planning needs a separate incremental benefit only if claimed as an extra
algorithmic contribution. The failure of that extra component does not erase
an effective simpler combination. Conversely, a CPU counterexample repairs a
surrogate defect; it proves no particular workload speedup.

## Current evidence state

- Two deterministic mathematical counterexamples executed and passed.
- Five independent accounting fixtures executed and passed.
- Initial calibration schema mismatch reported; v2 is under root ownership.
- This review does not authorize or report any new GPU run.

## Same-input verification after the mathematical repair

Root subsequently changed the Progress objective to expected joint credit per
expected common-cut wall; Commit-late risk is secondary for that arm. The
shared Risk-cost control retains its declared risk-first objective. The policy
now integrates a cached empirical row CDF conditional on each physical-batch
scenario, and common-cut wall includes the final modeled owner delivery.

The exact first counterexample now chooses Verify(B) first and predicts the
attainable two audio-seconds of credit. The exact 0.1/0.9-second row example now
predicts two audio-seconds, matching one of two equal-weight rows. The former
mean-based approximation predicted four. These comparisons are deterministic
CPU fixtures and establish correction of those mathematical errors only.

Ten additional independent CPU tests in `test_cpu_repairs.py` pass. They cover
CDF mass and inclusive deadline boundaries, explicit weighted tardiness,
zero/all-reject distributions, weighted scenario normalization, preserving the
Worker lease after early rows, owner-delivery cost, and complete/no-duplicate
targets across all generated split plans for one through sixteen targets.

The shared action family now contains bounded Generate/Generate and, when
all candidates are ready, Verify/Verify split batches. These are real proposed
physical dispatch alternatives, not mere within-batch row permutation. Both
new controls receive the same candidate family. Any eventual online gain from
batch splitting requires a matching strong cost/standard control and an actual
input, quality and paid-work audit; this CPU review cannot establish it.

## Independent compressed-calibration audit

The generated `calibration_v2` passed a second independent script check. The
90 development witness archives match their recorded hashes and reconstruct
2,000 distinct physical batches. All stored buckets contain at most eight
representative scenarios with positive weights summing to their original
sample support. No-fallback/fallback probability mass is exactly retained.
Calling the actual `predict_batch` with all 2,000 historical sets of observable
job features produces finite positive leases, normalized scenario/CDF mass,
and no modeled row completion after its physical lease.

Compression is approximate. The largest total-variation difference in the
failed-fraction distribution is 0.30 for the 16-row Verify bucket (40 physical
batches). Its normalized-cost P90 changes from 1.695 to 1.718. The global Verify
maximum ratio falls from 4.144 to 1.830 because the medoids do not retain the
maximum observation. These are retained distortion measurements, not hidden
failures. The model must not be described as preserving every K or every tail.
The separate final-model held-cell coverage check determines whether this
approximation is adequate for the next diagnostic experiment.

## Nonzero historical delivery allowance

`calibrate_delivery_allowance.py` reconstructs 14,670 actual Canonical row
transitions from all 90 development cells. Each row's absolute result clock is
reconstructed from enqueue, Worker queue delay and row service time and equals
the immutable receipt's rendered clock exactly. Owner install is independently
reconstructed from the common-frontier latency and the commit event; both
absolute clocks match exactly. Session offsets plus audio frontier and the
commit event's release clock reconstruct the same run origin. No anomalies or
negative-delay clipping occurred.

The measured row-result-to-Owner-install P90 is 79.496553 ms. The corresponding
actual certified-Consumer P90 is 80.293771 ms (median 38.614005 ms, maximum
213.151274 ms). `calibration_v3` adds the latter as the shared empirical
`owner_delivery_seconds` allowance, with raw CSV, provenance, source hashes
and a distinct immutable calibration version. Validation cells are excluded.

This removes the zero-delivery-time approximation. A single additive allowance
still does not reconstruct the serial Owner/WAL CPU resource or its interaction
with dispatch of the next physical batch. It is a common prediction parameter,
not an unconditional bound or evidence of improved online Goodput.

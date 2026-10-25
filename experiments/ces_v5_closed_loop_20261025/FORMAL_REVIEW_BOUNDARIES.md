# Formal closed-loop campaign: comparison and claim boundaries

Written before reviewing the 72-cell formal results. This is an interpretation
contract, not a report of measured improvement. Runtime and controller are
frozen; this document changes no algorithm, parameter, baseline, dataset,
dispatch order, metric, or execution gate.

## 1. What the frozen matrix contains

The main matrix is eight methods × two arrivals × three fresh-process repeats:
Fine, full Standard Safe Async, old Joint Cost-only, Strict+paid Fallback,
service-cost, reserved-progress, inherit and causal. All 48 main cells preserve
the original `ready` Proposer policy. Twenty-four separately labelled side-arm
cells add Fine+shared-progress, Standard+shared-progress, Cost+joint and
Causal+joint, with otherwise matched source, arrival, traffic, seed and repeat.
The predeclared counterbalanced order is not changed after observing results.

All cells are Mixed, fixed fine=2s/rho=1, the same two RTX3090 resource budget,
FP16 Proposer and FP32 Authority, common Row-complete/Batch-drained interfaces,
Trusted Render, actual Consumer observations and WAL admission predicates.
This matrix does not add Clean/High conditions, coarse-rho evaluation, another
model family, long-session recovery, or a new-source confirmation pool.

The semantic protection requirements are common; each execution still binds
its own actual Parent/frontier/input/contract identity. Different batch shapes
or evidence modes may produce different legal Canonical histories. Literal
digest identity, token equality or WER equality across methods is not assumed.

## 2. What each comparison can isolate

| Comparison | Supported intervention | What it does not isolate |
|---|---|---|
| service-cost vs reserved-progress | With the shared service book, risk/cost model, current-cut capabilities and GPU0 policy, change from cost-first selection to the finite-prefix residual-progress objective | A service-guard ablation; a new admission guarantee |
| reserved-progress vs inherit | Add the released-successor mechanism package: deadline propagation, successor value, corresponding priority/search seeds and symbolic continuation service intentions | Deadline backpropagation alone independently of the rest of that package |
| inherit vs causal | Add the current/successor Private-display completion and conditional ancestry-survival model, under the same main-arm GPU0 policy | A new retention primitive; proof that unknown Direct output is incompatible; global joint-resource optimality |
| Fine vs Fine+shared-progress | Effect of the shared GPU0 homogeneous-subset policy on a strong original Fine point | An exclusive CES capability |
| Standard vs Standard+shared-progress | The same GPU0 capability on the full conventional safe-async control | An exclusive RevTrace state-safety semantic |
| Cost vs Cost+joint | Candidate-aware GPU0 capability available to the strong simple cost reference | A concession available only to causal/CES |
| Causal vs Causal+joint | Incremental GPU0 coordination on the same GPU1 causal planner | Proof that the entire gain comes from conditional Parent planning rather than shared subset execution |
| Full method vs Fine/Standard/Strict/old Cost | End-to-end system integration under unchanged safety requirements and complete paid work | A single-factor attribution to each component in the full integration |

The simple and full policies receive the same executor capabilities and cost
accounting. A strong simple combination is a valid useful outcome; its gain
cannot be reassigned to the more complex planner merely because the latter
has a new name. Conversely, established components do not invalidate a genuine,
repeatable integration benefit. The evidence must distinguish those claims.

## 3. Missing comparison: no pure no-service-guard GPU arm

These 72 cells contain **no** controlled GPU pair differing only in persistent
service obligations. All new closed-loop modes share that protection. The
previous 48-cell `progress` campaign differs in runtime, observations, planning
horizon/objective and calibration/profile context. It is a historical failure
witness, not the missing single-factor service-guard control.

Likewise, changing the cost model or comparing Fine's natural FIFO service with
a complete new planner does not isolate the guard. CPU traces demonstrate that
the old target can be repeatedly postponed and that the new book prevents that
constructed failure. They do not measure the guard's isolated GPU Goodput gain.

A before/after cross-campaign latency can be reported descriptively with both
versions and contexts, but not as a causal estimate of guard-only benefit.
This gap must remain explicit; no extra GPU experiment is silently added to
repair it during this frozen campaign.

## 4. Safety, performance and recognition are different outcomes

Every actual result must pass the original checks against the actual current
Parent, released audio, execution contract, complete token/stop evidence,
Trusted Render and WAL. A predicted compatible successor is not an execution
job or a certificate. A row receipt does not release a still-occupied physical
Worker lease. A simulation or an earlier run's output cannot stand in for an
actual model result under a new Parent or layout.

Passing these checks establishes scoped admission/trace correctness. It does
not establish transcript completeness, recognition quality, bounded memory,
unconditional liveness, or an SLO guarantee. A complete run with capped outputs
is retained as `TOKEN_LIMIT_BOUNDARY`: valid provenance and incomplete content
can coexist. Its actual WER/CER, cap counts and all requested audio remain in
the quality and performance accounting.

Normal fresh-process durable runs are not crash-injection experiments. Their
WAL checks cannot be relabelled additional SIGKILL, power-loss or host-failure
recovery evidence. Original C1/C3 results remain separately scoped.

## 5. Primary and sensitivity metrics

Primary Audio Goodput retains the original first-legal-observation definition:

`Q = sum_q audio_q * 1(D_q <= release_q+2) * 1(C_q <= release_q+8)`;
`Goodput = Q / actual_run_wall`.

Actual Consumer application, not owner publication or a predicted ETA, supplies
D. Durable installation supplies C. An already displayed frontier retains its
pending Commit obligation; an overdue unseen frontier loses its own credit
but remains mandatory work and may enable later released audio. Late
publication cannot retroactively recover past Display credit.

All requested audio, unfinished frontiers, paid obsolete Private work, actual
Fallback, CPU/IPC/WAL overhead and complete physical leases remain accounted.
An incomplete/failed requested cell makes the comparative campaign incomplete;
it is not silently dropped to improve a median or success rate.

Report alongside the primary metric: certified-Consumer Commit, visibility
stable until certification, retractions, WER/CER/error denominators, capped
admissions, Display/Commit P50/P95/P99, whole-run dual-P99 pass count, both-card
GPU J/audio-s, actual calls/batches/fallbacks, candidate wait and fsync/host
cost. Better primary Goodput obtained only through earlier subsequently
withdrawn text is not automatically better dependable user experience.

The median of three per-run P99s is not a P99 pooled over all repeated
frontiers. GPU energy is not host-CPU energy. Summed overlapping row latencies
are not exclusive physical GPU time. All such clocks retain their labels.

## 6. Model and mathematical limits

The planner's objective is a finite-prefix, bounded-scenario prediction using
actual past Q/T. It is neither a proof of full-run optimality nor an exact
solution over unknown future model outputs. The bounded common cut pays its
declared released obligations; a search beam can still miss a better legal
plan. Future prompt lengths and service costs are explicit estimates, not
constructed future token histories.

Authority outcomes use compressed historical physical-batch scenarios,
exchangeable row identity and a bounded scenario quadrature. Original medoid
compression and subsequent quadrature are distinct approximations; selected
batch costs, row deadlines and tails must be checked against actual execution.
A fitted mean cost or empirical P90 is not a distribution-free bound.

Private remaining-to-Consumer CDFs are conditioned on actually observed Worker
start and missing receipt, not fictitious progress since enqueue. Finite
upper-endpoint bins preserve empirical mass but can conservatively delay it;
their approximation error is not model-prediction error coverage.

Conditional branch survival uses the joint accepted-early/fallback-late row
structure and all possible ancestor updates. Subsequent unknown Parents do not
inherit the first root's witness. Direct and Fallback have distinct empirical
rates; sparse unknown values are not actual incompatibility. The fitted rates
come from selected historical executions, not exact paired counterfactuals for
each current batch. Cross-ancestor and cross-GPU independence assumptions can
remain wrong despite sound admission; this affects performance prediction,
not write authorization.

The empirical service promise is not a hard Commit-first constraint or an
eight-second completion theorem. The two-dispatch deferral guard concerns a
persistently eligible unchanged identity at legal dispatch opportunities. It
does not bound GPU execution, storage stalls, unavailable Parents, failure or
unbounded arrival load in wall-clock time.

## 7. Statistical and source boundaries

The reused source pool has already participated in diagnosis and profile
fitting. It is **not independent held-out confirmation**, regardless of fresh
processes, new seeds or a new campaign name. This campaign can establish a
controlled diagnostic mechanism/performance result on that pool; a broader
generalization claim needs genuinely new evidence.

Seventy-two cells are not 72 independent acoustic sources. Main comparisons
have three matched fresh-process runs per method/arrival, repeatedly observing
the same source/frontier collection. Paired run intervals are small-sample
descriptive evidence. Source-cluster resampling is conditional on the actual
observed schedules; it does not re-execute the model or queue. Many pairwise
comparisons do not supply automatic multiplicity-corrected significance.

CPU counts such as 112 and 367 refer to different scoped suites or stages.
They must not be added into a headline number of independent validations,
interpreted as extra GPU trials, or substituted for the final frozen-source
test identity. Name each suite, source hash, evidence tier and actual result.

The exogenous F2 target map is frozen, but a policy can change which Proposer
jobs actually execute and consume it. Report requested fault targets separately
from actual consumed-F2 jobs. Different exposure is a policy outcome, not proof
that all methods saw an identical number of model-input faults. Do not access
fault labels online or retrospectively filter audio to equalize a result.

## 8. Pre-result decision discipline

Preserve every group, repeat, failed run and quality/cost tradeoff. First verify
input/history/accounting audits, then examine measured system outcomes and
trace actual critical paths. Do not tune the frozen policy after seeing a
weak first repeat or select the baseline that makes a favorite treatment win.

A useful C2 integration result requires repeatable measured benefit against
strong fair references with unchanged admission requirements and openly
reported quality and full cost. A narrower conditional-planning claim also
needs incremental value against inherit; a successor-mechanism claim needs
value against reserved-progress. GPU0 gains must survive the matched strong
reference side-arms before being assigned exclusively to causal coordination.

If only one arrival regime benefits, state that regime rather than claiming
universal improvement. If the simple method matches or wins, retain that
finding and narrow the independent algorithm claim. If no strong comparison
improves, preserve NO-GO without weakening baselines or changing denominators.
This does not erase original C1/C2/C3 evidence or imply that packaging alone can
repair a missing system benefit. No result here guarantees DSN acceptance.

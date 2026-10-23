# CES v4 evidence critique and minimal next algorithm obligations

Scope: read-only inspection of frozen CES v4 source and actual collected evidence. No GPU calls, no manuscript edits, no frozen-result changes. All new calculations below are descriptive recomputations of existing observations, not counterfactual serving results.

## 1. Numerical audit

Evidence base: `experiments/causal_evidence_scheduling_20261023/`, executed source `e0aeae1b418644c378dde331c59b55fc5948b40f`, public archive `01f6e04aa88cf704c129242e6bbdaf42de159525`.

The user's batch prediction statistics are reproduced from `collected/evidence/formal_diagnosis_v1/BATCH_PREDICTION_VS_ACTUAL.csv`, filtering `validation-staggered-mixed-{ces,cost}-r{0,1,2}`.

| Method / selected operation | Physical batches | Mean predicted occupancy s | Mean actual occupancy s | Actual fallback calls | Total model calls |
|---|---:|---:|---:|---:|---:|
| Full CES / Verify | 22 | 0.442462969 | 0.757213963 | 14 | 36 |
| Full CES / Generate | 48 | 1.207604668 | 1.113868423 | 0 | 48 |
| Joint Cost-only / Verify | 23 | 0.594674683 | 0.501285809 | 7 | 30 |
| Joint Cost-only / Generate | 46 | 1.247897334 | 1.129790337 | 0 | 46 |

CES-selected Verify batches cost about 71.14% more than their mean forecast. These are different selected batch populations; this does not establish that changing only the policy on an identical physical batch changes its cost, nor prove that within-batch dependence is the cause.

One method mapping in the supplied assessment needs correction: synchronized Mixed Goodput 11.110 is **Cost threshold (`cost_gate`)**, not Joint Cost-only (`cost`). The latter is 10.034; Full CES is 11.255. The official paired Full CES / Joint Cost-only estimate is +4.40%, ordinary 95% interval [-5.26%, +17.63%], not a statistically established advantage.

## 2. The observed deadline failure is display, not commit

Recomputed from `collected/evidence/formal_v1_independent_audit_final/COMMON_FRONTIERS.csv`. Each row below pools the same 135 frontiers across three actual runs, 405 observations, not 405 independent acoustic sources. Counts are not audio-weighted Goodput or paired effect estimates.

| Arrival / method | Frontiers | Display <= 2 s | Commit <= 8 s | Both |
|---|---:|---:|---:|---:|
| sync / CES | 405 | 356 | 405 | 356 |
| sync / Joint Cost-only | 405 | 336 | 405 | 336 |
| sync / Fine | 405 | 340 | 405 | 340 |
| sync / Standard | 405 | 350 | 405 | 350 |
| staggered / CES | 405 | 221 | 405 | 221 |
| staggered / Joint Cost-only | 405 | 255 | 405 | 255 |
| staggered / Fine | 405 | 242 | 405 | 242 |
| staggered / Standard | 405 | 233 | 405 | 233 |

Thus every observed Goodput failure in these methods is associated with display lateness, while total run wall also affects the Goodput denominator. Reducing Authority work can still help display through parent availability or shared execution pacing, but it must be connected to the actual legal display critical path. Reducing an already-zero Commit deadline-miss count is not itself an explanation of improved Goodput.

## 3. Source-level defects in the *performance proxy*, not admission safety

### 3.1 No Consumer coverage state reaches the policy

`runtime/src/revtrace/ces_policy.py:10` defines Target without actual display/consumer acknowledgement state. In `ces_policy.py:116`, display cost is `max(0, authority_finish - target.ready - display_slo)`. This is not the defined first-valid Consumer display clock.

The actual audit at `audit_ces_final.py:127-132` selects the first Consumer observation whose `valid_visible_frontier >= f`; the commit clock is independently selected from durable installs. Consumer runtime state and real application timing are in `certified_display.py:120,135-153`; owner dispatch does not consume acknowledgements of this state.

Consequences: a frontier already displayed on time is penalized as a display miss if Authority finishes late; a frontier whose only private display will be causally invalid can be optimistically treated as timely merely because Authority finishes sooner. Neither inference is generally valid.

### 3.2 Descendant age is neither remaining GPU work nor saved progress

`ces_runtime.py:62-63` collects proposal jobs from the still-leased physical batches in `inflight`, then filters by larger end-window. `:80` sums elapsed enqueue age. A row can already have completed while its physical batch remains leased. Larger-window jobs are not automatically a proven reusable causal chain under the new Canonical P.

`ces_policy.py:120-123` adds the same conditional loss formula to both evidence modes. Issued-age and descendant count are not measured exclusive future GPU cost and cannot be added as if they were a credit for legal audio progress.

### 3.3 Cost model and candidate-history state deserve repair, not overclaim

`ces_policy.py:50-52` approximates the distribution of a Verify batch by independent marginal rejection probabilities and one `ceil(sum p)` fallback size. It is an approximation even if rows were independent: expectation of nonlinear fallback cost is not generally cost at expected failed count, and accepted row completion is distinct from physical drain.

The correct random object is at least the failed subset, original padded input shape, verification row-release times, fallback occupancy and final Batch-drained time. K alone may be insufficient when failed rows have different audio/prompt shapes or selective fallback retains the original padded width.

`ces_runtime.py:134` updates `last_reject` only after a Verify result. Direct Generation does not clear or rebind it to a particular Candidate/Parent incarnation. An old rejection can remain the feature for much later contexts. This is a diagnosable stale-feature hypothesis, not proof of the performance root cause. Prefer rejection observations keyed to branch generation / parent relation and explicit feature age.

### 3.4 Search is limited before the objective is evaluated

`ces_policy.py:62` truncates to the earliest-deadline `limit` targets. `:92-95` only enumerates prefixes sorted by predicted rejection. It can miss a useful batch subset ranked by legal progress value or Parent-unlock value. A more accurate cost model alone cannot repair an excluded decision.

### 3.5 Birth mismatch must remain a predictor, never an admission decision

Actual synchronized CES has candidate-ready counts 5, 5, 7; selected Verify counts 5, 5, 6; same-birth counts 0 in all three runs; all selected candidates passed. See `CELL_OPPORTUNITIES.csv`. A hard birth-match Verify gate would discard demonstrated legal correct-context verification opportunities.

Additional support recomputed from `TARGETS.csv` (three actual runs pooled):

| Arrival / method | Targets | Candidate ready | Selected Verify | Accepted | Rejected | Accepted despite birth mismatch |
|---|---:|---:|---:|---:|---:|---:|
| sync / CES | 405 | 17 | 16 | 16 | 0 | 16 |
| sync / Joint Cost-only | 405 | 10 | 8 | 8 | 0 | 7 |
| staggered / CES | 405 | 90 | 89 | 73 | 16 | 13 |
| staggered / Joint Cost-only | 405 | 79 | 73 | 65 | 8 | 43 |

This is selected-outcome support, not an unbiased acceptance-rate estimate for all currently possible candidates. For Generate-selected targets, the verification outcome remains unknown.

### 3.6 Conditional known-P support exists; descendant benefit is not yet established

Independently read all four arrival/method groups' `collected/canonical_witnesses/validation-{arrival}-mixed-{ces,cost}-r{0,1,2}.jsonl.gz`. For every accepted Verify, compare `job.candidate_state_tokens` (candidate birth-state projection) with `selected.state_tokens` (actual trusted target-parent projection). Equality holds for sync CES 16/16, sync Cost 8/8, staggered CES 73/73, staggered Cost 65/65.

This supports the conditional entry point for retaining private progress: an accepted candidate need not have the same declared birth parent to produce the same projection under the correct target parent. It does **not** demonstrate that a later private chain exists, is still deadline-feasible, or would be lost by Direct Generation. Full chain/Consumer event analysis requires the original raw events and private records; compact Canonical witnesses are insufficient.

An illustrative earlier pilot, `POLICY_SNAPSHOTS_v3.json`, has 60 recorded decisions, 539 target observations, 59 candidate-ready observations, all 59 preview-compatible, and only 7 observations with any descendant. These are potentially repeated observations of the same job, not seven independent opportunities, and not formal v4 prevalence. Do not extrapolate them into a predicted speedup.

## 4. Residual dual-deadline value: necessary bookkeeping

For each requested audio atom q, maintain the actual first legal-display observation and the durable commit observation independently. Acknowledged display success is monotonic historical credit even if the current view later retracts; the original metric is first legal visibility, not stability forever. Retraction remains a separate metric.

For an unfinished atom:

1. Display already succeeded, Commit pending: **retain remaining Commit value**, but award no second display credit.
2. Display unresolved and deadline still feasible: evaluate joint probability of legal display and commit meeting their separate deadlines.
3. Display deadline already missed: its own dual-deadline credit is zero, but it may be a necessary predecessor unlocking later released frontiers. Do not drop its computation.
4. Both succeeded: no new audio credit. Its state may still be a legal parent for later work.

An objective that removes every already-visible audio interval would be wrong: it loses the pending Commit obligation. An objective that uses current visible frontier alone would also be wrong after a legal view retracts.

## 5. Minimal next mechanism worth testing

Use one algorithm with separable layers, not three independently tuned algorithm names:

- Shared foundation: batch-shaped fallback/row-completion/drain cost distribution available identically to Cost-only and CES. Treat calibrated quantiles as risk estimates, not deterministic SLO guarantees.
- Core candidate: bounded receding-horizon scheduling over actual residual audio deadline value, current legal Canonical parent and already-released parent-dependent targets. Evaluate Verify acceptance, actual fallback and Direct Generation outcomes separately; execute only the first legal homogeneous physical batch and replan after an observed event.
- Conditional extension: Proposer dispatch reordering only if existing released jobs exhibit measured legal display opportunity. No preemption of a running batch, no free cancellation, all launched work charged. Candidate count is a diagnostic, not the reward.

For successful Verify, candidate Z is known and TrustedRender under the actual target Parent determines P exactly, conditional on verification accepting. This permits a conditional Exact-P compatibility check of an existing private chain. Direct Generation / fallback P is unknown before generation. Do not treat unknown P as certainly incompatible: Fine often selects the same legal P. Use empirically calibrated conditional outcomes or conservative ranges, and audit each actual history.

The strongest cheap comparator is not old Cost-only alone: provide the same risk model, first-display acknowledgement ledger, parent dependency information and an EDF/least-slack policy with a simple conditional-compatible-candidate gate. If the bounded rollout equals that policy, do not attribute independent value to sophisticated causal planning.

## 6. Interface and proof obligations

1. Add immutable Consumer application acknowledgements carrying owner incarnation, session, contract/version/frontier, observation time and event identity. Poll without blocking GPU dispatch; deduplicate. Make this identical-cost information available to every method.
2. Distinguish row finished, row owner-received, row consumed and physical batch drained. Do not use leased batch membership as pending row computation.
3. Every forecasted future Parent is a symbolic branch until actual trusted evidence resolves it; do not splice outputs from different fixed policies or CPU reinterpret old Z as new-parent generation.
4. Fixed fine=2 s/rho=1 and original C1/C2/C3 + A/B/C/D/D1/WAL remain invariant. Scheduling chooses an evidence path, not what is legal to install.
5. No starvation: zero-immediate-credit predecessors still make progress through a declared age/service rule or a bounded fallback service discipline. This does not establish unconditional liveness under overload.
6. Preserve all raw failures, actual energy, drain work, incomplete requests and quality costs.

## 7. What this audit does and does not justify

GO for a new *design and bounded hypothesis test*: the wrong performance proxy is established by source, and candidate opportunities/extra fallback costs are actually observed.

Not yet GO for a new DSN algorithm contribution: no same-input counterfactual GPU run establishes that the proposed decisions improve anything; no proof currently links the historical selected-batch forecast error to the full observed deficit. The 405 counts do not make three runs into 405 independent trials. v4's validation pool is now diagnostic development evidence; a future confirmatory claim needs a newly frozen independent source pool.

Stop or narrow the claim if the shared risk model alone accounts for improvements, if simple gate/least-slack matches the causal rollout, if the legal-frontier/parent changes rarely alter actual choices, or if no positive end-to-end opportunity remains after accounting for physical GPU work and Consumer/WAL latency.

## 8. Cross-review conclusion: conditional state is a scheduling input, not a new reuse mechanism

Reviewed peer `ALGORITHM_PROPOSAL.md` and sent direct objections to its author. The main design is appropriate, subject to the following distinctions.

### 8.1 What already exists

`runtime/src/revtrace/continuity_proof.py::eligible_chain` already checks exact projected state at the certified boundary, matching branch generation, contiguous private edges, and a frozen in-flight input consistent with the private tip. Successful V's target projection can supply a *conditional* input to this existing predicate. It does not invent a new way to retain a branch, authorize a suffix, or reclaim already-launched GPU work.

The full Standard Safe Async control can apply the same predicate. A future C2 increment must therefore be the **action-dependent legal-dependency scheduling policy**, not exclusive possession of conditional-chain retention. Conventional schedulers could also represent such conditional dependencies once supplied; no claim that ordinary components are incapable of expressing the policy is justified.

### 8.2 Required reduction / counterexample test

If there is no deadline-feasible private successor, or Direct and successful V produce the same compatible parent distribution on the relevant support, their successor-enablement reward must be identical. The proposed planner should then reduce to the shared risk/cost/deadline policy. Any remaining fixed causal bonus would be an artificial advantage.

The required references are: the same batch-risk model and actual coverage ledger with (a) EDF/least-slack, (b) a simple known-if-valid-P compatibility gate, and (c) the same bounded lookahead with evidence-dependent enablement removed. If only richer common costs or the acknowledgement ledger explain the gains, the result is a useful proxy/interface repair, not independently demonstrated causal planning value.

### 8.3 Goodput denominator and pending obligations

The peer's identity `(Q+dQ)/(T+dT)>Q/T iff dQ-(Q/T)dT>0` is correct for complete quantities. Its use in a rolling horizon is an approximation, not an optimality theorem. Plans must be compared over the same released-obligation cut, with all unfinished work charged to the eventual run. `dT` is the incremental wall-clock makespan; GPU0 and GPU1 overlapping lease durations must not be summed as wall time. The Goodput reference slope must be shared and frozen or past-only, never fitted using future outcomes.

The design correctly retains already-timely-display / pending-Commit credit, and gives a deadline-missed predecessor no direct audio credit while retaining its unlock value. Both are necessary to avoid rewarding a wrong surrogate again.

### 8.4 Evidence limit

Authority finish is a legitimate route to legal display through Canonical publication; it is not universally irrelevant to Display. Absence of actual Consumer state establishes a proxy mismatch, but does not prove that mismatch caused the 31.51% deficit. The next existing-log audit must count the decisions where actual already-paid display, live private deadlines or a necessary parent unlock would change the ordering. Only then is an implementation experiment justified.

The limited accepted-Verify P matches establish a conditional known-P entry point. They do not show the size of an *incremental* legal reuse opportunity relative to Direct. Formal raw private jobs/Consumer events and paid same-input Direct/Verify controls are still required for that distinction.

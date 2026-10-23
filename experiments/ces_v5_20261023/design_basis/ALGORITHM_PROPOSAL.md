# CES next-step algorithm proposal: evidence-conditioned legal-progress scheduling

Status: design only. No new GPU experiment, manuscript change, or claim of measured improvement.

Success has two levels. **System-level integration success** is a repeatable, legal end-to-end gain against strong fair references; a simple combination of established mechanisms can meet this standard and be a useful systems contribution. **Independent conditional-planning success** is the narrower claim that Parent-conditioned enablement adds value beyond the shared risk model and simple deadline/compatibility rules. Failure of the second claim does not invalidate the first. If shared-risk/EDF is the simplest effective design, retain and evaluate that design rather than add MPC solely to seek originality.

Baseline: CES v4 execution source `e0aeae1`, publicly archived in `01f6e04aa88cf704c129242e6bbdaf42de159525`. This proposal was derived by reading the actual policy, owner, live coordinator, continuity proof, trusted renderer and Consumer implementation. It preserves fine=2 s, rho=1, FP16 Proposer/GPU0, FP32 Authority/GPU1, all existing admission predicates, D1 and WAL semantics.

## 1. Decision

Do not implement three independent v5 systems in sequence. Make batch-risk calibration a shared reference capability, then test one narrow additional scheduling capability: **an evidence action changes which already existing private continuations can legally remain useful, and the scheduler must value only the residual deadline obligations those continuations can still satisfy**.

The minimal implementation should begin with actual Consumer coverage and GPU1 evidence choices, but must have an explicit opportunity gate. If observed GPU1-only choices cannot influence still-live Display deadlines, do not spend a full formal campaign on this restricted policy. Enable bounded joint next-batch selection on GPU0 and GPU1 only if existing event analysis shows real, nonpreemptive dispatch opportunities. This is a conditional expansion of one mechanism, not a new speculative-decoding system. A successful simple shared-risk or deadline policy is an acceptable endpoint; extra planning complexity must justify itself rather than act as an entry requirement.

This is more precise than adding a descendant penalty or changing its weight. It is also narrower than claiming a new general-purpose MPC algorithm: bounded rolling planning and deadline scheduling are established tools. The potentially new research object is **evidence-conditioned legal enablement**, and its independent net value is unproven.

## 2. What actual code establishes

`ces_policy.Target` has no actual Consumer first-valid coverage. V4 prices Display tardiness with a predicted Authority finish. That can penalize an Authority operation after a legal Provisional view has already satisfied the Display obligation, or fail to notice that a fast Authority row does not make a private successor consumable.

`_features()` counts jobs from physical `inflight` leases. A row that already completed can remain in the leased batch until `Batch-drained`, so descendant age/count is neither remaining GPU work nor independent future display value.

`projection_compatible` renders the *known* candidate token sequence under the *current target* Parent and compares the result with its recorded private projection. It is useful conditional information, but it is not a proof of generation under that Parent and is not a certificate.

Authority completion is not always an irrelevant Display proxy: its Canonical publication can itself supply the first legal display after render/WAL/Consumer delivery. The mismatch is therefore specific, not universal. V4 lacks actual already-paid Display status, release/deadline-sensitive successor enablement, and the correct delivery path. This source-level mismatch is not by itself proof of the cause of the observed 31.51% regression.

`eligible_chain()` already provides a strict state-edge mechanism: exact projected state at the certified boundary, contiguous private state edges, matching generation, and matching frozen in-flight input. No string concatenation, KV reuse or DAG grafting is required or permitted.

`RealtimeConsumer` currently appends observations to its own rows and supplies them at close. A scheduler that optimizes actual coverage needs an immutable acknowledgement interface, not direct unsynchronized reads or a retrospective label. This interface must be available, and charged, for every compared method.

An independent peer recomputation in this design round found that Fine, Standard, Joint Cost-only and CES each satisfy Commit<=8 s on all 405 independent-Mixed frontiers per arrival regime. The observed Goodput deficit there therefore comes from Display misses and/or run-wall cost, not Commit-deadline violations. This does not make Commit constraints removable: they remain part of the objective and can bind on other loads.

The same peer audit found target-render P equal to candidate-born P for every observed accepted Verify in these subsets: synchronous CES 16/16 and Cost-only 8/8; staggered CES 73/73 and Cost-only 65/65. This establishes a real conditional-compatible entry path. It does **not** establish that a future private chain was present, still deadline-feasible, or different from the Direct outcome. Only seven target-observations in an earlier pilot snapshot had descendants; those can repeat the same job. The bounded formal archive lacks the full event/Consumer/private chain records, so the actual causal-opportunity denominator must be recovered from the indexed 8 TB raw logs before any predicted gain is stated.

## 3. State: residual obligations rather than current frontier alone

For each released fine frontier q of session s, retain its newly covered audio weight a[s,q], release r[s,q], deadlines dD=r+2 and dC=r+8, and two independent observation states:

- D: never legally observed / first legally observed on time / first legally observed late;
- C: not durably admitted / durably admitted on time / durably admitted late.

The coverage ledger is monotone **with respect to the existing first-valid-observation metric**, even when the present visible view is later retracted. Retractions remain separately measured; this proposal does not silently redefine first-visible Goodput as stable-display Goodput.

Anti-gaming constraint: the owner must immediately process every completed legal receipt and every ready durable commit using the same processing rule as the references. It must not defer an already-ready commit/publication to allow an older Provisional display to earn first-visible credit. V/G selection can still change real completion order; therefore report non-retracted and commit-aligned coverage sensitivity, retractions, WER/CER and primary first-visible Goodput together. An advantage consisting only of earlier subsequently withdrawn text does not establish better dependable user experience.

The eventually earned credit is:

`credit[s,q] = a[s,q] * 1(first valid Consumer observation <= dD) * 1(durable commit <= dC)`.

Important cases:

1. D is already on time, C is pending: retain the full residual Commit value. Removing this frontier from the objective would be wrong.
2. D is already late or its deadline has passed unseen: its own dual-deadline credit cannot be recovered. It may still be a mandatory Canonical predecessor that unlocks later frontiers. Never skip a safety predecessor merely because its immediate credit is zero.
3. Both pending: use the joint completion event, not an unjustified product of marginal probabilities.
4. Both complete and credited: no second reward for re-display, retained descendants, or another receipt.

The state also records current Canonical Parent/Frontier, the actual immutable job graph, frozen inputs and branch generations, ready candidate Z, worker lease identity, row completion state, and physical batch-drain state. Only released audio and observed job/result information enter decisions.

## 4. The specific causal distinction: known-if-valid versus unknown output

For a ready candidate Z and target Parent P, TrustedRender gives a deterministic candidate target projection P_V = Phi(P,Z).

- If complete correct-context verification succeeds, Z is selected and P_V is the resulting projected state. Before execution, P_V is therefore **known conditional on success**, not already authorized.
- If verification fails, actual FP32 Fallback selects an as-yet unknown output and projected state.
- Direct FP32 Generation also selects an as-yet unknown output and projected state.

For each hypothetical result branch, define `Enabled(P_next)` as the already existing completed or frozen-input private continuations that satisfy the existing exact-state chain checks under P_next. A branch may retain a whole Provisional hypothesis, never turn it into Canonical text or splice an uncertified suffix.

The planner can compute `Enabled(P_V)` exactly conditional on V success, using existing chain predicates. For Direct/Fallback, it must use a shared empirically calibrated conditional distribution or conservative range. **Unknown does not mean incompatible.** Direct can generate exactly the same P_V, and may preserve the same private progress. Treating Direct as guaranteed invalidation would recreate the unfair v1 assumption.

Historical Direct compatibility is not an exact counterfactual constant: changing physical batch composition/order can change processed-input layout and actual output. Calibrate by actual observable layout, retain uncertainty, run paid same-input controls where necessary, and audit every policy's actual history and quality separately. A wider uncertainty interval on Direct must not become an automatic asymmetric penalty that manufactures a Verify win.

This uses the already implemented `eligible_chain`/Consumer compatibility mechanism; it is not a new retention, grafting or execution primitive. Complete Standard Safe Async must receive the same legal retention capability. The prospective increment is how a scheduler anticipates the evidence-conditioned state transition, not an exclusive ability to preserve that state.

This creates an action-dependent legal enablement problem: a result changes not only a task's finish time but which existing continuations remain usable. A conventional fixed-DAG deadline scheduler is a necessary strong reference; the proposed increment must survive a reference that already has the same costs, deadlines, lookahead and GPU0 ordering, but does not make evidence-branch-dependent enablement transitions.

### Degeneracy / stopping test

If Direct and V-success produce the same compatible next projection with probability one on the relevant opportunities, the causal enablement distinction disappears and this proposal reduces to shared cost/deadline scheduling. If a simple known-P compatibility gate matches the full planner, the stronger joint-planning claim is NO-GO, while an independently effective system integration remains a valid outcome. Naming the same policy differently cannot create an independent contribution; equally, established components do not make a genuinely effective integration valueless.

## 5. Shared physical risk model, not CES-only help

Build a joint empirical model of physical verify time, failed-row pattern, actual fallback subset/layout, fallback occupancy and early row delivery. Preserve batch-level correlation by resampling complete past physical-batch outcome blocks conditioned on observable row/batch features. Sparse bins must shrink to a declared conservative shared model; do not fit an unconstrained high-dimensional predictor to three validation repeats.

Possible features: operation, row count, candidate/prompt length, released audio extent, interval, current observed candidate readiness/birth relationship, time since previous observed reject, and frozen input-layout class. Injection labels, future Z, future accept/reject and unavailable Consumer outcomes are forbidden.

The model must predict both:

- row-result times: when a legal result could reach owner/render/WAL/Consumer;
- full physical occupancy: when the Worker lease is reusable.

An accepted Verify row can become usable before a peer's fallback finishes, but the occupied GPU cannot be dispatched again. A P90/P95 model is a risk estimate, not a formal SLO guarantee. Report conditional calibration, coverage, selection bias and realized tails. Give this complete model to Joint Cost-only, least-slack and compatibility-gate references.

## 6. Actions and bounded planning

### GPU1 actions

Choose one homogeneous ready batch of either Direct FP32 Generation or complete Correct-context Verification with paid Fallback. At most one pending Canonical transition per session; the actual legal Parent must exist before dispatch. A bounded wait can depend only on a real dispatched candidate and declared slack, never a fault label.

### GPU0 actions (conditional extension)

At physical idle/Batch-drained only, select among legal, released private next jobs. Value each job's ability to satisfy a still-live Display obligation and its ability to supply a candidate for an already relevant Authority target. Do not increase verification fraction at the expense of earlier valuable display, and do not claim that an issued nonpreemptive batch was cancelled. Fine, Standard and simple policies must receive the same GPU0 dispatch capabilities where applicable.

### Search

Start with at most 16 ready sessions, bounded beam width 8 and two subsequent physical dispatch events. Form candidate batches from small declared priority lists: earliest residual deadline, shortest predicted lease, current legal-frontier credit, and known-if-valid compatibility. Enumerate prefix sizes and homogeneous operations, retain the shared reference plan in the beam, and issue only the first currently legal operation on each idle device. Replan after actual row/Consumer/commit events, but no dispatch may violate a still-held physical lease.

Use at most 16 shared physical-outcome scenarios per plan initially. This is a bounded implementable heuristic, not an online optimum. With n=16, width b=8, depth h=2 and m=16 scenarios, a straightforward implementation is O(b*h*m*n^2) cheap state transitions plus feature/render cost. Actual host overhead must be measured; do not assume it is free or below a chosen millisecond threshold.

Future Parent values are not generated by the simulator. The second step may carry an abstract unknown-Parent state and a calibrated continuation value, but cannot construct or claim to execute a concrete child under an unobserved Parent. The execution layer always waits for the real commit.

## 7. Objective and derivation

For plan pi and outcome scenario omega, compute only newly earned credits, using the residual ledger above. Include a bounded continuation estimate for released successor obligations that are enabled by completing mandatory predecessors. Do not reward descendant counts, queued ages or already spent GPU work.

The complete serving metric is Q/T, so a local objective should not ignore its denominator. The exact algebra

`(Q + deltaQ)/(T + deltaT) > Q/T  iff  deltaQ - (Q/T)*deltaT > 0`

motivates a rolling average-reward score `E[deltaQ - g*deltaT]`, with g a shared frozen/reference or past-only measured Goodput estimate, rather than arbitrary weights 4 and 0.25. Compare plans over a declared common released-obligation cut, so one plan cannot win merely by leaving difficult work unprocessed. Terminal obligations remain in the final denominator; no request is dropped from accounting.

Here deltaT is the actual/predicted wall-clock makespan to that common cut, **not** the sum of overlapping GPU0/GPU1 lease durations. The ratio identity is an exact comparison of completed Q/T outcomes; it is not a proof that a bounded stochastic rolling planner is globally optimal.

A second lexicographic criterion can minimize risk-estimated complete lease work among plans with indistinguishable primary credit. Keep a mandatory age/fairness rule to prevent zero-credit predecessors from starving indefinitely. Neither the score nor its risk estimates may weaken acceptance or allow an uncertified commit.

The score is still an approximation because the horizon and unknown-Parent continuation are bounded. This limitation is testable. A pure residual-credit ratio can starve a zero-immediate-credit predecessor; a pure least-slack rule can spend GPU on an unrecoverable Display obligation; a pure cost rule can postpone the only parent that unlocks a live deadline. The purpose of the two-step branch-aware rollout is to distinguish these cases, not merely to use a more elaborate predictor.

## 8. Required executable safety properties

1. Evidence-mode independence: all Direct and Verify/Fallback results pass unchanged Parent/Frontier/Contract/D1/WAL checks.
2. Conditional enablement soundness: a predicted V-success branch is never consumed before actual verification, trusted rendering and durable state installation make it real.
3. Exact-chain reuse only: existing private hypotheses remain Provisional and pass the original frozen-input/branch-generation checks. No new-parent GPU generation is inferred from CPU rendering.
4. Row/lease separation: Row-complete can trigger owner work; only Batch-drained releases a GPU lease. Duplicate row/final receipts do not create duplicate installation or credit.
5. Residual-credit idempotence: epoch/session/frontier observations merge exactly once. Retraction does not alter the historical metric, and re-display cannot double count.
6. Fair forward progress: zero-immediate-credit Canonical predecessors are not discarded or starved; existing failure and finite-storage assumptions remain explicit.
7. Crash/recovery: decisions are ephemeral; WAL restores the same admitted history. Any uncommitted plan is recomputed from real restored Parent and live job identities rather than treated as a persisted authorization.

These prove safety conditional on the original trusted owner/worker/storage assumptions. They do not prove a performance advantage, SLO success, transcript completeness or a distribution-free tail bound.

## 9. Counterexamples the design must answer

### A. Display already paid, Commit pending

Frontier A has on-time legal display and a near Commit deadline; B has already missed Display. An objective that removes all displayed frontiers prefers B's apparent new coverage, losing A's valid residual credit. Correct residual bookkeeping retains A's Commit value.

### B. Zero-credit predecessor unlocks a live child

A has missed Display, but admitting A is the only legal route to B's released private/Authority work. Greedy positive-credit-only scheduling never admits A; the two-step planner must value the actual unlock without skipping A.

### C. Apparent preservation is not incremental

V-success matches the private root, but Direct also produces that same root under its actual execution. Charging Direct certain invalidation falsely manufactures a causal advantage. Shared outcome evidence must make their enablement values equal in this case.

More generally, if no still-deadline-feasible private continuation can be affected and G/V have the same compatible-Parent outcome distribution, the score must algebraically reduce to the shared risk/deadline rule plus ordinary physical-time differences. It must not retain a positive causal bonus from the mere existence or age of private jobs.

### D. Early row, occupied GPU

One verified row is ready at 0.2 s but its peer fallback drains at 1.0 s. Crediting the first row's legal application is correct; dispatching a new Authority batch at 0.2 s is not.

### E. No live opportunity

At all Authority decisions the Display obligations are either already met or already impossible, and changing next Parent cannot affect any released child before its deadline. GPU1-only branch planning has no immediate Display-credit opportunity. Stop that restricted route instead of rerunning it with different weights. A GPU0 extension requires its own real idle/dispatch-space evidence.

## 10. Experimental decision gates

1. Existing-data opportunity count: distinguish actual on-time Consumer coverage, still-live uncovered frontiers, mandatory Parent unlocks, and available GPU0/GPU1 dispatch boundaries. This is a necessary mechanism audit, not an offline serving result.
2. Same-input actual Direct/Verify controls on selected legal opportunity types: measure actual output/projection compatibility and whole physical costs. Operator probes are labelled and charged; not substituted for deployed runs.
3. CPU interleavings: all properties above, including stale acknowledgements, duplicate receipts, partial WAL success, restart and row-complete/lease races.
4. Bounded real GPU pilot with frozen safety and accounting; no manuscript changes.
5. Freeze models/parameters after using v4's prior validation pool as diagnosis/development. The next confirmatory source pool must be genuinely new to this optimization, not renamed held-out data.
6. Formal comparison: Fine, Strict, complete Standard, shared-risk Joint Cost-only, residual-credit EDF/least-slack, simple known-P compatibility gate, same-lookahead planner without evidence-conditioned enablement, and full planner. All share Row SDK, cost calibration, Consumer ack, applicable GPU0 ordering and resource budgets.
7. System success requires repeatable independent end-to-end gain over the strongest fair references, with unchanged safety and honest quality/cost accounting. A claim of additional Parent-conditioned C2 planning requires incremental gain beyond the simple gate and shared-risk planner. If the simple design supplies the system gain, retain it and explain the integration and measured causal mechanism; mark only the exclusive extra-planner claim NO-GO. A common executor upgrade cannot be assigned exclusively to CES, but measured combined-system improvement may still be reported as such.

## 11. Own assessment of novelty and fit

The potentially defensible increment is not “deadline-aware verification”, “risk-aware batching”, “MPC”, or “joint scheduling” in isolation. It is using the **known-if-verified projected state to predict legal continuation enablement**, combined with the exact residual obligations of independently consumed display and durable admission, under two nonpreemptive physical timelines.

That fits original C2 because it never changes what constitutes trusted state and never gives the Proposer state-write permission. It chooses when and how to obtain legal evidence so that actual legal progress, rather than guessed descendant preservation, becomes timely.

It remains possible that Direct and Verify are mostly equivalent in their compatible-parent outcomes, or that too few live candidates exist. In those cases no amount of naming or planning sophistication establishes independent algorithm value. The opportunity count, strong compatibility-gate reference and same-lookahead ablation are intended to expose exactly that possibility early.

The research priority is a strong, dependable system result, not a requirement that every component be unprecedented. Therefore the final selection rule is **keep the simplest design that achieves a repeatable fair system gain; add the conditional planner only if it earns its complexity**. The report should separately state what established mechanisms were combined, what implementation/coordination adaptation was necessary, what end-to-end benefit was measured, and whether a narrower independent scheduling increment was supported.

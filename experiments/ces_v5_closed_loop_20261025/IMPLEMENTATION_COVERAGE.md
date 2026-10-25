# CPU design -> frozen online implementation coverage

Checkpoint: 2026-10-25. Study: `REVTRACE-CES-V5-CLOSED-LOOP-20261025`.

This is an implementation/evidence map, not a performance victory report or a
manuscript revision. Source anchors below were read from the clean Runtime
checkout at **`e45c66475ba1173a98b49b8c9e62f3e8cb45b333`**. They are not
historical line numbers copied from the earlier failed 48-cell prototype.
Paths are relative to this study directory unless stated otherwise.
The outer stage controller and v2 audit tools are separately hashed stage
artifacts, not files claimed to be inside that Runtime commit. In particular,
the post-run v2 auditor correction is not a change to the executed GPU source.

## 1. Current evidence state

| Item | Verified state at this checkpoint | What it does not establish |
|---|---|---|
| Frozen online implementation | Implemented in the actual Owner/dispatch path; source clean at e45c664 | Global joint optimality or an SLO guarantee |
| CPU implementation gate | 367 selected core tests pass; final source reviewer separately ran 112 related tests | New GPU service performance; the counts are not summed as independent tests |
| Execution-profile audit | Actual old-48 extracted profiles pass independent arithmetic/fit audit; repeated builds byte-identical | New-source validation, unselected-action counterfactuals or future retention certainty |
| Real GPU safety smoke | Four requested n8 serving cells (Fine/Causal x synchronous/staggered, Mixed, one repeat) pass the complete v2 audit | Superiority over Fine, Standard, Strict, Cost or matched ablations |
| Paid real GPU Oracle controls | Two n4 Strict diagnostics (Clean/Mixed) pass v2 audit | Deployment throughput/energy; Oracle work is separate from serving cells |
| Formal comparison | **Not started** at this checkpoint; `PLAN.smoke.json` has `formal_approved_after_smoke=false` | No formal performance GO; no independent-source confirmation |

The successful local read-only evidence is
`operations/1792910659633175100.json` (return code 0). It records
`smoke_audit_v2/SUMMARY.json`: 4/4 cells, no failures, 165 actual model calls;
and `smoke_oracle_audit_v2/SUMMARY.json`: 2/2 cells, no failures, 152 actual
model calls including the diagnostic work. These call counts are intentionally
not combined into a serving-performance comparison. The original failed
auditor and GPU raw records remain preserved.

Both Causal smoke histories pass deterministic observed-input/planner replay:
staggered has 29 observations/29 physical service dispatches and synchronous
has 13/13. Each has 66 actual commit retirements, zero residual service records
and no execution permission created for a predicted future Parent. This shows
that the new path ran legally; it does not show that every optional forecast
was active, changed a decision or produced a benefit. Such activity and net
value must be counted from the formal traces.

The older `ACTIVE_STATE.json` fields may still describe a running/pending
checkpoint; this document does not silently edit that record. The successful
v2 audit outputs and their explicit cell denominators are the evidence for the
smoke status stated here.

## 2. Source/test/log map

Source abbreviations:

- **P** = `runtime/src/revtrace/ces_closed_loop.py`.
- **O** = `runtime/src/revtrace/ces_closed_loop_owner.py`.
- **R** = `runtime/src/revtrace/ces_runtime.py`.
- **V5** = `runtime/src/revtrace/ces_v5_policy.py`.
- **T** = `runtime/tests/test_closed_loop_independent.py`.
- **A** = `runtime/tests/test_ces_closed_loop.py`.
- **I** = `runtime/tests/test_ces_v5_integration.py`.

Line anchors refer only to the frozen e45c664 source. Test names, not only line
numbers, are included so the acceptance assertion remains identifiable.

### 2.1 Stable identity and service obligations across replanning

**Status: implemented online, with bounded empirical service protection.**

- P:24 `Identity` binds Session, epoch, actual Parent version/digest, audio
  start/end and contract. P:103 `ClosedLoopState`; P:130 `observe` retains an
  unchanged obligation even when temporarily ineligible; P:149 `admitted`
  retires it only after actual installation; P:163 `record_dispatch` increments
  deferrals only after a real issue, preserves the earlier suffix promise and
  rejects duplicate dispatch receipts.
- O:192 `_closed_build_contexts` constructs the actual current identity;
  O:254 `_closed_dispatched` records `actual_dispatch_perf`/`decision_token`;
  O:37 `_closed_installed` observes actual commit time. R:166 `_dispatch`
  invokes the callback **after** `worker.submit`; R:49 `_event` emits the real
  commit before retirement. Selection/polling alone is not counted as service.
- Tests: T:77 `test_old_common_cut_suffix_gets_real_service_within_bound`;
  T:145 `test_polling_without_actual_dispatch_cannot_create_deferrals`;
  T:158 identity replacement; T:185 infeasible promise disclosure;
  T:222 temporarily absent work; T:479 actual dispatch -> row receipt -> WAL
  retirement; T:504 pre-issue rejection; A:47 actual-enqueue aging.
- Trace: `closed-loop-observation.service_book`,
  `closed-loop-service-dispatch.{actual_dispatch_perf,decision_token,records}`,
  `closed-loop-service-retired.{installed_perf,retired,actual_durable_install_observed}`;
  decision fields `service_obligations`, `service_promises`, `forced_sids`,
  `promise_violation_mass`, `promise_tardy_seconds`.
- Boundary: default two actual competing dispatches is a finite-deferral rule,
  not a wall-clock completion theorem. `promise_quantile=.9` is an empirical
  outcome-row-envelope promise, not a hard 10% Commit-late budget. Overload or
  bad predictions remain visible. Service state supplies no write permission
  and is not a newly claimed durable timing promise across process restart.

### 2.2 Released-successor deadline backpropagation and dependency planning

**Status: implemented online; maximum two released successor layers.**

- O:192 builds successors only when their actual audio release is <= the
  decision clock, with cumulative Generation-service **and delivery** estimates.
  P:352 `effective_deadlines` propagates useful successor deadlines backward.
  P:370 `_candidate_plans` uses inherited priorities in the actual candidate
  family; P:459 `_expanded` includes paid future Generation steps; P:700
  `choose_closed_loop` returns only the first currently executable batch.
- Tests: T:249 `test_released_successor_value_changes_real_first_parent_batch`
  changes the actual first Session set, not merely a log field; T:272 rejects
  unreleased audio; T:236 symbolic successor has no Job/token/certificate;
  T:562 shadow planning leaves actual objects and WAL unchanged; A:169
  cumulative-service backpropagation; A:234 reserved-progress isolation.
- Trace: `closed-loop-observation.contexts[*].released_successors` and complete
  `target_context`; `ces-decision.{effective_deadlines,symbolic_successors,
  symbolic_steps,successor_reward_used,symbolic_service_promises}`.
- Boundary: future Parent values remain unknown. A later real Job is constructed
  from the newly installed actual Canonical state, never from a symbolic model
  node. The two-layer horizon is a declared approximation, not an unbounded
  dependency DAG, grafting protocol or all-future-arrival optimizer.

### 2.3 Actual Consumer residual credit and finite-prefix Q/T

**Status: implemented online for all baseline/closed-loop information paths.**

- R:58 `_drain_consumer_acks` accepts immutable actual Consumer observations;
  R:88 `_display_status` distinguishes observed on-time Display from irreversible
  first-Display expiry. O:37 records actual committed transitions for every CES
  mode; O:48 `_closed_observed_credit` joins real ACKs with actual Commit time.
  P:568 `_evaluate` computes scenario-level finite-prefix ratios before
  averaging, using actual prefix Q/T and the paid common continuation.
- Tests: I:36 publication is not Consumer credit; I:62 future ACK cannot be read
  into an earlier decision; T:98 D-met retains pending C credit; T:67 preserves
  the real release+2/release+8 Commit-first-loss counterexample; T:402 retains
  observed Q/T; T:825 verifies actual Fine/Standard/Cost commit+ACK Q accumulation
  without fictitious closed-loop service events.
- Trace: `ces-consumer-ack`, `closed-loop-observation.{observed_credit_audio,
  elapsed_seconds}`, decision `finite_prefix_goodput`, `expected_current_credit_audio`,
  `expected_successor_credit_audio`, `expected_cut_wall_seconds`.
- Boundary: the primary atom is unchanged:
  `audio * I(first legal Consumer D <= release+2) * I(durable C <= release+8)`.
  Later Commit does not backfill a missed D. First visibility, retraction and
  stable-until-certified visibility are separately reported. A finite-prefix
  prediction is neither an exact full-run objective nor an online-optimality
  result.

### 2.4 Private/Canonical two-path forecasting through actual ancestry

**Status: implemented online; conditional empirical prediction, not permission.**

- O:98 forecasts only a real enqueued, not-yet-received Private job, not a
  cached completed node. O:138 validates the actual root and frozen causal
  edges. P:239 `_ancestor_survival_factor` and P:263
  `_private_survival_probability` integrate survival through each possible
  invalidating ancestor; P:568 combines first legal Private/Canonical paths
  without double-counting audio. Row CDFs, not mean ETAs, enter deadlines.
- Tests: T:313 parallel GPU paths use earliest Display/max wall, not summed
  durations; T:326 no duplicate credit; T:337 half-mass CDF; T:350 unproven
  Private path cannot earn credit; T:589 retained immutable older birth/audio
  root; T:623 cached completion is not future publication. A:117 prevents
  resetting survival at each ancestor; A:134 rejects an envelope-derived free
  interval; A:145 preserves accepted-early/fallback-late joint row structure.
- Trace: `target_context.private_path_currently_legal`,
  `private_delay_distribution`, `private_delay_includes_delivery`,
  `private_path` audit metadata, `expected_private_additional_credit_audio`,
  `conditional_private_prediction_enabled`, `private_authority_joint_model`,
  `private_ancestor_survival_model`.
- Boundary: Private and Authority forecasts use independence approximations
  when matched joint data are absent; successive transition-survival factors
  are likewise a declared model. Unknown outputs and retractions cannot be
  represented as known reusable state. Full actual history still passes
  separate D1/admission/WAL/Consumer checks.

### 2.5 Conditional Verify-success compatibility; Direct/Fallback remain distinct

**Status: implemented online; identifiable first transition only.**

- O:157 `_conditional_chain` trusted-renders the actually available candidate Z
  under the actual current Parent/chunk and checks `eligible_chain` on a shadow
  Session. O:177 obtains separate selected-history Direct/Fallback estimates.
  O:223-227 binds the first successor to the current transition model; deeper
  successors have `inherit_current_transition_model=False` and None rates.
  P:529/P:549 distinguish known-if-verified, unknown Direct and paid Fallback.
- Tests: T:360 root Verify equality cannot survive an unknown generated
  grandparent; T:381 uncalibrated unknown is not false with a Verify bonus;
  T:742 first-layer rates differ and depth-two does not inherit; A:104 keeps
  Direct/Fallback distinct. `test_audit_closed_v2.py:49` replays all four modes
  with released backlog; its six mutations reject false first flags, changed
  rates, deep inheritance and the legacy collapsed rate.
- Trace: `chain_preview.{verify_success_projection_digest,
  verify_success_chain_eligible,verify_success_chain_proof,condition}`,
  `direct_root_model`, `fallback_root_model`, and each successor's explicit
  rate/identity fields. A forecast says `requires_actual_parent`; it never
  contains a real future token sequence, Job or certificate.
- Boundary: first-layer inheritance here concerns the transition being
  predicted, **not** inherited execution authority. Sparse estimates stay None,
  not zero. Actual root equality in selected historical operations is not a
  full-chain-retention or same-target counterfactual guarantee. The v2 auditor
  repairs a false-positive in the old first-layer flag check; original audit
  files and failed output remain intact.

### 2.6 Actual row-completion distributions, observed clocks and risk costs

**Status: implemented online with disclosed finite-support approximations.**

- O:58 records received Worker-start telemetry. O:67 uses supported n/audio ->
  n -> global CDF backoff, requiring eight rows **and** eight physical batches.
  O:98 conditions remaining-to-Consumer delay on observed start/no received
  result; unknown start uses age zero, not elapsed enqueue time. Delivery is
  included once. Upper-endpoint bins preserve all mass in at most 32 bins.
  V5:136 `predict_batch` keeps physical failed-row-count scenarios and full
  paid Fallback; P:478/P:513 bound and audit scenario quadrature.
- Tests: T:654 support/backoff; T:684 observed-start clock and completed-terminal
  still awaiting Consumer; T:710 33/64/100/101/1000-point CDF mass/bound checks;
  T:729 delivery exactly once; `runtime/tests/test_ces_v5_policy.py:98` partial accepted row does not
  free the lease; :118 joint failed-count scenarios; :130 sparse backoff.
- Trace: `private_path.{age_clock,actual_lease_age_s,row_CDF_size_bucket,
  survival_conditioned_samples,censored_beyond_empirical_support,
  CDF_upper_endpoint_bins,CDF_one_sided_error_bound,private_delay_includes_delivery}`;
  decision `scenario_model`, `scenario_combinations`, `scenario_marginal_audit`
  (per-step marginal TV/fallback-mass/tail omissions), and physical accounting.
- Boundary: row identity is exchangeable within the selected empirical class.
  The CDF compression error bound is one-sided `(ceil(N/32)-1)/N` for the
  conditioned N samples, not a prediction-coverage or deadline guarantee.
  Original calibration compression, sparse-class transfer and absent temporal
  correlations are separate limitations. Raw profile rows/outliers remain.

### 2.7 GPU1 physical subbatches and GPU0 paid-prefix choices

**Status: real action selection implemented; no full joint optimum.**

- V5:414 `_plans` supplies homogeneous G/G, V/V and mixed V/G or G/V current-target
  partitions; P:370 adds inherited/promise priorities with a bounded beam.
  R:166 dispatches only one real first batch and never frees a Worker on a
  partial row. O:282 `_closed_proposal_selection` compares GPU0 prefixes while
  paying the entire remaining current Proposer cut; O:260 values candidate
  readiness only behind an **actual** occupied Authority lease.
- Tests: T:764 Fine/Standard/Cost/Service/Causal all price the same full GPU0
  cut; T:786 Cost/Service/Reserved/Inherited/Causal can use the same candidate
  capability, with zero value for idle Authority/already-issued target and no
  created future Job. `test_row_executor_protocol.py:25/28` and
  `test_row_lifecycle_transport.py:18/20` keep row completion separate from
  physical drain. T:296/T:562 preserve real inputs during forecast.
- Trace: `closed-loop-proposer-choice.{common_cut_sids,selected_sids,candidates,
  predicted_paid_lease_s,predicted_full_cut_wall_s,predicted_evidence_value,
  authority_occupied_lease_observed,actual_subset_differs}`;
  `ces-decision.{operation,sids,plan}`; `batch-dispatched`, immutable row
  receipts and `worker_batch_accounting.jsonl` physical phases/drain.
- Boundary: choices are bounded non-preemptive prefixes/homogeneous batches.
  No KV reuse, token preemption, heterogeneous free batch or physical
  cancellation is introduced. Different actual layouts can change outputs;
  each Canonical history is audited independently. Selecting a subset is a
  real action, but the existence of that action alone does not show a benefit.

### 2.8 Shared strong references and algorithm ablations

**Status: common capabilities implemented and scope-enforced; formal benefit pending.**

- R:166 keeps native Fine/complete Standard independent Generation, Strict
  correct-context Verify with actual paid Fallback, legacy Cost and new four
  closed-loop modes. All share two GPU roles, Row-complete transport, actual
  Consumer, D1, admission checks, WAL and paid physical work. Fine is not forced
  to run an unused expensive forecast merely to inflate its baseline overhead.
- P:700 separates `service_cost` (wall-first), `reserved_progress` (same
  finite-prefix current-credit objective without successor/Private reward),
  `inherit` (released successors) and `causal` (two legal display paths).
  Comparing only service_cost vs inherit would conflate objective change with
  successor value; reserved_progress is the required matched control.
- `run_closed_stage.py:126` enforces equal main GPU0 policy; side arms must
  match their own main input/config and change only the declared policy.
  `test_controller_audit.py:209/216/233` tests shared/Cost capabilities and
  matched side arms; A:217/226/234 tests degeneration/isolation; T:825 checks
  that baseline actual Q is not silently suppressed by missing commit routing.
- Trace: frozen `PLAN*.json`, each actual `config.json`/`provenance.json`, method
  and `proposer_policy`, actual `CES_host_cost`, physical model/Fallback/old
  work, D/C quantiles, WER/CER, two-card energy, unfinished work and source scope.
- Boundary: the four-cell smoke covers Fine/Causal only; Strict Oracles are
  not a measured competing deployment. Formal template main/side-arm cells
  are proposals until separately frozen and executed. No claim of beating
  Standard, Cost, reserved_progress or the best legal fixed policy exists yet.

## 3. Fixed search limits and nonclaims

`CLOSED_CONFIG.json` freezes two released successor layers, eight candidate
current-cut plans and at most sixteen scenario combinations per evaluation.
Two current/successor interleavings may be evaluated for a retained plan, so
eight plans does not imply exactly eight total forecast evaluations. Candidate
prefiltering is heuristic, not an admissible global-optimality pruning theorem.
Every evaluated continuation still pays the declared common cut. Actual Host
planning/feature costs are charged by the serving clock.

Inside the scenario budget, products are exact only within the declared
empirical model. Larger products use fixed-seed weighted stratified quadrature
with reported marginal approximation error. The shared P90-style promise and
estimated service/compatibility values may be wrong; those errors may select a
bad action but cannot authorize a bad state transition.

Not implemented/claimed: full GPU0/GPU1 joint or infinite-horizon optimality,
an unknown-token Oracle, a universal deadline/liveness guarantee, durable timing
reservations across crashes, DAG Grafting, Elastic rho, V2 coarse-candidate
replacement, KV-reuse Fallback, a new model/decoding algorithm, or performance
superiority inferred from CPU fixtures or one-repeat smoke.

## 4. Unchanged safety boundary and reproducible evidence layers

R:13 `validate_evidence`, actual `LiveQwenScheduler` admission/D1/WAL paths,
`row_lifecycle.py:70`/`row_delivery_executor.py:25` retain the original predicates.
T:416 actual ACK/D1/WAL resume; T:436 stale Parent; T:461 failed fsync; T:523
valid group prefix/torn-tail recovery; row transport duplicate/wrong-binding
tests remain executable. A torn-tail CPU fixture is not a new real GPU crash
or power-loss experiment. Original C1/C3 findings are preserved, not newly
re-proved by this scheduling smoke.

CPU commands for just the new mechanism/audit coverage, using fresh temporary
directories, are:

```powershell
cd D:\VLA_QWEN\RevTrace\experiments\ces_v5_closed_loop_20261025\runtime
python -m pytest tests/test_ces_closed_loop.py tests/test_closed_loop_independent.py -q --basetemp ../cpu_tmp_new_coverage_check
cd ..
python -m pytest test_audit_closed_v2.py test_controller_audit.py -q --basetemp cpu_tmp_new_audit_coverage_check
```

Existing records: `INDEPENDENT_CPU_GATE.json` / v7 XML (367 selected core tests),
`FINAL_RUNTIME_REVIEW_FINAL.json` (112 related tests on clean e45c664),
`INDEPENDENT_PROFILE_AUDIT_v1.json` (old-48 profile arithmetic only), and
`INDEPENDENT_AUDIT_V2_REVIEW.xml` (44 CPU audit/controller tests). They cover
different scopes and must not be summed into a fictitious GPU trial count.

Complete v2 GPU audits retain actual certificates, WAL, trusted rendering,
immutable receipts, lease separation, Consumer/ACK replay, quality/energy
denominators and every requested failed/missing cell. They do not run new GPU
models. The first-layer audit correction changes no frozen Runtime or raw GPU
result. Formal performance GO remains **PENDING**, including whether simple
shared service protection already explains any observed benefit.

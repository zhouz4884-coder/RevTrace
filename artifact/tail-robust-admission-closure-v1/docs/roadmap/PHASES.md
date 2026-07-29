# RevTrace phase roadmap

## Phase 0 — frozen discovery

Purpose: establish the physical opportunity and classify failed exactness.

Completed evidence:

- RevBatch throughput and exact-revision gate;
- same-input and repeated-run controls;
- BF16, FP16, and FP32 precision interventions;
- encoder/decoder backend interventions;
- state-projection accounting;
- selective canonical oracle.

Status: `FROZEN`.

## Phase 1 — deployed system baseline

Purpose: turn the mechanism oracle into a real two-GPU service.

Completed:

- versioned revision tickets and atomic state-entry ledger;
- GPU 0 batched proposer and GPU 1 singleton verifier;
- terminal verification and safe work stealing;
- natural live trace and flip-rich safety stress;
- hash-audited artifact and regression tests.

Status: `PASS`, with deterministic certificate unresolved.

## Phase 2 — risk and tail contract

Primary system name: **RevOCC** — risk-limiting optimistic state transactions.

Gate S1:

- fixed-probability, anytime-valid shadow-audit confidence sequence;
- sudden-drift and optional-stopping simulation;
- natural run with at least 30,000 eligible state entries per model;
- at least 500 randomized base audits per model;
- target risk budget `delta=0.5%`, confidence `1-alpha=95%`;
- adaptive extra audits excluded from the formal certificate.

Gate S2:

- terminal canonical reservation with concurrent discarded proposer work;
- deadline miss below 1%;
- wall-clock speedup at least 4x;
- GPU-normalized speedup at least 2x;
- no observed output, state-projection, stale, or replayed violations.

Current status:

- S1 simulation: `PASS` over 2,500 simulated trajectories;
- S1 natural shadow audit: `PASS` for both active policies;
- S1 frozen repair boundary: the 1.7B `tau=0.05` policy failed an independent
  c16 audit; the preregistered `tau=0.10` replacement passed on a fresh seed;
- S2 deployed terminal-tail gate: `PASS` for both Qwen3-ASR sizes with five
  runs per active policy;
- deterministic intermediate certificate: `UNRESOLVED`.

## Phase 3A — adaptive state certification

Primary controller name: **RevControl**.

Frozen design:

- every certificate is bound to a complete arithmetic/revision contract
  fingerprint;
- configuration changes start a fresh fail-closed epoch;
- a preregistered monotone policy family receives simultaneous anytime-valid
  confidence sequences;
- risk and verifier-queue prices select a policy inside the certified
  envelope;
- caught real failures are permanent policy exclusions for that exact
  contract;
- independent base audits alone support the formal certificate;
- idle VOI audits remain diagnostic unless a separate propensity design is
  preregistered.

Gate sequence:

`0.6B/c16 -> 0.6B/c64 -> 1.7B/c16 -> fresh 0.6B/c16 epoch`.

Status: `PASS`.

Observed controller trajectory:

`0.6B/c16 tau=0.05 -> 0.6B/c64 tau=0.20 -> 1.7B/c16 tau=0.10 -> fresh 0.6B/c16 tau=0.05`.

The c64 transition is fail closed for serving performance because its terminal
canonical shape is not independently certified. Across the three deployed
c16 epochs, minimum wall speedup is `4.932x`, minimum GPU-normalized speedup is
`2.466x`, and deadline/state/stale-result violations are all zero.

## Phase 3B — dual-channel idle auditing

Gate P3-B compares:

- fixed-probability base audits only;
- base plus unprioritized idle audits;
- base plus margin-only idle audits;
- base plus value-of-information idle audits.

The formal anytime-valid certificate continues to use independent base-audit
coins only.  Opportunistic audits are cancellable, lower priority than
terminal, state-blocking, and base-audit work, and do not enter the formal
confidence sequence unless a separately preregistered known-propensity design
is used.

Primary metrics:

- wall time and verifier GPU-seconds required to reach upper risk below 0.5%;
- drift-detection delay;
- deadline misses and SLO goodput;
- state errors discovered per verifier GPU-second.

Status:

`PHASE3B_BOUNDED_DIAGNOSTIC_PASS_VOI_AND_LIVE_SLO_UNRESOLVED`.

Across 2,000 retrospective trials, margin-prioritized idle audits increased
detection probability from `0.644` to `1.000` and reduced median verifier
requests from `283` to `226`. VOI matched detection but used three more median
requests. The measured pool contains only one unique failing job, so neither a
general VOI advantage nor live cancellability/SLO preservation is claimed.

## Phase 3C — state-pollution dynamics

Gate S3:

- at least 50 legal execution-shape flip pairs per architecture;
- fixed-future-audio canonical replay;
- Revision Impulse Response curves;
- RAF, reconvergence time, terminal difference, and Numerical State Exposure;
- natural and stress evidence reported separately;
- right-censored survival estimates rather than unsupported infinite
  half-life claims.

For legal state-entry flip pairs, report the pollution survival function,
pollution half-life, Revision Amplification Factor, terminal-difference rate,
and Numerical State Exposure.

Status:

`PHASE3C_MECHANISM_CONFIRMED_POPULATION_GATE_NOT_MET`.

After deduplicating replicated executions and separating natural,
waveform-stress, and independent-speech stress evidence, the 0.6B and 1.7B
models provide `19` and `15` distinct legal state pairs, respectively. This
is below the preregistered `50` pairs per model. The mechanism-level RIR
measurements are retained, but the population-generalization claim is
excluded.

## Phase 3D — second-architecture boundary

The second-architecture gate requires another revision architecture to
demonstrate:

1. execution environment can create a state difference;
2. that difference can enter a future revision;
3. RevOCC prevents or bounds the propagation.

Voxtral Realtime is the first candidate. A negative RAF result is acceptable if
it establishes a principled boundary where certification is unnecessary.

Status:

`PHASE3D_SECOND_ARCHITECTURE_BOUNDARY_PASS`.

Voxtral Mini 4B Realtime completed 10 growing-prefix revisions and 120
execution rows with zero observed singleton-repeat, cross-shape, or
replicated-row mismatch. Its decoded text is not re-injected into the next
transition, so it establishes a causal append-only boundary rather than a
second feedback-pollution architecture.

## Supporting baseline — preventive deterministic execution

Gate S5:

- repair or bypass the Qwen3-ASR incompatibility in vLLM batch invariance;
- treat it as a preventive-determinism baseline, not the main novelty;
- compare quality, capacity, wall performance, and GPU-normalized performance
  against optimistic state certification.

## Phase 4A — certified risk window

Status:

`PHASE4A_RISK_WINDOW_REPLAY_PASS_LIVE_SWITCH_UNRESOLVED`.

The controller uses observed margin order statistics rather than a manual
threshold ladder. Every contract switch invalidates the prior epoch and sets
the fast-path window to zero. Calibration and validation are temporally split:
validation failures cannot retroactively change the boundary. The frozen
c16-to-c64-to-c16 replay selects `0.0625 -> 0.109375 -> 0.0625` and keeps each
held-out upper risk bound below 0.5%. This remains a replay, not a live c64
performance result.

## Phase 4B — Whisper previous-text feedback intervention

Status:

`PHASE4B_FEEDBACK_CAUSAL_GATE_PASS`.

Whisper tiny.en and base.en each process 100 disjoint 90-second streams. The
same checkpoints and fixed future audio are replayed with previous-text
feedback ON and OFF. Twenty-one distinct legal execution-shape state pairs are
found; eight propagate under feedback ON and none propagate under feedback
OFF. No application-catastrophe event is observed, so hallucination-loop
prevention remains outside the claim.

## Phase 4C — SlackGuard physical gate

Status:

`PHASE4C_FULL_REQUEST_QUANTUM_NO_GO_FINE_GRAINED_UNRESOLVED`.

The measured full audit request takes 309.9 ms versus a 27.5 ms two-percent P99
intrusion budget. Because CUDA priority is not running-kernel preemption, a
full-request live audit cannot meet the intended contract. Fine-grained
cancellable checkpoints are the only legal repair.

## Phase 4D — diversity-aware active mining

Status:

`PHASE4D_ACTIVE_MINING_BUDGET_COMPLETE_TARGET_NOT_MET`.

Each model screens 500 independent LibriSpeech candidates and probes each at
most once. Pair yield improves by `2.78x` and `2.54x` over the previous natural
search, but only 8 and 5 pairs are found. The 50-pair population claim remains
excluded. The observed pairs retain high persistent-contamination mass, which
is reported as targeted mechanism damage rather than production prevalence.

## Post-Phase-4 paper and artifact freeze

- freeze the introduction claim spine and state-transaction formalization;
- synchronize risk proofs, system diagrams, experiment protocols, and the
  failure ledger;
- keep deterministic, production-error-rate, and cross-architecture claims
  outside the paper unless their corresponding gates pass;
- build and hash-audit the complete submission artifact.

## Phase 5A — live adaptive risk window

Status:

`PHASE5A_LIVE_ADAPTIVE_CONTROL_FAIL`.

The persistent two-GPU service executes c16 -> c64 -> c16 with a fresh
contract epoch at each switch. It learns thresholds from new evidence rather
than using a manual ladder. All three statistical upper bounds are below 0.5%,
but fresh canonical replay observes rare output/state violations. The c64
stage also exceeds the two-second RTX 3090 service region. This is retained as
the measured boundary between a risk-limited certificate and deterministic
state-entry exactness.

## Phase 5B — Whisper protected intervention

Status:

`PHASE5B_PROTECTION_PASS_PERFORMANCE_BOUNDARY`.

Both Whisper checkpoints protect every known Phase 4 feedback pair by
fail-closing feedback-bearing state entries to singleton canonical execution.
Feedback OFF uses distinct batched audio windows, performs zero state
certifications, and records local output disagreement separately from state
propagation. Whisper supplies cross-family causal/mechanism evidence rather
than a second main throughput result.

## Phase 5C — workload and energy frontier

Status:

`PHASE5C_WORKLOAD_FRONTIER_COMPLETE_WITH_BOUNDARIES`.

Eight live two-GPU cells cover two model sizes, concurrency 8/16/32,
30/60/120-second streams, synchronous/Poisson/burst arrivals, and
English/Chinese/mixed inputs. Seven cells have zero observed state violation;
one unseen c32/Chinese/burst contract defeats the frozen c16 threshold. Two
cells meet the two-second deadline without misses. Safety and service-capacity
failures remain separate.

## Phase 5D — live release-aware audit packing

Status:

`PHASE5D_LIVE_SLACK_PACKING_NO_GO`.

The live one-GPU gate preserves mandatory outputs, has zero deadline misses,
and substantially improves first audit completion, but mandatory P99 grows by
2.35%, above the frozen 2% limit. Full-request slack packing is stopped rather
than repaired with post-hoc guard tuning.

## Phase 5E — consequential state-pair corpus

Status:

`PHASE5E_CONSEQUENTIAL_CORPUS_COMPLETE`.

The deduplicated corpus contains 72 state pairs across Qwen3-ASR and Whisper,
with natural, stress, and targeted sources kept distinct. It is a mechanism
and damage-stress artifact, not a production prevalence estimator.

## Phase 6A — asymmetric contract evidence

Purpose:

- separate strict execution identity, execution-shape coverage, population
  risk, and service capacity;
- restore a positive certificate only for an exact contract and only after
  renewal canaries;
- retain each observed failure inside its recorded applicability cone;
- quarantine an unseen contract without invalidating certified lanes;
- fence state commits by session, contract, and policy epochs.

The semantic gate uses the real Phase 5 c32 counterexample and fails closed for
unsupported execution shapes. A covering positive certificate may warm-start
an unseen population, but it cannot mark that population certified.

## Phase 6B — complete contract scoping

The frozen repair reruns the exact
`Qwen3-ASR-0.6B/c32/120-second/burst/Chinese` cell. It must not read a c16
positive certificate, must quarantine the first contract observations, must
verify the known margin-0.109375 counterexample, and must preserve zero
observed state-projection violations in the full canonical audit. Safety and
the measured two-second capacity boundary are reported separately.

## Phase 6C — joint risk-SLO admission

The historical c64 workload is an offered load, not an admissible service
contract. Admission requires both the statistical risk budget and guarded P99
capacity. When c64 fails the capacity condition, the runtime reshapes active
service to a measured feasible concurrency and backpressures or queues the
remainder; overload cannot authorize an uncertified commit.

## Phase 6D — feasible live adaptation

The persistent two-GPU process switches between two service-feasible c16
populations and then returns to the original one. New populations learn in
separate quarantine lanes. Exact return may restore the old certificate only
after canary renewal; no positive certificate crosses populations.

## Phase 6E — submission repair freeze

The finalizer emits compact summaries, source-trace hashes, paper-facing tables,
claim boundaries, regression tests, and a hash-audited artifact. Large live
traces stay on the designated experiment disk. Phase 6 ends mechanism
expansion and begins the first submission freeze.

## Final Evaluation Closure

Status:

`FINAL_EVALUATION_CLOSURE_PASS`.

Four submission-facing evidence gaps are closed without adding a new mechanism
phase:

1. independent LibriSpeech and AISHELL quality evaluation reports WER/CER,
   terminal exactness, partial churn, paired bootstrap intervals, and
   catastrophic-outlier counts for four execution modes and two models;
2. one persistent c14 runtime separates cold certification, replay-audit
   adaptation, and independently seeded steady validation without restarting
   the model or controller;
3. Phase 2 FP16-b16, Phase 6 FP32-b16, Phase 7 FP16-b16, and Phase 7.1
   FP16-b14 authoritative paths remain distinct versioned contracts;
4. the final risk/SLO/performance table separates same-task Pareto points,
   capacity-only observations, and infeasible or statistically uncertified
   cells.

The first steady-state attempt is retained as a mechanism failure: post-stage
audit roots were recorded but not assimilated into the dynamic failure floor.
The repaired protocol promotes only the first unverified root per session in a
declared adaptation split and evaluates the next independently seeded split.
Verified canonical replay differences remain a repeatability boundary and are
not counted as online selection-authority violations.

## Tail-robust admission closure

Status:

`TAIL_ROBUST_C12_PASS_WITH_120S_AGE_BOUNDARY`

The historical c14 point stays outside the admission envelope. The fixed c12
reshape passes five-process, round-clustered 30-second admission with maximum
seed P99 1.877 s, cross-seed U95 1.868 s, zero miss rounds, and risk upper
bound 0.499706%. A complete 120-second profile fails the duration extension
and is retained as an operating boundary rather than repaired post hoc.

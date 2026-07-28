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

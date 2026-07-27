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

## Phase 3B — state amplification

Gate S3:

- at least 50 legal execution-shape flip pairs per architecture;
- fixed-future-audio canonical replay;
- Revision Impulse Response curves;
- RAF, reconvergence time, terminal difference, and Numerical State Exposure;
- natural and stress evidence reported separately.

## Phase 4 — second architecture

Gate S4 requires another revision architecture to demonstrate:

1. execution environment can create a state difference;
2. that difference can enter a future revision;
3. RevOCC prevents or bounds the propagation.

Voxtral Realtime is the first candidate. A negative RAF result is acceptable if
it establishes a principled boundary where certification is unnecessary.

## Phase 5 — preventive deterministic baseline

Gate S5:

- repair or bypass the Qwen3-ASR incompatibility in vLLM batch invariance;
- treat it as a preventive-determinism baseline, not the main novelty;
- compare quality, capacity, wall performance, and GPU-normalized performance
  against optimistic state certification.

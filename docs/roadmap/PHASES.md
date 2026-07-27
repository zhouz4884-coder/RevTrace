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

- stratified anytime-valid shadow-audit simulation;
- natural run with at least 30,000 state entries;
- at least 500 randomized shadow audits;
- target risk budget `delta=0.5%`, confidence `1-alpha=95%`;
- SLO goodput speedup at least 4x.

Gate S2:

- terminal-reserved state-commit EDF;
- audit preemption and canonical bypass;
- deadline miss below 1%;
- GPU-normalized speedup at least 2x;
- no uncertified exact-mode commit.

## Phase 3 — state amplification

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

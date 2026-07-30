# Checkpoint-20 ordinary-proposer closure

## Selected exact contract

The final candidate uses an ordinary FP16 batched proposer on GPU0 and a
batch-invariant FP16 canonical authority on GPU1. Intermediate canonical work
is singleton-shaped; terminal work is fixed B=12. A full terminal state
projection is the only legal checkpoint payload.

The contract is intentionally different from the rejected dual-lane contract.
Making GPU0 eligible as a second authority required batch-invariant execution,
which increased proposer latency enough to dominate the uncommon `k >= 2`
verification bursts. Cross-lane C2 remains a valid mechanism gate and negative
ablation, but its certificate is not transferred to this contract.

## Evidence roles

- The observed margin-0.03125 state mismatch from the causal probe is
  adaptation evidence and seeds only the calibration failure floor.
- Calibration and held-out service stages share the exact contract fingerprint,
  but the calibration stage is non-gating.
- The frozen threshold is evaluated over five new service seeds.
- Post-stage replay reports observed disagreements only.
- The formal risk claim comes exclusively from randomized base audits with
  independent pre-outcome audit coins and a time-uniform e-process.

## Frozen submission gates

- maximum per-seed P99 state-entry latency at most 1.9 seconds;
- zero deadline misses;
- time-uniform state-disagreement upper bound at most 0.5%;
- zero online authority violations;
- paired checkpoint quality over at least 16 English and 16 Chinese sessions,
  with zero catastrophic outliers.

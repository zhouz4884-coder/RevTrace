# Checkpoint/Rebase payload repair and dual-lane closure

This protocol supersedes the positive checkpoint/rebase numbers produced
before checkpoint-payload parity was repaired. Those older results remain
diagnostic only.

## Frozen contract

- Model: Qwen3-ASR-0.6B.
- Service: 120-second, concurrency-12, mixed English/Chinese natural
  distinct-sequence audio.
- Checkpoint interval: 30 seconds.
- Checkpoint payload: complete terminal state projection.
- Nonterminal selective authority: FP16 singleton execution split
  deterministically across GPU0 and GPU1.
- The GPU0 engine keeps `logprobs=20` for batched margin estimation, but both
  singleton authority requests use `logprobs=None`; the C2 artifact records
  both engine and request settings.
- Both engines request the same vLLM batch-invariant arithmetic runtime. A
  mixed ordinary/invariant lane pool is retained as a failed diagnostic
  contract and cannot authorize state updates.
- Terminal authority: FP16 fixed-shape batch-12 on GPU1.
- State update: only the selected authoritative result may enter the next
  revision state.

The executable gate values are in
`configs/checkpoint_dual_lane_closure.json`.

## C0 — payload parity

Service, post-stage replay, and quality evaluation call the same
`checkpoint_payload()` helper. The helper fails closed unless the transition is
terminal and the projected text equals `prefix + selected candidate`.

## C1 — statistical validity

Dependent post-stage replay revisions are reported as observed counts only.
The population-risk statement is rebuilt under the new fingerprint with
fixed-probability audit coins drawn before proposer and canonical outcomes.
A mixture e-process is inverted to obtain a time-uniform upper bound while the
revision error sequence may be arbitrarily dependent.

## C2 — lane compatibility

GPU0 and GPU1 receive byte-identical singleton jobs before one authoritative
state update. The gate contains 720 pairs, including initial segments and
post-checkpoint contexts. Any token, text, or state-projection mismatch kills
dual-lane authority. Both lane runtime settings must match the deployed
service.

## C3-C4 — authority and recalibration

The dual-lane policy and C2 artifact hash enter the fingerprint. No old
single-lane threshold or failure floor is migrated. Calibration precedes a
fresh frozen threshold and formal risk audit.

## C5 — five-seed system gate

All five frozen seeds are reported. The gate requires maximum seed P99 at most
1.9 seconds, zero deadline misses, zero output/state/authority violations, and
the independent risk UCB at most 0.5%. Overall, terminal, and nonterminal P99,
verification bursts, and energy are retained.

## C6 — paired quality

Sixteen 120-second natural sessions per language are evaluated on identical
continuous and checkpoint/rebase audio. The report includes paired bootstrap
intervals, per-boundary transcript edit analysis, and catastrophic-outlier
counts. This is an empirical paired quality statement, not deterministic
transcript equivalence.

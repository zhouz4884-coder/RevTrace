# Checkpoint-20 low-margin state-holdback closure

Decision: **CHECKPOINT20_HOLDBACK_FINAL_PASS**

## Frozen contract

- Margin threshold: `0.031251`.
- Low-margin nonterminal candidate: provisional display only; no textual state entry.
- Terminal/checkpoint authority: fixed B=12 FP16 canonical execution.
- Time-uniform state-risk UCB: 0.473%.

## Matched-seed repair attribution

- Seed: `20260824`; all declared controls match.
- P99: 2.338 s -> 1.841 s (21.243% lower).
- Deadline misses: 12 -> 0.
- Energy: 10.386 -> 9.236 J/audio-s (11.077% lower).

## Five-seed live service

| Seed | P50 | P95 | P99 | misses | verify | holdbacks | J/audio-s |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 20260840 | 0.675 | 1.199 | 1.414 | 0 | 10.000% | 18 | 9.239 |
| 20260841 | 0.657 | 1.154 | 1.316 | 0 | 10.000% | 9 | 8.532 |
| 20260842 | 0.656 | 1.180 | 1.262 | 0 | 10.000% | 14 | 8.525 |
| 20260843 | 0.666 | 1.103 | 1.217 | 0 | 10.000% | 10 | 8.645 |
| 20260844 | 0.656 | 1.054 | 1.181 | 0 | 10.000% | 10 | 8.407 |

## Paired natural quality

| Language | sessions | continuous | holdback/rebase | delta | bootstrap 95% CI | catastrophic |
|---|---:|---:|---:|---:|---:|---:|
| Chinese (CER) | 16 | 2.644% | 4.405% | 1.760% | [0.349%, 4.270%] | 0 |
| English (WER) | 16 | 2.535% | 3.986% | 1.451% | [0.214%, 3.616%] | 0 |

## Repair history and implementation

- Root cause: rare low-margin synchronous singleton verification serialized after the proposer and produced the 120-second tail spikes; age alone was not the causal bottleneck.
- Rejected repair: fixed-B=2 authority was not cross-shape equivalent to singleton authority.
- Rejected repair: fixed-B=12 intermediate authority added constant verification work and worsened P99.
- Selected repair: low-margin nonterminal candidates remain provisional; checkpoint/terminal fixed-B=12 execution is the only authoritative rebase for those candidates.
- `scripts/remote/run_phase5a_live_adaptive.py`: live holdback state-entry path and auditable per-round counters.
- `scripts/remote/run_checkpoint_dual_lane_shadow_audit.py`: pre-outcome randomized, time-uniform state-risk audit.
- `scripts/remote/run_checkpoint_rebase_quality.py`: paired natural quality gate with identical execution shape and bootstrap intervals.
- `scripts/finalize_checkpoint20_holdback_closure.py`: fail-closed gate aggregation using per-session event percentiles.

## Preserved negative result

The first two-episode calibration is retained as `calibration_insufficient_audits_negative.json`. After the frozen failure floor, it contained too few admitted validation events to certify the 0.5% risk target. Certification occurred only inside the following service episode, so that run was rejected rather than reported. The repaired protocol uses three calibration episodes and freezes the threshold before held-out service.

## Gate decisions

- `recalibration`: **PASS**
- `time_uniform_state_risk`: **PASS**
- `five_seed_tail`: **PASS**
- `paired_quality`: **PASS**

## Evidence boundary

- Low-margin nonterminal output is provisional and is not a selected state authority.
- The formal risk statement covers admitted high-margin state entries and is time-uniform under pre-outcome randomized audit coins.
- The contract is not deterministic arithmetic equivalence to singleton execution.
- Observed mean quality deltas at the frozen sample size do not establish population equivalence unless the reported confidence interval also supports it.

# RevTrace long-horizon protocol repair and checkpoint/rebase gate

Decision: **CHECKPOINT_REBASE_SLO_RISK_PASS_GUARD_FAIL**

## L1 — Protocol repair

The prior cyclic/rolled 120-second result is retained as historical evidence but is superseded for causal attribution. The repaired runner uses a duration/age/input-scoped fingerprint, singleton intermediate authority, fixed-shape terminal authority, true terminal tail semantics, natural distinct utterance sequences, one state projection, component timing, actual audio-sample/model-input sizes, and a true 4096-token runtime limit. The local suite passes 112 tests.

A deployment-only failure was also removed: a PuTTY/sed quoting error truncated a Python identifier on the server. Invalid runs terminated before producing evidence and are excluded; the valid runner was verified by local/remote SHA-256 equality.

## L2 — Proposer-only lower bound

Decision: **CONCURRENCY_RESHAPING_REMAINS_PLAUSIBLE**

| Concurrency | 90–120 s proposer mean | proposer P99 | logical P99 | misses |
|---:|---:|---:|---:|---:|
| 1 | 0.457 | 0.593 | 0.614 | 0 |
| 4 | 0.687 | 0.768 | 0.811 | 0 |
| 8 | 1.130 | 1.278 | 1.353 | 0 |
| 12 | 1.372 | 1.756 | 1.870 | 0 |

The 120-second proposer-only lower bound remains below the two-second deadline even at c12. Long-history recomputation is real, but it does not by itself reproduce the old 5.295-second tail.

## L3 — Strict frozen age–concurrency matrix

Decision: **CONCURRENCY_RESHAPING_CAN_RESTORE_SINGLE_STREAM_SLO**

| Age | c1 median | c4 median | c8 median | c12 median |
|---:|---:|---:|---:|---:|
| 30s | 0.479 | 0.546 | 0.607 | 0.742 |
| 60s | 0.338 | 0.584 | 0.700 | 0.889 |
| 90s | 0.442 | 0.695 | 1.047 | 1.435 |
| 120s | 0.513 | 0.916 | 1.398 | 2.035 |

At 120 seconds, c1 remains about 0.513 seconds while c12 reaches about 2.035 seconds. The boundary is therefore the interaction of long accumulated audio, terminal authority, and a fixed c12 shape; it is not an unavoidable single-stream limit.

## L4 — Repaired continuous full-selective service

| Mode | P99 | miss rounds | verify fraction | certificate/replay UCB | output/state/authority violations |
|---|---:|---:|---:|---:|---:|
| continuous | 2.393 | 8 | 5.28% | 0.50%/0.42% | 0/0/0 |

The repaired continuous path passes the statistical risk and state safety checks but fails the two-second SLO. This isolates a genuine long-horizon capacity problem after protocol confounders are removed.

Relative to repaired continuous service, Checkpoint-and-Rebase reduces P99 by 19.04%, reduces energy per audio-second by 48.86%, and removes 8 deadline-miss rounds.

## L5 — Authoritative Checkpoint-and-Rebase death gate

Rebase pilots are retained only as counterexample-discovery splits. Each observed root mismatch raises the monotonic dynamic failure floor; the table below uses the newest fresh-seed confirmation artifact rather than any discovery split.

| Mode | P99 | max age-bucket P99 | miss rounds | verify fraction | certificate/replay UCB | violations |
|---|---:|---:|---:|---:|---:|---:|
| checkpoint/rebase | 1.937 | 1.937 | 0 | 8.75% | 0.50%/0.42% | 0/0/0 |

| Language | Continuous error | Rebase error | Delta | Catastrophic outliers |
|---|---:|---:|---:|---:|
| Chinese (CER) | 2.65% | 3.20% | 0.55% | 0 |
| English (WER) | 2.72% | 2.87% | 0.16% | 0 |

The death gate requires every age-bucket P99 to be at most 1.9 seconds, zero deadline-miss rounds, statistical risk UCB at most 0.5%, zero output/state/authority violations, and the preregistered paired quality gate.

The independently confirmed rebase run restores the deployed two-second SLO with zero deadline-miss rounds. It does not pass the stricter 1.9-second admission guard: the maximum age-bucket P99 is 1.937 seconds, 0.037 seconds above that guard.

The guard failure is localized to one nonterminal round at 110 seconds. The proposer takes 0.607 seconds and two low-margin singleton canonical verifications are serialized for 1.283 seconds. There is no cross-round verifier backlog, checkpoint boundary, or thermal-throttling signature. Thus the remaining 37 ms guard failure is a synchronized selective-verification burst, not renewed full-history accumulation.

### Gate checks

- `each_age_bucket_p99_at_most_1p9_seconds`: **FAIL**
- `zero_deadline_miss_rounds`: **PASS**
- `risk_upper_bound_at_most_0p5_percent`: **PASS**
- `zero_output_state_authority_violations`: **PASS**
- `paired_quality_gate`: **PASS**

## Evidence boundary

- The threshold is learned by the live risk controller under the new fingerprint; it is not a hand-fixed 0.05 threshold.
- Zero observed replay violations are empirical and do not make FP16 inference mathematically deterministic.
- The quality gate contains four sessions per language and is a mechanism death gate, not a population-equivalence result.
- Audio-encoder token counts remain explicitly null because the frozen vLLM output does not expose them.

Raw artifacts and CSV tables are under `results/long_horizon/`.

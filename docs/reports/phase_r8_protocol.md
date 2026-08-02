# Phase R8 protocol: Safe Context Reanchoring

## Frozen R7 boundary

- `QWEN_R7_SEMANTIC_PERFORMANCE_PASS`
- `WHISPER_R7_PERFORMANCE_PASS`
- `WHISPER_R7_QUALITY_TAIL_FAIL`

R8 does not retune the frozen EFSC thresholds.  It tests whether externally
grounded acoustic context can repay sufficiency debt after EFSC has removed
unsafe feedback ancestry.

## R8.1 information gate

The first gate runs complete causal session views on the eleven frozen R7
quality roots:

- VACC-10, VACC-20, and VACC-30: the current window is conditioned only on a
  singleton capsule transcribed from raw audio strictly preceding that window;
- Snapshot+Delta: a frozen canonical anchor at a fixed window boundary plus a
  singleton transcription of only the later raw-audio delta.

References never choose an input within a trajectory.  The budgeted oracle may
choose one completed causal trajectory per session.  It passes only if it has
zero catastrophic outliers, retains pooled and split WER gates, and retains an
estimated energy reduction of at least 40% after charging measured capsule
time against the all-singleton canonical time.

If R8.1 fails, the implementation must distinguish missing information from a
view-construction or transition bug.  VACC runtime development is authorized
only after a legal finite-budget view closes every frozen root.

## Subsequent gates

1. Cross-modal sufficiency monitor: session-level holdout recall at least 90%
   and false-trigger rate at most 10%; it schedules recovery but never grants
   feedback authority.
2. Snapshot/capsule semantics: canonical agreement, feedback-lineage MVCC,
   audio-frontier binding, stale/cross-session/epoch rejection, idempotence,
   and no provisional ancestors after installation.
3. Frozen and new quality sets: zero catastrophic outliers, mean delta at most
   1 pp, bootstrap 95% upper bound at most 2 pp, zero repetition loops.
4. Serving: W1/W2 five new seeds; median wall speedup at least 2.5x, display
   and state P99 at most 1.9 s, and minimum energy reduction at least 40%,
   including background GPU energy.
5. Final risk certificate: at least 30,000 eligible fast commits, 1,200 random
   sentinels, time-uniform UCB at most 0.5%, and zero capsule-lineage violations.

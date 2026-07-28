# RevTrace Phase 4 paper tables

Decision: **PHASE4_TASKS_COMPLETE_WITH_BOUNDED_NEGATIVE_GATES**

## Whisper feedback intervention

| Model | Candidate windows | Distinct pairs | Persistent pairs | Median RAF | Max RAF | PCM |
|---|---:|---:|---:|---:|---:|---:|
| whisper-base.en | 100 | 16 | 6 | 1.000 | 153.000 | 0.375 |
| whisper-tiny.en | 100 | 5 | 0 | 1.000 | 2.750 | 0.000 |

Feedback-ON propagating pairs: **8**.
Feedback-OFF propagating pairs: **0**.
Application catastrophes: **0**; the
preregistered catastrophe-prevention claim is
**not eligible**.

## Diversity-aware state-pair mining

| Model | Screened | Probed | Distinct pairs | Pairs / 1000 rows | Yield gain | New vs Phase 3 | 50-pair gate |
|---|---:|---:|---:|---:|---:|---:|---:|
| Qwen3-ASR-0.6B | 500 | 500 | 8 | 1.000 | 2.78x | 7 | NOT MET |
| Qwen3-ASR-1.7B | 500 | 500 | 5 | 0.625 | 2.54x | 4 | NOT MET |

These are targeted-mechanism yields, not production occurrence rates.

## SlackGuard physical gate

The measured full-request quantum is
**11.27x** the
2% P99 intrusion budget.  The existing full-request implementation is a
frozen NO-GO; fine-grained cancellable checkpoints remain unimplemented.

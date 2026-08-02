# Whisper P0-P3 closure

Decision: `P0_P3_PAPER_THREATENING_C16_HEADLINE_FAIL`.

## P0 protocol repair

- Display and state goodput now use matched event scopes.
- Risk audits now execute the actual holdback transition instead of canonical state replacement.
- Every formal workload binds the policy path, SHA-256 and all runtime thresholds.
- Scheduler telemetry records occupancy, pending authority and lost batch slots.

## P1 causal decomposition

Attribution: `AUTHORITY_QUEUE_AND_BATCH_FRAGMENTATION`.

| Variant | Wall | GPU norm | Display | State P99 | Energy | Verify | Occupancy | Pending max |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| unprotected | 2.722x | 2.722x | 2.722x | 0.653s | 62.6% | 0.0% | 100.0% | 0 |
| feedback-off | 3.583x | 3.583x | 3.583x | 0.497s | 70.3% | 0.0% | 100.0% | 0 |
| checkpoint-only | 2.163x | 1.081x | 2.163x | 3.333s | 14.3% | 5.6% | 81.8% | 7 |
| risk-only | 1.953x | 0.977x | 1.953x | 2.033s | 4.7% | 11.8% | 81.8% | 2 |
| full-verify | 1.625x | 0.813x | 1.625x | 2.934s | -13.1% | 16.0% | 64.3% | 5 |
| holdback-dual | 2.136x | 1.068x | 2.136x | 3.478s | 13.4% | 5.6% | 72.0% | 7 |
| holdback-colocated | 2.109x | 2.109x | 2.109x | 3.674s | 53.0% | 5.6% | 75.0% | 7 |
| holdback-staggered-dual | 2.025x | 1.013x | 2.025x | 2.661s | 13.8% | 6.9% | 78.3% | 4 |
| holdback-staggered-colocated | 2.000x | 2.000x | 2.000x | 2.827s | 48.2% | 6.9% | 75.0% | 4 |

## P2 holdback

Selected topology: `None`.

## P3 independent validation

| Cell | Runs | Wall median | Wall min | GPU norm | Display | State P99 max | Energy median/min | Violations | Gate |
|---|---:|---:|---:|---:|---:|---:|---:|---:|:---:|
| base/c16 W1 sync | 5 | 2.709x | 2.037x | 1.355x | 2.709x | 4.782s | 32.5% / 10.3% | 0 | FAIL |
| base/c16 W2 poisson | 5 | 2.347x | 2.216x | 1.174x | 2.347x | 4.222s | 23.2% / 16.4% | 2 | FAIL |

## Statistical contracts

- Risk gate EARLY FAIL: 2 streams, 5,166 eligible entries, 121 pre-outcome audits, 1 repeat-stable caught error(s). The zero-error gate was irreversibly violated, so the 30k target was stopped.
- Paired c8 quality was not run because the c8 staggered topology failed its pre-run eligibility gate.
- c16 paired quality: mean WER delta -0.011 pp; bootstrap 95% upper 0.000 pp; catastrophic outliers 0.

The c16 cells decide whether Whisper remains a headline performance leg. The c8 cell is a disclosed low-load long-session boundary unless its stricter resource-positive gate passes.

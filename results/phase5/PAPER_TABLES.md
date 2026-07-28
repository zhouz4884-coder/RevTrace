# Phase 5 paper tables

## Live adaptive c16 -> c64 -> c16

| Stage | c | Events | Cert. event | Learned tau | Fast window | Risk upper | Verify | Goodput | P99 | Miss | T-cert. | Regret | J/audio-s |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| c16_initial | 16 | 2560 | 1497 | 0.03125 | 0.982 | 0.4508% | 68.48% | 21.013 | 1.406 | 0 | 67.898 | 17.675 | 8.035 |
| c64_drift | 64 | 3200 | 1350 | 0.015625 | 0.987 | 0.4989% | 56.47% | 42.900 | 2.889 | 448 | 35.782 | 0.000 | 4.611 |
| c16_return | 16 | 2560 | 1497 | 0.015625 | 0.990 | 0.4481% | 68.05% | 22.305 | 1.293 | 0 | 67.261 | 17.950 | 7.755 |

## Whisper protected feedback

| Model | Events | Verify | Protected pairs | Output/state violations | Wall speedup |
|---|---:|---:|---:|---:|---:|
| whisper-base.en | 300 | 100.00% | 16/16 | 0/0 | 1.002x |
| whisper-tiny.en | 300 | 100.00% | 5/5 | 0/0 | 1.006x |

### Feedback-OFF causal boundary

| Model | Events | Certification | Local differences | State-propagation violations | Wall speedup |
|---|---:|---:|---:|---:|---:|
| whisper-base.en | 300 | 0 | 284 | 0 | 6.444x |
| whisper-tiny.en | 300 | 0 | 281 | 0 | 6.117x |

### Replication-consistency signal boundary

| Model | Events | Known pairs protected | Output/state violations |
|---|---:|---:|---:|
| whisper-base.en | 300 | 10/16 | 36/32 |
| whisper-tiny.en | 300 | 1/5 | 11/10 |

## Workload and energy frontier

| Cell | Model | c | Wall | GPU norm. | Goodput | P99 | Miss | Verify | Output/state violations | State risk | 95% upper if zero | J/audio-s |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 0p6b-c16-d120-sync-mixed | Qwen3-ASR-0.6B | 16 | 4.642x | 2.321x | 5.325 | 4.858 | 346 | 3.12% | 0/0 | 0.000% | 0.312% | 15.582 |
| 0p6b-c16-d60-poisson-mixed | Qwen3-ASR-0.6B | 16 | 4.945x | 2.473x | 12.981 | 2.893 | 18 | 4.38% | 0/0 | 0.000% | 0.622% | 9.473 |
| 0p6b-c32-d120-burst-zh | Qwen3-ASR-0.6B | 32 | 6.767x | 3.383x | 3.910 | 5.591 | 1211 | 3.02% | 2/1 | 0.052% | NA | 13.760 |
| 0p6b-c8-d30-sync-en | Qwen3-ASR-0.6B | 8 | 4.333x | 2.167x | 12.063 | 1.421 | 0 | 7.50% | 0/0 | 0.000% | 2.466% | 7.743 |
| 1p7b-c16-d120-poisson-mixed | Qwen3-ASR-1.7B | 16 | 3.319x | 1.660x | 3.801 | 5.317 | 416 | 6.25% | 0/0 | 0.000% | 0.312% | 22.652 |
| 1p7b-c16-d30-sync-mixed | Qwen3-ASR-1.7B | 16 | 5.207x | 2.603x | 15.872 | 1.446 | 0 | 9.58% | 0/0 | 0.000% | 1.240% | 8.193 |
| 1p7b-c32-d60-burst-zh | Qwen3-ASR-1.7B | 32 | 5.353x | 2.677x | 12.045 | 2.983 | 283 | 5.31% | 0/0 | 0.000% | 0.312% | 9.294 |
| 1p7b-c8-d60-poisson-en | Qwen3-ASR-1.7B | 8 | 2.932x | 1.466x | 7.273 | 2.672 | 8 | 7.92% | 0/0 | 0.000% | 1.240% | 18.228 |

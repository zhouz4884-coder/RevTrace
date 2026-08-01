# Whisper base/c8 r5 closure

Decision: `R5_RISK_PASS_C8_PERFORMANCE_BOUNDARY`.

## Risk contract

- Frozen policy SHA-256: `434db6fb445f9594d114e1152b89af32fb607eee866acf1b761f6aff5f22e608`.
- Adaptation-only roots covered: 5.
- Independent risk entries: 60,032.
- Pre-outcome randomized canonical audits: 1,235.
- Caught state-entry errors: 0.
- Maximum time-uniform 95% upper risk: 0.4798%.
- Calibration verification fraction: 11.32%.

## Performance boundary

| Variant | GPUs | Wall | GPU-normalized | Display-SLO | State P99 | Verify | Energy reduction | Full gate |
|---|---:|---:|---:|---:|---:|---:|---:|:---:|
| dual_lane1 | 2 | 1.685x | 0.842x | 1.784x | 3.099s | 18.75% | -6.30% | FAIL |
| dual_lane2 | 2 | 1.591x | 0.795x | 1.684x | 3.277s | 18.75% | -16.10% | FAIL |
| dual_lane4 | 2 | 1.495x | 0.747x | 1.582x | 3.689s | 19.44% | -23.41% | FAIL |
| colocated_lane1 | 1 | 1.632x | 1.632x | 1.728x | 3.047s | 19.44% | 36.74% | FAIL |

The risk mechanism succeeds, but no tested c8 topology achieves the
complete production gate. Extra verifier lanes degrade performance;
physical-GPU colocation fixes resource efficiency but not wall/SLO
speedup. The defensible conclusion is a c8 low-load capacity boundary.

## Accounting repair

The colocated run exposed a resource-accounting defect: logical
proposer/verifier roles on the same CUDA device were charged as two
physical GPUs and their power was sampled twice. The runner now
deduplicates process-visible CUDA indices. Dual-GPU results are
unchanged; only colocated accounting required a rerun.

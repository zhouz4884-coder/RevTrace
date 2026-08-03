# R10 Qwen cross-adapter machine summary

Decision: **PASS_R10_QWEN_CROSS_ADAPTER_MATRIX**

| Model | Adapter | Wall | GPU-normalized | Energy reduction | Fine replay | Exact sessions | Edit P95 | Edit max | Tx violations | Authority mismatches |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 0.6B | dgft | 6.88x | 3.44x | 59.8% | 0.00% | 11/16 | 3.43% | 5.41% | 0 | 0 |
| 0.6B | hybrid | 5.19x | 2.59x | 51.3% | 5.00% | 13/16 | 2.15% | 5.41% | 0 | 0 |
| 1.7B | dgft | 6.06x | 3.03x | 51.0% | 0.00% | 9/16 | 1.79% | 2.86% | 0 | 0 |
| 1.7B | hybrid | 3.92x | 1.96x | 33.2% | 8.75% | 10/16 | 1.79% | 2.86% | 0 | 0 |

The FP32 batched authority establishes a new concurrency-invariant canonical path; it is not claimed to reproduce the original FP16 singleton trajectory bit-for-bit.

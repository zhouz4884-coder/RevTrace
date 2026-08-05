# Independent V100 matrix audit

- Decision: **PASS**
- Checks: **479/479**
- Phase counts: `{'V1': 24, 'V2': 16, 'V3': 32, 'V4': 12}`
- Errors: **0**

## Recomputed headline results

| Model | SG speedup | Hybrid speedup | c64 xRT | c64 P99 | scale efficiency | SLO capacity | c128 P99 |
|---|---:|---:|---:|---:|---:|---:|---:|
| Qwen3-ASR-0.6B | 4.682x | 5.764x | 147.138 | 1.115s | 91.1% | c64 | 2.266s |
| Qwen3-ASR-1.7B | 3.248x | 4.657x | 114.488 | 1.471s | 100.7% | c64 | 2.799s |

## Boundary

Independent RHEL7/8xV100 Transformers-eager contract; do not pool absolute results with RTX3090/vLLM. V3 is single-node scale-out.
Observed zero protocol violations is an empirical result over this matrix, not a mathematical zero-risk claim.

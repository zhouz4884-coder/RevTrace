# RevTrace V100 V1--V4 matrix

- Completed cells: **84**
- Failed cells retained: **0**
- Contract: All measurements use the independent RHEL7/8xTesla-V100-32GB Transformers-eager contract. Absolute values are not pooled with the RTX3090/vLLM contract. V3 is single-node scale-out, not multi-node.

## V1 authority microprofile

| Model | dtype | B | req/s | batch/singleton | repeat mismatch | singleton mismatch |
|---|---:|---:|---:|---:|---:|---:|
| Qwen3-ASR-0.6B | float16 | 1 | 1.483 | 0.955x | 0 | 0 |
| Qwen3-ASR-0.6B | float16 | 2 | 2.978 | 1.478x | 0 | 1 |
| Qwen3-ASR-0.6B | float16 | 4 | 5.648 | 2.850x | 0 | 2 |
| Qwen3-ASR-0.6B | float16 | 8 | 10.681 | 5.370x | 0 | 4 |
| Qwen3-ASR-0.6B | float16 | 16 | 18.429 | 9.277x | 0 | 8 |
| Qwen3-ASR-0.6B | float16 | 32 | 29.244 | 14.687x | 0 | 16 |
| Qwen3-ASR-0.6B | float32 | 1 | 1.658 | 0.990x | 0 | 0 |
| Qwen3-ASR-0.6B | float32 | 2 | 3.255 | 1.529x | 0 | 1 |
| Qwen3-ASR-0.6B | float32 | 4 | 5.875 | 2.766x | 0 | 2 |
| Qwen3-ASR-0.6B | float32 | 8 | 10.337 | 4.842x | 0 | 4 |
| Qwen3-ASR-0.6B | float32 | 16 | 16.433 | 7.633x | 0 | 8 |
| Qwen3-ASR-0.6B | float32 | 32 | 23.334 | 10.858x | 0 | 16 |
| Qwen3-ASR-1.7B | float16 | 1 | 1.571 | 1.003x | 0 | 0 |
| Qwen3-ASR-1.7B | float16 | 2 | 2.957 | 1.480x | 0 | 1 |
| Qwen3-ASR-1.7B | float16 | 4 | 5.744 | 2.775x | 0 | 2 |
| Qwen3-ASR-1.7B | float16 | 8 | 10.672 | 5.285x | 0 | 4 |
| Qwen3-ASR-1.7B | float16 | 16 | 17.016 | 8.503x | 0 | 8 |
| Qwen3-ASR-1.7B | float16 | 32 | 26.257 | 12.841x | 0 | 16 |
| Qwen3-ASR-1.7B | float32 | 1 | 1.646 | 0.975x | 0 | 0 |
| Qwen3-ASR-1.7B | float32 | 2 | 3.063 | 1.461x | 0 | 1 |
| Qwen3-ASR-1.7B | float32 | 4 | 5.451 | 2.542x | 0 | 2 |
| Qwen3-ASR-1.7B | float32 | 8 | 8.721 | 4.125x | 0 | 4 |
| Qwen3-ASR-1.7B | float32 | 16 | 12.346 | 5.839x | 0 | 8 |
| Qwen3-ASR-1.7B | float32 | 32 | 15.584 | 7.362x | 0 | 16 |

## V2 normal-load baselines

| Model | Mode | wall (s) | audio xRT | GPU-norm | display P99 | verify | edit P95 |
|---|---|---:|---:|---:|---:|---:|---:|
| Qwen3-ASR-0.6B | all-singleton | 76.249 | 6.295 | 6.295 | 5.728 | 0.000 | 0.0000 |
| Qwen3-ASR-0.6B | unprotected-batch | 12.995 | 36.936 | 36.936 | 1.356 | 0.000 | 0.0000 |
| Qwen3-ASR-0.6B | fp32-batch | 25.414 | 18.887 | 18.887 | 2.455 | 0.000 | 0.0000 |
| Qwen3-ASR-0.6B | margingate | 11.851 | 40.501 | 20.251 | 1.105 | 0.000 | 0.0000 |
| Qwen3-ASR-0.6B | llm42 | 86.716 | 5.535 | 2.768 | 1.100 | 1.000 | 0.0000 |
| Qwen3-ASR-0.6B | revtrace-sg | 16.286 | 29.474 | 14.737 | 1.095 | 0.067 | 0.0000 |
| Qwen3-ASR-0.6B | coarse-dgft | 12.558 | 38.223 | 19.111 | 1.106 | 0.000 | 0.0000 |
| Qwen3-ASR-0.6B | hybrid-dgft | 13.229 | 36.285 | 18.142 | 1.086 | 0.000 | 0.0000 |
| Qwen3-ASR-1.7B | all-singleton | 80.375 | 5.972 | 5.972 | 6.166 | 0.000 | 0.0000 |
| Qwen3-ASR-1.7B | unprotected-batch | 16.373 | 29.316 | 29.316 | 1.549 | 0.000 | 0.0000 |
| Qwen3-ASR-1.7B | fp32-batch | 38.966 | 12.318 | 12.318 | 4.202 | 0.000 | 0.0000 |
| Qwen3-ASR-1.7B | margingate | 18.315 | 26.208 | 13.104 | 1.433 | 0.033 | 0.0000 |
| Qwen3-ASR-1.7B | llm42 | 92.655 | 5.180 | 2.590 | 1.393 | 1.000 | 0.0000 |
| Qwen3-ASR-1.7B | revtrace-sg | 24.748 | 19.395 | 9.698 | 1.440 | 0.100 | 0.0000 |
| Qwen3-ASR-1.7B | coarse-dgft | 16.425 | 29.223 | 14.612 | 1.609 | 0.000 | 0.0318 |
| Qwen3-ASR-1.7B | hybrid-dgft | 17.260 | 27.811 | 13.905 | 1.466 | 0.000 | 0.0318 |

## V3 c128 scale-out

| Model | GPUs | throughput | speedup | efficiency | display P99 |
|---|---:|---:|---:|---:|---:|
| Qwen3-ASR-0.6B | 2 | 40.514 | 1.000x | 100.0% | 8.446 |
| Qwen3-ASR-0.6B | 3 | 41.696 | 1.029x | 68.6% | 7.890 |
| Qwen3-ASR-0.6B | 4 | 85.025 | 2.099x | 104.9% | 3.834 |
| Qwen3-ASR-0.6B | 8 | 148.930 | 3.676x | 91.9% | 2.266 |
| Qwen3-ASR-1.7B | 2 | 26.719 | 1.000x | 100.0% | 11.121 |
| Qwen3-ASR-1.7B | 3 | 32.536 | 1.218x | 81.2% | 11.800 |
| Qwen3-ASR-1.7B | 4 | 54.010 | 2.021x | 101.1% | 5.412 |
| Qwen3-ASR-1.7B | 8 | 111.133 | 4.159x | 104.0% | 2.799 |

## V4 bottleneck attribution

| Model | authority dtype | rho | throughput | authority/proposer | J/audio-s |
|---|---|---:|---:|---:|---:|
| Qwen3-ASR-0.6B | float16 | 1 | 33.712 | 1.088 | 6.319 |
| Qwen3-ASR-0.6B | float32 | 1 | 18.603 | 2.216 | 12.709 |
| Qwen3-ASR-0.6B | float16 | 3 | 41.306 | 0.517 | 4.692 |
| Qwen3-ASR-0.6B | float32 | 3 | 40.581 | 0.996 | 6.739 |
| Qwen3-ASR-0.6B | float16 | 5 | 40.250 | 0.368 | 4.612 |
| Qwen3-ASR-0.6B | float32 | 5 | 40.630 | 0.759 | 6.024 |
| Qwen3-ASR-1.7B | float16 | 1 | 28.499 | 1.002 | 9.483 |
| Qwen3-ASR-1.7B | float32 | 1 | 12.294 | 2.669 | 23.053 |
| Qwen3-ASR-1.7B | float16 | 3 | 33.345 | 0.524 | 7.167 |
| Qwen3-ASR-1.7B | float32 | 3 | 27.860 | 1.176 | 11.532 |
| Qwen3-ASR-1.7B | float16 | 5 | 32.597 | 0.391 | 6.840 |
| Qwen3-ASR-1.7B | float32 | 5 | 33.909 | 0.841 | 9.370 |

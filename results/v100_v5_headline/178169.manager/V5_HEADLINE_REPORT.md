# RevTrace V5 repeated V100 headline audit

Decision: **PASS** (30/30 cells, three repeats per configuration).

| Model | Allocation | c | Audio xRT median [min,max] | Display P99 median [min,max] | Commit P99 median [min,max] | A/P median [min,max] | 2s display misses |
|---|---:|---:|---:|---:|---:|---:|---:|
| Qwen3-ASR-0.6B | p1a1 | 64 | 40.319 [40.095,40.860] | 4.125 [4.056,4.197] s | 11.756 [11.655,11.998] s | 1.027 [1.026,1.039] | 1184/2880 |
| Qwen3-ASR-0.6B | p3a5 | 64 | 93.788 [88.259,94.393] | 1.756 [1.749,1.773] s | 4.991 [4.978,5.377] s | 0.595 [0.515,0.606] | 6/2880 |
| Qwen3-ASR-0.6B | p4a4 | 32 | 106.780 [106.685,110.952] | 0.779 [0.771,0.782] s | 2.124 [1.959,2.124] s | 0.661 [0.637,0.678] | 0/1440 |
| Qwen3-ASR-0.6B | p4a4 | 64 | 157.786 [157.577,157.869] | 1.089 [1.078,1.095] s | 3.080 [3.064,3.088] s | 0.941 [0.938,0.943] | 0/2880 |
| Qwen3-ASR-0.6B | p4a4 | 128 | 161.927 [159.011,163.213] | 2.079 [2.069,2.123] s | 6.012 [5.997,6.144] s | 0.984 [0.958,0.994] | 176/5760 |
| Qwen3-ASR-1.7B | p1a1 | 64 | 28.238 [26.635,28.651] | 5.475 [5.454,5.694] s | 19.698 [18.312,20.664] s | 1.221 [1.159,1.289] | 1680/2880 |
| Qwen3-ASR-1.7B | p3a5 | 64 | 77.704 [73.091,77.869] | 2.209 [2.205,2.350] s | 6.273 [6.267,6.912] s | 0.604 [0.581,0.606] | 106/2880 |
| Qwen3-ASR-1.7B | p4a4 | 32 | 97.566 [93.367,97.812] | 0.879 [0.875,0.912] s | 2.457 [2.454,2.492] s | 0.845 [0.830,0.876] | 0/1440 |
| Qwen3-ASR-1.7B | p4a4 | 64 | 111.722 [110.009,116.384] | 1.394 [1.361,1.430] s | 4.890 [4.665,4.960] s | 1.160 [1.128,1.211] | 0/2880 |
| Qwen3-ASR-1.7B | p4a4 | 128 | 107.305 [106.752,108.494] | 2.730 [2.725,2.734] s | 10.153 [10.094,10.183] s | 1.245 [1.232,1.250] | 960/5760 |

## Evidence boundary

- Display and certified-commit latency are distinct estimands.
- Three deterministic repeats support a median/range report; they do not support a high-powered significance claim.
- The p3a5 cell is an allocation sensitivity derived from the two-stage service model.
- This is single-node V100 evidence and does not establish multi-node scaling or an unbounded asynchronous queue.

# TC transaction-overhead attribution audit

## Decision

CLOSES_HOST_PROTOCOL_ATTRIBUTION_WITHOUT_NEW_GPU_RUN

This is a **local host-side CPU microbenchmark**, not a GPU or end-to-end serving result. It uses the production functions in `src/revtrace/dgft.py` on one frozen valid transaction fixture.

## Why the prior logs were insufficient alone

The existing online trace contains 1,048 commits across 16 files. Its `committed_perf - certified_perf` interval includes lock waiting, conversion, certificate construction and hashing, validation, state materialization, and the pending-version update. It is therefore an operational upper envelope, not an isolated protocol attribution.

Observed mixed coordinator interval: median 1317.701 us, P95 2716.598 us, P99 3784.038 us.

## Isolated microbenchmark

Warmup: 2,000 calls/variant. Measurement: 31 randomized repeats x 20,000 calls/variant. Values below are repeat-level nanoseconds per operation; P95/P99 describe variation across repeat aggregates, not per-request service tails.

| Path | Median (us/op) | P95 | P99 | Median delta vs raw (us) | Median ratio vs raw |
|---|---:|---:|---:|---:|---:|
| Raw immutable-state materialization; no validation | 19.077 | 19.813 | 19.885 | 0.000 | 1.00x |
| Production job validation | 24.835 | 25.636 | 25.887 | 5.745 | 1.30x |
| Cumulative job + certificate validation | 80.604 | 82.902 | 85.866 | 61.577 | 4.22x |
| Production `commit_canonical_segment` | 101.107 | 104.486 | 104.514 | 81.960 | 5.32x |

The paired difference between the production commit and the no-check materialization baseline is 81.960 us/op at the median. This difference is the cleanest local estimate of the validation work added to the same immutable-state installation.

## Attribution boundary

The result closes the narrow question of whether certificate, version, frontier, and ledger-state checks have a measurable host-side cost. It does not establish GPU scalability, service goodput, or an end-to-end speedup. Existing GPU experiments remain the evidence for those claims.

No new GPU run is required to close this *host-side protocol-cost* attribution: the microbenchmark isolates the production functions, while the pre-existing online trace provides a conservative deployed-path cross-check. A GPU run would only be necessary for a new claim about device utilization or end-to-end service performance.

## Reproduction

```powershell
E:\Anaconda\python.exe scripts\run_tc_transaction_overhead.py
```

Raw repeat samples and the complete environment are stored alongside the JSON result in `results/tc_transaction_overhead/`.

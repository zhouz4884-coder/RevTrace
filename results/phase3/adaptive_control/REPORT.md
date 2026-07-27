# RevTrace Phase 3A report

Decision: **PHASE3A_ADAPTIVE_CONTROL_PASS**

## Automatic policy sequence

| Stage | Selected threshold |
|---|---:|
| 0.6B / c16 initial | 0.050 |
| 0.6B / c64 | 0.200 |
| 1.7B / c16 | 0.100 |
| 0.6B / c16 fresh return epoch | 0.050 |

The controller retained the frozen c64 error at margin 0.078125 and the 1.7B
error at margin 0.0625 as hard exclusions.  Later zero-error audits cannot
erase those failures.

These are not four manually configured static thresholds.  Each row is the
endpoint of a contract-scoped controller epoch.  Risk and verifier-queue prices
select within the simultaneously certified policy envelope; the finite grid is
the current deployment approximation to that dynamic control objective.

## Deployed recovery

- Minimum wall speedup: 4.932x
- Minimum GPU-normalized speedup: 2.466x
- Deadline misses: 0
- Observed output/state/stale violations: 0

## Evidence boundary

The shadow studies establish a simultaneous, time-uniform statistical contract
over execution events.  They are not latency experiments and do not establish
bitwise deterministic inference.  The c64 stage is fail closed until a c64
terminal canonical path is independently certified.

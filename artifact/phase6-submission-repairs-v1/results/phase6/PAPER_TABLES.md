# Phase 6 paper tables

## Contract scoping repair

| Cell | Quarantine | Threshold | Known failure verified | State violations | P99 | Deadline misses | Wall speedup |
|---|---:|---:|---:|---:|---:|---:|---:|
| 0.6B-c32-d120-burst-ZH | 64 | 0.109376 | True | 0 | 6.107 s | 1266 | 5.905x |

## Feasible live adaptation

| Stage | Switch action | Learned threshold | Risk upper | Verify | Goodput | P99 | Miss | State violations |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| c16_en_initial | new_contract_quarantine | 0.031251 | 0.4997% | 95.62% | 22.032 | 1.297 s | 0 | 0 |
| c16_zh_drift | new_contract_quarantine | 0.015626 | 0.4948% | 95.56% | 28.052 | 0.881 s | 0 | 0 |
| c16_en_return | exact_restore_canary | 0.031251 | 0.4997% | 40.94% | 21.541 | 1.350 s | 0 | 0 |

## Joint capacity admission

| Offered | Historical P99/misses | Action | Live admitted | Guarded P99 | Live misses |
|---|---:|---|---:|---:|---:|
| c64 | 2.889 s / 448 | reshape/backpressure | c16 | 1.397 s | 0 |

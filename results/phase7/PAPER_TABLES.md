# Phase 7 paper-facing tables

## Guarantee taxonomy

| Mechanism | Guarantee | Batch difference | Stale/epoch | Adaptive evidence | Joint SLO |
|---|---|---:|---:|---:|---:|
| ordinary FP16 batch | none | no | no | no | no |
| FP16 singleton | canonical execution | yes, relative to itself | no | no | no |
| BIO/TBIK | operator arithmetic | yes, supported ops | no | no | no |
| LLM-42-style revision | verify every feedback transition | yes | yes | no | no |
| MarginGate-inspired | empirical low-margin verification | no | no | no | no |
| owner/version-only | single-writer version | no | yes | no | no |
| RevTrace strict | canonical state transition | yes | yes | no | yes |
| RevTrace risk-limited | statistical state-risk contract | no | yes | yes | yes |

## c64 offered-load

| Offered | Active | Queued | Active P99 | E2E P99 | Audio goodput | Energy | State risk upper |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 64 | 16 | 48 | 1.942 s | 44.797 s | 34.484 audio-s/s | 8.765 J/audio-s | 0.4932% |

## Delta sensitivity

| Delta | Required zero-error audits | Threshold | Verification | Warm-up cost |
|---:|---:|---:|---:|---:|
| 0.25% | 1,197 | 0.109376 | 5.052% | 2.002x |
| 0.50% | 598 | 0.109376 | 5.052% | 1.000x |
| 1.00% | 299 | 0.109376 | 5.052% | 0.500x |

Sensitivity performance values are offline/counterfactual except for the
shared live c32 reference. The c64 row is a live two-GPU measurement.


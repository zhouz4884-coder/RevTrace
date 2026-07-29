# Phase 7 paper-facing tables

## Guarantee taxonomy

| Mechanism | Guarantee | Authoritative state entry | Replay deterministic | Stale/epoch | Joint SLO |
|---|---|---:|---:|---:|---:|
| ordinary FP16 batch | none | no | no | no | no |
| one canonical draw | authoritative for that commit | yes | no | no | no |
| BIO/TBIK | supported-operator arithmetic | no | yes | no | no |
| LLM-42-style revision | verify every feedback transition | yes | no | yes | no |
| MarginGate-inspired | empirical low-margin verification | no | no | no | no |
| owner/version-only | single-writer version | no | no | yes | no |
| RevTrace authoritative | online canonical draw controls commit | yes | no | yes | yes |
| RevTrace risk-limited | statistical state-risk contract | yes | no | yes | yes |

## c64 offered-load

| Offered | Active | Queued | Active P99 | Guarded P99 | E2E P99 | Audio goodput | Energy |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 64 | 16 | 48 | 1.942 s | 2.042 s (fails guard) | 44.797 s | 34.484 audio-s/s | 8.765 J/audio-s |

Legacy `state_violations=1` is a selected-vs-later-replay field. The corrected
taxonomy is 0 online selection-authority violations, 1 canonical replay state
disagreement, and 0 transaction/stale commits. The realized finite-trace rate
is 1/960; no iid population upper bound is claimed.

## Fresh guarded-capacity point

| Active | Session episodes | Events | P99 | Guarded P99 | Miss | Replay state disagreement | Decision |
|---:|---:|---:|---:|---:|---:|---:|---|
| 14 | 98 | 1,470 | 1.413 s | 1.513 s | 0 | 0 | passes 100 ms headroom |

This c14 run uses a fresh float16 fixed-shape authoritative contract. Its
93.33% verification fraction is dominated by the pre-registered 1,350-event
cold-start evidence window; it is a capacity measurement, not a steady-state
throughput headline.

## Delta sensitivity

| Delta | Required zero-error audits | Threshold | Verification | Warm-up cost |
|---:|---:|---:|---:|---:|
| 0.25% | 1,197 | 0.109376 | 5.052% | 2.002x |
| 0.50% | 598 | 0.109376 | 5.052% | 1.000x |
| 1.00% | 299 | 0.109376 | 5.052% | 0.500x |

Sensitivity performance values are offline/counterfactual except for the
shared live c32 reference. The c64 row is a live two-GPU measurement.

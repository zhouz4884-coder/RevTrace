# RevTrace Phase 2 paper-facing tables

Decision: `PHASE2_RISK_AND_TAIL_GATE_PASS_DETERMINISTIC_CERTIFICATE_UNRESOLVED`

## Active deployed policy

| Model | Wall | GPU-normalized | SLO goodput | Miss | P99 | Output/state/stale |
|---|---:|---:|---:|---:|---:|---:|
| Qwen3-ASR-0.6B | 5.992x | 2.996x | 5.992x | 0/240 | 1.336 s | 0/0/0 |
| Qwen3-ASR-1.7B | 4.830x | 2.415x | 4.830x | 0/240 | 1.730 s | 0/0/0 |

## Five-run replication

| Model | Runs | Wall mean +/- 95% CI | Wall min | GPU min | SLO min | P99 max | Miss/output/state/stale | Cross-run output/state mismatch |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Qwen3-ASR-0.6B | 5 | 6.052 +/- 0.128x (95% CI) | 5.935x | 2.967x | 5.935x | 1.582 s | 0/0/0/0 | 0/0 |
| Qwen3-ASR-1.7B | 5 | 4.949 +/- 0.102x (95% CI) | 4.830x | 2.415x | 4.830x | 1.730 s | 0/0/0/0 | 0/0 |

## Active anytime-risk audit

| Model/policy | Eligible entries | Base audits | Unique job hashes | Caught output/state errors | 95% anytime state-risk upper | Decision |
|---|---:|---:|---:|---:|---:|---|
| Qwen3-ASR-0.6B / v1_tau0.05 | 30,025 | 660 | 209 | 0/0 | 0.480% | `S1_NATURAL_SHADOW_AUDIT_PASS` |
| Qwen3-ASR-1.7B / v2_tau0.10 | 30,155 | 597 | 204 | 0/0 | 0.478% | `S1_NATURAL_SHADOW_AUDIT_PASS` |

## Frozen 1.7B policy repair

| Policy | Tau | Seed | Caught state errors | Upper risk | Verify fraction | Wall | GPU-normalized | Miss | Decision |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| v1_frozen_failure | 0.05 | 20260729 | 1 | 1.668% | 9.58% | 4.972x | 2.486x | 0.00% | `S1_NATURAL_SHADOW_AUDIT_FAIL` |
| v2_independent_validation | 0.10 | 20260730 | 0 | 0.478% | 9.58% | 4.830x | 2.415x | 0.00% | `S1_NATURAL_SHADOW_AUDIT_PASS` |

Boundaries: entries are repeated execution events, not independent utterances; the risk target is disagreement with the frozen canonical execution; zero observed disagreement is not a deterministic arithmetic certificate.

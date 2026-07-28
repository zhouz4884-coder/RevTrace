# RevTrace Phase 3B dual-channel audit report

Decision: **PHASE3B_BOUNDED_DIAGNOSTIC_PASS_VOI_AND_LIVE_SLO_UNRESOLVED**

## Retrospective randomized-label replay

| Strategy | Detection probability | Median verifier requests | Median verifier GPU-s |
|---|---:|---:|---:|
| 2% base only | 0.644 | 283 | 87.70 |
| uniform idle | 0.716 | 330 | 102.27 |
| margin idle | 1.000 | 226 | 70.04 |
| VOI idle | 1.000 | 229 | 70.97 |

Margin-prioritized idle auditing increased detection probability by
0.356 and reduced the
median verifier-request count by
20.1%.

## Negative boundary

VOI did not outperform margin-only: its detection-probability difference was
0.000 and it used
3 more median
verifier requests.  The labelled pool contains two failures but only one unique
failing job.  This supports the dual-channel diagnostic mechanism, not an
amplification-aware VOI superiority claim.

Idle results remain excluded from the formal time-uniform confidence sequence.
The replay uses measured verifier service time but is not a live SLO
experiment; live cancellability and deadline preservation remain unresolved.

# Checkpoint-20 submission evidence closure

Decision: **CHECKPOINT20_HOLDBACK_SUBMISSION_EVIDENCE_PASS**

Mechanism digest: `fa7c07c28da4bf24a52e87a9d83d4671066ee9c1744b4aa21eeddf69c2476583`

## Contract and semantics

- All calibration, risk, five-seed service, semantic, and deployed-quality artifacts are content-addressed under one mechanism digest.
- Holdback semantic patterns: 5/5 passed.
- Fixed authority: GPU 1 FP16 batch-invariant B=12; proposer: GPU 0 ordinary FP16 B=12.

## Five-seed service

| Seed | P50 | P95 | P99 | misses | verify | holdbacks | J/audio-s |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 20260840 | 0.675 | 1.199 | 1.414 | 0 | 10.000% | 18 | 9.239 |
| 20260841 | 0.657 | 1.154 | 1.316 | 0 | 10.000% | 9 | 8.532 |
| 20260842 | 0.656 | 1.180 | 1.262 | 0 | 10.000% | 14 | 8.525 |
| 20260843 | 0.666 | 1.103 | 1.217 | 0 | 10.000% | 10 | 8.645 |
| 20260844 | 0.656 | 1.054 | 1.181 | 0 | 10.000% | 10 | 8.407 |

## Deployed B=12 paired quality

| Language | n | continuous | checkpoint+verify | checkpoint+holdback | checkpoint delta | holdback incremental | total delta | total 95% CI | catastrophic |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Chinese (CER) | 32 | 2.619% | 3.795% | 3.769% | 1.176% | -0.027% | 1.149% | [0.383%, 2.462%] | 0 |
| English (WER) | 32 | 2.590% | 3.492% | 3.519% | 0.902% | 0.027% | 0.929% | [0.270%, 2.051%] | 0 |

- Observed quality: **OBSERVED_QUALITY_TOLERANCE_PASS**.
- Population statement: **POPULATION_NONINFERIORITY_UNRESOLVED**.

## Provisional experience

- Holdbacks: 75 (2.170%).
- Resolved by next high-margin update: 70; by checkpoint authority: 5.
- Provisional lifetime P50/P95/max: 2.00/4.00/6.00 s.
- Displayed-text overwrite mean/P50/P95/max: 7.200%/0.000%/46.589%/100.000%.
- Zero-overwrite resolutions: 69.333%.
- The legacy forward edit metric is retained in raw JSON only; it counts normal appended text and can exceed 100%, so it is not used as the UX claim.

## Excluded branches

- Fixed B=2 burst authority: **NO_GO_EXCLUDED**.
- Dual-lane authority: **NO_GO_EXCLUDED**.
- Legacy B=8 single-engine quality: excluded from deployment claims.

## Evidence boundary

- The observed quality tolerance gate passed only if the paired sample mean delta stayed within 2 percentage points with no catastrophic outlier.
- Population noninferiority is unresolved unless the paired bootstrap upper bound is also at most 2 percentage points.
- The time-uniform risk statement concerns admitted state entries; margin is not a deterministic arithmetic certificate.
- Provisional experience statistics describe this frozen natural workload, not production prevalence.
- Legacy B=8 quality and the B=2 or dual-lane NO-GO branches are excluded from the selected contract.

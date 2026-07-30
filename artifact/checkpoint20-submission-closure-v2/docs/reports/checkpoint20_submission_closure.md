# Checkpoint-20 submission evidence closure

Decision: **REVTRACE_EXPERIMENTAL_EVIDENCE_COMPLETE_FOR_FGCS_SUBMISSION**

Mechanism digest: `fa7c07c28da4bf24a52e87a9d83d4671066ee9c1744b4aa21eeddf69c2476583`

## Contract and semantics

- All calibration, risk, five-seed service, semantic, and deployed-quality artifacts are content-addressed under one mechanism digest.
- Holdback semantic patterns: 5/5 passed.
- Fixed authority: GPU 1 FP16 batch-invariant B=12; proposer: GPU 0 ordinary FP16 B=12.

## Five-seed service

- Five seeds contain 3600 revision opportunities, 3539 committed state transitions, and 61 provisional holdbacks.
- The recorded 10% verification field is exactly the fixed checkpoint-authority fraction (6 of 60 rounds); synchronous low-margin verification is zero under holdback.

| Seed | P50 | P95 | P99 | misses | checkpoint authority | sync low-margin verify | holdbacks | holdback rate | J/audio-s |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 20260840 | 0.675 | 1.199 | 1.414 | 0 | 10.000% | 0 | 18 | 2.778% | 9.239 |
| 20260841 | 0.657 | 1.154 | 1.316 | 0 | 10.000% | 0 | 9 | 1.389% | 8.532 |
| 20260842 | 0.656 | 1.180 | 1.262 | 0 | 10.000% | 0 | 14 | 2.160% | 8.525 |
| 20260843 | 0.666 | 1.103 | 1.217 | 0 | 10.000% | 0 | 10 | 1.543% | 8.645 |
| 20260844 | 0.656 | 1.054 | 1.181 | 0 | 10.000% | 0 | 10 | 1.543% | 8.407 |

## Deployed B=12 paired quality

| Language | n | continuous | checkpoint+verify | checkpoint+holdback | checkpoint delta | holdback incremental | incremental 95% CI | total delta | total 95% CI | catastrophic |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Chinese (CER) | 32 | 2.619% | 3.795% | 3.769% | 1.176% | -0.027% | [-0.071%, 0.000%] | 1.149% | [0.383%, 2.462%] | 0 |
| English (WER) | 32 | 2.590% | 3.492% | 3.519% | 0.902% | 0.027% | [-0.049%, 0.103%] | 0.929% | [0.270%, 2.051%] | 0 |

- Observed quality: **OBSERVED_QUALITY_TOLERANCE_PASS**.
- Population statement: **POPULATION_NONINFERIORITY_UNRESOLVED**.

## Provisional experience

- Holdbacks: 75 (2.170%).
- Resolved by next high-margin update: 70; by checkpoint authority: 5.
- Provisional lifetime P50/P95/max: 2.00/4.00/6.00 s.
- Displayed-text overwrite mean/P50/P95/max: 7.200%/0.000%/46.589%/100.000%.
- Zero-overwrite resolutions: 69.333%.
- Continuous display reconstruction: 69 resolution episodes, 3 multi-holdback episodes, and maximum burst length 3.
- Actual P1->P2->...->authority transition overwrite mean/P95/max: 8.010%/48.731%/100.000%.
- Episode cumulative churn mean/P95/max: 0.087/0.655/1.399.
- Empty provisional events: 0; their defined overwrite boundary is exactly zero.
- The legacy forward edit metric is retained in raw JSON only; it counts normal appended text and can exceed 100%, so it is not used as the UX claim.

## Quality dependence and identity

- Cross-session source reuse: True; cluster bootstrap status: **NOT_IDENTIFIABLE_FROM_THIS_DESIGN**.
- Both language-specific session-source graphs form one connected component, so the paired bootstrap is reported only for the frozen constructed-session sample.
- Post-run identity extension covers 128 byte-hashed audio files, GPU UUIDs, package versions, Qwen-ASR source, the model fingerprint, and the authority runtime.
- Resume lineage audit: **RESUME_QUALITY_ATTESTATION_PASS**; continuous and checkpoint+verify transcripts are byte-for-byte inherited from the declared source artifact.

## Excluded branches

- Fixed B=2 burst authority: **NO_GO_EXCLUDED**.
- Dual-lane authority: **NO_GO_EXCLUDED**.
- Legacy B=8 single-engine quality: excluded from deployment claims.

## Evidence boundary

- The observed quality tolerance gate passed only if the paired sample mean delta stayed within 2 percentage points with no catastrophic outlier.
- Population noninferiority is unresolved unless the paired bootstrap upper bound is also at most 2 percentage points.
- The time-uniform risk statement concerns admitted state entries; margin is not a deterministic arithmetic certificate.
- Provisional experience statistics describe this frozen natural workload, not production prevalence.
- The paired bootstrap resamples fixed constructed sessions; cross-session source reuse prevents interpreting it as an independent-source population interval.
- The identity extension is a post-run content attestation and does not retroactively alter the frozen mechanism digest.
- Live seed runner source is a retrospectively frozen repository snapshot because those raw JSON files did not embed a runner SHA; quality and semantic runners have at-run SHA provenance.
- Legacy B=8 quality and the B=2 or dual-lane NO-GO branches are excluded from the selected contract.

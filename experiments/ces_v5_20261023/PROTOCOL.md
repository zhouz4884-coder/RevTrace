# RevTrace CES V5 bounded implementation and pilot

Authorized 2026-10-23 after the user selected the proposed implementation pace.
The immediate deliverable is an executable minimal V5, CPU safety regressions,
and an audited real dual-RTX3090 pilot with a decision about the next experiment.

Baseline public archive: `01f6e04aa88cf704c129242e6bbdaf42de159525`.
Executed V4 source: `e0aeae1b418644c378dde331c59b55fc5948b40f`.
New isolated source branch: `codex/ces-v5-20261023`.

## Scientific priority

Prefer the simplest combination producing repeatable system improvements.
Shared-risk cost calibration and deadline scheduling are valid useful outcomes.
An additional causal planner must justify its extra complexity, but its failure
does not invalidate an effective simpler system integration.

## Implementation scope

1. Shared physical Verify/Fallback risk estimates and row/lease accounting.
2. Actual Consumer first-legal observation acknowledgements for residual D/C
   obligations. Already displayed frontiers retain their pending Commit value.
3. Simple progress-aware evidence scheduling; a separately labelled GPU0
   deadline-order variant, using only legal jobs at physical dispatch boundaries.
4. Existing complete correct-context FP32 verification and paid FP32 fallback,
   independent FP32 generation, fine=2 s, rho=1, two fixed GPUs, original
   Parent/Frontier/Contract/A/B/C/D/D1 and WAL semantics.

No ready commit may be delayed to collect provisional display credit. First
legal visibility, retractions and commit-aligned visibility remain separate
metrics. Full run wall includes arrival, paid old work, drain and Consumer.
Unfinished requested frontiers remain in the accounting denominator.

## Staged evidence

The old V4 validation sources are now diagnostic development material. Reusing
them in this pilot is explicitly not a new independent confirmation. Calibration
is frozen before pilot execution and source identities are recorded. Any future
confirmatory study requires a newly frozen independent source pool.

CPU fixtures, historical cost calibration, paid GPU oracle controls and actual
online serving results are labelled separately. All execution attempts, failures
and negative effects are retained. No pilot observations are silently omitted.

The exact method list, source pool, arrival schedule, repetitions, risk
parameters and pilot continuation gates will be recorded in `PILOT_FREEZE.json`
before the first GPU cell. A successful bounded pilot is not automatically a
large formal matrix. GPU processes are launched only after current resource
ownership checks; other tasks are never terminated.

## Delivery

Deliver actual source identity, frozen configurations, environment, raw 8 TB
locations and hashes, CPU logs, per-cell and paired summaries, independent
safety/metric audit, diagnosis and GO/NO-GO for the tested next step. Preserve
the manuscript and the prior frozen study. Bounded audited evidence may be
synced to the already authorized GitHub repository after completion.

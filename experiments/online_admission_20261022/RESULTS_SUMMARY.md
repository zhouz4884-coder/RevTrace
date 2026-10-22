# Completed online study: results and decisions

Experiment:REVTRACE-ONLINE-ADMISSION-20261022. Real serving evidence is separate
from fixed-future/Oracle GPU diagnostics and read-only CPU reconstruction.

## Completion and audit

72/72 formal cells finished; no unfinished source or formal/post-processing STOP.
Independent raw certificate/WAL/consumer replay passed all72. The post-serving
actual processor reconstruction rehashed1,562 physical batches. This is CPU
reprocessing of recorded actual inputs, not generation on a new Canonical Parent.
Runtime119-file SHA256 verification and model/audio rehash passed after serving.

## Observable harm and selection alternatives

Full-source English WER uses764 reference words. Unprotected clean is16 errors;
F2 produces48 (sync16) or50 (cohort8). Fine, Score and Strict remain16; DGFT and
Standard Coarse produce17 in both clean and F2. No formal authority admission hit
the generation cap. F2 is injected, so these numbers do not estimate incidence.

All96 accepted unsafe F2-origin roots have real subsequent post-install Proposer
neural use. The32 independently generated-reference-known bad roots also have
that use. The audit conservatively follows post-install dependencies; it does
not claim every mismatch harms quality. Processing-only later Authority targets
are not counted as neural generation.

The sampled160 generated-reference targets comprise Score64/Strict64/unsafe32.
Accepted counts are31/32/32, with accepted-reference mismatches0/0/32. Labels are
diagnostic r0 targets across the same16 sources and two loads/traffic arms, not160
independent speakers or full labels for all admissions.

The32 fixed-future GPU controls (16 sources x two load-derived contexts) changed
newly generated Z in32 cases and final text in15. Word-error worse/equal/better
counts are13/17/2;7 sources were harmed in at least one context. Operator-control
error totals60/764 and62/764 must not be substituted for online48/764 and50/764.

## Online service comparison

Sync16/F2, medians across3 fresh runs. GPU energy is J/audio-s. Goodput uses
Display2s/Commit8s per common frontier; no row passed whole-run dual P99 here.

| Policy | Goodput | Display P99 s | Commit P99 s | GPU J/audio-s | WER % |
|---|---:|---:|---:|---:|---:|
| Fine independent FP32 Authority |10.653708|2.473368|4.753619|35.967247|2.094241|
| Correct-context Score+Fallback |5.140784|9.030128|9.698726|42.050584|2.094241|
| Strict Verify+Fallback |5.199830|10.659378|10.695980|42.412023|2.094241|
| DGFT Coarse |9.127384|3.929775|7.038643|31.109058|2.225131|
| Standard Safe Async Coarse |9.041587|3.973417|7.074341|31.073522|2.225131|
| Unprotected negative control |10.269711|2.320867|2.527304|24.423462|6.282723|

Effect estimates below are medians of paired per-repeat relative differences,
**not ratios of the separately reported medians**.

| Load/traffic | DGFT comparator | Goodput paired change [95% interval] | GPU energy paired change |
|---|---|---|---:|
|sync16/F2|Strict|+75.57% [+30.58%,+82.84%]|-26.73%|
|sync16/F2|Score|+77.55% [+29.71%,+91.35%]|-26.11%|
|sync16/F2|Fine|-19.84% [-25.05%,-12.29%]|-13.43%|
|sync16/clean|Fine|+7.31% [-9.65%,+32.39%]|-14.26%|
|sync16/clean|Strict|+19.58% [-9.59%,+53.73%]|-4.05%|
|cohort8/clean|Strict|-0.17% [-0.97%,+1.43%]|+2.39%|
|cohort8/F2|Fine|-11.72% [-18.26%,-6.99%]|-9.41%|

Strict/Score already use a strengthened paid selective fresh FP32 fallback,
preserving failed-row processed bytes with a full-layout safety guard. Neither
uses prohibited KV reuse. Their success cannot be dismissed as a semantic gap;
their measured verification/wait/fallback costs cannot be assumed away either.
Standard Safe Async is the full positive control, not an incomplete strawman.

## Quality and predeclared decisions

DGFT minus Fine/Score/Strict: WER+0.130890pp (17 versus16 errors/764), paired95%
interval[-0.280112,+0.534045]pp. The upper bound exceeds the frozen+0.5pp margin:
**quality noninferiority is NOT ESTABLISHED**. The interval includes zero; it is
not evidence that loss significantly exceeds0.5pp. CER point delta+0.085010pp.

All four load/traffic strata fail the predeclared overall best-legal-baseline
Goodput, strict Pareto and shared-contract-qualified cost gates. Literal no-loss
also fails. Do not replace those gates with a selected favourable comparison.

## Scientific interpretation

* C1 strengthened: actual future neural consumption and harmful outcomes are
  demonstrated under a controlled reachable fault channel, with legal selection
  alternatives tested. Provenance/selection guarantees are not truth/completeness.
* C2 bounded, not upgraded to universal superiority: the present implementation
  has a measured energy/latency/quality frontier and strong gains relative to
  verification under sync16/F2, but Fine is better on primary Goodput there and
  inexpensive verification is competitive in clean/lower-load regimes.
* C3 is retained from the separate recovery campaigns, not retested or inflated
  by this study. No new Elastic, KV, DAG or recovery algorithm is claimed.

These are experimental decisions, not a manuscript rewrite or an acceptance
probability estimate. The user's follow-up asks for raw-clock C2 bottleneck
diagnosis and a fair improvement plan; that work is explicitly pending.

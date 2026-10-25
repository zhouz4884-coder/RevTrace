# Stage D bounded confirmation design

Frozen before new-speaker GPU consumption. No selection of audio or decision
parameters on held-out results. Development uses the existing16-source cohort;
confirmation uses the metadata-selected16 new audio SHA and16 unseen speakers
in heldout_source_v1 (manifest d34d40df9dc3e000a50286cf5617aff32775b6dea341c228d593d7b7ffa542bd).

After A/C and corrected B gates:

* Always Fine, full Standard Safe Async and Fine-anchor Cost Gate are mandatory.
* B's certified shared operator is enabled for every applicable method only if
  its frozen equivalence and >5% operator-cost gate passes. If enabled, retain
  original Fine as an additional isolation arm; never give it only to V6.
* The causal-risk arm is conditional on the separately frozen C gate and a
  supported observable stratum. If unavailable, label the new causal algorithm
  NO-GO and evaluate the eligible cost-anchor system, not a made-up risk weight.

Development: Mixed-F2, sync and staggered, three counterbalanced fresh-process
repeats per eligible method. Confirmation: clean and Mixed-F2, both arrivals,
three counterbalanced repeats. Baseline mandatory arms give18+36 serving runs.
Fine=2s/rho1, FP16 GPU0, FP32 GPU1, row-complete, same release/consumer/WAL and
2s display/8s commit deadlines. All unfinished requests remain in the metrics.
Every actual numerical history is audited independently; no token-equivalence
assumption across methods or concatenated trajectory oracle.

Primary claim gate: a new C2 algorithm needs positive paired Goodput or same-
quality energy benefit against both matching Fine and Standard in independent
Mixed, with repeated-run support and no safety/quality regression hidden by
averaging. Report per-arrival failures, full whole-run dual-P99 pass counts and
small-n uncertainty. Exact-cache speed or a shared fallback operator is not an
exclusive state-causal algorithm contribution. No success threshold is loosened
after seeing results; no automatic next tuning cycle or manuscript editing.

# Pre-result complete32 / paired8 speaker report

Pure stdlib, no model/raw trace re-execution. **Source and controls were written before reading any new service results; no development execution.** Root freezes the independent complete source and fixed statistical contract, runs formal controls/preflight, then uses it on the full completed queue. No changes to service/source selection/reference/paper/CURRENT.

Scope is fixed at32cells /8distinct speakers, two strategies ×two fresh repeats. Old four-speaker matched/resident sensitivity banks are excluded. All original offered audio and partial EOS remain. Negative source/policy effects and missing/unbounded P99 remain; no favorable-result gate.

## Input config

After all32 service cells finish:

```text
python -B make_report_config.py --service-plan FROZEN_SERVICE_PLAN --campaign COMPLETE_SERVICE_ROOT --out NEW_CONFIG.json --raw-out NEW_8TB_REPORT_ROOT [--c4-summary COMPLETE_C4_SUMMARY --c4-gate COMPLETE_C4_GATE]
```

Config binds complete service PLAN, campaign SUMMARY/GATE/CONFIG/environment/runrecord, everycell's actual CONFIG/SUMMARY/GATE/EXTERNAL_NEW_TEST_AUDIT, and each original frozen cell config. Full32 IDs must match; never chooses a subset. C4files may be pending initially, but both are supplied together when final. The optional pending report is explicitly PERFORMANCE_COMPLETE_C4_PENDING and does not infer zero illegality from task/reference PASS.

C4final schema follows the agreed closure interface: PASS_COMPLETE_ORIGINAL_C4_CONFIRM32_TRACE_CLOSURE,32complete/passed cases,8sources, c4dde original checker,NN4f, both pending flags false. Everycase keeps PASS_UNCHANGED_C4_ACTUAL_TRACE, original checker PASS/35controls, original SourceIdentity and input-SHA equality; complete selected-step denominator comes from the source frames. Repeated35controls are not1120fault types.

Formal entry: `report_confirmation.py --config ... --manifest ... --prelaunch ...`. Prelaunch fields are config_sha256 and report CURRENT/noarg receipt path/SHA. Actual independent source and all input bytes are checked; actual environment/run record precede aggregation. Output remains8TB.

## Statistics, fixed before results

Source order is sorted speaker_id/source_id. For each source, combine both timing repeats inside each policy. Report all eight paired percentage-point gains and source-level credit/energy. Then use **stdlib random.Random(20261102),20,000 draws of8speakers with replacement** (`randrange(8)`). Policies and the two repeats are never split. Both estimands are always reported:

1. Primary: resampled ratio of summed credits to summed offered audio, then Full-call−Conservative inpp.
2. Secondary/source consistency: mean of eight per-speaker pairedpp differences.

Each95%percentile interval uses linear interpolation at index `(n-1)*p`,p=.025/.975. No clipping, one-sided rescue, switching estimator, source removal, frontier/transition/repeat pseudoreplication or seed search. Full20,000draws and sampled source indices stay in8TB raw; bounded PAPER_DATA includes point estimates/CIs.

Per-policy output: all offered/credit totals and duration-weighted%, original D2/C8 passes over16trials, original per-run D99/C99 median/range, EOS/missing counts, common model-drain boardJ. P99 is never recomputed by pooling frontiers; null/missing/unbounded rows are not silently dropped. Task/full originalstates/C/IDs and existing independent a13 audit must agree. Original quality is read unchanged, checked equal across both policies/repeats, then counted **once per source** for the unique-character CER.

Reference/model-generation costs are separate; the report does not recategorize proxy/reference GPU computation as serving success. C4closure remains its own evidence class. Confidence intervals describe this eight-speaker resampling experiment, not production prevalence.

Formal small controls: `python -B -m unittest -v test_report_controls` (eight distinct controls). They include complete-size/credit bounds, negative effects, differing mean-vs-weighted estimands, deterministic source resampling, linear percentile, and missingP99. No controls have been run in development.

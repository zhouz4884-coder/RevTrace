# Original C4 actual-trace closure for this NN16 cost bank

Minimal pure-standard-library orchestration. The fixed original checker is
`c4dde9ea9c7abf80fae084bc2293e193262c71e6` (`run_trace.py` plus its full original
manifest). The actual neural source remains NN4f
`4f4c3caba2b1068951d7a566e7d9e5aa6fc25f47`. This controller is a third source role.
It changes no original checking algorithm, safety rule, trace, neural result,
deadline, cost observation, or source label. It launches no model or GPU code.

Freeze this complete source under its own Git commit/manifest/bundle and run
the root no-argument preflight before controls or actual execution. Use the
frozen experiment Python and `-B`; set test TMPDIR/TEMP on the 8 TB disk.

Controller controls (10 named tests, no child/checker/NN launch):

```
python -B -m unittest -v test_c4_driver_controls
```

Before actual execution, root freezes a prelaunch JSON with these fields:

- `plan_sha256`, `nn_summary_sha256`, `nn_gate_sha256`, `nn_run_record_sha256`;
- `controller_manifest_sha256`, `checker_manifest_sha256`;
- `checker_timeout_seconds` (CLI default120);
- `NN16_complete_and_exclusive_window_released: true`;
- `root_noarg_preflight`, `root_noarg_preflight_sha256` for THIS controller.

Actual CLI, after all16 original NN terminal gates pass and resource exclusivity
has been released:

```
python -B run_c4_campaign.py \
  --plan /path/to/cost_plan_v1/PLAN.json \
  --manifest /path/to/COST_C4_DRIVER_V1_SOURCE.json \
  --checker-source /path/to/original/trace_source_v2 \
  --checker-manifest /path/to/original/TRACE_SOURCE_v2.json \
  --prelaunch /path/to/new/PRELAUNCH.json \
  --nn-summary /8TB/results/.../cost_nn_v1_campaign/SUMMARY.json \
  --nn-gate /8TB/results/.../cost_nn_v1_campaign/GATE.json \
  --nn-run-record /8TB/results/.../cost_nn_v1_campaign/RUN_RECORD.json \
  --out /8TB/results/revtrace/dsn_continuity_cost_20261102/cost_c4_closure_v1
```

No existing output can be overwritten. Every plan cell maps its own original
raw CONFIG, full facts, publications, Consumer, ORIGIN, ingress and ALL numeric
Owner attempt directories (dispatch/result/Owner events/policy audit). Input
byte lengths and SHA are frozen before each original checker child, then
rechecked after it. The original C4 checker also independently enforces its
complete-frame, original-call, durable-state, Consumer and original-clock rules.

The original35 checker controls repeat for every case; they are35 distinct
controls, not560 independent fault types. Failed cases and their exact child
logs/gates are retained and every remaining planned cell is explicitly checked
or failed. No outcome-based omission or altered fallback is allowed.

`GATE.json` and `ROOT_ACTUAL_TRACE_RECHECK_CLOSURE.json` set
`root_actual_trace_recheck_pending=false` only after all16 unchanged C4 checks
pass. They bind the original NN driver's pending gate by SHA. The original
driver `GATE.json`, original per-NN pending entry, source and raw files remain
unchanged; the separate closure receipt completes that planned obligation.
Root may use the bound closure receipt in the final combined release gate.

# Fixed32 actual-service trace closure using unchanged original C4

Pure-stdlib orchestration only. Original checker remains
`c4dde9ea9c7abf80fae084bc2293e193262c71e6` with its complete6-file manifest;
actual neural source remains NN4f
`4f4c3caba2b1068951d7a566e7d9e5aa6fc25f47`; production support remains
`a13fa0a335529dc188f7e738877a3acd027ce4a7`. This new controller is a separate
source role. It imports/runs no neural or GPU implementation.

Root freezes this source and full manifest/bundle, records environment/config/
out on8TB, and performs the no-argument controller gate. Only after the WHOLE
32-cell service queue releases its exclusive resource window run:

```
python -B -m unittest -v test_c4_driver_controls
```

There are12 controller/schema controls. They do not start the original checker,
models, inference or actual trace analysis. The original35 controls repeat in
each subsequent C4 actual case; this is35 distinct controls, not1120 fault types.

Freeze prelaunch fields `plan_sha256`, `service_summary_sha256`,
`service_gate_sha256`, `service_run_record_sha256`,
`controller_manifest_sha256`, `checker_manifest_sha256`,
`checker_timeout_seconds` (default120),
`NN32_complete_and_exclusive_window_released:true`,
`root_noarg_preflight` and `root_noarg_preflight_sha256` for THIS controller.

Actual CLI, after all32 original terminal task/semantic gates exist:

```
python -B run_c4_campaign.py \
  --plan /path/to/frozen/CONFIRMATION_PLAN.json \
  --manifest /path/to/CONFIRMATION_C4_V1_SOURCE.json \
  --checker-source /path/to/unchanged/trace_source_v2 \
  --checker-manifest /path/to/unchanged/TRACE_SOURCE_v2.json \
  --prelaunch /path/to/NEW_PRELAUNCH.json \
  --service-summary /8TB/.../service/SUMMARY.json \
  --service-gate /8TB/.../service/GATE.json \
  --service-run-record /8TB/.../service/RUN_RECORD.json \
  --out /8TB/.../confirm32_original_c4_v1
```

This fixed study is8 speakers×2 strategies×2fresh=32. All planned IDs, original
outputs, per-speaker reverse/GPU roles and task receipts must match; SLO misses
do not prune structural checks. Each actual original config/fact/publication/
Consumer/ORIGIN/ingress plus ALL numeric Owner epoch directories and complete
dispatch/result/Owner-event/policy logs gets its byte/SHA input manifest before
the unchanged original `run_trace.py` child. Normal and recovery/fault log
schemas use the same complete Owner enumeration. No hidden epoch omission or
relabelling of reference-only/CPU records is allowed.

Each passing case retains original C4 summary/gate hashes, actual/NN/checker/
controller roles, input SHA equality before/after and the exact expected
half-second/EOS fresh selected-transition count. All cases are checked or
explicitly failed; none skipped. Every original35 controls and actual trace
gate must pass. No opaque success boolean can replace original checker output.

Terminal summary/gate schema agreed with the independent report consumer:

- `status: PASS_COMPLETE_ORIGINAL_C4_CONFIRM32_TRACE_CLOSURE` only32/32PASS;
- `planned_cells/completed_cells/passed_cells:32`, `failed_cells:0`,
  `expected_source_count:8`;
- `actual_checker_source_commit:c4dde...`, `actual_NN_source_commit:4f4c...`,
  `code_commit` actual new controller; all full identities in `execution_roles`;
- `Root_actual_trace_audit_pending:false` and
  `root_actual_trace_recheck_pending:false` together;
- `cells[]` identity `cell_id/source_id/speaker_id/strategy/repeat`, original
  raw path, `status:PASS_UNCHANGED_C4_ACTUAL_TRACE`, original `checker_summary`,
  original checker summary/gate SHA, `input_SHA_before_after_equal:true`,
  `expected_original_selected_steps`.

Failures use `FAIL_OR_INCOMPLETE_ORIGINAL_C4_CLOSURE_PRESERVED`, keep pending
flags true and preserve all case errors/logs. The original service pending gate
and `ROOT_ACTUAL_TRACE_RECHECK_ENTRY.json` remain unchanged and are bound by SHA
in a separate final closure receipt. This closes a planned scientific obligation;
it is not a new independent fault campaign, proof of GPU arithmetic, or human
quality result.

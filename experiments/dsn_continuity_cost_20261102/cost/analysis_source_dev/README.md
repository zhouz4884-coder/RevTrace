# Cost aggregation and original-probe clock-floor calibration

New independent source; **not executed in development**. Observer3cf and driverb164 remain frozen and untouched. Root must freeze this complete source and rerun controls with full IDs/config/environment/records before any calibration or aggregate. All raw/output stays on8TB.

## Sequence

1. Wait until NN16 is terminal. `build_analysis_plan.py` refuses to hash inputs before its original driver gate reports `COMPLETE_FROZEN_COST_NN_CAMPAIGN`; do not run it during the exclusive GPU window.
2. Freeze analysis inputs using `build_analysis_plan.py --cpu-campaign ... --nn-campaign ... --observer-source ... --observer-manifest ... --driver-source ... --driver-manifest ... --out NEW_CONFIG_DIR --raw-root NEW_8TB_ANALYSIS_ROOT`.
3. Root writes a calibration prelaunch record binding CALIBRATION.json SHA and its analysis CURRENT/noarg receipt. Set `CUDA_VISIBLE_DEVICES=''`. Run `calibrate_clock_floor.py --config CALIBRATION.json --manifest ANALYSIS_MANIFEST --prelaunch CALIBRATION_PRELAUNCH`.
4. Root then freezes both terminal calibration SUMMARY/GATE files in aggregate prelaunch `calibration_inputs` using the same `{absolute_path:{bytes,sha256}}` inventory schema. This prevents a future unbound calibration result from being substituted. Run `aggregate_cost.py --config AGGREGATE.json --manifest ANALYSIS_MANIFEST --prelaunch AGGREGATE_PRELAUNCH`.

Both prelaunch records require `config_sha256`, `root_noarg_preflight`, `root_noarg_preflight_sha256`. The actual independent analysis checkout/complete manifest is verified. Each entry writes its own actual environment and run record before measurement/aggregation. Original NN4f, COST_V1 observer3cf and production driverb164 retain separate execution identities.

## Clock control

Fixed4096calls ×8repeats,512warmup; deterministic alternating bare/wrapped order. The original, byte-verified `CostProbe` is imported and wraps a null target without installing protocol or model modules. Bare and wrapped **batch** wall/threadCPU/processCPU capture total loop/observer differences. Separate bare single-call samples use the identical clock ordering. Original wrapped inner span distributions are exported in full to8TB.

The original meter reads `threadCPU→processCPU→wall` before the target and `wall→processCPU→threadCPU` after it. Thus the CPU bracket surrounds extra clock calls, and a microshort target can show CPU>wall. This is a meter-floor/bracket property, not negative application blocking. Null calibration is a lower-reference resolution diagnostic; metadata, nesting and actual objects may cost more. **Never subtract the null floor** or relabel wall−CPU as lock wait. Calls within10×the null-reference median are annotated heuristically, with no claim that this is an error bound.

## Aggregate

CPU12 is retained by source/policy/fresh repeat. Complete FactStore/Consumer replay, standalone input-materialization/owned-binding probes and actual NN path footprints are separate accounts. Main paper CSV includes only coarse FactStore commit, full Consumer apply and actual fsync families. They overlap inclusively and are never summed. Per-run observed means and fresh-run min/median/max are not population confidence intervals. Frozen NN summaries provide median threadCPU and exclusive sums, so missing inclusive per-service threadCPU means remain null rather than inferred.

NN16 yields all16 original endpoints and exactly8 source/policy/repeat off/on pairs. Full selected parent/next state/C/IDs digests must agree within each pair for a fixed-task interpretation; mismatch is preserved as a diagnostic gate, with no dropped pair. Actual model/abandoned job counts, Consumer/publication roles and per-worker host intervals remain visible. Host call intervals are neither GPU kernel time nor service wall.

Both-board origin→externally confirmed model-drain energy is independently reintegrated from raw external power and cross-checked against the original driver integral and drain witness. Original SERVICE_END, source energy and Owner export remain distinct. Off/on differences are **total observation impact**, including possible schedule/call-count changes and export; they are not protocol-removal overhead.

Output: bounded PAPER_DATA.json, CSVs for CPU checks/coarse footprints, all observed families,16NN cells and8observation pairs, plus explicit unsubtracted-footprint scope. Full model data, raw spans, facts and power remain8TB. The cost driver’s task/reference/Consumer PASS does not imply zero illegal installs under a separately frozen c4 refinement checker; that safety audit remains Root’s separate evidence.

Formal small controls: `python -B -m unittest -v test_analysis_controls` (six distinct controls, no neural work). No controls or measurements have been executed from this development directory.

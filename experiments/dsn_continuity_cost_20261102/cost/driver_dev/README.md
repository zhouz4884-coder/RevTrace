# Frozen current-cost campaign driver

New independent driver source. **No development tests or experiments have been executed.** Freeze this directory, create its complete manifest and formal run records, then run controls before the campaign. It never modifies observer `3cf7cd10a3ba76958b4173aa20eb6116ac779a39`, original NN4f, old raw or CURRENT.

`run_campaign.py --phase cpu|nn|both` consumes the unchanged observer build_plan output. CPU12 and NN16 must both have their full frozen matrices even for a phase-only launch. Each phase uses its original list order. The initial NN4 validity gate checks source/task/physical release/timing coverage; it never stops based on performance. Technical/identity/semantic/resource failure preserves all results and stops the remaining queue.

Required CLI:

```text
python -B run_campaign.py --phase cpu --plan PLAN.json --manifest DRIVER_MANIFEST.json --prelaunch DRIVER_PRELAUNCH.json --observer-source ORIGINAL_COST_V1_CLEAN_ROOT --observer-manifest COST_V1_MANIFEST.json --support-source ORIGINAL_A13_CLEAN_ROOT --support-manifest A13_MANIFEST.json --out NEW_8TB_CAMPAIGN_DIR
```

`--cpu-timeout` defaults180s, `--nn-timeout` defaults600s. Both must equal the prelaunch values, even for a phase-only run. All new logs, records and results must resolve within the designated8TB mount. Raw cell paths are frozen in the plan; no output is overwritten.

Prelaunch JSON fields:

- `plan_sha256`;
- `root_noarg_preflight`, `root_noarg_preflight_sha256`: Root CURRENT receipt binding the **driver** full commit and complete driver manifest;
- `cpu_timeout_seconds:180`, `nn_timeout_seconds:600`;
- NN/both additionally `exclusive_GPU_window_authorized_by_root:true`, and `asset_byte_gate:{path,sha256}`. That actual current gate must report PASS plus `all_asset_bytes_verified:true`.

The driver separately validates its own source, COST_V1 observer, original NN4f and the complete a13 production-support source/manifest. The latter is **not copied or reimplemented**: its exact `process_cleanup`, `run_paired_campaign.stop_owned_processes`, ExternalObserver, READY/allocator checks and selected-trace/reference audit are imported only after the complete clean a13 tree is verified. Both drivers use pure stdlib; this does not initialize models.

Per-cell PRELAUNCH records are written before Popen, with all three execution roles, actual config/environment/input hashes and raw/summary/gate paths. HANDLE records preserve PID/start_ticks/command SHA. Child start_new_session is enabled. CPU-only phase does not query NVML or take a GPU lease; its timeout cleanup signals only the proved launched CPU session via production PID-generation/group proof. NN failure cleanup uses the complete production Owner/descendant-group and CUDA-release helper, never a global kill. A failed proof/release stops with explicit unverified-release gate.

NN runs preserve original run_trial GATE/SUMMARY, origin, EOS/all-offered and physical drain. Independent a13 audits bind full original states/C/IDs, recount Consumer endpoints, and integrate both physical boards from original origin to externally confirmed model drain. Whole-program safety/refinement is not inferred from a runtime PASS: each cell includes a `ROOT_ACTUAL_TRACE_RECHECK_ENTRY.json` for Root's separately frozen c4 checker. The campaign gate explicitly marks that check pending.

On/off span exports must have exactly one Owner and one Supervisor/Consumer account. Overflow, missing critical families, missing recorded rows or negative-exclusive anomalies fail cost validation. WAL commit counts bind actual durable facts, and Consumer timing counts bind actual publications. CPU replay similarly binds complete-fact and Consumer counts. The frozen observer summarizer keeps inclusive families and separate thread roots; CPU component probes, full-object replay and actual NN timing are not added together or called a protocol-removal tax.

Formal small controls: `python -B -m unittest -v test_driver_controls`. Six distinct controls cover matrix completeness/duplicates/boolean modes, output escape and execution-role command separation. These are contract controls, not serving or benchmark evidence. Production cleanup already has separate process/orphan controls; this source does not claim its six pure controls retest OS/CUDA release.

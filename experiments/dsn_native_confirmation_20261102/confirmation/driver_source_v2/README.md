# Strict new test-speaker confirmation driver

Pure stdlib. **Only source/static work; no development tests/models/remote/CURRENT actions.** Root freezes this independent complete source/manifest, runs formal controls, binds completed selection/reference files, freezes all service configs/plan and prelaunch records, then launches the complete matrix.

## Input interface

Selection receipt status must be `PASS_STRICT_METADATA_SELECTED_SPEAKER_DISJOINT_AUDIO_AVAILABLE`, with `model_calls:0` and `sources[]`: distinct source_id/speaker_id, original_split=`AISHELL1/StreamCorrect/aishell1_testset@16f6fd1e17418f1c4111a18fdd39543813206d96`, split_directory=`StreamCorrect/aishell1_testset`, exact archive_member.path under that bare directory, original PCM16 mono16k header, path/audio_sha256/frames/duration,8–9s original waveform. N is the receipt's metadata-frozen speaker count, passed explicitly as `--expected-sources`. No hard-coded12 or mixed split; smaller strict inventories remain explicit.

Reference receipt status must be `PASS_CONTINUOUS_ORIGINAL_AND_RESTORED_SHORT_REFERENCES`, actual_NN_source_commit4f, generator_source_commit independent, selection_receipt{path,sha256}, exact frozen sources plus source_ids/speaker_ids, reference_details{path,sha256,bytes,expected_steps}, reference_gate{path,sha256}, genesis{path,sha256}. DETAILS retains original list schema `source_id/end/original_full_start_cut/original_full_cut/original_full_result`. All terminal files/hashes and completeN/steps must pass **before** NN configuration freeze. The reference generator and its paid GPU work remain reference-only; this driver does not execute them or count them as service trials/successes.

## Build

```text
python -B make_service_plan.py --manifest DRIVER_MANIFEST --selection-receipt SELECTION_RECEIPT --reference-receipt REFERENCE_RECEIPT --template OLD_FINAL4F_NORMAL_CONFIG --environment FROZEN_SHARED_FP32_ENV --base-source CLEAN_4F --base-manifest ORIGINAL_4F_MANIFEST --support-source CLEAN_A13 --support-manifest ORIGINAL_A13_MANIFEST --expected-sources N --config-dir NEW_8TB_CONFIG_DIR --raw-root NEW_8TB_SERVICE_ROOT --out NEW_PLAN.json
```

The old template must be the single-chain normal4f config. Original backend, decoding, two full workers, full learned-C warmup, no VAD,500ms cadence,2s lookahead,FP32,allocator,240s service cap,D2/C8 and complete EOS are retained. Only new source, primary GPU, identity labels, strategy and completed strict reference bindings vary. Model preload is exactly the unchanged original warmup source plus the current new input. No timing observer is imported.

## Actual per-speaker ABBA

Seed20261102 first shuffles sorted metadata speakers, then chooses and saves each speaker's r0 two-policy order. r1 **directly uses that speaker's saved r0 order[::-1]**. It never derives the order from reversed block parity. Each repeat's two policies have the same GPU role; primary GPU rotates0→1 across repeats. Plan validation checks full4N scope, exact seeded order and each speaker's actual reverse, including odd N. Frozen data are never replaced based on performance, EOS or prediction outcomes.

## Run

```text
python -B run_confirmation.py --plan NEW_PLAN.json --manifest DRIVER_MANIFEST --prelaunch PRELAUNCH.json --out NEW_8TB_SERVICE_ROOT
```

Prelaunch fields: plan_sha256; driver Root CURRENT/noarg receipt path/hash; exclusive_GPU_window_authorized_by_root:true; asset_byte_gate{path,sha256} reporting current PASS/all_asset_bytes_verified and matching original environment assets_manifest_sha256. Environment package/interpreter, actual model/source bytes and the complete clean original4f/a13 trees are revalidated. Each run has separate driver/actualNN/support/selection/reference roles, config/environment hashes, original raw/summary/gate locations and PID/start_ticks/commandSHA before/together with launch.

Directly invokes the untouched original4f resilience_trial.py. ExternalObserver, actual READY/allocator checks, complete selected-state/C/IDs+reference audit, all-offered Consumer endpoints and origin→confirmed model-drain energy use byte-bound original a13 production code. Failure cleanup reuses its full PID-generation/descendant-group/CUDA-release helper, never a global kill. Incomplete/unsafe release fails and stops the queue.

**Performance misses continue the complete matrix.** Only identity, technical, semantic or resource failure stops, preserving results and remaining planned cells. Summary reports every run and per-source two-repeat paired credit/energy, keeping speaker as the acoustic unit. It explicitly marks Root's later separately frozen c4 actual-trace audit pending. Runtime/reference PASS is never relabelled as proof of zero illegal installs.

Formal small controls: `python -B -m unittest -v test_confirmation_controls` (nine distinct controls; no benchmarks/models). V2 changes only the strict versioned split/directory contract and adds one control; frozen6aeV1 is preserved. No controls were executed in development.

# New strict test-speaker service driver: static source ready

Directory `driver_source_dev/`: confirmation_common.py, make_service_plan.py, run_confirmation.py, test_confirmation_controls.py, README.md. **No precommit controls, model calls, raw reruns, remote/CURRENT or paper changes.** Root freezes this independent complete source/manifest and formally runs eight contract controls before launch.

## Receipt interface agreed with both agents

- Selection: `PASS_STRICT_METADATA_SELECTED_SPEAKER_DISJOINT_AUDIO_AVAILABLE`, `model_calls=0`; sources include source_id/speaker_id/path/audio_sha256/frames/duration/header/archive_member/original_split, strictly `StreamCorrect/aishell1_testset`, original PCM16 mono16k8–9s. One waveform per distinct speaker. N is the metadata-frozen count passed explicitly, not forced to12.
- Reference: `PASS_CONTINUOUS_ORIGINAL_AND_RESTORED_SHORT_REFERENCES`, actual_NN_source_commit4f, separate generator identity; bound selection SHA/exact sources, complete source_ids/speaker_ids; terminal DETAILS/GATE/GENESIS path/SHA. DETAILS has original full list schema and expected_steps=sum ceil(frames/8000). Strict full-N/step/hash pass is required before service config freeze.
- Reference generation GPU calls/energy stay reference-only, outside service outcomes and successful serving counts.

## Plan and real execution

`make_service_plan.py` accepts the old final4f single-source normal CONFIG, original shared FP32 environment, clean4f and clean a13 complete manifests, completed receipts, expectedN, new config/raw paths. Full CLI is in source README. It preserves original source settings/backend/decoding/warmup, noVAD/500ms/2s lookahead/two full FP32workers/allocator/D2C8/EOS. Only current new source, labels, strategy and primary GPU vary. It invokes no models.

Each speaker has explicit saved r0 order from seed20261102 metadata permutation; **r1 uses that exact speaker order[::-1]**. Validation checks all4N cells, per-speakerABBA, exact seeded sequence and same-repeat GPU role/repeat0→1 rotation. This avoids the former block-parity cancellation. Both even and odd N are covered by formal controls.

`run_confirmation.py --plan ... --manifest ... --prelaunch ... --out ...` directly launches original4f resilience_trial.py, with no cost observer. It verifies own/4f/a13 identities before each fresh cell. Prelaunch needs planSHA, driver CURRENT/noarg path/SHA, Root exclusiveGPUwindow and current full model-byte gate. All per-cell source/config/environment/reference/selection roles and PID/startticks/commandSHA are recorded.

The original a13 production resource-cleanup, ExternalObserver, actual READY+allocator validation, strict selected C/U/state/IDs reference comparison, actual Consumer endpoint recount and common origin→physical-model-drain energy are reused from their byte-verified clean complete tree. Technical/semantic/resource failures stop and preserve the queue; **performance misses continue every frozen cell**. No selection/threshold/EOS changes after observing results.

Summary contains every cell, within-repeat pairs and source-level two-repeat combined credit/energy with one acoustic unit per speaker. A dedicated ROOT_ACTUAL_TRACE_RECHECK_ENTRY.json hands allraw/source/reference identities to Root's later separately frozen c4 audit; no zero-illegal claim is inferred from runtime PASS.

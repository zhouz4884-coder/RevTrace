# Strict metadata-first audio acquisition

Pure stdlib. **Only source/static work; no precommit tests, network, WAV reads, models, remote or CURRENT changes.** Root freezes this complete independent source/manifest and formally runs eight controls before any acquisition. New data/raw all resolve to the designated8TB mount.

The original1129b7af5001566a223594ccc35cfcbe1c0fa5db acquisition module is byte-vendored. Only its previously validated bounded HTTPS Range, exact localZIP extraction/CRC and staged-range byte verifier are called. Its old four-source main and8–15s inspect function are **never called**. New inspect logic retains complete original PCM16 mono16k WAVs and enforces integer frames128000–144000 (8–9s), without trim/concat/resample/pad.

## Freeze config

```text
python -B make_acquisition_config.py --selection-dir FROZEN_SELECTION_DIR --rule RULE.json --reference-metadata ORIGINAL_REFERENCE_JSON --expected-sources N --dataset-root NEW_8TB_DATASET --raw-out NEW_8TB_RAW --out NEW_CONFIG.json [--staged-ranges FROZEN_SAME_MEMBER_STAGE_INDEX]
```

Inputs are selection99a8's METADATA_SELECTION.json/GATE.json/HISTORICAL_EXCLUSION_INPUTS.json and frozen RULE. Actual metadata-selectedN, primary and each same-speaker cyclic technical_header_fallback_order are immutable. Full original_split namespace is `AISHELL1/StreamCorrect/aishell1_testset@16f6fd1e17418f1c4111a18fdd39543813206d96`; separate split_directory/member paths use `StreamCorrect/aishell1_testset`. No hard-coded4/12 or mixed split.

The metadata-only builder does not open newWAV or reference text. It freezes the established official reference.jsonSHAe040232c…; the acquisition entry checks and parses original `audio_path`/`text_zh` only **after** validating the irrevocable metadata/rule/exclusion/gate lock. GT text is copied unchanged and never selects/replaces a source. Missing/conflicting reference for a technically accepted source stops.

## Formal entry and exact fallback rules

`acquire_audio.py --config CONFIG --manifest COMPLETE_SOURCE_MANIFEST --prelaunch PRELAUNCH`.

Prelaunch fields: config_sha256, root_noarg_preflight and root_noarg_preflight_sha256. Own clean complete source, vendored helper, metadata identity and all inputs are bound before reading candidate data. Actual environment/run records precede transport. Network/CRC/Range failures have exactly three retries of the **same member** or stop. They never advance a candidate. Staged blobs must bind identical public URL, exact Range, bytes/SHA on8TB.

Only after exact ZIP CRC succeeds may invalid WAV header/actual duration move to the next already locked **same-speaker** candidate. Exhausting that speaker stops the complete cohort with preserved partial sources and explicit failed speaker; it never emits reducedN PASS. Root must separately freeze any explicit technical cohort amendment before reference/model work. Historical or newly accepted WAV/PCM hash collision is an independence STOP, never header fallback. No replacement speaker, widened duration or split is authorized.

Accepted WAVs are complete original CRC-verified bytes, created exclusively and made read-only, or compared byte-for-byte against an existing same-source file. WAV and PCM SHA, actual frame duration, original member and fallback index are retained. EveryRange attempt remains8TB; no signed redirects or error URLs are printed.

## Output

SOURCE_RECEIPT.json (and dataset/SOURCE_RECEIPT_v1.json) status `PASS_STRICT_METADATA_SELECTED_SPEAKER_DISJOINT_AUDIO_AVAILABLE` only after all frozenN pass. Fields include acquisition and selection source identities, recipe/catalog/exclusion/metadataSHA, strict split namespace+directory, all complete source specs/reference/header/member, new_speaker_count/new_utterance_count, model_calls=0/gpu_calls=0. `DATA_MANIFEST.json` supplies data_freeze_sha256 without circular hashing; receiptSHA is external inGATE. No reference GPU computation is performed here.

Formal controls: `python -B -m unittest -v test_acquisition_controls` (eight distinct controls, mocked transport only). No development controls were executed.

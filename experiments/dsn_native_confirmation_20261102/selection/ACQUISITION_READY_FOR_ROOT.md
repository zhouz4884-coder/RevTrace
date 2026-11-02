# Strict audio acquisition source: ready for clean freeze

`acquire_source_dev/` contains acquisition_common.py, acquire_audio.py, make_acquisition_config.py, test_acquisition_controls.py, README.md, DEPENDENCIES.json and byte-exact vendor/acquire_selected.py. **No controls, network, audio read, model, remote, CURRENT or paper action was executed.** Only source/static file work occurred.

The original transport dependency is1129b7af5001566a223594ccc35cfcbe1c0fa5db, acquire_selected.py9884bytes/SHA16e7acc64e07c356bf08382f6ed1cff50742385fdb3a2160f030e2acc64401bb. Old main/four-source count/8–15s inspector are not invoked; bounded Range/localZIP extraction+CRC/staged-byte helpers are reused verbatim. New strict fullPCM header/8–9s validation is explicit.

## Interface locked to selection99a8

- METADATA_SELECTION status PENDING_AUDIO, exact N and same-speaker technical_header_fallback_order; RULE, GATE and HISTORICAL_EXCLUSION_INPUTS SHA bound. Metadata flags require no newWAV/reference/model read before lock.
- Full versioned original_split=`AISHELL1/StreamCorrect/aishell1_testset@16f6fd1e17418f1c4111a18fdd39543813206d96`; split_directory/member paths use bare `StreamCorrect/aishell1_testset`. This matches the new driver/reference V2 contracts; old6ae/8995 are untouched.
- All frozen speakers must pass. A source that exhausts header candidates yields explicit FAIL/partial receipt, not a smallerN PASS. Root must separately freeze any technical cohort amendment; no replacement speaker/split/band is authorized.

## Build and launch

After Root freezes source and formally runs eightcontrols:

```text
python -B make_acquisition_config.py --selection-dir FROZEN_SELECTION_OUTPUT --rule FROZEN_RULE --reference-metadata ORIGINAL_REFERENCE_JSON --expected-sources N --dataset-root NEW_8TB_DATASET --raw-out NEW_8TB_ACQUISITION --out NEW_CONFIG.json [--staged-ranges FROZEN_STAGE_INDEX]
python -B acquire_audio.py --config NEW_CONFIG.json --manifest ACQUISITION_MANIFEST --prelaunch PRELAUNCH.json
```

PRELAUNCH binds config_sha256 and Root CURRENT/noarg receipt path/SHA for the acquisition source. Actual execution environment and full run record precede transport. Official reference metadatae040232c… is parsed via original audio_path/text_zh only after metadata/rule/exclusion/gate validation; it is never a candidate-selection signal.

Transport/CRC errors retry exactly the same member3times or STOP. Only CRC-correct invalid header/actual8–9s extent advances the same frozen speaker's next cyclic member. Historical or new selected WAV/PCM hash collision is immediate independence STOP, never header fallback. Missing/conflicting original reference stops, never chooses a different source. Staged bytes must bind exact URL, content-range, compressed+4096 size/SHA and8TB path. No signedredirect/errorURL is logged.

Final SOURCE_RECEIPT status strictAUDIO_AVAILABLE has complete sources, original reference strings, WAV/PCM hashes, header/frame duration/member/index, selection/acquisition identities and originalN. DATA_MANIFEST externalSHA supplies data_freeze_sha256 without self-reference; GATE externally binds receiptSHA. Same receipt is installed into the new dataset root. Existing completed dataset receipts are never overwritten. Models/GPU calls remain0.

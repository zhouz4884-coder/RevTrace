# Original MAGICDATA68 test workload preparation

This source runs on CPU and uses only the Python standard library. It does not
invoke models or use GPU libraries. Original corpus files stay on the experiment
disk; source delivery contains code, tests and bounded receipts only.

The official compressed test archive is acquired unchanged from
https://openslr.magicdatatech.com/resources/68/test_set.tar.gz (2,201,936,013 bytes).
Its HTTP ETag and byte length are pinned in configuration. Transport attempts and
partial files are preserved. Existing complete archives are verified and never
overwritten. SHA256 covers all compressed bytes. Full gzip EOF and tar/member
checks precede selection. No archive checksum is represented as externally
published when only our acquired SHA256 is available.

The separately SHA-bound official test.scp and SPKINFO metadata are path/speaker
metadata. All 24,279 WAV members from all 43 test speakers are scanned and hashed.
The first pass never opens TRANS.txt. It validates RIFF chunks, PCM layout,
original rate/channel/bit depth and frames without decoding audio samples.

Eligible original WAVs are mono, 16,000 Hz, PCM16 and 192,000–320,000 frames
inclusive. Sort eligible speakers lexicographically and take at most four. Per
speaker take the original utterance nearest 256,000 frames; ties use raw source
ID lexicographically. No transcript, model result or measured performance enters
this choice. Fewer than four eligible speakers remain the actual smaller N.
Zero eligible speakers yields an evidenced NO-GO, never a relaxed condition.

Write and fsync IDS_FROZEN.json, including the complete census and archive hashes,
before the second archive pass. The second pass copies only the selected whole
WAVs byte for byte. It never concatenates, trims or resamples them. The selected
reference lookup decodes an official transcript value only when its first key
matches a previously selected raw ID. A matching raw-speaker field, if present,
is removed; the remaining UTF-8 text is preserved, including internal spaces.
SELECTED_TRANSCRIPTS.json binds IDs_FROZEN SHA, selected text, original TRANS
member SHA/size/path and selected row SHA. No unselected text is retained.

ORIGINAL_SELECTION_BANK.json records corpus MAGICDATA68, official test split,
raw and namespaced IDs (MD68_), original compressed archive identity, complete
census, frozen IDs, selected label binding, WAV member byte SHA and PCM data SHA.
It does not use the AISHELL namespace and does not claim a synthesized workload.

Invocation (explicitly frozen config, source manifest, new output directory):

```
CUDA_VISIBLE_DEVICES='' python -B prepare_magicdata.py --config CONFIG.json \
  --manifest PREP_SOURCE_MANIFEST.json --out NEW_OUTPUT --mode controls
CUDA_VISIBLE_DEVICES='' python -B prepare_magicdata.py --config CONFIG.json \
  --manifest PREP_SOURCE_MANIFEST.json --out NEW_OUTPUT --mode acquire_select
```

Required configuration keys: experiment_id, source_commit,
source_manifest_sha256, experiment_disk, archive_path,
selected_audio_directory, archive_url, archive_bytes, allowed_archive_urls,
expected_ETag, metadata_archive, metadata_archive_sha256, test_scp_sha256,
speaker_info_sha256, expected_WAV_members, expected_test_speakers,
maximum_tar_members, maximum_expanded_member_bytes, maximum_single_WAV_bytes,
expected_controls. Optional fields: expected_environment, selection_rule,
official_expected_sha256, maximum_download_attempts,
network_socket_timeout_seconds, maximum_download_wall_seconds.

No raw WAV/archive or transcripts belong in the source Git repository.

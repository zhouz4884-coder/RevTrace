# Original-full references for conditional independent native confirmation

This is a separate **offline neural oracle/reference generator**, not a
service, performance benchmark, or source-selection program. No downloader,
archive scanner, source ranking, fallback selection, training or early-view
projection exists here. The unchanged complete bdfa method runtime is imported
and verified; no execution source is copied or patched.

Preparation is allowed while the old-source campaign runs. Do not invoke the
generator or write a final new-source experiment config until the root's
decision after that campaign. Source code and pure CPU controls can be frozen
now. Neither this README nor a prepared checkout means new references exist.

After that decision, the order is:

1. Select four speaker-disjoint sources by locked metadata rules and a fixed
   seed, excluding all previously used speakers. Check actual WAV header,
   frames, CRC/range acquisition and SHA. Freeze `SOURCE_SELECTION_v1.json`.
   Never inspect model compatibility or responses to choose the sources.
2. Freeze the generator's separate source/manifest, its config, dependency and
   environment hashes, experiment ID, and new raw result location. The method
   source remains `bdfa3b1307d267a5a4caf6484e1ad465c39a592e` throughout.
3. In an explicitly allocated GPU/CPU/IO window, generate original full
   A+C+U references. The exact old source0 1.5-to-2.0-second neural warmup is
   retained, discarded, and reset to genesis. All four new sources then start
   from their own genesis. No temporal offered stream is simulated.
4. Require the complete reference gate and hash `DETAILS.json` mechanically.
   Only then freeze the final timed service plan against those details and
   the unchanged bdfa source. Do not remove or replace sources after outcomes.

The CLI is `python -B original_full_reference.py --plan PLAN.json --manifest
GENERATOR_MANIFEST.json --out NEW_8TB_OUTPUT`. No final PLAN is shipped here.
The future plan must explicitly contain:

| Field | Meaning |
|---|---|
| `experiment_id` | Separate reference-only experiment ID |
| `generator_source_commit`, `generator_source_manifest_sha256` | Actual separate clean generator source |
| `model_runtime_root`, `model_runtime_manifest` | Complete clean bdfa checkout and its fixed manifest |
| `method_config`, `method_config_sha256` | The original bdfa source0 pilot fullspec config, exact SHA `30387d47...` |
| `source_selection_manifest`, `source_selection_manifest_sha256`, `sources` | Locked metadata receipt and identical ordered four source objects |
| `old_task_fidelity_gate`, `old_task_fidelity_gate_sha256` | Actual old69 gate, fixed SHA `79f9355a...` |
| `frozen_environment_record`, `frozen_environment_sha256` | Previously validated native environment |
| `backend`, `corrector_dtype` | Exactly the fixed method backend, FP32 |
| `fixed_old_warmup` | Original source0 audio object, original 24000 cut, `fixed_start=24000`, `fixed_end=32000` |
| `cache_root`, `gpu` | Allocated 8 TB cache and one GPU 0/1 |

The future selection receipt has `metadata_only_before_neural=true`,
`method_source_commit=bdfa...`, `selection_created_utc`, `excluded_speakers`
and ordered `sources`. Each source has `source_id`, `speaker_id`, raw 8 TB
`path`, `audio_sha256`, actual `frames` (8-15 s at 16 kHz), and official
`reference`; archive/header provenance may be additional immutable metadata.
Plan and receipt source objects must be identical, including order.

The method config anchors the original backend and fixed warmup. Runtime and
generator commits are separately checked, package/dtype/TF32 state is recorded,
and all inputs are hashed. The output contains original `selected_correction`,
returned IDs, complete start/end feedback states and full hashes for every
500 ms step **including the final partial EOS and early empty-return steps**.
These records match unchanged `run_service_campaign.audit_cell`'s required
schema. No latency/goodput/service claim is produced.

Thirteen pure stdlib CPU controls exercise source/speaker/metadata locking,
original backend/warmup fidelity, exact call route without speculative hooks,
complete EOS/None preservation, fresh-source identities, unchanged-repeat
values and rejection of altered full-result hashes/paths. They load no model
packages and make no GPU, network, ZIP or audio-file call.

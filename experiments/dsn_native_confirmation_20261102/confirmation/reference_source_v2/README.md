# New-source ORIGINAL short references — NOT RUN

Only this new source is developed. NN4f/59 files, old raw, models, Paper_DSN and
CURRENT remain untouched. No controls or model calls have been executed by the
author. Root must freeze the complete tree, run the 14 CPU controls, bind its
manifest/environment/run and exclusive-GPU prerequisites, then launch.

## What is executed

The actual neural dependency must be a complete clean `4f4c3caba...` checkout,
byte-matched on all59 tracked files. The generator imports only the ORIGINAL
`long_reference` pure `continuous_transitions`, `frontiers`, `compare_edge` and
JsonLines helpers. It never calls the old long-reference main, two-speaker
synthetic recipe or its receipt gate. All new source audio remains complete
8--9-s original utterances selected by metadata first; actualN is not forced12.

One protected FP32 recognizer--corrector loads on the chosen physical GPU, uses
the unchanged old fixed warmup from the template, and resets to original genesis.
For each source: original engine insert_audio/infer executes every500ms and
partialEOS continuously, without between-step restoration. Then each saved
complete start is restored into the ORIGINAL CandidateBridge.full_step twice.
Complete start/end, selected originalC, returnedIDs and native-evaluation flags
must agree. The generated state source marker is actual4f, never relabeledBDFA.

On the first failed boundary per source, preserve the original path and run
two further same-input full-step calls and one original continuous-prefix
repeat. A prefix uses the original source EOS rule, never fakeEOS at stop_at.
Diagnostics never replace reference output. Execution exceptions preserve the
pending original input and stop remaining sources after controls; mismatches
retain all attempted comparisons. Root may diagnose/repair using a new source,
not replace a metadata-selected source based on output/performance.

## Plan and run

```
python -B make_reference_plan.py --template <old final4f service config> \
  --selection-receipt <terminal audio-ready speaker-disjoint receipt> \
  --environment <frozen original interpreter+packages record> \
  --base-source <clean original4f> --base-manifest <original59-file manifest> \
  --asset-byte-gate <Root actual full-model-byte PASS gate> \
  --gpu 0 --gpu-uuid <actual physical UUID> --cache-root <8TB cache> \
  --raw-out <fresh8TB reference result> --out <frozen reference PLAN.json>

python -B run_reference.py --plan PLAN.json --manifest GENERATOR_SOURCE.json \
  --prelaunch ROOT_REFERENCE_PRELAUNCH.json
```

Prelaunch requires planSHA, no-argumentCURRENT receipt path/SHA for this
generator source, and `exclusive_GPU_window_authorized_by_root:true`. Existing
CUDA owners or a different GPUUUID fail before model load. The original author
checkout, all59 neural source bytes, frozen environment/packages, model-byte
gate, complete selected audio/header/PCM and old warmup source are checked.

Selection receipt must use
`PASS_STRICT_METADATA_SELECTED_SPEAKER_DISJOINT_AUDIO_AVAILABLE`, `sources`,
`metadata_first:true`, integer`model_calls:0`, and `no_concat/no_trim/no_resample`.
All source objects, hashes and order bind into the reference plan. Missing use
evidence is not silently treated as zero. No source selection is done here.

V2 binds `original_split` to the complete namespace
`AISHELL1/StreamCorrect/aishell1_testset@16f6fd1e17418f1c4111a18fdd39543813206d96`.
It separately requires `split_directory=StreamCorrect/aishell1_testset` and the
bare archive member `StreamCorrect/aishell1_testset/<source_id>.wav`. This is a
strict identity alignment before any data/model run, not a new data split or
method change. The frozen8995 predecessor remains untouched; one new control
rejects directory/revision/member substitutions. No tests have run from V2.

## Driver interface

Only a complete pass emits REFERENCE_RECEIPT.json:

* status `PASS_CONTINUOUS_ORIGINAL_AND_RESTORED_SHORT_REFERENCES`;
* actual_NN_source_commit4f plus separate generator_source_commit;
* selection_receipt path/SHA and exact ordered sources/source_ids/speaker_ids;
* reference_details path/SHA/bytes/expected_steps to REFERENCE_DETAILS.json;
* reference_gate path/SHA; genesis path/SHA to all original source initial cuts;
* reference_kind `strict`, two restored repeats/edge, paid reference ledger;
* reference_onlytrue/actual_serving_runs0; external resource closure still owed.

DETAILS is the list schema already consumed by a13/resilience_metrics:
source_id/end/original_full_start_cut/original_full_cut/original_full_result.
Root's service configs bind these terminal bytes only after the original
reference process exits and CUDA owners are externally verified empty.

## Accounting

Original BoundedPower records both boards from before torch/CUDA/model import
through load, fixed warmup, reference calls and failure controls. This is paid
reference work, not serving energy or latency. Actual helper/step attempts,
completed steps and native_model_evaluatedtrue are separately counted; a
buffer-only call is not mislabeled a new neural inference. Loader-internal
neural calls are not instrumented, but their elapsed/energy lies in the stated
reference window. No oracle computation is made free in service comparisons.

All model/data/cache/raw remain8TB. Only bounded receipts/configs/manifests/
summaries belong in GitHub. If this tree is frozen, stop editing it and create
a new source_v2 for any repair. Do not run this during another timed GPU bank.

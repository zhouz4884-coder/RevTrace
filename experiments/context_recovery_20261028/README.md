# RevTrace context/recovery research — 2026-10-28 checkpoint

Baseline evidence archive: `4af44aac707ba84119ea13f05f6a9130c869dec4`.
Baseline runtime v7: `e1511deb6766ce68084128436907b8e2b8e3d417`.
The user has prioritized cross-contract R7/R8/R9 diagnosis, a new untouched
holdout, paid context-recovery feasibility, four-arm real cold recovery, and
native multi-cycle neural applications. This research remains in progress.

## Completed real cold-recovery pilot

Four fresh episodes use the same logical fault: session0 at192000samples,
after real WAL sync and before publication, with the same full logical cut.
Each prefix uses the original initialization; only restart ordering changes.
Both methods use the full native renderer and identical resources.

| Method / startup order | Old facts visible, s | First new certified fact, s | Precrash debt cleared, s |
|---|---:|---:|---:|
| RevTrace / full renderer first |13.762|31.034|32.932|
| RevTrace / workers and renderer overlap |14.437|19.406|21.339|
| Complete Standard / full renderer first |13.812|31.156|32.987|
| Complete Standard / workers and renderer overlap |14.693|19.190|20.988|

The optimization reduces time to new certified computation by about11.6–12.0s
in this pilot, while old-fact visibility becomes0.68–0.88s slower. Standard
gets the same benefit. These are one-repeat development observations, not a
statistical superiority result or a new exclusive scheduling algorithm.
All four whole-episode D2/C8 P99 gates fail after the cold interruption.
Their measured WER is identical at6.0606%;18.51s of previously accepted audio
debt survives and is completed. Filesystem caches remain warm/unspecified;
the processes and GPU model weights are cold-reloaded, not the entire host.

The completed CPU audit independently rebuilds the real processed batch inputs,
same-job native P/text and durable text bindings, and directly recounts the
three Consumer clocks. All four pass with zero new neural inference. Its
source is separate from the tested runtime; no production admit/step function
is used as its proof. It does not certify model truth or arbitrary faults.

## Prospective untouched holdout: frozen, not evaluated

48 reconstructed90s sessions from24 new speaker/chapter clusters and318
nonreused original utterances have been frozen. Membership is determined by
metadata and duration only. It has zero recorded utterance/speaker overlap
with the conservative retained-archive inventory, and zero ASR model calls.
Two sessions from one speaker are one cluster, not two independent speakers.

The inputs come from the first two content-hashed public LibriSpeech train.100
shards at dataset commit `fed4943ea9bdc207dc01b65e0928dd100e18a2a1`.
They preserve same-chapter numeric utterance order with0.1s separators and
whole utterances; these are reconstructed read-speech sessions, not original
uninterrupted recordings. Model-pretraining exposure is unknown. “Untouched”
means unused by this experiment's development/evaluation, relative to the
audited evidence registry. Audio and parquet files remain on the8TB disk.

Manifest SHA256:
`2be8fc874313393a7564272bed714e3a3cb5ab50751fe49dfe20280bf094b9b0`.
This holdout stays sealed until the mechanism/evaluation decision is frozen.

## Native model pilot: ten cells complete, failures retained

The v8 runtime is `27804a4f7b0da57d6e431360677ec791161cb60e` and passes330
Linux CPU tests with zero skips. The only runtime-source additions beyond v7
are paid input-operator code/tests; the native and ASR code is unchanged.
The native pilot uses actual fixed-version LangGraph checkpoint/resume,
independent SQLite application state, three model read/write requests and
the real composed kernel. Complete Standard receives the same selection.

The first completed development cells expose two weaknesses: FP16 Qwen2.5-1.5B
generates repeated token0 (`!`) to its budget, while its FP32 path writes
schema-valid but task-incorrect plans. Protected real multi-cycle histories
pass the observed lifecycle checks, but this does not establish correct task
performance or attributable downstream harm. All ten clean smoke cells have
completed. The eight protected cells each complete three real write cycles,
but all task-success counts are zero. The two candidate-only cells each retain
three unfulfilled requests. Numerical/model/implementation causes require
diagnosis before any large native comparison. Both the earlier eight-cell
snapshot and the terminal ten-cell snapshot are retained.

The v8 `actual_gpu_call_count` field counts entries in `actual_calls`, including
zero-GPU structural verification rejections. For the observed Strict fallback
cells, nine entries mean six neural invocations plus three CPU structural
checks. Its `verification_rejections` counter excludes structural rejections.
These accounting limitations are retained in the original records and will
receive an explicit recount/fix; the raw data is not rewritten.

## R7/R8/R9 decision boundary

R7's margin/risk FAST_COMMIT, R8's context views and the current FP32 exact
adapter are distinct contracts. R8 already attempted VACC, Snapshot+Delta,
continuous replay and singleton arbitration; R9 added canonical segmentation
and local repair. No renamed version of these is a new mechanism.

The R9 development quality cohort is50s and its final3 cohort is40 sessions
of30s, whereas original R7 used128 randomized90s sessions. These results
cannot retrospectively close each of the11 R7 anomalies under the same input
and baseline without a case-level mapping. The new audit is resolving those
mappings and the true paid acquisition cost of a trusted context anchor.
R7 historical execution identity remains UNKNOWN where original bindings are
missing. The newly reconstructed128 input waveforms do not repair that fact.

## Evidence and next gates

- `publication_update_v1/`: exact raw archive/index, four recovered episodes,
  native completed-cell snapshot, native asset audit and holdout freeze.
- `source/` plus `SOURCE_v1/v2`, tar and Git bundles: clean frozen analysis
  sources, including failed/earlier revisions and CPU test records.
- `runtime_v8/`: complete v8 source bundle/manifest and CPU evidence; no paid
  operator GPU result is claimed before its own run.
- Goal amendment: the broad waiting-policy expansion is deferred. Complete
  the small repaired strong-baseline check and paid input attribution, then
  decide whether context recovery has real headroom for a formal GPU matrix.

No new context-recovery algorithm, independent-source scheduling win, natural
incident rate, universal quality guarantee or acceptance outcome is established
by this checkpoint. Paper rewriting waits for audited research results.

Dataset sources: [OpenSLR dataset card](https://huggingface.co/datasets/openslr/librispeech_asr)
and its [content-addressed parquet commit](https://huggingface.co/datasets/openslr/librispeech_asr/commit/fed4943ea9bdc207dc01b65e0928dd100e18a2a1).

# Fixed nine-call Whisper bad-data diagnostic

This is an independent small source package, not a modification of the running
RevTrace runtime. Freeze its complete clean Git commit and byte manifest. The
input plan binds the retained development source/worker-record hashes, complete
original jobs, actual conditioning/decoder inputs, model/tokenizer/weight assets,
and expected outputs. Expected outputs are comparison evidence only.

Exactly six formal single-row calls repeat these three old FP32 Authority inputs
twice: authority-6-102 (0.455s word loop), authority-7-120 (2s word loop), and
authority-5-117 (0.3s blank loop). Each uses the same original CPU features and
FP32 GPU features, initial decoder IDs, eager FP32 GPU1, greedy budget256 and
actual EOS/budget terminal. Raw sequences, original-prefix removal, selected Z,
projection, stop, exact-old comparison, timing and GPU1 board energy are saved.

Exactly three further formal calls use the same complete original source audio
with empty history, the same checkpoint, greedy256 and no timestamps. These are
different-segmentation whole-source quality references. They are not same-contract
legal oracles, replacements for failed streaming results, native OpenAI transcribe
fallback reproductions, or online-serving results.

One explicitly separate model warmup uses one second of zero audio, empty history
and a four-token budget. No extra repeats, peers, VAD, deduplication, repetition
stopping, fallback, parameter search, model changes, or holdout consumption.

The original Whisper worker executed variable-prompt rows serially, with neural
batch_rows=1. The diagnostic preserves that tensor layout but omits original peer
scheduling to obey the nine-call bound. It must not claim an original full-lease
replay or compare deployed queue latency. All old outputs and bad results remain.

Before any processor/model load, record experiment ID, full source commit+manifest,
frozen plan/config/environment hashes, model and tokenizer assets, raw result path,
summary and gate paths. All models/data/environments/caches/logs/results stay on
the designated 8TB disk. Require GPU idle before model load, then bind physical
GPU1 through CUDA_VISIBLE_DEVICES=1. Never signal another process.

CPU-only --validate-inputs-only reconstructs three feature/prompt inputs and
loads no neural model or GPU. Original attention-mask bytes were not separately
recorded; the exact same pinned processor reconstructs and newly hashes the mask.
The decoded audio/features and actual first decoder IDs are fully checked.

The execution gate accepts nine completed paid calls with correct input and
terminal accounting, regardless of matching old outputs or whole-source quality.
Those outcomes are scientific evidence, never triggers for hidden extra calls.
A failure preserves STOP and all completed/attempt records with no automatic retry.

Record strict same-input repeat consistency, old-output exactness and three
complete-reference WER results. These decide whether a narrow shared adapter
repair deserves consideration; they never select H3 sources, load or thresholds.

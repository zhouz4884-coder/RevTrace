# Bounded StreamCorrect adaptation

This family evaluates a controlled adaptation of the author's native
Whisper + released Ultravox/LoRA correction recurrence. It does not reproduce
the paper's H20 CER/latency benchmark. No model training or output-based source
selection is permitted.

## Frozen scientific question

Can the independently selected corrected feedback continue unchanged while
complete native ASR work and an actual provisional Consumer retain progress
across a compatible feedback installation? A changed transcript is one reason
for incompatibility. An unchanged transcript is not sufficient: audio buffers,
token groups, context, alignment cursor, language and configuration must agree.

## Author identities and acquisition

- Official publication: https://aclanthology.org/2026.emnlp-industry.142/ .
- Author code: `vu-duy-tung/StreamCorrect` at
  `bbb9f7fde13fabb6c0940f5bae215150d1ea1cb3`.
- Released assets: `playwithmino/StreamCorrect` at
  `16f6fd1e17418f1c4111a18fdd39543813206d96` (public, ungated).
  The author's HF profile links the same GitHub identity. Its
  `StreamCorrect.zip` contains the native `error_corrector_ckpt` LoRA adapter;
  this was found by reading the public ZIP central directory, not by guessing
  a model name. Full compressed archive size 1,042,360,494 bytes; published LFS
  SHA-256 `e15c960dceca7d50d9b47f00f9ad45b3b6aaf4ec36d8146d56fed1415d0f50ee`.
- Adapter size 60,877,264 bytes (56,361,194 compressed). The native adapter config
  identifies `fixie-ai/ultravox-v0_5-llama-3_2-1b`, pinned HF revision
  `b95bec8ab291eeb04b5cd600dd473377f6b79026` (public, ungated).
- Author `large-v2-zh.pt.zip` size 5,728,245,750 bytes, published LFS SHA-256
  `ab30ddd181d1ab323711ea29d991f1d68ab9b6f0e43f5b8612f2dad6a65d07a4`.
- Root README advertises MIT but the pinned root has no LICENSE file; the
  adapter card leaves license unspecified. Research execution and public
  metadata inspection do not establish redistribution rights. Do not put the
  external model weights or copied author source in our GitHub artifact.

The setup script still contains an unresolved `[username]/StreamCorrect`
placeholder. This does not mean the model was unpublished: live public HF
metadata and exact archive inspection found the real release. Remote HF API
connections reset, so local official HTTPS metadata was the successful fallback.

## Bounded execution sequence

1. Finish CPU interface and state reconciliation gates locally. Acquire native
   assets only during an explicitly scheduled idle experiment-disk window.
2. Create an isolated environment on the designated disk; do not modify the
   validated RevTrace environment. Inventory code, weights, tokenizer, library
   versions and clean source commits. Run a source gate before paid calls.
3. Select four complete AISHELL test utterances from distinct speakers by
   metadata only: lexicographically first eligible speaker and utterance with
   8–15 seconds of mono 16kHz audio. Select before ASR or correction inference.
   Retain every selected source even if correction, compatibility or quality
   is poor. No fallback source search based on generated text.
4. Preserve the author's `beam_size=4`, 500ms input cadence, frame threshold 20,
   1s minimum initial audio, 30s audio buffer, greedy corrector `max_new_tokens=8`
   and actual LoRA weights. Use fixed chunk boundaries and no VAD for the
   controlled wrapper; this changes the native front end and must be stated.
5. Two source cohorts, two sessions each. Compare three arms with two fresh
   process repetitions: sequential author recurrence, overlapped conservative
   drop on every trusted installation, and overlapped RevTrace strict state
   compatibility retention with a legal two-lane Consumer. Twelve measured
   cells, fixed balanced randomized order. One common declared warmup per
   process is separate. No physical early exit in this application family.

## What must remain authentic

The actual author's ASR inference and SpeechLM correction function choose the
appended token IDs. No correction output is replaced, forced to a candidate,
normalized for admission, or chosen by reference correctness. The complete
selected ASR feedback, including alignment and context state, is rerun in each
arm. Exact full histories must match; if not, that pairing fails rather than
being repaired by replaying an earlier decision invisibly.

Private work uses the same native ASR candidate computation without the
corrector. It has no authority to change trusted feedback. A complete private
state at the newly installed trusted boundary must equal that trusted state
byte-for-byte before later private steps or visible text can survive. Different
native token grouping, context or cursor denies retention even if decoded text
matches. All caches must be cleaned/reset at the cut as the author does.

Report corrected/unchanged updates and compatible/incompatible boundaries for
all updates, including empty-emission updates. Empty updates carry no positive
audio/text usefulness credit by themselves. The required witness is naturally
observed interleaving with both genuinely changed and unchanged selections. If
the fixed cohort lacks either, report the missing case and stop the application
claim; do not manufacture a matching root or expand by inspecting outputs.

## End-to-end accounting and limits

Original offered audio times, D2/C8 deadlines, all selected input and complete
quality denominators remain unchanged. Record actual Consumer application,
audio/text withdrawal, authoritative selection, model completion and both-GPU
power integrals. Empty early modes cannot earn audio credit. Fixed-model load
cost is recorded separately from post-ready serving, and all arms pay the same
native weights and resource capacity. Baseline sequential may leave the second
GPU idle; both boards remain in the energy boundary.

A trajectory-only or timestamp-replay result must be labeled accordingly and
cannot become an online service performance result. Missing weights or an
unvalidated native state interface ends this bounded adaptation at a documented
integration boundary; it does not trigger new training or replace the core
service evidence.

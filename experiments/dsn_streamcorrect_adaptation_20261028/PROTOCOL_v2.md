# StreamCorrect adaptation, public exact-backbone route

This supersedes only the prior access-precondition status. The initial 401
observations and CPU-v1 artifact remain historical evidence. The source cohort,
native feedback contract and no-training scope are unchanged.

## Exact public ModelScope distribution

The user requested ModelScope. Public `LLM-Research/Llama-3.2-1B-Instruct`
provides the original BF16 weight under `llama3.2`, without requesting a new
account or changing access controls. Its weight is 2,471,645,608 bytes, SHA-256
`1ff795ff6a07e6a68085d206fb84417da2f083f68391c2843cd2b8ac6df8538f`.
Reconstructing the standard 135-byte Git-LFS pointer yields Git blob SHA-1
`5daf23edd80cedb879a4a18e6049a19b2417a3f7`, exactly the pointer blob published
by the canonical Meta Hugging Face repository at
`9213176726f574b556790deb65791e0c5aa438b6`. The ModelScope file revision is
`f8e6bf8fec8194d75228ef38e85fda45c6046fbd`. This establishes an exact expected
original weight identity, rather than matching only a model name. The actual
download must match that SHA-256 before use.

Public source links:

- https://modelscope.cn/models/LLM-Research/Llama-3.2-1B-Instruct
- https://huggingface.co/meta-llama/Llama-3.2-1B-Instruct
- https://huggingface.co/fixie-ai/ultravox-v0_5-llama-3_2-1b
- https://huggingface.co/datasets/playwithmino/StreamCorrect

## Frozen metadata-first inputs

Four complete utterances were selected before any ASR/correction output, by
the first lexicographically eligible source per distinct speaker with an actual
WAV header duration in [8,15] seconds, mono PCM16 at 16kHz:

| Source | Speaker | Full seconds | Cohort |
|---|---|---:|---|
| BAC009S0764W0209 | S0764 | 8.068 | A |
| BAC009S0765W0203 | S0765 | 8.334 | A |
| BAC009S0767W0329 | S0767 | 8.6689375 | B |
| BAC009S0768W0136 | S0768 | 8.1439375 | B |

The full source/asset plan SHA-256 is
`0f87184b55b81cee9ae977d95d596093a148cac0c210df3dfb3ba6e1d08ea704`.
No source is replaced after seeing a correction, compatibility or quality result.

## Compatibility repairs versus controlled adaptation

Two path-resolution repairs retain exact original weights and model functions:
Ultravox's nested `text_model_id` resolves to the byte-matched original local
ModelScope backbone; the author Whisper loader's redundant generic large-v2
download is suppressed while its original Chinese-checkpoint key conversion
and large-v2 alignment-head selection still execute. The author ASR inference
and learned Authority corrector's prompt/generate/selection code are unchanged.

The front end uses fixed 500ms chunks and no VAD, which is a declared controlled
adaptation. Private predicts the actual first beam's continuation, then passes
that prediction through the same native selected-text retokenization, token
append and cache/beam-reset path as Authority. It cannot see future trusted
choices. This prevents spurious representation differences solely from skipping
the native update adapter. It does not force private predictions to match any
learned correction.

The full cut includes native audio buffers, token groupings, context text and
token IDs, alignment cursor, language, initial tokens and decoder identity,
frozen weights/config/source contract, source identity, absolute input frontier
and complete rendered transcript. KV/attention/beam caches must actually be
empty/reset at this native boundary. Telemetry-only first-token clocks and log
counters are excluded because they do not determine candidate/selection state.
Unknown or unequal state denies retention. Final correctness remains the
unchanged actual learned selected-feedback history, not a ground-truth oracle.

## Bounded launch and comparison

Run two prerequisite native joint-service witnesses, one per cohort, retaining
every output and update. These are separate from the performance comparison.
Only if the fixed four sources naturally contain both changed and unchanged
actual learned selections with nonempty continuation content and actual
same-source private work ahead at the trusted installation is the formal
comparison started. Purely empty repetitions remain in the full denominator
but cannot satisfy this positive witness gate. Actual model start/end clocks
distinguish physically running work, completed-but-unconsumed work, and a
merely pending request that has not started. Missing either meaningful case
ends this bounded application claim; it does not authorize selecting new
sources by output or manufacturing matching roots.

The formal comparison has 12 cells: two two-session cohorts × three arms
(`sequential`, conservative `drop`, `joint`) × two fresh-process repetitions,
with a fixed balanced randomized order. Authority executes the same native
ASR+LoRA correction recurrence in every arm. The strong sequential arm uses
two full native ASR+corrector replicas, one per GPU and source; this credits
the published call-level replication alternative instead of leaving a GPU
idle. Overlapped arms use one Authority and one Private on the same two-board
capacity, and share the same
strict legal two-lane Consumer; `drop` loses computation on each trusted
installation, while `joint` keeps only strict complete-state-compatible work.
There is no physical early exit in this application experiment.

The complete actual trusted state history and token/text choices must match
across all six formal cells per cohort, including process repetitions. A
mismatch fails that comparison; it is not hidden by replaying selected outputs.
Record accepted-input and Canonical fsync WALs, actual model calls, actual FIFO
Consumer applications and both-GPU power. All offered frontiers and original
D2/C8 clocks remain in the denominator. Empty initial-buffer updates earn no
processed-audio credit until a real native model evaluation occurs; empty text
earns no provisional audio credit. Ground-truth quality uses every selected
reference with an explicitly stated normalization, and is distinct from exact
trusted-history preservation.

Everything large stays on the 8TB disk. Downloads/decompression/model startup
must not overlap the core timed service cells on the shared machine/disk.

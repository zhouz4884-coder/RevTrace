# R7/R8 provenance and semantic feasibility audit

This is a read-only source/raw audit. It does not reproduce GPU inference,
repair historical provenance, or establish an exact-contract quality failure.
The JSON inventory includes128sessions,all11root records,66R8metric artifacts,
input hashes and bounded remote provenance observations.

## What is actually established

R7's11catastrophic flags independently agree with the recorded per-session WER
under `delta>10pp OR (WER>2*max(canonicalWER,1) AND delta>5pp)`. Roots are
2,8,22,32,41,54,57,78,90,95,122. The128sessions contain1,645unique utterances
without reuse. Each of the11roots combines8–16speakers. Of88internal10s window
boundaries,87 fall inside an utterance according to source sample metadata.
This is neither natural continuous long-form speech nor evidence that each
boundary cuts a word. Acoustic segmentation and speaker switching remain
confounders to distinguish from context removal.

Old R7 uses `ElasticFeedbackController` in
`src/revtrace/feedback_coherence.py`: `_choose_action`417–451 permits FAST_COMMIT
from margin thresholds; `step`466 onward appends candidate tokens to future
feedback. `ElasticFeedbackState`72 has no canonical WAL receipts or certified
FP32 ancestry. `run_r7_whisper_quality.py` emits batched proposed and feedback-off
outputs,while separately executing singleton canonical for comparison.
The default `DistinctPromptWhisper` precision is FP16,96newtokens,10s windows,
bounded previous-text history. Its canonical reference also has126capacity
rebases. These guarantees/costs cannot be relabelled as current exact FP32 DGFT.

## Checkpoint distinction and R8 cost

`run_r8_whisper_views.py` reconstructs `canonical_after` from the already
generated complete reference `canonical_trace`. Snapshot+Delta then reads a
fixed-boundary anchor directly from that array; only delta/capsule GPU calls
are charged in the view's `capsule_seconds`. That anchor is an available
diagnostic reference,not an already certified online EFSC checkpoint generated
for free. A deployment must account for producing and preserving its ancestry.

`install_authoritative_feedback_capsule`283 only projects supplied tokens into
ancestry-free atoms. It does not execute or verify the model. Some callers do
pay a raw-audio singleton call. Other R8 paths explicitly admit independent
batched replay as causally independent,not as bitwise singleton selection:
`run_r8_csdr_quality.py`977–983 says this directly. Selective terminal closure
at1166ff replays only monitor-positive unsafe lineages; unchecked monitor-negative
lineages are not converted into deterministic exactness by their agreement.

R8 has already tried VACC10/20/30,Snapshot+Delta,CSM,yield/minscore/acoustic/
agreement selectors,canonical leases,continuous replay,bounded/empty/full
prompt policies,overlap and same-prompt singleton arbitration. On the11original
roots,VACC10/20/30 leave3/5/7outliers and Snapshot+Delta leaves2. A reference-aware
session-level chooser obtains0,but does not provide an online label. The
`estimated_energy_reduction` combines component time with a different prior
energy result; it is not actual same-run energy. The same-prompt repair on a
later128-session confirmation leaves Tiny1,Base2,Small4 outliers. All negative
files remain in the inventory.

Later R9/R9.E documentation already develops coarse canonical segments and
local singleton repair. Any next mechanism must compare with those actual
implementations and their contract/quality limitations,not repeat the old
R8proposal as if the repository had stopped there.

## Provenance status

Original launcher identifies:

- project:`/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9/projects/revtrace_r7_0849660`
- env:`.../envs/streamtxn-cu128/bin/python`
- manifest:`.../datasets/revtrace/librispeech/whisper-w-quality.json`
- quality:`.../results/revtrace/r7_efsc/whisper_base_quality/paired-128.json`
- log:`.../logs/revtrace/r7_efsc/whisper_base_quality/paired-128.log`

The remote manifest currently byte-matches the archive copy:
`e500c0bb5200fb48d521869907826b71192220179a4055570748d0033c4a1cde`.
Current remote R7/R8 runners and feedback_coherence also byte-match archive.
The current project CODE_COMMIT reads2112157301fc36ab6d9b2e70e918a9f42dd52b2c,
but original paired128JSON andlog have no execution commit/environment binding;
project SOURCE_MANIFEST.json andENVIRONMENT.json are absent. Current markers
cannot retrospectively establish the executed historical version. That identity
remains UNKNOWN; a new faithful reproduction needs its own complete freeze.

## Relation to the current exact path

Current LP1 `whisper_kernel_worker.py` loads FP32Authority independently,
consumes each contiguous interval and accumulated history through actual
`get_prompt_ids`,records actual decoder input consumption,and sends results
through trusted render/kernel/WAL. It has no margin-based FAST_COMMIT or EFSC
safe-reset path. Therefore the old R7 failure is not presently demonstrated as
a failure of this exact path. Native prompt realization/truncation still needs
explicit observation; full stored history does not prove every token is consumed.

If a valid exact Canonical checkpoint exists,its P/Z/text and identity already
survive in WAL. Ordinary recovery is replay and trusted re-render,not new GPU
reconstruction. If only the old FAST_COMMIT history exists,constructing the
last correct checkpoint may require executing each unchecked transition in
order from the last actual authority. CPU reinterpretation of oldZ cannot do
that. At terminal the full unchecked suffix must close; its cost may approach
the full Canonical baseline. Empty-context capsules instead define another
conditioning contract and cannot guarantee the original transcript's quality.

## Bounded next gate

1. Faithfully replay the archived11failure contexts under a newly frozen legacy
   contract,with clear/range20/30/same-prompt singleton/full Canonical controls.
   Treat this as historical reproduction,not current exact-serving failure.
2. Separately run current exact semantics on matched audio/intervals and retain
   actual Parent/P/decoder IDs. Locate a reachable need for restoration before
   implementing another context-recovery policy. Distinguish complete content
   generation from correct provenance throughout.
3. For a real reachable gap,charge generation of every missing certified
   checkpoint transition. Only a bounded measured improvement beyond these
   strong controls justifies a new mechanism.
4. If exact authority already supplies the needed history or reconstruction
   costs approximately full Canonical,use NO-GO for this new recovery novelty
   route. Preserve R7/R8 as adaptation/quality boundaries; they do not retract
   C1/C2/C3 and do not prove a new independent contribution.
5. Independent confirmation should use source-/chapter-consistent sequential
   speech or long-form audio and a newly frozen manifest. The old randomized
   multi-speaker90s pool has already been used extensively for diagnosis.

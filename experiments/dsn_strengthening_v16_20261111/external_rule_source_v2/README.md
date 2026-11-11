# External LA2 read-policy experiment v2

Authored source and 28 controls; no tests or raw replay were performed before
freezing. CPU/model imports must never overlap a timed GPU campaign. Root must
allocate a new idle receipt for this specific experiment.

Experiment ID: REVTRACE-V16-EXTERNAL-LA2-SHADOW-20261111-V2.
Full fixed scope: the previously recorded PILOT24; no new speaker selection,
model inference, training, neural source edit or reference generation.

The actual task already uses PaddedAlignAttWhisper inside original C/U. We add
a read policy above those actual delivered candidates. LA2 is a primary-source
decision-rule adapter, not replacement LA-ASR, whole WhisperStreaming, a new
GPU/system run, a matched alternative computation schedule, or a closed-loop
causal speedup. Canonical-only and 0.5-second fixed lag are generic controls.

The Chinese Unicode code-point adaptation and conservative existing-whole-view
mapping are intentional. Unmapped prefix characters retain content metrics,
never fractional audio credit. No word timestamps are invented. Changes to an
already confirmed prefix stall extension; actual canonical conflict or complete
state support refutation resets it. The author system's timestamp alignment,
prompts and trimming are not imitated.

Ordinary update unit: first nonempty actual Consumer view whose real audio
frontier exceeds the previous maximum and whose audio was actually accepted.
Repeated views, ASR/full-C at the same frontier, canonical handover and delayed
older views cannot create another agreement sample. A jump in F supplies one
available hypothesis, not a fabricated hypothesis for every skipped chunk.

Terminal release occurs on actual final C/U delivery, never by guessing EOS
output or counting the same final input again. Canonical support and exact full
feedback-state equality precede prefix mapping. An actual support refutation
cancels pending delayed views even if their text has not changed.

All four rules receive the exact same completed candidate schedule per cell.
No observer sends original Consumer ACK, modifies visible_job_ids, pins nodes,
changes GC or touches Owner/worker commands. A live replacement would affect
ACK/GC and future computation, so this offline tradeoff cannot certify that
different deployed schedule or its resources/SLO. Actual original G is carried
unchanged into every observer; only offline V changes. Metric files explicitly
name offline_shadow_D/credit. First-cover, not sustained coverage, is used in
the original D/C endpoint; later refutations are separate counts/text edits.

Raw dependencies reuse the previously frozen OPV1 all24 input set (522 entries,
OP config SHA 420dd86121c1487dbc6a3ac3b26398f411b4d96d6cdb14e0aa00685cc24f19d5).
Formal preparation rehashes every input and verifies complete NN/driver/auditor
sources. It rechecks facts, strict full references and actual Consumer source
bindings using the frozen original parsers and OPV1 registry.

CPU procedure, only after coordinated GPU-idle authorization:

1. Import the complete own source bundle into the legacy repository under its
   distinct refs/revtrace/execution ref; preserve legacy HEAD/dirty files.
2. Run root no-argument preflight for CURRENT=de0936; run explicit own-source
   preflight using the new full execution commit and complete source manifest.
3. Stage complete source/bundle/manifest onto designated8TB. Use the same pinned
   no-neural environment with PYTHONDONTWRITEBYTECODE=1 and CUDA_VISIBLE_DEVICES=''.
4. prepare_idle.py records actual Python/platform/numpy, config, root-specific
   idle receipt, unchanged original input hashes and new exact raw output paths.
5. make_prelaunch.py binds actual config/environment/source receipts. A root
   explicit --run-record gate can additionally verify its mandatory run fields.
6. run_shadow.py first runs all28 controls (including AST-extracted original
   author HypothesisBuffer/finish, not a model), then all24 fixed cell replays.
   Any failed control prevents raw replay. Preserve gate/failure and partials;
   do not edit frozen source/config or relabel a repaired version.
7. Recheck complete source/input/default CURRENT receipts, worker/CUDA idle,
   archive only bounded source/bundle/metrics and publish all nulls. Raw inputs
   stay on the 8TB disk. No positivity/Ready-hit threshold is a validity gate.

Expected raw output:
/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9/results/revtrace/dsn_strengthening_v16_20261111/EXTERNAL_LA2_SHADOW_V2

Every cell has four rows/frontier files, one LA2 prefix/decision file, raw and
whitespace-stripped edit/exposure summaries under both frozen alignments. Full
cell-rule and within-schedule contrast tables retain all24. No window is treated
as an independent speaker. Final text equality and actual-SUP credit identity
are required controls, never inferred from character count alone.

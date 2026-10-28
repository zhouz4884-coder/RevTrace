# REVTRACE-FREEZE-BOUNDARY-20261027 — development protocol

This is the execution index for the complete user goal in
`C:/Users/LENOVO/.codex/attachments/0be9347d-16dd-4405-9059-688c391d7d74/goal-objective.md`.
All seven workpackages remain in scope. This protocol is not a claim of completion.

## Identity and scope

Archive baseline: `84c41fca5b2576d121e67b9273b2b72ea2b53b7c`.
Actual LP1 source baseline: `7c176556592c2a4fad436056b8b96be52cac9ea4`.
New branch: `codex/freeze-boundary-20261027` in `.execution/lp1_runtime`.
Each executable revision must receive its own commit, complete source manifest,
frozen configuration, environment, result location and post-run gate. Existing
source bundles/raw and negative results remain immutable.

## Mechanism under test

Filter eligible Private dispatches after the effective `_ready` gate and before
`_make_job` freezes the parent, prompt and audio identity. A wait is one-shot per
session/frontier and has a fixed expiration. It never changes a dispatched job.
When released, run the original eligibility gate again and construct a new job
from actual state. Other eligible sessions can use an available worker.

All six policies share the same state-safe runtime, Row-complete transport,
worker lease lifecycle, trusted Render, input/canonical WAL, actual Consumer,
original display 2 s / commit 8 s clocks and all offered/accepted denominators:
immediate; fixed bounded wait; ordinary pending-Authority ETA wait; lead/inflight
backpressure; simple recent-gain adaptive wait; state-aware wait. Standard receives
the same candidate policy. Tuning budget and permissible observations must be
frozen before the development matrix; validation sources are selected only after
checking every historical manifest and before model inference.

The controller may observe canonical/private lineage, pending Authority identity
and live execution phase, elapsed time, completed historical service costs, queue
state and original deadline. Future output, future finish time, source identity
and fault labels are prohibited features. Prediction only controls dispatch time.

Main comparison uses the complete common Row-complete backend, including physical
multirow batches. LP1 prefix continuation remains batch1-only; a batch1 orthogonal
check must supply it to every comparison arm. It cannot be enabled by deleting
the physical batch-size assertion.

## Causal diagnosis and metrics

Keep the full eligible opportunity denominator and separate historical ex-post
windows from deployable predictions. Match actual input and full batch layout
for paid operator controls; if an old parent is no longer legal, do not dispatch
it as service. Report input changes, skipped-but-canonically-covered work, batch
membership/padding and queue effects separately without adding overlapping costs.

Primary records include all-offered dual-deadline Audio Goodput; actual Consumer
Display/Commit P50/P95/P99; run-level dual P99 success; GPU0/GPU1 physical paid
leases and energy; WER/CER; rollbacks; missing/rejected/unfinished obligations.
Run-level repeats are not independent source tasks. Diagnose failures before
bounded repair and rerun. A case confined to the old single-source batch16 cap
cannot be promoted to general algorithm success.

## Recovery, native application and proof workpackages

Recovery compares original duplicate and reused processor paths under identical
fault, cold/warm conditions and original episode clocks. Preserve asset/parser/
processor identities, trusted rerender, owner/epoch, all digests and input debt.
Measure import/asset/processor/WAL/render/Consumer/worker phases and three distinct
outcomes: old certified fact visible, first new certified fact, and debt drained.
Existing early-worker overlap is a baseline, not a new contribution.

Reuse the native CPU gate ZIP. New neural evidence must use pinned LangGraph
checkpoint/resume and a separate persistent application store, two structurally
different task families and at least two real model read/write cycles, including
state written back after a subsequent request. Retain base-model task failures.
The independent checker recomputes from actual input, WAL and consumer receipts;
missing evidence is UNKNOWN. It cannot call the tested admit()/step() as its proof.

Use TLA+/TLC first; specify conditional parameterized properties before TLAPS.
Distinguish safety, selection completeness, liveness and timed service. Each
counterexample must name necessary observations, actual witness and checked scope.

## Delivery and stop discipline

Deliver code/config/environment identities, raw/hash index, runnable analyses,
failed versions, independent review, all seven evidence tables in the user goal,
and a revised contribution matrix. Check DSP, Heartbeat Thinking, AOSpec,
adaptive waiting and speculative backpressure against primary literature.
Paper claims change only after implemented work and real validation. No automatic
submission. A performance NO-GO does not terminate recovery/native/formal work.

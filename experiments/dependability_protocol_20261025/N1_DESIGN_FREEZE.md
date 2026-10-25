# N1: Late completed Proposal, frozen intervention design

This is a fault/ordering experiment, not natural prevalence or a faster CES.
Baseline: public Row SDK measured commit 2bc71af5457de5d065ff9e771d2fad428c5c6ed9,
129 original byte-verified files. The current changes mechanically separate
per-result acceptance from physical lease handling and add a diagnostic broker.

## Intervention and legal controls

Use real Qwen3-ASR-1.7B on two RTX3090s: FP16 proposal GPU0, FP32 authority GPU1,
fine=2 s, rho=3, full utterances, batch=4, durable group-ready WAL, trusted render.
No model token, prompt, audio, stop, budget, generation time or output is edited.
The broker starts **after** actual executor poll / batch completion, stores
immutable serialized complete results, and frees the drained physical lease.
Per-session logical busy remains until owner delivery. Already issued GPU work
is neither cancelled nor treated as free. Hold wall time remains in latency,
energy and complete run denominators.

Two fixed windows per session, chosen before new GPU execution:

* Covered: proposal window1 (2 s), authority window3 (6 s).
* Ahead: proposal window7 (14 s), authority window6 (12 s).

Both results must actually complete. Proposal-first delivers P then A; authority-
first delivers A, waits for actual durable installation, then delivers P. The
two orders share a capture phase but fresh-process model outputs are not assumed
identical: actual frozen jobs, processed inputs, full Z/P/text/stop are compared.
Only matched targets support fixed-content ordering attribution. Nonmatches
remain reported, not discarded from coverage or performance denominators.
No-order controls measure the non-intervened instrumented runtime, not an
unmeasured historical binary. A 45 s broker timeout is a retained failed run.

## Methods and Consumer distinction

1. Full coordination (lazy receive/reconcile + D1 + exact private chain).
2. Single-guard ablation: omit only owner receive freshness; all other code,
   pending job immutability, reconciliation, WAL and Consumer checks retained.
   This is a controlled legacy-path adaptation, not the entire original binary.
3. Full Standard Safe Async: conventional independent policy adapter, sharing
   executor, render, WAL and complete Consumer semantics. It may match or win.

For all three, run both existing snapshot and two_lane Consumers. `snapshot`
retains epoch/version/covered-target checks but lacks the exact-root chain
condition; it is not labelled a full safe Consumer. `two_lane` is the full
Consumer. Do not weaken either implementation or create a strawman latest-wins.
Old birth Parent alone is not illegal: a complete exact-compatible chain may
remain provisional after a canonical update.

## Audio and bounded matrix

Use the first four metadata-ordered sessions of the previously frozen PhaseD
manifest, SHA256 ad6a8b714d87fdae9d09249f4915e27c59131aca5600629d334d16476d026a9f:
3729-6852-0003, 4970-29095-0021, 1995-1836-0010, 4077-13751-0021.
All have >14 s actual audio; no clipping/concatenation or outcome-based selection.
These are reused diagnostic sources, not independent held-out population data.

Pilot: full/two_lane, authority-first, covered and ahead (2 fresh runs).
Formal: 3 methods x 2 Consumers x 2 windows x 2 orders x 2 repeats =48;
plus 3 methods x 2 Consumers x no-order x 1 repeat=6. Total54 formal.
Seed20261025, same input audio and fresh process. Pilot is not pooled as repeats.
Stop on infrastructure / binding / input failure; preserve raw failures. Do not
silently retry or automatically add sources to obtain a mismatch. If all ahead
chains happen compatible, that is an explicit coverage limitation, not failure
of the correctness property or license to corrupt generated content.

## Estimands / independent checks

Report captured/delivered payload identities, covered/gen-stale publications,
exact-chain incompatible publications, actual Consumer applications, certified
and visible frontiers, text/churn, first legal display times, raw-vs-legal SLO
credit, full denominators, WER/CER, GPU lease/energy, IPC/render/WAL/Consumer cost.
Raw publication is not actual visible harm; Consumer successful rejection is a
positive control. Canonical history and final WER are separately checked.
No claim of Canonical contamination from a Proposal-only delivery experiment.
No unconditional liveness or production incidence inference.

CPU gate: full focused protocol regression and new post-compute ordering tests.
GPU audit gate: immutable source/config/audio identities, real input capture,
timestamps, legal Authority renderer/WAL, complete cases, owned-worker exit,
actual Consumer records, independently reconstructed exact-chain eligibility.

# Phase R7 closure: EFSC performance passes, Whisper quality tail remains open

## Frozen decision

`QWEN_R7_PASS__WHISPER_PERFORMANCE_PASS_QUALITY_TAIL_FAIL__FROZEN_EFSC_STOP`

No further threshold sweep or EFSC risk epoch is authorized.  The frozen
controller has already established its systems value.  The remaining Whisper
failure is outside its action space: EFSC can withhold unsafe text authority,
but it cannot reconstruct useful context after that context has been removed.

This is not a paper-wide NO-GO.  It is a stop decision for **frozen EFSC as the
complete Whisper solution**.

## What passed

### Qwen R7.Q0

The same controller, with the architecture-specific joint text/audio rebase
adapter, passed on both Qwen3-ASR sizes.

| Model | Live events | Formal repeats | Median wall | Median P99 | Median events/s | Energy |
|---|---:|---:|---:|---:|---:|---:|
| Qwen3-ASR-0.6B | 10,080 | 5 | 7.169 s | 0.748 s | 33.475 | 2.073 J/audio-s |
| Qwen3-ASR-1.7B | 10,080 | 5 | 7.916 s | 0.864 s | 30.318 | 3.056 J/audio-s |

Both models had zero observed semantic/acoustic rebase violations.  Relative
to the previously frozen deployed RevTrace medians, R7 adds approximately
1.73x and 1.89x wall-clock/goodput speedup and lowers P99 by 51.5% and 48.4%,
respectively.  These are live-model serving results, not a simulator claim.

The initial text-only Qwen reset was invalid: it cleared text while retaining
cumulative audio, causing old audio to be transcribed again from an empty
prefix.  The repair was a joint text/acoustic rebase.  This was a state-adapter
code defect, not evidence against the controller.

### Whisper R7.3 serving performance

The production-unit c16 experiment used one authority-free GPU and a paired
FP16 singleton canonical baseline per seed.  A 0.5 s release coalescing window
was applied symmetrically to all baselines after the first workload exposed
release fragmentation spanning 0.181--0.438 s; this is a workload-protocol
repair, not an EFSC threshold sweep.

| Cell | Repeats | Median wall/GPU speedup | Max display P99 | Max state P99 | Min energy reduction | Occupancy | Violations |
|---|---:|---:|---:|---:|---:|---:|---:|
| W1 | 5 | 4.060x | 1.294 s | 1.293 s | 72.86% | 1.0 | 0 |
| W2 | 5 | 4.196x | 1.303 s | 1.303 s | 72.35% | 1.0 | 0 |

Thus EFSC solves the previously observed authority-queue and batch-fragmentation
problem.  Performance, latency, energy, occupancy, authority, and semantic
preflight gates all pass.

## What failed

### Whisper R7.5 strict quality tail

The disjoint quality set contains 128 sessions, 1,645 unique utterances, no
utterance reuse, and 10,000 paired bootstrap replicates.

| System | Mean WER | Delta vs canonical | Catastrophic session outliers |
|---|---:|---:|---:|
| FP16 singleton canonical | 32.329 | 0.000 pp | 0 |
| Frozen EFSC | 30.859 | -1.469 pp | 11 |
| Feedback off | 28.789 | -3.539 pp | 13 |
| Longer-context view | 27.719 | -4.609 pp | 6 |
| Reference-aware two-view oracle | 29.940 | -2.388 pp | 5 |

The aggregate result is favorable: the pooled bootstrap 95% upper bound is
0.109 percentage points and both split mean gates pass.  Repetition-loop rate,
semantic violations, and utterance reuse are zero; maximum state age and debt
are both three, and reset-recovery P95 is one window.  Nevertheless, the
pre-registered zero-catastrophic-tail condition fails with 11 sessions.

This failure must not be hidden behind the improved mean WER.

## Root-cause separation

### 1. Code and logging

The quality tracer initially recorded `prepare_action` from the last session in
a batch.  The controller decisions, prompts, hypotheses, WER, and serving
metrics were unaffected.  The tracer now stores per-session preparation data
in `preparation_debug`.  The causal cutset reconstructs the prompt from the
controller and validates prompt length, so it does not depend on the stale
debug field in the first traced artifact.

### 2. Same-input numerical divergence

A causal four-way cutset was run on 33 failure-associated c16 workloads (528
events): singleton encoder/singleton decoder (SE_SD), batched encoder/batched
decoder (BE_BD), batched encoder/singleton decoder (BE_SD), and singleton
encoder/batched decoder (SE_BD).

| Path | Projection mismatches vs SE_SD | Exact rate | Runtime | Fraction of SE_SD cost |
|---|---:|---:|---:|---:|
| SE_SD | 0 | 100.000% | 94.849 s | 100.00% |
| BE_BD | 5 | 99.053% | 22.934 s | 24.18% |
| BE_SD | 9 | 98.295% | 94.345 s | 99.47% |
| SE_BD | 5 | 99.053% | 22.720 s | 23.95% |

The batched path reproduced all selected workloads.  However, none of the five
same-input numerical mismatches occurred in the catastrophic sessions.  The
only low-cost cutset (`SE_BD`) leaves all five mismatches; `BE_SD` costs almost
the full canonical path and is worse.  Therefore a projection cutset cannot
repair the observed quality tail.

### 3. Mechanism limit

The catastrophic traces contain 10-second speech windows that emit only one to
ten tokens and terminate early after EFSC has reduced or emptied prompt
context.  Some candidates have high margin (for example 1.2578), and many
outputs match the feedback-off path.  This is neither state-lineage corruption
nor a batch/singleton arithmetic flip.  It is **context starvation caused by
safe authority erasure**.

The reference-aware two-view oracle is decisive: even an oracle choosing
between the frozen EFSC and empty-context view leaves five catastrophic
sessions.  A longer context reduces the count to six but also does not close
the gate.  Consequently, threshold tuning, entropy features, or another choice
among the existing views cannot produce the required zero-tail result.

## Why further EFSC testing stops

R7.4 (large sentinel risk audit), R7.6 (baseline matrix), and further threshold
sweeps are stopped by protocol after R7.5.  They would measure the frozen
mechanism more precisely without adding the missing information needed to
recover speech context.  The prepared scripts remain available, but no result
from an unexecuted script is promoted as evidence.

Naive cascading speculation is also not the next repair.  Existing depth-one
prefetch ablations recorded 22 prefetches, 19 reuses, three discards, and three
state/output violations.  Any later speculation must use exact version fencing
and a certified parent chain; the old prefetch mechanism is not admissible.

## Proposed next mechanism: authoritative safe reanchoring

The next method must add a context-recovery operation rather than retune EFSC.
The recommended design is a **Verified Context Capsule / Acoustic Reanchor**:

1. Keep EFSC's display/state separation and bounded authority lattice.
2. On HOLD/RESET, retain no unverified generated-text authority.
3. Reconstruct a compact context capsule from exogenous audio or a previously
   certified checkpoint, not from the rejected hypothesis.
4. Bind the capsule to the audio frontier and revision version; overlap and
   deduplication must be deterministic.
5. Allow the capsule to restore continuity without granting broad historical
   text write authority.
6. Keep refresh off the common critical path; if asynchronous work crosses a
   revision boundary, use MVCC parent/version validation and discard stale
   descendants.

The new death gate should require all of:

- zero state-lineage violations;
- zero catastrophic quality outliers on the frozen 128-session set and a new
  held-out set;
- pooled and split WER gates retained;
- at least 2.5x wall-clock speedup;
- display/state P99 at most 1.9 s;
- at least 40% energy reduction.

If authoritative reanchoring cannot satisfy these joint gates, Whisper remains
an honest cross-architecture mechanism/generalization boundary while Qwen
continues to carry the paper's performance headline.

## Auditable artifacts

- `results/r7_efsc/qwen_q0_joint_10k/`
- `results/r7_efsc/qwen_q0_formal/`
- `results/r7_efsc/whisper_base_preflight/`
- `results/r7_efsc/whisper_base_quality/paired-128.json`
- `results/r7_efsc/whisper_base_quality/paired-128-traced.json`
- `results/r7_efsc/whisper_base_quality/two-view-oracle.json`
- `results/r7_efsc/whisper_base_cutset/quality-roots.json`

## Core code

- `src/revtrace/feedback.py`: architecture-independent EFSC state machine.
- `src/revtrace/qwen_feedback.py`: Qwen joint text/acoustic rebase adapter.
- `src/revtrace/whisper_feedback.py`: Whisper bounded-text projection adapter.
- `scripts/remote/run_r7_qwen_live.py`: live Qwen semantic/performance runner.
- `scripts/remote/run_r7_whisper_workload.py`: Whisper serving workload runner.
- `scripts/remote/run_r7_whisper_quality.py`: paired quality and per-window trace runner.
- `scripts/remote/run_r7_whisper_cutset.py`: four-way causal encoder/decoder cutset.
- `scripts/analyze_r7_quality_lattice_oracle.py`: two-view mechanism upper bound.

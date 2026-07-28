# RevTrace Phase 4 adaptation and generality report

Decision: **PHASE4_TASKS_COMPLETE_WITH_BOUNDED_NEGATIVE_GATES**

## Scope

Phase 4 tests four claims left open by Phase 3: whether a risk-window
controller can contract and re-expand without hand-written thresholds; whether
previous-text feedback causally propagates legal execution-shape flips in a
second model family; whether idle audits can be made live without harming the
serving tail; and whether diversity-aware search can expand the population of
distinct consequential state pairs.

## Phase 4A — certified risk-window replay

The split-sample controller invalidates evidence on every contract switch,
sets the fast-path window to zero, learns a margin boundary only from the
calibration prefix, and uses the held-out suffix only to accept or reject that
boundary.  It selected `0.0625` for the initial c16 epoch, `0.109375` for the
c64 drift epoch, and `0.0625` after returning to c16.  Every held-out admitted
audit was correct and each upper risk bound remained below 0.5%.

This establishes controller semantics and fail-closed recovery.  It is not a
live c16-to-c64 serving run.  The reported c16 GPU-normalized values are
projections from matching frozen deployments; no c64 performance number is
invented.

## Phase 4B — Whisper feedback intervention

The expanded gate evaluated two real Whisper checkpoints.  It found
**21** distinct legal singleton-versus-batch pairs;
**8** propagated under previous-text
feedback, whereas **0** propagated
when the same model and future audio were replayed without that feedback edge.
The causal gate decision is **PHASE4B_FEEDBACK_CAUSAL_GATE_PASS**.

The study observed **0** preregistered
application-level catastrophe events.  Therefore the stronger hallucination
loop prevention claim is
**not eligible**.
No example is promoted into a rate claim without the five-event gate.

## Phase 4C — SlackGuard physical gate

The full-request audit quantum measured 309.9 ms, while a 2% P99 perturbation
budget permits 27.5 ms.  The quantum is therefore
**11.27x** too large.
CUDA stream priority cannot preempt a running kernel, so running the proposed
live experiment would not test the intended cancellable mechanism.  The
full-request implementation is frozen as a NO-GO.  A legal repair requires
token-, block-, or encoder/decoder-checkpoint quanta below the measured budget.

## Phase 4D — diversity-aware active mining

| Model | Screened | Probed | Distinct pairs | Pairs / 1000 rows | Yield gain | New vs Phase 3 | 50-pair gate |
|---|---:|---:|---:|---:|---:|---:|---:|
| Qwen3-ASR-0.6B | 500 | 500 | 8 | 1.000 | 2.78x | 7 | NOT MET |
| Qwen3-ASR-1.7B | 500 | 500 | 5 | 0.625 | 2.54x | 4 | NOT MET |

The final run screens 500 independent LibriSpeech candidates per model and
gives each candidate at most one replicated execution-shape probe.  It uses no
logit or token noise.  The result is **PHASE4D_ACTIVE_MINING_BUDGET_COMPLETE_TARGET_NOT_MET**.  Persistent
Contamination Mass and TailRAF are reported only for the observed targeted
pairs; neither the search yield nor the stress trajectory estimates production
prevalence.

## Interpretation

Phase 4 strengthens the causal and measurement story but does not rewrite a
failed gate as success.  The paper-facing system performance remains the real
two-GPU RevTrace deployment from Phases 1–3.  Phase 4 adds an automatic
risk-window abstraction and a cross-family feedback intervention, while
retaining two bounded negatives: full-request SlackGuard lacks a physically
cancellable quantum, and active mining may fail the 50-pair population gate.

All zero-violation observations remain empirical.  RevTrace does not claim
bitwise deterministic floating-point execution.

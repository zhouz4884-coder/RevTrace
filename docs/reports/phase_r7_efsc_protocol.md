# R7 protocol: Elastic Feedback-State Coherence

## Decision before execution

R7 does **not** assume that a Whisper result transfers to Qwen.  It uses one
architecture-independent controller and two explicit projection adapters:

- Qwen receives the exact token projection produced by the official rollback
  and tokenizer path, then replaces the next rollback-prefix state. Its
  effective feedback state also includes the cumulative-audio replay
  frontier: whenever a result is denied text authority, the frontier advances
  with it so denied audio is not retranscribed from an empty/stale text prefix.
- Whisper appends the authorized segment token IDs to its bounded
  previous-text history.

Only the adapter and calibrated margins may differ.  A model-specific branch
in the action controller is a protocol failure.  The Qwen applicability gate
`R7.Q0` must pass before the expensive Whisper performance preflight begins.

## Problem isolated by P0-P3

The frozen negative result is not a failure of feedback-state control.  It is a
failure of synchronous singleton authority as the Whisper production policy:
canonical work creates state dependencies, an authority queue, batch
fragmentation, and long-tail state-entry stalls.  Margin refinements did not
remove every repeat-stable state error.

R7 changes the action space.  A risky output may be displayed without gaining
future feedback authority.  Recovery is performed by moving downward in a
feedback-state lattice, not by placing singleton work on the critical path.

## Shared state model

Let `D_t` be the displayed hypothesis, `H_t` the textual feedback state used by
the next revision, and `A(H_t)` the revisions that can causally influence that
state.  EFSC permits `H_{t+1}` to contain only an authorized subset of displayed
history.

The controller owns four actions:

| Action | Display | Next feedback state | Critical-path canonical work |
|---|---|---|---:|
| FAST_COMMIT | candidate | architecture projection of candidate | no |
| PROVISIONAL_HOLD | candidate | unchanged | no |
| DECAY_SUFFIX | unchanged/candidate | suffix of already authorized state | no |
| SAFE_RESET | unchanged/candidate | empty | no |

For every action except FAST_COMMIT,

`A(H_{t+1}) subseteq A(H_t)`.

Token decay is not a causal reset: a retained token can still depend on an old
prompt that generated it.  The hard influence bound is therefore enforced by
periodic SAFE_RESET.  If the maximum influence horizon is `H`, no admitted
ancestor may remain in feedback state for more than `H` later revisions.

The Qwen adapter therefore performs a joint text/acoustic rebase. This is not
a model-specific controller branch: HOLD/DECAY/RESET remain the shared action,
while the adapter retires every architecture-specific replay component that
would otherwise regenerate denied state. A text-only reset is invalid for
Qwen because its next request still contains the accumulated waveform.

## Debt and hysteresis

The frozen controller has three modes:

`COHERENT -> QUARANTINE -> REANCHOR -> COHERENT`.

- COHERENT admits a candidate only when the enter-margin contract passes and
  debt, age, and prompt-load bounds remain valid.
- QUARANTINE displays candidates but withholds feedback authority.  It exits
  only after a minimum hold and a consecutive safe streak at a stricter exit
  margin.
- REANCHOR follows DECAY or RESET.  A new safe observation is required before
  state writes resume.

Feedback debt counts consecutive fast state entries since the last hard reset.
The first frozen contract uses `K_min=1`, `N_safe=2`, `H_max=3`, and `D_max=3`.
Thresholds are not hand-coded paper constants: each model derives them from a
calibration epoch, may adapt once, then freezes before formal auditing.

## Epoch-fenced evidence

Two background evidence channels are deliberately separated:

1. A pre-outcome random sentinel audit samples FAST_COMMIT candidates and
   certifies only the current frozen epoch.  Its result never mutates service.
2. A triggered diagnostic probe inspects HOLD/DECAY/RESET events.  Because it
   is selected by the policy, it cannot certify the current epoch; it may only
   design the next epoch.

The certification GPU cost is reported independently from one-GPU steady-state
serving and from low-frequency renewal canaries.

## Cross-architecture gate

The R7.Q0 gate prevents a Whisper-only success from becoming a cross-family
claim.  For both Qwen3-ASR scales it requires held-out state-entry replay,
coverage of known numerical roots, actual execution of FAST_COMMIT/HOLD/RESET,
zero provisional-ancestor and stale-version violations, the same bounded
ancestry horizon, and five-seed c16 serving non-regression.  If it fails, EFSC
may still be reported as a Whisper-specific mechanism but **not** as the shared
RevTrace solution.

## Whisper gates

The base.en c16 W1/W2 preflight compares canonical, unprotected, prior verify,
holdback-only, EFSC, and feedback-off.  The preflight stops unless median wall
speedup is at least 2.5x, display and committed-state P99 are at most 1.9 s,
energy reduction is at least 35%, occupancy is at least 90%, and critical-path
canonical work is zero.

For the declared Poisson start process (20 ms mean inter-arrival), every
batched baseline uses the same bounded 0.5-second admission coalescing window.
The wait ends as soon as all c16 sessions are released.  This bound is derived
before the repaired run from the frozen five-seed release span (0.181--0.438 s)
and the 1.9-second SLO; the excluded zero-wait run is retained as scheduler
fragmentation evidence rather than silently overwritten.

The formal risk epoch then requires at least 60,000 eligible entries and 1,200
pre-outcome random audits with a time-uniform 95% upper risk bound at most 0.5%.
Quality uses 128 disjoint 90-second sessions and freezes mean WER delta at most
1 pp, bootstrap upper delta at most 2 pp, no catastrophic outlier, and no worse
repetition-loop rate than canonical.  A hallucination-suppression claim is made
only if the data show a significant improvement.

Small.en runs only after base.en passes.  It reuses the exact controller and
actions; only its calibrated thresholds may differ.

## X0 measured headroom

The frozen paired c8/180-second P1 attribution establishes a real, but scoped,
performance opportunity.  Removing all online authority yields 2.722x wall
speedup and 62.56% energy reduction; feedback-off reaches 3.583x and 70.30%.
Relative to the unprotected path, risk-only authority adds 3.837 s,
checkpoint-only authority adds 2.520 s, and their full combination adds
6.581 s of wall time.  A 2.5x design has 0.866 s of incremental budget above
the measured unprotected path, whereas a 2.7x design has only 0.080 s.

This is `PASS_X0_HEADROOM_FOR_2_5X`, not an EFSC serving result and not evidence
that c16/90-second R7 will pass.  The bound and source hashes are recorded in
`results/r7_efsc/authority_lower_bound.json`.

## Fallback and stop rule

If EFSC fails the quality contract, no new cooldown heuristic is allowed.  The
only remaining mechanism is a projection replay cutset.  It proceeds only if
all known roots have zero projection mismatch, each scale has at least 10,000
held-out events, and replay costs at most 25% of full canonical execution.

The machine-readable source of truth is
`configs/revtrace_r7_efsc_gate.json`.

# Bounded post-serving labels and future controls — frozen before outcome audit

This closes the existing P3 correctness/propagation requirement. It is not a
new selector, new serving method, new performance run, or independent topic.
Do not run until the existing 72-cell controller terminates successfully and
both GPUs are free. No diagnostics are inserted into the timed formal cells.

## Deterministic selection without outcome filtering

1. Use repeat r0, both frozen loads and both clean/F2 traffic arms, for Score
   and Strict. For each of the sixteen sources, take its first actual Authority
   job with chunk_id>=2 and end_window>=5. This selects 128 target source rows
   if all opportunities exist; report missing opportunities explicitly.
2. Also take every actual Unprotected-F2 Authority target whose candidate origin
   was the one injected Proposer job, for r0 and both loads: up to32 source rows.
   Retain issued-but-not-selected, ineffective and missing opportunities. Do not
   replace them with cases chosen by margin, output difference or recognition.
3. Replay each selected target with its entire original physical peer batch.
   Do not reconstruct a singleton and call it the same GPU reference. Share an
   oracle only for an identical complete ordered target/candidate operator;
   hashes exclude purely observational job IDs and clocks, not input/state.

## Generated reference and complete checks

Run the frozen v3 worker in its already-tested diagnostic mode, FP32, greedy,
same budget, same actual audio/processor layout, with full independent target
generation and same-input repeat, oracle-as-candidate check, and actual fallback
layout repeat/self-check where applicable. Check original versus replayed
processor batch tensors/IDs/features before calling outputs comparable.
Accepted candidates must agree with the separately generated reference on
the measured batch. A disagreement is a numerical/reference-contract failure,
not a silently discarded case. Unknown labels stay unknown.

The unsafe Unprotected replay uses the strict *diagnostic* operator to obtain
labels; it does not retrospectively protect the original admitted trajectory.
All calls/power/wall are diagnostic costs, excluded from serving comparisons.

## Observable future effect, all up-to32 unprotected source opportunities

Starting at the actual unsafe target and its correct-parent generated reference,
run a paired continuation to the complete source endpoint with the next live
chunk index, same waveform, precision, budget and declared two-row layout. Only
the parent feedback differs. Repeat the identical pair; save actual inputs,
new Z, normalized P/text, stop/cap and full-reference error counts for both.

Report different new Z, different final text, worsening/equal/improving errors
separately. A copied-prefix difference is not new generation; token divergence
is not automatically semantic damage. These are controlled trace-derived
counterfactuals, not natural fault incidence or new online trajectories. The
actual clean/F2 serving comparisons remain separately matched using their
logged pre-intervention state/processed inputs; nonmatches are total effects,
not attributed solely to feedback.

All choices above precede viewing formal WER/P99/energy tables. All outcome
branches are retained. If exact inputs/repeats fail, freeze that evidence and
do not claim equivalence or positive propagation for that opportunity.

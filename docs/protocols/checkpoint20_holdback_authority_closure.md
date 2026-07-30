# Checkpoint-20 low-margin state-holdback closure

## Selected candidate

The ordinary FP16 batched proposer emits provisional text. A proposal whose
full-candidate minimum margin is at or below the frozen threshold is held out
of the textual revision state. `prepare_job` has already advanced the audio
frontier, so the next chunk is decoded from the last admitted text state plus
additional audio. Every 20 seconds, and at session termination, a fixed B=12
batch-invariant FP16 authority reconstructs the complete terminal state
projection and starts a fresh segment.

This is a state-entry transaction contract, not exact equivalence to the
official singleton trajectory:

- high-margin entries are admitted under a time-uniform statistical risk
  contract;
- low-margin nonterminal candidates remain provisional and have no authority;
- terminal/checkpoint results are always canonical;
- deadline pressure never promotes a held-back candidate.

## Causal comparison

The preceding ordinary-authority contract failed the five-seed P99 gate in two
seeds because a rare low-margin singleton verification serialized after the
proposer. A fixed B=2 authority was rejected because it was not cross-shape
equivalent to B=1, and fixed B=12 intermediate verification was rejected
because its constant work increased P99 further. Holdback removes this
nonterminal serialization without weakening state-entry authority.

## Frozen gates

- five independent 120-second seeds, maximum seed P99 at most 1.9 seconds;
- zero deadline-miss events and zero selected-authority violations;
- time-uniform state-disagreement UCB at most 0.5%;
- at least 16 English and 16 Chinese paired quality sessions;
- per-language observed mean WER/CER increase at most 2 percentage points;
- zero catastrophic quality outliers.

## Event and evidence terminology

- A `revision opportunity` is one session-round pair presented to the
  controller.
- A `committed state transition` occurs only when an authoritative or admitted
  result updates textual feedback state.
- A `provisional holdback` advances audio but does not commit generated text.
- The recorded 10% `verification_fraction` in the frozen service JSON is the
  fixed checkpoint-authority fraction (6 of 60 rounds), not synchronous
  low-margin verification. Under holdback, the latter is zero.

Resume-based quality repair must match the mechanism digest, exact contract
file, B=12 deployment parameters, session set, ordered source IDs, references,
and inherited transcripts before any GPU worker starts. The final evidence
also records a post-run content identity extension with audio byte hashes,
GPU UUIDs, software versions, and source fingerprints. That extension does not
retroactively strengthen fields absent from the at-run mechanism contract.

## Calibration sufficiency repair

The first two-episode run produced 1,440 audited events but did not certify:
after enforcing the pre-existing `0.031251` failure floor, the split-sample
validation suffix contained too few admitted events for a 0.5% upper bound.
The controller certified only after event 1,893 in the following heldout
episode, contaminating its service latency with fail-closed calibration.
That run is retained as `calibration_insufficient_audits_negative.json`.
The repaired protocol uses three calibration episodes and starts heldout
measurement only after certification. It disables dependent post-stage replay;
the separate randomized anytime audit supplies the formal risk claim.

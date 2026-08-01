# Excluded Whisper W5 epoch 202726

## Decision

`EXCLUDED_FAIL_CLOSED_STATE_ROOT`

The entire formal seed epoch `202726` is excluded from paper aggregates. The
first three completed seeds are not retained selectively.

## Trigger

`base-W1-seed20272604-revtrace.json` reported one stable output mismatch and
one stable state-entry mismatch. A same-input canonical repeat was exact, so
the event is not classified as transient canonical nondeterminism.

The escaping event occurred at session 3, window 1 with prior prompt length
30 and proposer margin 0.06640625. The frozen base/c16 policy covered a lower
global threshold, a later-window frontier, and a high-load frontier beginning
at prompt length 67. It therefore did not cover this early, medium-prompt
numerical root.

## Repair protocol

1. Extract the event as an external W4 adaptation root.
2. Renew the base/c16 state-age policy without overwriting older policy
   artifacts.
3. Run an independent 30,000-entry/500-audit W4 certificate on disjoint
   `202727xx` seeds.
4. Run a dual-GPU live preflight with zero output/state violations.
5. Start the formal matrix on disjoint epoch `202728` only after both gates
   pass.

This record distinguishes a policy-boundary failure from an implementation
failure and prevents post-hoc seed selection.

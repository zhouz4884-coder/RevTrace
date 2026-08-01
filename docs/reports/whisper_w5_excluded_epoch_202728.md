# Excluded Whisper W5 epoch 202728

## Decision

`EXCLUDED_FAIL_CLOSED_LONG_STATE_ROOT`

The entire formal epoch `202728` is excluded from paper aggregates. No
completed base W1/W2 rows are selectively retained.

## Trigger and attribution

`base-W3-seed20272841-revtrace.json` reported one stable output mismatch and
one stable state-entry mismatch at session 6, window 13, prior prompt length
97, and proposer margin 0.048828125. Same-input singleton repetition was
exact, so the event is a repeat-stable batch-to-canonical numerical root, not
canonical nondeterminism or state leakage.

The frozen base/c8 policy had only a global 0.015626 frontier. It therefore
did not cover this late long-state decision. A first renewal at window 13
was also insufficient: an independent audit exposed an earlier long-prompt
root. Further independent auditing showed that state age was not the common
factor; prior prompt load was. The final frozen policy uses a prompt-load
frontier at 58 tokens and retains the global threshold. Frozen-calibration
verification cost is 11.103%, below the 20% gate.

## Repair protocol

1. Treat the W3 event as adaptation-only and exclude epoch `202728`.
2. Use `202729xx` and `202731xx` only for adaptation, then run two independent
   30,000-entry/500-audit base/c8 certificates on disjoint `202733xx` seeds.
3. Run a fresh 180-second c8 dual-GPU preflight.
4. Release formal epoch `202730` only if all safety and performance gates pass.

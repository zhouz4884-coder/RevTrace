# Preserved formal development outcomes

## v1 source 035659082a93ba55167bee3709fd6de717f2bba1

Actual single-CPU pilot at `results/revtrace/freeze_boundary_20261027/formal/pilot_v1`:

- SANY rejected three empty-sequence spellings `<<>>` in AdmissionLifecycle, treating the adjacent closing token as an incomplete `>` operator. No admission state exploration completed; this is syntax failure, not a safety counterexample.
- Actual TLAPS 1.5.0 checked all 20 proof obligations in ProtocolProofs (exit 0). This parameterized lemma result is separately valid; it does not turn the failed TLC pilot into a successful study.
- Repair changes only empty sequence spacing to `<< >>`, preserving all guards, constants, invariants and expected negatives. The next run must freeze a new source commit.

## v2 source 3b954d3892e00f150189b23147aac637bd0ff519

The first spacing repair was insufficient: SANY still rejected `=<< >>` because the adjacent equality/opening token is lexically ambiguous. The concrete error is retained in `formal/pilot_v2`. V3 adds spacing around the equality as well: `= << >>`. No transition or invariant is relaxed. The unchanged parameterized TLAPS module again proved all 20 obligations; the TLC pilot is still not a pass.

## v3 source 210b373f9bc287ae71cf163fd97dcb8b1a95f879

TLC explored 54,156 distinct states before its extra default deadlock diagnostic stopped at a valid bounded terminal history: all two offered audio units were durable, installed and visible, the allowed restart completed, and the only committed receipt was replayed. No declared safety violation was reported. The finite specification already permits stuttering, but configs omitted `CHECK_DEADLOCK FALSE`. V4 states that choice explicitly for all finite cuts. This is not a deadlock-freedom result and does not claim accepted work always completes when the finite job-ID set is exhausted. All safety invariants, negatives and explicit fairness properties remain active.

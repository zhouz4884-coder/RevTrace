# RevTrace Phase 6 submission-repair report

Decision: `PHASE6_SUBMISSION_REPAIRS_COMPLETE`

## Phase 6A — Evidence lifecycle and epoch fencing

Decision: `PHASE6A_SEMANTIC_GATE_PASS`.

The offline semantic gate uses the real Phase 5 c32 failure. Positive
certificates restore only for an exact contract and remain canary-gated.
The c32 counterexample persists at a threshold floor of
`0.109376` only inside its execution
applicability cone. Cross-contract positive reuse is zero. Contract and policy
epoch changes both reject late results. This is protocol evidence, not a
serving benchmark.

## Phase 6B — Complete contract scoping

Decision: `PHASE6B_CONTRACT_SCOPING_REPAIR_PASS`.

The exact 0.6B/c32/120-second/burst/Chinese cell was rerun. The first
64 state entries were fail-closed, the
known margin 0.109375 event was verified, and
the final state-violation count is
0. The live P99 is
6.107 seconds with
1266 misses. Contract scoping is
repaired, but the cell remains a capacity boundary.

## Phase 6C — Joint risk–SLO admission

Decision: `PHASE6C_JOINT_RISK_SLO_ADMISSION_PASS`.

The historical c64 contract (P99
2.889 seconds,
448 misses) is not admitted at c64. The
controller reshapes active service to c16 and backpressures 48 new sessions.
The live admitted stage has guarded P99 1.397 seconds and
0 deadline misses.

## Phase 6D — Feasible live adaptation

Decision: `PHASE6D_FEASIBLE_LIVE_ADAPTATION_PASS`.

The persistent two-GPU process switched English c16 to Chinese c16 and back.
Both populations remained in the two-second service region. The two new
contracts learned independently; the exact return used
`exact_restore_canary` and renewed in 64 events rather
than 1358, reducing recertification events by
95.29%. Cross-contract certificate reuse and
deadline misses are both zero. The largest observed stage-level state risk is
0.0000% and every reported statistical upper bound is at
most 0.5%.

### Implementation repair audit

The first attempt incorrectly erased the quarantine learning window whenever a
caught proposer/canonical counterexample appeared. The second attempt retained
quarantine evidence but invalidated an active statistical certificate too
aggressively while leaving its cached copy eligible for exact return. The
final state machine separates three cases: quarantine failures raise the
learning floor; active-certificate failures atomically recompute the stricter
window and retain it only if the risk gate still holds; return-canary failures
delete the cached certificate. Both failed raw traces are preserved by hash
and summarized in the Phase 6D result.

## Publication boundary

Risk-limited mode may observe errors allowed by its statistical contract.
Canonical-consistent strict mode is relative to the frozen canonical path, not
mathematical truth or a bitwise repeatability guarantee. The repaired c32
contract remains non-admissible under the two-second SLO. No
deterministic-certificate, Whisper-speedup, or slack-packing claim is added in
Phase 6.

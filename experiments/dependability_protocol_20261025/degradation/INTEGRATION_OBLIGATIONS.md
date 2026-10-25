# Obligations before calling the CDE core a live mechanism

Current code is CPU core/accounting plus a tested actual fsync input journal.
No CDE serving Runtime, held-out GPU result or performance advantage exists yet.
v0 core13/input8 are preserved in09a375c; v1 overlapping full set has25 tests,
including4 receipt-bridge tests. Do not add25+13+8 or call them GPU trials.

1. v0 applied an in-memory acceptance intent. v1 now separates nonmutating
   `acceptance_intent` and receipt-bound `accept_released`; `accept_durably`
   checks first, actually synchronizes the input journal, then changes accepted
   eligibility. CPU injected-sync-failure leaves accepted/debt unchanged. Live
   wiring must call this bridge and acknowledge only afterward; it is not yet
   integrated into the GPU runtime. Receipts rely on the trusted local caller,
   not a MAC against a malicious owner.
2. InputJournal v0 pins accepted prefixes; explicit terminal rejection/abort
   decisions and recovery rebuilding need integration. Wholly unaccepted new
   sessions may be rejected; accepted prefixes cannot be erased. Do not reset
   rejection or acceptance obligations silently on restart.
3. Whole-interval reservation avoids the demonstrated partial-credit deadlock,
   but does not prove progress if a reserved source permanently stops offering
   audio. Keep the availability/fairness assumption explicit; unused reservation
   expiry or accepted-prefix termination would require a declared, actually
   computed trusted final interval, not a fabricated frontier. Test this limit.
4. Recovery must restore outstanding full-interval reservations consistently
   with accepted debt and the same quantum/budget; setting every reservation
   to zero would create unbacked acceptance. Do not allow new input to consume
   credit needed by already acknowledged incomplete intervals.
5. Current policy core selects modes by observed debt age/credit; it is NOT yet
   a validated feedback-aware per-target scheduler. Actual queue/lease and
   valid-provisional inputs must influence any claimed extra control. Do not
   repeat the CES mistake of logging a feature that never changes decisions.
6. Consumer ACK must be actual local application, tied to the current epoch and
   canonical context. Server publication or an old ACK cannot mint new coverage.
   No-history recovery needs an explicit fresh-stream acknowledgement to avoid
   waiting forever for a nonexistent canonical snapshot.
7. Replay arrivals are not network backpressure. Separate source offered time,
   acceptance time and model dispatch eligibility. After restart, previously
   accepted audio is physically available, but original deadlines must not be
   reset; new t0 cannot give expired requests fresh SLO credit. All audio offered
   during downtime stays offered/unaccepted/rejected in explicit denominators.
8. All safe baselines get the same ingress semantics/resource and cost budget;
   compare the extra feedback-aware control against ordinary fair credit/queue
   control, not only unlimited original DGFT. Rejected input is not a latency win.
9. Prepared audio/manifest persistence is an explicit prototype assumption.
   InputJournal does not store live waveform bytes; do not claim survival of
   lost input storage, host corruption or a deployed distributed ingress.
10. Freeze a new runtime/manifest/config before GPU, separate from unchanged
    N1 f0e5864. Keep new CDE/attack/base formal validation and gate outcomes in
    the combined completion audit. Do not declare the original goal finished
    merely because N1 and the base finite model complete.

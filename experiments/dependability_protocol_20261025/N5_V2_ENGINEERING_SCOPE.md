# N5 v2 common runtime repair, not a new CES/controller family

Four v1 real GPU development episodes passed independent input/row/Consumer,
Canonical WAL and asset replay gates. Recomputed controller CPU was1.47/1.70s
at c4 and3.62/3.95s at c16. Host time additionally includes input fsync (up to
2.34s). These are shared accounting/decision costs, not all caused by CDE's
feedback condition and not subtractable from wall time to claim a GPU speedup.

v2 eliminates repeated ingress-book cloning when original offers, canonical
versions, grant permission and rejection deadlines have not changed. On a real
trigger, whole-credit round-robin advances to a fixed point; its cursor moves
only for a real grant, not arbitrary idle tick counts. A diagnostic CPU-only
uncached v2 path produces identical fixed-clock ACK/Canonical histories in
four controller modes. This is not a claim of exact v1 wall-clock/decision
equivalence: v1's tick-dependent fair tie order was changed explicitly.

CPU benchmark: four repeats of10000 no-op calls on one final16-source snapshot,
all obligations unchanged and no journal write. Cached median threadCPU0.125s,
uncached1.492s on this Windows host. This is only a local idle-state CPU result;
Windows timing quantization is retained. No end-to-end/GPU improvement is inferred.
The1000-call v1 benchmark under-resolved the cached CPU measurement and remains
retained, not quoted as infinite speedup or zero overhead.

All safe baselines receive the same v2 common engine. Fine's trusted selection,
resources, limiter and deadline ability are not weakened. CDE feedback rule,
thresholds, fixed rho and source pool remain unchanged. An older Consumer ACK
is now explicitly fenced/logged rather than fail-stopping the Owner; it cannot
mint coverage. No actual future output/fault-label or new candidate source is used.

Additional CPU controls reproduce the pre-fix completed-session cursor failure,
same-input repaired closure, active-book immutability on actual fsync failure,
and stale-ACK fencing without loss of canonical service. No v1 GPU data is edited.
v2 has a new branch/source identity and separate development output. It must
independently pass Linux tests and actual GPU/data audits before formal freeze.

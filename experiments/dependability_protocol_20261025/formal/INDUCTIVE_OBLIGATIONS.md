# Conditional invariants and abstraction-to-code correspondence

## Evidence scopes

The Python BFS and separately written JS DFS agree on all reachable-state SHA256,
state/transition counts and violated properties for 63 finite configurations.
There are 73,770 state visits and 290,192 edges **summed across configurations**;
these are not 73,770 distinct global deployment states. Seven full-guard cuts
have no monitored violation. Every search exhausted its worklist without a
state cutoff. Results are in CROSSCHECK_v2; Python supplies shortest witnesses.
v1 was a draft without an explicit receipt-return action; v2 adds that action
so write-before-receipt is tested even before actual Consumer application.

Bounds: one canonical interval, released frontiers0/1/2, private prefix plus one
successor (depth<=2), one epoch change, one retry of an already durable identity,
one immutable row per lane, independently ordered row completion/batch drain,
FIFO publications. Malformed parent/interval and foreign receipt are separate
injected initial cuts, not natural histories. The model does not enumerate all
multi-session schedules, arbitrary histories, neural outputs, all disk failures,
or actual model-input realizations. The shared formal specification is not
independent authorship. Cross-language agreement does not exclude a shared
specification error; production mapping/tests below are an additional obligation.

## I1 Authorized ancestry — induction on accepted installs

Base: genesis has the declared empty/current P and no selected history.
Step: only the owner calls canonical replacement, with the recorded current
Parent, same session/epoch/contract/runtime, complete trusted selection witness,
frozen actual conditioning input and exact selected Z/P. Validation leaves state
unchanged on failure. Therefore an accepted next P extends the recorded parent
chain. No private result has this write transition. An arbitrary trusted worker
or caller corruption can violate the premise; hashes do not repair it.

Mapping: `dgft.commit_canonical_segment`, `LiveQwenScheduler._commit_ready` and
the actual trusted execution boundary. Serialized certificates contain the
declared runtime/audio/prompt/Z/P bindings; model-input-audit hashes are separate
observations, not hardware attestations or necessarily certificate fields.
Cross-check: parent/epoch/foreign-row cuts; actual core tests `test_dgft`,
`test_online_coordinator`, row receipt validation and historical E1 F5 boundary.

## I2 Gap-free unique admission — induction on frontier

Base F0 is genesis or a validated recovered prefix. Step requires a=F and b>a;
the consumed identity is new; acceptance appends one transition and sets F=b.
Thus intervals are contiguous, nonoverlapping and strictly advancing, regardless
of the chosen allowed interval lengths. Identical retry is an old receipt, not
another step. This proves neither quality invariance nor an implemented elastic
granularity algorithm. It also does not make a sync group globally atomic.

Mapping: core predicate, stable session/audio transaction identity and persisted
consumed receipt. Cross-check: gap cut and core duplicate/restart tests. The
finite model's single retry abstracts a lookup; changed-payload and arbitrary
history dedup are tested by actual WAL code, not proved by that abstraction.

## I3 Fresh publication — atomic owner check then provisional publish

At acceptance, require b>current F and active generation. Check and publication
are serialized in one owner action; a Canonical install cannot interleave
between them. Therefore those two stale classes cannot be newly published.
Restart additionally relies on a fresh job registry/transport plus epoch
fencing. The model's explicit job-epoch guard abstracts that boundary; the old
Runtime does not reconnect arbitrary multiprocessing queues after restart.
No inference is made that an ahead result automatically has a compatible root.

Mapping: `_accept_result` (mechanically extracted original receive body), lazy
finite reconciliation, immutable job registry. N1 omits only the receive
freshness decision. CPU tests demonstrate covered publications and actual
Consumer successful rejection separately; N1 supplies real completed rows.

## I4 Exact-chain provisional continuity — induction on path edges

Base: at the new canonical audio boundary, actual private projection equals
canonical P. Step: each next private job's frozen input equals its predecessor's
actual output, chunk/frontier order advances, generation matches and the complete
pending job, if any, is rooted at that tip. Therefore retaining the **whole**
private view preserves a causal input path from the certified boundary. It does
not certify its transcript, numerical equivalence to another regeneration,
reference-path selection, token/audio alignment or any unobserved new-parent
execution. Batch-dependent input realization remains an independent boundary.

On every canonical Consumer update, retain only if this predicate still holds;
on every new provisional delivery, check it again. A later correction may validly
withdraw a previously legal view. Removing the check can expose an incompatible
view even while every canonical transition remains legal.

Mapping: `continuity_proof.eligible_chain` plus `ContinuityView._compatible` and
typed certified/provisional lanes. Full Standard is allowed both. Model equal
and different-boundary cuts and actual exact-chain CPU tests check this
distinction. N1 pilot's four equal-root targets are positive controls. The
completed54-run N1 audit supplies one actual root-incompatible snapshot view;
the full two_lane Consumer excludes it. It occurs before the later chosen IPC
hold: reachability, not a causal effect of that later intervention (N1 report).

## I5 Durable certified view — prefix persistence and typed publication

A successful durable receipt follows complete synchronous persistence. Recovery
validates each complete frame and reconstructs a contiguous state/identity/render
prefix; only an incomplete final frame may be discarded. Each certified snapshot
must name an installed/persisted fact with exact Z/P/text and identity. On restart,
fresh Consumer stream and replay reestablish those facts without reinstalling an
identical acknowledged request. A complete bad frame fails closed, not silently
rolled back. No storage corruption repair or power-loss measurement is claimed.

Mapping: `DurableCommitJournal`, `replay_bound_text`, canonical publication and
strict bound Consumer. The model tests incomplete-prefix/sync ordering and the
receipt-return boundary. Full-frame corruption, changed retry payload, journal
second-owner lock, multi-record prefix and actual SIGKILL are separate code/GPU
evidence, not consequences of a symbolic checksum bit.

## Progress and completeness limits

These are safety arguments. Eventual publication needs fair owner/Consumer
scheduling, available audio, terminating selected computation, finite pending
work and successful storage. No unbounded-stream memory claim, cap-free
recognition, natural failure prevalence, unconditional liveness or bounded RTO
follows. A 2 s/8 s SLO miss remains a measured capacity/performance outcome.

Full history induction is conditional reasoning, not automatically machine-
checked by the finite checker. A future stronger mechanized refinement could
increase assurance; it is not silently implied by the present cross-check.

## Actual regression evidence

CPU_N1_v1.xml:152 focused tests; remote Linux same152. Expanded local set:
CPU_PROTOCOL_EXPANDED_v1.xml,206 tests, includes original admission/coordinator,
immutable row/batch transport and progress, terminal recovery and display policy.
These sets overlap and must not be added. They are not the whole historical
repository test suite. N1 measured Runtime source remains f0e5864; auxiliary
checker changes never modify formal GPU measurements.

# Certified degradation: layered specification and conditional arguments

This is a protocol extension of INDUCTIVE_OBLIGATIONS, not an unbounded verified
implementation or a new neural theorem. The original I1–I5 remain premises.

## State and externally observable obligations

For session s, O_s is audio offered at the immutable original arrival clock,
A_s a durably accepted prefix, C_s its installed certified prefix, V_s a legally
applied current-root view, and R_s the reserved complete authority interval.
The manifest gives immutable audio bytes, sample rate, language and EOF. Store
the original origin and explicit rejection; changing them on restart is not
recovery. Local input-ACK markers are server logical receipt facts, not measured
network client ACKs. Consumer observation is a different read-only channel.

Invariant E1:0<=C_s<=A_s<=O_s, R_s>=A_s,
`sum_s(R_s-C_s)<=B`. Reserve a whole next interval before accepting its prefix;
acceptance cannot create a hole or a job beyond A_s. R may extend beyond currently
released O, but no model dispatch can consume that unaccepted reservation.
EOF clips an interval, never grows it. In canonical_generate mode only trusted
Authority selected Z may install; none of the five modes relaxes I1–I5.

E2: every synchronized accepted prefix remains a recovery obligation until its
real certified transition, or an explicit durable resolution. This prototype
never aborts accepted audio. Only wholly unaccepted new sessions may be rejected,
with persistent reason. A timeout retains debt/failure; it is not silently
certified. All offered, rejected and missing frontiers remain metric denominators.

E3: CERTIFIED-ONLY/RECOVERY actual visible text/frontier is the currently applied
certified fact (including the explicit no-certified-snapshot-yet F=0 case).
Entering the mode withdraws tentative visibility, not Canonical state. Old V is
not converted into new C or relabelled current after a Canonical/epoch change.
The actual owner/contract/epoch/version observation fence is read-only telemetry;
it never supplies selection evidence. Single owner and FIFO local Consumer are
assumed; no network delivery or Byzantine authenticity is proved by a digest.

## Conditional preservation arguments

Reserve increases R only if the full incremental credit fits B; offering only
increases O; acceptance clones the book, validates bounds, fsyncs its complete
snapshot, then swaps the active book and emits the receipt. A sync exception
cannot increase dispatch-eligible A. A trusted admitted interval advances C
within A and decreases debt; no mode action mutates C or P. Thus E1 is preserved
by induction over successful owner transitions, conditioned on I1/I2.

After process crash, input framing validates a complete snapshot prefix and
Canonical WAL validates a complete selected history. Reconcile old snapshot C
with real restored C, requiring old C<=actual C<=A. R, EOF, rejection, prefix
digest and original clock are restored/validated before eligibility. Fresh
epoch/stream observations start empty. The actual immutable audio prefix is
rehash-checked. Under successful sync, intact available storage/audio, and the
single-writer assumption, acknowledged A is not lost or falsely advanced.
This argues E2, not bounded RTO, cap-free recognition, storage repair or host
power-loss behavior. Input ledger failures can fail availability closed.

A reservation need not uniquely be stored in this exact format. The finite
positive control reconstructs a correct R from fixed quantum/EOF/A. A naive
zero-reservation recovery fails readiness; correct conventional reconstruction
does not. Therefore no minimality or conventional-composition impossibility is
claimed. Conventional input journals, backpressure and full Standard can carry
these application obligations.

Mode publication carries current contract/epoch/revision and is applied by an
actual Consumer. In the two strict modes provisional arrivals are suppressed
and existing private visibility is purged. I4 is still required for every normal
provisional view; no string splice or stale-as-fresh grant is added. These steps
preserve E3. They can **reduce** provisional coverage or miss deadlines. Honest
withdrawal is not necessarily a Goodput or quality improvement.

## Independent bounded crosscheck

CDE_PYTHON_v2 uses BFS; separately written CDE_JS_v2 uses DFS. Both exhaust the
same finite specification; compare_envelope_v2 checks counts, transitions,
reachable-state SHA and violated properties for every configuration. Bounds:
one session/three units or two sessions/two units, quantum2/budget2, one restart,
five modes, one delayed observation; violating states are terminal. No all-history
neural or OS/FS refinement proof, fairness/liveness or performance conclusion.

The base model separately checks actual private ancestry and row/drain ordering;
this envelope abstraction assumes trusted canonical admission and legal Private
consume, and treats successful input persistence atomically. It is not a full
Cartesian-product verification of both runtimes. v2 adds an explicit old-root
ACK counterexample within the same epoch; an epoch-only fence is insufficient.

Guard omissions cover sync-before-ACK, reservation reconstruction, explicit
mode purge, epoch fence, current-root observation, trust bypass (negative only),
credit limit and terminal rejection. Python contains executable shortest action
traces; JS verifies complete reachable sets under the same shared specification,
not independent authorship. See CDE_CROSSCHECK_v2.json for exact totals.

## Source correspondence and evidence separation

- CreditBook.reserve/offer/check/restore: integer O/A/C/R and immutable prefix.
- InputJournal.checkpoint: actual append/checksum/chain/fsync; active book swap
  only after success in CertifiedEnvelopeScheduler._ingress.
- _ready/_make_job/_finish_commit: accepted frontier bounds and original I1–I5.
- _consume_acks/valid_private_frontier: incarnation/epoch and current version.
- _choose_mode/_set_mode: observed feedback/queue/lease policy and typed transition;
  no output truth, fault label or future service estimate input.
- EnvelopeView.consume: strict-mode purge and no fresh coverage from old text.
- Constructor/run: original origin, persistent terminal rejection, full offered
  accounting and final actual Consumer catch-up.

Runtime408d756 differs from21d15cb only in optional fault observer. CPU238 tests
include sync failure before dispatch, canonical-prefix recovery, EOF/reservation,
old ACK fencing, mode behavior and common core/Consumer/WAL/row tests; overlapping
counts are not added. CPU fixtures, finite model, asset reprocessing, controlled
GPU process faults and independent live workload performance remain separate
evidence. Formal performance/recovery experiments are pending, not inferred.

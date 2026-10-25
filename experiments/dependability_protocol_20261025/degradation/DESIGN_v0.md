# Certified Degradation Envelope — design hypothesis, not GPU success

## My design judgment

Do not make this another evidence-selector or tuned rho controller. The useful
missing accounting is **offered != accepted != certified != currently visible**.
A private queue can be empty while accepted audio still lacks certified state;
dropping queued work can lower latency while silently losing that debt. A
degradation controller should conserve explicit input obligations and control
only not-yet-issued work. Whether this improves offered-audio service relative
to ordinary fair backpressure is a falsifiable experiment, not assumed novelty.

## Four frontiers, not one overloaded progress counter

For each session: O=actually offered/released audio; A=durably accepted prefix;
C=durably admitted canonical audio; V=actual legally consumed provisional view.
Invariant0<=C<=A<=O. V can be farther ahead than C only with the existing exact
private-chain condition, and never earns certified coverage. It can validly
withdraw after correction. Received/rejected/offered input and any unfinished
accepted debt remain in the full experiment denominator.

Let R be a reserved end for the next authority interval, and let

    debt = sum_s(A_s-C_s)
    reserved_debt = sum_s(max(A_s,R_s)-C_s) <= B

Reserve a **whole next authority interval**, not arbitrary tiny per-session
credits. Otherwise all sessions can fill half a coarse interval and deadlock:
no session has enough accepted audio to run the authority that returns credit.
Reservations are not permission to consume future audio. Actual acceptance and
job dispatch still require released audio, immutable audio/manifest identity,
current parent/frontier and all original checks. Credit returns on actual WAL
admission; graceful EOF releases only unused reservation, not accepted debt.

An accepted-input decision journal pins the immutable input manifest/chunk
digests and accepted prefix before acknowledging acceptance. On recovery,
canonical WAL and input decisions reconstruct outstanding debt. This is not a
second canonical P history. Its CPU/fsync/storage cost is charged to every
baseline granted the same acceptance semantics. The existing prepared audio
files can back a replay prototype; do not call it a deployed network ingress.

## States and only permitted actions

* NORMAL: accept within reserved credit; normal private/display and authority.
* DEGRADED: debt/lag warning from actual canonical and valid Consumer progress;
  limit additional not-yet-issued private lead. No GPU cancellation is claimed.
* CERTIFIED-ONLY: stop new speculative dispatch/publication; keep authority
  draining accepted intervals and publish genuine durable canonical facts.
  Complete old work stays paid and may only be retired/cached under old rules.
* BACKPRESSURE/REJECT: no additional credit without capacity. Backpressure
  delays acceptance, not original offered timestamps or deadlines. The minimal
  controller may reject a wholly unaccepted new session explicitly; it cannot
  erase already accepted audio. An abort, if supported, is a distinct recorded
  terminal outcome and cannot install a fabricated audio frontier.
* RECOVERY: no provisional credit from an old epoch; restore both ledgers,
  replay trusted render, start a new Consumer stream and republish durable facts.
  Leave only after actual certified Consumer acknowledgment, not owner load time.

Hysteresis and bounded response must be declared, not tuned on held-out results.
Controller cannot read payload targets, fault flags, future model lengths or
post-hoc WER. Any state transition leaves the original admission predicate fixed.

## Fair comparison and possible NO-GO

All methods get the same immutable row executor, full safe Consumer, input
credit semantics/physical resource budget and cost metering. Compare:
AlwaysFine+fair limiter; fixed original DGFT; full Standard+same limiter;
ordinary queue/token backpressure; CDE and its feedback-state ablation.
Separate shared accounting correctness from extra feedback-aware control value.
Count rejected/blocked offered input; report matched acceptance-set comparisons
as a secondary diagnostic only, not a substitute for offered-audio results.

If ordinary fair queue/credit control achieves the same safety/service envelope,
credit it. CDE may then be a specification/engineering completion, not an
independent algorithm contribution. No promise that overload meets all deadlines.

## Before implementation/GPU

1. Prove reservation conservation and no partial-interval credit deadlock under
   available whole-interval B; test fair granting, EOF, sync failure, partial
   journal tail, crash after acceptance/before canonical, repeated decisions.
2. Inspect actual Consumer ACK availability and map V to current canonical
   ancestry; do not mistake an old ACK or server emit for current legal view.
3. Integrate outside frozen N1 runtime in a new branch/source directory.
4. Freeze source-disjoint validation inputs and workload arrival transitions,
   SLOs/denominators and all strong baselines before new GPU execution.

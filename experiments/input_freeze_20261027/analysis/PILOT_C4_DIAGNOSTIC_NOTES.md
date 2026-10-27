# Independent six-arm c4 pilot findings

Source fdb1b1e30b06ee781046621376f458431f3ecb9f. Six completed fresh-process
development cells, one repeat, four original sources, synchronized arrivals,
rho1, full Row-complete backend and raw_slack wait budget. Remote reads only.
No production admit()/step() was used by this independent trace analysis.

## Measured facts

Each arm has34 offered frontiers,61.725 offered audio seconds,34 Private jobs,
34 Authority jobs,393 total Proposal tokens,zero caps,zero private skips,
zero expired Private targets,full actual certified coverage and all34 D2/C8
frontiers passing. All complete Z/P/text/Stop outputs match the immediate arm.
These prove a feasibility check on this input; they do not show a waiting benefit.

|Policy|Wait activations|Proposal paid lease seconds|Private physical batches|
|---|---:|---:|---:|
|immediate|0|10.719744|11|
|fixed|1|11.091719|12|
|pending_eta|1|11.116739|12|
|backpressure|0|10.871269|11|
|recent_gain|2|11.355161|13|
|state_aware|1|11.120887|12|

Every wait's actual next declared P is unchanged from the prewait Private P.
Every release nevertheless reports canonical_projection_changed=true. These
observations demonstrate that the old refresh proxy does not measure the
input-changing mechanism. In fixed/pending/state,one processed row differs from
the immediate row input because splitting one2-row batch changes tensor shape;
two full batch-layout identities differ. Recent changes two processed rows and
four batch-layout identities. Thus unchangedP is not universal processed-input
equality. Complete outputs remain identical on all recorded calls.

No overlapping physical Worker leases or duplicate job identities were found.
All decision Parent/frontier values match already observed commits, pending Job
identities were actually pending, original audio-release/D2 clocks match the
manifest, and cohort released/held sets partition the full eligible set.

## Integration defect and bounded repair

The old controller was called only when GPU0 became idle. It logged a fixed
.25s wait as.41796s, although the relevant Authority installed after.10725s;
the remaining delay came while a different session occupied GPU0. The new
tick hook must close logical waits every owner loop, including while GPU0 is
busy, and leave its physical lease untouched. Log logical release, owner
observation lag, Worker availability and postrelease-to-enqueue delay separately.
The original five logged waits remain gross blocked intervals, not exclusive
policy wait cost. Their completed GPU results are retained.

Old remaining-Authority estimates were .03874/.04686/.05012/.005/.01511s;
actual time to install was .10725/.11824/.08501/.05113/.10216s respectively.
The ETA underestimates these small tails. It currently predicts historical
enqueue-to-host receipt; installation and WAL/owner delay remain additional.
Do not claim a correct exact-install ETA from this predictor.

The v3 candidate records a pure description of prewait effective input following
the existing rebase rule, then records the actual new Job declaration. This is
CPU bookkeeping and does not generate a model output. Processed input changes
still require independent actual Worker records. Recent feedback now uses an
actual Consumer D2 AIMD rule with actual postwait service cost logs. Canonical
refresh by itself no longer increases the budget; absent output remains UNKNOWN.

## Next gate

V3 has44 focused CPU tests passing, plus two provided real-scheduler integration
tests that require root's tick/ACK integration. Next c16 development should
retain all original16sources and both sync/staggered arms. Both deadline-reserve
options and simple fixed/pending baselines remain eligible for equal-budget
development. No old-source cap or pilot micro-difference selects validation
sources. Independent confirmation still requires a new frozen manifest.

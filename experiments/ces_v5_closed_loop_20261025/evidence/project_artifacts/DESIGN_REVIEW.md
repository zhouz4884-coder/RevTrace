# Independent review of the complete closed-loop CES design

Date: 2026-10-25. This document is a design and acceptance review, not a claim
that the new implementation or GPU experiment has passed. Root owns runtime
implementation, freezing and all GPU execution. This reviewer modifies no
runtime, paper or historical evidence.

Starting source: `126dc815962e8f726b0cbdf214a19318b28a3629` on the isolated
`codex/ces-v5-closed-loop-20261025` branch. The failed 48-cell V5 result remains
archived at public main `d0529564935b4a045960645d3a00a2740c4bbaf4`.

## Design judgment

Proceed with one bounded closed-loop mechanism: preserve service obligations
across replanning, propagate deadlines through released Canonical dependencies,
and score actual Private/Canonical paths over the same audio atoms. These
parts address the observed same-Parent repeated postponement and the omissions
already identified in the CPU review. They do not alter the state-admission
predicate or justify assuming that the combined system will outperform Fine.

The implementation must make all four parts operational at actual dispatch:
(1) persistent service identity, (2) released successor obligations, (3) two
legal Display paths, and (4) conditional Verify-success compatibility. Logging
these features while the selector ignores them would not constitute full
integration. Conversely, a feature that has no usable opportunity should be
reported as dormant; it must not be assigned an artificial bonus.

## 1. Separate execution identity from a symbolic future obligation

A current executable target is identified by:

`(owner run, session, epoch, Parent version/digest, audio start/end, contract)`.

Its service record retains first eligibility, actual deferral count, an
unchanged completion promise where applicable, and the observed reason for
any breach. Replanning must not reset these fields or create a fresh identity
to erase waiting. Deferrals count actual issued physical batches that omit
an eligible target, not polling cycles or read-only planning calls.

An already released successor can be represented symbolically by Session,
audio interval, release, D/C deadlines and current ancestor identity. Its
future Parent projection is not yet known. It must not be represented as an
already executable Job or assigned a fabricated Parent. The actual next Job
is built only after the preceding transition has really passed admission and
WAL installation.

Service records are performance state. They confer no write permission and
need not silently extend C3's durability guarantee. Across a new owner epoch,
rebuild obligations from the durable Canonical state and fixed session
manifest, reject old ACKs/results, and explicitly reset or reconstruct the
performance record. Do not claim preservation of a timing promise across a
crash unless it is actually persisted and tested.

## 2. Carry a completion obligation without reverting to Commit-first

The original two-target counterexample must remain in the acceptance suite:
with G(A)=1.4 s, V(B)=0.2 s, A's own Display already missed, A Commit due 1.5 s
and B Display due 0.5 s, B-first earns two audio-seconds while A-first earns
zero. Both complete all work in 1.6 s. A deadline is a performance obligation;
making every Commit deadline a lexicographic hard constraint restores the old
zero-credit result.

The proposed service obligation comes from the first selected *complete*
continuation for a target, rather than retroactively forbidding the tradeoff
that continuation already chose. For an unissued suffix target, retain a
declared empirical completion quantile (for example `promise_quantile=0.9`).
Subsequent new work must not repeatedly move this promise later without an
explicit, logged breach/least-violation decision. A finite-deferral bound is a
separately declared forward-progress fallback, not a proof of the Commit SLO.

For the initial counterexample, the initial choice may promise A at 1.6 s even
though its own C deadline is 1.5 s. The next replan should not keep changing
that 1.6-s promise to 2.8, 4.0, etc. If real service or new observations make
the promise infeasible, retain the original obligation and report the breach;
do not hide it by resetting first-seen time.

Avoid an additional unexplained `Commit-late risk budget=0.1`. In the same
counterexample B-first has two late audio-seconds out of four, while A-first
has none. A 10% constraint would select A again; a least-violation fallback
would not activate because A is feasible. A quantile for a retained service
promise and a global Commit-violation budget are different concepts.

The completion suffix is a scheduling obligation, not a cached executable
command. Revalidate its identity, candidate readiness, Parent, frontier and
contract at issue time. Worker leases remain non-preemptive; previously paid
GPU work is not canceled or removed from cost.

## 3. Backpropagate deadlines through real, released dependencies

For each still-relevant audio atom q, retain its own weight, release, actual
first legal Display observation and C requirement. Its credit remains:

`weight(q) * I(D(q)<=release(q)+2) * I(C(q)<=release(q)+8)`.

If D is already satisfied, a predecessor may inherit the successor's remaining
C deadline. If D is still attainable only along a Canonical path, it may
inherit that path's D deadline minus the paid remaining work. If an independent
legal Private path can satisfy D, do not pretend Authority is a mandatory
Display predecessor. If D is irreversibly late, q has zero own credit but may
still be a necessary ancestor of a different, released, creditable atom.

A useful effective deadline is therefore path-specific. Only propagate along
an actually permitted dependency and deduct its complete modeled service,
physical lease and delivery costs. Do not propagate from unreleased audio or
double-count the same audio through both paths. The result guides which legal
subbatch to issue now; it does not authorize future audio or an unknown state.

The symbolic module already present in the CPU study must now receive current
runtime snapshots and affect candidate selection. At least one CPU case must
show that toggling a released successor changes the chosen *Session set* while
the current targets/costs remain otherwise fixed. A log field alone is not
evidence that backpropagation is operational.

## 4. Model Private and Canonical Display as two actual paths

The Display endpoint is `min(legal Private observation, Canonical publication)`.
It is not generally equal to Authority completion. The runtime snapshot needs
actual completed/in-flight Private jobs, frozen inputs, branch generation,
Consumer ACK history and physical Worker availability. A pending private row
may supply a forecast path, but cannot be credited as an already applied view.

The full objective should account for observed cumulative credit and elapsed
wall time when comparing a common finite continuation, and explicitly state
its remaining horizon. A scenario-level finite-prefix ratio is a reasonable
declared objective; it is still not an optimal policy for all future arrivals.
The two paths share resources and state, so their event probabilities cannot
be multiplied as independent facts without an explicit model assumption.

First legal visibility is historical. A later retraction does not erase that
original metric; uninterrupted visibility until certification and retractions
remain separate sensitivities. Ready, valid Authority results must proceed
through normal installation promptly. Delaying a ready commit to let a stale
Private view earn first-visible credit is not an acceptable scheduling action.

## 5. Conditional Verify-success compatibility must remain conditional

For an actually available candidate Z and current target Parent P, trusted
render defines `P_V = Phi(P, chunk, Z)`. On a read-only shadow of the current
Session, use the existing exact `eligible_chain` rule to determine whether a
successful Verify would retain the actual private chain. Check the matching
audio boundary, exact projection, branch generation, every frozen edge and
any in-flight successor input. Do not substitute string prefix concatenation
or merely matching birth Parent.

This is only the successful-Verify branch. It does not prove that the FP32
verifier will accept Z. Expected benefit must include measured acceptance risk
and complete paid Fallback. No shadow projection may mutate real Session
state, produce a certificate, publish a Canonical view, or dispatch a future
child before the actual commit.

Direct Generation and Fallback produce an unknown P before execution. Unknown
is not equivalent to incompatible. In the absence of matched conditional data,
use an interval or neutral common treatment for these unknown outcomes. Giving
Direct zero retention probability while giving Verify a positive preservation
bonus merely recreates the invalid operation-specific assumption implicitly.
If the interval cannot distinguish actions, omit that differential reward and
retain the conditional chain information for audit/action construction. The
physical evidence-choice cost can still distinguish the actions.

## 6. Actual actions and shared baselines

GPU1 choices must include real homogeneous subbatches and order, using shared
physical cost/calibration and actual Batch-drained leases. A limited change to
GPU0 ordering at n<=16 with batch limit=16 still selects the same ready set;
that alone is not a new joint-resource action. If the full design proposes
GPU0 subsets or waiting, these choices and costs must be explicit and shared
with the appropriate control. No running batch is physically preempted.

Required comparison pairs may be staged instead of expanded into a needless
full Cartesian matrix:

| Question | Required comparison |
|---|---|
| Does the complete integration improve the system? | Full vs Fine, complete Standard Safe Async and strong shared-cost control |
| Does persistent service state matter? | Same full actions/model with and without persistent suffix/service obligations |
| Does released-successor propagation matter? | Reservation-only vs reservation+backpropagation, same action budget |
| Do dual paths matter? | Same planner with Canonical-only forecast vs actual permitted Private+Canonical paths |
| Does conditional compatibility actually help? | Full vs neutral/disabled conditional compatibility, if that feature is exercised |
| Is a gain only from executor/subbatch capability? | Give that capability to Fine/Standard or a complete conventional cost/EDF control |

Shared transport, Consumer and measurement facilities are available to all
arms. Do not force Fine to run an unused expensive predictor to inflate its
overhead; charge each method's real decision cost. No source/fault labels or
future outputs enter the policy. All methods retain the same precision,
quality, arrival, energy window, unfinished-request and SLO definitions.

## 7. CPU acceptance matrix before GPU freeze

| Area | Required fixture/assertion |
|---|---|
| Initial tradeoff | Original 2/8-second Commit-first counterexample still chooses B-first and completes all work |
| Closed-loop persistence | Six-arrival same-identity postponement probe no longer silently moves the original suffix promise on every decision |
| Infeasible service | Overload/cost-error case logs breach and least violation without changing admission or dropping work |
| Correct aging | Repeated pure planning/polling does not increment deferrals; an actual competing physical dispatch does |
| Identity | Parent, epoch, contract or frontier change cannot inherit an unrelated promise; unchanged identity retains first eligibility |
| Completion/restart | Promise resolved on actual durable install; restart reconstructs performance state and rejects stale ACK/results |
| Released successors | A released useful successor changes an actual selected subset; an unreleased successor has no influence |
| Zero/duplicate reward | D-met retains C credit; D-expired does not regain own credit; Private and Canonical routes cannot duplicate an atom |
| Backprop degeneration | No eligible successors/paths reduces to the reservation-only rule |
| Private path | Actual pending legal Private work can make Authority unnecessary for D, while C still requires certification |
| Conditional P | Same Verify-success Z is rendered under the correct current P/chunk; full eligible_chain succeeds/fails for the right reasons |
| Unknown Direct/Fallback | Unknown P is not labeled incompatible and does not create an unearned Verify preference |
| Failed Verify | Rejected candidate invokes real modeled fallback; failure cannot receive successful-compatibility credit |
| Snapshot purity | Shadow evaluation leaves Session, jobs/results, Canonical tokens and WAL bytes unchanged |
| Future authority | No child job is built/dispatched with a hypothetical next Parent; only the first currently legal action executes |
| Physical completion | Early row completion never releases a still-live Worker lease; all suffix/unselected work stays accounted |
| Receipt/install faults | Duplicate/stale/wrong-batch rows, mode mismatch, Fallback failure, partial group WAL and restart fail closed as before |
| Probability/numerics | Row CDF/scenario mass, inclusive deadlines, finite clocks, scalar-vs-optimized outputs and split action completeness pass |
| Model horizon | Same completed set with different P/Private state is never merged as equivalent without proof |
| Observable use | Decision logs identify which obligation/path/compatibility fact changed the actual action; dormant features are counted |

The counterexamples prove structural properties only. The GPU pilot must still
independently check every actual input/history, full verifier result, D1/WAL,
Consumer, physical cost and quality. Previous validation audio is diagnostic
development now; any later confirmatory claim requires an independent freeze.

## 8. Conditional safety argument and remaining empirical question

The safety argument can be conditional and simple: planner output selects a
currently permitted evidence computation; it neither installs nor certifies
state. The single owner rechecks actual Parent/Frontier/Contract, full trusted
Token/Stop evidence, D1 render and WAL for every result. Induction over
accepted transitions therefore preserves the original admission invariant,
regardless of prediction errors. This depends on the existing trusted-worker,
single-owner and storage assumptions. It does not establish liveness or an
SLO bound merely because the planner is safe.

The empirical question remains whether the complete closed-loop implementation
reduces observed eligible deferral and inherited Parent delay sufficiently to
improve Goodput/Commit tails at acceptable energy and quality. If only the
reservation or shared-cost part helps, retain that simpler effective
combination. If conditional compatibility has no opportunity or no net value,
report that directly. No part receives an innovation/performance claim solely
because it appears in the design.

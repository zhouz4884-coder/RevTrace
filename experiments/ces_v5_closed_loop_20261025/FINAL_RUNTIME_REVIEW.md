# Final independent runtime review

Date: 2026-10-25. Verdict: **GO for the already authorized bounded GPU
validation after source/config freezing. No remaining blocking issue was
identified in the reviewed integration.** This is a source and CPU verdict;
it is not a GPU performance result or a DSN contribution acceptance decision.

The review did not edit runtime implementation, start SSH/GPU work or modify
the paper. Root and the planner author repaired the issues reported below.

This is the renewed final-byte review. The earlier report remains unchanged
as `FINAL_RUNTIME_REVIEW_v1_91f827.md`, along with all earlier probe and JUnit
outputs. A previous PASS was not transferred to new hashes.

## Reviewed source identity

The isolated runtime is frozen at commit
`e45c66475ba1173a98b49b8c9e62f3e8cb45b333`, based on
`126dc815962e8f726b0cbdf214a19318b28a3629`. The clean frozen tree was checked
against the independently reviewed and tested bytes below. This verdict does
not transfer an older CPU gate to unreviewed hashes:

| File | SHA256 |
|---|---|
| `src/revtrace/ces_closed_loop.py` | `2226264d46153f7db269f83364810d17fbe169386f9b48e5ff5b0d9cb0dda66e` |
| `src/revtrace/ces_closed_loop_owner.py` | `450ac323118968e904589f202283802c054569e25c1fbc81fbb129c196a7d9b0` |
| `src/revtrace/ces_runtime.py` | `32a65f852a39ea0fc1d96337e79ebc4ba7539d5582eac270a0ceb0f229b6e166` |
| `scripts/run_tc_live_qwen.py` | `bce156e44e116fcf99fd4f56b5956f72d7f54432abe648037916d078884203e9` |

The original `live_qwen`, `dgft`, durable journal, trusted Display/render,
exact continuity predicate, full verifier, row executor and row worker show
no implementation diff from the isolated base. Their unchanged code remains
responsible for actual admission, complete evidence, WAL and Worker leases.

## 1. The formerly symbolic components now reach real dispatch

| Component | Actual online route verified |
|---|---|
| Current identity and service debt | Owner creates Session/epoch/Parent digest/frontier/contract identity; `_closed_choose` invokes the stateful planner at Authority availability |
| Persistent completion obligation | Only successful `worker.submit` is followed by `_closed_dispatched`; actual `commit` invokes `_closed_installed` and retires the matching debt |
| Released successor propagation | `_closed_build_contexts` enumerates up to two already released frontiers, weights/deadlines and paid cost estimates; these enter candidate construction and the scored continuation |
| Actual past credit | Only real committed intervals joined with already received legal Consumer ACKs enter cumulative credit; observing two paths never creates two credits for one atom |
| Current/future Private path | Only an actual unfinished, frozen Proposer job is forecast; completed cached or withdrawn nodes are not manufactured into a future publication |
| Conditional Verify-success root | A read-only Session shadow uses trusted render and the existing `eligible_chain`; the real state/job/WAL is untouched |
| Unknown Direct/Fallback branch | Separate calibrated root rates are used on the first transition; later unobserved Parent classes remain unknown rather than inheriting root success |
| GPU0 execution choice | Real prefix subbatches compete using a paid common current-Proposer cut; only the first real subbatch is issued |
| GPU0/GPU1 readiness interaction | Candidate-preparation value requires an actually occupied Authority lease and a target not already dispatched to Authority; idle GPU1 is not assigned a fictitious wait |
| CLI/provenance | Closed modes, explicit proposer policy, frozen PlannerConfig and calibration identity are part of the execution contract and source manifest |

The online choice still issues only a currently legal Job. Symbolic successor
features contain no future tokens or executable future Parent. The actual
next Job is rebuilt by the existing owner after real trusted admission.

## 2. Blocking errors found and repaired before the GPU freeze

### Direct/Fallback rate conflation

The earlier successor scalar set both Direct and Fallback preservation to the
Direct rate. With Direct=0.8, Fallback=0.1 and all Verify rows rejected, it
would predict 0.8 rather than 0.1. The interface now carries independent rates;
the production Owner leaves the legacy equal-rate fixture field null. The
first layer uses the current transition's appropriate rates, while depth two
has no fabricated known future-Parent class.

### A Private branch becoming unconditionally legal again at a later ancestor

The earlier model restarted its free-before-parent interval at every symbolic
layer. A pending Private result could therefore cross an incompatible first
root update yet receive unconditional credit merely because it completed
before a later parent update.

The read-only CPU probe retained this exact counterexample: root update 6.6,
next update 7.1, old Private completion 6.9, final Canonical completion 9.1 and
Display deadline 8.0. The model previously awarded two audio-seconds despite
the declared root preservation probability being zero. After repair it awards
zero. Every target keeps the declared release+2/release+8 deadline relation.

The model now integrates each Private completion time through every crossed
ancestor's row-completion distribution and conditional compatibility. The
first root's early-row CDF, not the latest physical envelope, determines when
free current legality can end. A currently illegal row that finishes before
root installation is not buffered and later republished by the model.

Independent additional checks confirm: a legal Private completion before the
first root still receives probability one; an unretained completion after it
receives zero; an exchangeable half-early/half-late root gives one-half; and
all-rejected Verify uses the 0.1 Fallback rate rather than 0.8 Direct rate.

These are CPU semantic repairs. They are not measured speedups.

## 3. Time, work and publication accounting

The pending-Private forecast uses observed Worker batch-start telemetry, not
enqueue age as GPU progress. When start has not been observed, age is zero and
the uncertainty is logged. Its conditional distribution includes modeled
delivery before conditioning on the unobserved application; an explicit flag
prevents the planner from adding that delivery again.

Supported row-CDF selection follows n/audio, n, then global with at least
eight row observations and eight physical batches. At most 32 weighted
upper-endpoint bins retain all probability mass and conservatively delay the
empirical CDF; the exact profile and distortion bound remain available.
Unknown/out-of-support rows receive an explicit fallback, not a clipped
negative completion time.

Authority early rows do not release their physical Worker. Every scored
continuation pays full physical leases, actual modeled fallback and delivery.
The new Proposer subset selector also includes the rest of the current ready
cut in its scored cost. The observed occupied Authority lease bounds a possible
candidate-readiness opportunity; it is not permission to preempt either GPU
or to treat a future candidate as ready.

Private preservation is conditional on the correct current branch edges and
publication path. The owner never promotes a symbolic score, CPU render or
compatibility estimate into a certificate. Already valid ready Authority
results continue through the original immediate commit path; service planning
does not hold a ready result merely to earn earlier provisional-view credit.

## 4. Service promises are not Commit-first or durability guarantees

The completion promise is a quantile of the previously selected suffix's
physical-outcome row-time envelope plus delivery. It is not the request's
Commit deadline and not an exact per-row P90 guarantee. Initial choices retain
the original Commit-first-loss counterexample: useful B-first is permitted.
Subsequent actual dispatches update a stable service identity; polling does
not age it, temporary absence does not erase it, and actual WAL installation
retires it. Broken promises and least-violation outcomes remain observable.

A new owner scope/epoch rebuilds performance state while the existing WAL
recovers Canonical history. No claim is made that the scheduling promise itself
survives a crash or that a finite deferral count provides an SLO guarantee.

## 5. Independent CPU validation performed on the reviewed integration

This reviewer ran:

`python -m pytest tests/test_ces_closed_loop.py tests/test_closed_loop_independent.py -q`

Final-byte result: **112 passed in 1.72 seconds**. This includes constructed mathematical
cases and actual owner/control-path tests with fake CPU workers, including
stale-parent rejection, ACK accounting, submit failure, WAL failure, partial
valid WAL prefix recovery, shadow purity and no cached-view resurrection.
It does not constitute a real GPU or process-SIGKILL recovery experiment.

JUnit: `FINAL_RUNTIME_REVIEW_TESTS_v3.xml`, SHA256
`9f25cf61c525f286d02a234ca46f98ef562476826601ba0da76ee1045a28c766`.

The reviewer also reran its own unchanged-input branch probe after the repairs:
`audit_closed_loop_counterexamples.py --expect-deep fixed`. Final result:
`FINAL_RUNTIME_BRANCH_PROBE_RELEASE.json`, SHA256
`3601fc6de35a3f84dc116af7c3cb95fa66ff6e35461a4428ff31c98c551a3cff`.
The earlier failing and intermediate outputs remain preserved.

The final review also explicitly checked the baseline-credit repair: Fine,
Standard and Cost now record the same actual commit observations needed to
join Consumer ACKs and compute past Q/T. Only CLOSED methods retire service
debt or emit closed-service events. The three added actual-owner CPU tests
exercise commits plus ACKs end to end, rather than assigning Q manually.
Their shared information no longer remains silently zero for a Cost control
that enables the same candidate-preparation capability.

The planner's 91f827-to-222626 byte change was independently isolated to the
`private_ancestor_survival_model` description string. Restoring that string
in memory reproduced the old SHA256 exactly. No runtime file was changed by
this check. Despite this being metadata-only, the current source was reread
and all 112 related tests and unchanged-input branch probes were rerun. The
Owner/runtime shared-credit change was reviewed as an actual behavior change.

A separate tests agent reports all 367 scoped tests passed on these same
final source hashes in `INDEPENDENT_CPU_GATE.json`. This review's own executed
count is 112; the two counts are not added or presented as independent samples.

## 6. Precise remaining model and execution limits

The implemented controller now has online successor contexts, actual service
debt, actual pending-Private forecasts and conditional branch evaluation. These
are no longer a disconnected symbolic module. The following claims still
require separate evidence or remain outside this implementation:

- The bounded beam, finite scenario quadrature and two-layer successor horizon
  do not establish a globally optimal GPU0/GPU1 plan.
- GPU0 remains a bounded sequential subbatch heuristic with an occupied-lease
  opportunity term; it is not a single exact joint optimizer for both GPUs.
- Row identity and several time/compatibility relationships remain empirical
  exchangeability/independence approximations. Unknown future Parent features
  are cost estimates, not generated model inputs.
- Historical root equality does not guarantee full-chain retention or future
  recognition quality. Runtime structural checks remain necessary.
- Current known-good past credit uses ACKs actually received by the owner;
  the independent final Consumer trace remains the metric authority.
- No new real GPU result, fairness/quality result, energy gain, passing SLO
  capacity point or complete real-history audit follows merely from this CPU
  review. Those are the next bounded experiment's purpose.

Fine, complete Standard, strong Cost-only and the reservation/inheritance
ablations must retain shared applicable executor capabilities and real costs.
If only simpler service protection helps, credit that useful combination.
The richer causal component needs its own observed opportunity and incremental
benefit before it receives a performance contribution claim.

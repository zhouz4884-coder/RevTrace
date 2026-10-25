# Independent CPU acceptance contract for closed-loop CES

This file is a CPU/code review record, not GPU performance evidence. The prior
48-cell GPU pilot remains frozen; its failure to pass the C2 upgrade gate is not
relabelled by this implementation work.

## Independent acceptance cases

1. Keep the exact release+2 s / release+8 s counterexample: a stale zero-display-
   credit task must not be promoted unconditionally ahead of a still-salvageable
   displayed-and-committed task merely because its commit deadline is earlier.
2. A target repeatedly placed in a scored suffix keeps an identity-bound
   service obligation across replans. Under the declared bounded CPU costs it
   cannot be replaced by fresh arrivals indefinitely. This is not a measured
   GPU deadline guarantee.
3. Already observed on-time Display retains pending Commit credit. Late
   Canonical publication cannot repair an expired first-Display deadline.
4. Released successors may change a predecessor's predicted scheduling value
   and deadline; unreleased audio must not enter the plan. A symbolic future
   Parent is not an executable Job, certificate, token sequence, or projection.
5. Direct Generation/Fallback has an unknown next Parent. Unknown must not be
   recoded as incompatible or used to invent a Verify-only preservation gain.
6. Session, Parent, epoch, frontier or execution-contract changes invalidate the
   old service reservation. Old promises never confer write permission.
7. Keep ready-candidate, paid Fallback, immutable receipt, duplicate detection,
   stale Parent, trusted render, partial WAL, restart and physical Worker-lease
   checks. Completion of one row or one GPU does not release another lease.
8. Both GPUs execute in wall time; their concurrent durations are not added as
   a fake critical path. Additional physical calls and residual work remain
   charged, and all targets remain in the scored common cut.

## Baseline regression before closed-loop edits

Command from `runtime/`:

```text
python -m pytest tests/test_ces.py tests/test_ces_v5_policy.py \
  tests/test_ces_v5_integration.py tests/test_row_executor_protocol.py \
  tests/test_row_lifecycle_transport.py tests/test_row_progress_integration.py \
  tests/test_durable_journal.py -q
```

Result: 116 tests passed, 2.07 seconds of pytest execution. These use fake CPU
workers, constructed tokens and clocks; no neural generation or GPU service was
performed by this reviewer. The same suite will be rerun after implementation.

## New pure-planner review

The independent file is `runtime/tests/test_closed_loop_independent.py`.
Its initial pure-planner implementation passed 18 cases but exposed eight
input-checking omissions (nonfinite clocks/weight/ETA, negative weight and a
nonfinite successor ETA). Source review also exposed a two-level forecast bug:
the root Verify compatibility was carried across an intervening symbolic
Generation, whose actual Parent is unknown. Both classes were repaired in the
new planner; the eight explicit invalid-input regressions and multi-level
unknown-Parent regression are retained. No historical runtime was changed.

After repair, 41 pure-planner cases pass. They include the real 2/8-second
Commit-first counterexample, an old target's bounded actual first-batch service,
identity-bound debt, non-aging polls, epoch/Parent/contract replacement,
currently missing eligible work retained until actual admission, and released
successor value changing the actual first Parent batch. Additional checks ensure
Private/Canonical paths use earliest Display without double-counted credit,
parallel GPU clocks use wall time rather than summed durations, and unknown
Direct Parent receives no invented Verify-only bonus. These are deterministic
CPU model results, not the counterfactual speedup of an old real GPU trace.

The temporary absence of a Session from the eligible list does not prove that
its work committed: its debt remains until the owner reports actual admission
or observes a replacement identity. A different Session never inherits that
debt. An explicit restart reset removes scheduling intent, not certified state.

The Private completion distribution is explicitly integrated at each deadline:
a constructed mixture with half the mass at 0.1 seconds and half at 3 seconds
earns half the potential 2-second Display credit, even though its mean is below
the deadline. A current Private path must have an actual legality witness before
that forecast can supply credit. Observed prefix Q/T is retained in the finite-
prefix ratio, and absent usable Private forecasts the causal score degenerates
to the inherited forecast.

Fairness review identified that `service_cost` puts cut wall time first, while
`inherit` puts finite-prefix credit (including successor credit) first. Their
comparison is not a single-factor successor ablation. The new
`reserved_progress` control addresses this: it shares finite-prefix planning
and service protection but omits successor reward/backpropagation and future
Private credit. Author tests verify the no-successor degeneration. Any GPU
claim of independent successor benefit must use this matched comparison, not
weaken Fine or Standard.

## Additional unchanged core safety regression

The following nine files pass 139 tests (0.92 seconds): `test_dgft.py`,
`test_online_admission.py`, `test_live_qwen.py`, `test_lazy_reconciliation.py`,
`test_certified_display.py`, `test_consumer_bound_identity.py`,
`test_continuity_proof.py`, `test_contract_manifest.py`, and
`test_terminal_recovery_contract.py`.

An exploratory wider selection found two pre-existing packaging dependencies:
`test_dual_lane_contract.py` imports absent `scripts.remote`, while a
`test_revguard_state_contract.py` report assertion requires absent
`runtime/docs/reports/revguard_state_contract_report.md`. These are not claimed
as passing or silently removed. They do not execute the new planner. The
bounded runtime snapshot and original frozen evidence remain unchanged.

## Integrated owner-level review

All four modes (`service_cost`, `reserved_progress`, `inherit`, `causal`) are
tested using actual owner code and fake CPU workers: Consumer ACK, D1, six
certified transitions, restart without duplicates, stale Parent rejection,
failed fsync without successful publication, and recovery from one complete
group transition plus a torn following frame. The latter is a CPU file-
truncation control, not a GPU SIGKILL or power-loss experiment.

Actual enqueue increments service dispatch once; a busy-worker poll does not.
Receipt arrival alone retains debt, and actual WAL installation retires it,
recording the actual installation time and whether the original promise was
late. A fake Worker rejection before issue does not increment dispatches or
deferrals. Shadow context construction leaves Sessions, frozen jobs, results
and WAL bytes unchanged while exposing only released symbolic successors.

One owner helper mismatch was found and repaired: an existing exact-chain
proof accepted a retained in-flight edge with an older immutable birth Parent
and audio root, while the new forecast helper erroneously required its audio
root to equal the newly advanced Canonical frontier. The test first failed,
then passed after allowing the older prefix while retaining the frozen causal
edge checks. Changing the actual pending input still rejects it. Completed
cached nodes are explicitly not counted as future publication opportunities.

The independent file now has 68 passing cases (41 pure-planner plus 27 actual-
owner/helper CPU cases). The combined 18-file core selection, including 13
author cases and 255 original cases, passes **336/336 in 3.67 seconds**.
Machine-readable record: `INDEPENDENT_CPU_REGRESSION_v3.xml`. The v1 record is
an invocation typo (nonexistent author-test filename; zero tests ran); v2 is
the earlier valid 325-test checkpoint and is not overwritten.

After the final Owner-only minor changes (per-child delivery in inherited
remaining service and read-only GPU0 rebase cost features), the same complete
selection passes **336/336 in 3.73 seconds**. Record:
`INDEPENDENT_CPU_REGRESSION_v4.xml`, using the dedicated
`cpu_tmp_independent_v4` pytest directory. Exact tested source hashes are in
`INDEPENDENT_CPU_GATE.json`.

The final trace-only Owner changes (complete context snapshots, exact actual
dispatch clock/token, and commit event preceding service retirement) were then
rerun independently: **336/336 in 3.64 seconds**. Final record:
`INDEPENDENT_CPU_REGRESSION_v5.xml`, dedicated `cpu_tmp_independent_v5`.
`INDEPENDENT_CPU_GATE.json` now identifies that exact tested source and retains
the prior valid v4 checkpoint.

### Final affected-implementation gate (v6; supersedes v5 for latest source)

The owner was subsequently strengthened in six specified areas, so the old
336-test result is not presented as coverage of the new code. Twenty-three
additional independent cases exercise the actual new helpers:

- exact supported n/audio -> n -> global backoff requires both eight rows and
  eight distinct physical batches; a neighbouring n is not silently called a
  same-shape profile;
- unknown Worker start uses age zero, observed start uses the actual received
  Worker clock rather than enqueue; a terminal component may remain in the
  distribution while its Consumer application is still unobserved;
- Consumer remaining-delay already includes delivery and the full causal score
  charges it once;
- 33/64/100/101/1000-point distributions retain all mass in at most 32 upper-
  endpoint bins; compressed CDF never exceeds the original CDF and the deficit
  is bounded by `(ceil(N/32)-1)/N`;
- first released successor receives distinct Direct and Fallback rates, while
  depth-two receives neither root rates nor root Verify compatibility;
- Fine/Standard/Cost/Service/Causal can all price and execute the same GPU0
  prefix capabilities, with complete paid remainder in every candidate cut;
  candidate value is zero with idle Authority or an already issued target,
  positive only behind an actual tracked Authority lease, and available to
  the applicable cost/service controls rather than exclusive to Causal.

The final explicit core selection passes **364/364 in 3.75 seconds**: 91
independent new cases, 18 author cases, and 255 unchanged core cases. Record:
`INDEPENDENT_CPU_REGRESSION_v6.xml`, dedicated `cpu_tmp_independent_v6_full`.
`INDEPENDENT_CPU_GATE.json` contains the exact latest planner/owner/runtime/test
hashes and preserves the prior v5 and v4 checkpoints. This is the current CPU
gate; previous counts remain historical checkpoints, not substitute evidence.

### Final shared-baseline data-path gate (v7; supersedes v6)

Root then identified an actual integration omission not caught by the earlier
manual-prefix-value fixtures: only closed-loop mode commits populated the
observed committed-credit ledger. Thus Cost could use the shared GPU0 planner
but its actual observed Q remained zero, suppressing the same candidate value
available to Causal. The repair records actual committed observations for every
CES mode, while retaining admission/debt retirement events only for modes that
actually use the closed-loop service book.

Three additional independent end-to-end tests now freeze `causal_joint` in the
CPU Owner contract before initialization for Fine, Standard and Cost. They run
real owner code with fake workers, produce six actual commits and Consumer
ACKs, independently reconstruct Q from those events, and require the shared
observed Q to equal that positive sum. They also require no fictitious
closed-loop-service dispatch/retirement events or service book state in those
baseline modes. This covers the actual data route rather than injecting Q.

The latest complete selection passes **367/367 in 3.97 seconds**: 94
independent tests, 18 author tests, 255 original core tests. Final current
record: `INDEPENDENT_CPU_REGRESSION_v7.xml`, dedicated
`cpu_tmp_independent_v7_full`. `INDEPENDENT_CPU_GATE.json` now binds the v7
exact source/test hashes and retains earlier checkpoints. Neither 336 nor 364
is presented as the latest implementation's final gate. The existing actual-
old48 profile arithmetic audit remains PASS and needs no inference rerun for
this Owner-only accounting repair.

CPU implementation/safety gate: GO for the next separately frozen bounded GPU
test, subject to final source identity and environment checks. Passing fixtures
does not establish end-to-end Goodput benefit, estimator calibration, future
model equivalence, an SLO bound, or a general optimality result. No GPU/SSH was
used by this independent reviewer.

## Independent audit of actual old-48 execution profiles

`audit_execution_profiles_independent.py` imports none of the fitter. It reads
the bounded CSV/JSON evidence, independently recomputes physical leases, row
fractions, batch/row/source denominators, generated-length summaries,
Jeffreys means, Wilson intervals, robust ridge coefficients and held-cell
errors. It also checks output/input-manifest hashes, two repeated profile
builds byte-for-byte, and that non-proposal Authority calibration is unchanged.

Result: `INDEPENDENT_PROFILE_AUDIT_v1.json` is PASS. There are 48 complete
historical cells: 44 protocol-complete plus four complete token-limit-boundary
cells. All four capped Proposer rows and zero capped Authority rows are
retained. The extraction includes 6,205 Proposer rows, 798 physical Proposer
batches, and 6,125 actual selected Direct/Fallback transitions. Of those,
389 have a pre-enqueue available same-frontier Private node and 5,736 have no
such node; no-node cases are correctly excluded rather than labelled failure.

| Actual selected class | Root equality | Prediction |
|---|---:|---:|
| Direct, same birth | 108/127 | 0.84765625 |
| Direct, mismatched birth | 214/235 | 0.9088983051 |
| Fallback, same birth | 0/6 | null (sparse) |
| Fallback, mismatched birth | 12/21 | 0.5681818182 |

This provides a concrete reason not to model unknown Direct output as
incompatible: equality is common in the actual observed node-available
selections. It is not a Direct-vs-Verify counterfactual, full-chain retention
probability, new inference, independent-source confirmation or SLO guarantee.
The 389 denominator must not be replaced by 6,125; the latter includes mostly
no-candidate opportunities. The same-birth Fallback estimate remains unknown,
not zero. The previous validation pool is explicitly training/diagnostic now.

The held-cell historical diagnostic has 198 physical batches in 12 cells,
median absolute error 0.1186275863 seconds and mean absolute error 0.2509876706
seconds. The acoustic sources are reused; this is not held-source validation.
Both profile builds produce identical six data/calibration files. Final
calibration SHA256:
`5ab06eabb4f295b59652c29c7ed1fa87121d623c3a0f6c78aad500ba7226a5fd`.

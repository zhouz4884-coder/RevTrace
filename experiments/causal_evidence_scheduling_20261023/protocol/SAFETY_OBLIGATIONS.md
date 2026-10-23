# CES evidence-choice refinement argument (conditional, not a new trust model)

Assume the original single Canonical Owner, correct trusted FP32 worker and D1
renderer, fixed manifests/audio/runtime/assets, successful WAL synchronization
and intact storage. FP32 denotes the pinned implementation; it is not a claim
of layout-invariant numerical outputs. The prediction table is not trusted.

For each Owner-ready transition t, CES selects either G or V under the same
Parent, newly covered interval, full waveform prefix and contract. G computes
fresh complete FP32 Z. V teacher-forces every candidate token in the *actual
current correct target input*, including the stop/budget condition, and either
returns a fully verified Z or pays a fresh complete FP32 generation. No prefix
or margin-only success is installed. A candidate's birth is predictive, not a
sufficient or necessary certificate. Missing/failed work cannot authorize t.

The sealed row receipt binds worker incarnation, batch, job, session, parent,
contract/epoch/runtime, interval and input identity including operation and
candidate identity. The owner validates operation, correct input evidence and
all original D1/admission predicates; duplicate/cross-bound results fail closed.
Only the original WAL/install path can advance the Canonical parent. Induction
over accepted WAL transitions therefore preserves the original invariants:
evidence selection changes how Z is obtained, not the accepted-state predicate.
WAL-replay preservation has the original storage assumptions. No unconditional
liveness or cross-layout equality is implied by this argument.

Private results retain their original causal-generation/version checks. A new
Canonical result can invalidate speculative work; CES predicts its possible
cost, but does not preserve incompatible text by concatenation. Complete rows
may be consumed early; the worker remains leased until the independent exact
BatchDrained receipt. All work, including fallback and obsolete work, is billed.

## CPU coverage and pilot obligations

- New tests exercise all declared policies through the actual owner and WAL
  restart, absent candidates, wrong evidence modes, wrong target/context/audio,
  bad token/stop/dtype, unpaid/failed fallback and stale parents.
- Inherited SDK tests exercise A/B/C/D/D1, private causality, partial/torn WAL,
  duplicate receipts, wrong batch/incarnation, row vs physical drain and safe
  positive-control behavior. The selected 21-module suite passes 235 tests.
- Full legacy test discovery is NOT claimed: unrelated historical finalizer
  scripts are intentionally absent from the frozen runtime subset; that failed
  collection is retained as cpu_tests_v1, not silently called a runtime pass.
- Real GPU pilot must validate actual processed-input/context receipts, full
  token/stop/repeated/legal-oracle checks, final trusted-render/WAL replay and
  physical lease accounting before formal parameters are frozen.
- Each altered actual batch/history is audited separately. There is no assumed
  shared Canonical output or automatic quality noninferiority between policies.

## Final scoped coverage and retained boundaries

Final executed sourcee0aeae1:243 local scoped tests and234 Linux scoped tests;
six additional external CPU interleaving tests exercise G-to-V owner switching
and wrong-operation completed results without changing frozen runtime code.
Four CES/Strict Linux process-kill fixtures plus three inherited partial-row
WAL fixtures pass. They remain CPU/synthetic-model evidence, not GPU recovery.
The original primitive/model assumptions, previous V0/V1 NO-GO and batch-input
realization limits remain. No universal equality between teacher-forced checks
and another physical greedy layout is claimed. Actual selected histories and
bounded same-input greedy/repeat oracle checks are audited independently.

The final Cost-only control has the SAME joint planner and deadlines without
causal rejection/preservation features. The rowwise causal control preserves the
same one-target score and wait rule. This comparison may establish an empirical
increment, not a proof that conventional primitives cannot express the policy.

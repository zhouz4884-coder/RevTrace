# Dispatch-freeze audit and development implementation

Read the complete active goal and current root AGENTS. This work inspected the
frozen LP1 source and existing V6 evidence only. No GPU, remote mutation, paper
edit, branch change, or live runtime edit was performed.

## Existing evidence

- V6 `C_ANALYSIS_FREEZE.md` froze 18 fresh-process cells, clean/Mixed, hold
  0/.75/1.5 seconds and three repeats. C randomized the installation time of the
  window-5 Authority result, not the next Private dispatch.
- `C_ACTIONABILITY_DECISION.md`: Mixed 1.5-vs-0 has 48/48 exact Authority target
  matches and GPU0 paid-lease increases 6.289/6.265/5.839 seconds. The three caps
  are repeated observations of one old source. Independent D 36 cells have zero
  caps. The immediate Verify/Generate causal-risk upgrade remains NO-GO.
- `C_witness_final/C_CRITICAL_SOURCE_CLOCKS.csv`: old-source Private6 freezes
  before delayed Authority5 installation; P changes, 10 becomes 256 tokens and
  the shared batch lease becomes about14.2s. Clean delayed arms have old version
  but the SAME P and 10 tokens. Version delay alone is not sufficient.
- Read-only recomputation from all98 raw `events.jsonl`/`worker_records.jsonl`:
  12,283 Private jobs,2,236 with a pending earlier-frontier Authority;212 logical
  P differences against eventual Authority P. Only12 of13 total caps overlap
  this pending-predecessor cut. These are actual-dispatch denominators, not all
  offered windows or independent samples.
- D heldout36:4,643 Private jobs,878 predecessor-pending,64 logicalP differences,
  zero caps;486 pending predecessors install within.5s,663 within.75s. These are
  ex-post clocks and logical comparisons, not online estimates, realized-input
  equality tests, saved-work claims, or a performance GO.

## Source insertion and immutable boundary

Actual source: `.execution/lp1_runtime/runtime/src/revtrace/live_qwen.py`.

- `_ready_time`249: original absolute audio release; envelope overrides it with
  `origin + offset + end`, retaining original clocks across restart.
- `_make_job`273: checks release;285–296 performs eligible Canonical rebase;
  subsequent lines freeze P,parent,chunk/frontier,epoch/contracts/audio hashes;
  enqueue event occurs before return. Waiting belongs before this call.
- `_ready`340: reconciles covered windows as a side effect. `_dispatch`398 calls
  it repeatedly. Do not put renewing timer creation inside `_ready`.
- `_dispatch`407–410: obtain effective ready sessions, filter timing permission,
  then create immutable jobs only for released sessions. Keep available other
  sessions in the batch. Authority lane must remain unchanged.
- `_receive`421: Row-complete may deliver logical rows while inflight lease
  persists until batch-drained. Waiting never cancels or frees such a lease.
- `certified_envelope.py`230 onward: actual inherited ready gate retires expired
  accepted Private targets, admits only durably accepted audio and preserves
  all offered-window accounting. The filter must run after this effective gate.
- `kernel_runtime.py`96–103: `protocol_dispatch` binds actual immutable job.
  `composed_kernel.py`dispatch checks parent equals current Canonical version.
  A matched-delay old-parent counterfactual cannot bypass this; if invalid,
  execute it only as a labelled paid operator diagnostic outside legal service.
- `row_delivery_executor.py`42–56 exposes observed execution_phase and row
  delivery; batch-drained alone returns physical worker to idle.
- `current_prefix_worker.py`6 and `prefix_continuation.py`48 enforce batch1.
  Main mixed-batch study should use complete row backend for EVERY arm.

## Six fair policies

Every arm uses identical service estimates, original D2/C8 and max wait budget.
The candidate controller never changes Canonical predicates.

1. Immediate: original ordering, zero deferral.
2. Fixed: development-selected fixed maximum delay, clipped to original slack;
   default condition is relevant pending Authority. All-ready fixed is also
   implemented for identical-budget development tuning. Early release on a
   Canonical transition is shared ordinary behavior.
3. Pending ETA: waits for a current-parent Authority when its past-calibrated
   residual fits the same budget. This is the strongest direct simple baseline.
4. Backpressure: waits when current Private lead exceeds a frozen threshold and
   an Authority lease exists; no lineage-content feature.
5. Recent feedback: adapts finite delay using previously observed useful
   refresh/covered-target outcomes. This is a disclosed proxy, not an observed
   counterfactual compute saving.
6. State aware: same ETA model plus currently known pending-predecessor target,
   Private depth and Private-vs-Canonical P difference. These predict timing
   utility only. If this matches ordinary pending waiting, report equivalence.

For any initial decision time t, original release r, default/past Private cost
cP and frozen maximum B, full_service maximum delay is max(0,min(B,r+D-t-cP)).
Shared development alternative raw_slack uses max(0,min(B,r+D-t)); it bounds
waiting by D2 but DOES NOT promise subsequent output is on time. Both options
are exposed identically for every baseline, never selected on heldout results.
The unconditional old-cost reserve can suppress the very input-changing
opportunity under investigation; retain both as a declared falsifiable contrast.
Persist that
absolute bound keyed by(session,window). It never moves when replanning or when
the Parent changes. On Parent change, expiry, coverage or cursor retirement,
release/close the record and let the ordinary live state decide the next job.

Development defaults are provisional (.75s maximum,.25s fixed,1.7s fallback
Authority receipt ETA,.5s fallback Private receipt ETA), not a calibrated result.
Calibrate on development data then freeze; heldout data must not tune them.

## Tests and integration caveats

TEMP files `dispatch_wait.py` and `test_dispatch_wait.py` implement/test this API.
40 CPU tests pass. They cover finite bounds, original deadlines, no job mutation,
other-session progress, epoch/parent/contract filtering, forbidden feature
access, conditional-state information, late ETA, target retirement and observed
history. These are component fixtures; integration tests against the real
scheduler/kernel and GPU pilots remain necessary.

Call observe_event for actual `batch-dispatched` and `executor-complete` events.
The latter receipt-minus-enqueue is only a delivery-cost predictor; separate
physical batch/energy ledgers remain authoritative. All arms must enable the
same telemetry. Place filtering over effective ready sessions before slicing a
batch if blocked early sessions must not head-of-line block other sessions.
Such waiting intervals can overlap ordinary queue delay and must not be summed
as exclusive GPU idle time. Record actual GPU0 occupancy separately.

One-shot decisions are made the first time a target enters the filter; an
unselected queued target does not silently receive a fresh budget later. Preserve
this rule in all baselines or explicitly change the frozen decision contract.

Opportunity decomposition must report input changed/unchanged, target covered
without issuance, target retired at original deadline, batch membership/padding
change, physical waiting, row completion, total paid lease and actual Consumer
coverage. Token-count reduction alone cannot establish net service benefit.

## Reproducible raw census and initial cost bank

Private-dispatch opportunity accounting is reproducible with the TEMP
`audit_private_dispatch_opportunities.py`; its result is
`PRIVATE_DISPATCH_OPPORTUNITIES.json`, including196 raw file hashes.

Development calibration is reproducible with
`calibrate_dispatch_receipts.py`; result `DEVELOPMENT_RECEIPT_CALIBRATION.json`
uses A24 + C hold_0 clean/Mixed6 only. D and C artificial-hold arms excluded.
Authority generate and verify are stratified separately; only independent
generate is eligible for current runtime initialization. Each stratum includes
all-row p50/p90/max and up to64 actual identity-hash-selected bootstrap samples.
Batch16 independent Authority:1,456rows/91batches, p90=1.94705s.
Batch16 Proposal:1,536rows/96batches, p90=1.53325s.
Batch4 independent Authority:104rows/26batches,p90=.99258s;
Proposal64rows/16batches,p90=.97841s. These predict receipt costs, not paid-lease
savings. Histories remain dependent and bootstraps are not independent tasks.

Confirm C is rho1,fine2s,batch16,Qwen3-ASR1.7B,FP16Proposal/FP32Authority,
decoupled and group-ready WAL. Start with a complete-row c4 legality pilot,
then matched c16 using the original complete16-source manifest; do not select
sources based on caps or outputs. Public hashes/metadata remain distinct from
actual newly frozen source and runtime environment validation.

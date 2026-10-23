# Independent V5 implementation and pilot review

Review date: 2026-10-23. This is a source/CPU review until a named GPU audit is
attached. Reading historical logs and generating predictions creates no new
GPU serving evidence.

## Judgment and experiment scope

Proceed to the bounded pilot after the CPU and integration gates pass. The V4
failure supports changing the objective and its cost inputs; it does not
establish that either change will improve serving. A simple composition that
improves real Goodput/cost is a useful outcome even if a more elaborate planner
has no additional value.

Root freezes 48 serving cells: eight arms (Fine, Standard, old joint Cost-only,
shared Risk-cost, Progress, Progress+GPU0 ordering, Fine+the same GPU0 ordering,
Standard+the same GPU0 ordering), two arrival schedules, three fresh-process
paired repeats, on the reused old validation16 diagnostic pool under Mixed F2.
Two four-session Strict oracle diagnostics are separate paid correctness cells;
their extra model work cannot be included as ordinary deployment performance.

The extra Fine/Standard ordering arms are necessary to attribute a joint-arm
benefit. Shared Consumer ACK instrumentation and physical row completion are
available to every arm. All arms receive the same frozen calibration file;
the old Cost-only arm intentionally ignores the new risk fields and remains
the historical-method control. Risk-cost is the decisive shared-model control
for any additional progress-aware benefit.

The old validation sources have already informed the V5 design. These runs
are diagnostic, not a new independent confirmation. Further confirmatory work
must freeze a new source pool before observing its outcomes.

## Source findings

1. Consumer ACKs are frozen records emitted only after a legal view has been
   applied. They contain run, contract, epoch, session, version, frontier and
   actual observation time. They provide scheduling telemetry, never a
   certificate or state-write permission.
2. The owner checks identity and observation time before recording first legal
   visibility. A later retraction does not erase this historical metric. The
   independent audit also measures uninterrupted visibility until certified
   application, so changing commit timing cannot silently be sold as stable
   display improvement.
3. V5 does not await a not-yet-ready candidate. Verify and Generate remain
   homogeneous operations, paid fallback remains real FP32 computation, and
   row completion does not release the physical Worker lease.
4. Existing Parent/Frontier/Contract, D1 render, admission and WAL checks are
   reused. The owner immediately processes ready authority results through
   `_commit_ready`; scheduling must never delay that path to acquire display
   credit.
5. `progress_joint` changes the next legal proposer dispatch order at an idle
   Worker boundary. It does not preempt already issued work. Same-order Fine
   and Standard controls are included in the pilot.
6. Batch scenarios model the empirical failed-row count jointly. Current row
   failure identity is exchangeable within a size bucket; birth/rejection
   features help enumerate candidate partitions but do not constitute a
   calibrated per-state conditional failure distribution. Claims must retain
   this distinction.
7. The score is a bounded common-cut heuristic over current pending targets.
   It does not solve the full future queue or prove an optimal policy. Zero
   residual display credit must still leave overdue predecessors eligible for
   execution; every common-cut plan includes them.

## Integration issue found before GPU execution

Initial `calibration_v1` stored every observed scenario in each bucket, while
the policy rejected buckets with more than eight representative scenarios.
This would have failed at the first V5 decision. Root was notified before any
pilot launch. The corrected frozen calibration must retain raw COST_ROWS,
original support counts, representative weights and tail/failed-count support.
Taking the first eight rows would be an invalid repair.

The initial 90% coverage report was for a ratio predictor, not the complete
scenario predictor used by the scheduler. It cannot establish 90% coverage of
that final predictor. A final-model held-cell check is required and remains a
historical calibration diagnostic, not an SLO guarantee or speed result.

## Independent audit deliverables

`audit_v5.py` takes explicit results/source/model/reference/expected-cell paths.
It retains the original certificate/WAL/D1/complete verification, candidate
origin, receipt digest, physical lease and actual Consumer replay checks. It
adds exact reconstruction of accepted Consumer ACKs and `display_met` /
`display_expired` features at each V5 decision.

Every expected cell appears as passed, failed or missing. A failed cell does
not disappear through success-only directory iteration. No aggregate
superiority claim is eligible when requested cells are missing or failed.

The audit emits first-legal dual-deadline Goodput, the certified-Consumer commit
clock sensitivity, and uninterrupted-visible-until-certified Goodput. It also
retains retraction counts, withdrawn audio, actual two-GPU serve-window energy,
model calls, physical batch occupancy, fallback, fsync, final WER/CER and all
requested audio frontiers. Owner install and Consumer application remain
separate clocks.

`summarize_v5.py` reports repeat-paired effects and source-cluster sensitivity
conditional on observed schedules. Individual audio frontiers are not treated
as independent runs. Group medians and medians of paired changes remain
distinct. Three-run pilot intervals are descriptive and do not replace an
independent formal study.

Five CPU accounting fixtures pass: withdrawal vs first-visible credit, pending
Commit value after early display, unfinished denominators, full-reference
quality counts and paired-run effect construction. These tests are synthetic
accounting checks, not new model results.

## Decision discipline

- If Risk-cost wins and Progress does not, retain the simpler useful integration.
- If only proposer ordering wins, credit the ordering mechanism and shared
  executor rather than an evidence-selection improvement.
- If first-legal Goodput improves but uninterrupted coverage worsens, report
  both and diagnose commit/withdrawal timing before claiming a display benefit.
- If all methods miss whole-run dual P99, report local Goodput effects without
  claiming a passing capacity point.
- If an arm changes actual batch shape or Canonical history, independently
  audit its input, render and quality. Equivalent WER is not token identity.
- No actual V5 performance claim is supported until real requested cells and
  their independent audit complete.

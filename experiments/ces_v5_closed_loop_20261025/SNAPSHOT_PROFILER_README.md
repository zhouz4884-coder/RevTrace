# Bounded frozen-snapshot CPU profiler

Prepared for post-run diagnosis, not executed on the current remote serving
matrix. It imports only the frozen pure planning modules and the v2 context
restorer. No neural model, GPU, SSH, live controller, or runtime edit occurs.

```text
python profile_closed_snapshots.py --root RESULTS_ROOT --stage formal --source FROZEN_RUNTIME --plan PLAN.smoke.json --source-manifest SOURCE_MANIFEST.json --output RESULTS_ROOT/formal_cpu_snapshot_profile_v1
```

The script refuses to run until the exact requested stage is complete and its
original safety audit reports PASS. All frozen source-manifest bytes must match.
It refuses an existing output directory. Pass `--audit-dir` if the matching
completed audit is stored under a versioned name.

## Frozen sampling rule

- One declared `r0`, Mixed, staggered cell for each of `service_cost`,
  `reserved_progress`, `inherit`, `causal` (four cells maximum).
- At most five decisions per cell, ranked by **recorded actual Authority host
  planner wall**, ties by original event index. This selects overhead hotspots,
  not favourable performance outcomes; it cannot estimate average run overhead.
- `--arrival sync` changes the predetermined arrival class for all four cells,
  not independently per method. `--max-decisions` can reduce but never exceed 5.

## Exact replay and chronology

The state book is rebuilt through all actual observation, enqueue/dispatch,
Consumer ACK and durable-install events, even between unprofiled decisions.
Actual Parent/contract/frontier bindings, observed earned audio and each logged
book snapshot are checked. Unselected original choices update the book as
recorded; they are not re-optimized into a different history.

For selected decisions the complete pure `choose_closed_loop` result must equal
every recorded planner field, including operation, selected Sessions, score,
plans, promises and forecast fields. A separate `cProfile` call starts from
another deep copy of the same state and must yield exactly the same result.
Failure means no timing conclusion, not an opportunity to substitute a nearby
decision. The original certificate/WAL/D1/full-context safety audit remains a
prerequisite; this profiler is not a replacement safety audit.

## Outputs and interpretation

`SNAPSHOT_REPLAY.csv` records exact-match status, actual Owner planner time,
ordinary replay time, instrumented replay time, target/successor/CDF counts and
enumerated plans. `HOTSPOTS.csv` lists the 50 largest cumulative hotspots per
selected decision; cumulative values overlap and must not be added. `.prof`
files support later local inspection; selected immutable JSON snapshots and
input/source/script hashes allow replication.

The original Owner timer includes context construction and observation logging;
the replay covers **only the pure planning function**. `cProfile` adds overhead.
Ordinary replay precedes the profiled call, so shared function caches may already
be warm; hardware, Python and concurrent host activity can also differ. Neither
timing is a measured replacement for the original Owner interval.

This tool does not switch modes or synthesize a future model history. It can
identify implementation hotspots worth testing for semantic equivalence. It
cannot establish that removing host cost will improve GPU Goodput, that a
different action would be better, or that the algorithm's cost model is correct.
Such conclusions require separate measured controls.

Local tests use deliberately constructed CPU events. They cover deterministic
top-wall selection, reconstruction across an unprofiled middle decision,
fail-closed score mismatch and rejection of a corrupted service-book snapshot.

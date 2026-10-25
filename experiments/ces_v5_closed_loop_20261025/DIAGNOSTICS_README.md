# Independent closed-loop observed-history diagnostics

This is analysis of the frozen experiment, not a runtime patch. It makes no GPU,
SSH, model, or scheduler calls. The accompanying unit tests use explicitly
constructed CPU event histories; their pass count is not serving evidence.

## Invocation

Run after the formal controller and original safety audit finish, using a new
output directory. The root may be a remote experiment filesystem or a full local
mirror with the same `root/stage/cell` layout; a flattened bounded archive is not
silently interpreted as the complete raw dataset.

```text
python analyze_closed_diagnostics.py --root RESULTS_ROOT --stage formal --plan PLAN.smoke.json --output RESULTS_ROOT/formal_independent_diagnostics_v1
```

For the re-audited smoke records, also pass
`--audit-dir RESULTS_ROOT/smoke_audit_v2`. Existing output directories are refused
to preserve previous analyses. The script does not write into a raw cell.

## Independent recomputation

- Requested frontiers come from the frozen session durations, including final
  partial windows. Audio weights and the denominator retain all requests.
- Display is the actual Consumer's first legal coverage; Commit is the actual
  durable installation. Stable-display/actual-certified-Consumer sensitivity is
  reported separately, including intervening withdrawals.
- Full serving wall includes arrival, drain, and actual Consumer observations.
  All completed physical Proposer and Authority leases/model phases are paid,
  including fallback and obsolete work. A row terminal is not a worker release.
- Energy integrates both sampled GPUs over that same wall. Less than 99.5%
  coverage yields no comparable energy metric; observed partial energy remains
  available without filling the missing interval with zero.
- Each Authority critical path is independently recomposed as release → legal
  Parent → enqueue → Worker start → row terminal → trusted render → emission →
  Owner receive → durable install. Its components must sum to measured latency.
- `TARGET_DEFERRALS.csv` groups actual repeated eligible observations by stable
  session/epoch/Parent/frontier identity and checks their eventual real Job.
  Fine/Standard omit target feature snapshots, so their absent deferral counts
  are **missing**, not zero.
- Service-promise retirement is reconciled with actual installation, including
  expired promises and breaches. Repeated cumulative book snapshots are not
  summed as independent debts.

## Host planning versus GPU work

`DECISION_ACTIVATION.csv` retains the measured Authority planner wall and base
feature wall, actual snapshot-to-first-enqueue delay, and the residual. These
are elapsed host intervals, not CPU-thread active time or separately metered
host energy. Context construction and observation logging are inside the
frozen Authority planner timer.

`CRITICAL_PATHS.csv` separately intersects eligible-to-enqueue waiting with
actual occupied GPU1 leases and with observed Authority scheduling intervals.
The intersections use interval unions. They may overlap each other and must not
be added as mutually exclusive causes. Summing per-target waiting is likewise
not exclusive GPU work or a reclaimable speedup.

The frozen runtime has no standalone GPU0-selector CPU timer. Its overhead is
paid in actual whole-run wall; this tool explicitly reports that finer timing as
unmeasured. Any later exact frozen-snapshot CPU replay/cProfile is a host-hotspot
or action-sensitivity study, **not a GPU performance counterfactual**.

## Prediction and activation limits

- Inherited deadlines, released successors, selected inherited targets,
  positive Private forecasts, and forced-service choices are separate counts.
  Activation does not show that a feature caused an improvement.
- Forecast cut credit is compared with the eventual *actual* history. The
  suffix was replanned and is not a counterfactual execution of the forecast.
- Pending-Private delivery CDF versus actual same-job Consumer publication is
  recorded separately. The CDF alone is not the probability of legal retention
  through future Parents. Repeated forecasts are correlated observations.
- WER/CER are retained from the separately audited final-reference counts in
  `SERVICE_CELLS.csv`, with its input hash. This timing script does not claim to
  rerun recognition or independently regenerate reference tokens.

## Comparisons and gates

The paired output includes `causal_joint` versus `cost_joint`, and both
`fine_shared_progress` and `standard_shared_progress`, alongside Fine,
Standard, Strict, cost, service-cost, reserved-progress, inherit and causal.
Group medians and paired run-level relative changes are different fields.
Three-run bootstrap intervals are descriptive; the 135 repeated frontiers are
not 405 IID samples. Reused validation audio is a diagnostic/training pool,
not fresh confirmatory evidence.

The 72-cell plan has no same-new-model no-service-guard arm. Historical 48-cell
failures can motivate this design but cannot isolate its guard effect alone.
Shared executor or shared GPU0 progress benefits are not attributed exclusively
to the causal planner.

Any absent, incomplete, capped, unplanned or failed-audit run is retained in the
requested-cell inventory. A complete cap-hit run is retained as a measured
quality boundary. Incomplete runs retain declared audio/frontiers and recorded
completed lease lower bounds; unknown unfinished work is never zero-filled.
No complete-matrix comparative claim is enabled without all requested records
and the exact original safety-audit PASS status.

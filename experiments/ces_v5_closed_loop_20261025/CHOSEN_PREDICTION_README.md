# Actual selected first-batch prediction diagnosis

```text
python diagnose_closed_prediction.py --root RESULTS_ROOT --stage formal --source FROZEN_RUNTIME --plan PLAN.smoke.json --source-manifest SOURCE_MANIFEST.json --output RESULTS_ROOT/formal_chosen_prediction_v1
```

Only run after all requested cells and the original safety audit pass. Inputs
and the frozen runtime manifest are hash-checked; raw results and runtime are
read-only. Failed diagnostic cells remain listed, not silently dropped.

The decision's `planned_seconds`/common-cut costs include later physical batches
and, in some modes, successor obligations. They are retained as metadata but
are **not compared to the selected first batch**. This tool calls the frozen
`predict_batch` using precisely the first actual operation and selected target
features, joining chronological real enqueue and Batch-dispatched events to
the complete accounting record by actual Job IDs.

Fine/Standard do not log target features. Their selected **direct generation**
can be diagnosed using the known dispatched audio prefix, interval and prompt
length. This is not a claim that those policies used a predictor online. The
same frozen risk predictor is used for every method; cost/Strict may originally
have chosen with other rules. No unselected Verify/Generate outcome is filled.

Clock definitions follow the historical calibration labels:

- Lease prediction: Worker start to **Batch-drained**, including preprocessing,
  complete calls, postprocessing and drain overhead.
- Row CDF prediction: Worker start to **`completed_perf` (trusted render
  complete)**, not merely terminal EOS. Terminal, render, emission, Owner
  receipt, durable installation and actual certified Consumer are distinct.
- Model-phase wall is reported separately from the complete lease. Neither is
  GPU kernel-active time; no kernel profiler was run.
- Actual Fallback K and actually executed fallback rows/calls are both retained;
  a full-layout fallback can pay for more rows than the rejected count.

Outputs include mean/P90 first-lease calibration, the entire frozen predicted
scenario distribution, exchangeable row-CDF residuals and Owner-delivery
allowance coverage. Row outcomes are correlated within real physical batches;
coverage is selected-action calibration, not per-row IID evidence or same-batch
counterfactual comparison across policies.

Snapshot-to-enqueue delay explicitly consumes Display/Commit deadline slack.
The tool separately records snapshot-anchored and actual-worker-start-anchored
deadline probabilities to distinguish pre-dispatch delay from service-model
error. It does not subtract total planner wall from the run and claim that as
a recoverable Goodput benefit. All costs in the original end-to-end run remain.

Unit tests use artificial CPU event/cost fixtures only. They check common-cut
versus first-lease separation, rendered versus terminal row clocks, fallback
cost retention, CDF mass and exact dispatch identity matching.

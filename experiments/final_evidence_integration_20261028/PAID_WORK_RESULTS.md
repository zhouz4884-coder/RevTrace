# Real paid-work and latency decomposition

Population: all six terminal repaired v10 c16 staggered development runs,
fine2s/rho1, FP16 Proposer/GPU0 and FP32 Authority/GPU1, same full row-complete,
kernel/D1, WAL, input obligations and actual Consumer. One repeat per policy.
This analysis adds no model invocation. Exact decimals, batch histograms, input
identities and 810 frontier paths are in `records_v2/cost_v2/RESULT.json`.

## Physical costs (seconds, complete runs)

Paid lease is the interval from trusted kernel dispatch receipt to trusted
Batch-drained receipt, not early row completion. Model wall is synchronized
real model-call wall, not a CUDA utilization counter. A batch's lease is
partitioned into owner→worker, worker preprocessing, model, between-call gap,
worker postprocessing and owner-after-drain overhead; their sums match exactly.

|Policy|P rows / batches|GPU0 paid lease|GPU0 model wall|GPU1 paid lease / 15 batches|GPU1 model wall|Goodput D2/C8|
|---|---:|---:|---:|---:|---:|---:|
|Immediate|102 /14|22.677|20.692|25.820|22.836|2.0032|
|Fixed|67 /17|21.926|20.854|25.892|22.772|1.8481|
|Pending ETA|97 /14|23.360|21.828|26.017|23.185|1.6175|
|Backpressure|80 /16|22.111|20.916|25.948|22.919|1.4847|
|Recent gain|111 /15|23.060|21.473|25.835|22.979|1.8329|
|State aware|114 /15|22.259|20.623|25.925|22.969|2.0711|

All 181 physical batches are charged, all 810 Authority rows committed, all
six selected histories/14-of-687 WER errors match. Every whole-run D2/C8 check
fails. GPU0/GPU1 leases overlap in wall time: do not sum them into run duration.
Individual latency percentiles are not sums of component percentiles.

## Nonuse is not reclaimed computation

|Policy|Obsolete P rows already paid|Entirely obsolete batches|Mixed-obsolete batch paid lease|Covered without issuing|Expired without issuing|
|---|---:|---:|---:|---:|---:|
|Immediate|18|0|5.140s|0|33|
|Fixed|0|0|0|7|61|
|Pending ETA|4|0|1.942s|0|38|
|Backpressure|8|0|3.283s|0|55|
|Recent gain|22|0|5.198s|0|24|
|State aware|20|0|5.093s|0|21|

Mixed-obsolete time is the paid time of a batch containing both used and unused
rows, **not** an avoidable cost attribution to those rows. All-batch categories
are disjoint. Covered-unissued and expired-unissued identities are disjoint.
No result retirement is called physical GPU cancellation.

## What the decomposition explains

Fixed waiting executes 35 fewer P rows than immediate, but uses 17 rather than
14 physical batches; synchronized model wall rises 20.692→20.854s. Its seven
covered-unissued windows do not establish that those seven windows account for
the entire row difference: 61 rather than 33 windows expire without execution.
Task counts and token counts alone therefore overstate useful cost savings.

All six Authority paths spend approximately 22.77–23.19s in model calls and
25.82–26.02s in receipt-bound leases. They cannot be made cheap by retiring a
Private output. For Immediate, median precondition wait is1.762s, owner queue
0.334s, worker-to-host-row2.054s, install0.051s and actual Consumer delay0.014s.
These are marginal medians, not an additive median critical path. Per-row
nonoverlapping component paths are available in the CSV and each sums to its
actual end-to-end latency. The busy-queue part uses interval union, so a busy
worker is not double-counted as multiple independent delays.

Free-run comparisons also record P, root, processed-row, batch tensor and Z
differences. They are joint observations affected by grouping and execution
timing; they are not causal shares. The separately paid old/new fixed-layout
operators in the context package provide the actual input-intervention evidence:
one input change increases work, the other reduces work, both without cap.

State aware's slightly higher point Goodput is not attributable to waiting:
the independent action audit found zero actual waits. This decomposition
supports the existing NO-GO for a larger state-aware algorithm matrix, not a
theorem that every future feedback-sensitive controller must fail.

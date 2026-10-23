# RevTrace — Causal Evidence Scheduling (CES), bounded study

Status: **research complete; current CES v4 is NO-GO for an independent new C2
algorithm claim**. The protected implementation works, but it does not establish
repeatable net benefit over all strong cost/readiness/rowwise controls on the
independent Mixed workload. Negative results are retained, not tuned away.

Read `reports/RESEARCH_REPORT.zh.md` and `reports/CONTRIBUTION_EVIDENCE_MATRIX.csv`.
Detailed formal tables and paired intervals are under
`evidence/evidence/FORMAL_RESULTS_v1/`. Group-column medians are not paired effects.

## Implementation and fixed contracts

Baseline GitHub23ba88c; verified Row SDK2bc71af; executed sourcee0aeae1.
`runtime/` is the exact executable source; `source_bundles/CES_EXECUTED_v4.bundle`
preserves the complete executed prototype history. Current files are byte-equal
to Git blobs and the source manifest;168 unique reachable blobs were scanned.

The Owner chooses either complete FP32 correct-context token/stop/budget
verification with actual full FP32 fallback, or independent FP32 generation.
The proposer never receives Canonical write permission. Original A/B/C/D, D1,
Parent/Frontier/Contract, WAL, private causality and physical lease checks remain.
No Elastic rho, grafting, V2/coarse substitution, KV-reuse fallback, or new model.

Full CES uses a bounded ranked-prefix/batch-order plan with empirical costs,
candidate readiness/birth, observed rejection, deadlines and issued private
work. Predictions cannot change admission. Joint Cost-only has the SAME planner
without causal features. Rowwise causal has the SAME one-target score without
cross-request optimization. Readiness-only and a simple cost gate are retained.
Fine and Standard do not pay unused predictor loops; all share row capability.

## Actual scope

33 real dual-RTX3090 pilot cells and180 formal fresh-process cells;9 methods,
2 pools of16 sources, synchronous/staggered arrivals, Clean/Mixed/High. Mixed
has3 repetitions; Clean/High1 each are descriptive. All fine2s/rho1, FP16 GPU0,
FP32 GPU1,256-token budget, same WAL and local two-lane Consumer.

All180 formal cells passed admission/WAL/D1/receipt/lease/Consumer audit.
All7,002 physical worker batches and53,005 row-input observations were CPU
restaged/repeated exactly. This is preprocessing evidence, not an additional
neural oracle or cross-layout GPU equivalence proof. Actual bounded greedy/
repeat GPU oracles are distinguished from regular serving measurements.

## Reproduction

Use the frozen environment/provenance and original model/audio manifests; model
weights/audio are not redistributed. Runtime expects Python/PyTorch/CUDA and
Qwen3-ASR assets pinned in the evidence. Example cell:

```sh
python runtime/scripts/run_tc_live_qwen.py \
  --model /path/to/Qwen3-ASR-1.7B --manifest /path/to/manifest.json \
  --output /unique/new/cell --code-commit e0aeae1b418644c378dde331c59b55fc5948b40f \
  --sessions 16 --arrival sync --ces-method ces --ces-traffic mixed \
  --ces-calibration /path/to/calibration_v5/CALIBRATION.json \
  --online-donors /path/to/DONORS.json --online-fallback-layout selective \
  --trusted-text-binding --capture-model-inputs --phase-n-instrumentation \
  --display-protocol canonical-snapshot-v1 --publish-canonical-display \
  --consumer-policy two_lane --retain-verified-private-prefix \
  --result-delivery row --durable-journal-path /unique/new/state.wal \
  --journal-sync-mode group_ready
```

CPU tests require `PYTHONPATH=runtime/src:runtime/scripts:runtime/tests` on Linux;
run the scoped lists in research/cpu_tests.py, not unrelated legacy finalizer
tests whose historical scripts are outside this runtime subset. Explicit CPU
fixture failures/collection limitations are documented in WORKLOG.

## Evidence boundaries

Large original logs/model/data remain on the authorized8TB disk. The complete
project/result index has5,731 files and1,907,130,927 bytes; index SHA256
`e6b502b4f478fe275350bb16dc079277559a250ae95982daa6b29e0ce470ef32`.
The bounded package retains actual Canonical witnesses, full WALs, compressed
cell metadata, all metrics, quality counts, input replay hashes, failed pilot
energy audit and negative outcomes. Compact witnesses are explicitly derived,
not byte copies of full IPC rows; raw hashes point to complete source records.

Read `protocol/METRIC_SCOPE.md`: primary commit is durable Owner install;
actual certified-Consumer clocks are also supplied. GPU energy excludes padding
and model initialization, and is not host energy. Overlapping row durations are
not exclusive GPU seconds.7 Linux SIGKILL cases are CPU fake-model fixtures,
not new GPU recovery trials. Initial pilot1 energy coverage was insufficient
for strict comparisons and is not silently extrapolated.

No manuscript/title/abstract edits. Original C1/C2/C3 evidence and prior V0/V1,
batch-input-realization and other negative conclusions remain unchanged.
This is not a DSN acceptance guarantee or a claim to exhaust the topic.

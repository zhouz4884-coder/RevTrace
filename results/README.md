# Results policy

`results/phase0` and `results/phase1` contain migrated compact evidence.
`results/phase2` is the first standalone-project evidence tree and includes
raw compact records, independent policy-repair validation, five-run
replication, paper-facing CSV/Markdown tables, and a source manifest.
Future experiments use:

```text
results/<phase>/<experiment_id>/
  RUN.json
  summary.json
  tables/
  manifests/
```

Large request-level traces, model outputs, GPU profiles, and logs stay on the
experiment disk. Paper-facing aggregates are copied only after validation and
must include hashes pointing back to the raw run.

`results/r10_qwen_cross_adapter` is the compact exception containing the four
complete per-event JSON records for the final Qwen cross-adapter gate.  Its
`summary.json` records SHA-256 hashes, code commit, per-cell gates, and the
fail-closed matrix decision.  Failed/smoke realizations are retained under
`diagnostics` and are not mixed into the production aggregate.

The same directory also contains two `sg/` cells rerun on the R10 workload and
`ablation_summary.json`. Together with the four coarse/hybrid cells, these form
the six-cell ceteris-paribus SG/Coarse-DGFT/Hybrid-DGFT ablation. The SG raw
records retain their failed tail-SLO decisions even though all independently
replayed output, state, and version checks are exact.

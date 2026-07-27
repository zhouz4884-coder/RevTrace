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

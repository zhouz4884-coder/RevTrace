# Results policy

`results/phase0` and `results/phase1` contain the migrated compact evidence.
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

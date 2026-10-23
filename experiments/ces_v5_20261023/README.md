# RevTrace CES V5 — CPU implementation and research audit

This snapshot contains a runnable CPU-tested CES V5 scheduling implementation,
historical physical-cost calibration, mathematical counterexamples, and finite
scheduling-model oracles. **No V5 GPU run was performed.** The user paused
server/GPU work because the server network is unavailable.

Read `RESEARCH_DECISION.zh.md` for the integrated algorithm judgment, its
derivation, references, implemented scope, and remaining empirical questions.
The original manuscript and V4 frozen results were not edited.

## Implemented runtime

- Immutable actual Consumer acknowledgements, used only for scheduling.
- Residual joint Display/Commit credit, complete common-cut accounting.
- Shared empirical batch scenarios with row-completion CDFs and separate lease.
- Homogeneous G/G and V/V sub-batch choices alongside Verify/Generate choices.
- The original full FP32 correct-context verification, paid fresh fallback,
  independent FP32 generation, D1, admission predicates and WAL remain required.

`progress_joint` is currently a GPU0 deadline-order **ablation**, not a claim
that a full two-GPU joint planner exists. At c16/batch16 it can be set-equivalent
to FIFO. The symbolic predecessor-deadline module is separate from runtime
execution and never constructs an unknown Parent or token output.

## Reproduce the CPU checks

From the snapshot directory, with Python, pytest and the runtime's ordinary
CPU dependencies available:

```text
python -m pytest runtime/tests/test_ces_v5_policy.py runtime/tests/test_ces_v5_integration.py
python -m pytest test_cpu_planning_oracle.py test_deadline_backprop.py test_cpu_repairs.py test_v5_analysis.py
python math_counterexamples_v5.py --expect repaired
python cpu_planning_oracle.py
```

Set `PYTHONPATH` to `runtime/src`, `runtime/scripts`, `runtime/tests` and the
snapshot directory when invoking tests directly. The recorded full run script
`run_cpu_validation.py` sets these paths and refuses to overwrite old evidence.
Use a new result directory for independent reruns.

For historical calibration scripts, the local collection uses the sibling V4
directory's `collected/` layout. In the public V4 archive the same files are
under `evidence/`; provide that directory as `collected/` in a separate local
reproduction checkout, and place its
`evidence/calibration/calibration_v5/CALIBRATION.json` at the V4 root as
`CALIBRATION_v5.json`. Source hashes in each calibration identify the exact
input bytes. CPU safety/oracle tests do not require these historical inputs.

## Evidence boundaries

- `cpu_validation_*`: CPU protocol tests and synthetic mathematical fixtures.
- `calibration_*`: models derived from historical V4 development observations.
- `*_predictor_audit`: checks against actual historical selected batches, not
  counterfactual V5 execution and not a new independent validation campaign.
- `cpu_planning_oracle.py`: exact only for its declared finite deterministic
  action set and fixed transition/cost assumptions. No real GPU optimum claimed.
- `deadline_backprop.py`: symbolic deadline inheritance for released obligations.
- `audit_v5.py` / `summarize_v5.py`: tools prepared for future real runs; missing
  runs remain missing and cannot be turned into favorable results.

Reference V4 archive: `01f6e04aa88cf704c129242e6bbdaf42de159525`.
Runtime parent source: `e0aeae1b418644c378dde331c59b55fc5948b40f`.
All actual GPU model/audio/raw logs remain on the designated 8 TB experiment
disk. This bounded snapshot contains no model weights, source audio, credentials
or newly generated GPU evidence.

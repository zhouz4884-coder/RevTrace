# RevTrace CK5 — composed protocol and full-service recovery

Experiment ID `REVTRACE-CK5-20261026`. Steps 1–5 complete; no manuscript edits.

Read [the final research report](FINAL_REPORT.zh.md) first, followed by
[the contribution map](CONTRIBUTION_EVIDENCE_MATRIX.md),
[the protocol](PROTOCOL.md), [the conditional obligations](COMPOSITION_OBLIGATIONS.md)
and [engineering decisions](ENGINEERING_DECISIONS.md).

## Exact artifacts

- `SOURCE_v6.json` / `SOURCE_v6.tar.gz`: exact148-file executed source, commit
  `b8aa802c687256d3801612dc8bee585ee849ddea`.
- `RUNTIME_CK5_v6.bundle`: complete recoverable runtime Git history.
- `BOUNDED_EVIDENCE_v1.tar.gz` / metadata:2250 bounded records, source/configs,
  native WALs, independent audits, XML, cost/recovery/actual-consumer checks and
  raw8TB hash index. No audio, weights, credentials or manuscript.
- `analysis_v1`:84 formal run descriptive groups and same-input paired results.
- `CPU_win32_v6.xml`, `CPU_EXTERNAL_v4.xml`:258+12 supported Windows tests;
  final Linux258+12 and exact models in bounded archive.
- `FORMAL_PRODUCT_v6_exact.json`, `FORMAL_TWO_SESSION_v6.json`,
  `INFORMATION_CHARACTERIZATION_v1.json`:finite scopes/counterexamples.
- `WHISPER_ORACLE_v3.json`:16 actual GPU operator calls, not serving throughput.
- `LOCAL_EVIDENCE_IDENTITY_v1.json`:archive and included-file hash validation.

## Recount without GPU

Use a new directory; scripts refuse overwriting final outputs:

```powershell
python unpack_evidence.py
python aggregate_results.py --root collected_v6 --output analysis_recount
```

`unpack_evidence.py` creates `collected_v6` after verifying archive SHA256 and
every member path/type. `analysis_v1` is frozen; choose a new output for recount.

For runtime tests, extract SOURCE_v6 into a new directory (no dependencies or
models embedded) or clone the bundle. Run `regression.py` against the local
runtime; it selects the supported suite. `test_composed_recovery_external.py`
is a separate CPU fixture suite. Environment details are in the final resource
record and per-run provenance. There is no automatic new GPU execution on read.

Full raw traces remain on the declared8TB path in the final report. Raw byte
hashes identify retained data but do not replace access to large event traces.
Controllers and independent checkers are included for inspection, not a promise
that different hardware/software reproduces identical neural output or timing.

## Main outcome

84 formal +6 development episodes completed on final source; all recorded
safety audits pass. Normal24/24 dual P99 pass. Fault36/36 and post-sync8/8 miss
whole-run dual SLO. Old certified facts become visible earlier while new neural
work still waits on cold models. Full Standard benefits too. Eight actual
unique reused sources, not90 independent subjects. This strengthens protocol
and recovery evidence, not a new exclusive performance algorithm.

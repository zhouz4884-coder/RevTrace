# Online State-Admission Necessity and Cost Study

Experiment: **REVTRACE-ONLINE-ADMISSION-20261022**. This is the completed
72-cell online experiment and audit snapshot, not a manuscript revision or a
claim that every part of the wider research programme is complete.

## Result first

* Controlled wrong-context feedback was admitted and then consumed by real later
  GPU inference. Unprotected full-serving WER changed from16/764 errors (2.094%)
  in clean traffic to48/764 (6.283%, sync16) or50/764 (6.545%, cohort8) under F2.
* Correct-context Score/Strict verification with paid selective FP32 fallback is
  a valid strong alternative. It is not a deliberately weakened competitor.
  The independently generated-reference-labelled accepted subsets had zero
  reference mismatches; unlabelled cases remain unknown.
* DGFT's rate separation has workload-dependent benefits. In sync16/F2, its paired
  median Goodput is75.6% above Strict but19.8% below independent Fine Authority;
  its GPU energy is26.7% below Strict and13.4% below Fine. These are different
  comparisons, not one combined win. Standard Safe Async Coarse remains a full
  positive control and has comparable results.
* All four predeclared best-legal-baseline overall performance gates are NO-GO.
  Quality noninferiority was not established: DGFT has17 rather than16 word
  errors/764, with a paired WER-difference95% upper bound0.534pp above the frozen
  0.5pp margin. This is not proof of significant harm above0.5pp.

## Read the evidence

| Question | File |
|---|---|
| Setup, controls, acceptance criteria | [protocols/PROTOCOL.md](protocols/PROTOCOL.md) |
| Numerical result and scope | [RESULTS_SUMMARY.md](RESULTS_SUMMARY.md) |
| All24 method/load/traffic groups | [GROUPS.csv](evidence/collected/FORMAL_RESULTS_v1/GROUPS.csv) |
| All72 individual formal cells | [SERVICE_CELLS.csv](evidence/collected/formal_v1_audit_v3/SERVICE_CELLS.csv) |
| Same-repeat comparisons and intervals | [PAIRED_COMPARISONS.json](evidence/collected/FORMAL_RESULTS_v1/PAIRED_COMPARISONS.json) |
| Every predeclared decision | [GONOGO.json](evidence/collected/FORMAL_RESULTS_v1/GONOGO.json) |
| Physical GPU phase costs | [PHYSICAL_MODEL_PHASES.csv](evidence/collected/formal_v1_audit_v3/PHYSICAL_MODEL_PHASES.csv) |
| Actual job clocks, not additive physical GPU time | [JOB_CLOCKS.csv](evidence/collected/formal_v1_audit_v3/JOB_CLOCKS.csv) |
| Real subsequent neural-use witnesses | [NEURAL_FEEDBACK_CHAINS_v1](evidence/collected/NEURAL_FEEDBACK_CHAINS_v1/SUMMARY.json) |
| Sampled generated-reference and fixed-future GPU controls | [REFERENCE_AND_FUTURE_LABELS.json](evidence/collected/FORMAL_RESULTS_v1/REFERENCE_AND_FUTURE_LABELS.json) |
| Byte-exact runtime and data identity | [FINAL_CODE_MODEL_DATA_IDENTITY.json](evidence/FINAL_CODE_MODEL_DATA_IDENTITY.json) |
| Full raw index retained on8TB | [RAW_EVIDENCE_INDEX.json](evidence/RAW_EVIDENCE_INDEX.json) |
| Read-only candidate-readiness bounds | [supplemental_audits](supplemental_audits/CANDIDATE_WAIT_SUMMARY_REMOTE.json) |
| This published snapshot's complete file hashes | [DELIVERY_MANIFEST.json](DELIVERY_MANIFEST.json) |

## Frozen execution and evidence tiers

The executed runtime is`55cd52dfdbab71298cdb7eae3b0c08c9424020c6`, with119
manifested files. `runtime/` is a byte-verified copy, not the current dirty root
working tree. It uses Qwen3-ASR-1.7B, a resident FP16 Proposer on GPU0 and FP32
target/Authority on GPU1 (two RTX3090s), durable group-ready WAL, trusted Render
and an actual local two-lane consumer. Model/audio assets are not redistributed.

Six policies x two workloads x clean/F2 x three paired repeats =72 fresh formal
cells. There are16 distinct speakers/full utterances, not72 independent datasets.
The16–28s English sources were previously used in Phase D and were not used to
choose the fault donor/pilot. F2 is an artificial context-substitution stress
condition, not measured natural incidence. Workloads are sync16 and the same16
sources as two8-stream cohorts (0s/32s,0.25s internal stagger).

Display2s/Commit8s Goodput is partial deadline-qualified audio progress divided
by full arrival-and-drain wall time, not an entire-run P99 pass. All unfinished
requests remain in the denominator; all72 formal cells finished. Energy includes
both GPUs over the measured serving interval; it is not total-system energy.
The common-frontier view and arrival definitions are in the frozen protocol.

The independent post-serving processor replay covers1,562 real batches but is
CPU tensor reconstruction, not new generation. Generated-reference160 labels and
32 fixed-future opportunities are separate real GPU diagnostics, not serving
performance. Their192 unlabelled direct-root cases are not filled with zeros.
Prior failed pilots and controls remain in the indexed evidence.

## Raw evidence and reproducibility

`evidence/` contains the byte-exact919-file bounded payload plus its original
MANIFEST; configurations, source/data/environment identities, pilot failures,
formal metadata, statistical tables, physical costs, all source/frontier results
and independent audit outputs are included. The full raw index has1,568 files;
raw worker/events/consumer/power/WAL files remain on the designated8TB disk at the
recorded result root. No originals were replaced by summaries.

The separate complete formal/control raw export contains1,216 files,536,989,047
uncompressed bytes,49,679,570 compressed bytes. It exceeded the previously frozen
45MB publication bound and is **not silently reduced or claimed as uploaded**.
Its archive/manifest hashes and retained location are in
`supplemental_audits/RAW_EXPORT_SUMMARY_REMOTE.json`. The independently readable
bounded tables are published without changing that bound.

Run `python analysis/check_scoped_runtime.py` from this study directory. The
15-file scope is explicit in`CPU_PROTOCOL_SCOPE.json`; the snapshot also carries
legacy tests whose separate campaign tools are not bundled, so unscoped
`pytest` is not a supported standalone reproduction command. Recorded Windows/
Linux frozen-runtime regressions each passed163 tests. Run standalone helper
tests from`analysis/`. `analysis/` contains the actual audit/statistics/
control/pack scripts; remote scripts require the recorded8TB layout, dependencies,
model and licensed data, not just this Git checkout. No GPU work launches merely
by reading this repository. Historical analysis outputs are immutable snapshots;
the publication audit reports hashes and safety checks, not GPU attestation or a
proof of complete credential absence.

## Scope and pending work

No manuscript body, title or abstract is edited by this release. Existing Phase N,
Phase D, Opportunity A/B, Elastic and recovery results remain under their own
protocols and are not overwritten or pooled with these measurements. This is a
public, attributable research repository, not the anonymous review mirror.
The newly requested C2 bottleneck analysis and possible mechanism plan are
**pending** and are not represented as a completed algorithm or new GPU result.

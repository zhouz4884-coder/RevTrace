# RevTrace CES V5: closed-loop completion and bounded GPU evaluation

The previously CPU-only released-successor planning and cross-replan service
obligations are now wired into the actual runtime. This artifact retains the
implementation, all negative results, independent audits and an explicit
**NO-GO for the current full controller as a C2 performance upgrade**.

Start with [the Chinese research report](RESEARCH_REPORT.zh.md),
[algorithm explanation](ALGORITHM_EXPLANATION.zh.md),
[implementation/test/trace map](IMPLEMENTATION_COVERAGE.md), and
[Contribution–Evidence Matrix](CONTRIBUTION_EVIDENCE_MATRIX.md).

- Runtime commit: `e45c66475ba1173a98b49b8c9e62f3e8cb45b333` (isolated implementation snapshot; exact source files and manifest included).
- Formal plan:72 fresh-process serving cells,16 sources, sync/staggered Mixed-F2,3 repeats;4 safety-smoke and2 paid Strict Oracle cells remain separate.
- Safety and local independent event/quality/energy audits pass. The exact20 CPU snapshot replays are not GPU speed measurements.
- Full Causal/Fine paired Goodput: essentially equal in sync; -32.35% in staggered. New local component gains do not overcome the strong-baseline deficit.
- Same final aggregate WER/CER does not mean identical histories or harmless display retractions.22 Proposer capped rows,0 capped Authority admissions, and0/72 whole-run dualP99 passes are retained.
- Old validation audio was reused for calibration/diagnosis; this is not independent held-out confirmation, a natural fault-rate estimate, or a global optimum claim.

## Layout

`runtime/` is the exact140-file frozen source. `evidence/` contains the verified
bounded collection; `analysis/` is the separately implemented local raw-event,
reference-text and power recomputation. In the working checkout, these latter
directories are named `collected/` and `local_review/` respectively.

Important evidence subdirectories:

- `formal_audit/`, `formal_summary/`: all72 requested cells, real costs and paired results.
- `formal_independent_diagnostics_v2/`: actual activation, critical paths and service promises.
- `formal_chosen_prediction_v1/`: only actually selected first-batch prediction versus physical timing.
- `formal_cpu_snapshot_profile_v1/`: exact CPU replay and profiling; no counterfactual serving gain.
- `formal_proposal_tails_v1/`: all real Proposer rows/batches; its method column denotes runtime method. Use the cell label to distinguish joint/shared side arms.
- `RESOURCE_RELEASE.json`:156 original Worker PID/starttick identities and both GPU controllers released; other users' processes untouched.
- `RAW_INDEX.json`, `MANIFEST.json`, `COLLECTION_TRANSPORT_INDEX.json`: full8TB raw identities, bounded-file hashes and transport verification.

The full model-input arrays, audio and model weights remain on the designated
8TB experiment disk. The bounded archive is85,453,556bytes, verified through
three parts; each published file is below40MB. Raw GPU evidence is preserved.
The declared Linux pytest basetemp is excluded and recorded as a CPU fixture,
not silently promoted into GPU evidence; source, commands, logs and JUnit remain.

## Version and correction discipline

No frozen runtime or measurement was changed after launch. Original smoke
audit false-positive, diagnostics' `journals` classification error, and collection
layout/CPU-temp failures are preserved beside corrected checks. Core diagnostic
CSVs are byte-identical across its classification-only correction.

Use `evidence/formal_FREEZE.json` and `FORMAL_CONTROLLER_FINAL.json` for the actual
f17378 controller. `FORMAL_FREEZE_LOCAL.json` retains a transient, unexecuted
7c0a3b import-renaming state; it is not the executed controller.

No manuscript/title/abstract edits, extra GPU tuning, Elastic-rho restart,
Grafting, V2 Selector, automatic submission, or acceptance guarantee is included.

# CES V5 bounded GPU pilot and closed-loop diagnosis

Experiment `REVTRACE-CES-V5-GPU-20261025`; runtime
`126dc815962e8f726b0cbdf214a19318b28a3629`.

**Result:** tested admission checks pass, but the current online prototype is
NO-GO as an additional C2 performance contribution. It is not the complete
successor-aware algorithm discussed in the CPU design: online deadline
backpropagation and cross-replanning service protection are absent.

Start with [the Chinese research report](RESEARCH_REPORT.zh.md),
[Contribution–Evidence Matrix](CONTRIBUTION_EVIDENCE_MATRIX.md), and
[machine-readable decision](DECISION.json).

The48online cells use16reused diagnostic acoustic sources, two arrival regimes,
eight method labels and three paired fresh-process repeats. Fixedfine2s/rho1,
FP16GPU0/FP32GPU1, original safety/D1/WAL and sharedRow-complete. TwoOracle
diagnostics and six paid operator batches are separate from performance runs.
No paper edits, no larger matrix, no new GPU runs after closure.

Progress/Fine pairedGoodput: sync−1.43%(descriptive interval crosses0),
staggered−12.39%; staggeredenergy+8.80%. Complete failing/negative outcomes
are retained. The observed41/405 and56/405lateCommit counts repeat the same
135frontiers across3runs; they are not IID acoustic samples.

## Evidence layers

- `evidence/`: original and metadata-corrected audits, frozen configurations,
  environment/model hashes, actual events/Consumer/WAL, Canonical witnesses,
  physical-batch accounting, paired summaries and8TBraw index.
- `analysis/`: separate local event-to-metric reconstruction, first/stable
  visibility, lateCommit timing, deferred targets, actual selected-row forecast
  checks, input-coverage qualifications and arrival-only mathematical bounds.
- [Independent CPU cause review](INDEPENDENT_CPU_CAUSE_REVIEW.md): exact2/8
  constructed counterexamples, not GPU timing or a promised repair speedup.
- [Actual trace spot audit](ACTUAL_TRACE_SPOT_AUDIT.md): sameParent5 target
  deferred13times; its13.068squeue is not idle/free reclaimable GPU time.
- [Analysis corrections](ANALYSIS_REPAIRS.md): original metadata typo and an
  assertion-stopped supplementary reader bug, with original versions retained.

Input processor replay covers1693physical batches/12685row inputs with exact
CPUrepeats. It does not assert universal GPU forward equivalence. The48online
serving cells contain1713actual model calls; operator/Oracle costs are separate.
All100recorded original worker handles and the GPUcontroller exited; resource
snapshot showed noGPUcompute processes. No foreign process was terminated.

## Reproduction and provenance

`PROTOCOL.md` was frozen before GPU execution. The exact runtime and initial
controllers are in `SOURCE_AND_CONTROLLERS_v1.tar.gz`; itsSHA256 is
`89d722d8fe0de330ee857c5d3e641de0c1f1869bdf164291f835635c4dfc5cd3`.
It references the prior CPU source archive without relabelling that archive as
GPUevidence. `tools/` contains post-run audit/diagnosis implementations; each
audit records source hashes. See script headers for the original local/remote
stage layout and explicit8TBmodel/audio/result dependencies.

The remote raw index covers915files/363940021bytes; full model inputs and raw
files remain on the designated8TBdisk. Bounded downloadSHA256:
`497ceeb431fefd3409f6431d3f8370319b8032e8199893385143636d89a958e1`.
Top-levelMANIFEST.json verifies every delivered file; no weights/audio/caches
or credentials are included. Historical results and manuscript files remain
unchanged. This is an authorized public research archive, not an anonymous
review-mirror refresh or a claim of submission readiness.

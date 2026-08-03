# Phase R9 Final Report: Directional Granularity Feedback Transactions

> Historical pre-R9.E report. Its 15/16 service matrix has been superseded by
> the fresh 16/16 online, contract-bound matrix in
> [R9.E Online Evidence and Submission Closure](r9e_online_submission_closure.md).
> Do not use the historical service numbers below as submission claims.

## Decision

`QUALIFIED_R9_EVIDENCE_15_OF_16_STRICT_CELLS`

R9 closes the Whisper quality mechanism and validates it at three model
scales.  The untouched quality gate passes 3/3, the development gate passes
3/3, and 15/16 real two-GPU service cells satisfy every pre-registered
per-cell threshold.  One Base/Poisson cell is retained as a reproducible
low-load capacity boundary rather than relabelled as a pass.

## R9.0--R9.2: problem and legal oracle

The previous Whisper path could protect feedback-state integrity but could not
always preserve enough semantic context after safe truncation.  R9 therefore
separates two granularities:

1. a 10-second fine proposer supplies low-latency provisional text and a
   directional coverage witness;
2. a dynamic 15--30-second canonical segment supplies stable text;
3. only a versioned, lineage-valid canonical transition may update feedback
   state;
4. an asymmetric local omission triggers singleton replay of that display
   segment, not a full-session replay;
5. full replay is reserved for persistent asymmetric omission or an explicit
   repeated-phrase degeneration witness.

The key invariant is that a risk signal schedules verification but never
authorizes state installation.  Coverage scores and repetition scores are
empirical witnesses, not deterministic numerical certificates.

## R9.3: failures encountered and their causes

### Fixed asymmetry was under-specified

The runner accepted an asymmetry parameter but failed to pass it into segment
decisions.  Some early files therefore silently used a default.  The call path
was fixed and all paper-facing cells were rerun.

### Segment-boundary transport looked like an omission

A word sequence can move from one adaptive segment to its neighbor.  Comparing
each coarse segment with only the corresponding fine segment produced a false
coverage deficit and one harmful repair.  The boundary-adjusted deficit now
cancels only missing mass recovered by an adjacent segment while retaining the
original local denominator.  This prevents a long neighbor from diluting a
real omission.

### Structural warnings caused catastrophic replay tails

The original policy escalated failed EOS/yield salvage to full-session replay.
In Base seed 1005 this produced 18 singleton calls over 180 seconds, reduced
wall speedup to 1.855x, and increased energy by 4.7%.  A structural warning is
not semantic evidence.  The revised policy requires directional omission or a
repeated-4-gram fraction of at least 0.25.  The same seed then reaches 2.715x
wall speedup, 27.54% energy reduction, 1.010-second display P99, zero semantic
violations, and zero full-session replay.

### The remaining service boundary is compute, not semantics

Base/Poisson seed 2026103003 obtains 2.453x wall and 1.226x GPU-normalized
speedup; an identical rerun obtains 2.488x and 1.244x.  Both have zero semantic
violations, no repair amplification, acceptable tails, and about 20--21%
energy reduction.  Phase timing shows a dual-path time of about 10.83 seconds,
of which coverage decisions consume only about 0.06 seconds.  The provisional
proposer, rather than semantic repair, is the limiting path.

Two-sided diagnostics reject easy tuning explanations:

- minimum 20 seconds: 1.869x, 24 salvage calls, energy +3.9%;
- maximum 25 seconds: 2.389x, 73 segment jobs, energy reduction 17.7%;
- proposer budget 28: passes narrowly but raises correction P95 to 69.2% and
  triggers replay;
- proposer budget 30: 2.515x, but with insufficient margin to replace the
  pre-registered 32-step matrix.

The final artifact therefore retains the negative boundary cell.

## R9.4: quality evidence

All values below are paired WER differences relative to the prior unsafe/fine
comparison; negative is better.  Speedups in this table are projections from
measured component times, not deployed wall-clock claims.

| Cohort | Model | Sessions | Mean WER delta (pp) | Bootstrap 95% upper (pp) | Catastrophic | Audio amp. | Projected 2-GPU speedup |
|---|---:|---:|---:|---:|---:|---:|---:|
| Development | Tiny | 128 | -12.23 | -10.48 | 0 | 1.036x | 3.70x |
| Development | Base | 128 | -18.21 | -16.17 | 0 | 1.034x | 4.39x |
| Development | Small | 128 | -25.27 | -22.15 | 0 | 1.048x | 4.49x |
| Untouched final3 | Tiny | 214 | -8.26 | -5.15 | 0 | 1.025x | 4.36x |
| Untouched final3 | Base | 214 | -11.03 | -7.51 | 0 | 1.000x | 4.75x |
| Untouched final3 | Small | 214 | -13.76 | -9.09 | 0 | 1.000x | 5.46x |

The final3 manifest contains 214 previously unused utterances and 2487.72
seconds of audio.  Its SHA-256 is
`7af1c7dd65b88edfd0f5748e7d363af2dda6d418fea3a3bcb4a928ddd2a1d95c`.
The audit found zero overlap with 11,091 prior utterance IDs and no file-hash or
audio-metadata mismatch.

## R9.5: real two-GPU service evidence

These are real wall-clock and NVML energy measurements on two RTX 3090 GPUs.

| Model / arrival | Cells passed | Wall median (min) | GPU-normalized median | Energy median (min) | Display P99 max | Commit P99 max | Audio amp. max |
|---|---:|---:|---:|---:|---:|---:|---:|
| Base / sync | 5/5 | 2.741x (2.613x) | 1.370x | 28.56% (24.50%) | 1.202 s | 32.422 s | 1.012x |
| Base / Poisson | 4/5 | 2.754x (2.453x) | 1.377x | 28.58% (19.99%) | 1.432 s | 32.759 s | 1.012x |
| Tiny / sync | 3/3 | 2.689x (2.621x) | 1.345x | 29.09% (27.09%) | 0.972 s | 32.174 s | 1.020x |
| Small / sync | 3/3 | 3.631x (3.002x) | 1.815x | 31.51% (21.02%) | 1.552 s | 33.800 s | 1.042x |

Across 16 cells, RevTrace issued 1,048 versioned commit certificates and
observed zero semantic/state-install violations.  The rule-of-three 95% upper
bound is 0.286%; this is not a mathematical zero or a floating-point exactness
certificate.

## Code changed in R9

- `src/revtrace/dgft.py`: directional coverage, boundary transport correction,
  repeated-phrase degeneration witness, transaction primitives.
- `scripts/remote/run_r9_segment_oracle.py`: adaptive canonical segments,
  local singleton salvage, and bounded escalation.
- `scripts/remote/run_r9_coverage_fallback.py`: paired quality evaluation,
  local repair, post-repair checks, and fixed parameter propagation.
- `scripts/remote/run_r9_dgft_service.py`: real two-GPU proposer/authority
  pipeline, versioned state installation, repairs, energy/tail metrics, and
  phase timing.
- `scripts/remote/run_r9_semantic_escalation_gate.sh`: frozen development gate.
- `scripts/remote/run_r9_final3_confirmation.sh`: untouched final3 execution.
- `scripts/remote/run_r9_service_matrix_v2.sh`: 16-cell real service matrix.
- `scripts/audit_r9_holdout.py`: ID, hash, duration, and metadata audit.
- `scripts/build_r9_untouched_manifest.py`: prior-result exclusion and manifest
  construction.
- `scripts/finalize_r9.py`: machine-auditable final aggregation without hiding
  the 15/16 strict service result.
- `tests/test_dgft.py`: coverage-boundary, repetition, and transaction tests.

## Claim boundary

R9 establishes scale generality over Whisper Tiny/Base/Small and complements
the earlier Qwen family evidence.  It does not establish universality over all
streaming ASR models.  The deployed service results are real; quality-table
speedups are projections.  The risk contract is empirical; correctness of
state installation comes from canonical selection plus transaction checks.

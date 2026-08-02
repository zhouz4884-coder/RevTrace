# Phase R9: Dual-Granularity Canonical Segment Commit

## Frozen starting point (R9.0)

- `QWEN_PRIMARY_STRONG_PASS`
- `WHISPER_SCALE_INTEGRITY_PASS`
- `WHISPER_QUALITY_TAIL_UNRESOLVED`

The R8 confirmation sessions are development evidence only.  They may select a
fixed R9 segment policy, but they cannot support the final generalization claim.

## R9.1 legal-oracle death gate

The fixed candidates are sequential 10-second singleton authority, one fused
20-second singleton segment, and one fused 30-second singleton segment.  Every
candidate starts from the last certified prompt.  Reference transcripts and WER
are used only after a full trajectory has completed.

A candidate advances only when all three model scales have zero catastrophic
sessions, mean paired WER delta at most 1 percentage point, bootstrap 95% upper
bound at most 2 points (also per split), and either halves measured authority
time relative to R8 continuous replay or projects to at least 2.5x two-GPU wall
speedup.

Fused authority is a new coarse-grained canonical trajectory.  It is not
presented as bitwise equality with per-window singleton.  Zero observed
violations remains empirical evidence unless all installed transitions are
checked by the frozen canonical path and transaction validator.

## Pre-registered service contract if R9.1 passes

- Provisional display P99: at most 1.9 seconds.
- Canonical segment commit P99: at most 36 seconds.
- Median wall speedup: at least 2.5x.
- GPU-normalized speedup: at least 1.25x.
- Minimum energy reduction: at least 20% (25% is the stretch target).
- Authority audio amplification: at most 1.2x.
- Stale, lineage, duplicate, gap/overlap and cross-session installs: zero.

Dynamic 15--30 second boundaries are retained only if a raw-audio hard boundary
does not increase quality failures, adds at most 10% authority GPU work over the
best fixed policy, improves rollback P95, and does not increase corrections.

## Frozen final policy after development and validation repair

The first 40-session confirmation cohort exposed one Base-scale omission: a
30-second coarse candidate dropped its final sentence while the fine trajectory
retained it.  That cohort was therefore reclassified as validation evidence and
is not used for the final generalization claim.

Lowering the directional threshold globally from 0.37 to 0.20 repaired the
omission but initially caused one harmful repair in the 128-session development
cohort.  Inspection showed that the apparent loss was content transported
across an adaptive segment boundary: the previous coarse segment contained the
same words that appeared late in the corresponding fine segment.  R9 therefore
freezes a boundary-transport correction before its second untouched test:

- forward directional coverage threshold: 0.20;
- asymmetry margin: 0.15;
- structural threshold: 0.20;
- subtract only omission mass that disappears when the current segment is
  concatenated with an adjacent segment;
- local display repair first;
- full-session escalation only after persistent asymmetric omission or an
  explicit repeated-4-gram degeneration score of at least 0.25 after local
  salvage.  A structural/EOS warning alone does not authorize a full replay.

The correction retains the current segment's denominator, so adding a long
neighbor cannot dilute a true omission.  Coverage remains a reference-free
empirical scheduling witness, not a deterministic certificate.

The first and second confirmations became validation evidence after the Base
omission and the service-tail full-replay failure, respectively.  The final
policy was therefore frozen before a third untouched confirmation.  Its
manifest SHA-256 is
`7af1c7dd65b88edfd0f5748e7d363af2dda6d418fea3a3bcb4a928ddd2a1d95c`.
It contains 214 previously unused LibriSpeech utterances (2487.72 seconds), has
zero overlap with 11,091 utterance identities found in 1,211 prior result
files, and passed per-file hash and audio-metadata checks.

## Final service interpretation

The frozen 32-step proposer matrix contains 16 real two-GPU cells.  Fifteen
strictly satisfy every pre-registered per-cell gate.  One Base/Poisson cell is
a reproducible low-load capacity boundary (2.453x wall and 1.226x
GPU-normalized speedup; one identical rerun gives 2.488x and 1.244x).  It has
zero semantic violations, no replay amplification, acceptable tail latency,
and about 20--21% energy reduction.  This miss is retained as a negative result
and is not relabelled as a pass.  The Base/Poisson group median remains above
the service thresholds.

Diagnostics show that 20--30 second segments increase structural salvage and
that a 25-second maximum increases segment jobs; neither is adopted.  A
30-step proposer can move the boundary cell just above 2.5x, but with limited
headroom, so the paper-facing matrix keeps the pre-registered 32-step policy.

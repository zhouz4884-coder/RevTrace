# RevTrace model-scale generality audit

## Decision

`MECHANISM_GENERALIZES; PERFORMANCE_IS_FAMILY_DEPENDENT; WHISPER_QUALITY_NOT_CLOSED`

The model set is selected by family and scale rather than by measured outcome:

- Qwen3-ASR: both available public sizes used by the project (0.6B and 1.7B).
- Whisper: three consecutive English checkpoints (tiny.en, base.en, and
  small.en).
- The Whisper tiny/small transfers reuse the Whisper-base EFSC and CSM
  policies, P32/R48 execution budgets, confirmation manifest, and thresholds.
  No per-checkpoint retuning is allowed.

This five-checkpoint matrix is intended to rule out a favorable-checkpoint
selection story. It does not imply that every checkpoint satisfies every
quality or service gate.

## Deployed/service evidence

| Family | Checkpoint | Runs | Wall speedup | GPU-normalized | Display P99 | State P99 | Absolute energy reduction | Integrity |
|---|---|---:|---:|---:|---:|---:|---:|---|
| Qwen3-ASR | 0.6B | deployed gate | 5.533x | 2.766x | -- | 2.979 s | -- | 0 output/state/stale violations |
| Qwen3-ASR | 1.7B | deployed gate | 4.751x | 2.375x | -- | 2.587 s | -- | 0 output/state/stale violations |
| Whisper | tiny.en | 1 zero-shot transfer | 2.623x | 1.311x | 1.120 s | 1.177 s | 26.95% | 0 stale/lineage violations |
| Whisper | base.en | 1 matched-version transfer | 2.518x | 1.259x | 1.784 s | 2.129 s | 23.42% | 0 stale/lineage violations |
| Whisper | small.en | 1 zero-shot transfer | 2.608x | 1.304x | 2.557 s | 2.689 s | 7.16% | 0 stale/lineage violations |

The Qwen rows use selective canonical verification: only a small fraction of
revision transitions enter the authority path. The Whisper R8 rows maintain an
independent continuous raw-audio lineage replay. The second full inference lane
is therefore useful work for correctness, but it imposes substantially more
compute and energy than Qwen's sparse verifier. A common 5x performance
expectation across these two execution structures would be physically
unjustified.

## Frozen Whisper quality transfer

| Checkpoint | Mean WER delta vs its canonical path | Bootstrap 95% upper | Catastrophic outliers | Semantic violations | Quality decision |
|---|---:|---:|---:|---:|---|
| tiny.en | -2.378 pp | -1.589 pp | 2 / 128 | 0 | FAIL (outlier gate) |
| base.en | -2.495 pp | -1.557 pp | 2 / 128 | 0 | FAIL (outlier gate) |
| small.en | -4.276 pp | -2.708 pp | 6 / 128 | 0 | FAIL (outlier gate) |

Average WER improves for all three transfers, including both dataset
splits, but the per-session catastrophic-outlier contract is not closed. These
negative rows must remain visible; they are evidence against checkpoint
selection, but they prohibit a claim of universal Whisper quality preservation.
The base.en quality row is a post-fix diagnostic on the set used to isolate the
asymmetric-context failure and is not an untouched final holdout. The tiny.en
and small.en rows are zero-shot scale transfers of that frozen fix.

The earlier base.en implementation also has a 10-seed sync/Poisson matrix:
2.408x median wall speedup [2.093, 2.737], 1.204x median GPU-normalized
speedup [1.047, 1.368], 1.730 s median state P99 [1.520, 2.036], and 19.49%
median energy reduction [8.10%, 29.15%]. It establishes variance but is not
mixed into the matched-version tiny/base/small scale comparison.

## Claim boundary

Supported:

1. The revision-transaction and lineage-integrity abstraction transfers across
   two architecture families and five checkpoint scales.
2. Strong Qwen deployed performance holds at both available model scales.
3. Whisper obtains a repeatable moderate wall-clock benefit; tiny/base/small do
   not exhibit a hidden no-speedup checkpoint.
4. The Qwen/Whisper gap is explained by different authority workloads, not by
   silently changing the cost accounting.

Not supported:

1. A universal 4--5x speedup across model families.
2. A universal Whisper quality-preservation guarantee.
3. Deterministic correctness from a margin threshold.
4. Using the one-seed tiny/small rows as variance-qualified headline numbers.

## Publication recommendation

Use Qwen3-ASR 0.6B/1.7B as the primary deployed-performance result. Present
Whisper tiny/base/small as a predeclared cross-architecture transfer and
capacity-boundary study, including all failed quality gates. Additional Whisper
sizes have diminishing value unless the paper claims a scaling law. The next
scientifically important improvement is not another checkpoint: it is reducing
Whisper's continuous replay cost or eliminating its remaining session-level
quality outliers without checkpoint-specific tuning.

## Auditable sources

- `results/phase1/deployed_v1/summary.json`
- `results/r8_csdr/service-budgeted-cutset-p32r48/w1-seed*.json`
- `results/r8_csdr/service-budgeted-cutset-p32r48/w2-seed*.json`
- `results/r8_csdr/service-budgeted-cutset-p32r48/tiny-transfer-seed2026083101.json`
- `results/r8_csdr/service-budgeted-cutset-p32r48/base-latest-seed2026083101.json`
- `results/r8_csdr/service-budgeted-cutset-p32r48/small-transfer-seed2026083001.json`
- `results/r8_csdr/r8-pristine-tiny-confirm-budget48-fullcontext.json`
- `results/r8_csdr/r8-pristine-confirm-asymfix.json`
- `results/r8_csdr/r8-pristine-small-confirm-budget48-fullcontext.json`
- `scripts/remote/run_r8_whisper_tiny_transfer.sh`

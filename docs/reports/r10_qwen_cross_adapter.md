# R10: Qwen DGFT Cross-Adapter Closure

## Decision

`PASS_R10_QWEN_CROSS_ADAPTER_MATRIX`

R10 answers a narrow but important submission question: can the directional
granularity mechanism used for Whisper be installed on Qwen without creating a
second, unrelated serving system?  The answer is yes.  RevTrace remains the
single state-certifying transaction runtime.  DGFT and RevOCC are evidence
adapters that propose different authorities for that same commit protocol.

The four production cells all pass the predeclared correctness, quality, and
performance gates.  Across 320 live revision events, there are zero observed
transaction-install violations, zero authority batch-repeat mismatches, and
zero authority batch-versus-singleton mismatches.

## Legal Qwen mapping

The cross-adapter does not transplant Whisper code mechanically.

- Fine lane: three native 2-second FP16 batched Qwen revisions.
- Coarse lane: one 6-second FP32 authority at the same audio frontier.
- Both lanes start from the last committed macro-state.
- DGFT mode commits the coarse authority through the existing RevTrace
  certificate and versioned ledger.
- Hybrid mode requests native 2-second singleton replay only for directional
  omission or low-margin numerical risk.
- A fresh official 2-second FP16 singleton run remains an independent semantic
  reference.  Changing the authority path cannot silently redefine quality.

The first coarse segment is executed twice as a batch and once row-by-row as
FP32 singleton.  Any mismatch fails closed before service timing begins.  The
preflight therefore certifies the selected FP32 authority implementation while
remaining outside the deployed wall-clock and energy interval.

## Production matrix

| Model | Adapter | Wall speedup | GPU-normalized speedup | Energy reduction | Native replay | Exact sessions | Edit-rate P95 | Worst edit | Display P99 | Commit P99 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Qwen3-ASR-0.6B | DGFT | **6.88x** | **3.44x** | **59.8%** | 0.00% | 11/16 | 3.43% | 5.41% | 0.826 s | 2.582 s |
| Qwen3-ASR-0.6B | Hybrid | **5.19x** | **2.59x** | **51.3%** | 5.00% | 13/16 | 2.15% | 5.41% | 0.782 s | 3.853 s |
| Qwen3-ASR-1.7B | DGFT | **6.06x** | **3.03x** | **51.0%** | 0.00% | 9/16 | 1.79% | 2.86% | 1.018 s | 3.219 s |
| Qwen3-ASR-1.7B | Hybrid | **3.92x** | **1.96x** | **33.2%** | 8.75% | 10/16 | 1.79% | 2.86% | 0.990 s | 4.437 s |

All cells use 30-second English/Chinese sessions at concurrency 16.  The two
GPUs have different roles, so GPU-normalized speedup divides the deployed wall
speedup by two.  Even the slowest hybrid cell retains 1.96x GPU-normalized
throughput and 33.2% lower energy per processed audio second.

## What the comparison says

DGFT is the throughput-oriented adapter.  It accepts the invariant coarse
authority and achieves 6.06--6.88x wall speedup.  Hybrid spends 5.00--8.75% of
events on native fine replay.  On 0.6B, this raises exact sessions from 11 to 13
and reduces P95 edit rate from 3.43% to 2.15%, while retaining 5.19x wall
speedup.  On 1.7B, replay raises exact sessions from 9 to 10 but does not change
P95 or worst edit rate; the 3.92x speedup is therefore a measurable cost for a
smaller quality gain.  The paper should report both operating points rather
than claim hybrid universally dominates DGFT.

This result does not replace the stronger RevOCC Qwen headline.  It establishes
adapter composability: one transaction core supports a numerical-risk adapter
(RevOCC) and a granularity authority adapter (DGFT).  The manuscript should
lead with the common state-entry contract and transaction semantics, then show
the adapters as architecture-specific evidence providers.  Presenting RevOCC
and DGFT as two co-equal end-to-end systems would unnecessarily fragment the
paper.

## Problems found and repaired

### 1. Chinese coverage was silently empty

The original DGFT coverage helper tokenized only Latin words.  Chinese
transcripts could therefore appear to have zero directional omission.  The
coverage representation now preserves Latin words and individual CJK
characters in source order.  This is a correctness repair, not a performance
optimization.

### 2. Singleton coarse authority had unacceptable economics

The first full 0.6B FP16 singleton authority run was semantically acceptable
but reached only 1.73x wall speedup, 0.865x GPU-normalized speedup, and increased
energy by 11.5%.  Authority/proposer service ratio was 4.40 because 16 coarse
jobs were executed serially on GPU 1.  This killed singleton authority as the
production realization, not DGFT as an adapter.

### 3. Full-context FP32 authority initially exceeded memory

vLLM initially reserved for a 65,536-token context.  FP32 authority on the
24-GB GPU could not allocate that cache.  R10 bounds the authority to 4,096
tokens, which is still far above the 30-second workload and follows the existing
fixed-shape authority protocol.

### 4. Invariance audit contaminated service timing

The first FP32 smoke result appeared slower than singleton because two repeated
batches plus all row-by-row singleton audits were included in wall and energy
measurements.  The audit is now a fail-closed preflight before the service
measurement interval.  Its 10.72--11.10 seconds are retained explicitly in the
result JSON under `authority_preflight_seconds_excluded_from_service`; they are
not hidden or charged to steady-state service.

## Claim boundaries

- FP32 batch equality was observed against FP32 singleton on the audited first
  segment for both scales and both modes.  It defines a versioned,
  concurrency-invariant authority path.
- It is not a bitwise repair of the original FP16 singleton trajectory.
- Zero observed violations over 320 events is empirical evidence, not a
  mathematical zero-failure claim.
- Exact-session counts are measured against a fresh official 2-second FP16
  singleton reference.  Non-exact sessions remain bounded by the reported edit
  rates; no session exceeds 5.41% edit rate and none exceeds the 25% catastrophic
  threshold.
- R10 demonstrates two scales of one Qwen family.  Cross-family generality still
  comes from the separate Whisper/DGFT experiments, not from these four cells
  alone.

## Auditable artifacts

- `src/revtrace/cross_adapter.py`: adapter decision, fine-lane summaries, and
  transaction certificate construction.
- `src/revtrace/dgft.py`: mixed English/CJK directional coverage.
- `scripts/remote/run_qwen_dgft_cross_adapter.py`: live two-GPU runner,
  invariance preflight, independent semantic audit, energy and latency metrics.
- `scripts/remote/run_r10_qwen_cross_adapter.sh`: frozen four-cell remote matrix.
- `scripts/finalize_r10_qwen_cross_adapter.py`: fail-closed result aggregator.
- `configs/revtrace_r10_qwen_cross_adapter.json`: frozen contract and gates.
- `tests/test_cross_adapter.py`, `tests/test_dgft.py`, and
  `tests/test_finalize_r10_qwen_cross_adapter.py`: unit and checked-in artifact
  audit.
- `results/r10_qwen_cross_adapter/*.json`: complete per-event production
  records.
- `results/r10_qwen_cross_adapter/diagnostics/`: retained failed and smoke
  realizations used to diagnose the production path.

The four production artifacts were generated from commit
`f54c1ab0bb397ee648839977274d159823c37a15`; the finalizer records their SHA-256
digests and fails if a required cell or gate is missing.

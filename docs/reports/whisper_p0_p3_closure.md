# Whisper P0-P3 protocol repair and headline closure

## Decision

`P0_P3_PAPER_THREATENING_C16_HEADLINE_FAIL`

The c16 production cells are now present in the repository and independently
recomputable.  Their median throughput is useful, but the pre-registered
headline contract does not pass.  This is a negative result for using Whisper
as a second performance leg of the current paper; it does not invalidate the
Qwen3-ASR RevTrace system result or the cross-architecture feedback mechanism.

The failure is not attributed to one remaining aggregation bug.  P0 repaired
the known metric, audit, policy-binding, and source-identity defects before the
formal R6 runs.  The frozen finalizer then reproduced the same fail-closed
decision on Linux and Windows.

## P0: protocol and implementation repairs

The formal rerun includes the following corrections.

1. Display and state goodput compare matched event scopes.  A terminal display
   event can no longer be counted on only one side of a speedup ratio.
2. Randomized risk audits execute the real low-margin transition.  They do not
   replace the tested state with a canonical state before judging it.
3. Every formal workload binds the policy file path, SHA-256 digest, complete
   runtime threshold set, runtime source identity, precision, topology, and
   terminal contract.
4. The quality runner explicitly binds `low_margin_policy=verify`; the earlier
   output that omitted this evidence field is retained as
   `c16-verify-pre-binding-fix.json` and is not the final evidence.
5. Scheduler records now expose batch occupancy, unfilled proposal slots,
   pending canonical authorities, and verifier service time.
6. Staggered checkpoint scheduling preserves the finite-horizon checkpoint
   count instead of accidentally increasing verification work.
7. Final summaries use portable root-relative evidence paths and deterministic
   LF serialization, so independent Windows and Linux finalization produces
   identical bytes.

These changes affect experimental validity and attribution.  They did not
relax any performance, latency, energy, quality, or risk gate.

## P1: causal decomposition

The c8/180-second causal matrix identifies the dominant mechanism as
`AUTHORITY_QUEUE_AND_BATCH_FRAGMENTATION`.

| Variant | Wall | GPU-normalized | State P99 | Energy reduction | Verify | Mean occupancy | Pending max |
|---|---:|---:|---:|---:|---:|---:|---:|
| Unprotected | 2.722x | 2.722x | 0.653 s | 62.6% | 0.0% | 100.0% | 0 |
| Feedback off | 3.583x | 3.583x | 0.497 s | 70.3% | 0.0% | 100.0% | 0 |
| Checkpoint only | 2.163x | 1.081x | 3.333 s | 14.3% | 5.6% | 81.8% | 7 |
| Risk only | 1.953x | 0.977x | 2.033 s | 4.7% | 11.8% | 81.8% | 2 |
| Full verify | 1.625x | 0.813x | 2.934 s | -13.1% | 16.0% | 64.3% | 5 |
| Holdback, dual GPU | 2.136x | 1.068x | 3.478 s | 13.4% | 5.6% | 72.0% | 7 |
| Holdback, colocated | 2.109x | 2.109x | 3.674 s | 53.0% | 5.6% | 75.0% | 7 |

Feedback removal raises wall speedup from 2.722x to 3.583x, showing that
growing feedback state is real work.  More importantly, adding canonical
authority reduces occupancy and creates queues.  Full verification loses
40.3% of unprotected wall speedup and makes energy reduction negative.  This
is a systems phase transition: sparse serial authority work fragments proposal
batches and blocks future state entry.

## P2: c8 capacity boundary

Neither staggered topology satisfied the strict pre-run eligibility contract,
so the protocol correctly stopped before five-seed, risk, and quality claims.

| Topology | Wall | GPU-normalized | State P99 | Energy reduction | Result |
|---|---:|---:|---:|---:|---|
| Dual GPU | 2.025x | 1.013x | 2.661 s | 13.8% | FAIL |
| Colocated | 2.000x | 2.000x | 2.827 s | 48.2% | FAIL |

The c8/180-second workload is therefore a disclosed low-load, long-session
capacity boundary.  It is not promoted to a production-performance result.

## P3: c16 production matrix

Each W1 and W2 cell contains five fresh independent seeds using two verifier
lanes, no speculative prefetch, no cohort barrier, no proposer spillover, and
the frozen R6 policy.  The headline contract requires median wall >=2.0x,
median GPU-normalized >=1.0x, median display goodput >=2.0x, minimum energy
reduction >=15%, maximum display P99 <=1.9 s, maximum state P99 <=4.0 s, and no
state, stale-commit, or display-deadline violation.

| Cell | Wall median/min | GPU-normalized median | Display P99 max | State P99 max | Energy median/min | State violations | Result |
|---|---:|---:|---:|---:|---:|---:|---|
| W1 synchronized | 2.709x / 2.037x | 1.355x | 1.495 s | 4.782 s | 32.5% / 10.3% | 0 | FAIL |
| W2 Poisson | 2.347x / 2.216x | 1.174x | 1.534 s | 4.222 s | 23.2% / 16.4% | 2 | FAIL |

The good news is real: all ten runs exceed 2.0x wall speedup, display P99 stays
below 1.9 seconds, and median energy reduction remains positive.  The bad news
is decisive: W1 violates the tail and minimum-energy contracts; W2 violates
the tail and exact state contract.  Median speed cannot compensate for those
failures in a state-certified system.

## Risk and quality contracts

The independent R6 risk run stopped as soon as a zero-error certificate became
impossible.  Two streams produced 5,166 risk-eligible entries and 121
pre-outcome randomized audits; one repeat-stable state error was caught.  The
30,000-entry target was not completed because additional samples cannot repair
a pre-registered zero-error gate.

The quality path passed: 128 sessions and 1,647 unique utterances produced a
mean WER delta of -0.0106 percentage points, a paired-bootstrap 95% upper bound
of 0, and no catastrophic outlier.  Quality is therefore not the cause of the
headline failure.

## Failure attribution

### Fixed code and protocol defects

Matched-scope goodput, real transition auditing, complete policy/source
binding, finite-horizon checkpoint scheduling, and quality-policy provenance
were repaired before final interpretation.  Cross-platform finalization and
the 184-test suite pass.  These defects explain why earlier pilot numbers were
not publication-ready; they do not explain away the R6 failure.

### Method limitation

The learned policy is adaptive rather than a fixed threshold, but its feature
space remains empirical.  R3-R6 progressively added exact window rules after
new repeat-stable roots appeared.  Independent evidence then found additional
high-margin errors.  Policy updates also change verification timing and batch
composition, so they alter the distribution on which the next policy is
evaluated.  This moving frontier is not a deterministic certificate.

### System limitation

Canonical verification introduces serial authority work.  At long state age,
even a sub-10--20% verification fraction can reduce proposal occupancy, create
pending-authority bursts, and increase state-entry P99.  Extra verifier lanes,
padding, barriers, shared weights, spillover, and speculative prefetch did not
remove the boundary; several increased contention or changed the workload
distribution.

### Numerical and model mechanism

The underlying state flips are repeat-stable on the canonical path and are not
explained by session crossover, random sampling, or rollback implementation.
They arise when low-precision, batch-shape-dependent reductions change a
token/EOS/punctuation decision; feedback then turns a local numerical change
into a different future state.  Margin correlates with risk but does not bound
the multi-subgraph perturbation.

## Scientific consequence

Whisper can support the paper's cross-architecture causal claim: batching can
create feedback-bearing state differences and RevTrace's authority mechanism
can prevent known differences from entering state.  It cannot currently
support a strong cross-architecture performance headline under the frozen
contract.

Restoring that headline requires a genuinely stronger exactness mechanism, not
another post-hoc threshold: for example, a deterministic operator slice, an
arithmetic-path-preserving grouped verifier, or a cheaper canonical replay
cutset.  Until such a mechanism passes fresh W1/W2 and risk gates, the paper
must keep Whisper performance as a measured boundary and retain Qwen3-ASR as
the validated high-performance system.

## Reproducibility and evidence

- Machine summary: `results/whisper_p0_p3/summary.json`
- Human-readable summary: `results/whisper_p0_p3/summary.md`
- Content manifest: `results/whisper_p0_p3/MANIFEST.json`
- Finalizer: `scripts/finalize_whisper_p0_p3.py`
- Runtime: `scripts/remote/run_whisper_w_system.py`
- Quality runner: `scripts/remote/run_whisper_w_quality.py`
- Dynamic policy builder: `scripts/build_whisper_w_state_age_policy.py`
- Incremental frontier compiler: `scripts/update_whisper_window_frontier.py`
- Early-fail recorder: `scripts/record_whisper_r6_early_fail.py`

The manifest hashes all 301 remote evidence files.  The repository contains
all 298 Git-sized evidence files; three oversized intermediate policy-search
artifacts remain on the experiment disk and are recorded by exact path, size,
and SHA-256 rather than being silently omitted.

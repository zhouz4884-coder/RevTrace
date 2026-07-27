# Claim boundaries

## Established

- BF16/FP16 batched execution can diverge from singleton execution for
  Qwen3-ASR under identical semantic inputs.
- Revision feedback can propagate a numerical token flip into future model
  state.
- A deployed two-GPU proposer/verifier service can preserve high wall-clock and
  SLO goodput while version-checking state commits.
- Under the frozen 30-second, concurrency-16 workload, fixed-shape terminal
  canonical execution reduced the observed 2-second state-entry miss rate from
  5.42% in Phase 1 to 0/240 for both tested Qwen3-ASR sizes.
- The resulting deployed wall-clock speedups are 5.99x and 4.97x; the
  corresponding GPU-normalized speedups are 3.00x and 2.49x.
- The flip-rich suite exercises real execution-shape flips without artificial
  logit noise.
- A fixed-probability mixture e-process provides a time-uniform upper bound on
  cumulative unsafe fast-path state entries under arbitrary temporal drift,
  provided the base audit coin is independent and fixed before observing the
  canonical outcome.

## Not established

- Zero deterministic state-entry risk.
- A production mismatch prevalence derived from the stress suite.
- Generality beyond the Qwen3-ASR model family.
- Novelty of generic low-margin verification or generic batch-invariant
  kernels.
- A universal deadline guarantee outside the frozen workload, model versions,
  fixed terminal batch size, and runtime.
- Singleton equivalence of the terminal fixed-shape canonical path.
- Determinism of the FP16 intermediate margin gate.

## Required wording

- `0/480` natural violations is empirical evidence, not proof.
- `0/1,021` stress false-safe events is stress coverage, not production risk.
- Wall-clock and GPU-normalized speedups must be reported together.
- Exact, risk-limited, and best-effort modes must remain separate.
- Deadline pressure cannot authorize uncertified commits in exact mode.
- `0/240` deadline misses is a measured frozen-workload result, not a
  distribution-free latency guarantee.
- The terminal canonical path is a versioned service contract; it is not
  claimed to reproduce the FP16 singleton terminal trajectory.
- Adaptive extra audits may prioritize diagnostics but cannot be counted in
  the formal e-process unless their inclusion probability is handled
  separately.

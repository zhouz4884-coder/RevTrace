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
- The active-policy deployed wall-clock speedups are 5.99x and 4.83x; the
  corresponding GPU-normalized speedups are 3.00x and 2.42x.
- Five real service runs per active policy produced mean wall speedups of
  6.052x and 4.949x, with zero deadline miss, output/state violation, stale
  commit, or cross-run output/state trace mismatch across the frozen runs.
- The active anytime audits bound canonical state disagreement at 0.480% and
  0.478% with 95% time-uniform confidence under the frozen audit design.
- The flip-rich suite exercises real execution-shape flips without artificial
  logit noise.
- A fixed-probability mixture e-process provides a time-uniform upper bound on
  cumulative unsafe fast-path state entries under arbitrary temporal drift,
  provided the base audit coin is independent and fixed before observing the
  canonical outcome.

## Not established

- Zero deterministic state-entry risk.
- Semantic correctness against an external transcript ground truth; the risk
  contract measures disagreement with the frozen canonical execution.
- A production mismatch prevalence derived from the stress suite.
- Generality beyond the Qwen3-ASR model family.
- Novelty of generic low-margin verification or generic batch-invariant
  kernels.
- A universal deadline guarantee outside the frozen workload, model versions,
  fixed terminal batch size, and runtime.
- Singleton equivalence of the terminal fixed-shape canonical path.
- Determinism of the FP16 intermediate margin gate.
- A c16 deployment guarantee inferred from c64 calibration; the two batch
  shapes are separate populations for this study.
- Direct observation of every selected fast-path state. The
  `selected_*_violations` fields in raw audit records cover only mandatory or
  randomized canonical checks; unaudited disagreement is controlled by the
  time-uniform upper bound rather than counted directly.

## Required wording

- Zero observed verified-selection violations and zero five-run system
  violations are empirical evidence, not deterministic proof.
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
- The c64 calibration failure is retained as a concurrency boundary and does
  not replace the independently seeded c16 validation.
- The frozen 1.7B/c16 v1 audit at `tau=0.05` caught a state error at margin
  `0.0625` and failed its 0.5% budget. It remains a failed result and is used
  only to preregister, not validate, the independent v2 policy.
- The active risk-limited threshold is a model-and-concurrency-specific policy:
  `tau=0.05` for Qwen3-ASR-0.6B/c16 and `tau=0.10` for
  Qwen3-ASR-1.7B/c16. Neither threshold is a deterministic margin certificate
  or a cross-model/cross-concurrency constant.
- Paper tables must label raw `selected_*_violations` as observed violations
  among verified selections, not as the unknown total over unaudited entries.
- The frozen Transformers runtime reports that the shared Qwen2 tokenizer
  configuration does not enable `fix_mistral_regex=True`. Changing that flag
  would migrate the canonical token trajectory, so tokenizer migration is
  outside the frozen Phase 2 comparison.
- A process-group cleanup warning after the diagnostic audit result is written
  is not a serving failure or performance result; it remains an implementation
  hygiene issue.

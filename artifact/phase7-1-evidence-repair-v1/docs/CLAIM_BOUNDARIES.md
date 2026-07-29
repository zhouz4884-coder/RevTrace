# Claim boundaries

## Phase 3A adaptive-control boundary

- A contract fingerprint change invalidates all old evidence and starts a new
  fail-closed epoch.
- Adaptive policy selection is valid only inside the preregistered
  simultaneous confidence envelope; a post-hoc threshold is not allowed.
- Caught real failures are permanent exclusions for every policy whose fast
  path contains the failed margin under the same contract.
- Opportunistic idle audits are excluded from the formal confidence sequence.
- The Phase 3A controller is statistical and does not establish deterministic
  floating-point exactness.

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

## Phase 4 boundaries

- The certified risk-window sequence is a split-sample replay of measured
  audits. Matching c16 performance projections are not a live c16-to-c64
  service transition, and no c64 goodput is claimed.
- Whisper feedback pairs come from 100 disjoint 90-second streams per model;
  no source audio sample is reused across sessions.
- Whisper feedback OFF is the same checkpoint and fixed future audio with only
  the previous-text edge removed. The observed 21-pair causal gate is not a
  production mismatch-prevalence estimate.
- Zero observed Whisper application catastrophes means hallucination-loop
  prevention is not an eligible claim.
- CUDA stream priority is not kernel preemption. The 309.9 ms full-request
  audit quantum fails the 27.5 ms intrusion budget, so Phase 3B remains an
  offline diagnostic until a finer cancellable quantum is implemented.
- Active mining improved targeted pair yield but produced only 8 and 5 pairs
  within the frozen 500-candidate budgets. It does not establish a 50-pair
  population claim.
- Persistent Contamination Mass and TailRAF describe only observed targeted
  pairs; they are not production probabilities or expected production damage.

## Phase 5 boundaries

- The live c16 -> c64 -> c16 controller learned contract-specific thresholds,
  but its split-sample risk certificates are statistical. The adaptive run
  observed rare post-certification output/state disagreements, so it did not
  pass the frozen zero-observed-violation gate and is not an exactness result.
- The independently seeded static-policy run also observed disagreements.
  Its throughput is an independent risk-certified performance reference, not
  a deterministic oracle.
- c64 exceeded the two-second RTX 3090 service region in both adaptive and
  static runs. This is a measured capacity boundary, not a controller bug.
- Whisper protection verifies every feedback-bearing transition with the
  singleton canonical path. It demonstrates finite cross-family protection,
  but its throughput is a performance boundary rather than a second main
  speedup result.
- Whisper Feedback OFF can bypass state-entry certification because generated
  text is not admitted into future model state. Local batched output
  differences may still exist.
- In the eight-cell workload matrix, an unseen c32/Chinese/burst contract
  produced one state-projection violation above the c16 frozen threshold.
  The matrix therefore establishes a contract-fingerprint failure boundary;
  it does not support universal cross-contract threshold transfer.
- Several longer or more concurrent workload cells exceeded the two-second
  deadline while preserving state safety. Deadline/capacity failure and state
  safety are reported separately.
- Live Release-Aware Audit Packing preserved outputs and had zero deadline
  misses, but increased mandatory P99 by 2.35%, above the preregistered 2%
  limit. It is frozen as a NO-GO and is not a paper optimization claim.
- The 72-record consequential state-pair corpus is deduplicated mechanism and
  stress evidence. It is not an estimate of production mismatch prevalence.

## Phase 6 boundaries

- Execution identity is an exact-equality boundary. Execution-shape evidence
  may be compared only through recorded set inclusion; concurrency labels do
  not define a numerical-risk ordering.
- A positive statistical certificate is restored only for an exact contract
  and only after renewal canaries. A covering certificate may provide a
  conservative warm start, but it cannot certify a new population.
- A negative counterexample persists only where its recorded execution
  signature is applicable. A c32/c64 failure is not a global margin floor and
  does not automatically propagate to a different kernel path.
- Quarantine is contract-local. An unseen population is fail closed without
  revoking unrelated certified lanes.
- State commits are fenced by session, contract, and policy epochs. A result
  from an earlier policy or contract cannot cross a mode switch.
- Risk-limited mode is a statistical contract and may observe errors within
  its declared bound. Canonical-authoritative commit means equality to the
  online authoritative draw used for that commit, not mathematical truth or
  repeatability of a later independent canonical draw.
- The c32 Chinese burst repair closes unsafe c16-certificate reuse. It does not
  convert an overloaded c32 workload into an SLO-admissible workload.
- The c64 result is a capacity boundary. Its active concurrency must be
  reshaped, backpressured, or rejected; queued-session waiting is reported
  separately from active-session state-entry latency.
- The fresh c14 point passes the registered 100 ms headroom contract
  (1.413 s measured P99, 1.513 s guarded P99). Its high verification fraction
  is cold-start evidence acquisition and is not a steady-state throughput
  headline.
- Exact return to a cached population is not cross-contract reuse. It still
  requires renewal canaries before the fast path is reopened.
- Zero observed violations in a finite live run remains empirical evidence,
  not a deterministic arithmetic certificate.
- The online controller's statistical bound applies to the measured
  proposer-admission disagreement process. It does not prove bitwise
  repeatability of two independent canonical-runtime executions; replay
  differences are reported separately.

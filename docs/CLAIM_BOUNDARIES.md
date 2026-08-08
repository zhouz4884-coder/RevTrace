# Claim boundaries

## Submission claim set: invariant -> DGFT -> RevTrace

- **Paper invariant.** Generated output may be displayed provisionally, but it
  may not acquire write authority over future feedback state until the active
  execution contract certifies that state transition.
- **Mechanism.** Dual-Granularity Feedback Transactions (DGFT) decouple a
  fine-grained proposal lane from a coarser canonical-authority lane. A
  directional coverage witness determines when the coarse result covers the
  fine state entry; uncovered regions are selectively replayed at fine
  granularity.
- **System.** RevTrace implements DGFT with parent-version binding, atomic
  state installation, stale-descendant invalidation, architecture-specific
  rebase adapters, and fail-closed authority-invariance preflight.
- **Certification layer.** Contract fingerprints, policy epochs,
  pre-outcome audits, and anytime-valid risk bounds remain a named part of the
  system. Risk signals schedule authority work; they never serve as
  deterministic floating-point certificates.

SG certification is the coinciding-granularity special case of DGFT. Proposal
and authority units are identical, the directional-coverage witness
degenerates, and selective fine replay becomes risk-triggered
re-verification. This relation is semantic, not arithmetic: the legacy FP16
singleton SG authority and the FP32 batched DGFT authority are two distinct,
versioned canonical paths. No bitwise identity is claimed between them.

## Quality-contract vocabulary

The paper defines two non-interchangeable quality questions and never pools
their values:

1. **Canonical-reference deviation** asks how far the deployed output is from
   an independent authority reference under the declared contract. Qwen
   reports mixed-unit edit rate against a fresh FP16 singleton reference
   (R10 P95 at most 3.43%; worst session 5.41%).
2. **Unprotected-feedback delta** asks whether protection improves or harms
   task quality relative to the same model with unsafe feedback admitted.
   Whisper reports paired WER delta against unprotected feedback execution;
   all frozen R9.E deltas are negative.

The first quantity is a reference-fidelity contract; the second is an
application-benefit comparison. Neither may be relabeled as the other.

## Certification-evidence scope

- The deepest statistical audit (about 30,000 audited decisions and the
  reported 0.48% anytime-valid upper bound) was collected through the SG
  adapter. It is evidence that the certification layer can be stress-audited,
  not an audit performed inside every DGFT production cell.
- The checkpoint-20, 120-second long-horizon evidence was also collected on
  the SG adapter. DGFT currently contributes fail-closed preflight invariance
  plus exhaustive-trajectory zero transaction-install violations under its
  frozen production contracts.
- The certification layer is adapter-independent by construction, but these
  empirical scopes must remain visible. Adapter independence is not a license
  to transfer a numerical bound between canonical paths or contract digests.
- Finite zero observed violations remain empirical evidence. They are not a
  deterministic arithmetic certificate or a claim of zero population risk.

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

## Final evaluation closure boundaries

- The independent quality result covers deterministic 64-utterance
  LibriSpeech test-clean and AISHELL-1 holdouts. It is not a full-corpus WER
  leaderboard or a production quality-prevalence estimate.
- A degenerate paired bootstrap interval of `[0, 0]` records zero empirical
  error-rate delta on the evaluated holdout. It is not a mathematical
  population-equivalence interval. With 0 terminal mismatches in 64 samples,
  the exact one-sided 95% upper bound is about 4.57% per model-language cell.
- The quality-only risk-limited mode applies a previously certified frozen
  policy to isolate transcript quality. The persistent steady-state experiment
  is the evidence for dynamically learned threshold behavior.
- F5 separately evaluates the deployed Phase-2 authority split: the FP16
  batched proposer and low-margin FP16 singleton authority share GPU 0, while
  every terminal revision uses the real GPU-1 FP16 fixed-shape b16 authority.
  Terminal and nonterminal verification fractions are reported separately.
  The frozen headline thresholds are 0.05 for 0.6B and 0.10 for 1.7B.
- The first steady-state attempt is retained as a mechanism-feedback failure.
  Its replay-audit roots were recorded but not assimilated into the dynamic
  failure floor. The repaired protocol uses a distinct adaptation split and
  an independently seeded validation split in the same live contract epoch.
- Only the first unverified replay mismatch per session is treated as a new
  adaptation root. Later rows on that diverged replay trajectory are cascade
  descendants, not independent counterexamples.
- In steady validation, all three replay roots had already used authoritative
  verification. They establish FP16 replay non-repeatability, not an
  unverified fast-path state write or an online selection-authority violation.
- The steady verification fraction is 9.05%, but its P99 is 1.766 s versus
  1.468 s during cold certification. The lower verification rate improves
  goodput and energy, not every latency quantile.
- c14 capacity rows have risk, SLO, and energy evidence but no same-task
  all-canonical normalized-goodput baseline. They are not plotted as
  end-to-end Pareto speedup points.
- F6 headline energy is paired against the exact contract-matched
  all-canonical workload. The repaired baseline executes each terminal only
  once through the fixed-shape authority; it does not also time a discarded
  singleton. RevTrace uses 19.66% and 26.08% of matched all-canonical
  J/audio-s for 0.6B and 1.7B, respectively. This is a measured two-GPU
  energy comparison, not a claim about other hardware or arrival processes.
- `comparison_eligible`, `safe_frontier_eligible`, and
  `energy_frontier_eligible` are separate fields. A point may be shown as an
  infeasible comparison without entering the safe frontier, and only a
  matched all-canonical energy pair may enter the energy frontier.
- Phase 2 FP16-b16, Phase 6 FP32-b16, Phase 7 FP16-b16, and Phase 7.1
  FP16-b14 are distinct versioned canonical contracts and are never pooled.
- `batch_invariant_requested=true` records a runtime request, not verified
  end-to-end audio-to-token invariance. Every frozen contract therefore also
  records `end_to_end_invariance_verified=false`.
- The reporting name `fp32_fixed_contract` replaces
  `fp32_reproducible`. Repeatability evidence for that contract comes from
  the separate 720/720 probe, not from the quality run itself.
- Periodic post-stage canonical replay is excluded from service timing.
  Replay disagreements and online selection-authority violations remain
  separate evidence categories.
- In the three independent F7 steady seeds, only two have zero deadline
  misses. Seed 1 has two synchronized rounds above 2 seconds, which appear as
  28 event-level misses because all 14 sessions share each round latency
  (P99 2.028 s). This is retained as cross-seed tail variance; it is not
  presented as an all-seed SLO pass or as a state-safety failure.
- The follow-up tail-robust closure does not rehabilitate c14. An instrumented
  same-seed run has no 2-second miss but still has three rounds above the
  preregistered 1.9-second guard; all three serialize proposer and selective
  canonical work.
- The accepted c12 capacity contract is scoped to Qwen3-ASR-0.6B, FP16,
  English, 30-second synchronized sessions, two RTX 3090 GPUs, the frozen
  runtime digest, and `tau=0.0625`. It is supported by five independent
  processes, not by duplicated per-session event counts.
- The c12 maximum seed P99 is 1.877 s and its one-sided cross-seed 95% upper
  bound is 1.868 s. The separately computed terminal and nonterminal
  seed-P99 upper bounds are 1.271 s and 1.748 s. The risk upper bound is
  0.499706%; this remains a statistical content contract rather than
  deterministic inference.
- The original cyclic/rolled 120-second profile (20/60 miss rounds and
  P99=5.295 s in the final age bucket) is superseded for causal attribution.
  It remains historical failure evidence, but its magnitude mixed real
  long-history work with repaired input-construction, authority-shape, and
  timing confounders.
- Under the repaired natural-input protocol, continuous long-horizon service
  still fails the two-second SLO (P99=2.393 s and 8/60 miss rounds). This is the
  causal evidence for a real long-history capacity problem.
- The independently confirmed Checkpoint-and-Rebase run restores the deployed
  two-second SLO (P99=1.937 s and 0/60 miss rounds), with a dynamically learned
  threshold of 0.031251, zero observed output/state/authority violations, and
  certificate/replay one-sided 95% upper bounds of 0.4997%/0.4152%.
- Checkpoint-and-Rebase does not pass the stricter preregistered 1.9-second
  admission guard: the final age bucket is 1.937 s, 0.037 s above the guard.
  This 100 ms headroom failure is retained and is not repaired by further seed
  selection.
- The 1.937 s peak is one nonterminal 110-second round: the proposer takes
  0.607 s and the current worker serializes two required low-margin singleton
  canonical checks for 1.283 s. There is no cross-round verifier backlog,
  checkpoint boundary, or thermal-throttling signature. This identifies a
  selective-verification burst, not renewed full-history growth.
- The paired quality gate contains four sessions per language. Its WER/CER
  deltas (0.155/0.550 percentage points) and zero catastrophic outliers support
  the mechanism death gate, not population-level quality equivalence.
- Version and epoch fencing linearize online state mutations. Later
  canonical-replay disagreements are repeatability evidence and do not
  retroactively change which online result held selection authority.

## Whisper W0-W7 cross-family closure

- The full paper remains a method-driven state-consistency systems paper.
  Whisper is an independent feedback architecture and scale closure, not a
  new paper identity or a model-specific optimization claim.
- Whisper's state-entry projection is the start-of-previous marker plus the
  bounded raw generated-token suffix of all confirmed prior segments admitted
  to the next window.  This follows long-form `condition_on_prev_tokens`
  semantics: it neither retains only the immediately preceding segment nor
  decodes and re-tokenizes history.  LocalAgreement-2 protects confirmed
  display text; it does not certify equality of that future prompt state.
- The raw Whisper history budget is derived from the checkpoint's
  `max_target_positions // 2` (224 total prompt tokens for base.en/small.en,
  including the start-of-previous marker), rather than a hand-set context
  length.
- The W-suite canonical path is the same distinct-prompt executor at FP16 and
  batch size one.  Dtype, model weights, decoder, audio, and hardware are held
  fixed within causal system comparisons.
- Margin is a pre-outcome admission signal, not a deterministic arithmetic
  certificate.  Policy selection uses calibration-only evidence, and the
  paper-facing content guarantee comes from independent fixed-probability
  audits and a time-uniform upper bound.
- Policy thresholds may change only at a versioned policy epoch.  They are
  frozen inside each performance comparison, so dynamic control is not
  confounded with seed-specific post-outcome tuning.
- Independent audits and repeat-controlled W5 replays showed that one scalar
  margin is not a sufficient contract: later feedback states and high
  prior-prompt loads admitted higher-margin errors after earlier failure floors
  had been covered.  The renewed policy is therefore a contextual
  margin-by-state-age-and-prompt-load frontier.  Caught rows only select the
  next epoch; the final certificate comes from a new independent seed.
- A terminal transcript has no successor previous-text state.  The final W5
  contract therefore does not claim terminal singleton exactness and does not
  spend state-authority work on terminal revisions.  Terminal batch quality is
  governed by the disjoint paired W6 gate against a 96-token singleton
  reference, including mean and bootstrap-upper WER deltas, per-split bounds,
  catastrophic outliers, and provisional UX.  A W6 failure blocks the strong
  W7 decision; it may not be hidden by the state-entry result.
- The W5 RevTrace path uses deferred state authority: a low-margin batched
  transcript may be shown provisionally, but its raw tokens do not enter the
  next-window prompt. The queued FP16 singleton canonical result selects the
  authoritative next prompt state. This is a state-authority intervention,
  not LocalAgreement display confirmation and not an unverified holdback.
- Prompt state is capacity-safely rebased before the declared 96-token
  next-segment budget would exceed the checkpoint-derived 224-token history
  bound.  Rebase only discards feedback authority; it never admits an
  uncertified token.  Its paired quality cost is measured in W6.
- Paper-facing state-entry P99 and deadline misses include every nonterminal
  transition that updates feedback state, including deferred risk-authority
  transitions.  Provisional display latency is measured from readiness to the
  completion of the batch proposal and is reported independently.  The faster
  display clock cannot substitute for stable state-entry latency.  Terminal
  output has no state-entry edge and is evaluated by W6 quality rather than
  being relabeled as a state transition.
- W4 randomized canonical audits run only as a shadow side channel and never
  replace the proposal in live feedback state. Earlier protocol-development
  audits that canonicalized audited or low-margin rows are excluded because
  the audit itself changed the state distribution being certified.
- The final W4 contracts use 180-second sessions so their audit distribution
  includes the post-checkpoint state regime exercised by long W5 cells.
- W4 policy calibration applies the same declared-budget capacity rebase
  before each decode. Long calibration runs that reached the raw 224-token
  cap without this pre-decode rebase are excluded as protocol-development
  artifacts.
- Every formal W5 RevTrace fast-path state write is exhaustively replayed
  against the same-state FP16 singleton canonical after wall-clock and energy
  timing. A first mismatch is followed by a same-input repeated-singleton
  control: only a mismatch against a repeat-stable canonical result is
  attributed to the fast path, while a repeat-unstable result is reported as
  finite-precision ambiguity. This validation cost is excluded from serving
  performance by construction.
- Production W5 cells offer exactly their certified active concurrency
  (16 sessions for c16 and 8 sessions for c8). The separate B1 boundary is the
  only cell that offers 32 sessions and reshapes them to active c16; the
  superseded sessions=32 production epoch is excluded because it measured
  overload queueing rather than the registered production contract.
- The initial Poisson implementation only permuted ready sessions and is
  excluded from W5.  Frozen W5 evidence uses actual initial session release
  times and includes queue wait in event latency.
- The small.en energy result must sample the GPU on which the executor
  actually runs.  Any pre-repair GPU-0-hard-coded energy smoke is excluded.
- Risk evidence is not pooled across base.en and small.en or across c8 and c16
  execution fingerprints.
- The offered c32 burst boundary is either independently certified or
  explicitly reshaped to the certified c16 contract.  It never silently uses
  a c16 certificate at active c32.
- The final base.en/c8 r5 policy passes two fixed, independent 180-second
  state-risk certificates (60,032 eligible entries, 1,235 pre-outcome
  canonical audits, zero caught errors, maximum time-uniform 95% upper risk
  0.4798%).  This does not make c8 a production-performance success.  Across
  dual-GPU lane counts 1/2/4 and corrected single-GPU colocation, no topology
  passes the complete wall, GPU-normalized, display-SLO, latency, verification
  and energy gate.  The paper must report c8 as a low-load capacity boundary,
  not pool it with successful c16 evidence.
- Resource accounting counts distinct physical CUDA devices rather than
  logical proposer/verifier roles.  The pre-repair colocated result that
  divided GPU-normalized speedup by two and sampled one GPU's power twice is
  excluded.  Dual-GPU measurements are unaffected by this repair.

## Independent V100 V1--V5 scale-out boundary

- The V100 study is a separate RHEL 7.6, 8xTesla-V100-32GB,
  Transformers-eager contract. Its absolute timings and speedups are never
  pooled with RTX3090/vLLM measurements.
- V3 is single-node replica scale-out, not model parallelism and not
  multi-node scaling. The p4a4 c64 cells are the largest measured points that
  satisfy the 2 s display SLO for both Qwen sizes; c128 is retained as an
  overload boundary.
- Nominal scale efficiency compares p4a4 against p1a1 at the same c64 load and
  normalizes by the 4x physical-GPU increase. The 100.7% 1.7B value is not a
  statistical claim of superlinear scaling.
- Batched repeatability and batch-to-singleton equivalence are distinct.
  V1 observes zero repeat mismatches but nonzero batch-to-singleton
  mismatches in both FP16 and FP32; FP32 is not treated as an unconditional
  arithmetic certificate on V100.
- V2 SG final edit is measured against the independent FP16 singleton
  reference. The 1.7B Coarse/Hybrid P95 edit boundary is 3.18% and remains
  visible wherever their speedup is reported.
- V4 authority/proposer ratios are bottleneck-attribution measurements.
  Increasing the granularity ratio amortizes FP32 authority work but increases
  segment-commit latency; low provisional-display P99 does not relabel that
  commit latency.
- V5 repeats only the frozen headline and allocation-sensitivity cells three
  times. Report medians and min--max ranges, not significance claims. At
  p4a4-c64, display P99 is 1.089/1.394 s while six-second certified-segment
  commit P99 is 3.080/4.890 s; the 2 s SLO applies only to display. The p3a5
  result is a cost-model sensitivity, not a new scheduler contribution.
- V5 observes no transaction-install or uncertified-ancestry violation across
  30 completed cells. This is a finite exhaustive-trace observation, not a
  probability-zero or unbounded-queue guarantee.
- Zero transaction-install, ancestry, and directional-omission violations are
  exhaustive observations over the finite 84-cell matrix, not a deterministic
  zero-risk or population failure-rate claim.

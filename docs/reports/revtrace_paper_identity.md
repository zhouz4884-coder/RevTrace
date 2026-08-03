# RevTrace paper identity: DGFT-primary state-certified serving

## Frozen paper-level thesis

RevTrace is not a Whisper optimization, a dtype trick, or a collection of
batching patches. Its paper identity has four explicit levels:

> **state-entry invariant (paper thesis) -> DGFT (mechanism) -> RevTrace
> runtime + certification layer (system).**

The invariant is:

> A numerically plausible output must not acquire write authority over future
> model state until the execution contract's risk and authority conditions
> certify that transition.

DGFT, or **Dual-Granularity Feedback Transactions**, is the mechanism that
separates fast fine-grained proposals from a coarser canonical authority and
selectively replays only fine regions not covered by the coarse authority.
RevTrace is the runtime that implements DGFT with versioned state transactions
and a visible, anytime-valid certification layer.

Ordinary batching, dtype selection, queueing, and model-specific decoding
adapters are implementation substrate.  They expose the performance
opportunity but are not the paper's novelty.

## Contribution taxonomy

| Layer | Paper contribution | Evidence required |
|---|---|---|
| Invariant / semantics | State-entry projection and committed trace-equivalence | Qwen rollback state and Whisper previous-token state |
| DGFT mechanism | Fine proposal, coarse authority, directional coverage witness, selective fine replay | SG/coarse/hybrid same-workload ablation and cross-family adapters |
| Certification layer | Contract-scoped, epoch-versioned dynamic risk frontier with anytime-valid bounds | Calibration-only policy selection plus independent pre-outcome audits |
| RevTrace runtime | Versioned CAS commit, holdback, checkpoint/rebase, stale-descendant invalidation and fail-closed preflight | Same-executor live serving, fault/age tests, and exhaustive trace audit |
| Engineering substrate | FP16 execution, batching, queues and adapters | Reported for reproducibility; never used as a novelty claim |

The headline speedup is acceptable evidence only when the method changes the
amount and timing of canonical authority work while weights, dtype, decoder,
hardware, audio and arrivals remain fixed.  A kernel-only or dtype-only gain
is excluded from the method headline.

## Mechanism contributions

1. **State-entry invariant and projection.** Each architecture declares the minimal
   projection of generated output that can influence a future transition.
   Qwen3-ASR writes a rollback/retokenized revision prefix; Whisper writes a
   start-of-previous marker plus the bounded raw generated-token suffix of
   accumulated confirmed prior segments. Display-only suffixes and terminal
   text have no future-state authority.
2. **DGFT.** Fine proposal units execute on the high-throughput path; a
   canonical authority operates on a coarser unit. A directional coverage
   witness tests whether the authoritative coarse result covers the fine
   state entries. RevTrace selectively replays uncovered fine regions rather
   than paying singleton authority for every proposal.
3. **Contract-scoped adaptive risk control.** A contract fingerprint binds
   model, precision, runtime, kernels, concurrency class, chunk policy, and
   canonical path.  Pre-outcome randomized audits and time-uniform confidence
   sequences restrict fast-path state risk.  Admission uses a learned
   margin-by-feedback-state-age-and-load frontier, rather than one global
   hand-written threshold.  Adaptation-only failure roots may select a new policy epoch
   but are excluded from its independent certificate; the resulting policy is
   frozen within each causal performance comparison.
4. **Versioned revision transactions.** Session, contract, policy, and state
   versions fence every commit.  Holdback, checkpoint/rebase, quarantine, and
   stale-result rejection ensure that an unqualified result may be displayed
   provisionally but cannot silently become a parent state.

## Precise SG relationship and canonical-path boundary

Same-granularity (SG) certification is the degenerate DGFT configuration in
which proposal and authority granularities coincide. The directional coverage
witness then degenerates, and selective fine replay reduces to
risk-triggered re-verification of the proposal unit. This is why SG is a clean
mechanism ablation rather than a second unrelated method.

The relation does **not** imply that the SG and coarse-DGFT arithmetic paths
are identical. The SG cells use an FP16 singleton authority. R10 coarse and
hybrid DGFT use a versioned FP32 batched authority that passes its own
batch-repeat and batch-vs-singleton preflight. They are distinct canonical
paths, and the manuscript does not claim bitwise equality between them.

## Unified quality contract

Quality has a common schema but family-specific estimands:

- **Canonical-reference deviation:** Qwen reports mixed-unit edit rate against
  an independent fresh FP16 singleton reference. The frozen R10 cells have
  P95 edit rate at most 3.43% and worst-session edit rate 5.41%.
- **Unprotected-feedback delta:** Whisper reports paired WER delta against the
  same model under unprotected feedback execution. All frozen R9.E deltas are
  negative, which answers an application-benefit question rather than a
  canonical-fidelity question.

These metrics appear under one quality contract but are never numerically
pooled or described as measuring the same quantity.

## Certification evidence boundary

The certification layer is adapter-independent, but the strongest empirical
stress evidence is not evenly distributed across adapters. The roughly 30k
audit decisions and 0.48% anytime-valid upper bound, and the checkpoint-20
120-second long-horizon experiment, were collected on the SG adapter. DGFT
production cells instead carry fail-closed authority-invariance preflight and
exhaustive-trajectory zero transaction-install violations. The paper states
this division explicitly; it does not transfer an SG numerical certificate to
a different DGFT canonical path or contract digest.

## Why the system gains are method-driven

The speedup is created by an authority split, not by changing the task:

- all-canonical execution grants every transition authoritative computation
  and is safe but expensive;
- unprotected batching is fast but allows batch-sensitive choices to enter
  future feedback state;
- fixed synchronous verification pays canonical cost on a hand-written
  region and produces avoidable tail latency;
- LocalAgreement protects display stability, not future prompt-state write
  authority;
- RevTrace admits certified fast transitions and spends canonical work only
  where the risk contract, checkpoints, or version protocol require it.

Same-executor ablations hold weights, dtype, decoding, hardware, audio, and
arrival trace fixed.  Therefore the difference between all-canonical,
unprotected batch, fixed-margin verification, LocalAgreement, feedback-off,
and RevTrace is the state-authority method rather than an unrelated code path.

Formal performance rows use two disjoint evidence intervals. Wall-clock,
energy and SLO metrics end when serving ends. Every fast-path state write from
that measured trace is then replayed against the same-state singleton
canonical. A first mismatch receives a same-input repeated-singleton control;
only disagreement against a repeat-stable canonical result is attributed to
the fast path. Replay cost is not presented as serving work. This prevents
either a shadow audit or a validation oracle from improving the timed state
trajectory while separating mechanism failure from canonical
non-repeatability.

Production cells offer exactly their certified active concurrency. The
separate overload boundary is the only cell that offers 32 sessions and
reshapes them to active c16, so queueing beyond the registered production
contract cannot contaminate the production P99.

## Role of Whisper W0-W7

Whisper is an independent architecture and scale closure.  Its purpose is to
test whether the same control plane works when the state projection changes
from Qwen rollback state to previous-text prompt state.  It must not redefine
the paper as a Whisper paper.

The positive Whisper serving path is a control-plane intervention:
low-risk proposals may enter the architecture-specific projection,
low-margin proposals remain provisional until a deferred singleton authority
selects the next prompt state, and terminal proposals are governed by a
separate paired output-quality contract because they have no successor
feedback edge. Prompt history is capacity-safely rebased before the declared
decoder budget would overflow. Active state-entry latency includes every
nonterminal transition that actually acquires feedback-state authority.
Provisional display latency and paired terminal/whole-session WER remain
separate evidence; neither can substitute for state-entry correctness.

The cross-family claim is earned only if base.en and small.en independently
pass the risk, state, performance, energy, quality, and UX gates.  A failure
is retained as an applicability boundary and is not hidden by pooling with
Qwen results.

## Claim boundaries

- Margin is a scheduling signal, not a deterministic floating-point
  certificate.
- Zero observed failures is paired with a statistical upper bound.
- Feedback-OFF is a physical upper bound, not a functionally equivalent
  baseline.
- FP16/FP32 changes define versioned execution contracts; they are not
  silently pooled.
- The experiment measures mechanism safety and serving value, not the
  population prevalence of numerical divergence.

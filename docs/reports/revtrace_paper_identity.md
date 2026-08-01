# RevTrace paper identity and causal attribution

## Frozen paper-level thesis

RevTrace is not a Whisper optimization and is not a collection of batching
patches.  It is a state-consistency method for feedback-driven generative
serving:

> A numerically plausible output must not acquire write authority over future
> model state until the execution contract's risk and authority conditions
> permit that transition.

Ordinary batching, dtype selection, queueing, and model-specific decoding
adapters are implementation substrate.  They expose the performance
opportunity but are not the paper's novelty.

## Contribution taxonomy

| Layer | Paper contribution | Evidence required |
|---|---|---|
| Algorithm / semantics | State-entry projection and trace-equivalence argument | Qwen rollback state and Whisper previous-token state |
| Statistical control | Contract-scoped, epoch-versioned dynamic risk frontier | Calibration-only selection plus independent time-uniform audits |
| System architecture | Canonical authority split, transactional commit, holdback, checkpoint/rebase and stale-result rejection | Same-executor live serving and fault/age tests |
| Engineering substrate | FP16 execution, batching, queues and adapters | Reported for reproducibility; never used as a novelty claim |

The headline speedup is acceptable evidence only when the method changes the
amount and timing of canonical authority work while weights, dtype, decoder,
hardware, audio and arrivals remain fixed.  A kernel-only or dtype-only gain
is excluded from the method headline.

## Method contributions

1. **State-entry projection.**  Each architecture declares the minimal
   projection of generated output that can influence a future transition.
   Qwen3-ASR writes a rollback/retokenized revision prefix; Whisper writes a
   start-of-previous marker plus the bounded raw generated-token suffix of
   accumulated confirmed prior segments. Display-only suffixes and terminal
   text have no future-state authority.
2. **Contract-scoped adaptive risk control.**  A contract fingerprint binds
   model, precision, runtime, kernels, concurrency class, chunk policy, and
   canonical path.  Pre-outcome randomized audits and time-uniform confidence
   sequences restrict fast-path state risk.  Admission uses a learned
   margin-by-feedback-state-age-and-load frontier, rather than one global
   hand-written threshold.  Adaptation-only failure roots may select a new policy epoch
   but are excluded from its independent certificate; the resulting policy is
   frozen within each causal performance comparison.
3. **Versioned revision transactions.**  Session, contract, policy, and state
   versions fence every commit.  Holdback, checkpoint/rebase, quarantine, and
   stale-result rejection ensure that an unqualified result may be displayed
   provisionally but cannot silently become a parent state.

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

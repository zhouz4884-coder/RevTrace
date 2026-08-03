# RevTrace paper blueprint: DGFT-primary narrative (FGCS first)

## Decision

`BLUEPRINT_DGFT_PRIMARY_SINGLE_MECHANISM`

The paper freezes to one mechanism, one system, one thesis:

- **Mechanism:** DGFT (Dual-Granularity Feedback Transactions).
- **System:** RevTrace, the state-certifying transaction runtime that DGFT
  commits through.
- **Thesis:** a numerically plausible output must not acquire write authority
  over future model state until the execution contract's risk and authority
  conditions permit.
- **RevOCC:** not a named contribution in the manuscript. It appears only as
  the same-granularity certification configuration (SG-DGFT) in the mechanism
  ablation, carrying the legacy Qwen strong baseline.

This matches the R10 closure report's own recommendation: leading with the
common state-entry contract avoids fragmenting the paper into two co-equal
systems.

## Why DGFT-primary is the right freeze

1. One mechanism now spans two architecture families and five checkpoints:
   Qwen3-ASR 0.6B/1.7B (R10) and Whisper tiny/base/small (R9.E). Two parallel
   mechanisms would read as component stacking; one abstraction with
   architecture-specific evidence adapters reads as a method-driven systems
   paper.
2. The DGFT Qwen headline is stronger than the legacy RevOCC headline
   (6.88x/6.06x wall vs 5.99x/4.83x) while using a stronger authority regime
   (FP32 concurrency-invariant authority with fail-closed batch=singleton
   preflight), so the demotion loses no headline strength.
3. The SG/Coarse/Hybrid ladder is a genuine alternatives axis, which top
   systems venues explicitly reward ("weigh alternatives").

## Required refinements to the proposed framing

These are writing-strategy opinions, not repository facts:

1. Keep the certification layer visible. DGFT is the mechanism, but the
   anytime-valid risk contract and versioned transaction semantics are what
   separate this work from speculative-execution-with-rollback systems. If the
   statistical certification disappears from the narrative, reviewers will
   classify the paper as another speculative-serving paper.
2. The special-case relation must be written precisely: SG certification is
   DGFT with coinciding proposal and authority granularities, where the
   directional coverage witness degenerates and selective replay degenerates
   into risk-triggered re-verification. Do not claim bitwise identity between
   the FP16-singleton SG authority and the FP32-batch DGFT authority; they are
   different canonical paths.
3. Do not mix contracts in one table. R10 uses 30-second bilingual sessions at
   c16; the legacy Phase 3A numbers come from a different frozen contract. The
   ablation table must either carry contract labels or be made ceteris paribus
   (see gap G1 below).
4. Quality vocabulary must be unified once but reported by family. Qwen uses
   certified-output deviation from an independent canonical reference (mixed-
   unit edit rate). Whisper uses paired WER delta against unprotected feedback
   execution. They answer different questions and must not be pooled. Any
   auxiliary Whisper singleton-reference result is labeled separately rather
   than used to blur this primary family-level distinction.

## Pre-submission evidence closure

- **G1 (completed):** SG cells were rerun for 0.6B/1.7B under the R10 workload
  contract (30 s, c16, bilingual, synchronous arrival, FP16 2-second
  singleton authority). SG reaches 5.10x/4.68x wall speedup,
  2.55x/2.34x GPU-normalized speedup, and 69.1%/66.1% energy reduction with
  zero observed output, state, or stale-commit violations across 240 events
  per model. Both SG cells retain a terminal-burst tail boundary: 3.33%/4.17%
  of state entries exceed two seconds (P99 2.735/2.964 s). Coarse-DGFT reaches
  6.88x/6.06x wall speedup and 0.826/1.018 s provisional-display P99 on the
  same audio workload; directly measured service throughput is 1.385x/1.276x
  SG. The ablation is now ceteris paribus, while latency
  columns remain path-semantics-specific.
- **G2 (explicitly bounded):** the deepest statistical certification (30,025/30,155
  randomized audits; anytime UCB 0.480%/0.478%) and the long-horizon evidence
  (checkpoint-20, 120 s) were collected on the SG path, not the DGFT path.
  Write this honestly: the certification layer is adapter-agnostic and was
  stress-audited on the SG adapter; DGFT cells carry preflight invariance plus
  exhaustive-trace zero violations. No SG numerical certificate is transferred
  to an FP32 DGFT canonical path.
- **G3 (completed):** `docs/CLAIM_BOUNDARIES.md` and
  `docs/reports/revtrace_paper_identity.md` now carry the DGFT-primary claim
  set. The superseded R9 preview reruns are explicitly ignored; the frozen
  online-closure matrix remains tracked under
  `results/r9_dgft/service/online_closure_matrix/`.

## Title candidates

1. RevTrace: Dual-Granularity Feedback Transactions for State-Certified
   Revision-Generative Serving
2. Certified State: Risk-Limited Feedback Transactions for Batched
   Revision-Generative Inference
3. When Batching Rewrites the Future: State-Certified Serving for
   Revision-Generative Models

Title 1 is the venue-safe choice: system name + mechanism + problem.

## Abstract skeleton (6-8 sentences, contribution summary not contents list)

1. Problem sentence: revision-generative streaming models feed generated
   output back into future state; low-precision batching can flip a local
   decision, and feedback turns the flip into a persistent trajectory change.
2. Scope sentence: ordinary serving metrics (throughput, latency, energy)
   cannot see this because they assume outputs are terminal.
3. Idea sentence: we introduce DGFT, which separates a fast fine-grained
   proposer from a slower coarse canonical authority and commits only
   state entries whose directional coverage, risk evidence, and parent version
   validate.
4. System sentence: RevTrace implements DGFT as a transaction runtime with
   versioned commits, stale rejection, fail-closed preflight invariance, and
   anytime-valid risk-limiting certificates.
5. Results sentence A (Qwen): 6.88x wall / 3.44x GPU-normalized / 59.8%
   energy reduction on Qwen3-ASR-0.6B, 6.06x/3.03x/51.0% on 1.7B, zero
   transaction-install violations, FP32 authority invariance preflight passed.
6. Results sentence B (Whisper): 16/16 real two-GPU service cells across
   Whisper tiny/base/small (2.841x median wall, 31.13% energy reduction,
   1,048 certificates, zero violations), with certified transcripts improving
   WER by 8-25 percentage points over unprotected feedback execution.
7. Boundary sentence: certification is empirical and contract-scoped; risk
   signals schedule verification but never authorize state installation.

## Contribution spine (four bullets, in order)

1. The first characterization of feedback-state contamination
   (Numerical State Exposure) in revision-generative serving, with causal
   evidence that batching-created differences propagate through feedback
   (8/8 pairs propagate with feedback on, 0/8 with feedback off; RAF up to
   153).
2. DGFT: a dual-granularity certification mechanism in which risk signals
   schedule verification but never authorize state installation; SG
   certification appears as the coinciding-granularity special case.
3. RevTrace: a transaction runtime (versioned CAS commit, stale-descendant
   invalidation, fail-closed preflight invariance, architecture-specific
   rebase adapters) plus stratified anytime-valid risk-limiting certification.
4. Cross-family evaluation: five checkpoints, two architecture families, zero
   per-checkpoint retuning; speedup, energy, tail, quality, and safety
   evidence with disclosed capacity boundaries.

## Section-to-evidence map

### 1 Introduction
Motivating example from Phase 4B (Whisper feedback-on vs feedback-off causal
intervention) plus one RAF-153 trace. Contributions list above. Results teaser
table: one row per family with headline wall speedup, energy, violations,
quality. Style model: vLLM/SOSP'23 opens with one named inefficiency and one
named idea; do the same — name the problem (state pollution) and the idea
(dual-granularity feedback transactions) within the first page.

### 2 Background and motivation
Revision-generative models and feedback state (Qwen rollback prefix; Whisper
condition_on_prev_tokens). Batching non-determinism sources. Phase 0/1/2
evidence hierarchy: natural traces vs stress tests vs deterministic guarantees
are distinct tiers and must stay separated. Use the three failure modes as the
subsection spine: numerical divergence, context starvation after safe erasure,
granularity insufficiency — each later maps to a DGFT component.

### 3 Design: DGFT and RevTrace
3.1 State-entry invariant (thesis statement, contract grammar).
3.2 DGFT: fine lane, coarse authority, directional coverage witness (Latin +
CJK units), risk evidence, selective fine replay, degenerate SG case.
3.3 RevTrace runtime: parent-version binding, certificate consumption, stale
invalidation, rollback/rebase adapters, fail-closed preflight invariance
(R10 FP32 batch-repeat + batch-vs-singleton audit, excluded from service
timing by design and recorded explicitly).
3.4 Certification modes: deterministic / risk-limited / best-effort; e-value
and time-uniform bounds; why risk signals are never certificates.

### 4 Implementation
Adapters per family, FP32 authority with 4,096-token bound, online causal
arrival scheduling (R9.E), two RTX 3090s. Keep short; cite artifacts.

### 5 Evaluation
- Q1 performance: R10 four-cell Qwen matrix (6.88/5.19/6.06/3.92x wall) and
  R9.E sixteen-cell Whisper matrix (2.841x median wall, 1.421x GPU-normalized,
  31.13% energy). Per-contract baselines only; never cross-contract.
- Q2 quality: Qwen edit-rate contract (P95 <= 3.43%, worst 5.41%, exact
  sessions per mode) and Whisper paired-WER contract (all negative deltas,
  untouched third confirmation). State which reference each column uses.
- Q3 safety: zero transaction-install violations across 320 Qwen events and
  1,048 Whisper certificates; preflight invariance; SG-path anytime audits
  0.480%/0.478% labeled as certification-layer evidence; rule-of-three bounds
  where applicable.
- Q4 efficiency: R10 energy reductions 33.2-59.8%; legacy matched-energy F6
  (5.40 vs 27.45 J/audio-s) as SG-path companion point; Whisper 31.13%.
- Q5 mechanism ablation: the completed same-workload SG / Coarse-DGFT /
  Hybrid-DGFT ladder, fine-replay fraction, authority/proposer ratio, and the
  SG terminal-burst tail boundary; rejected alternatives include FP16
  singleton coarse authority (1.73x/-11.5% energy), the per-row CUDA
  synchronization defect, and structural-warning replay storms.
- Q6 generality: five checkpoints, zero-shot tiny/small transfer, Voxtral
  append-only boundary.
- Q7 tails and robustness: display P99 across all cells (<=1.492 s Whisper,
  <=1.018 s Qwen R10); commit P99 explained as segment-granularity
  certification latency, not display latency; SG-path checkpoint-20 120 s
  evidence labeled by path.

### 6 Discussion and boundaries
Virtual arrival streams vs real GPU time/energy; two execution structures
explain the Qwen/Whisper speedup gap; FP32 authority is a canonical path, not
a bitwise FP16 repair; zero observed violations is exhaustive-trace evidence,
not an iid rate or a floating-point exactness certificate; c8 low-load
capacity boundary disclosed.

### 7 Related work
LLM serving systems (vLLM/PagedAttention, Sarathi-Serve, DistServe, SGLang,
Llumnix); speculative execution and verification (speculative decoding,
BIO/TBIK, LLM-42 adaptations); inference non-determinism (2025 industry
attention makes the problem timely); OCC lineage (Kung-Robinson) as analogy
only; anytime-valid statistics (e-values, confidence sequences).

### 8 Conclusion
Thesis restated, two-family evidence, boundary sentence, artifact pointer.

## What to cut or compress

Phase 3B VOI, 4C SlackGuard, 4D mining: one paragraph or appendix only.
Phase 5/6/7: compress into controller-adaptation and reviewer-defense
evidence; do not give them sections. The manuscript must not read as a phase
log; organize by claim, never by chronology.

## Terminology freeze

DGFT, RevTrace, state-entry invariant, directional coverage witness, canonical
authority, fine replay, SG certification (same-granularity special case).
Do not print "RevOCC" in the manuscript; keep it in configs/artifacts only.
Do not print "EFSC" either unless a reviewer asks for the evolution story —
the failed-then-repaired trajectory is better told in one Discussion
paragraph as lessons learned.

## Style lessons applied (from top-venue practice)

- One named problem, one named idea, stated within the first page
  (vLLM/SOSP'23 pattern).
- Quantify the problem before proposing the solution (motivation section with
  measured propagation, not assertion).
- The abstract summarizes contributions, not contents; premises and outcomes
  in plain sentences.
- Evaluation weighs alternatives (SG/Coarse/Hybrid ladder) and reports what
  failed (singleton authority economics, c8 boundary) — disclosed negatives
  are credibility, not weakness.
- Real-system statement up front: real two-GPU wall-clock and NVML energy;
  arrival streams are causal virtual time; say so once, precisely.

## Auditable sources

- `docs/reports/r10_qwen_cross_adapter.md`
- `results/r10_qwen_cross_adapter/summary.json`
- `docs/reports/r9e_online_submission_closure.md`
- `results/r9_dgft/FINAL_REPORT_ONLINE.json`
- `docs/reports/phase_r9_final_report.md`
- `docs/reports/model_scale_generality_audit.md`
- `results/final_closure/REPORT.md`
- `artifact/checkpoint20-submission-closure-v2/README.md`

# RevTrace paper blueprint: DGFT-primary narrative (FGCS first)

## Decision

`BLUEPRINT_DGFT_PRIMARY_SINGLE_MECHANISM`

> **Structure note (2026-08-03):** the section structure, page budget,
> figure/table plans, and drafting order in this document are superseded by
> `revtrace_paper_outline_v2.md` (`OUTLINE_V2_THEORY_GUIDED`). This blueprint
> remains the evidence map and claim-boundary reference.

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
   ablation table is now ceteris paribus (G1 closed); latency columns remain
   path-semantics-specific and are never pooled across scopes.
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
2. RevTrace: Dual-Granularity Feedback Transactions for State-Certified
   Streaming ASR (conservative variant: all evidence is ASR; keeps the title
   honest about the validated scope while leaving room for the general framing
   inside the paper)
3. Certified State: Risk-Limited Feedback Transactions for Batched
   Revision-Generative Inference

Title 1 is the venue-safe choice: system name + mechanism + problem. If title 1
is kept, the abstract's first sentence must scope the evidence explicitly
("We study revision-generative streaming ASR models"), so the general title is
never read as a validated claim over text LLMs or other modalities.

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

1. Problem characterization of feedback-state contamination
   (Numerical State Exposure) in revision-generative serving, with causal
   evidence that batching-created differences propagate through feedback:
   among 21 distinct legal singleton-batch state pairs, 8 propagated to later
   revisions with feedback enabled while none propagated when the feedback
   edge was removed; RAF reaches 153 on the persistent pairs. Do not claim
   "first" without a completed novelty search.
2. DGFT: a dual-granularity certification mechanism in which risk signals
   schedule verification but never authorize state installation; SG
   certification appears as the coinciding-granularity special case.
3. RevTrace: a transaction runtime (versioned CAS commit, stale-descendant
   invalidation, fail-closed preflight invariance, architecture-specific
   rebase adapters) plus stratified anytime-valid risk-limiting certification.
4. Cross-family evaluation: five checkpoints, two architecture families, zero
   per-checkpoint retuning; speedup, energy, tail, quality, and safety
   evidence with disclosed capacity boundaries.

## Submission outline and page budget (FGCS)

Target: 12-14 published pages (FGCS single-column Elsevier format), roughly
9,000-10,000 words plus 45-55 references, 6-7 figures, 7 tables. The elsarticle
single-column double-spaced draft will run about 28-32 pages. Page numbers
below are published-format budgets.

| # | Section | Pages | Core content | Why it is necessary |
|---|---|---:|---|---|
| 0 | Abstract | 0.2 | 6-8 sentence skeleton below; no content list | Reviewers decide relevance here; FGCS requires a self-contained claim+result summary |
| 1 | Introduction | 1.5-2 | Problem naming, causal motivating example (8/21 vs 0/21, RAF 153), four contributions, results teaser table | A systems paper must name one problem and one named idea within the first page; the teaser table prevents reviewers from doubting the headline before the design |
| 2 | Background and motivation | 2 | Revision-generative models; state-entry projection per family; three measured failure modes; evidence-tier separation | Without measured motivation the design reads as a solution in search of a problem; the three failure modes become the spine that the design later answers one-to-one |
| 3 | Design | 3 | State-entry invariant; DGFT (fine lane, coarse authority, directional coverage witness, selective replay); SG as degenerate case; RevTrace runtime; certification modes | This is the paper's intellectual core; SG derivation here is what makes the ablation a mechanism comparison instead of a system comparison |
| 4 | Implementation | 0.75 | Adapters, FP32 authority with 4,096-token bound, online causal coordinator, preflight accounting, 2xRTX 3090 | Establishes "real system, real measurements" before evaluation; short by design |
| 5 | Evaluation | 4 | Q1-Q7 per the evidence map; same-workload ablation table is the centerpiece | The longest section because every claim above must be discharged here; alternatives and disclosed negatives live inside it |
| 6 | Discussion and boundaries | 1 | Arrival-stream reality, execution-structure gap, certification scope split, c8 boundary, one-paragraph lessons learned | Pre-empts the four most likely reviewer attacks instead of leaving them to the rejection letter |
| 7 | Related work | 1.25 | Serving systems; speculation/verification; non-determinism; OCC analogy; anytime-valid statistics | Positions the paper and defends novelty against the nearest neighbors; kept after evaluation so differences can be stated against measured facts |
| 8 | Conclusion | 0.5 | Thesis restatement, two-family evidence, boundary sentence, artifact pointer | Standard closure; artifact sentence supports the reproducibility signal |

Figure budget (6 main-text figures; full seed tables, 16-cell detail, and
negative-experiment panels move to the appendix):
F1 two-panel problem-and-idea diptych: (a) contamination trajectory — a
batch-created flip enters feedback and the trajectory diverges (one RAF-153
root, labeled 8/21 causal contrast); (b) the same scenario under DGFT — the
flip is provisionally displayed but stopped at the state entry by its
certificate, trajectory stays canonical. F1 leads with the problem because
reviewers have no prior intuition for feedback-state contamination; panel (b)
satisfies the journal expectation that figure 1 already conveys the approach
sketch.
F2 system architecture merged with the commit timeline (fine lane / coarse
authority / transaction runtime / certificate consumption / stale
invalidation) — one double-width figure.
F3 same-workload SG/Coarse/Hybrid comparison (throughput, wall, absolute
service joules, tail) — the mechanism figure.
F4 Qwen R10 + Whisper R9.E cross-family headline matrix (wall / GPU-norm /
energy).
F5 quality panels: Qwen mixed-unit edit-rate distribution, Whisper paired WER
deltas (development + untouched confirmation).
F6 stratified certification evidence: SG anytime-bound trajectories, Qwen FP32
contract-scoped preflight, exhaustive transaction-check accounting (320 Qwen
events + 1,048 Whisper certificates).

Table budget (5 main-text tables):
T1 contracts and results teaser (one row per family: headline wall, energy,
violations, quality, evidence scope).
T2 same-workload six-cell ablation with contract and latency-scope labels —
the centerpiece mechanism table.
T3 cross-family production matrix (Qwen four cells + Whisper sixteen cells
aggregated; per-seed detail in appendix).
T4 unified quality contract, split by estimand: Qwen canonical-reference edit
rate vs Whisper unprotected-feedback WER delta; never pooled, never a single
combined quality number.
T5 guarantee taxonomy vs prior approaches (ordinary FP16, owner-version,
LocalAgreement, MarginGate-class, RevTrace) with claim boundaries.

Drafting order (evidence-before-prose): T1-T5 tables and F3-F6 figures first,
then Section 5 prose around them, then Sections 3 and 2, then Introduction and
abstract last, related work in parallel. This order prevents claim drift:
every sentence in Sections 1-3 must cite a table or figure that already
exists.

Hard writing rules:
- organize by claim, never by phase chronology; phase numbers never appear in
  section titles;
- every performance number carries its contract label (model, precision,
  topology, workload, arrival);
- every zero is paired with its scope (exhaustive trace vs statistical bound);
- latency columns always carry their scope (display vs state-entry vs segment
  commit);
- relative energy percentages are never compared across contracts; same-
  workload absolute joules are the comparable quantity.

## Section-to-evidence map

### 1 Introduction
Motivating example from Phase 4B (Whisper feedback-on vs feedback-off causal
intervention): among 21 distinct legal singleton-batch state pairs, 8
propagated with feedback enabled and none with the feedback edge removed; one
RAF-153 trace makes the amplification concrete. Never write "8/8" — the
denominator is 21. Contributions list above. Results teaser
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
CJK units), risk evidence, selective fine replay. Formalize the granularity
ratio rho = g_a / g_p: SG is rho = 1, Qwen coarse is rho = 3, Whisper uses
rho in [1.5, 3], Hybrid keeps rho > 1 with selective g_p replay. This makes
the SG special case a parameter degeneration, not prose.
3.3 RevTrace runtime: parent-version binding, certificate consumption, stale
invalidation, rollback/rebase adapters, and contract-scoped preflight
invariance (R10 FP32 batch-repeat + batch-vs-singleton audit under the frozen
deployment contract, excluded from service timing by design and recorded
explicitly). Never generalize the preflight to arbitrary batches, hardware,
or inputs.
3.4 Stratified certification layer: different adapters carry different evidence
regimes — SG numerical risk uses pre-outcome randomized audits with
time-uniform bounds; Qwen DGFT authority uses contract-scoped FP32 preflight;
DGFT transaction integrity uses exhaustive online certificate/install
validation; quality uses independent references and untouched holdouts. Name
the stratification explicitly; never present one certificate type as covering
all paths.

### 4 Implementation
Adapters per family, FP32 authority with 4,096-token bound, online causal
arrival scheduling (R9.E), two RTX 3090s. Keep short; cite artifacts.

### 5 Evaluation
Prose structure: organize as five questions in the manuscript (Q1 does DGFT
improve cross-architecture serving efficiency; Q2 is granularity change really
necessary — the same-workload ablation centerpiece; Q3 are state safety and
quality preserved; Q4 what evidence and guarantees does each layer carry; Q5
which models and boundaries apply). The Q1-Q7 list below is the internal
evidence inventory that feeds these five questions.
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
capacity boundary disclosed; DGFT energy tradeoff is model-dependent (never
write "DGFT dominates SG in all dimensions" — throughput and tail improve,
direct energy tradeoff depends on scale). Include a preflight amortization
analysis: R10 preflight costs 10.7-11.1 s per contract; report amortized cost
per served session and the break-even horizon, otherwise reviewers will ask
why ~11 s of startup cost is excluded from 30-second sessions.

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
authority, fine replay, SG certification (same-granularity special case),
stratified certification layer, contract-scoped preflight invariance.
DGFT expands to **Dual-Granularity Feedback Transactions**; R9-era reports used
"Directional Granularity", which is superseded and must not appear in the
manuscript (directional coverage is an evidence witness, not the mechanism
body).
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

## Pre-submission offline audits (completed; no new GPU experiments)

1. CJK coverage regression: after dgft.py adopted mixed Latin/CJK coverage
   units, replay the R9.E 2,050-segment coverage decisions and confirm zero
   changed scheduling decisions on the Latin-only Whisper traces.
2. Motivation denominator audit: unify the 8/21 propagation count, the RAF 153
   source pairs, their selection criteria, and statistical unit in one place
   before citing them in the introduction.
3. Single contract manifest: bind R9.E, R10, the SG risk audits, and both
   families' quality artifacts to their exact scopes so readers cannot assume
   one shared execution contract across all evidence.

Completion artifacts: `Paper/audits/cjk_coverage_replay.json`,
`Paper/audits/denominator_audit.json`, and
`Paper/audits/contract_inventory.json`; regenerate with
`scripts/audit_paper_submission.py` after running the coverage replay.

## Auditable sources

- `docs/reports/r10_qwen_cross_adapter.md`
- `docs/reports/r10_same_workload_dgft_ablation.md`
- `results/r10_qwen_cross_adapter/summary.json`
- `results/r10_qwen_cross_adapter/ablation_summary.json`
- `docs/reports/r9e_online_submission_closure.md`
- `results/r9_dgft/FINAL_REPORT_ONLINE.json`
- `docs/reports/phase_r9_final_report.md`
- `docs/reports/model_scale_generality_audit.md`
- `docs/CLAIM_BOUNDARIES.md`
- `docs/reports/revtrace_paper_identity.md`
- `results/final_closure/REPORT.md`
- `artifact/checkpoint20-submission-closure-v2/README.md`

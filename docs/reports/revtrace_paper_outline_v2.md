# RevTrace paper outline v2: theory-guided structure (FGCS first)

## Decision

`OUTLINE_V2_THEORY_GUIDED_SUPERSEDES_BLUEPRINT_STRUCTURE`

This outline supersedes the *structure* sections of
`revtrace_dgft_paper_blueprint.md` (which remains the evidence map). The
paper is restructured from an engineering-log narrative into a
theory-guided systems paper:

> Formal problem -> derive necessary conditions -> design a mechanism that
> satisfies them -> experiments test the theory's predictions and boundaries.

The upgrade is not mathematical decoration. Three transaction properties of
the already-implemented runtime are provable system invariants; the cost
decomposition predicts the measured SG/Coarse/Hybrid ordering; the causal
experiment validates the propagation channel the recurrence identifies.

## One-sentence argument

In batched serving of revision-generative streaming ASR, where generated
output is written back into future model state, we show that separating
display authority from state-write authority via Dual-Granularity Feedback
Transactions (DGFT) prevents feedback-state contamination while preserving
throughput, using the RevTrace transaction runtime with contract-scoped
stratified certification, supported by causal propagation evidence
(8 of 21 legal pairs propagate with feedback, 0 of 21 without), a
same-workload SG/Coarse/Hybrid ablation, and zero transaction-install
violations across 320 Qwen revision events and 1,048 Whisper commits;
certification is contract-scoped, and risk signals schedule verification
but never authorize state installation.

## Positioning statement (for cover letter and final intro pass)

> A theory-guided systems paper with formally stated transaction invariants,
> analytically derived granularity trade-offs, and real-system validation.

One paragraph version (Chinese anchor):
以反馈状态动力学定义问题，以事务不变式证明安全，以成本模型推导DGFT，
以跨架构真实系统实验验证理论预测。

---

## 1. Terminology and notation freeze

Canonical symbols, defined once in Section 2 and reused everywhere:

| Symbol | Meaning |
|---|---|
| `S_t` | committed feedback state entering round `t` |
| `A_t` | exogenous input of round `t` (audio frontier) |
| `Y_t` | generated output of round `t` |
| `T(.,.,.)` | model/adapter state-update function: `S_{t+1} = T(S_t, A_t, Y_t)` |
| `Phi(Y_t; S_t)` | state projection: the part of `Y_t` actually written to next state (Qwen rollback prefix; Whisper previous-text prompt) |
| `Y_t^f`, `Y_t^a` | fine batched proposer output vs canonical authority output |
| `epsilon_t` | local output divergence `d_Y(Y_t^f, Y_t^a)` |
| `e_t` | state-entry divergence `d_S(Phi(Y_t^f;S_t), Phi(Y_t^a;S_t))` |
| `C_t` | contamination event: `Phi(Y_t^f;S_t)` installed while `e_t > 0` |
| `D_t` | trajectory state distance `d_S(S_t^f, S_t^a)` |
| `L_t`, `beta_t` | local perturbation-decomposition coefficients (old-difference propagation; new-revision coupling) |
| `RAF_{t,K}` | measured trajectory amplification factor over horizon `K` |
| `Gamma_j` | authority commit tuple `(sid, e, p, v_j, [f_j, f_{j+1}), C_j)` |
| `tau_t` | transaction object `(sid, e, p, v_parent, [a_s, a_e), Y_t, Phi(Y_t), cert)` |
| `g_p`, `g_a`, `rho` | proposal granularity, authority granularity, ratio `g_a/g_p` |

Paper invariant (the mathematical core, boxed in Section 2):

```
Display(Y_t)  =/=>  Authorize( Phi(Y_t; S_t) )
```

Four protocol properties (spine of Section 3/4, Fig. 2 labels, and T5):

1. **Authority separation** — display and state-write permission are distinct.
2. **Parent ownership** — a result commits only onto the parent version it actually read.
3. **Frontier monotonicity** — committed audio frontiers advance monotonically, no gap, no overlap.
4. **Evidence non-authority** — margin/coverage/repetition schedule verification; they never authorize installation.

Classification rule (enforced at every claim):

| Status | Allowed for |
|---|---|
| Theorem/Lemma | uncertified-ancestry exclusion; stale-descendant rejection; committed-state linearizability; granularity-independent transaction safety; SG as the `rho = 1` reduction. All from program invariants, provable by induction over commit sequences. |
| Proposition / cost analysis | when Coarse beats SG; granularity vs tail latency; Hybrid Pareto trade-off. Depend on cost assumptions and hardware. |
| Empirical finding | 8/21 propagation; RAF up to 153; 6.88x; UCB 0.480%; architecture-family clustering; WER improvements. Never written as universal laws. |

Forbidden in manuscript: `RevOCC`, `EFSC`, `Directional Granularity`
(superseded by Dual-Granularity), `8/8` (denominator error; correct figure
is 8 of 21 legal pairs), any cross-contract pooled number.

## 2. Title (frozen)

> **RevTrace: Dual-Granularity Feedback Transactions for State-Certified
> Streaming ASR Serving**

Empirical scope exactly matches the title; no implied generalization to
text LLMs or VLMs. Extension to other feedback-driven revision models is
stated once in Introduction/Conclusion as future direction, not prepaid in
the title. Riskier memory-oriented alternative ("When Outputs Become State")
held back for possible TPDS special-issue reframe.

---

## 3. Section-by-section outline

Page budget total: 13-14 published pages (Elsevier single column), ~9,500
words of body text, 6 figures, 5 tables.

### Section 1 — Introduction (1.5 pp)

Job: name the problem and the idea within the first page (vLLM/SOSP'23
pattern). Open with the state-write framing, not with batching errors.

Paragraph jobs:

1. Field stake: streaming/revision-generative serving feeds outputs back
   into future state (Qwen rollback prefix; Whisper condition_on_prev_tokens).
2. Bottleneck: ordinary serving treats outputs as terminal; batching-created
   local divergence then becomes persistent trajectory divergence.
   Hook numbers: 8 of 21 legal state pairs propagate with feedback, 0 of 21
   after removing the feedback edge; RAF up to 153 (labeled: RAF measured on
   the 6 persistent pairs, not on the 21-pair set).
3. Prior attempts do not cover this: LocalAgreement protects display
   stability, not state ancestry; speculative decoding verifies tokens, not
   state-write authority; deterministic-inference work fixes arithmetic, not
   feedback semantics.
4. This paper: outputs are speculative writes; DGFT separates fine display
   from coarse state authority; RevTrace installs only contract-certified
   transitions.
5. Contributions (4 bullets):
   1. Problem characterization + causal verification of feedback-state
      contamination (no "first" claim until pre-submission literature sweep
      confirms; use "we characterize").
   2. DGFT mechanism with provable transaction invariants; SG as `rho = 1`
      reduction.
   3. RevTrace runtime + stratified, contract-scoped certification.
   4. Cross-family evaluation: 2 architecture families, 5 checkpoints,
      performance/quality/safety/boundary evidence.

Teaser: T1 (claim-contract map) appears here or at Section 2 end.

### Section 2 — Model and Problem Formulation (1.5 pp)

Deliberately not called "Background". This section owns the math objects.

- **2.1 Revision-generative state machine.** Define `S_{t+1} = T(S_t, A_t, Y_t)`;
  define `Phi(Y_t; S_t)`; ordinary batching implicitly assumes
  `S_{t+1} = Phi(Y_t^batch; S_t)`, conflating "was generated" with "may write
  state". State the boxed invariant.
- **2.2 Display output versus state projection.** Concrete instantiations:
  Qwen rollback prefix; Whisper previous-text prompt. Display-only suffixes
  carry no future-state authority.
- **2.3 State-entry divergence and contamination.** Define `epsilon_t`, `e_t`,
  `C_t`. Upgrade the problem statement from "outputs differ" to "a differing
  output acquired future-state write permission".
- **2.4 Feedback amplification.** Local perturbation decomposition
  `D_{t+1} <= L_t D_t + beta_t e_t` — explicitly a decomposition, not a
  Lipschitz claim (no assumed value of `L_t`). Removing the feedback edge sets
  `beta_t = 0`: the recurrence identifies the feedback edge as the only
  channel through which a local state-entry divergence becomes persistent;
  the causal experiment (Section 6, H1) confirms the prediction. Define
  `RAF_{t,K}` as a measurable trajectory-amplification indicator, not a
  theoretical bound.
- **2.5 Design requirements derived from the model.** Four requirements,
  each traced to a formula: display/authority separation; parent ownership;
  frontier monotonicity; evidence non-authority. These become Section 3
  structure, Fig. 2 labels, and T5 columns.

### Section 3 — DGFT: Theory and Mechanism (2.5-3 pp) — theoretical core

- **3.1 DGFT transaction definition.** `tau_t` tuple; commit tuple `Gamma_j`;
  validity predicate `Valid(Gamma_j)` (session, contract epoch `e`, policy `p`,
  parent version, frontier start, certificate = 1).
- **3.2 Theorem 1 — Uncertified-Ancestry Exclusion.** If future feedback
  state is updated only through authority commits satisfying `Valid`, no fine
  proposal absent from the authority certificate can become an ancestor of
  any future committed state. Proof: induction over the commit sequence;
  provisional display never mutates committed state. Deliberately
  architecture-agnostic: does not depend on margin accuracy, model
  determinism, FP16/FP32 agreement, Qwen vs Whisper.
- **3.3 Theorem 2 — Committed-State Linearizability.** Parent-version check
  + frontier-continuity check + version/frontier advancement imply accepted
  commits form a fork-free, gap-free, overlap-free linear history.
  Corollary: Stale-Descendant Rejection (a revision based on
  `v_parent != version(S_j)` cannot legally commit). The 320 Qwen events and
  1,048 Whisper certificates are *exhaustive validation of the protocol on
  the evaluated traces* — not failure-probability-zero claims.
- **3.4 Theorem 3 — Granularity-Independent Transaction Safety.** For any
  `rho >= 1`, if the authority segment starts at the committed parent, covers
  a contiguous audio frontier, yields a legal state projection, and passes the
  same certificate/version checks, Theorems 1-2 hold. Corollary: SG is the
  `rho = 1` reduction — proposal and authority granularities coincide, the
  directional coverage witness degenerates, fine replay degenerates into
  risk-triggered re-verification. Same protocol, not narrative repackaging.
  Note the canonical-path boundary: SG runs an FP16 singleton authority;
  Coarse/Hybrid run an FP32 batched authority — distinct canonical paths, no
  bitwise-identity claim.
- **3.5 Authority-cost decomposition (a Proposition, not a Theorem).** With
  `B` sessions, verification ratio `q` (SG), selective-replay ratio `r`
  (Hybrid), singleton authority cost `C_s`, batched coarse cost `C_c(rho,B)`,
  commit cost `C_commit`, queue/fragmentation cost `Q_s`:
  `T_SG^a ~= q B rho C_s + Q_s`;
  `T_DGFT^a ~= C_c(rho,B) + r B rho C_s + C_commit`;
  end-to-end `T_service ~= max(T_p, T_a) + T_repair` (proposer/authority
  parallel on two GPUs). Coarse beats SG when
  `C_c + r B rho C_s + C_commit < q B rho C_s + Q_s`. Predicts: SG tail
  bursts even at 8-10% verification; coarse amortizes invocation + queue;
  Hybrid trades `r` for quality at performance/energy cost; the trade-off may
  reverse across models because `C_c(rho,B)` is model-dependent. Section 6 H3
  checks each prediction.
- **3.6 Operating-point trade-offs.** Configuration policy
  `pi in {SG, Coarse, Hybrid}`; objective `J(pi)` over latency/energy/quality
  subject to `TxViolation(pi) = 0` and display/quality caps. DGFT provides a
  safety-constrained operating envelope, not a single optimum. Must NOT say
  RevTrace solves this optimization online (no online optimizer implemented);
  wording: "the formulation exposes the trade-off surface; the evaluated
  contracts instantiate three operating points."

### Section 4 — RevTrace System (1.5 pp)

Each module in the three-element pattern (motivation / mechanism / ablation
hook):

- **4.1 Architecture-specific adapters.** State-projection adapter, authority
  adapter, evidence adapter; Qwen rollback vs Whisper prompt-state
  differences live here, not in a second design section.
- **4.2 Certificate and versioned ledger.** CAS-style commit, certificate
  consumption, session/contract/policy/state version fencing.
- **4.3 Directional coverage witness and selective fine replay.** Latin + CJK
  units; replay only uncovered fine regions (Hybrid adds risk-triggered
  replay at rate `r`).
- **4.4 Stratified certification layer.** Four strata with non-transferable
  scopes: (i) SG numerical risk — randomized audit + anytime UCB; (ii)
  authority implementation — contract-scoped preflight (batch repeat,
  batch-vs-singleton, fail-closed); (iii) transaction integrity — exhaustive
  online certificate/install validation; (iv) semantic quality — independent
  references. Risk signal never becomes certificate.
- **4.5 Online coordinator.** Two-GPU scheduling, stale-descendant
  invalidation, terminal frontier closure, rollback/rebase.

### Section 5 — Implementation (0.75 pp)

Keep short; cite artifacts. Qwen rollback adapter and Whisper prompt adapter;
FP32 authority with 4,096-token KV bound; online causal arrival scheduling;
vectorized decoder host transfer; two RTX 3090s; preflight excluded from
steady-state timing and reported separately (10.7-11.1 s).

### Section 6 — Evaluation (4 pp): five hypothesis tests

Structure each subsection identically: *theory prediction -> experiment ->
numbers -> verdict*. Not phase chronology, not Q1-Q7.

| H | Question | Theory prediction | Evidence | Key numbers (scope-labeled) |
|---|---|---|---|---|
| H1 | Does state divergence propagate through the feedback edge? | `beta_t = 0` => no propagation | Phase 4B causal intervention | 8/21 propagate with feedback; 0/21 without; RAF up to 153 (6 persistent pairs) |
| H2 | Do the transaction invariants exclude uncertified ancestry? | Theorems 1-2 | Exhaustive trace validation | 320 Qwen events + 1,048 Whisper commits, 0 install violations; stale rejection exercised; terminal frontier closure |
| H3 | Does authority granularity drive performance? | cost decomposition of 3.5 | Same-workload SG/Coarse/Hybrid ladder (T2) | Coarse vs SG throughput 1.385x/1.276x; wall -27.8%/-21.6%; SG terminal-burst 2s miss 3.33%/4.17%; 1.7B direct energy +15.1% vs SG (model-dependent reversal, as predicted) |
| H4 | Does one invariant hold across adapters? | safety proof needs only projection/authority/certificate interfaces | Cross-family production cells | Qwen 0.6B/1.7B: 6.88x/6.06x wall, 3.44x/3.03x GPU-norm, -59.8%/-51.0% energy; Whisper 16/16 cells, 2.841x median wall, -31.13% energy; same runtime, per-family adapters |
| H5 | What does each certification layer guarantee? | evidence scopes are non-transferable | stratum-by-stratum audit | SG UCB 0.480%/0.478% (~30k audits, SG adapter only); Qwen FP32 preflight 0 mismatch (frozen contract); 0/320 + 0/1,048 exhaustive-trace evidence; quality: Qwen P95 edit <=3.43% vs FP16 reference, Whisper paired WER deltas all negative (-8 to -25 pp) |

Writing rules for Section 6: per-contract baselines only; latency columns
labeled by semantics (display vs state-entry vs segment-commit); quality
estimands reported per family and never pooled; every "zero" carries its
scope.

### Section 7 — Discussion and Boundaries (1 pp)

1. FP32 authority is a new canonical path, not a bitwise FP16 repair.
2. SG's UCB belongs to the SG adapter; it is not transferred to DGFT paths.
3. Qwen and Whisper quality estimands answer different questions.
4. Virtual arrival streams vs real GPU wall-clock/energy — stated once,
   precisely.
5. Display latency vs commit latency semantics differ.
6. Preflight amortization: break-even
   `N_break-even = ceil( T_preflight / (T_baseline/session - T_DGFT/session) )`;
   report one-time cost, break-even sessions/audio-hours, and steady-state
   result. Pre-empts "why is the 11 s preflight excluded from 30 s runs".
7. Not every ASR system needs DGFT (append-only boundary: Voxtral; c8
   low-load capacity boundary).

### Section 8 — Related Work (1 pp)

Collision matrix (built during pre-submission sweep, rendered as table or
dense prose):

| Work | Output feeds future state? | Separates display/state? | Authority granularity | Versioned commit? | Statistical certificate? |
|---|---|---|---|---|---|
| streaming ASR confirmation / LocalAgreement | | | | | |
| speculative decoding (+ verification variants) | | | | | |
| stateful LLM serving / runtimes (vLLM, SGLang, Sarathi-Serve, DistServe, Llumnix) | | | | | |
| inference non-determinism studies | | | | | |
| OCC/MVCC lineage (Kung-Robinson) — analogy only | | | | | |
| anytime-valid statistics (e-values, confidence sequences) | | | | | |

Use "first" only if the sweep confirms no prior work jointly handles
batch-created divergence + feedback propagation + state-entry authority.

### Section 9 — Conclusion (0.25 pp)

Thesis restated in one sentence; two-family evidence in two sentences;
boundary sentence; artifact pointer; one sentence on extension to other
feedback-driven revision models.

---

## 4. Figure budget (6 main-text figures)

- **F1 — Problem diptych (page 1-2).** Two panels, same scenario.
  (a) Ordinary batching: audio revision -> batched proposal differs locally
  -> output displayed -> output enters feedback state -> next revision reads
  changed parent -> trajectories diverge. Two tracks (canonical trunk,
  contaminated branch). Corner evidence annotation: "8/21 legal state pairs
  propagate with feedback; 0/21 after removing the feedback edge; tail RAF
  up to 153 (measured on the 6 persistent pairs)" — keep the two experiment
  sets visually distinct so RAF is never read as a statistic over 21 pairs.
  (b) DGFT: identical local difference; at the state-entry boundary:
  "PROVISIONAL DISPLAY ok / STATE WRITE denied"; coarse authority later
  produces certificate; only then the frontier advances. Key caption line:
  "DGFT does not require every provisional output to be identical; it
  prevents uncertified outputs from becoming future-state parents."
- **F2 — Architecture + commit timeline (double panel).** Top: fine proposal
  lane, evidence adapter, coarse canonical authority, certificate/ledger,
  feedback state, provisional display surface. Bottom: timeline with fine
  revisions p1-p3, provisional display, coarse authority covering the same
  frontier, certificate consumption, parent-version check, commit or
  selective replay, stale-descendant invalidation. Label the four protocol
  properties A-D on the diagram. Risk/coverage witness arrows go to the
  verification scheduler, NEVER directly to commit.
- **F3 — Same-workload ablation (double panel).** (a) Pareto scatter:
  x = wall speedup, y = P95 edit rate (lower better), size = service energy,
  color = SG/Coarse/Hybrid, markers for 0.6B and 1.7B. Reads as: Coarse =
  throughput point, Hybrid = quality-conservative point, SG = same-granularity
  certification point. (b) Latency-scope dumbbells: SG state-entry P99 vs
  DGFT display P99 and segment-commit P99, axes labeled by semantics. Never
  plot SG state-entry latency against DGFT display latency in one unlabeled
  chart.
- **F4 — Cross-architecture production matrix.** Qwen 4 operating points +
  Whisper 16 cells (per model/arrival group); wall/GPU-normalized/energy.
- **F5 — Quality distributions (double panel).** Qwen edit-rate CDF (with
  exact-session counts); Whisper paired WER deltas (dev + untouched, with
  bootstrap uppers). Two estimands, two panels, no pooled axis.
- **F6 — Stratified certification (four-rung ladder or matrix).** Strata as
  in 4.4; each rung carries its evidence and scope; draw explicit
  "no transfer" separators between rungs.

## 5. Table budget (5 main-text tables)

- **T1 — Claim-contract map** (Introduction or Section 2 end). Columns:
  Family | Model | Proposal path | Authority path | Workload contract |
  Quality reference | Main claim. Anti-pooling device from page one.
- **T2 — Same-workload SG/Coarse/Hybrid ladder** (the central table).
  Columns: config, model, `rho`, verify/replay fraction, wall speedup,
  GPU-normalized speedup, service energy (absolute J and delta vs SG),
  display latency, authority/state-entry latency (scope-labeled), quality
  reference metric, SLO gate. Six cells, one contract.
- **T3 — Cross-architecture production summary.** Aggregates only; seed-level
  detail to appendix.
- **T4 — Quality contracts.** Two visual zones (Qwen: FP16 singleton
  reference, mixed-unit edit rate, catastrophic=0, P95 bounded; Whisper:
  unprotected-feedback paired WER delta, dev/untouched split). No unified
  "quality gain" column.
- **T5 — Guarantee taxonomy.** Rows: unprotected FP16 batching; owner/version
  check only; LocalAgreement; confidence/margin gate; SG-DGFT; Coarse/Hybrid
  DGFT. Columns: protects display? protects feedback ancestry? canonical
  authority? stale rejection? risk quantification? semantic reference?
  critical-path verification? The most effective table for differentiating
  from margin-gate and rollback baselines.

Appendix: full seed tables, 16-cell detail, negative experiments, parameter
tables, contract manifests.

## 6. Claim Ledger (internal; do not print)

| Claim | Evidence | Scope | Allowed wording | Forbidden wording |
|---|---|---|---|---|
| feedback propagation | 8/21 vs 0/21 | Whisper legal pairs (Phase 4B) | "8 of 21 propagated" | "8/8" |
| amplification | RAF up to 153 | 6 persistent pairs | "tail RAF up to 153 on the six persistent pairs" | RAF as statistic over 21 pairs |
| Qwen performance | R10 cells | c16, 30 s, bilingual, 2 GPUs | "up to 6.88x" | "universally 6.88x" |
| Whisper service | R9.E | 16 cells | "16/16 cells pass" | "all Whisper workloads" |
| SG numerical risk | randomized audits | SG adapter only | "UCB 0.480% on the SG path" | "DGFT risk <= 0.48%" |
| DGFT transactions | 320 + 1,048 | completed traces | "zero observed install violations" | "zero failure probability" |
| Qwen quality | FP16 reference | mixed-unit edit | "P95 bounded (<=3.43%), worst 5.41%" | "WER improved" (Qwen) |
| Whisper quality | unprotected feedback | paired WER | "WER delta improved (all negative)" | pooled cross-family quality |
| energy vs SG | same-workload meters | 1.7B Coarse | "direct service energy +15.1% vs SG" | "DGFT dominates SG on all axes" |

## 7. Anti-pseudo-theory discipline (four forbidden moves)

1. No global Lipschitz constant for the network. `D_{t+1} <= L_t D_t +
   beta_t e_t` is a local perturbation decomposition; never claim known `L_t`.
2. Margin is never an error bound — own evidence shows high-margin state
   roots exist. Margin schedules; certificates authorize.
3. Zero observed violations is exhaustive-trace protocol validation, not
   probability zero and not floating-point exactness.
4. No formula per engineering rule. Directional coverage threshold, 4-gram
   repetition, 4,096-token bound belong to adapters and frozen contracts, not
   to theory. Sophistication comes from few stable math objects reused
   throughout, not formula density.

## 8. Drafting order (fixed)

0. Freeze this outline + terminology ledger + Claim Ledger (this document).
1. Tables T2, T3, T4, T5 (numbers already audited in `results/`).
2. Section 6 Evaluation (H1-H5), because every subsection is prediction ->
   test and the numbers are frozen.
3. Section 3 core theory pages — definitions, contamination, recurrence/RAF,
   four requirements, Theorems 1-3 with short proofs, SG `rho=1` corollary,
   cost decomposition, then attach the ablation.
4. Fig. 1 and Fig. 2 (write captions first; a good caption is the compressed
   subsection).
5. Section 2 Problem and Motivation prose.
6. Section 4 system description, Section 5 implementation.
7. Discussion (Section 7), Related Work (Section 8, with collision-matrix
   sweep), then Introduction and Abstract last.

## 9. Pre-submission offline audits (completed)

1. CJK coverage replay: re-run the 2,050 R9.E Whisper coverage segments
   against the CJK-aware `dgft.py`; confirm Latin-only decisions unchanged.
2. Denominator audit: unify sources and statistical units of 8/21, RAF 153,
   and any residual 8/8 occurrence in text or figures.
3. Single contract manifest: bind R9.E, R10, SG risk audit, and quality
   artifacts by scope so no reader can assume one execution contract.

Frozen outputs are under `Paper/audits/`; regenerate them with
`scripts/audit_r9_coverage_replay.py` and
`scripts/audit_paper_submission.py`.

## Auditable sources

Same as `revtrace_dgft_paper_blueprint.md` § Auditable sources, plus:
`results/r10_qwen_cross_adapter/ablation_summary.json`,
`docs/reports/r10_same_workload_dgft_ablation.md`.

# Pre-submission reviewer assessment

## Review setup

- **Input scope:** the compiled 18-page `Paper/main.pdf`, manuscript sources,
  tables, figure legends, frozen audits, and the repeated single-node V100
  matrix.
- **Assessment boundary:** Figures 1, 2, and 6 remain author-declared
  placeholders awaiting final artwork. Multi-node execution is explicitly not
  evaluated. Adapted baselines are assessed only under their declared
  revision-level contracts.
- **Shared manuscript claim:** generated revisions that are fed back into a
  streaming model are speculative state writes; DGFT separates low-latency
  display from certificate-bearing state-write authority, and RevTrace
  implements that contract efficiently.
- **Visible evidence:** a legal-pair causal intervention; formal ancestry,
  lineage, and granularity theorems; a 250,000-attempt transaction fuzzer;
  Qwen and Whisper evaluation over five checkpoints; normal-load and
  flip-rich adapted baselines; RTX 3090 production contracts; and an
  independently repeated 8xV100 single-node scaling contract.

## Reviewer 1 - technical soundness emphasis

- **Overall assessment:** the technical chain is substantially complete. The
  paper distinguishes display, state entry, and certified segment commit, and
  does not convert zero observed violations into a mathematical guarantee.
- **Who would be interested, and why:** serving-runtime, streaming-ASR, and
  reliable-agent researchers would value a concrete authorization boundary
  for feedback-generated state.
- **Major strengths:** causal removal of the feedback edge; theorem-to-runtime
  correspondence; exhaustive protocol mutation/replay testing; cross-family
  contracts; repeated c64 scale evidence; explicit c128 failure boundary.
- **Major concerns:** the V100 result is single-node; c64 certified-commit P99
  is 3.080/4.890 s rather than the 2 s display target; and the MarginGate and
  LLM-42 comparisons are faithful adaptations rather than original systems.
- **Technical failings to address before the case is established:** replace
  Figures 1, 2, and 6; retain the multi-node and cross-contract non-pooling
  boundaries; ensure that no prose labels c64 as a certified-commit 2 s SLO
  pass. These requirements are satisfied in the present text except for final
  artwork.
- **Criteria readout:** originality strong; significance strong within systems
  and ML serving; technical soundness strong with bounded external validity;
  nonspecialist readability moderate because the contract vocabulary is dense.
- **Recommendation posture:** competitive after final figures and a final
  consistency audit; no additional broad experiment is required for the
  declared single-node claim.

## Reviewer 2 - originality and significance emphasis

- **Overall assessment:** the strongest contribution is not a batching
  optimization but the reclassification of feedback revisions as state writes
  requiring separate authority. DGFT is the mechanism that operationalizes
  this invariant.
- **Who would be interested, and why:** database-inspired ML systems,
  speculative-serving, streaming inference, and self-revising agent systems
  share the underlying problem of untrusted generated state becoming future
  context.
- **Major strengths:** the paper identifies a reusable systems abstraction;
  same-granularity certification is presented as a reduction rather than a
  second disconnected method; risk schedules work but never grants authority;
  high-throughput evidence follows from the two-plane mechanism.
- **Major concerns:** the current implementation uses platform-scoped FP32
  authority, and broader non-ASR generality is argued rather than measured.
- **Technical failings to address before the case is established:** preserve
  the distinction between the invariant, DGFT, and its Qwen/Whisper adapters;
  do not advertise FP32 as a universal determinism repair; keep future
  multimodal and distributed extensions out of the validated claim set.
- **Criteria readout:** originality strong; scientific importance strong for
  feedback-driven serving; interdisciplinary reach plausible but not proven
  beyond systems/ML; technical evidence proportionate to the scoped claims.
- **Recommendation posture:** the paper has a defensible high-level identity
  and should be positioned around state-write authority, not the 6.88x maximum
  alone.

## Reviewer 3 - readership and readability emphasis

- **Overall assessment:** the abstract and introduction communicate the central
  distinction clearly, and the new dual-plane figure makes the strongest scale
  result and its latency boundary visible at a glance.
- **Who would be interested, and why:** readers outside ASR can understand the
  broader lesson that a displayed model output is not automatically safe to
  reuse as future state.
- **Major strengths:** one-sentence thesis; explicit claim contracts; separate
  quality estimands; visual separation of display and commit latency; honest
  negative boundaries.
- **Major concerns:** acronyms and contract terminology accumulate rapidly;
  placeholder architecture figures currently interrupt the explanatory flow;
  the evaluation section is information-dense.
- **Technical failings to address before the case is established:** final
  Figures 1, 2, and 6 must explain the feedback edge, dual-plane runtime, and
  evidence ladder without internal experiment identifiers. Captions should
  remain claim-bearing and self-contained.
- **Criteria readout:** readability good for systems readers and moderate for
  nonspecialists; significance is clearest when framed as authorization of
  generated state rather than ASR-specific acceleration.
- **Recommendation posture:** retain the current 18-page evidence rather than
  compressing away boundaries; improve accessibility through the pending
  schematics, not by deleting contract definitions.

## Cross-review synthesis

- **Consensus strengths:** a distinct and defensible problem; DGFT as one
  coherent mechanism; formal/runtime alignment; unusually disciplined claim
  boundaries; strong single-node performance with a repeated capacity result.
- **Consensus technical risks:** no measured multi-node ledger; platform-scoped
  authority; adapted rather than native external baselines; three missing final
  schematics.
- **Where emphasis differs:** Reviewer 1 weights the finite and single-node
  evidence boundary; Reviewer 2 weights the abstraction's novelty; Reviewer 3
  weights the manuscript's accessibility.
- **Broad-interest readout:** the result is most compelling to ML systems,
  databases, streaming inference, and reliable-agent communities. Broader
  impact depends on presenting feedback-state authorization as the central
  lesson.
- **Most important remaining action:** insert final Figures 1, 2, and 6 and run
  the same PDF visual/identifier audit. The experimental case is otherwise
  strong enough for the declared FGCS scope.

## Risk / unsupported claims

- The evidence does not establish multi-node scalability or data-center
  production deployment.
- The 2 s SLO applies to provisional display, not certified-segment commit.
- FP32 is one validated canonical authority implementation, not a universal
  bitwise certificate.
- Zero observed state/transaction violations are finite evidence; the formal
  guarantee is protocol-relative and assumes a non-Byzantine authority.
- The stress mismatch suite tests failure coverage and is not a production
  prevalence estimate.

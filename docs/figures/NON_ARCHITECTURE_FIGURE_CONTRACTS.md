# RevTrace non-architecture figure contracts

Backend: Python/matplotlib only.

Target: double-column systems/ML journal figures, 183 mm wide, editable SVG and
PDF plus 600 dpi TIFF and 300 dpi PNG previews. All quantitative panels are
traceable to frozen repository data. Red denotes a failed boundary, not a
method family. Teal denotes a passed guard, not statistical significance.
Figure 1 is intentionally excluded from this renderer.

## Figure 2 — Batching creates both the opportunity and the state risk

- Core conclusion: low-precision batching exposes a large performance envelope
  but is not a semantics-preserving transform; same-input and feedback controls
  isolate execution shape and revision feedback as the causal chain.
- Archetype: asymmetric mechanism/analysis composite.
- Panel a: median-to-maximum speedup envelopes for both Qwen3-ASR models.
- Panel b: a fully vectorized exactness matrix reporting token, partial, and
  final exactness together with distance from deterministic execution.
- Panel c: a same-input causal chain reporting singleton-repeat, batch-repeat,
  and singleton-versus-batch mismatches over 720 revision events.
- Panel d: two 21-pair counterfactual dot matrices showing propagation with
  feedback enabled and disabled.
- Reviewer risk: the performance envelope and exactness matrix share a frozen
  workload matrix but do not estimate a production error rate; the 21-pair
  suite is causal evidence, not prevalence evidence.

## Figure 3 — RevTrace converts the opportunity into efficient serving

- Core conclusion: replicated RevTrace deployment jointly occupies the fast
  and sub-SLO region, reduces matched energy, and stays inside the time-uniform
  0.5% risk budget.
- Archetype: asymmetric quantitative figure with a hero phase-space panel.
- Panel a: speedup-versus-P99 replicate phase space with open run markers,
  means, covariance ellipses, energy reduction, and risk UCB annotations.
- Panel b: matched all-canonical-to-RevTrace energy slopegraph for both models.
- Panel c: risk-budget bullet chart with audit counts and observed violations.
- Reviewer risk: covariance ellipses summarize replicate geometry and are not
  population confidence regions; risk events are correlated execution events.

## Figure 4 — Adaptation is contract-scoped and jointly risk/SLO aware

- Core conclusion: the safe operating surface depends jointly on concurrency,
  horizon, model, latency, energy, and state safety; RevTrace adapts to exact
  contracts rather than transferring a fixed threshold.
- Archetype: 3D hero landscape plus subordinate contract evidence.
- Panel a: 3D configuration landscape; height encodes wall speedup, marker
  shape encodes model, color encodes joint-contract outcome, and labels report
  P99 and energy.
- Panel b: live risk–latency phase trajectory for c16→c64→c16; point area
  encodes goodput and labels report learned thresholds.
- Panel c: recertification funnel from 1,358 flat-relearning events to 64
  exact-contract-renewal events.
- Panel d: second-family counterfactual feedback dot matrices.
- Reviewer risk: the controller trajectory and workload frontier are distinct
  protocols; the 3D view encodes measured cells rather than a fitted surface.

## Figure 5 — Checkpoint-20 Holdback closes the long-session tail

- Core conclusion: withholding low-margin display authority while advancing
  audio removes synchronized verification stalls, repeats across held-out
  seeds, and preserves quality and observable display-authority behavior.
- Archetype: asymmetric long-horizon validation composite.
- Panel a: mechanism trajectory from continuous execution through checkpoint/
  rebase to Checkpoint-20 Holdback, with guard/deadline bands and causal
  annotations.
- Panel b: five-seed P50–P95–P99 latency fan with per-seed energy labels.
- Panel c: paired quality forest separating total checkpoint+holdback change
  from the holdback-only increment.
- Panel d: provisional-transition overwrite raincloud/rug with means, medians,
  and sample counts.
- Reviewer risk: panel a is a sequential mechanism progression rather than a
  paired estimator; quality intervals are descriptive for the frozen
  constructed-session sample because source audio is reused.

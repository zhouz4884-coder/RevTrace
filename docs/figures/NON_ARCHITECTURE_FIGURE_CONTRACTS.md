# RevTrace non-architecture figure contracts

Backend: Python/matplotlib only.

Target: double-column systems/ML journal figures, 183 mm wide, editable SVG and
PDF plus 600 dpi TIFF and 300 dpi PNG previews. All quantitative panels are
traceable to frozen repository data. Red denotes a failed boundary, not a
method family. Green denotes a passed guard, not statistical significance.

## Figure 2 — Batching creates both the opportunity and the state risk

- Core conclusion: low-precision batching delivers large throughput gains but
  changes revision outputs, and previous-text feedback converts some local
  execution differences into persistent state differences.
- Archetype: quantitative grid.
- Panel a: median and maximum audio-throughput speedup for both Qwen3-ASR
  models.
- Panel b: token, partial-transcript, and final-transcript exactness under
  ordinary batching.
- Panel c: same-input controls separating singleton repeatability from
  batch-repeat and cross-shape mismatches.
- Panel d: Whisper feedback-on versus feedback-off propagation under fixed
  future audio.
- Reviewer risk: throughput and exactness share a workload matrix but are not a
  deterministic-error-rate estimate; Whisper pair yield is not production
  prevalence.

## Figure 3 — RevTrace converts the opportunity into efficient serving

- Core conclusion: state-certified revision serving achieves approximately
  5–6x wall-clock speedup, remains below the two-second SLO, sharply reduces
  energy, and keeps the time-uniform state-risk bound below 0.5%.
- Archetype: asymmetric quantitative grid with the replicated wall-speedup
  panel as hero evidence.
- Panel a: five real two-GPU wall-speedup replicates per model with mean and
  95% t interval.
- Panel b: matching state-entry P99 replicates with the two-second deadline.
- Panel c: matched two-GPU energy for RevTrace and all-canonical execution.
- Panel d: randomized anytime risk upper bounds against the frozen budget.
- Reviewer risk: risk events are correlated execution events, not independent
  utterances; matched energy and service replication use different repeat
  counts and are labelled separately.

## Figure 4 — Adaptation is contract-scoped and jointly risk/SLO aware

- Core conclusion: RevTrace adapts evidence to exact execution contracts,
  preserves safe performance across heterogeneous workloads, and refuses
  unsafe or overloaded contracts rather than transferring a convenient
  threshold.
- Archetype: asymmetric mixed quantitative figure.
- Panel a: live c16→c64→c16 controller trajectory showing learned thresholds,
  risk bounds, and the c64 SLO failure.
- Panel b: eight-cell workload frontier, wall speedup versus P99, with deadline
  and state-safety status encoded independently.
- Panel c: exact-contract renewal versus flat recertification.
- Panel d: feedback-on/off causal propagation in a second model family.
- Reviewer risk: the controller trajectory and workload matrix are distinct
  protocols; markers communicate boundaries rather than imply a pooled fit.

## Figure 5 — Checkpoint-20 Holdback closes the long-session tail

- Core conclusion: withholding low-margin text authority while advancing audio
  removes synchronized verification stalls, restores the long-session SLO,
  and adds little incremental ASR degradation.
- Archetype: quantitative grid.
- Panel a: sequential long-session mechanism outcomes—continuous,
  checkpoint/rebase, and the final holdback contract—with the 1.9 s guard and
  2.0 s deadline.
- Panel b: five independent 120 s seed latency quantiles and energy.
- Panel c: paired quality forest plot for checkpoint total and holdback-only
  incremental deltas.
- Panel d: actual provisional display-transition overwrite distributions.
- Reviewer risk: panel a is a mechanism progression, not a paired estimator;
  the quality interval is descriptive for the frozen constructed-session
  sample because source audio is reused across sessions.

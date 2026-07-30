# RevTrace Figures 2--5: V3 visual contracts

Backend: Python/matplotlib only. Figure 1 remains out of scope.

All values are read from the frozen source-data tables under
`figures/source_data/`. The redesign changes visual hierarchy, not experimental
claims.

## Figure 2

- **Core conclusion:** batching offers an order-of-magnitude performance
  opportunity, but execution shape changes model outputs and feedback turns a
  local numerical flip into persistent revision state.
- **Archetype:** asymmetric mixed-modality figure.
- **Hero evidence:** model-wise median-to-maximum throughput envelope.
- **Supporting evidence:** six exactness gauges, same-input causal controls,
  and an ON/OFF feedback flow.
- **One-look anchors:** 11.07x, 17/720, and 8/21 -> 0/21.
- **Reviewer risk:** do not call empirical exact-match deficits a production
  error rate.

## Figure 3

- **Core conclusion:** the deployed two-GPU system simultaneously occupies the
  high-speed, positive-SLO-headroom, low-energy, risk-budget-feasible region.
- **Archetype:** asymmetric quantitative composite.
- **Hero evidence:** replicated speedup versus P99-headroom phase space.
- **Supporting evidence:** matched energy slopegraph, anytime-risk budget, and
  an auditable sample-size ledger.
- **One-look anchors:** 6.05x/4.95x mean speedup, 80.3%/73.9% less energy,
  max P99 1.58/1.73 s, and risk UCB below 0.5%.
- **Reviewer risk:** observed zero violations is reported with an upper bound;
  it is not mathematical zero.

## Figure 4

- **Core conclusion:** RevTrace adapts to workload contracts and its causal
  feedback boundary transfers across model families, while strong serving
  speedup remains established only for Qwen3-ASR.
- **Archetype:** 3D hero landscape plus compact evidence rail.
- **Hero evidence:** concurrency-duration-speedup operating surface with
  pass/fail contract encoding.
- **Supporting evidence:** c16 -> c64 -> c16 controller trajectory,
  exact-contract recertification funnel, and a three-family generality ledger.
- **One-look anchors:** 5.21x best safe frontier point, 1.293 s returned P99,
  22.3 events/s, and 95.29% fewer recertification events.
- **Reviewer risk:** Whisper is cross-family causal/protection evidence with a
  1.00x all-canonical performance boundary; Voxtral is an append-only negative
  boundary, not another positive performance result.

## Figure 5

- **Core conclusion:** Checkpoint-20 Holdback removes the long-session
  synchronized verification tail while preserving the state contract and
  adding negligible incremental quality change.
- **Archetype:** mechanism-led quantitative composite.
- **Hero evidence:** sequential P99/miss waterfall.
- **Supporting evidence:** five-seed latency fan, paired quality forest, and
  empirical overwrite ECDF.
- **One-look anchors:** 1.414 s P99, 40.9% lower than continuous, 5/5 seeds
  below 1.9 s, and zero observed deadline/authority violations.
- **Reviewer risk:** provisional display is not authoritative state; overwrite
  statistics describe the measured 75 transitions only.

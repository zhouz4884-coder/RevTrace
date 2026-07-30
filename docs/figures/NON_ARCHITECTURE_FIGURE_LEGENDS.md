# RevTrace non-architecture figure legends

## Figure 2 | Batching creates both the opportunity and the state risk

**a,** Median-to-maximum audio-throughput speedup envelope of ordinary
multi-session batching over singleton streaming for Qwen3-ASR-0.6B and
Qwen3-ASR-1.7B across the frozen Phase 0 workload matrix. Open and filled
markers denote medians and maxima. **b,** Vector exactness matrix at token,
partial-transcript, and final-transcript levels. Each cell reports exact match
and its percentage-point distance from deterministic execution. **c,**
Same-input controls over 720 revision events. Repeated singleton execution is
stable; repeated batched execution and singleton-versus-batch execution expose
execution-shape drift. **d,** Counterfactual dot matrices under fixed future
audio. Eight of 21 previous-text differences propagate when feedback is
enabled, compared with zero of 21 when feedback is disabled. Counts characterize
the constructed causal suite, not production prevalence.

## Figure 3 | RevTrace converts the opportunity into efficient serving

**a,** Joint deployed phase space of real two-GPU wall-clock speedup and
state-entry P99 over FP16 singleton-canonical execution. Open symbols are five
independent runs per model, diamonds are means, and translucent ellipses show
replicate covariance. Direct annotations report mean speedup, matched energy
reduction, and anytime state-risk UCB. The dashed line is the frozen 2 s SLO.
**b,** Matched all-canonical-to-RevTrace energy slopegraph (mean, three
replicates per mode); endpoint labels report joules per audio-second and
percentage reduction. **c,** Time-uniform state-risk upper bounds under
randomized shadow auditing, with audit counts and observed state violations.
The dashed line is the pre-registered 0.5% budget. Execution events are
correlated and are not presented as independent utterances.

## Figure 4 | Adaptation is contract-scoped and jointly risk/SLO aware

**a,** Measured 3D configuration landscape across model, concurrency, and audio
horizon. Height is wall-clock speedup; marker shape identifies model; color
identifies joint risk/SLO outcome; direct labels report P99 and joules per
audio-second. The panel shows measured cells, not a fitted surface. **b,** Live
risk–latency trajectory across an exact-contract switch from concurrency 16 to
64 and back to 16. Point area is goodput, arrows show temporal order, and labels
report learned thresholds. **c,** Events required to restore an exact
certificate under flat relearning and exact-contract renewal. **d,**
Second-family causal boundary: previous-text differences propagate under
feedback but not when feedback is disabled. Panels a and b use distinct
protocols and are not pooled.

## Figure 5 | Checkpoint-20 Holdback closes the long-session tail

**a,** Sequential long-session mechanism trajectory from continuous revision
serving through checkpoint/rebase to Checkpoint-20 Holdback. Dashed lines show
the 1.9 s guard and 2.0 s deadline; annotations give the causal intervention
and deadline-miss rounds. **b,** P50, P95, and P99 state-entry latency across
five independent held-out 120 s seeds; labels along the lower edge report
joules per audio-second. All seeds record zero deadline misses and zero
authority violations. **c,** Paired English WER and Chinese CER forest plot.
Dark intervals show total checkpoint+holdback change; light intervals isolate
the holdback-only increment. The shaded region is the pre-registered ±2
percentage-point tolerance. **d,** Distribution of already displayed text
overwritten at provisional-to-authority and provisional-to-provisional
transitions. Diamonds are means and vertical bars are medians.

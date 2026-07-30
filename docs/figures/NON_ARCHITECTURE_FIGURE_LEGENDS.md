# RevTrace non-architecture figure legends

## Figure 2 | Batching creates both the opportunity and the state risk

**a,** Throughput opportunity envelope of ordinary multi-session batching over
singleton streaming for Qwen3-ASR-0.6B and Qwen3-ASR-1.7B across the frozen
Phase 0 workload matrix; the highlighted maxima are 11.07× and 8.75×.
**b,** Radial exactness gauges at token, partial-transcript, and
final-transcript levels; each ring reports the exact-match rate and its distance
from deterministic execution. **c,** Same-input controls over 720 revision
events. Repeated singleton execution is stable, whereas singleton-versus-batch
execution exposes 17 shape-dependent divergences. **d,** Counterfactual
feedback flow under fixed future audio. Eight of 21 previous-text differences
propagate when feedback is enabled, compared with zero of 21 when feedback is
disabled. Counts characterize the constructed causal suite, not production
prevalence.

## Figure 3 | RevTrace converts the opportunity into efficient serving

**a,** Joint deployed phase space of real two-GPU wall-clock speedup and P99
deadline headroom over FP16 singleton-canonical execution. Open symbols are five
independent runs per model, diamonds are means, and translucent ellipses show
replicate covariance. Direct annotations report mean speedup, matched energy
reduction, and anytime state-risk UCB. The upper-right quadrant is jointly
faster and farther below the frozen 2 s SLO. **b,** Matched
all-canonical-to-RevTrace energy slopegraph (mean, three replicates per mode);
endpoint labels report joules per audio-second and percentage reduction.
**c,** Time-uniform state-risk upper bounds under randomized shadow auditing,
with audit counts and observed state violations. The dashed line is the
pre-registered 0.5% budget. Execution events are correlated and are not
presented as independent utterances.

## Figure 4 | Adaptation is contract-scoped and jointly risk/SLO aware

**a,** Measured 3D configuration landscape across model, concurrency, and audio
horizon. Height is wall-clock speedup; marker shape identifies model; color
identifies joint risk/SLO outcome; direct labels report P99 and joules per
audio-second. The panel shows measured cells, not a fitted surface. **b,** Live
risk-latency trajectory across an exact-contract switch from concurrency 16 to
64 and back to 16. Point area is goodput, arrows show temporal order, and labels
report learned thresholds. **c,** Events required to restore an exact
certificate under flat relearning and exact-contract renewal. **d,** Layered
generality ledger. Qwen3-ASR-0.6B/1.7B supplies deployed system evidence;
Whisper tiny/base supplies cross-family feedback-causality evidence (8/21 with
feedback versus 0/21 without) but remains a 1.00× all-canonical performance
boundary; Voxtral Mini 4B supplies an append-only bypass boundary with zero
observed drift across 120 execution rows. These layers must not be pooled into
a claim of cross-family performance generalization.

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

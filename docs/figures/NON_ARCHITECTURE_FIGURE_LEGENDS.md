# RevTrace non-architecture figure legends

## Figure 2 | Batching creates both the opportunity and the state risk

**a,** Median and maximum audio-throughput speedup of ordinary multi-session
batching over singleton streaming for Qwen3-ASR-0.6B and Qwen3-ASR-1.7B across
the frozen Phase 0 workload matrix. **b,** Exact-match rate at token-event,
partial-transcript, and final-transcript levels; the dashed line denotes exact
execution. **c,** Same-input controls over 720 revision events. Repeated
singleton execution is stable, whereas repeated batched execution and
singleton-versus-batch execution expose execution-shape drift. **d,** In the
second-family Whisper feedback experiment, 8 of 21 distinct future-audio pairs
propagate a previous-text difference when feedback is enabled, compared with
0 of 21 when it is disabled. Counts characterize the constructed causal suite,
not production prevalence.

## Figure 3 | RevTrace converts the opportunity into efficient serving

**a,** Real two-GPU wall-clock speedup over FP16 singleton-canonical execution.
Open circles are five independent runs per model; filled markers show the mean
and 95% Student-\(t\) interval. **b,** State-entry P99 for the same runs; the
dashed line is the frozen 2 s service-level objective. **c,** Matched two-GPU
energy per processed audio second for RevTrace and all-canonical execution
(mean ± s.d., three replicates). **d,** Time-uniform upper confidence bound on
state-entry risk under the randomized audit protocol; the dashed line is the
pre-registered 0.5% budget. Execution events are correlated and are not
presented as independent utterances.

## Figure 4 | Adaptation is contract-scoped and jointly risk/SLO aware

**a,** Live controller trajectory across an exact-contract switch from
concurrency 16 to 64 and back to 16. Each bar reports state-entry P99; labels
give the learned threshold \(\tau\) and the anytime risk upper confidence
bound. Red marks the c64 SLO failure, not a statistical comparison.
**b,** Workload frontier across concurrency and audio duration. Marker fill
encodes state-safety status, marker edge encodes deadline status, marker area
encodes throughput, and crosses denote state-boundary failure. The 2 s SLO is
shaded. **c,** Events required to restore an exact certificate under flat
relearning and exact-contract renewal. **d,** Second-family causal boundary:
previous-text differences propagate under feedback but not when feedback is
disabled. Panels a and b use distinct protocols and are not pooled.

## Figure 5 | Checkpoint-20 Holdback closes the long-session tail

**a,** Sequential mechanism progression on the long-session protocol:
continuous revision serving, checkpoint/rebase, and Checkpoint-20 Holdback.
Dashed lines show the 1.9 s guard and 2.0 s deadline; annotations give deadline
miss rounds. This panel compares successive protocols and is not a paired
estimator. **b,** P50, P95, and P99 state-entry latency across five independent
held-out 120 s seeds. All seeds record zero deadline misses and zero authority
violations; mean energy is reported in-panel. **c,** Paired English WER and
Chinese CER changes in percentage points. Dark intervals show total change
from continuous execution to checkpoint plus holdback; light intervals isolate
the incremental holdback contribution. The shaded region is the pre-registered
±2 percentage-point tolerance. Intervals are descriptive for the frozen
constructed-session sample because source audio is reused across sessions.
**d,** Distribution of the fraction of already displayed text overwritten at
provisional-to-authority and provisional-to-provisional transitions. Diamonds
show means and horizontal bars show medians.

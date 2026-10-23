# REVTRACE-CES-FORMAL-v1 — immutable pre-validation release specification

Named evidence base23ba88c; executed candidate source
`e0aeae1b418644c378dde331c59b55fc5948b40f` (runtime_v4).
The CES main rule is unchanged from runtime_v3 on all60 recorded decision
snapshots; v4 strengthens controls and per-run source provenance, not tuning CES.
Calibration_v5 is development-history-only contextual cost plus original strict
rejection priors and measured row timing. No independent CES outcome has been
used to fit parameters or choose source audio. The independent pool is the
previous study's source-held-out pool, not a claim that nobody ever observed
baseline results on those sources.

## Fixed scope and comparison

180 fresh-process cells:9 methods ×2 source pools ×2 arrival patterns ×
(Mixed3 repeats +Clean1 +High1). The initial252-cell draft was reduced BEFORE
formal execution, then expanded for two stronger simple controls: primary Mixed
keeps its3 repetitions; all clean/high controls
remain, but their single runs are descriptive and cannot support repeatability.
No new repetitions will be added merely to obtain significance.

Methods: Fine, Strict+complete paid fallback, readiness/birth, readiness-only,
cost threshold, joint Cost-only, causal-only/no-joint, CES and full Standard
Safe Async. All use fine2s/rho1,
FP16 GPU0 proposer, FP32 GPU1 authority, same row SDK, eager profile,256-token
budget, D1, original private continuity, two-lane Consumer and group-ready WAL.
Fine/Standard bypass unnecessary prediction; Strict does not spin through the
CES cost model while waiting for absent candidates. All get the same row lease
capabilities. No output/quality equality is presumed between actual layouts.

Load:16 distinct original audios per pool, full durations, synchronous or0.25s
uniform stagger. No cyclic replay or result-selected source removal. Traffic
is clean, Mixed at even-session window5, and high at every window>=5. Faults
are fixed exogenous session/frontier entries, not schedule-dependent job IDs.
Issued/consumed/covered fault targets are reported separately. No fault label
enters the selector. Mode order rotates/reverses by repeat and stratum.

The CES score, candidate wait cap0.15s, robust-ridge rule, training-only bounds,
rejection priors and ranked-prefix/order enumeration are fixed as documented in
CES_ALGORITHM.md. Cost-only receives identical contextual physical cost models
AND the same joint batch/order/deadline planner, without causal rejection or
descendant features. Causal-only retains the complete one-target CES score and
bounded wait but chooses rowwise. The old myopic cost rule is cost_gate, not
passed off as the strongest Cost-only ablation.
Historical age/descendant signals are predictors, not deterministic rejection
proofs or measurements of exclusive GPU work. Actual physical costs are billed
separately, including complete drain, fallback and obsolete peer work.

## Metrics and predeclared decision

Primary Goodput uses every requested fine audio frontier: actual local Consumer
legal display<=2s and original Owner WAL-install/commit<=8s, divided by complete
serving+drain+Consumer wall. This retains the previous comparison clock. Report
actual certified-Consumer commit timing and its stricter Goodput separately;
do not call install time a network/client-consumption time. All incomplete
frontiers remain failures in the denominator. Whole-run dual-P99 pass is a
separate statistic. P50/95/99, both GPUs' clipped-window energy, full-final
Canonical WER/CER and integer reference/error counts, physical batches/calls,
actual verification/fallback, waits, fsync, CPU/IPC and private losses are retained.
Do not sum overlapping row durations as exclusive GPU seconds.

Independent Mixed is primary; both arrivals and8 comparators are predeclared.
Use10,000 same-source/repeat paired bootstrap draws with seed20261023, conditional
on observed schedules (no queue resimulation). Measured energy resamples paired
runs, not replicated sources. Report ordinary95% intervals and conservative
99.84375% intervals for32 planned endpoint comparisons (8 controls ×2 arrivals
×2 performance routes). Quality is separately required: WER/CER point deltas
not worse and ordinary upper bounds within0.5pp; literal equality is labeled
separately from tolerance-based noninferiority.

GO requires all8 independent comparisons in a declared arrival regime to show
either: consistent positive Goodput across all3 pairs and simultaneous lower
bound>0; or>=10% energy reduction, simultaneous upper energy bound<0, and
Goodput lower bound>=-2%, at the required quality. Safety, complete accounting
and independent input/Consumer/WAL audit are mandatory. A result equal to cost-
only/simple gates or attributable only to shared row delivery is NO-GO for
independent CES novelty. No acceptance, optimum or universal-superiority claim.

Any model/numerical, code or semantic failure is preserved and classified; it
does not authorize silent retries, changed baselines or parameter search on
validation. Original C1/C2/C3, prior V0/V1 NO-GO, Batch-dependent Input
Realization and previous negative results remain intact. No manuscript changes.

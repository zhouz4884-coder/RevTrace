# Online State-Admission Necessity and Cost — execution protocol v1

Only C1/C2 are expanded; retain C3. No original manuscript or frozen experiment
edits; no Elastic/DAG/V2/KV/independent GPU recovery continuation. Study root on
8TB: projects/revtrace_online_admission_20261022 and
results/revtrace/online_admission_20261022. Every run retains code/config/model/
data/environment/commands/raw timestamps and all negative results.

## Policies and fairness

All serving runs reserve the same FP16 Proposer GPU0 and FP32 target GPU1,
Qwen3-ASR-1.7B/eager/MB16/budget256/fine2s, actual released audio and full independent
sources. Same A/B/C/D1, durable group-ready WAL, trusted Render, whole-view
compatibility and actual two-lane consumer. Per-policy execution/selection rule
is honestly declared in chi; different legitimate histories are allowed.

- Clean Reference = fault-free Fine independent FP32 Authority; no duplicate
  differently named run. Fine independent Authority is also run with F2 affecting
  only Proposer, and remains a safety/cost control.
- Unprotected Feedback = waits for real FP16 candidate, deterministically
  reconstructs its fields under current parent, installs without FP32 selection.
  Explicit unsafe negative contract, not falsely labelled trusted FP32 generation.
  FP32 worker remains resident/idle; its GPU energy is still measured.
- Correct-context Score+Fallback = all candidate-token margins at correct target
  inputs, fixed threshold0.05, D1 stop/budget/Render conditions; low-score or malformed
  rows get actual FP32 generation fallback. Never call margin alone a certificate.
- Strict Verify+Fallback = all token argmax, EOS/budget and reconstructed projection
  under correct target input/FP32 contract; any failed row gets real independent
  FP32 generation. Preserve the submitted batch layout during fallback and bill all
  rows computed, including outputs not selected. No KV reuse or free failed work.
- DGFT Coarse = rho3 independent FP32 Authority, original protected coordination.
- Standard Safe Async Coarse = full conventional positive control with the same
  protection/continuity semantics; it is not intentionally incomplete.

Verify strategies use rho1 and wait for a real native candidate at that target;
its prior private ancestry may differ and is *not* mistaken for certified ancestry.
The correct target parent/audio/input are constructed independently. Candidate
wait and additional GPU costs are part of serving, not removed by offline timing.

## Traffic, fault and independent sources

Fault-free and controlled-F2 are distinct traffic arms. Inject once per session at
the first actual Proposer dispatch with end_window>=5 and chunk_id>=2, before model
execution. Wrong context comes from a frozen deterministic unrelated same-language
old E1 donor pool, chosen without confidence/quality/target-output selection.
It is a controlled context source substitution, not natural fault prevalence.
Normalize offered P/text from the actual wrong-context-generated Z under declared
parent so D1 consistency is not used as a substitute for selection. Preserve raw
wrong-context P/text, original job, actual consumed tokens/processor inputs and
normalization cost; no CPU reinterpretation is called correct-parent generation.

Formal source pool:16 full16–28s independent English Phase-D sources, not used to
choose E1/F2 faults. They have appeared in previous quality/load studies; do not
call them never-seen data. Pilot uses four separate Elastic source IDs (disjoint
utterances/speakers from the formal pool; verify before GPU). Donor pool is neither
pilot nor formal audio. Repeated windows/runs are not new speakers.

Candidate nominal fault opportunities, effective conditioning changes, changed Z,
admitted changed P and new future generation are separate denominators. Within-
method fault-free/F2 differences are attributed to propagation only when actual
pre-intervention processed input/state match and repeats support the comparison.
Otherwise retain them as unmatched total effects, not clean causal propagation.
Always distinguish future generated Z from copied prefix and final WER/CER.

## Pilot, freeze and formal scope

CPU first: malformed token/stop/projection, wrong parent/input/contract, no future
audio, candidate-not-ready wait, paid fallback, runtime/source mismatch, repeated
result, WAL replay and stale private publication checks. Fake outputs are CPU only.
Pilot then: six policies×fault-free/F2×four full independent sources. Strict/Score
pilot additionally executes target greedy Oracle and its same-input repeat at the
same actual processor batch; validates Oracle-as-candidate complete checking. All
diagnostic work is timed/billed but pilot is not formal serving performance.

No formal matrix launches until independent pilot audit confirms semantic/source/
stop/projection/input/oracle checks. Freeze source commit, all hardware/runtime
settings and exact run order after pilot. No outcome-selected fault/audio filtering.
Planned formal two workloads:16 sync streams; same16 streams as two8-stream cohorts
at0s and32s with within-cohort0.25s staggering. Actual overlap/queues come from logs.
Six strategies×two workloads×two traffic arms×three paired fresh repeats =72 cells.
The fixed workload definitions do not change if one method fails SLO or wins.

## Measurements and predeclared acceptance

Primary SLOs Display2s/Commit8s; supplementary grid D={2,5,8},C={4,8,12,16}.
Common2s and exact final audio frontiers, all incomplete frontiers remain as +inf.
Display=actual consumer view application; Commit=WAL-complete owner install;
separately retain first certified consumer availability. Audio Goodput=audio seconds
meeting both deadlines divided by full arrival+drain wall. Partial Goodput is not
whole-run P99 pass. Quality=full-source micro English WER/CER; capped/incomplete
content separate. No cherry-picking output quality differences across granularities.

Strict protected safety: zero unauthorised/incorrectly certified state entries;
any violation stops further formal issuance and is reported, not hidden by fallback.
Score false acceptance/rejection/detection uses full target oracle labels where
actually measured; unknown cases are not silently labelled correct. Report score
fallback rate and structural-vs-selection guarantees separately.

GPU J/audio-s: integrate both devices over strict serving window with>=99.5%
coverage, padding samples outside the measured window. CPU/IO/WAL, candidate wait,
verify, fallback, queue/preprocess/model/receive, render and consumer separate.
No physical cancellation of uncancellable calls; all submitted work is counted.

Performance claim: per frozen workload, DGFT must beat each best legal verification
alternative by >=5% primary dual-SLO Goodput with paired95% CI lower bound>0 and
all three repeat deltas positive, while WER/CER95% upper delta<=+0.5pp and no added
admission failure. Alternative cost claim requires>=10% lower strict GPU energy
with95% lower improvement>0, Goodput noninferiority2%, quality noninferiority and
no worse2% Display/Commit P99. Report all endpoints even if none passes. Bootstrap
10k,seed20261022,paired run/source; energy run-only. Conditional source resampling
does not rerun queues and cannot prove universal capacity.

P4 deliverables: raw index/config/source hashes, per-round traces and full cost
tables; controlled failures; Contribution–Evidence Matrix merging old feedback,
new online necessity/cost, repaired T1, D visibility and C3 recovery; eleven-page
candidate outline with claims/gates, not an edited original paper. Answer observed
future harm, alternative guarantee/cost, reproducible DGFT regimes and DSN viability
without guaranteeing acceptance or asserting a unique universally minimal protocol.

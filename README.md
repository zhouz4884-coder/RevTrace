# RevTrace

State-certified and risk-limited serving for revision-generative models.

RevTrace studies a systems problem that ordinary LLM batching metrics miss:
low-precision batching can change a generated revision, and a revision model
feeds that result back into its future state. A locally small numerical flip can
therefore become a persistent trajectory change.

The core execution contract is:

> A transition may enter future revision state only when its parent version
> matches the committed version and its state-entry evidence satisfies the
> selected certification mode.

## Current paper-facing result

The Phase 3A Qwen3-ASR deployment uses an FP16 batched proposer, an FP16
singleton verifier for risky intermediate revisions, a fixed-shape terminal
canonical path, versioned state commits, and a contract-scoped adaptive
controller. Thresholds are selected from a simultaneous confidence envelope;
they are not manually configured per stage.

| Model / active policy | Two-GPU wall speedup | GPU-normalized speedup | 2 s SLO goodput | Deadline miss | P99 state entry | Observed state violations |
|---|---:|---:|---:|---:|---:|---:|
| Qwen3-ASR-0.6B / `tau=0.05` | 5.99x | 3.00x | 5.99x | 0/240 | 1.336 s | 0/240 |
| Qwen3-ASR-1.7B / `tau=0.10` | 4.83x | 2.42x | 4.83x | 0/240 | 1.730 s | 0/240 |

The real Phase 3A controller trajectory is:

| Epoch | Contract fingerprint | Selected policy | Controller response |
|---:|---|---:|---|
| 1 | 0.6B / FP16 / c16 | `tau=0.05` | initial certification |
| 2 | 0.6B / FP16 / c64 | `tau=0.20` | new epoch and fail-closed contraction |
| 3 | 1.7B / FP16 / c16 | `tau=0.10` | model-drift contraction |
| 4 | 0.6B / FP16 / c16 | `tau=0.05` | fresh-epoch re-expansion |

Across the three deployed c16 epochs, the minimum wall-clock speedup is
`4.932x` and the minimum GPU-normalized speedup is `2.466x`, with zero
deadline misses and zero observed output, state, stale-result, or replay
violations. The c64 epoch remains fail closed because its terminal canonical
shape has not been independently certified.

Across five real two-GPU runs per active policy, mean wall speedups are
`6.052 +/- 0.128x` and `4.949 +/- 0.102x` (95% t intervals), with no deadline
miss, output/state violation, stale commit, or cross-run trace mismatch. The
active randomized shadow audits cover 30,025 and 30,155 risk-eligible execution
events; their anytime 95% state-disagreement upper bounds are 0.480% and 0.478%.
These observations do not establish deterministic arithmetic equivalence or a
production transcript-error rate.

Current decision:

`PHASE3A_ADAPTIVE_CONTROL_PASS_DETERMINISTIC_CERTIFICATE_UNRESOLVED`

## F5-F8 submission closure

The deployment-path, matched-energy, replication, and reporting protocols are
complete:

`F5_F8_PROTOCOL_CLOSURE_PASS_WITH_F7_TAIL_VARIANCE`

- **F5 deployed-path quality:** the full quality matrix now contains 1,280
  real ASR executions across two models, two languages, and five execution
  modes. The additional 256 executions use the real Phase-2 authority split:
  GPU-0 FP16 batched proposal, model-specific low-margin singleton authority,
  and GPU-1 FP16 fixed-shape b16 terminal authority. All four deployed cells
  are terminal-text exact with their paired singleton reference, have zero
  empirical WER/CER delta, zero catastrophic outliers, and zero online
  selection-authority violations. The 0/64 one-sided 95% terminal-mismatch
  upper bound remains 4.57% per cell.
- **F6 matched energy:** three paired c16/d30 runs per model sample both
  reserved RTX 3090s during both RevTrace service and all-canonical replay.
  Qwen3-ASR-0.6B achieves `5.890 +/- 0.111x` wall and
  `2.945 +/- 0.055x` GPU-normalized speedup while using
  `5.398 +/- 0.096` versus `27.450 +/- 0.041` J/audio-s. Qwen3-ASR-1.7B
  achieves `4.756 +/- 0.071x` and `2.378 +/- 0.036x`, using
  `8.166 +/- 0.131` versus `31.312 +/- 0.191` J/audio-s. Online stale/replay
  events and matched canonical replay output/state disagreements are all zero.
- **F7 independent steady seeds:** the restored c14 contract is repeated
  without another 1,350-event cold certification. Across three independent
  six-episode seeds, goodput is `15.874 +/- 0.588` state entries/s, energy is
  `9.450 +/- 0.208` J/audio-s, and verification is
  `8.545 +/- 0.437%`. Every seed has zero unverified fast-path replay roots.
  Tail behavior is not hidden: two seeds have zero deadline misses, while the
  first has two synchronized rounds above 2 seconds (28 event-level misses)
  and P99=2.028 s; mean P99 is 1.916 s.
- **F8 evidence separation:** `fp32_fixed_contract` replaces the overbroad
  reproducibility label; empirical `[0,0]` bootstrap deltas are not population
  equivalence; terminal/nonterminal verification is separated; comparison,
  safe-frontier, and energy-frontier eligibility are distinct; and every
  frozen contract explicitly records
  `end_to_end_invariance_verified=false`.

See the
[final closure report](results/final_closure/REPORT.md),
[machine-readable summary](results/final_closure/summary.json), and
[hash-audited compact artifact](artifact/final-evaluation-closure-v1).

## Tail-robust admission closure

The F7 tail variance is closed without relabeling the rejected c14 result:

`TAIL_ROBUST_C12_PASS_WITH_120S_AGE_BOUNDARY`

- An instrumented same-seed c14 run reproduced three rounds above the
  preregistered 1.9-second admission guard. All three execute the proposer and
  then a selective canonical batch serially. The selective-nonterminal P99 is
  1.995 s, versus 1.308 s for terminal canonical rounds and 0.846 s for the
  unverified fast path. No cross-round verifier backlog or thermal-throttling
  signature was observed. The historical c14 point remains rejected.
- A dedicated c12 calibration process issued the dynamic threshold
  `tau=0.0625` after 1,369 audits, with anytime state-risk upper bound
  `0.499706%`. Five subsequent processes froze that threshold and used
  disjoint seeds.
- Across 5,400 held-out events / 450 release rounds, seed P99 values are
  1.704, 1.877, 1.756, 1.862, and 1.797 s. The maximum is 1.877 s and the
  one-sided cross-seed 95% upper bound is 1.868 s, both below the 1.9-second
  guard. The terminal and nonterminal upper bounds are 1.271 and 1.748 s,
  respectively. Deadline-miss rounds, online selection-authority violations,
  and unverified fast-path replay roots are all zero.
- The conservative c12 reshape retains 87.7% of the rejected c14 mean
  goodput and increases mean J/audio-s by 9.6%, while reducing the cross-seed
  P99 upper bound from 2.079 to 1.868 s.
- The original cyclic/rolled 120-second c12 profile reported a 5.295 s final
  age-bucket P99, but protocol repair showed that number mixed a real
  long-history cost with confounders in input construction, authority shape,
  and timing attribution. It is retained as historical failure evidence, not
  as the causal long-horizon estimate.
- Under the repaired natural-input protocol, continuous service still fails
  the two-second SLO (P99 2.393 s; 8/60 miss rounds). Checkpoint-and-Rebase
  lowers independently confirmed P99 to 1.937 s with 0/60 miss rounds,
  dynamically learns `tau=0.031251`, records zero observed output/state/
  authority violations, and keeps certificate/replay 95% upper bounds at
  0.4997%/0.4152%. It therefore restores the deployed two-second SLO, but
  misses the preregistered 1.9-second admission guard by 0.037 s. The strict
  guard is not relabeled as a pass.

See the
[tail-robust closure report](results/tail_robust/REPORT.md),
[admission protocol](docs/protocols/TAIL_ROBUST_ADMISSION_CONTRACT.md), and
[change/failure diagnosis](docs/reports/tail_robust_change_diagnosis.md).
The repaired long-horizon evidence is in the
[protocol-repair report](docs/reports/long_horizon_protocol_repair.md) and
[machine-readable summary](results/long_horizon/long_horizon_summary.json).

## Phase 3B--3D bounded results

Phase 3B retrospectively replayed 2,000 audit schedules over 1,550 measured
labels. Margin-prioritized idle auditing raised failure-detection probability
from `0.644` to `1.000` while reducing median verifier requests from `283` to
`226`. The more complex VOI policy also detected every replayed failure but
used three additional median requests; because the pool contains only one
unique failing job, VOI superiority and live SLO preservation remain
unresolved. Idle labels remain outside the formal certificate.

Phase 3C found many execution-shape output flips, but strict deduplication
yielded only `19` and `15` legal state pairs for the 0.6B and 1.7B models,
below the preregistered `50`-pair population gate. The mechanism is real but
heterogeneous: natural 0.6B pairs have mean RAF `9.357`, half-life `2`
revisions, and `50%` terminal difference, whereas natural 1.7B pairs have RAF
`1.0`, half-life `1`, and zero terminal difference. Stress evidence is kept
separate and is not used as a production prevalence estimate.

Phase 3D executed Voxtral Mini 4B Realtime for 10 growing-prefix revisions and
120 execution rows. No singleton-repeat, cross-shape, or replicated-row
mismatch was observed. Because decoded text is not fed back into the next
transition, Voxtral establishes an append-only architecture boundary rather
than a second instance of Qwen3-ASR state pollution. Zero observed flips is
not a deterministic certificate.

## Phase 4 adaptation and feedback results

Phase 4A replaces a hand-written threshold ladder with a continuous
split-sample risk window. On the frozen c16-to-c64-to-c16 replay it selected
observed margin boundaries `0.0625 -> 0.109375 -> 0.0625`, invalidated evidence
at each contract switch, and kept every held-out upper risk bound below 0.5%.
This establishes fail-closed controller semantics; it is not a new live c64
serving result.

Phase 4B provides the positive second-family result. Two real Whisper
checkpoints were evaluated on 100 disjoint 90-second streams each. Legal
singleton-versus-batch execution produced 21 distinct state pairs. Eight pairs
propagated when previous text was fed into the next window, while zero
propagated when the same model and future audio were replayed with feedback
disabled. Whisper-base contained six pairs still different at the two-window
horizon, including RAF values up to `153`. No preregistered application
catastrophe occurred, so RevTrace does not claim hallucination-loop prevention.

Phase 4C freezes full-request SlackGuard as a physical NO-GO: the measured
309.9 ms audit quantum is `11.27x` the 27.5 ms P99 intrusion budget, and CUDA
stream priority cannot preempt a running kernel. Phase 4D completed the
500-candidate budget per Qwen3-ASR model. Active mining improved distinct-pair
yield by `2.78x` and `2.54x`, but found only 8 and 5 pairs rather than 50;
population generality remains outside the claim.

Phase 4 decision:

`PHASE4_TASKS_COMPLETE_WITH_BOUNDED_NEGATIVE_GATES`

## Phase 5 system-hardening results

Phase 5 completes all A--E work packages and freezes the decision:

`PAPER_CORE_GO_WITH_PHASE5_MEASURED_BOUNDARIES`

The live c16 -> c64 -> c16 controller learns thresholds
`0.03125 -> 0.015625 -> 0.015625` from fresh contract epochs. It reaches
21.01, 42.90, and 22.31 state-entry events/s, but rare post-certification
disagreements remain and c64 has 448 two-second deadline misses. The controller
therefore demonstrates live risk adaptation, not deterministic exactness.

Whisper protection closes all 21 known feedback-bearing state pairs with zero
observed output/state violation, but all-state-entry canonical execution is a
1.00x performance boundary. When previous-text feedback is disabled,
certification is bypassed: tiny/base obtain 6.12x/6.44x wall speedup and local
batch differences do not create any state-propagation violation.

The eight-cell Qwen3-ASR workload matrix spans 2.93x--6.77x wall speedup and
1.47x--3.38x GPU-normalized speedup. Seven cells have zero observed state
violation and two have zero deadline misses. One unseen c32/Chinese/burst
contract exceeds the frozen c16 risk boundary; the result is retained rather
than repaired with a post-hoc threshold.

Live release-aware audit packing preserves outputs and has zero deadline
misses, but raises mandatory P99 by 2.35%, above its frozen 2% limit, so the
optimization is stopped. The Phase 5 artifact also freezes 72 distinct
consequential state pairs and explicitly excludes production-prevalence
claims.

See the
[Phase 5 report](docs/reports/phase5_system_hardening_report.md) and
[paper-facing tables](results/phase5/PAPER_TABLES.md).

## Phase 6 submission-repair results

Phase 6 completes the evidence-lifecycle, contract-scoping, joint risk--SLO
admission, feasible adaptation, and artifact-freeze work packages:

`PHASE6_SUBMISSION_REPAIRS_COMPLETE`

Positive certificates are now keyed by the exact execution contract and
restored only after renewal canaries. Counterexamples raise contextual floors
inside their measured applicability cone; contract or policy epoch changes
fence stale results. The exact 0.6B/c32/120-second/burst/Chinese repair catches
the known margin-0.109375 event with zero state violations, but its 6.107 s P99
and 1,266 deadline misses keep it outside the two-second service region.

The joint admission controller therefore rejects c64 as offered and reshapes
active service to c16, where guarded P99 is 1.397 s with zero deadline misses.
In the live English-c16 -> Chinese-c16 -> English-c16 sequence, the two new
population contracts learn independently. Returning to the exact English
contract performs 64 renewal canaries before restoring its certificate,
reducing recertification events by 95.29% versus flat relearning. Cross-contract
reuse, deadline misses, and observed state violations are all zero.

The learned thresholds (`0.031251` for English and `0.015626` for Chinese) are
outputs of the live split-sample risk controller plus observed failure floors;
they are not a fixed hand-written threshold ladder. Their upper risk bounds are
statistical (at most 0.5%), not deterministic arithmetic certificates.

See the
[Phase 6 report](docs/reports/phase6_submission_repair_report.md),
[paper-facing tables](results/phase6/PAPER_TABLES.md), and
[audited artifact](artifact/phase6-submission-repairs-v1).

### Phase 7 frozen reviewer-defense status

`PHASE7_REVIEWER_DEFENSE_COMPLETE_WITH_COMPATIBILITY_BOUNDARIES`

Phase 7 adds exact-signature/certificate-bound reshaping, public-source SOTA
probes, faithful MarginGate/RW-TTT/LLM-42 revision adaptations, a seven-step
causal ablation, full c64 queue accounting, and delta sensitivity. The live
64-offered/16-active run drains 1,920 audio-seconds in 55.678 seconds
(34.484 audio-s/wall-s), with active P99 1.942 seconds and end-to-end P99
44.797 seconds after queueing. The legacy audit fields contain three selected
vs later-replay output disagreements and one state disagreement. They decompose
into zero online selection-authority violations, one canonical replay state
disagreement, and zero stale/epoch commits. Because events are temporally and
batch correlated, Phase 7D reports the realized 1/960 replay-disagreement rate
without an iid population interval.

The active P99 is below the hard two-second deadline, but adding the frozen
100 ms capacity guard gives 2.042 seconds. This overload/backpressure result
therefore does not pass the guarded admission contract.

Phase 7.1 repaired the evidence taxonomy and added a fresh c14 capacity point.
Across 1,470 live events, c14 measured P99 1.413 seconds and guarded P99
1.513 seconds, with zero deadline miss and zero observed output/state replay
disagreement. This passes the 100 ms headroom contract. Its 93.33% verifier
fraction is dominated by the pre-registered 1,350-event cold-start evidence
window, so it is a capacity point rather than a steady-state throughput
headline. Phase 6D and Phase 7D are now explicitly recorded as distinct
float32 and float16 authoritative-execution contracts, respectively.

The failed mixed-language certificate-transfer run is retained because it
demonstrates why an unobserved execution signature cannot inherit an English
certificate. See the
[Phase 7 report](docs/reports/phase7_reviewer_defense_report.md),
[Phase 7.1 correction and performance report](docs/reports/phase7_1_corrections_and_performance.md),
[collision matrix](docs/research/phase7_related_work_collision_matrix.md), and
[paper tables](results/phase7/PAPER_TABLES.md).

### Checkpoint-20 submission evidence closure

`REVTRACE_EXPERIMENTAL_EVIDENCE_COMPLETE_FOR_FGCS_SUBMISSION`

The repaired long-horizon contract keeps low-margin nonterminal output
provisional instead of synchronously selecting it as textual feedback state.
Every 20 seconds, a fixed-B=12 FP16 canonical checkpoint reconstructs the
authoritative segment; terminal revisions use the same canonical authority.
This removes the rare singleton-verification stall that caused the earlier
120-second tail regression without calling the provisional candidate exact.

Across five frozen 120-second seeds (3,600 revision opportunities and 3,539
committed state transitions), the worst
per-session event P99 is 1.414 seconds, total deadline misses are zero, and
online selection-authority violations are zero. Fixed checkpoint authority
runs on 10% of opportunities (6 of 60 rounds), synchronous low-margin
verification is zero, and the service holds back 61 low-margin provisional
candidates (1.883% of non-checkpoint opportunities). A separate
pre-outcome randomized audit covers 30,423 admitted high-margin state entries
and yields a 95% time-uniform state-risk UCB of 0.4733%.

The final paired quality gate uses the deployed GPU-0 ordinary FP16 B=12
proposer and GPU-1 batch-invariant FP16 fixed-B=12 authority on 32 English and
32 Chinese 120-second sessions. Relative to continuous full history, observed
mean deltas are +0.929 percentage points WER and +1.149 percentage points CER,
with zero catastrophic outliers. Holdback itself adds +0.027 points WER and
-0.027 points CER relative to synchronous checkpoint verification. Both
observed means pass the pre-registered 2-point gate, but the paired-bootstrap
upper bounds are 2.051 and 2.462 points; the exact conclusion is
`POPULATION_NONINFERIORITY_UNRESOLVED`.

Five real-model semantic patterns pass: a holdback advances accumulated audio
but cannot update text, language, or chunk version; service, quality, and
replay checkpoint payloads agree; and checkpoint reset is reconstructible.
The deployed quality trace contains 75 provisional holdbacks (2.170%). Their
P50/P95/maximum lifetime is 2/4/6 seconds; 93.33% resolve at the next
high-margin update, 69.33% preserve all already displayed normalized units,
and the original provisional-to-authority overwrite mean is 7.20%. A
continuous display audit reconstructs 69 resolution episodes, including three
multi-holdback bursts with maximum length three. Across the actual
P1->P2->...->authority transitions, overwrite mean/P95/max is
8.01%/48.73%/100%; episode cumulative churn mean/P95/max is
0.087/0.655/1.399. Normal appended text is excluded from overwrite cost, and
an empty provisional display has overwrite zero.

Every selected artifact is content-addressed under mechanism digest
`fa7c07c28da4bf24a52e87a9d83d4671066ee9c1744b4aa21eeddf69c2476583`.
The finalizer rejects changed raw files, runner-role changes, a different
model/data/runtime fingerprint, legacy B=8 single-engine quality, and the
fixed-B=2 or dual-lane NO-GO branches.

The final audit also byte-hashes all 128 source audio files and records both
GPU UUIDs, package versions, the Qwen-ASR source tree, and the authority
runtime. This identity extension is a post-run attestation, not a retroactive
change to the mechanism digest. Quality sessions contain no within-session
source repetition, but all 64 sources per language are reused across sessions
and each language forms one connected source-overlap component. Consequently,
the paired bootstrap is descriptive for the frozen constructed-session sample;
it is not an independent-source population interval.

The failed two-episode calibration is retained: it showed that the original
split did not provide enough admitted validation events and contaminated the
held-out service stage with fail-closed verification. The repaired calibration
uses three episodes and freezes the threshold before held-out execution.

See the
[submission evidence report](docs/reports/checkpoint20_submission_closure.md),
[protocol](docs/protocols/checkpoint20_holdback_authority_closure.md), and
[machine-readable summary](results/checkpoint20_holdback_authority/final_summary_v2.json).

## Phase map

- **Phase 0 — discovery and causal controls:** RevBatch performance opportunity,
  same-input/repeated-run controls, precision interventions, legal selective
  oracle, and state-projection analysis.
- **Phase 1 — deployed system baseline:** real two-GPU proposer/verifier service,
  versioned state commit, terminal work stealing, natural traces, and flip-rich
  stress.
- **Phase 2 — tail and risk contract:** terminal-reserved state-commit EDF,
  fixed-probability anytime risk-limiting audits with frozen margin-stratum
  diagnostics, and a `<1%` deadline-miss gate.
- **Phase 3A — adaptive control (pass):** contract-scoped certificate
  epochs, simultaneous policy confidence envelopes, permanent failure-ledger
  exclusions, risk/queue-priced policy selection, and dual-channel auditing.
- **Phase 3B — dual-channel idle auditing (bounded diagnostic pass):** compare fixed-probability base
  audits, base plus idle audits, margin-only idle audits, and
  value-of-information idle audits without contaminating the formal
  certificate.
- **Phase 3C — state-pollution dynamics (population gate not met):** estimate Revision Impulse Response
  survival curves, pollution half-life, Revision Amplification Factor, and
  Numerical State Exposure from legal state-entry flip pairs.
- **Phase 3D — second-architecture boundary (pass):** test whether Numerical State
  Exposure predicts the certification strength needed by another
  feedback/revision architecture.

Preventive deterministic execution remains a strong supporting baseline, and
paper/artifact freezing follows completion of Phase 3A--3D; neither is a
renumbered Phase 3 work package.

Phase 4 adds the certified-risk-window replay, the Whisper feedback
intervention, the SlackGuard physical stop gate, and diversity-aware state-pair
mining. Its bounded negatives remain first-class results rather than being
hidden by new thresholds or relaxed pair definitions.

See [the phase roadmap](docs/roadmap/PHASES.md) and
[claim boundaries](docs/CLAIM_BOUNDARIES.md).

## Repository layout

```text
artifact/       frozen, hash-audited evidence bundles
configs/        experiment gates and the experiment registry
deployment/     service topology and deployment records
docs/           reports, protocols, roadmap, and research notes
exports/        generated paper tables/figures (local by default)
logs/           local transient logs (large logs stay on the experiment disk)
Paper/          manuscript source
results/        compact registered results organized by phase
scripts/        finalizers, validators, artifact builders, and remote runners
src/revtrace/   state-transaction implementation
submission/     submission checklists and frozen release material
tests/          semantic, gate, manifest, and regression tests
third_party/    pinned external code references
tmp/            disposable local work
```

## Reproduce the frozen checks

```powershell
python -m pytest -q
python scripts/validate_repository.py
```

Remote experiments use `scripts/remote/` and write large state under:

```text
<DATA_ROOT>/projects/revtrace
<DATA_ROOT>/results/revtrace/<phase>/<experiment_id>
<DATA_ROOT>/logs/revtrace/<phase>/<experiment_id>
```

The source extraction provenance is recorded in
[`docs/PROVENANCE.md`](docs/PROVENANCE.md).

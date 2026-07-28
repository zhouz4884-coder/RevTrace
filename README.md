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

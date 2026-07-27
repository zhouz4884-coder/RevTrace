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

The frozen Phase 1 Qwen3-ASR deployment uses an FP16 batched proposer, an FP16
singleton canonical verifier, versioned state commits, and terminal work
stealing.

| Model | Two-GPU wall speedup | GPU-normalized speedup | 2 s SLO goodput | P99 reduction | Observed state violations |
|---|---:|---:|---:|---:|---:|
| Qwen3-ASR-0.6B | 5.53x | 2.77x | 5.23x | 38.3% | 0/240 |
| Qwen3-ASR-1.7B | 4.75x | 2.38x | 4.49x | 41.7% | 0/240 |

The flip-rich safety stress suite contains 1,021 real execution-shape flips and
zero observed margin-gate false-safe events. These observations do not establish
a deterministic certificate or a production error rate.

Current decision:

`DEPLOYED_SYSTEM_GATE_PASS_DETERMINISTIC_CERTIFICATE_UNRESOLVED`

## Phase map

- **Phase 0 — discovery and causal controls:** RevBatch performance opportunity,
  same-input/repeated-run controls, precision interventions, legal selective
  oracle, and state-projection analysis.
- **Phase 1 — deployed system baseline:** real two-GPU proposer/verifier service,
  versioned state commit, terminal work stealing, natural traces, and flip-rich
  stress.
- **Phase 2 — tail and risk contract:** terminal-reserved state-commit EDF,
  stratified anytime risk-limiting audits, and `<1%` deadline-miss gate.
- **Phase 3 — amplification:** Revision Impulse Response, Revision Amplification
  Factor, Numerical State Exposure, and amplification-aware verification.
- **Phase 4 — generality:** a second feedback/revision architecture.
- **Phase 5 — deterministic baseline:** Qwen3-ASR-compatible preventive
  batch-invariant execution or another independently certified canonical path.

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

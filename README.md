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
- **Phase 3B — amplification:** Revision Impulse Response, Revision Amplification
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

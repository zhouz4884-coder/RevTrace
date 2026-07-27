# RevTrace Phase 2 frozen artifact

Decision: `PHASE2_RISK_AND_TAIL_GATE_PASS_DETERMINISTIC_CERTIFICATE_UNRESOLVED`

This bundle contains compact real two-RTX-3090 system records, five-run
replication tables, randomized shadow-audit evidence, negative interventions,
the frozen risk protocol, exact runner sources, and SHA-256 manifests.

Evidence boundaries:

- performance numbers are measured wall-clock and GPU-normalized results;
- natural audit rows are repeated execution events, not independent utterances;
- the risk bound is disagreement with a frozen canonical execution, not WER;
- zero observed errors are not a deterministic arithmetic certificate;
- v1 failures remain evidence and are not relabeled as v2 validation;
- full logs, models, caches, and environments remain on the experiment disk.

Validate from the repository root:

```powershell
python -m pytest -q
python scripts/validate_repository.py
```

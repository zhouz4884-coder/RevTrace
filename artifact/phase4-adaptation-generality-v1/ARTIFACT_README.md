# RevTrace Phase 4 adaptation and generality artifact

This compact artifact contains the Phase 4 configurations, executable analysis
and remote-runner code, semantic tests, exact compact result records, and the
claim-boundary report.

Evidence tiers remain separate:

- `risk_window` is split-sample controller replay, not a live c16/c64 service;
- Whisper results use real weights and legal execution-shape interventions;
- SlackGuard records a physical NO-GO for full-request audit quanta;
- active-mining yield is targeted mechanism coverage, not production
  prevalence.

Run the local checks from the repository root:

```powershell
python -m pytest -q
python scripts/finalize_phase4.py
python scripts/validate_repository.py
```

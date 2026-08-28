# Senior-author figure QA

The corrected senior-author artwork for Figures 1--3 was accepted on
2026-08-28. Alternative Visio redraws were rejected because they reduced the
information density and visual hierarchy of the supplied figures.

## Technical review

- **Figure 1:** the two executions share parent `H_t/V1`; the outputs are
  `Y_t^a` and `Y_t^f`; their post-output states are canonical
  `H_{t+1}^a/V2` and contaminated `H_{t+1}^f/V2`. The 8/21, 0/21, and measured
  tail RAF=153 annotations match H1. Panel B is English-only and uses the
  paper's fork-free-history and granularity-independent-safety terminology.
- **Figure 2:** proposer/authority separation, projection adapter, certificate,
  parent-version/frontier checks, ledger, and dual display/commit clocks match
  the system. FP16/FP32 are labeled as evaluated implementations, R4 is scoped
  to risk/coverage evidence, and authorization binds certificate and parent
  version.
- **Figure 3:** all four certification strata and their no-transfer boundaries
  match H5. Stratum IV states the complete, separate estimands: Qwen mixed-unit
  edit rate versus FP16 singleton and Whisper paired WER delta versus
  unprotected feedback. These quantities are never pooled.
- All three supplied figures are 2400x1792 pixels and exceed 350 effective ppi
  at their frozen manuscript widths.

## Manuscript review

- Final length: 18 pages.
- No blocking overfull float, undefined reference, or Type 3 font issue.
- No visible clipping or overlap after placement at the frozen widths.
- Repository test suite: 258 passed.

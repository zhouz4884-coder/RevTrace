# RevTrace Phase 3 evidence index

Phase 3 keeps controller, diagnostic, causal-dynamics, and architecture-boundary
evidence separate.  A PASS in one package does not silently promote an
unresolved claim in another.

| Work package | Evidence | Status |
|---|---|---|
| Phase 3A adaptive control | [`adaptive_control/summary.json`](adaptive_control/summary.json) | adaptive controller gate passed; deterministic arithmetic certificate unresolved |
| Phase 3B dual-channel idle auditing | [`idle_audit/summary.json`](idle_audit/summary.json) | bounded retrospective diagnostic pass; VOI advantage and live SLO unresolved |
| Phase 3C Revision Impulse Response | [`rir_population/summary.json`](rir_population/summary.json) | mechanism confirmed; 50-pair population gate not met |
| Phase 3D second architecture | [`second_architecture/summary.json`](second_architecture/summary.json) | append-only boundary passed; zero observed flips is not a certificate |

The paper-facing performance result remains Phase 3A.  Phase 3B does not claim
live serving performance, Phase 3C stress inputs do not estimate production
prevalence, and Phase 3D growing-prefix inference is not presented as a vLLM
websocket-serving benchmark.

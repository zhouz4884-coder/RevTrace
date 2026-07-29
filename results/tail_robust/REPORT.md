# RevTrace Tail-Robust Admission Closure

Decision: **TAIL_ROBUST_C12_PASS_WITH_120S_AGE_BOUNDARY**

## R1 - F7 slow-round diagnosis

Decision: **C14_GUARD_TAIL_REPRODUCED_WITHOUT_DEADLINE_MISS**

The original c14 evidence remains rejected by the multi-seed capacity
certificate. The instrumented rerun is used only to identify reproduced
critical-path behavior; it is never substituted for the historical negative.

- Instrumented rounds: 270
- Instrumented deadline-miss rounds: 0
- Instrumented rounds above the 1.9-second admission guard: 3
- Reproduced deadline-miss classification: `none`
- Guard-tail classification: `{'serial_proposer_then_selective_canonical': 3}`
- Runtime fact: the runner allows at most one fixed-shape canonical batch per release round and waits before state commit; it has no cross-round verifier backlog
- Unverified fast-path P99: 0.8463251394964756 s
- Terminal canonical P99: 1.3081940800882876 s
- Selective nonterminal P99: 1.9945126381516456 s

## R2 - Cluster-aware capacity certificate

The statistical unit is a synchronous release round. Admission requires both
the maximum held-out seed P99 and the one-sided cross-seed 95% upper bound to
remain below 1.9 seconds, zero miss rounds, risk upper bound at most 0.5%, and
zero online selection-authority violations.

Historical c14 accepted: **False**

C12 terminal seed-P99 U95/max=1.271/1.283s; nonterminal seed-P99 U95/max=1.748/1.764s.

## R3 - c12 five-process heldout

accepted=True, max seed P99=1.877s, U95=1.868s, miss rounds=0

| Process | P99 (s) | Miss rounds | Verify fraction | Goodput | Online authority violations |
|---|---:|---:|---:|---:|---:|
| heldout_seed_1 | 1.704 | 0 | 8.333% | 14.937 | 0 |
| heldout_seed_2 | 1.877 | 0 | 9.815% | 12.854 | 0 |
| heldout_seed_3 | 1.756 | 0 | 8.796% | 14.238 | 0 |
| heldout_seed_4 | 1.862 | 0 | 8.796% | 14.077 | 0 |
| heldout_seed_5 | 1.797 | 0 | 9.537% | 13.507 | 0 |

Relative to the rejected historical c14 point, c12 retains 87.7% of mean goodput, increases mean J/audio-s by 9.6%, and reduces the cross-seed P99 upper bound from 2.079s to 1.868s.

## R4 - State guarantee

RevTrace provides **version-linearized state-commit ordering** and
**risk-bounded semantic conformance**. It does not make nondeterministic
inference deterministic.

## R5 - 120-second age profile

C12_120S_AGE_PROFILE_CAPACITY_BOUNDARY, P99=5.367s, miss events=240

| Session age (s) | Rounds | P99 (s) | Maximum (s) | Miss rounds | Mean proposer (s) | Mean canonical (s) | Mean output tokens |
|---|---:|---:|---:|---:|---:|---:|---:|
| 0-30 | 15 | 1.904 | 1.942 | 0 | 0.617 | 0.305 | 11.8 |
| 30-60 | 15 | 1.956 | 2.017 | 1 | 0.940 | 0.078 | 12.1 |
| 60-90 | 15 | 4.486 | 4.725 | 5 | 1.615 | 0.253 | 15.2 |
| 90-120 | 15 | 5.295 | 5.367 | 14 | 1.911 | 0.721 | 15.4 |

## Operating envelope

The former Pareto table is reorganized into certified production contracts,
a robust reshape contract, and deliberate boundary probes. No boundary probe
is counted as a failed production contract.

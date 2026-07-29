# Tail-Robust Closure: Change and Failure Diagnosis

This file separates changes to the research mechanism from changes made only
to observe or operate the experiment.

## Research-protocol changes

- The historical c14 point remains rejected. No rerun may overwrite its two
  observed deadline-miss rounds.
- The fixed reshape is c12. It was chosen before any c12 candidate sweep.
- One dedicated c12 process calibrates the dynamic risk threshold. Five fresh
  processes then use that frozen threshold on disjoint seeds.
- Capacity is certified with release rounds as the tail unit, a one-sided
  cross-seed 95% P99 bound, a 0.1-second SLO guard, zero miss rounds, the
  frozen risk upper bound, and zero online authority violations.
- The 120-second age profile is conditional on the c12 30-second held-out
  contract passing.

## Instrumentation changes

`scripts/remote/run_phase5a_live_adaptive.py` now records, per release round:

- proposer, canonical execution, verifier collection, commit, and total
  state-entry latency;
- terminal status, low-margin count, verification count, fixed shape, and
  selected token lengths;
- verifier dispatch/backlog fields; and
- sampled GPU power, SM clock, and temperature.

These fields diagnose the critical path. They do not change the proposal,
selection, canonical, or state-update rules.

## Code defect found before a scientific result

The first instrumentation draft computed token-count telemetry by iterating the
last selected candidate dictionary rather than the list of selected candidates.
Static review found the error before an output file was produced. The fix
introduced an explicit `round_selected_records` list. No prior paper result was
changed and no failed scientific cell was discarded.

## Environment failure

Stopping the first diagnostic process left a re-parented vLLM EngineCore
process holding approximately 16.9 GiB on one RTX 3090. The next verifier
failed startup because only 6.77 GiB remained free. The exact orphan process
was identified through `nvidia-smi` and its parent chain, then terminated.
The orchestration script now fails before launch if either of the two GPUs has
less than 20,000 MiB free and prints the occupying compute processes.

This was a process-lifecycle failure, not evidence about c14 tail behavior or
the RevTrace mechanism.

## Measured mechanism diagnosis

The instrumented c14 rerun contains 270 release rounds. It does not reproduce
the historical two rounds above 2.0 seconds, but it does reproduce three
rounds above the 1.9-second admission guard. All three are selective
nonterminal rounds that execute the proposer before the fixed-shape canonical
path:

- total latency: 1.992, 1.998, and 1.916 seconds;
- proposer latency: 0.959, 0.717, and 0.777 seconds;
- canonical execution: 1.015, 1.233, and 1.075 seconds.

The corresponding class P99 values are 0.846 seconds for unverified fast-path
rounds, 1.308 seconds for terminal canonical rounds, and 1.995 seconds for
selective nonterminal rounds. There is no cross-round verifier backlog.
Guard-exceeding rounds are no hotter and do not have lower minimum SM clocks
than the within-guard population, so measured telemetry does not support
thermal throttling as the explanation.

## Result of the fixed reshape

The preregistered c12 reshape passes all admission gates over five independent
processes. It reduces the cross-seed P99 upper bound from 2.079 to 1.868
seconds while retaining 87.7% of historical c14 mean goodput. The cost is a
9.6% increase in mean J/audio-s. This is the measured tradeoff that solves the
30-second F7 tail-robustness problem.

The 120-second extension is not solved by c12: proposer mean latency grows from
0.617 to 1.911 seconds across the four age buckets, canonical mean latency
from 0.305 to 0.721 seconds, and commit work from 0.027 to 0.238 seconds.
Twenty of 60 release rounds miss the deadline. This is retained as a
duration/cumulative-context boundary for future work.

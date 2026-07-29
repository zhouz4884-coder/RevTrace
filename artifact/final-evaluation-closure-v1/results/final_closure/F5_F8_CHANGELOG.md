# F5-F8 protocol-closure change log

This log separates changes to the original research idea from implementation
repairs and reporting-only repairs.

## F5 - Deployed-path quality

- Classification: protocol gap, not a failure of the RevTrace mechanism.
- Previous behavior: `run_final_quality_mode.py` used a local singleton draw
  for every authoritative RevTrace verification.
- New behavior: `run_f5_deployed_quality.py` reproduces the frozen Phase-2
  authority split. The FP16 batched proposer and low-margin intermediate
  singleton execute on GPU 0; every terminal revision is selected from a real
  GPU-1 FP16 fixed-shape b16 draw.
- Protocol repair during closure: the initial wrapper incorrectly applied
  the 0.6B `tau=0.05` policy to 1.7B. The final 1.7B English and Chinese
  cells were rerun with the independently validated headline `tau=0.10`.
- Research idea changed: no.
- Evidence changed: four additional model-language cells, 256 utterances.

## F6 - Matched energy

- Classification: implementation/protocol accounting bug found during F6.
- Rejected first attempt: the all-canonical audit executed a singleton for
  every terminal item and then also executed the fixed-shape terminal
  authority, while timing only the discarded singleton path. These runs were
  deleted and are not used.
- Repair: `run_revtrace_dual_gpu.py` now executes 224 intermediate singleton
  transitions plus one terminal fixed-shape batch for the c16/d30 contract.
  It records terminal batch latency for every affected request and counts the
  batch wall time once in the all-canonical baseline.
- Protocol repair during closure: the unfinished 1.7B `tau=0.05` run was
  stopped before producing a result. All final 1.7B energy repetitions use
  the headline `tau=0.10`; 0.6B remains at `tau=0.05`.
- Reporting repair: the old
  `proposer_gpu_terminal_verified_events` counter actually counted local
  low-margin intermediate verification. It is renamed
  `proposer_gpu_intermediate_verified_events`; terminal and nonterminal
  verification fractions are now derived separately from event records.
- Runner repair: a scientifically valid completed run that returns the older
  mechanism-gate code `2` is retained and the remaining preregistered
  repetitions continue. Only a missing result file or an unexpected exit
  aborts F6.
- Research idea changed: no.
- Expected scientific effect: a stronger all-canonical baseline and therefore
  a more conservative speedup and energy comparison.

## F7 - Steady-state replication

- Classification: replication closure.
- The prior certified c14 threshold is restored; the 1,350-event cold
  certification is deliberately not repeated.
- Three independently seeded six-episode stages run under the same frozen
  contract. Post-stage replay remains excluded from service time.
- Result boundary: seed 1 contains two synchronized rounds above the 2-second
  deadline (28 event-level misses, P99 2.028 s); seeds 2 and 3 have zero
  misses. The protocol is complete with measured tail variance, not an
  all-seed SLO pass.
- Classification repair: stage `output_violations` and `state_violations`
  compare the selected online trace with a later independent canonical replay.
  They are renamed as replay disagreements and are not counted as online
  selection-authority failures. All three seeds have zero unverified
  fast-path replay roots.
- Research idea changed: no.

## F8 - Reporting repair

- `fp32_reproducible` is reported as `fp32_fixed_contract`.
- A `[0, 0]` paired bootstrap interval is labeled as an empirical holdout
  delta, not a population-equivalence proof.
- Terminal and nonterminal verification fractions are separate.
- `comparison_eligible`, `safe_frontier_eligible`, and
  `energy_frontier_eligible` are separate.
- Every contract records `end_to_end_invariance_verified=false`.
- Canonical replay disagreement remains separate from online selection
  authority.

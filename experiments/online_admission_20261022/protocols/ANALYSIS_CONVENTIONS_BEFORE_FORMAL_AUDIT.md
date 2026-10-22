# Analysis conventions fixed before inspecting formal outcome tables

The source, workload, safety requirements and numerical gates remain those of
FORMAL_FREEZE.json, PROTOCOL.md and FORMAL_ESTIMANDS_PRE_FREEZE_v2.md. This file
specifies the mechanical estimator, not a new success criterion. At this point
only completion counts/identities have been inspected, not formal metric tables.

* Every completed and failed cell is reconciled with the frozen 72 entries.
  Missing frontiers stay in the population as infinite latency/zero good audio.
  A terminal failure is not silently rerun or dropped from a comparison.
* Report each repeat and each source, then paired-repeat medians and ranges.
  Never divide two separately reported medians and call that a paired effect.
* Bootstrap 10,000 times with seed 20261022. Sample the three paired repeat
  indices and the sixteen source indices with replacement. A source draw is
  shared across both arms and all selected repeats because these are the same
  audio sources, not newly independent windows. Source-resampled Goodput and
  error ratios are conditional on the observed schedule; they do not simulate
  a new arrival stream. Energy is paired-repeat-only, not source-resampled.
* Goodput counts audio-duration weights on common 2-second plus exact final
  frontiers, divided by arrival-and-drain serving wall. Display is actual
  consumer application; Commit is durable owner installation. Also report
  first certified consumption separately; it must not replace Commit silently.
* Report all three predeclared claim types separately: primary Goodput;
  strict raw-latency/energy Pareto; shared-service-contract-qualified cost.
  A failed test stays failed when another claim type passes.
* Literal no-quality-loss point and confidence tests are separate from the
  +0.5 percentage-point noninferiority tolerance. A tolerance pass with higher
  WER/CER cannot be called quality-preserving without that qualification.
* Compare DGFT with Fine independent Authority, Score+Fallback and
  Strict+Fallback individually. A superiority statement over the best legal
  alternative requires all relevant comparisons, not just the weakest one.
  Standard Safe Async remains a complete positive control, even if equivalent
  to or better than DGFT.
* Deduplicate model work by actual physical worker batch/phase, retaining
  discarded, obsolete, padding and fallback work. Candidate GPU completion,
  owner receipt, eligibility/enqueue and consumer application are distinct
  clocks; audio-ready to enqueue is not named pure candidate wait.
* Operator/oracle/CPU replay calls are a separately costed diagnostic campaign,
  never online performance observations or free operations in a serving arm.

No original paper, old measurements, running source or frozen cell is changed.

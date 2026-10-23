# CPU-only scope update

On 2026-10-23 the user confirmed that the server network is unavailable and
explicitly requested CPU audit and further algorithm research. All subsequent
work in this stage is local CPU work. No further SSH checks or GPU launch are
performed. The earlier 48-serving-cell + 2-oracle-cell discussion remains an
unexecuted proposal, not an active or completed experiment plan.

Deliverables now include a working V5 CPU implementation, cost calibration and
its limitations, mathematical counterexamples and a bounded exhaustive model
oracle, model-mechanism analysis, independent safety/accounting review, source
hashes and the next GPU hypothesis. The model oracle certifies only the tested
finite scheduling model; it does not produce real GPU outputs or serving gains.

The initial CPU implementation is retained in source history before audit fixes.
The audit found that Commit-first lexicographic priorities can lose joint
Display/Commit credit, mean row time does not preserve deadline probabilities,
and simple GPU0 reordering often cannot change the dispatch set at c16/batch16.
These are addressed or explicitly isolated before declaring the CPU stage ready.

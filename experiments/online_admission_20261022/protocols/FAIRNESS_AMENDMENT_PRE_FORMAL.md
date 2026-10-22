# Strong-fallback review before any formal results

The initial pilot conservatively regenerates the whole submitted FP32 batch
when a candidate fails. That preserves the operator used by the independent
Oracle, but it is not automatically the cheapest *legal* fallback. Requiring
all successful rows to be recomputed could unfairly handicap verification.

Before freezing the formal source, test a selective fresh-generation fallback:
select failed rows from the **already correct processed input tensors**, preserve
their row bytes/padding/masks/features and frozen parent/audio, and execute new
FP32 generation. No KV reuse, hidden-state transfer, partial speculative decoding,
online availability selector or new model algorithm. If the actual tensor layout
is not demonstrably row-separable, retain paid whole-layout fallback.

The physical batch row count can change. Do not assume bitwise equivalence to
the old full-batch FP32 execution: it is a separately declared valid fallback
operation, with actual per-row inputs and numerical repeat/Oracle controls. All
accepted candidates still require complete checks at their original target
operation; no candidate is accepted because a different fallback layout is faster.

Run a bounded extra pilot for Score/Strict × clean/F2, before formal launch. Only
if selected-row provenance, stop/projection, repeat and source checks pass may
the stronger variant replace the full-layout version in the six-policy formal
comparison. Retain the original full-layout pilot and all failures; do not use
diagnostic pilot times as a formal speedup. No SLO/quality/statistical threshold,
source/fault/workload choice changes. This amendment is motivated by baseline
validity, not by inspection of formal or pilot performance/quality tables.

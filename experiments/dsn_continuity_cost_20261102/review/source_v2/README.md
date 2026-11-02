# Independent gap recount — preparation only

No script in this directory has been executed by its author. Root must freeze
the complete source, run controls, and register config/environment/raw/summary/
gate before execution. It imports only byte-pinned original reference_view and
reference_kernel, never history_analysis or its selector/merger/area helpers.
This V2 directory adds fallback/upgrade scope accounting and one new control
to the ten controls frozen with V1. All eleven still require a new formal run.

The recount reloads raw bytes from the frozen BANK_MANIFEST, reconstructs the
original FIFO baseline including metadata, and creates a separate query state.
Candidate tips must already be Consumer-registered. Their full immutable job,
input/result projection, complete Z, text, epoch, revision/generation, mode and
individual revocation are checked; host-only results supply proof nodes only.
Every candidate is tested with the original native compatibility relation and
original core apply-request/view-applied. This is a restricted per-cut predicate
check, not a reexecution of the Owner, model, physical lifecycle or all original
publication receipt ownership.

Independent sorted endpoint sweeps include original actual apply, next same-
source apply, actual host complete arrivals and explicit generation retirement.
The positive interval set is compared to reported GAPS by a second partition
sweep; equal totals alone cannot pass. It recomputes audio unions, categories,
right-censoring scope and first D2/C8 accounting including partial EOS.

The output separates recovery from a certified-only actual view from upgrading
an already legal ahead view. Unconditional max-frontier choice need not keep
the current whole text unchanged. A current-view-preserving fallback can keep
a legal current view and query historical results only when it is absent or
invalid. This audit reports the fixed-history maximum opportunity; it does not
silently implement that different online policy.

Expected root invocation after freeze (all destinations must be fresh):

```
python -B recount_gaps.py --h-output <H-positive3-or-all-output> \
  --bank-manifest <frozen-BANK_MANIFEST.json> \
  --reference-source <clean-H2-source> --reference-manifest <H2-SOURCE.json> \
  --reference-commit aa1965c650f42eee00c6015297f1d706e6dcec23 \
  --source-commit <new-independent-commit> --source-manifest <new-SOURCE.json> \
  --selection positive3 --out <8TB-new-independent-output>
```

Only positive3 or already reported positive attempts are fully recounted here;
the primary all287 run retains the zero/censored/failure denominator. A positive
subset audit does not independently re-prove that every other attempt is zero.
No measured online gain, incidence estimate, new neural work, or token-to-text
render equivalence follows from this audit.

# Related-work verification and claim positioning (2026-10-28)

Workflow: citation verification using official publication metadata and primary
pages. Academic-search MCP is unavailable; public Crossref DOI lookups were used
instead. Four raw DOI responses and their hashes are in `related_metadata_v1/`.
The public OpenReview API returned403 and its website requested verification;
both failures are retained and no challenge was bypassed. Publication status
below uses independently accessible primary sources where available. A failure
to find a venue is not proof that no publication exists.

## Published work that must be credited

|Reference / primary source|Verified status|Relevant content / limit on our claim|
|---|---|---|
|[Dynamic Speculative Agent Planning](https://openreview.net/pdf/0b98c9fcf66a2a3ac799c3c6824030256c2f7ce3.pdf), Guan et al.; [author organization ICLR2026 list](https://research.google/conferences-and-events/google-at-iclr-2026/)|ICLR2026; indexed official PDF says published as conference paper; Google author list confirms title/authors|Online prediction of speculative depth with target verification and latency/cost control. Therefore adaptive speculation or a tunable cost/latency dial alone is not our new contribution. We did not reproduce its agent benchmarks.|
|[RAGCache](https://doi.org/10.1145/3768628), Jin et al.; [author's published copy](https://chaojin0310.github.io/files/papers/TOCS25-RAGCache.pdf)|Crossref verified journal article, ACM TOCS; online2025-11-07, print2026-02-28,44(1)|Dynamic speculative pipelining overlaps retrieval/generation and avoids redundant work. Do not confuse its acronym DSP with Dynamic Speculative Agent Planning. Neither paper licenses a claim that delaying or restarting inference is itself new.|
|[Orca](https://www.usenix.org/conference/osdi22/presentation/yu), Yu et al.|Official OSDI2022 proceedings|Iteration-level scheduling and selective batching address requests trapped behind a batch. Shared row-complete execution here is not an exclusive RevTrace scheduling novelty; a row return still does not free an undrained physical Worker lease.|
|[Serving DNNs like Clockwork](https://www.usenix.org/conference/osdi20/presentation/gujarati), Gujarati et al.|Official OSDI2020 proceedings|Predictable model execution and explicit resource scheduling are strong prior concepts. Ordinary ETA/deadline/backpressure controls must remain baselines, not be renamed causal innovation.|
|[Turning Whisper into Real-Time Transcription System](https://aclanthology.org/2023.ijcnlp-demo.3/), Macháček et al.|ACL Anthology and Crossref DOI10.18653/v1/2023.ijcnlp-demo.3, system demonstrations2023|Local agreement and adaptive latency already stabilize streaming text. Stable display and feedback write eligibility remain distinct questions; do not pretend display prefix confirmation is absent from prior systems.|
|[State Management in Apache Flink](https://www.vldb.org/pvldb/vol10/p1718-carbone.pdf), Carbone et al.|Crossref verified PVLDB10(12),2017, DOI10.14778/3137765.3137777|Consistent operator/input-progress snapshots and recovery are established. Conventional composition can encode our application predicates: the successful full Standard control must remain visible. Do not assert Flink only protects a sink or requires all neural operators to be deterministic.|
|[ARIES](https://doi.org/10.1145/128765.128770), Mohan et al.|Crossref verified ACM TODS17(1),1992|Durable logs and restart recovery are established. RevTrace must specify what selected output/input/debt/renderer identity is logged; mere use of WAL, retry IDs or grouping is not by itself new.|

## Background only — no formal venue independently confirmed in this check

- [Heartbeat Thinking](https://arxiv.org/abs/2610.26233), submitted2026-10-19:
  continued invocations during speech updates and reusable tool preparation.
  The arXiv record is verified; it is kept as background, not promoted to a
  formally published principal competitor or a reason to reopen experiments.
- [AOSpec](https://arxiv.org/abs/2608.00881), submitted2026-08-01:
  agent action/observation speculation with origin-state verification. The
  arXiv record is verified; no formal venue was confirmed in this bounded
  check. State-bound speculation must still be accurately acknowledged, not
  dismissed as if prepublication means the idea cannot exist.

## Position supported by our own measurements

This study's input-freeze cost evidence is narrowly about actual future neural
inputs and paid complete batch cost; it is not a new generic speculation depth
algorithm. Its six-policy repaired comparison fails to show a new superior
controller. The trusted-render extraction is a concrete, exact-contract
recovery dependency optimization shared with Standard. Ordinary dependency
separation is not claimed unprecedented; its verified token/Stop/P/text binding
and separate old/new/debt recovery clocks are the measured engineering result.

The defensible paper center remains application-defined certified admission,
legal two-timeline private consumption, and durable selected history/input
obligations. Full conventional implementations can reproduce those semantics.
Novelty must be argued from the specified boundary and measured tradeoff, not
from an alleged impossibility of composition or from scheduler names. These
checks do not prove no other related work exists and do not constitute a new
end-to-end performance comparison against any published system.

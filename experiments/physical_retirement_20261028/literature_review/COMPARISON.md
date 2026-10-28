# Source-linked mechanism comparison

Verified 2026-10-28. The last column is our interpretation and a proposed experimental obligation, not a claim made by the cited paper. “Outside the reviewed scope” is not an impossibility claim.

| Work | Trigger / unit of decision | What the mechanism establishes | Reviewed workload / boundary | RevTrace comparison obligation |
|---|---|---|---|---|
| [Retire, 2026 preprint](https://arxiv.org/html/2610.01160v1) | Runtime-selected `SUPERSEDE(scope, epoch, successor)` | Version authority, bounded old execution, closed-writer prefix inheritance, isolated reclamation | Revising LLM agents; vLLM; H100/GB200 and distributed/co-tenant tests | Closest neighbor. Compare feedback-derived usefulness and compatible-progress retention. Parent-version cancellation alone is an adaptation, not the whole system. |
| [Orca, OSDI 2022](https://www.usenix.org/system/files/osdi22-yu.pdf) | Scheduler selects active requests every model iteration; completion includes EOS | Iteration scheduling and selective batching admit new requests and remove finished work without waiting for an entire fixed batch | Autoregressive Transformer serving; GPT-3-family evaluation | Credit the execution granularity. Supply all policies the same safe-point capability. Our batch-drain optimization does not constitute a new continuous-batching algorithm. The reviewed paper does not define our Canonical/Private compatibility predicate. |
| [InferCept, ICML 2024](https://arxiv.org/html/2402.01869v2), [author code](https://github.com/WukLab/InferCept) | Augmentation stop / external interaction pauses decoding; later resumption | Chooses preserve/discard/swap using resource-waste estimates; chunks recomputation and pipelines swapping; resumed requests retain original arrival priority | Tool, environment, chat, image, and speech augmentations | Pausing reusable context differs from proving a private row permanently useless. Compare shared resources and retained progress fairly. This is not evidence that interception itself is new. Do not label a timeout-only policy InferCept. |
| [Borealis, CIDR 2005](https://www.cs.umd.edu/~abadi/papers/cidr05.pdf) | Input insertion/deletion/replacement revision records; downstream correction | Retained history supports replay and output deltas; tentative results can be reconciled after missing inputs return | Distributed stream-query operators; bounded history and consistency/availability choices | Revision-aware state and tentative/stable output are prior ideas. Our opportunity concerns actual model feedback, branch compatibility, and GPU resource effects under a fixed trusted contract. Preserve accepted audio rather than copying history-expiration/load-shedding semantics. |
| [Naiad, SOSP 2013](https://www.microsoft.com/en-us/research/wp-content/uploads/2013/11/naiad_sosp2013.pdf) | Logical timestamps, outstanding events, dataflow reachability, progress frontiers | Coordinates consistent notifications when earlier relevant events can no longer arrive; supports cyclic and incremental computation | Distributed timely dataflow and iterative/streaming workloads | A completion/progress frontier is related machinery. It does not itself certify a neural feedback-state transition. Explain the added model-state and Consumer conditions, rather than claiming frontiers or independent progress are new. |
| [Time Warp / Virtual Time, 1985](https://gdo-pdes-course-2014.llnl.gov/attachments/20776356/20907222.pdf) | A causally earlier event invalidates optimistic execution | Rollback and antimessages undo dependent effects; virtual-time commitment supports safe reclamation | Optimistic distributed discrete-event simulation | Optimistic branches, causal invalidation, and delayed commitment have longstanding foundations. Our evidence must establish the chosen feedback-stream realization and service value. Physical decode retirement is an execution integration, not invention of causal rollback. |
| [Speculative decoding, ICML 2023](https://proceedings.mlr.press/v202/leviathan23a.html) | Approximation model drafts; target-model verification accepts/corrects tokens | Speculative sampling preserves the target distribution under the algorithm's assumptions | Autoregressive model decoding | A candidate-verification relationship is prior art. Distributional correctness does not automatically prove identical deployed floating-point states or legal streaming feedback. State the actual RevTrace equivalence/admission contract. |

## What can reasonably be claimed if the experiment succeeds

“We combine trusted feedback-state progress, selective preservation of compatible speculation, and decode-safe termination of provably obsolete work. On the evaluated streaming workload, this preserves the original trusted contract while reducing interference experienced by other legal sessions.”

This is a candidate contribution sentence. Replace it with the actual measured outcome and supported workload boundaries after live validation. The full combination can be meaningful even when its ingredients are established techniques. Its value depends on the coordination difficulty, newly supported service behavior, and strong shared-capability controls.

## Claims the evidence must not imply

- First physical LLM cancellation, first version authority, first safe-point execution, first causal rollback, or first tentative/stable streaming output.
- A `parent_cancel` loss is a full Retire defeat. Scope selection is a material part of an adaptation.
- A successful combined Standard is external prior art or a reason to erase the author's original combination.
- Offline tail bounds, fewer result rows, or cancel-request counts are realized resource savings.
- Trusted coverage cancellation alone demonstrates every possible incompatible-branch revocation.

## Expected decisive plots / tables

These are proposed displays; no new measurements are asserted here.

1. **Lifecycle timeline:** actual Canonical install → cancel request → worker safe-point acknowledgment → canceled-row terminal → synchronized batch drain → next legal job starts. Overlay the row-complete arm with the same input and layout.
2. **Policy comparison:** original row-complete, watchdog, parent cancellation, trusted coverage, causal retirement; show protected Canonical outcomes, accepted-input accounting, actual legal-session stalls/progress, and retained useful completions together.
3. **Cost and boundary:** no-cancel overhead, cancel latency, GPU/lease occupancy, and recomputation. Show the abnormal-tail source separately from normal and independent sources.
4. **Combination confirmation:** branch retention × Consumer policy on the unified final implementation, including a full-Standard positive control. Separate compatible preservation from required incompatible withdrawal; no arbitrary zero-rollback guarantee.

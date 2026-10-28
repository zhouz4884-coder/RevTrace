# Baseline identities for RevTrace physical retirement

Verified: 2026-10-28. Scope: primary-source literature and the current local source; no new GPU experiment. This document defines identities, not reproduction or performance claims. The academic-search MCP catalog was not present; publisher, author, laboratory, and arXiv primary sources were read through web search instead.

## The closest external work: Retire

**Retire** is the system in **Yanxin Zhang, Rahul Sharma, Nitin Vegesna, Zheyu Fu, Chang Liu, and Trivikram Krishnamurthy, _Serving a Revisable World: Versioned Execution for Interruptible Agents_, arXiv:2610.01160v1, submitted 2026-10-01**. The authors are affiliated with NVIDIA. A peer-reviewed venue and author code repository were not verified in the reviewed primary sources. Cite the dated preprint, not an invented conference. [Identity](https://arxiv.org/abs/2610.01160), [full text](https://arxiv.org/html/2610.01160v1).

Its runtime selects a scope and explicitly supplies `SUPERSEDE(scope, old_epoch, new_epoch, revised_context, contract)`. Its vLLM control plane coordinates revocation, bounded execution, certified completed-prefix inheritance, and asynchronous reclamation. Short decode uses model-step boundaries; long work adds bounded checks. It covers publication, KV ownership, distributed participants, and tenants. The recorded-agent replay preserves interruption timing but uses controlled 8192-token, zero-overlap state (§§3, 5–7; Appendix A.2.1). [Mechanism and evaluation](https://arxiv.org/html/2610.01160v1).

**Interpretation for this project:** a policy that cancels every old parent is not a faithful implementation of all Retire behavior. The experiment must not infer a full-system Retire victory or defeat from that policy. Retire can, in principle, receive a feedback-derived supersession decision from a client; our integration must earn its value in that concrete workload.

## Other verified identities

| Work | Verified publication / source identity | Primary sources and what was checked |
|---|---|---|
| **Orca** | Gyeong-In Yu, Joo Seong Jeong, Geon-Woo Kim, Soojeong Kim, Byung-Gon Chun. _Orca: A Distributed Serving System for Transformer-Based Generative Models_. OSDI 2022, pp. 521–538. | [USENIX record](https://www.usenix.org/conference/osdi22/presentation/yu), [paper](https://www.usenix.org/system/files/osdi22-yu.pdf), especially §3 and Fig. 4. |
| **InferCept** | Reyna Abhyankar, Zijian He, Vikranth Srivatsa, Hao Zhang, Yiying Zhang. _InferCept: Efficient Intercept Support for Augmented Large Language Model Inference_. ICML 2024, PMLR 235:81–95. | [Publisher record](https://proceedings.mlr.press/v235/abhyankar24a.html), [author manuscript](https://arxiv.org/html/2402.01869v2), §§2–5; [author repository](https://github.com/WukLab/InferCept), including the augmentation-stop registration interface. |
| **Borealis** | Daniel J. Abadi et al. _The Design of the Borealis Stream Processing Engine_. CIDR 2005. | [Author-hosted paper](https://www.cs.umd.edu/~abadi/papers/cidr05.pdf), §§3 and 6. Do not conflate its author list/year with the earlier 2004 Brown technical report. |
| **Naiad** | Derek G. Murray, Frank McSherry, Rebecca Isaacs, Michael Isard, Paul Barham, Martín Abadi. _Naiad: A Timely Dataflow System_. SOSP 2013. DOI: 10.1145/2517349.2522738. | [Author laboratory record](https://www.microsoft.com/en-us/research/publication/naiad-a-timely-dataflow-system-2/), [paper](https://www.microsoft.com/en-us/research/wp-content/uploads/2013/11/naiad_sosp2013.pdf), §§2–3. |
| **Time Warp** | David R. Jefferson. _Virtual Time_. ACM TOPLAS 7(3):404–425, July 1985. DOI: 10.1145/3916.3988. | [Publisher DOI](https://doi.org/10.1145/3916.3988); publisher text returned HTTP 403. The paper itself was read from [Jefferson's LLNL course copy](https://gdo-pdes-course-2014.llnl.gov/attachments/20776356/20907222.pdf), linked by the [LLNL course page](https://computing.llnl.gov/projects/pdes-modeling-complex-asynchronous-systems/2014-course). |
| **Speculative decoding** | Yaniv Leviathan, Matan Kalman, Yossi Matias. _Fast Inference from Transformers via Speculative Decoding_. ICML 2023, PMLR 202:19274–19286. | [Publisher record](https://proceedings.mlr.press/v202/leviathan23a.html), [paper](https://proceedings.mlr.press/v202/leviathan23a/leviathan23a.pdf). |

## Local Standard identity is different from external prior art

The frozen source checkout is `.execution/lp1_runtime`, actual source commit `040fcc95f4cd3bbc4d918bc1dd4502b0b768990c`; runtime code is below its `runtime/` directory. This identity was read from the current local pointer and source, not from the dirty root HEAD.

`runtime/src/revtrace/standard_safe_async.py` explicitly describes an independently written conventional policy adapter that shares the executor and commit core. It explicitly disclaims being a native external serving system or independent neural implementation. Its current cancellation is logical.

`runtime/scripts/continuity_controller.py` gives the full Standard the same private-prefix retention and Consumer rules. Thus **Standard + the complete composition is an author-built alternative implementation / positive control**. Equal protected behavior supports implementation independence and composability. It does not establish that an external published system already provided the complete RevTrace combination, and it is not evidence of comparative speedup between distinct algorithms.

## Labeling rules for the next experiment

1. `row_complete`: the original shared executor; completed rows can return early, but the physical worker remains occupied until `BatchDrained`.
2. `watchdog`: the same new executor with a frozen timeout/token policy. A canceled useful row remains an unfulfilled service obligation unless later satisfied; its cancellation is not an admission failure.
3. `parent_cancel`: the same executor, canceling on any parent-version change. Label it a conservative parent-version policy. It is **not** an original Retire reproduction.
4. `trusted_cover`: the same executor, canceling only when actual installed Canonical coverage reaches the row target. This simple policy must be included independently of any more elaborate causal policy.
5. `causal_retire`: the same executor and guards, using the implemented feedback-derived proof of uselessness; preserve compatible branches. Credit only the predicates actually exercised by live runs.
6. `standard_full`: if enabled, the full author-built alternative receives the same retention, Consumer, trust, recovery, and retirement capabilities. Treat it as a positive control.

No arm inherits a paper's measured result merely by adopting its name or one idea. Native external reproduction would require the identified author source and its actual mechanisms; a controlled adaptation must name the changed workload and shared executor.

## Evidence required to make the comparison useful

The executor is a common actuator. Report a cancellation request separately from a worker-confirmed canceled row, a fully completed row, and synchronized `BatchDrained`. A token/EOS mask or suppressed output alone does not prove that GPU work or a physical lease was released. With a static batch and no compaction/refill, cancellation can shorten the batch only after all remaining useful rows terminate; do not claim immediate per-row capacity recovery.

All arms retain identical trusted selections, actual Consumer processing, original deadlines, offered-input denominators, and accepted-input obligations. Show other legal sessions' actual stall, progress, deadline results, worker reuse, and resource occupancy. Record lost useful work and required recomputation as well as saved obsolete work.

The scientific opportunity is a concrete feedback-stream composition: derive when in-flight speculation has become useless while preserving still-compatible progress, and show that this decision improves service under the unchanged correctness contract. Existing mechanisms are valid building blocks. If simple trusted coverage already captures the measured benefit, keep that result and avoid attributing benefit to unexercised causal machinery.

# Phase 7 related-work collision matrix

Frozen before Phase 7 comparison runs. “Direct” means source was executed on
the same RTX 3090 server; “adaptation” means the published mechanism does not
natively target Qwen3-ASR revision feedback and is reproduced under the
explicitly named adaptation.

| Work | Original object | Guarantee | Phase 7 treatment | Boundary |
|---|---|---|---|---|
| LLM-42 | nondeterministic text-LLM dynamic batching | fixed-path verify and rollback | original source import/server attempt plus `LLM-42-style revision baseline` | source custom kernel could not build without `nvcc`; adaptation verifies every feedback revision |
| Thinking Machines `batch_invariant_ops` | batch-invariant primitive operators | bitwise operator equality | source operator and Qwen3-ASR subgraph run | not a feedback-state transaction system |
| LayerCast / TBIK | deterministic arithmetic, mainly TP invariance | fixed reduction topology | public TBIK source operator run | RTX 3090 used documented Triton fallback; not end-to-end ASR |
| vLLM Batch Invariance | deterministic vLLM serving | batch-invariant kernels | actual Qwen3-ASR decode attempt | failed at unsupported `_half_to_float` log-softmax path |
| SGLang deterministic inference | deterministic SGLang serving | deterministic engine mode | source Qwen3-ASR import attempt | current stack requires Torch 2.11/CUDA 13-era dependencies absent from frozen server |
| MarginGate | text-LLM token verification | low-margin selective canonical check | `MarginGate-inspired revision baseline` | no state transaction, asymmetric evidence, or joint SLO admission |
| RW-TTT | request-owned test-time-training state | owner/version READ/WRITE commit | `owner/version-only state baseline` | versioning cannot detect a legal batch numerical flip |

## Frozen novelty boundary

RevTrace does **not** claim the first observation of inference nondeterminism,
margin-triggered verification, versioned mutable state, or deterministic
kernels. The claimed object is the feedback edge by which a generated ASR
revision becomes future model state. RevTrace combines contract-scoped
statistical evidence, state-entry transaction fencing, asymmetric failure
memory, and joint risk/SLO admission so an uncertified transition cannot
silently contaminate later revisions.

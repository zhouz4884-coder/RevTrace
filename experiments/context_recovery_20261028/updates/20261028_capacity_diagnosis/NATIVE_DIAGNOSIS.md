# Native numerical and task-quality diagnosis

The ten original Qwen2.5-1.5B smoke cells remain frozen. Eight protected
cells completed actual three-write LangGraph/checkpoint/store/Consumer
lifecycles but none of their offered planning steps met the objective task
criteria. The two FP16 candidate-only cells produced budget-exhausted token0
sequences and no accepted application writes. These are not successful task
protection observations.

The paid same-input diagnostic used two original actual requests, two repeats,
and FP32/BF16/FP16 on the same physical GPU0. Each request had151,936 last-step
logits. All four FP16 forwards had151,936NaNs and emitted token0 prefixes;
all eight FP32/BF16 forwards were finite and repeated the original FP32
three-token prefix. The original weight blob matched its official content hash.
This localizes the FP16 pathology to this precision/execution realization,
not corrupt weights. It does not prove the internal first nonfinite layer,
full-answer BF16 quality, general numerical equivalence, or any serving benefit.

Two separate actions follow. Accounting now excludes CPU structural verification
rejections from GPU-call counts and requires EOS for a complete candidate.
The original raw records are not rewritten. For an informative application
control, all arms may use an explicitly different existing Qwen3-4B checkpoint,
BF16 draft, FP32 authority, thinking disabled and the unchanged frozen task
instructions/scorer. This is a stronger-model control, not a state-admission
innovation or a removal of the failed1.5B evidence. Model assets, actual inputs,
full output/Stop, processor and objective outcomes remain separately audited.

First execute only the ten clean smoke cells and actual same-input selection
self-checks. Expand controlled-fault/restart or validation only if this control
has useful task-quality headroom; protocol success alone is not that gate.
No task oracle is a generation input. The four structurally fixed native
validation tasks and the48audio sessions are not used to tune the model or
repair rules. Standard receives all identical implementation capabilities.

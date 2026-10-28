# v9 diagnostic/accounting repair, before new GPU execution

The v8 native smoke is retained exactly. Its FP16 candidate returned repeated
token0 to budget; its FP32 selected plans were schema-valid but task-incorrect.
This is not yet attributed to numerical overflow, model capability or a code
defect. The next same-input FP32/BF16/FP16 operator records actual logits and
short generated prefixes before a repair or larger native comparison is chosen.
Three-token prefixes are not complete selected answers or application writes.

Two accounting defects were identified in v8: `actual_gpu_call_count` counted
CPU structural rejection entries, and `verification_rejections` omitted them.
v9 separates actual generate/verify model invocations from structural CPU work,
counts both content and structural rejections explicitly, and makes the native
candidate `complete` flag require the existing EOS condition. Admission had
already required EOS separately; no rejected/capped answer is newly admitted.

The first paid dispatch-input operator failed before loading a model because
its archived runtime stores a model basename while the live runner resolves
the model path at process creation. v9 uses the identical declared model store,
rejects path escapes, and retains the original failed attempt with zero GPU
model calls. It changes no model arithmetic or safety predicate.

The existing native lifecycle gate alone is not a task-quality or harm gate.
Do not expand the native comparison solely because protected histories completed
three writes when the clean model succeeds on zero planning steps. Diagnose
the actual failure and use equally capable, fairly configured strong controls;
keep all base-model errors. No model/task improvement is claimed by this source.

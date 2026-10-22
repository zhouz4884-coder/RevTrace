# P1 independent-audit coverage repair, before supplemental GPU results

The original96 diagnostic invocations remain immutable. Their output and original
processor-input controls passed. Independent audit correctly rejected its own
additional nonempty actual-GPU-input requirement on all-pass verification batches:
GenerationMixin is never called there. Mixed batches captured fallback inputs but
not the verification forward's augmented input. This is an observer/audit coverage
defect, not a demonstrated model mismatch or correctness defect.

Freeze a supplemental12-invocation identity-only comparison: the same six already
selected Strict/Score physical operations, reference then observer, no new audio
selection and no timing/performance claim from these hashing calls. Add a read-only
forward-pre-hook on the actual correct-context verification call, preserving all
kwargs and recording post-cast tensor bytes. Retain existing fallback input capture.
Complete Z/P/text/stop, decisions, original processor tensors and original physical
peer order must still match the old actual operations; reference/observer actual
verification and fallback tensors must match. Do not rerun the96 measured ABA
invocations or promote this extension to a serving result. A disagreement stops
the interface gate pending same-input/legal-operator diagnosis.

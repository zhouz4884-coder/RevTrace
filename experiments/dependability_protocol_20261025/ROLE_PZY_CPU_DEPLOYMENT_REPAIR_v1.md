# Recorded-ID decoder registration repair, zero new neural calls

The optional CPU-only P/Z/Y decoder v1 imported generic AutoProcessor without
qwen_asr registration. It returned Qwen2TokenizerFast rather than the measured
ASR processor and failed with AttributeError before writing output. Remote
operation log/oldscript retained; all64GPUmeasurements and original full CPU
asset gate remain unchanged. v2 imports the sameqwen_asr registration used by
the already successful actual-input auditor, explicitly disables CUDA and uses
the measured decode flags. No fix_mistral_regex flag, tokenizer asset, model,
output or execution contract is changed. Result is only decoded recorded IDs,
not a new-parent generation or a repeat GPU experiment.

v2then found a real schema mismatch:repeat lives in the formal FREEZE/owner
launch, not CASE_PLAN. It failed before writing output. v3takesrepeat from the
frozen64plan and asserts exactcase-name alignment. Both failed logs/oldscripts
remain. The pinnedtransformers tokenizerwarning is retained; no regex/assets
changed. The successful base-input audit already reproduces actual IDs under
that pinned implementation, so this is not grounds to silently change it.

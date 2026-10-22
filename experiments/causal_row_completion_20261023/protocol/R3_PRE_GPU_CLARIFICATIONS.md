# R3 clarification before trajectories or outcomes

Use the frozen8 independent native30.13–33.21s full utterances; this is not an
hour-scale service soak or8 new subjects per adapter. Same8 across adapters is
one shared audio pool. All comparisons are controlled neural trajectories, not
natural incidence or deployed serving capacity.

Native singleton physical layouts are shared by clean/fault arms, avoiding a
new peer-dependent batch perturbation in propagation comparisons. Two complete
same-input repeats, fixed future waveform and native declared adapter inputs.
Qwen FP32 cumulative rollback5/fine2s/budget256; Whisper small.en FP32 explicit
get_prompt_ids(cumulative history), contiguous10s windows/budget128. The audio
checkpoint before the injected operation is10s in both, but target spans/window
counts differ. Report elapsed audio as well as K; no family-only causal inference.

The one wrong-context neural operation is real. Its field normalization under
the declared pre-fault history is explicitly the existing F2 adaptation, not a
claim that wrong-context Z was generated under that declared parent. Later steps
actually consume the resulting P and generate fresh Z; no old-Z reparenting.

First check that native Qwen full-prefix processing still supplies the30s+ audio
to actual tensors. Processor config chunk_length30 alone proves neither support
nor truncation. Compare actual frame coverage and a tail-only input contrast.
If unsupported, retain this NO-GO/boundary and do not claim full-source future
coverage from a truncated input. Distinguish source-ending right censoring from
input-limit,token-budget,process or protocol censoring.

No word/audio alignment timestamps have been established for these references.
Never manufacture per-window reference text by proportional word counts. Final
full-source WER/CER is valid; intermediate errors against the fixed full-source
reference must be labelled partial-hypothesis/full-reference diagnostics, not
aligned-prefix recognition accuracy. Report P,new Z,complete visible Y and any
adapter-specific incremental text separately, with first equality,redivergence
and all missing/capped outcomes retained.

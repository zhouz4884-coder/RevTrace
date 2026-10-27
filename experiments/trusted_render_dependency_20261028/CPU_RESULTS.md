# CPU result, not deployed recovery RTO

Actual component source973d4c66e2f4d8227ec5546f86da310e38151846,
orchestration source965cd9db556445aa37c0000c1b40a3b2d8d4887a.
The first orchestration version72e7e55failed before recording environment or
invoking any component due to an importlib local-binding error. Its original
source, terminal log and externally identified failure are retained. It is not
a semantic NO-GO or GPU experiment.

| Check | Observed result |
|---|---|
|Same-job actual GPU row re-render|184/184exactP/text |
|Durable selected-text bindings|56/56exactP/text |
|Paid old/new-input rows, each under its own actual input|28/28exactP/text |
|Complete actual vocabulary|151,705IDs, both skip-special modes; matching block/global digests |
|Fixed-seed random token/Unicode/rollback controls|4,096matching signatures |
|Parser language/tag/repetition controls|Matching digest |
|Valid256token budget termination|Matching digest; not falsely rejected for lack of EOS |
|Invalid/short/internal-EOS/overbudget controls|All4rejected |
|Altered descriptor/program/helper/version/loader/assets/special mode|All7fail closed before replay |
|Light process imports|No torch, transformers, qwen_asr or librosa before/after |
|Fresh component load including renderer class|Native13.0859s; light1.8337s |
|Replay all268observations|Native0.1675s; light0.1582s |
|Weights loaded / neural inference|0 /0 |

The backend program is an export of the actual native tokenizer, not a text
cache or a hand-rebuilt vocabulary. Serialized normalized backend structure,
Rust engine/version/critical files, fixed native encode_batch/decode defaults,
all model assets, package source inventory and exact parser dependency AST are
bound. Source inspection checked the real fast-tokenizer wrappers before porting;
single-string encode uses the native single-row encode_batch entry point.

Gate: GO_CPU_COMPONENT_CONFORMANCE_NOT_SERVING_RTO. This supplies a concrete
dependency/critical-path opportunity. It does not prove wall-clock service RTO,
whole-Python/Rust refinement, semantic recognition quality, host attestation or
arbitrary tokenizer API equivalence. A separate new-contract serving comparison
must preserve all token/text/P/source/epoch/debt checks and offer the same change
to full Standard. Old v7WAL cannot silently acquire this new allowed interpreter.

## Tokenizer warning is not a repair instruction

The native preparation printed a fix_mistral_regex warning. Inspection of the
installed Transformers4.57.6source showed its local-model branch can issue the
warning for a large vocabulary and config transformers_version4.57.6, without
comparing this model's actual regex against a reference. This model is qwen3_asr,
not a Mistral-family model. The warning alone establishes neither a tokenizer
fault nor a permitted flag change. No regex was changed. The exported backend
preserves the exact observed native default, including its flag settings.

This work continues original goal5. Context/dispatch algorithm NO-GO decisions,
untouched holdout nonuse and all prior negative/model-quality results remain.

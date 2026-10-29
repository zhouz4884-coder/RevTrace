# Frozen native path compatibility repair (v6)

This amendment precedes all native neural calls. The two witness runs and twelve formal cells, fixed four metadata-selected utterances, strong two-Authority sequential baseline, original selection logic, all-offered denominators, D2/C8 targets, and primary interpolated quantile rule remain as frozen in protocol v2.

## Observed defect and sufficient repair

Actual CPU preflight of v5 under the existing remote Transformers 4.57.6 failed: `AutoConfig.from_pretrained(..., text_model_id=local_path)` applies overrides only after the custom Ultravox config constructor has already attempted its nested original Meta model lookup. Offline loading therefore fails before model construction. This is an implementation path-resolution defect, with zero model calls; it is not a semantic-hypothesis failure or application result. The original v5 diagnostic is retained.

The v6 wrapper loads the unchanged published dynamic config class, changes only the original `text_model_id` path in the input dictionary before construction, and constructs the original processor class with its original tokenizer and feature extractor. The original processor explicitly requests `openai/whisper-large-v3-turbo`, whose 128-bin extractor differs from the 80-bin metadata bundled in the Ultravox directory. Thus v6 acquires the exact original official extractor metadata at revision `41f01f3fe87f28c78e2fbf8b568835947dd65ed9` (340 bytes, SHA256 `7ccc62c6f2765af1f3b46c00c9b5894426835a05021c8b9c01eecb6dfb542711`), rather than substituting the bundled 80-bin file. Original left padding, EOS padding, processor constructor, and stack factor are retained.

The actual repaired CPU path loaded the original configuration and processor and produced a synthetic CPU feature tensor with shape `[1,128,100]`; CUDA remained uninitialized and no model was constructed. This validates the loader/interface only. No application quality or performance is inferred.

## New source identity

The complete v6 execution source is `a720d02a8cb81db6545d7d9ec6bdc31419dd091d`, with fourteen byte-identified files. Local CPU contract tests pass 24/24. The source bundle, manifest, plain snapshot, local explicit provenance gate, and preserved v5 diagnostic are in this family. The global machine-local current pointer remains on the f0 source until the preceding f0 GPU campaign is complete; v6 will be selected and checked before its own GPU launch.

The original author candidate decoding, learned corrector prompt/generation/selection, selected-text feedback update, and native alignment logic are unchanged. The fixed 500ms/no-VAD serving front end remains a controlled adaptation. No claim of reproducing the published native benchmark is added.

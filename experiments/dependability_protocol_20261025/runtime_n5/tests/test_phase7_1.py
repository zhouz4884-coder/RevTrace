from revtrace.phase7_1 import (
    CanonicalRuntimeProvenance,
    classify_postrun_disagreements,
    guarded_capacity,
)


def provenance(dtype: str) -> CanonicalRuntimeProvenance:
    return CanonicalRuntimeProvenance(
        model="Qwen3-ASR-0.6B",
        configured_weight_dtype=dtype,
        accumulation_dtype="kernel-defined-unrecorded",
        sampling_dtype="vllm-internal-unrecorded",
        attention_backend="vllm-auto",
        fixed_batch_shape=16,
        batch_invariant_requested=dtype != "float32",
        temperature=0.0,
        max_tokens=32,
        terminal_and_intermediate_same_engine=True,
    )


def test_dtype_is_part_of_automatic_fingerprint() -> None:
    fp16 = provenance("float16").contract_fingerprint(
        proposer_dtype="float16",
        concurrency=16,
        language="English",
        arrival="episode-sync",
    )
    fp32 = provenance("float32").contract_fingerprint(
        proposer_dtype="float16",
        concurrency=16,
        language="English",
        arrival="episode-sync",
    )
    assert fp16 != fp32


def test_violation_taxonomy_separates_replay() -> None:
    stage = {
        "output_violations": 2,
        "state_violations": 1,
        "audit_violation_rows": [
            {
                "verified": True,
                "comparison": {"state_projection_token_exact": False},
            },
            {
                "verified": False,
                "comparison": {"state_projection_token_exact": True},
            },
        ],
    }
    result = classify_postrun_disagreements(stage)
    assert result["online_selection_authority_violations"] == 0
    assert result["canonical_replay_state_disagreements"] == 1
    assert result["unverified_selected_vs_postrun_state_disagreements"] == 0


def test_c16_wave_misses_headroom_despite_hard_deadline() -> None:
    result = guarded_capacity(
        measured_p99_seconds=1.9418401885777712,
        guard_seconds=0.1,
        deadline_seconds=2.0,
    )
    assert result["hard_deadline_met"]
    assert not result["headroom_contract_met"]

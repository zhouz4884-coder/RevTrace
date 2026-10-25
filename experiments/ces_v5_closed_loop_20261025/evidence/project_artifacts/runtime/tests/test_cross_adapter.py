from revtrace.cross_adapter import (
    decide_qwen_cross_adapter,
    normalized_boundary_chunk_id,
    unit_edit_rate,
)


def test_dgft_uses_coarse_authority_but_preserves_evidence_diagnostics():
    decision = decide_qwen_cross_adapter(
        fine_text="alpha beta gamma",
        coarse_text="alpha beta",
        fine_minimum_margin=0.01,
        mode="dgft",
        terminal=True,
    )
    assert decision.selected_authority == "coarse-segment"
    assert not decision.replay_required
    assert set(decision.reasons) == {
        "directional-omission", "fine-numerical-risk", "terminal-finalization"
    }


def test_hybrid_replays_only_when_a_frozen_signal_requires_authority():
    safe = decide_qwen_cross_adapter(
        fine_text="模型配置完成",
        coarse_text="模型配置完成",
        fine_minimum_margin=0.5,
        mode="hybrid",
    )
    assert not safe.replay_required
    assert safe.selected_authority == "coarse-segment"

    omission = decide_qwen_cross_adapter(
        fine_text="模型配置完成",
        coarse_text="模型完成",
        fine_minimum_margin=0.5,
        mode="hybrid",
    )
    assert omission.replay_required
    assert omission.selected_authority == "fine-singleton-replay"


def test_unit_edit_rate_and_boundary_transport_are_deterministic():
    assert unit_edit_rate("alpha beta", "alpha beta") == 0.0
    assert unit_edit_rate("模型配置", "模型") == 0.5
    assert normalized_boundary_chunk_id(6, 3) == 9

from __future__ import annotations

import pytest

from revtrace.whisper_state import (
    LocalAgreement2,
    PromptState,
    PromptTransition,
    StalePromptTransition,
    WhisperStateRiskPolicy,
    WhisperStateAction,
    WhisperVersion,
    append_prompt_tokens,
    capacity_rebase_required,
    commit_prompt_transition,
    cuda_device_index,
    longest_common_prefix,
    prompt_state_action,
    physical_cuda_device_count,
    proposer_authority_spillover_eligible,
    proposer_terminal_spillover_eligible,
    terminal_frontier_reached,
    work_budget_requires_authority,
)


def test_physical_cuda_device_count_deduplicates_colocated_roles() -> None:
    assert cuda_device_index("cuda") == 0
    assert cuda_device_index("cuda:0") == 0
    assert physical_cuda_device_count(("cuda:0", "cuda:0")) == 1
    assert physical_cuda_device_count(("cuda", "cuda:1")) == 2


def test_cuda_device_index_rejects_non_cuda_device() -> None:
    with pytest.raises(ValueError, match="not a CUDA device"):
        cuda_device_index("cpu")


def test_longest_common_prefix() -> None:
    assert longest_common_prefix([1, 2, 3], [1, 2, 4]) == (1, 2)


def test_previous_token_state_accumulates_without_retokenizing() -> None:
    first = append_prompt_tokens(
        (), (10, 11), start_of_previous_token=99, maximum_tokens=5
    )
    assert first == (99, 10, 11)
    second = append_prompt_tokens(
        first,
        (12, 13, 14),
        start_of_previous_token=99,
        maximum_tokens=5,
    )
    assert second == (99, 11, 12, 13, 14)


def test_previous_token_state_rejects_degenerate_budget() -> None:
    with pytest.raises(ValueError):
        append_prompt_tokens(
            (), (10,), start_of_previous_token=99, maximum_tokens=1
        )


def test_local_agreement_two_requires_two_hypotheses() -> None:
    policy = LocalAgreement2()
    assert policy.update([1, 2, 3]) == ()
    assert policy.update([1, 2, 4]) == (1, 2)
    assert policy.flush([1, 2, 4, 5]) == (1, 2, 4, 5)


def test_whisper_state_risk_policy_is_state_age_aware() -> None:
    policy = WhisperStateRiskPolicy(
        margin_threshold=0.03515725,
        late_window_index=7,
        late_margin_threshold=0.0703135,
    )
    assert policy.reason(0.03, window_index=2) == "base-margin"
    assert policy.reason(0.06, window_index=6) is None
    assert policy.reason(0.06, window_index=7) == "late-state-margin"
    assert policy.reason(None, window_index=0) == "missing-margin"
    assert not policy.requires_canonical(0.08, window_index=8)


def test_whisper_state_risk_policy_rejects_partial_late_clause() -> None:
    with pytest.raises(ValueError):
        WhisperStateRiskPolicy(
            margin_threshold=0.03,
            late_window_index=7,
        )


def test_whisper_state_risk_policy_is_prompt_load_aware() -> None:
    policy = WhisperStateRiskPolicy(
        margin_threshold=0.02,
        late_window_index=7,
        late_margin_threshold=0.04,
        high_load_prompt_tokens=110,
        high_load_margin_threshold=0.09,
    )
    assert policy.reason(
        0.08, window_index=2, prompt_tokens=109
    ) is None
    assert policy.reason(
        0.08, window_index=2, prompt_tokens=110
    ) == "high-load-state-margin"
    assert prompt_state_action(
        policy,
        0.08,
        window_index=2,
        prompt_tokens=110,
        terminal=False,
        checkpoint_due=False,
    ) == WhisperStateAction.RISK_AUTHORITY


def test_whisper_state_risk_policy_rejects_partial_load_clause() -> None:
    with pytest.raises(ValueError):
        WhisperStateRiskPolicy(
            margin_threshold=0.03,
            high_load_prompt_tokens=100,
        )
    with pytest.raises(ValueError):
        WhisperStateRiskPolicy(
            margin_threshold=0.03,
            high_load_prompt_tokens=100,
            high_load_margin_threshold=0.02,
        )


def test_prompt_commit_is_parent_version_bound() -> None:
    version = WhisperVersion("s0", 3, 7, 0)
    state = PromptState(version, (), "")
    transition = PromptTransition(
        parent=version,
        selected_token_ids=(10, 11),
        selected_text="hello",
        source="canonical",
        terminal=False,
        minimum_margin=0.1,
    )
    committed = commit_prompt_transition(state, transition)
    assert committed.prompt_token_ids == (10, 11)
    assert committed.version.state_version == 1
    with pytest.raises(StalePromptTransition):
        commit_prompt_transition(committed, transition)


def test_prompt_state_action_separates_display_and_state_authority() -> None:
    policy = WhisperStateRiskPolicy(margin_threshold=0.05)
    assert prompt_state_action(
        policy,
        0.01,
        window_index=2,
        terminal=False,
        checkpoint_due=False,
    ) == WhisperStateAction.RISK_AUTHORITY
    assert prompt_state_action(
        policy,
        1.0,
        window_index=2,
        terminal=False,
        checkpoint_due=False,
    ) == WhisperStateAction.FAST_COMMIT
    assert prompt_state_action(
        policy,
        0.01,
        window_index=9,
        terminal=False,
        checkpoint_due=True,
    ) == WhisperStateAction.CHECKPOINT_AUTHORITY
    assert prompt_state_action(
        policy,
        0.01,
        window_index=10,
        terminal=True,
        checkpoint_due=True,
    ) == WhisperStateAction.TERMINAL_AUTHORITY


def test_capacity_rebase_uses_declared_decoder_envelope() -> None:
    assert not capacity_rebase_required(
        128,
        declared_next_segment_tokens=96,
        maximum_prompt_tokens=224,
    )
    assert capacity_rebase_required(
        129,
        declared_next_segment_tokens=96,
        maximum_prompt_tokens=224,
    )


def test_terminal_spillover_requires_every_session_at_terminal_frontier() -> None:
    assert not terminal_frontier_reached(
        [9, 8, 9], windows_per_session=10
    )
    assert terminal_frontier_reached(
        [9, 10, 9], windows_per_session=10
    )
    with pytest.raises(ValueError):
        terminal_frontier_reached([0], windows_per_session=0)


def test_terminal_spillover_requires_terminal_and_no_ready_proposal() -> None:
    assert proposer_terminal_spillover_eligible(
        terminal=True,
        ready_sessions=[],
    )
    assert not proposer_terminal_spillover_eligible(
        terminal=False,
        ready_sessions=[],
    )
    assert not proposer_terminal_spillover_eligible(
        terminal=True,
        ready_sessions=[3],
    )


def test_authority_spillover_requires_no_ready_proposal() -> None:
    assert proposer_authority_spillover_eligible(ready_sessions=[])
    assert not proposer_authority_spillover_eligible(ready_sessions=[2])


def test_work_budget_saturation_requires_extended_authority() -> None:
    assert work_budget_requires_authority(
        80,
        proposer_max_new_tokens=80,
        authority_max_new_tokens=96,
    )
    assert not work_budget_requires_authority(
        79,
        proposer_max_new_tokens=80,
        authority_max_new_tokens=96,
    )
    assert not work_budget_requires_authority(
        80,
        proposer_max_new_tokens=80,
        authority_max_new_tokens=80,
    )
    with pytest.raises(ValueError):
        work_budget_requires_authority(
            -1,
            proposer_max_new_tokens=80,
            authority_max_new_tokens=96,
        )


def test_authority_budget_can_require_earlier_capacity_rebase() -> None:
    """A smaller speculative work cap must not define target state."""

    assert not capacity_rebase_required(
        129,
        declared_next_segment_tokens=80,
        maximum_prompt_tokens=224,
    )
    assert capacity_rebase_required(
        129,
        declared_next_segment_tokens=96,
        maximum_prompt_tokens=224,
    )

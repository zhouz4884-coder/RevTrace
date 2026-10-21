from __future__ import annotations

import pytest

from revtrace.feedback_coherence import (
    CoherenceMode,
    EFSCContract,
    ElasticFeedbackController,
    ElasticFeedbackState,
    EpochFencedBackgroundProfiler,
    FeedbackAction,
    FeedbackCandidate,
    FeedbackIdentity,
    ProfilerChannel,
    QwenRollbackAdapter,
    StaleFeedbackCandidate,
    WhisperHistoryAdapter,
    calibrate_hysteresis_margins,
)


def contract(**updates: object) -> EFSCContract:
    values: dict[str, object] = {
        "enter_margin": 0.05,
        "exit_margin": 0.10,
        "minimum_hold_windows": 1,
        "safe_streak_required": 2,
        "maximum_quarantine_windows": 3,
        "maximum_feedback_debt": 3,
        "maximum_influence_windows": 3,
        "maximum_prompt_tokens": 32,
        "decay_suffix_tokens": 2,
    }
    values.update(updates)
    return EFSCContract(**values)  # type: ignore[arg-type]


def initial(session_id: str = "s") -> ElasticFeedbackState:
    return ElasticFeedbackState(
        FeedbackIdentity(session_id, 4, 7, 0),
        last_reset_version=0,
    )


def candidate(
    state: ElasticFeedbackState,
    margin: float | None,
    tokens: tuple[int, ...] = (10, 11),
    *,
    terminal: bool = False,
) -> FeedbackCandidate:
    identity = state.identity
    return FeedbackCandidate(
        session_id=identity.session_id,
        contract_epoch=identity.contract_epoch,
        policy_version=identity.policy_version,
        parent_state_version=identity.state_version,
        token_ids=tokens,
        minimum_margin=margin,
        terminal=terminal,
    )


@pytest.mark.parametrize(
    "adapter",
    [WhisperHistoryAdapter(16), QwenRollbackAdapter()],
)
def test_shared_controller_actions_apply_to_whisper_and_qwen(adapter: object) -> None:
    controller = ElasticFeedbackController(
        contract(maximum_influence_windows=10)
    )
    state = initial()
    actions: list[FeedbackAction] = []
    for margin in (0.20, 0.01, 0.20, 0.20, 0.20):
        state, preparation = controller.prepare_for_proposal(state, adapter)  # type: ignore[arg-type]
        if preparation.action is not None:
            actions.append(preparation.action)
        state, decision = controller.step(
            state,
            candidate(state, margin),
            adapter,  # type: ignore[arg-type]
        )
        actions.append(decision.action)
    assert actions == [
        FeedbackAction.FAST_COMMIT,
        FeedbackAction.PROVISIONAL_HOLD,
        FeedbackAction.PROVISIONAL_HOLD,
        FeedbackAction.DECAY_SUFFIX,
        FeedbackAction.FAST_COMMIT,
    ]
    assert state.mode == CoherenceMode.COHERENT


@pytest.mark.parametrize(
    "adapter",
    [WhisperHistoryAdapter(16), QwenRollbackAdapter()],
)
def test_provisional_output_never_becomes_feedback_ancestor(adapter: object) -> None:
    controller = ElasticFeedbackController(contract())
    state, committed = controller.step(
        initial(), candidate(initial(), 0.20, (1, 2)), adapter  # type: ignore[arg-type]
    )
    assert committed.candidate_became_ancestor
    before_atoms = state.atoms
    provisional_version = state.identity.state_version + 1
    state, held = controller.step(
        state, candidate(state, 0.01, (99,)), adapter  # type: ignore[arg-type]
    )
    assert held.action == FeedbackAction.PROVISIONAL_HOLD
    assert held.display_token_ids == (99,)
    assert state.atoms == before_atoms
    assert provisional_version not in state.ancestors
    assert not held.candidate_became_ancestor


def test_qwen_projection_replaces_prefix_while_whisper_appends_history() -> None:
    controller = ElasticFeedbackController(contract(maximum_feedback_debt=8))
    qwen = initial("q")
    whisper = initial("w")
    qwen, _ = controller.step(qwen, candidate(qwen, 0.2, (1, 2)), QwenRollbackAdapter())
    whisper, _ = controller.step(
        whisper,
        candidate(whisper, 0.2, (1, 2)),
        WhisperHistoryAdapter(16),
    )
    qwen, _ = controller.step(qwen, candidate(qwen, 0.2, (3,)), QwenRollbackAdapter())
    whisper, _ = controller.step(
        whisper,
        candidate(whisper, 0.2, (3,)),
        WhisperHistoryAdapter(16),
    )
    assert tuple(atom.token_id for atom in qwen.atoms) == (3,)
    assert tuple(atom.token_id for atom in whisper.atoms) == (1, 2, 3)


def test_decay_is_non_expanding_but_only_reset_erases_causal_ancestry() -> None:
    controller = ElasticFeedbackController(
        contract(maximum_feedback_debt=8, decay_suffix_tokens=1)
    )
    adapter = WhisperHistoryAdapter(16)
    state = initial()
    state, _ = controller.step(state, candidate(state, 0.2, (1, 2)), adapter)
    original_ancestors = state.ancestors
    state, _ = controller.step(state, candidate(state, 0.01), adapter)
    state, _ = controller.step(state, candidate(state, 0.2), adapter)
    state, decision = controller.step(state, candidate(state, 0.2), adapter)
    assert decision.action == FeedbackAction.DECAY_SUFFIX
    assert state.ancestors.issubset(original_ancestors)
    assert state.ancestors  # token truncation is not a causal reset

    # The hard influence horizon, not DECAY, eventually erases every ancestor.
    state, preparation = controller.prepare_for_proposal(state, adapter)
    assert preparation.action == FeedbackAction.SAFE_RESET
    assert state.ancestors == frozenset()


def test_feedback_debt_forces_reset_before_an_unbounded_chain() -> None:
    controller = ElasticFeedbackController(contract())
    adapter = QwenRollbackAdapter()
    state = initial()
    for _ in range(3):
        state, preparation = controller.prepare_for_proposal(state, adapter)
        assert preparation.action is None
        state, decision = controller.step(
            state, candidate(state, 0.2), adapter
        )
        assert decision.action == FeedbackAction.FAST_COMMIT
    assert state.feedback_debt == 3
    with pytest.raises(RuntimeError, match="retire feedback debt"):
        controller.step(state, candidate(state, 0.2), adapter)
    state, preparation = controller.prepare_for_proposal(state, adapter)
    assert preparation.action == FeedbackAction.SAFE_RESET
    assert preparation.reason == "feedback-debt-bound"
    assert state.feedback_debt == 0
    assert state.atoms == ()
    assert state.mode == CoherenceMode.REANCHOR


def test_influence_horizon_is_independent_of_margin_success() -> None:
    controller = ElasticFeedbackController(
        contract(maximum_feedback_debt=100, maximum_influence_windows=2)
    )
    adapter = QwenRollbackAdapter()
    state = initial()
    preparations: list[FeedbackAction] = []
    for _ in range(4):
        state, preparation = controller.prepare_for_proposal(state, adapter)
        if preparation.action is not None:
            preparations.append(preparation.action)
        state, decision = controller.step(
            state, candidate(state, 1.0), adapter
        )
    assert preparations == [FeedbackAction.SAFE_RESET]
    assert state.oldest_ancestor_age == 0


def test_terminal_display_does_not_acquire_future_state_authority() -> None:
    controller = ElasticFeedbackController(contract())
    adapter = WhisperHistoryAdapter(16)
    state = initial()
    state, decision = controller.step(
        state, candidate(state, 1.0, (77,), terminal=True), adapter
    )
    assert decision.action == FeedbackAction.PROVISIONAL_HOLD
    assert decision.display_token_ids == (77,)
    assert state.atoms == ()
    assert not decision.candidate_became_ancestor


def test_stale_contract_policy_and_parent_fail_closed() -> None:
    controller = ElasticFeedbackController(contract())
    state = initial()
    stale = FeedbackCandidate("s", 4, 8, 0, (1,), 0.2)
    with pytest.raises(StaleFeedbackCandidate):
        controller.step(state, stale, QwenRollbackAdapter())


def test_calibration_is_data_derived_and_hysteretic() -> None:
    value = calibrate_hysteresis_margins(
        [0.02, 0.06, 0.10, 0.20],
        [0.01, 0.05],
        exit_quantile=0.75,
    )
    assert value.enter_margin == 0.05
    assert value.exit_margin == 0.10
    assert value.exit_margin > value.enter_margin


def test_epoch_fence_keeps_triggered_diagnostics_out_of_certificate() -> None:
    profiler = EpochFencedBackgroundProfiler(
        epoch=3, sentinel_probability=0.1
    )
    sentinel = profiler.decide(FeedbackAction.FAST_COMMIT, draw=0.01)
    assert sentinel.channel == ProfilerChannel.RANDOM_SENTINEL
    assert sentinel.certifies_current_epoch
    profiler.observe(sentinel, state_error=True)

    diagnostic = profiler.decide(FeedbackAction.PROVISIONAL_HOLD)
    assert diagnostic.channel == ProfilerChannel.TRIGGERED_DIAGNOSTIC
    assert not diagnostic.certifies_current_epoch
    profiler.observe(diagnostic, state_error=True)

    assert profiler.evidence.sentinel_audits == 1
    assert profiler.evidence.caught_state_errors == 1
    assert profiler.evidence.diagnostic_probes == 1
    assert profiler.evidence.diagnostic_errors == 1

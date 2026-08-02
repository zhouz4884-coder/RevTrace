from revtrace.dgft import (
    boundary_adjusted_coverage_deficit,
    adaptive_audio_plan,
    balanced_replay_plan,
    build_dual_axis_certificate,
    CanonicalSegmentJob,
    FeedbackTransactionState,
    commit_canonical_segment,
    commit_checkpoint_rebase,
    commit_session_fallback,
    repeated_ngram_fraction,
    classify_asymmetric_omission_conflict,
    classify_coverage_conflict,
    cross_granularity_coverage_deficit,
    digest_tokens,
    fixed_segment_plan,
)


def test_boundary_adjustment_cancels_adjacent_transport() -> None:
    fine = ["alpha beta", "gamma delta epsilon"]
    coarse = ["alpha beta gamma", "delta epsilon"]
    adjusted, raw, residual = boundary_adjusted_coverage_deficit(
        fine, coarse, 1
    )
    assert raw == 1
    assert residual == 0
    assert adjusted == 0.0


def test_boundary_adjustment_preserves_true_omission() -> None:
    fine = ["alpha beta", "gamma delta epsilon"]
    coarse = ["alpha beta", "gamma epsilon"]
    adjusted, raw, residual = boundary_adjusted_coverage_deficit(
        fine, coarse, 1
    )
    assert raw == 1
    assert residual == 1
    assert adjusted == 1 / 3


def test_repeated_ngram_fraction_detects_phrase_loop() -> None:
    loop = (
        "he was a man of the same kind and was a man of the same kind "
        "and was a man of the same kind"
    )
    assert repeated_ngram_fraction(loop) >= 0.25
    assert repeated_ngram_fraction("a short ordinary sentence") == 0.0
import numpy as np


def test_directional_cross_granularity_coverage_detects_omission():
    fine = "alpha beta gamma delta epsilon"
    coarse = "alpha beta epsilon"
    assert cross_granularity_coverage_deficit(fine, coarse) == 0.4
    decision = classify_coverage_conflict(
        fine, coarse, threshold=0.25
    )
    assert decision.fallback_required
    assert decision.deficit == 0.4


def test_cross_granularity_coverage_is_reference_free_and_order_sensitive():
    assert cross_granularity_coverage_deficit("", "") == 0.0
    assert cross_granularity_coverage_deficit("", "hallucination") == 1.0
    assert cross_granularity_coverage_deficit(
        "one two three", "one two three"
    ) == 0.0
    assert cross_granularity_coverage_deficit(
        "one two three", "three two one"
    ) > 0.0


def test_asymmetric_omission_escalates_but_mutual_disagreement_does_not():
    omission = classify_asymmetric_omission_conflict(
        "alpha beta gamma delta", "alpha beta",
        forward_threshold=0.20, reverse_ceiling=0.20,
    )
    assert omission.fallback_required
    mutual = classify_asymmetric_omission_conflict(
        "alpha beta gamma delta", "omega sigma tau",
        forward_threshold=0.20, reverse_ceiling=0.20,
    )
    assert not mutual.fallback_required


def test_fixed_segment_plan_has_no_gap_or_overlap():
    assert fixed_segment_plan(windows=9, windows_per_segment=2) == (
        (0, 2), (2, 4), (4, 6), (6, 8), (8, 9)
    )


def test_balanced_replay_plan_avoids_short_tail():
    plan = balanced_replay_plan(
        start_sample=0, end_sample=25 * 16_000,
        maximum_samples=10 * 16_000,
    )
    assert plan[0][0] == 0
    assert plan[-1][1] == 25 * 16_000
    assert all(left[1] == right[0] for left, right in zip(plan, plan[1:]))
    durations = [(end - start) / 16_000 for start, end in plan]
    assert max(durations) <= 10.0
    assert min(durations) >= 8.0
    assert fixed_segment_plan(windows=9, windows_per_segment=3) == (
        (0, 3), (3, 6), (6, 9)
    )


def _state():
    return FeedbackTransactionState(
        session_id=7,
        contract_epoch=3,
        policy_version="frozen-r9",
        prompt_tokens=(4, 5),
        speculative_version=10,
    )


def _job(**overrides):
    values = dict(
        session_id=7,
        contract_epoch=3,
        policy_version="frozen-r9",
        parent_checkpoint_id=0,
        audio_start_window=0,
        audio_end_window=3,
        segment_id="7:0:3",
        prompt_digest=digest_tokens((4, 5)),
    )
    values.update(overrides)
    return CanonicalSegmentJob(**values)


def test_atomic_segment_commit_advances_all_authoritative_fields():
    result = commit_canonical_segment(
        _state(), _job(), segment_tokens=(8, 9),
        next_prompt_tokens=(4, 5, 8, 9),
        descendant_versions=(9, 11, 12),
    )
    assert result.accepted
    assert result.state.checkpoint_id == 1
    assert result.state.audio_frontier_window == 3
    assert result.state.prompt_tokens == (4, 5, 8, 9)
    assert result.state.stable_token_segments == ((8, 9),)
    assert result.invalidated_speculative_versions == (11, 12)


def test_segment_commit_rejects_stale_and_gap_jobs_without_mutation():
    state = _state()
    for job, reason in (
        (_job(parent_checkpoint_id=2), "stale-parent-checkpoint"),
        (_job(audio_start_window=1), "audio-gap-or-overlap"),
        (_job(contract_epoch=2), "stale-epoch"),
        (_job(session_id=8), "cross-session"),
        (_job(prompt_digest="bad"), "prompt-digest-mismatch"),
    ):
        result = commit_canonical_segment(
            state, job, segment_tokens=(1,), next_prompt_tokens=(1,)
        )
        assert not result.accepted
        assert result.reason == reason
        assert result.state is state


def test_duplicate_segment_is_idempotently_rejected():
    first = commit_canonical_segment(
        _state(), _job(), segment_tokens=(1,), next_prompt_tokens=(4, 5, 1)
    )
    duplicate = commit_canonical_segment(
        first.state,
        _job(parent_checkpoint_id=1, audio_start_window=3, audio_end_window=4,
             prompt_digest=digest_tokens((4, 5, 1))),
        segment_tokens=(2,), next_prompt_tokens=(2,),
    )
    assert not duplicate.accepted
    assert duplicate.reason == "duplicate-segment"


def test_checkpoint_rebase_preserves_prefix_and_replaces_descendants():
    state = FeedbackTransactionState(
        session_id=7,
        contract_epoch=3,
        policy_version="frozen-r9",
        checkpoint_id=3,
        audio_frontier_window=90,
        prompt_tokens=(99,),
        stable_token_segments=((1,), (2,), (3,)),
        committed_segment_ids=("s0", "s1", "s2"),
        speculative_version=10,
    )
    result = commit_checkpoint_rebase(
        state,
        expected_contract_epoch=3,
        expected_policy_version="frozen-r9",
        rebase_checkpoint_id=1,
        audio_start_frontier=20,
        final_audio_frontier=90,
        replacement_segments=((20,), (30,)),
        next_prompt_tokens=(20, 30),
        fallback_id="rebase:7:20",
        descendant_versions=(9, 11, 12),
    )
    assert result.accepted
    assert result.state.stable_token_segments == ((1,), (20,), (30,))
    assert result.state.committed_segment_ids == (
        "s0", "rebase:7:20", "rebase:7:20:1"
    )
    assert result.state.audio_frontier_window == 90
    assert result.invalidated_speculative_versions == (11, 12)


def test_checkpoint_rebase_rejects_invalid_cut_without_mutation():
    state = _state()
    result = commit_checkpoint_rebase(
        state,
        expected_contract_epoch=3,
        expected_policy_version="frozen-r9",
        rebase_checkpoint_id=2,
        audio_start_frontier=1,
        final_audio_frontier=3,
        replacement_segments=((1,),),
        next_prompt_tokens=(1,),
        fallback_id="bad",
    )
    assert not result.accepted
    assert result.reason == "invalid-rebase-checkpoint"
    assert result.state is state


def test_terminal_fallback_atomically_replaces_coarse_branch():
    coarse = commit_canonical_segment(
        _state(), _job(), segment_tokens=(99,), next_prompt_tokens=(4, 5, 99)
    ).state
    result = commit_session_fallback(
        coarse,
        expected_contract_epoch=3,
        expected_policy_version="frozen-r9",
        final_audio_frontier=9,
        replacement_segments=((1, 2), (3, 4)),
        next_prompt_tokens=(1, 2, 3, 4),
        fallback_id="fallback:7",
        descendant_versions=(11, 12),
    )
    assert result.accepted
    assert result.state.stable_token_segments == ((1, 2), (3, 4))
    assert result.state.audio_frontier_window == 9
    assert result.invalidated_speculative_versions == (11, 12)


def test_dual_axis_certificate_separates_display_and_feedback_state():
    certificate = build_dual_axis_certificate(
        job=_job(), audio=b"raw-audio", display_tokens=(1, 2, 3),
        feedback_state_tokens=(1, 2), canonical_runtime_digest="runtime-v1",
    )
    assert certificate.display_sha256 != certificate.feedback_state_sha256
    assert certificate.audio_sha256


def test_adaptive_audio_plan_is_gap_free_and_uses_late_silence():
    audio = np.ones(70 * 16_000, dtype=np.float32)
    audio[28 * 16_000:29 * 16_000] = 0
    audio[56 * 16_000:57 * 16_000] = 0
    plan = adaptive_audio_plan(
        audio, sample_rate=16_000, minimum_seconds=15, maximum_seconds=30
    )
    assert plan[0][0] == 0
    assert plan[-1][1] == audio.size
    assert all(left[1] == right[0] for left, right in zip(plan, plan[1:]))
    assert 28 * 16_000 <= plan[0][1] <= 29 * 16_000


def test_adaptive_audio_plan_never_creates_a_subminimum_tail():
    audio = np.ones(50 * 16_000, dtype=np.float32)
    audio[19 * 16_000:20 * 16_000] = 0
    audio[49 * 16_000:50 * 16_000] = 0
    plan = adaptive_audio_plan(
        audio, sample_rate=16_000, minimum_seconds=15, maximum_seconds=30
    )
    durations = [(end - start) / 16_000 for start, end in plan]
    assert all(15 <= value <= 30 for value in durations)

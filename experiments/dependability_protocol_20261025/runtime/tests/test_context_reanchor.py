from __future__ import annotations

from dataclasses import replace

import pytest

from revtrace.context_reanchor import (
    CapsuleRejected,
    ContextCapsule,
    RecoveryState,
    RecoveryVersion,
    advance_audio_frontier,
    asymmetric_context_conflict,
    bound_feedback_prompt,
    extract_bounded_audio_delta,
    install_context_capsule,
    publish_provisional,
    safe_display_override_candidate,
)


def test_bound_feedback_prompt_preserves_marker_and_recent_suffix() -> None:
    assert bound_feedback_prompt(
        (99, 1, 2, 3, 4),
        start_of_previous_token=99,
        maximum_content_tokens=2,
    ) == (99, 3, 4)


def test_bound_feedback_prompt_handles_unmarked_and_zero_budget() -> None:
    assert bound_feedback_prompt(
        (1, 2, 3),
        start_of_previous_token=99,
        maximum_content_tokens=2,
    ) == (99, 2, 3)
    assert bound_feedback_prompt(
        (99, 1),
        start_of_previous_token=99,
        maximum_content_tokens=0,
    ) == ()


def test_bounded_audio_delta_uses_frontier_overlap() -> None:
    previous = (
        "And after a little consideration he came to the conclusion that "
        "his duty was to escape as quickly as he could."
    )
    overlapping = (
        "After a little consideration he came to the conclusion that his "
        "duty was to escape as quickly as he could. They bent eagerly over "
        "the board."
    )
    assert extract_bounded_audio_delta(previous, overlapping) == (
        "They bent eagerly over the board."
    )


def test_bounded_audio_delta_fails_closed_without_overlap() -> None:
    assert extract_bounded_audio_delta(
        "The previous window has enough words.",
        "A completely unrelated decode begins here and continues.",
    ) is None


def test_asymmetric_context_conflict_is_a_fail_closed_schedule_signal() -> None:
    assert asymmetric_context_conflict(2, 8)
    assert asymmetric_context_conflict(1, 23)
    assert not asymmetric_context_conflict(3, 23)
    assert not asymmetric_context_conflict(1, 7)


def test_display_override_rejects_nonterminal_or_repetitive_candidate() -> None:
    valid = dict(
        terminated_by_eos=True,
        generation_steps=20,
        maximum_generation_steps=96,
        compression_ratio=1.2,
        longest_repetition_run=1,
    )
    assert safe_display_override_candidate(**valid)
    assert not safe_display_override_candidate(
        **(valid | {"terminated_by_eos": False})
    )
    assert not safe_display_override_candidate(
        **(valid | {"compression_ratio": 7.04})
    )
    assert not safe_display_override_candidate(
        **(valid | {"longest_repetition_run": 4})
    )
from revtrace.feedback_coherence import (
    CoherenceMode,
    ElasticFeedbackState,
    FeedbackAtom,
    FeedbackIdentity,
    install_authoritative_feedback_capsule,
)


def initial_state() -> RecoveryState:
    return RecoveryState(
        version=RecoveryVersion(
            session_id="s0",
            contract_epoch=3,
            policy_version=7,
            revision_version=4,
            feedback_lineage_version=2,
            audio_frontier_version=10,
            anchor_id="genesis",
        ),
        prompt_token_ids=(1, 2),
        prompt_text="old",
        provisional_display="visible provisional text",
    )


def capsule(state: RecoveryState) -> ContextCapsule:
    return ContextCapsule.create(
        capsule_id="cap-1",
        parent=state.version,
        audio_start_version=6,
        audio_end_version=10,
        expires_after_audio_frontier=12,
        prompt_token_ids=(7, 8, 9),
        prompt_text="canonical snapshot",
        canonical_runtime_digest="runtime-sha256",
    )


def test_audio_and_display_advance_without_feedback_authority() -> None:
    state = initial_state()
    displayed = publish_provisional(state, "new provisional")
    advanced = advance_audio_frontier(displayed, new_frontier=11)
    assert advanced.prompt_token_ids == state.prompt_token_ids
    assert advanced.version.feedback_lineage_version == 2
    assert advanced.version.revision_version == 4
    assert advanced.version.audio_frontier_version == 11
    assert advanced.provisional_display == "new provisional"


def test_capsule_install_is_atomic_and_preserves_display() -> None:
    state = initial_state()
    installed = install_context_capsule(state, capsule(state))
    assert installed.prompt_token_ids == (7, 8, 9)
    assert installed.version.anchor_id == "cap-1"
    assert installed.version.revision_version == 5
    assert installed.version.feedback_lineage_version == 3
    assert installed.version.audio_frontier_version == 10
    assert installed.provisional_display == state.provisional_display


def test_current_capsule_reinstall_is_idempotent() -> None:
    state = initial_state()
    item = capsule(state)
    installed = install_context_capsule(state, item)
    assert install_context_capsule(installed, item) is installed


@pytest.mark.parametrize(
    "mutation, message",
    [
        ({"session_id": "other"}, "cross-session"),
        ({"contract_epoch": 4}, "contract epoch"),
        ({"policy_version": 8}, "policy version"),
        ({"parent_anchor_id": "old"}, "parent anchor"),
        ({"parent_feedback_lineage_version": 1}, "feedback lineage"),
        ({"audio_end_version": 11}, "future audio"),
        ({"canonical_runtime_digest": ""}, "provenance"),
        ({"token_sha256": "bad"}, "digest"),
    ],
)
def test_capsule_rejects_invalid_authority(mutation, message) -> None:
    state = initial_state()
    with pytest.raises(CapsuleRejected, match=message):
        install_context_capsule(state, replace(capsule(state), **mutation))


def test_capsule_rejects_expired_and_stale_replay() -> None:
    state = initial_state()
    item = capsule(state)
    expired = advance_audio_frontier(state, new_frontier=13)
    with pytest.raises(CapsuleRejected, match="expired"):
        install_context_capsule(expired, item)

    installed = install_context_capsule(state, item)
    second = ContextCapsule.create(
        capsule_id="cap-2",
        parent=state.version,
        audio_start_version=6,
        audio_end_version=10,
        expires_after_audio_frontier=12,
        prompt_token_ids=(10,),
        prompt_text="stale",
        canonical_runtime_digest="runtime-sha256",
    )
    with pytest.raises(CapsuleRejected, match="parent anchor"):
        install_context_capsule(installed, second)


def test_authoritative_projection_clears_provisional_ancestry() -> None:
    state = ElasticFeedbackState(
        identity=FeedbackIdentity("s0", 3, 7, 5),
        atoms=(FeedbackAtom(11, frozenset({2, 5})),),
        mode=CoherenceMode.QUARANTINE,
        feedback_debt=2,
        hold_age=1,
        safe_streak=0,
        last_reset_version=1,
    )
    installed = install_authoritative_feedback_capsule(state, (20, 21))
    assert tuple(atom.token_id for atom in installed.atoms) == (20, 21)
    assert installed.ancestors == frozenset()
    assert installed.identity.state_version == 6
    assert installed.mode == CoherenceMode.COHERENT
    assert installed.feedback_debt == 0

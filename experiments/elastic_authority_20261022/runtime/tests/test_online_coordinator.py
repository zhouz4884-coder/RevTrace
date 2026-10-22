from revtrace.causal_scheduler import initial_session_arrivals, group_ready_events
from revtrace.online_coordinator import OnlineRevisionCoordinator


def test_poisson_arrival_is_generated_once_and_reproducible() -> None:
    left = initial_session_arrivals(
        sessions=8, arrival="poisson", scale=0.02, seed=7
    )
    right = initial_session_arrivals(
        sessions=8, arrival="poisson", scale=0.02, seed=7
    )
    assert left == right
    assert len({row.session_id for row in left}) == 8
    assert all(row.arrival_time > 0 for row in left)


def test_group_ready_events_preserves_causal_release() -> None:
    groups = group_ready_events(
        [(0, 1.0), (1, 1.1), (2, 4.0)], concurrency=2, coalesce=0.5
    )
    assert groups == [([0, 1], 1.1), ([2], 4.0)]


def test_online_certificate_is_consumed_before_commit() -> None:
    coordinator = OnlineRevisionCoordinator(
        sessions=1,
        contract_epoch=1,
        policy_version="r9-dgft-v4-semantic-escalation",
        contract_digest="contract",
        canonical_runtime_digest="runtime",
    )
    version = coordinator.register_speculative(
        0, window_index=0, ready_time=0.0
    )
    event = coordinator.commit_segment(
        session_id=0,
        audio_start_sample=0,
        audio_end_sample=16_000,
        audio=b"audio",
        prompt_tokens=(),
        display_tokens=(1, 2),
        feedback_state_tokens=(1, 2),
        authority_started=1.0,
        authority_finished=1.1,
    )
    assert event["certificate_consumed"]
    assert event["invalidated_speculative_versions"] == [version]
    assert coordinator.state(0).audio_frontier_window == 16_000
    coordinator.assert_complete([16_000])

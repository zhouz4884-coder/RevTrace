from __future__ import annotations

import os

import pytest

from revtrace.durable_journal import JournalError, JournalConflictError
from revtrace.online_coordinator import OnlineRevisionCoordinator


CONTRACT = {
    "sessions": 1,
    "contract_epoch": 1,
    "policy_version": "durable-test-v1",
    "contract_digest": "frozen-contract",
    "canonical_runtime_digest": "frozen-runtime",
}


def make_coordinator(path):
    return OnlineRevisionCoordinator(
        **CONTRACT,
        durable_journal_path=path,
    )


def commit_segment(coordinator, *, start=0, end=100, audio=b"segment-0",
                   prompt=(), tokens=(11, 12)):
    import time

    started = time.perf_counter()
    return coordinator.commit_segment(
        session_id=0,
        audio_start_sample=start,
        audio_end_sample=end,
        audio=audio,
        prompt_tokens=prompt,
        display_tokens=tokens,
        feedback_state_tokens=tokens,
        authority_started=started,
        authority_finished=started + 0.001,
    )


def committed_events(coordinator):
    return [
        event for event in coordinator.events()
        if event.get("event") in {
            "canonical-segment-committed",
            "terminal-fallback-committed",
        }
    ]


def test_acknowledged_commit_restores_and_same_retry_is_idempotent(tmp_path):
    path = tmp_path / "session.wal"
    first = make_coordinator(path)
    original = commit_segment(first)
    assert first.state(0).checkpoint_id == 1
    assert original["durable_journal_sequence"] == 1
    first.close()

    resumed = make_coordinator(path)
    state = resumed.state(0)
    assert state.checkpoint_id == 1
    assert state.audio_frontier_window == 100
    assert state.prompt_tokens == (11, 12)
    assert state.stable_token_segments == ((11, 12),)
    assert state.committed_segment_ids == ("0:0:100",)
    assert state.contract_epoch == 2  # Restart is a durable fencing epoch.

    replay = commit_segment(resumed)
    assert replay["idempotent_replay"] is True
    assert replay["durable_journal_sequence"] == 1
    assert resumed.state(0).checkpoint_id == 1
    assert len(committed_events(resumed)) == 1
    assert resumed._journal._next_sequence == 3  # genesis, commit, restart fence
    resumed.close()


def test_same_transaction_id_with_changed_payload_fails_closed(tmp_path):
    path = tmp_path / "session.wal"
    first = make_coordinator(path)
    commit_segment(first)
    first.close()

    resumed = make_coordinator(path)
    with pytest.raises(JournalConflictError, match="different content"):
        commit_segment(resumed, audio=b"different-audio")
    assert resumed.state(0).checkpoint_id == 1
    assert len(committed_events(resumed)) == 1
    resumed.close()


def test_torn_tail_is_discarded_without_losing_last_fsynced_commit(tmp_path):
    path = tmp_path / "session.wal"
    first = make_coordinator(path)
    commit_segment(first)
    first.close()

    with path.open("ab", buffering=0) as stream:
        stream.write(b"\x00\x00\x00\x80partial-frame")
        os.fsync(stream.fileno())
    resumed = make_coordinator(path)
    assert resumed._journal.truncated_tail_bytes > 0
    assert resumed.state(0).checkpoint_id == 1
    assert resumed.state(0).prompt_tokens == (11, 12)
    replay = commit_segment(resumed)
    assert replay["idempotent_replay"] is True
    assert len(committed_events(resumed)) == 1
    resumed.close()


def test_complete_frame_checksum_corruption_fails_closed(tmp_path):
    path = tmp_path / "session.wal"
    first = make_coordinator(path)
    commit_segment(first)
    first.close()

    payload = bytearray(path.read_bytes())
    payload[8] ^= 0x01  # Modify a byte in a complete frame's JSON payload.
    path.write_bytes(payload)
    with pytest.raises(JournalError, match="checksum mismatch"):
        make_coordinator(path)


def test_journal_rejects_a_second_active_owner(tmp_path):
    path = tmp_path / "session.wal"
    first = make_coordinator(path)
    try:
        with pytest.raises(JournalError, match="active owner"):
            make_coordinator(path)
    finally:
        first.close()


def test_wal_growth_tracks_new_state_deltas_not_full_history(tmp_path):
    def write_commits(path, count):
        service = make_coordinator(path)
        for index in range(count):
            start = index * 100
            end = start + 100
            prompt = () if index == 0 else (index + 9,)
            token = index + 10
            commit_segment(
                service,
                start=start,
                end=end,
                audio=f"audio-{index}".encode(),
                prompt=prompt,
                tokens=(token,),
            )
        service.close()
        return path.stat().st_size

    size_20 = write_commits(tmp_path / "twenty.wal", 20)
    size_40 = write_commits(tmp_path / "forty.wal", 40)
    assert size_40 < size_20 * 2.5


def test_terminal_replacement_is_durable_and_deduplicated(tmp_path):
    path = tmp_path / "session.wal"
    first = make_coordinator(path)
    event = first.commit_terminal_fallback(
        session_id=0,
        final_audio_frontier=100,
        audio=b"terminal-audio",
        replacement_segments=((31, 32), (33,)),
        next_prompt_tokens=(31, 32, 33),
        fallback_id="terminal:0",
        authority_started=0.0,
    )
    assert event["durable_journal_sequence"] == 1
    first.close()

    resumed = make_coordinator(path)
    assert resumed.state(0).stable_token_segments == ((31, 32), (33,))
    assert resumed.state(0).checkpoint_id == 1
    duplicate = resumed.commit_terminal_fallback(
        session_id=0,
        final_audio_frontier=100,
        audio=b"terminal-audio",
        replacement_segments=((31, 32), (33,)),
        next_prompt_tokens=(31, 32, 33),
        fallback_id="terminal:0",
        authority_started=0.0,
    )
    assert duplicate["idempotent_replay"] is True
    assert resumed.state(0).checkpoint_id == 1
    assert len(committed_events(resumed)) == 1
    resumed.close()

"""Fail-closed online coordinator for revision-state authority commits."""

from __future__ import annotations

from dataclasses import asdict, replace
import hashlib
import json
import threading
import time
from pathlib import Path
from typing import Any, Sequence

from .dgft import (
    CanonicalSegmentJob,
    FeedbackTransactionState,
    build_dual_axis_certificate,
    build_terminal_fallback_certificate,
    commit_canonical_segment,
    commit_session_fallback,
    digest_bytes,
    digest_token_segments,
    digest_tokens,
)
from .durable_journal import DurableCommitJournal


class OnlineRevisionCoordinator:
    """Consume certificates before an authority transition enters state.

    Each session has an independent lock-protected transaction state.  The
    coordinator records real process timestamps at registration, certification
    and commit; it does not reconstruct commit lag from audio duration.
    """

    def __init__(
        self,
        *,
        sessions: int,
        contract_epoch: int,
        policy_version: str,
        contract_digest: str,
        canonical_runtime_digest: str,
        durable_journal_path: str | Path | None = None,
    ) -> None:
        initial_states = [
            FeedbackTransactionState(
                session_id=sid,
                contract_epoch=contract_epoch,
                policy_version=policy_version,
                contract_digest=contract_digest,
                canonical_runtime_digest=canonical_runtime_digest,
            )
            for sid in range(sessions)
        ]
        self._journal = (
            DurableCommitJournal(durable_journal_path, initial_states)
            if durable_journal_path is not None else None
        )
        self._states = (
            self._journal.states() if self._journal is not None
            else initial_states
        )
        self._locks = [threading.Lock() for _ in range(sessions)]
        self._pending_versions: list[set[int]] = [set() for _ in range(sessions)]
        self._next_versions = [state.speculative_version + 1 for state in self._states]
        self._events: list[dict[str, Any]] = (
            self._journal.events() if self._journal is not None else []
        )
        self._events_lock = threading.Lock()

    @staticmethod
    def _request_digest(payload: dict[str, Any]) -> str:
        encoded = json.dumps(
            payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False
        ).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()

    def state(self, session_id: int) -> FeedbackTransactionState:
        with self._locks[session_id]:
            return self._states[session_id]

    def register_speculative(
        self, session_id: int, *, window_index: int, ready_time: float
    ) -> int:
        with self._locks[session_id]:
            version = self._next_versions[session_id]
            self._next_versions[session_id] += 1
            self._pending_versions[session_id].add(version)
        self._record({
            "event": "speculative-registered",
            "session_id": session_id,
            "revision_version": version,
            "window_index": window_index,
            "ready_time": ready_time,
            "wall_timestamp": time.time(),
        })
        return version

    def commit_segment(
        self,
        *,
        session_id: int,
        audio_start_sample: int,
        audio_end_sample: int,
        audio: bytes | memoryview,
        prompt_tokens: Sequence[int],
        display_tokens: Sequence[int],
        feedback_state_tokens: Sequence[int],
        authority_started: float,
        authority_finished: float,
        virtual_ready_time: float | None = None,
        virtual_commit_time: float | None = None,
    ) -> dict[str, Any]:
        certified_at = time.perf_counter()
        with self._locks[session_id]:
            state = self._states[session_id]
            segment_id = f"{session_id}:{audio_start_sample}:{audio_end_sample}"
            request_sha256 = self._request_digest({
                "kind": "canonical-segment",
                "session_id": session_id,
                "segment_id": segment_id,
                "audio_start_sample": audio_start_sample,
                "audio_end_sample": audio_end_sample,
                "audio_sha256": digest_bytes(audio),
                "prompt_sha256": digest_tokens(prompt_tokens),
                "display_sha256": digest_tokens(display_tokens),
                "feedback_state_sha256": digest_tokens(feedback_state_tokens),
                "contract_digest": state.contract_digest,
                "policy_version": state.policy_version,
                "canonical_runtime_digest": state.canonical_runtime_digest,
            })
            if self._journal is not None:
                replay = self._journal.lookup_commit(
                    session_id, segment_id, request_sha256
                )
                if replay is not None:
                    return replay
            if tuple(int(v) for v in prompt_tokens) != state.prompt_tokens:
                raise RuntimeError("online prompt/state mismatch")
            job = CanonicalSegmentJob(
                session_id=session_id,
                contract_epoch=state.contract_epoch,
                policy_version=state.policy_version,
                parent_checkpoint_id=state.checkpoint_id,
                audio_start_window=audio_start_sample,
                audio_end_window=audio_end_sample,
                segment_id=segment_id,
                prompt_digest=digest_tokens(state.prompt_tokens),
                contract_digest=state.contract_digest,
                canonical_runtime_digest=state.canonical_runtime_digest,
                audio_sha256=digest_bytes(audio),
            )
            certificate = build_dual_axis_certificate(
                job=job,
                audio=audio,
                display_tokens=display_tokens,
                feedback_state_tokens=feedback_state_tokens,
                canonical_runtime_digest=state.canonical_runtime_digest,
            )
            descendants = tuple(sorted(self._pending_versions[session_id]))
            result = commit_canonical_segment(
                state,
                job,
                certificate=certificate,
                display_tokens=display_tokens,
                segment_tokens=display_tokens,
                next_prompt_tokens=feedback_state_tokens,
                descendant_versions=descendants,
            )
            if not result.accepted:
                raise RuntimeError(f"online commit rejected: {result.reason}")
            event = {
                "event": "canonical-segment-committed",
                "session_id": session_id,
                "segment_id": job.segment_id,
                "parent_checkpoint_id": job.parent_checkpoint_id,
                "checkpoint_id": result.state.checkpoint_id,
                "audio_start_sample": audio_start_sample,
                "audio_end_sample": audio_end_sample,
                "authority_started_perf": authority_started,
                "authority_finished_perf": authority_finished,
                "certified_perf": certified_at,
                "committed_perf": None,
                "actual_commit_latency_seconds": None,
                "virtual_ready_time": virtual_ready_time,
                "virtual_commit_time": virtual_commit_time,
                "invalidated_speculative_versions": list(
                    result.invalidated_speculative_versions
                ),
                "certificate_consumed": True,
                "certificate": asdict(certificate),
            }
            if self._journal is not None:
                journal_sequence, fsync_seconds = self._journal.commit_transition(
                    session_id=session_id,
                    transaction_id=segment_id,
                    request_sha256=request_sha256,
                    parent_state=state,
                    next_state=result.state,
                    event=event,
                )
            self._states[session_id] = result.state
            self._pending_versions[session_id].difference_update(
                result.invalidated_speculative_versions
            )
            committed_at = time.perf_counter()
        event["committed_perf"] = committed_at
        event["actual_commit_latency_seconds"] = committed_at - authority_started
        if self._journal is not None:
            event["durable_journal_sequence"] = journal_sequence
            event["journal_fsync_seconds"] = fsync_seconds
        self._record(event)
        return event

    def assert_complete(self, audio_sizes: Sequence[int]) -> None:
        for sid, expected in enumerate(audio_sizes):
            state = self.state(sid)
            if state.audio_frontier_window != int(expected):
                raise RuntimeError(
                    f"session {sid} frontier {state.audio_frontier_window} "
                    f"!= {expected}"
                )

    def close_speculative_descendants(self, session_id: int) -> tuple[int, ...]:
        """Invalidate proposer descendants that outlived the terminal commit."""

        with self._locks[session_id]:
            stale = tuple(sorted(self._pending_versions[session_id]))
            self._pending_versions[session_id].clear()
            if stale:
                self._states[session_id] = replace(
                    self._states[session_id],
                    speculative_version=max(
                        self._states[session_id].speculative_version, *stale
                    ),
                )
        if stale:
            self._record({
                "event": "terminal-speculation-invalidated",
                "session_id": session_id,
                "invalidated_speculative_versions": list(stale),
                "wall_timestamp": time.time(),
            })
        return stale

    def commit_terminal_fallback(
        self,
        *,
        session_id: int,
        final_audio_frontier: int,
        audio: bytes,
        replacement_segments: Sequence[Sequence[int]],
        next_prompt_tokens: Sequence[int],
        fallback_id: str,
        authority_started: float,
    ) -> dict[str, Any]:
        with self._locks[session_id]:
            state = self._states[session_id]
            request_sha256 = self._request_digest({
                "kind": "terminal-fallback",
                "session_id": session_id,
                "fallback_id": fallback_id,
                "final_audio_frontier": int(final_audio_frontier),
                "audio_sha256": digest_bytes(audio),
                "replacement_segments_sha256": digest_token_segments(
                    replacement_segments
                ),
                "feedback_state_sha256": digest_tokens(next_prompt_tokens),
                "contract_digest": state.contract_digest,
                "policy_version": state.policy_version,
                "canonical_runtime_digest": state.canonical_runtime_digest,
            })
            if self._journal is not None:
                replay = self._journal.lookup_commit(
                    session_id, fallback_id, request_sha256
                )
                if replay is not None:
                    return replay
            descendants = tuple(sorted(self._pending_versions[session_id]))
            certificate = build_terminal_fallback_certificate(
                state=state,
                fallback_id=fallback_id,
                audio=audio,
                replacement_segments=replacement_segments,
                feedback_state_tokens=next_prompt_tokens,
            )
            result = commit_session_fallback(
                state,
                expected_contract_epoch=state.contract_epoch,
                expected_policy_version=state.policy_version,
                final_audio_frontier=final_audio_frontier,
                replacement_segments=replacement_segments,
                next_prompt_tokens=next_prompt_tokens,
                fallback_id=fallback_id,
                certificate=certificate,
                audio=audio,
                descendant_versions=descendants,
            )
            if not result.accepted:
                raise RuntimeError(f"online fallback rejected: {result.reason}")
            event = {
                "event": "terminal-fallback-committed",
                "session_id": session_id,
                "fallback_id": fallback_id,
                "committed_perf": None,
                "actual_commit_latency_seconds": None,
                "invalidated_speculative_versions": list(
                    result.invalidated_speculative_versions
                ),
                "certificate_consumed": True,
                "certificate": asdict(certificate),
            }
            if self._journal is not None:
                journal_sequence, fsync_seconds = self._journal.commit_transition(
                    session_id=session_id,
                    transaction_id=fallback_id,
                    request_sha256=request_sha256,
                    parent_state=state,
                    next_state=result.state,
                    event=event,
                )
            self._states[session_id] = result.state
            self._pending_versions[session_id].difference_update(
                result.invalidated_speculative_versions
            )
            committed_at = time.perf_counter()
        event["committed_perf"] = committed_at
        event["actual_commit_latency_seconds"] = committed_at - authority_started
        if self._journal is not None:
            event["durable_journal_sequence"] = journal_sequence
            event["journal_fsync_seconds"] = fsync_seconds
        self._record(event)
        return event

    def events(self) -> list[dict[str, Any]]:
        with self._events_lock:
            return list(self._events)

    def snapshot(self) -> dict[str, Any]:
        return {
            "states": [asdict(self.state(sid)) for sid in range(len(self._states))],
            "events": self.events(),
        }

    def _record(self, event: dict[str, Any]) -> None:
        with self._events_lock:
            self._events.append(event)

    def close(self) -> None:
        """Release the optional single-owner journal lock."""
        if self._journal is not None:
            self._journal.close()

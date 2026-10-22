"""Checksummed, append-only coordinator journal for process-restart recovery.

The journal is single-owner. A record becomes committed only after the full
frame has been appended and fsync has returned. Session state and the
idempotency key are in the same frame, so recovery cannot observe one without
the other.
"""

from __future__ import annotations

from dataclasses import asdict, replace
import hashlib
import json
import os
from pathlib import Path
import struct
import threading
import time
from typing import Any, Sequence

from .dgft import FeedbackTransactionState
from .dgft import digest_token_segments, digest_tokens


_HEADER = struct.Struct(">I")
_DIGEST_BYTES = 32
_MAX_RECORD_BYTES = 32 * 1024 * 1024
_SCHEMA_VERSION = 1


class JournalError(RuntimeError):
    """The journal cannot safely accept or restore a coordinator state."""


class JournalConflictError(JournalError):
    """A transaction ID was reused with different content or ancestry."""


class DurableCommitJournal:
    """Single-writer checksummed write-ahead log for session state commits."""

    def __init__(
        self,
        path: str | os.PathLike[str],
        initial_states: Sequence[FeedbackTransactionState],
    ) -> None:
        if not initial_states:
            raise ValueError("at least one initial session state is required")
        self.path = Path(path).expanduser().resolve()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock_path = self.path.with_name(self.path.name + ".lock")
        self._mutex = threading.RLock()
        self._poisoned = False
        self.timing_hook = None
        self._closed = False
        self.truncated_tail_bytes = 0
        self._states: dict[int, FeedbackTransactionState] = {}
        self._state_hashes: dict[int, str] = {}
        self._commits: dict[tuple[int, str], dict[str, Any]] = {}
        self._events: list[dict[str, Any]] = []
        self._next_sequence = 0
        self._last_digest = ""
        self._initial = {state.session_id: state for state in initial_states}
        if len(self._initial) != len(initial_states):
            raise ValueError("session IDs must be unique")

        self._lock_fd = self._acquire_lock()
        self._fd: int | None = None
        try:
            file_existed = self.path.exists()
            self._fd = os.open(
                self.path,
                os.O_CREAT | os.O_RDWR | os.O_APPEND | getattr(os, "O_BINARY", 0),
                0o600,
            )
            if not file_existed:
                self._sync_parent_directory()
            self._scan_and_recover_tail()
            if not self._states:
                self._append_record({
                    "kind": "genesis",
                    "schema_version": _SCHEMA_VERSION,
                    "sequence": 0,
                    "previous_sha256": "",
                    "states": {
                        str(sid): self._state_to_json(state)
                        for sid, state in sorted(self._initial.items())
                    },
                    "state_hashes": {
                        str(sid): self._initial_state_hash(state)
                        for sid, state in sorted(self._initial.items())
                    },
                })
            else:
                self._validate_initial_contract()
                # A new process incarnation fences work that was registered
                # by the previous coordinator but never committed.
                self._append_restart_epoch()
        except BaseException:
            self.close()
            raise

    @staticmethod
    def _state_to_json(state: FeedbackTransactionState) -> dict[str, Any]:
        return asdict(state)

    @staticmethod
    def _state_from_json(value: dict[str, Any]) -> FeedbackTransactionState:
        try:
            return FeedbackTransactionState(
                session_id=int(value["session_id"]),
                contract_epoch=int(value["contract_epoch"]),
                policy_version=str(value["policy_version"]),
                contract_digest=str(value.get("contract_digest", "")),
                canonical_runtime_digest=str(
                    value.get("canonical_runtime_digest", "")
                ),
                checkpoint_id=int(value.get("checkpoint_id", 0)),
                audio_frontier_window=int(
                    value.get("audio_frontier_window", 0)
                ),
                prompt_tokens=tuple(int(x) for x in value.get("prompt_tokens", [])),
                stable_token_segments=tuple(
                    tuple(int(x) for x in segment)
                    for segment in value.get("stable_token_segments", [])
                ),
                committed_segment_ids=tuple(
                    str(x) for x in value.get("committed_segment_ids", [])
                ),
                checkpoint_audio_frontiers=tuple(
                    int(x) for x in value.get(
                        "checkpoint_audio_frontiers", [0]
                    )
                ),
                speculative_version=int(value.get("speculative_version", 0)),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise JournalError(f"invalid state payload: {exc}") from exc

    @staticmethod
    def _json_digest(value: Any) -> str:
        payload = json.dumps(
            value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
        ).encode("utf-8")
        return hashlib.sha256(payload).hexdigest()

    @classmethod
    def _initial_state_hash(cls, state: FeedbackTransactionState) -> str:
        return cls._json_digest({"genesis_state": cls._state_to_json(state)})

    @classmethod
    def _transition_state_hash(cls, parent_hash: str, delta: dict[str, Any]) -> str:
        return cls._json_digest({"parent": parent_hash, "delta": delta})

    @classmethod
    def _restart_state_hash(cls, parent_hash: str, next_epoch: int) -> str:
        return cls._json_digest({
            "parent": parent_hash,
            "transition": "restart_epoch",
            "contract_epoch": next_epoch,
        })

    def _acquire_lock(self) -> int:
        fd = os.open(
            self._lock_path,
            os.O_CREAT | os.O_RDWR | getattr(os, "O_BINARY", 0),
            0o600,
        )
        try:
            if os.name == "nt":
                import msvcrt

                if os.fstat(fd).st_size == 0:
                    os.write(fd, b"\0")
                    os.fsync(fd)
                os.lseek(fd, 0, os.SEEK_SET)
                try:
                    msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
                except OSError as exc:
                    raise JournalError(
                        f"journal already has an active owner: {self.path}"
                    ) from exc
            else:
                import fcntl

                try:
                    fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                except OSError as exc:
                    raise JournalError(
                        f"journal already has an active owner: {self.path}"
                    ) from exc
            return fd
        except BaseException:
            os.close(fd)
            raise

    def _release_lock(self) -> None:
        if getattr(self, "_lock_fd", None) is None:
            return
        fd = self._lock_fd
        self._lock_fd = None  # type: ignore[assignment]
        try:
            if os.name == "nt":
                import msvcrt

                os.lseek(fd, 0, os.SEEK_SET)
                msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)
            else:
                import fcntl

                fcntl.flock(fd, fcntl.LOCK_UN)
        finally:
            os.close(fd)

    def _sync_parent_directory(self) -> None:
        if os.name == "nt":
            return
        fd = os.open(self.path.parent, os.O_RDONLY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)

    def _scan_and_recover_tail(self) -> None:
        assert self._fd is not None
        data = self.path.read_bytes()
        offset = 0
        expected_sequence = 0
        previous_digest = ""
        while offset < len(data):
            remaining = len(data) - offset
            if remaining < _HEADER.size:
                break
            (payload_size,) = _HEADER.unpack_from(data, offset)
            if payload_size <= 0 or payload_size > _MAX_RECORD_BYTES:
                raise JournalError(
                    f"invalid frame length {payload_size} at offset {offset}"
                )
            frame_end = offset + _HEADER.size + payload_size + _DIGEST_BYTES
            if frame_end > len(data):
                break
            payload_start = offset + _HEADER.size
            payload_end = payload_start + payload_size
            payload = data[payload_start:payload_end]
            stored_digest = data[payload_end:frame_end]
            actual_digest = hashlib.sha256(payload).digest()
            if stored_digest != actual_digest:
                raise JournalError(
                    f"checksum mismatch in complete frame at offset {offset}; "
                    "refusing to skip committed/corrupt data"
                )
            try:
                record = json.loads(payload)
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise JournalError(
                    f"invalid complete record at offset {offset}"
                ) from exc
            if int(record.get("schema_version", -1)) != _SCHEMA_VERSION:
                raise JournalError(
                    f"unsupported journal schema at offset {offset}"
                )
            if int(record.get("sequence", -1)) != expected_sequence:
                raise JournalError(
                    f"journal sequence mismatch at offset {offset}"
                )
            if str(record.get("previous_sha256", "")) != previous_digest:
                raise JournalError(
                    f"journal hash-chain mismatch at offset {offset}"
                )
            self._apply_record(record, recovering=True)
            previous_digest = actual_digest.hex()
            self._last_digest = previous_digest
            expected_sequence += 1
            offset = frame_end

        if offset != len(data):
            self.truncated_tail_bytes = len(data) - offset
            os.ftruncate(self._fd, offset)
            os.fsync(self._fd)
        self._next_sequence = expected_sequence

    def _append_record(self, record: dict[str, Any]) -> tuple[int, float]:
        return self._append_records([record])[0]

    def _append_records(self, records: Sequence[dict[str, Any]]) -> list[tuple[int, float]]:
        """Sync a bounded set of complete frames once, then apply each transition.

        Recovery may expose a valid prefix of an unacknowledged group. This is
        per-transition durability, not an all-or-nothing multi-session transaction.
        """
        self._ensure_healthy()
        assert self._fd is not None
        if not records or len(records) > 256:
            raise JournalError("journal group must contain 1 to 256 transitions")
        prepared, frames, digests = [], [], []
        previous = self._last_digest
        for index, source in enumerate(records):
            record = dict(source)
            record["sequence"] = self._next_sequence + index
            record["previous_sha256"] = previous
            payload = json.dumps(
                record, sort_keys=True, separators=(",", ":"), ensure_ascii=False
            ).encode("utf-8")
            if len(payload) > _MAX_RECORD_BYTES:
                raise JournalError("journal record exceeds maximum frame size")
            digest = hashlib.sha256(payload).digest()
            frames.append(_HEADER.pack(len(payload)) + payload + digest)
            digests.append(digest)
            prepared.append(record)
            previous = digest.hex()
        started = time.perf_counter()
        try:
            self._write_frame(b"".join(frames))
        except BaseException:
            # The write outcome may be uncertain; do not accept more commits
            # until a fresh process has scanned and recovered the WAL tail.
            self._poisoned = True
            raise
        elapsed = time.perf_counter() - started
        try:
            for record in prepared:
                self._apply_record(record, recovering=False)
        except BaseException:
            # The durable bytes now exist. Force restart/replay instead of
            # continuing with memory and the journal at different positions.
            self._poisoned = True
            raise
        self._last_digest = digests[-1].hex()
        self._next_sequence += len(prepared)
        return [(int(record["sequence"]), elapsed) for record in prepared]

    def _write_frame(self, frame: bytes) -> None:
        """Append one full frame and force it before returning to the caller."""
        assert self._fd is not None
        write_started=time.perf_counter() if self.timing_hook is not None else None
        remaining = memoryview(frame)
        while remaining:
            written = os.write(self._fd, remaining)
            if written <= 0:
                raise OSError("short journal write")
            remaining = remaining[written:]
        sync_started=time.perf_counter() if self.timing_hook is not None else None
        os.fsync(self._fd)
        finished=time.perf_counter() if self.timing_hook is not None else None
        if self.timing_hook is not None:
            self.timing_hook('write',write_started,sync_started)
            self.timing_hook('fsync',sync_started,finished)

    def _apply_record(self, record: dict[str, Any], *, recovering: bool) -> None:
        kind = record.get("kind")
        if kind == "genesis":
            if self._states or int(record.get("sequence", -1)) != 0:
                raise JournalError("genesis must be the first journal record")
            states = {
                int(sid): self._state_from_json(value)
                for sid, value in record["states"].items()
            }
            if set(states) != set(self._initial):
                raise JournalError("journal session set differs from service config")
            for sid, state in states.items():
                self._assert_static_contract(sid, state)
            expected_hashes = {
                int(sid): str(value)
                for sid, value in record.get("state_hashes", {}).items()
            }
            actual_hashes = {
                sid: self._initial_state_hash(state)
                for sid, state in states.items()
            }
            if expected_hashes != actual_hashes:
                raise JournalError("genesis state hash mismatch")
            self._states = states
            self._state_hashes = actual_hashes
            return

        if not self._states:
            raise JournalError("journal data appears before genesis")

        if kind == "restart_epoch":
            parent_hashes = {
                int(sid): str(value)
                for sid, value in record["parent_state_hashes"].items()
            }
            next_hashes = {
                int(sid): str(value)
                for sid, value in record["next_state_hashes"].items()
            }
            if parent_hashes != self._state_hashes:
                raise JournalError("restart epoch parent state hash mismatch")
            if set(parent_hashes) != set(self._states) or set(next_hashes) != set(self._states):
                raise JournalError("restart epoch changed session set")
            next_epoch = int(record["next_contract_epoch"])
            states = {
                sid: replace(state, contract_epoch=next_epoch)
                for sid, state in self._states.items()
            }
            if any(next_epoch != state.contract_epoch + 1 for state in self._states.values()):
                raise JournalError("restart must advance each contract epoch by one")
            expected_hashes = {
                sid: self._restart_state_hash(parent_hashes[sid], next_epoch)
                for sid in self._states
            }
            if next_hashes != expected_hashes:
                raise JournalError("restart epoch state hash mismatch")
            self._states = states
            self._state_hashes = next_hashes
            event = record.get("event")
            if isinstance(event, dict):
                event = dict(event)
                event["durable_journal_sequence"] = int(record["sequence"])
                if recovering:
                    event["recovered_from_wal"] = True
                self._events.append(event)
            return

        if kind != "commit":
            raise JournalError(f"unknown journal record kind: {kind!r}")
        session_id = int(record["session_id"])
        current = self._states.get(session_id)
        if current is None:
            raise JournalError("commit references unknown session")
        transaction_id = str(record["transaction_id"])
        key = (session_id, transaction_id)
        if key in self._commits:
            raise JournalError("duplicate transaction ID inside the WAL")
        if int(record["parent_checkpoint_id"]) != current.checkpoint_id:
            raise JournalError("WAL commit parent does not match recovered state")
        parent_hash = str(record["parent_state_sha256"])
        if parent_hash != self._state_hashes.get(session_id):
            raise JournalError("WAL commit parent state hash mismatch")
        delta = record["state_delta"]
        next_state = self._apply_state_delta(
            current,
            transaction_id=transaction_id,
            delta=delta,
            event=record["event"],
        )
        next_hash = self._transition_state_hash(parent_hash, delta)
        if next_hash != record["next_state_sha256"]:
            raise JournalError("WAL commit state hash mismatch")
        event = dict(record["event"])
        if int(event.get("session_id", -1)) != session_id:
            raise JournalError("event and state session IDs differ")
        event["durable_journal_sequence"] = int(record["sequence"])
        if recovering:
            event["recovered_from_wal"] = True
        self._states[session_id] = next_state
        self._state_hashes[session_id] = next_hash
        self._commits[key] = {
            "request_sha256": str(record["request_sha256"]),
            "event": event,
            "sequence": int(record["sequence"]),
        }
        self._events.append(event)

    def _assert_static_contract(
        self, session_id: int, state: FeedbackTransactionState
    ) -> None:
        initial = self._initial.get(session_id)
        if initial is None or state.session_id != session_id:
            raise JournalError("state has an unexpected session ID")
        static_fields = (
            "policy_version", "contract_digest", "canonical_runtime_digest"
        )
        for name in static_fields:
            if getattr(state, name) != getattr(initial, name):
                raise JournalError(f"journal contract mismatch for {name}")
        if state.contract_epoch < initial.contract_epoch:
            raise JournalError("journal contract epoch precedes requested epoch")

    def _apply_state_delta(
        self,
        current: FeedbackTransactionState,
        *,
        transaction_id: str,
        delta: dict[str, Any],
        event: dict[str, Any],
    ) -> FeedbackTransactionState:
        kind = delta.get("kind")
        if kind == "canonical-segment":
            certificate = event.get("certificate", {})
            start = int(delta["audio_start_sample"])
            end = int(delta["audio_end_sample"])
            segment_tokens = tuple(int(x) for x in delta["segment_tokens"])
            prompt_tokens = tuple(int(x) for x in delta["next_prompt_tokens"])
            audio_sha = str(delta["audio_sha256"])
            checks = (
                event.get("event") == "canonical-segment-committed",
                int(event.get("session_id", -1)) == current.session_id,
                str(event.get("segment_id", "")) == transaction_id,
                str(certificate.get("segment_id", "")) == transaction_id,
                int(certificate.get("parent_checkpoint_id", -1)) == current.checkpoint_id,
                int(certificate.get("audio_start_window", -1)) == start,
                int(certificate.get("audio_end_window", -1)) == end,
                str(certificate.get("contract_digest", "")) == current.contract_digest,
                str(certificate.get("policy_version", "")) == current.policy_version,
                str(certificate.get("canonical_runtime_sha256", "")) == current.canonical_runtime_digest,
                str(certificate.get("prompt_sha256", "")) == digest_tokens(current.prompt_tokens),
                str(certificate.get("audio_sha256", "")) == audio_sha,
                str(certificate.get("display_sha256", "")) == digest_tokens(segment_tokens),
                str(certificate.get("feedback_state_sha256", "")) == digest_tokens(prompt_tokens),
                start == current.audio_frontier_window,
                end > start,
            )
            if not all(checks):
                raise JournalError("canonical WAL delta failed certificate/parent validation")
            next_speculative = int(delta["speculative_version"])
            invalidated = tuple(int(x) for x in delta["invalidated_speculative_versions"])
            if next_speculative < max((current.speculative_version, *invalidated)):
                raise JournalError("canonical WAL delta regressed speculative version")
            return replace(
                current,
                checkpoint_id=current.checkpoint_id + 1,
                audio_frontier_window=end,
                prompt_tokens=prompt_tokens,
                stable_token_segments=(
                    *current.stable_token_segments, segment_tokens
                ),
                committed_segment_ids=(
                    *current.committed_segment_ids, transaction_id
                ),
                checkpoint_audio_frontiers=(
                    *current.checkpoint_audio_frontiers, end
                ),
                speculative_version=next_speculative,
            )

        if kind == "terminal-fallback":
            certificate = event.get("certificate", {})
            frontier = int(delta["final_audio_frontier"])
            replacements = tuple(
                tuple(int(x) for x in segment)
                for segment in delta["replacement_segments"]
            )
            prompt_tokens = tuple(int(x) for x in delta["next_prompt_tokens"])
            audio_sha = str(delta["audio_sha256"])
            checks = (
                event.get("event") == "terminal-fallback-committed",
                int(event.get("session_id", -1)) == current.session_id,
                str(event.get("fallback_id", "")) == transaction_id,
                str(certificate.get("fallback_id", "")) == transaction_id,
                int(certificate.get("parent_checkpoint_id", -1)) == current.checkpoint_id,
                str(certificate.get("contract_digest", "")) == current.contract_digest,
                str(certificate.get("policy_version", "")) == current.policy_version,
                str(certificate.get("canonical_runtime_sha256", "")) == current.canonical_runtime_digest,
                str(certificate.get("audio_sha256", "")) == audio_sha,
                str(certificate.get("replacement_segments_sha256", "")) == digest_token_segments(replacements),
                str(certificate.get("feedback_state_sha256", "")) == digest_tokens(prompt_tokens),
                frontier >= current.audio_frontier_window,
                transaction_id not in current.committed_segment_ids,
            )
            if not all(checks):
                raise JournalError("terminal WAL delta failed certificate/parent validation")
            next_speculative = int(delta["speculative_version"])
            invalidated = tuple(int(x) for x in delta["invalidated_speculative_versions"])
            if next_speculative < max((current.speculative_version, *invalidated)):
                raise JournalError("terminal WAL delta regressed speculative version")
            return replace(
                current,
                checkpoint_id=current.checkpoint_id + 1,
                audio_frontier_window=frontier,
                prompt_tokens=prompt_tokens,
                stable_token_segments=replacements,
                committed_segment_ids=(
                    *current.committed_segment_ids, transaction_id
                ),
                checkpoint_audio_frontiers=(
                    *current.checkpoint_audio_frontiers, frontier
                ),
                speculative_version=next_speculative,
            )

        raise JournalError(f"unknown state delta kind: {kind!r}")

    def _validate_initial_contract(self) -> None:
        if set(self._states) != set(self._initial):
            raise JournalError("journal session set differs from service config")
        for sid, state in self._states.items():
            self._assert_static_contract(sid, state)

    def _append_restart_epoch(self) -> None:
        epochs = {state.contract_epoch for state in self._states.values()}
        if len(epochs) != 1:
            raise JournalError("sessions disagree on coordinator contract epoch")
        next_epoch = next(iter(epochs)) + 1
        parent_hashes = dict(self._state_hashes)
        next_hashes = {
            sid: self._restart_state_hash(parent_hashes[sid], next_epoch)
            for sid in self._states
        }
        event = {
            "event": "coordinator-restarted",
            "contract_epoch": next_epoch,
            "recovered_state": True,
        }
        self._append_record({
            "kind": "restart_epoch",
            "schema_version": _SCHEMA_VERSION,
            "next_contract_epoch": next_epoch,
            "parent_state_hashes": {
                str(sid): value for sid, value in sorted(parent_hashes.items())
            },
            "next_state_hashes": {
                str(sid): value for sid, value in sorted(next_hashes.items())
            },
            "event": event,
        })

    def lookup_commit(
        self, session_id: int, transaction_id: str, request_sha256: str
    ) -> dict[str, Any] | None:
        with self._mutex:
            self._ensure_healthy()
            stored = self._commits.get((int(session_id), str(transaction_id)))
            if stored is None:
                return None
            if stored["request_sha256"] != request_sha256:
                raise JournalConflictError(
                    "transaction ID was already committed with different content"
                )
            event = dict(stored["event"])
            event["idempotent_replay"] = True
            event["durable_journal_sequence"] = stored["sequence"]
            return event

    def _build_state_delta(
        self,
        *,
        parent_state: FeedbackTransactionState,
        next_state: FeedbackTransactionState,
        transaction_id: str,
        event: dict[str, Any],
    ) -> dict[str, Any]:
        if event.get("event") == "canonical-segment-committed":
            if (
                len(next_state.stable_token_segments)
                != len(parent_state.stable_token_segments) + 1
                or next_state.stable_token_segments[:-1]
                != parent_state.stable_token_segments
                or next_state.committed_segment_ids
                != (*parent_state.committed_segment_ids, transaction_id)
                or next_state.checkpoint_audio_frontiers[:-1]
                != parent_state.checkpoint_audio_frontiers
                or len(next_state.checkpoint_audio_frontiers)
                != len(parent_state.checkpoint_audio_frontiers) + 1
            ):
                raise JournalError("canonical commit is not a single forward-state delta")
            certificate = event.get("certificate", {})
            delta = {
                "kind": "canonical-segment",
                "audio_start_sample": int(event["audio_start_sample"]),
                "audio_end_sample": int(event["audio_end_sample"]),
                "audio_sha256": str(certificate["audio_sha256"]),
                "segment_tokens": list(next_state.stable_token_segments[-1]),
                "next_prompt_tokens": list(next_state.prompt_tokens),
                "invalidated_speculative_versions": list(
                    event.get("invalidated_speculative_versions", [])
                ),
                "speculative_version": next_state.speculative_version,
            }
        elif event.get("event") == "terminal-fallback-committed":
            if (
                next_state.committed_segment_ids
                != (*parent_state.committed_segment_ids, transaction_id)
                or len(next_state.checkpoint_audio_frontiers)
                != len(parent_state.checkpoint_audio_frontiers) + 1
                or next_state.checkpoint_audio_frontiers[:-1]
                != parent_state.checkpoint_audio_frontiers
            ):
                raise JournalError("terminal replacement is not a single state delta")
            certificate = event.get("certificate", {})
            delta = {
                "kind": "terminal-fallback",
                "final_audio_frontier": next_state.audio_frontier_window,
                "audio_sha256": str(certificate["audio_sha256"]),
                "replacement_segments":[
                    list(segment) for segment in next_state.stable_token_segments
                ],
                "next_prompt_tokens": list(next_state.prompt_tokens),
                "invalidated_speculative_versions": list(
                    event.get("invalidated_speculative_versions", [])
                ),
                "speculative_version": next_state.speculative_version,
            }
        else:
            raise JournalError("durable journal accepts only committed state transitions")

        derived = self._apply_state_delta(
            parent_state,
            transaction_id=transaction_id,
            delta=delta,
            event=event,
        )
        if derived != next_state:
            raise JournalError("state delta does not reconstruct coordinator result")
        return delta

    def commit_transition(
        self,
        *,
        session_id: int,
        transaction_id: str,
        request_sha256: str,
        parent_state: FeedbackTransactionState,
        next_state: FeedbackTransactionState,
        event: dict[str, Any],
    ) -> tuple[int, float]:
        with self._mutex:
            record = self._prepare_commit_record(
                session_id=session_id, transaction_id=transaction_id,
                request_sha256=request_sha256, parent_state=parent_state,
                next_state=next_state, event=event,
            )
            return self._append_record(record)

    def commit_transitions(self, transitions: Sequence[dict[str, Any]]) -> list[tuple[int, float]]:
        """Batch independent, already validated session transitions at one barrier.

        No new waiting window is introduced. Only one next transition per session
        is allowed, so all parents are checked against the current durable state.
        """
        with self._mutex:
            if not transitions or len(transitions) > 256:
                raise JournalError("journal group must contain 1 to 256 transitions")
            session_ids = [int(item["session_id"]) for item in transitions]
            if len(set(session_ids)) != len(session_ids):
                raise JournalConflictError("group contains dependent transitions from one session")
            records = [self._prepare_commit_record(**item) for item in transitions]
            return self._append_records(records)

    def _prepare_commit_record(
        self, *, session_id: int, transaction_id: str, request_sha256: str,
        parent_state: FeedbackTransactionState, next_state: FeedbackTransactionState,
        event: dict[str, Any],
    ) -> dict[str, Any]:
            self._ensure_healthy()
            existing = self.lookup_commit(
                session_id, transaction_id, request_sha256
            )
            if existing is not None:
                raise JournalConflictError(
                    "commit_transition called for an already committed ID; "
                    "coordinator must return the idempotent outcome"
                )
            current = self._states.get(int(session_id))
            if current is None:
                raise JournalError("commit references unknown session")
            if (
                current.checkpoint_id != parent_state.checkpoint_id
                or current.audio_frontier_window != parent_state.audio_frontier_window
                or current.prompt_tokens != parent_state.prompt_tokens
                or current.committed_segment_ids != parent_state.committed_segment_ids
                or current.contract_epoch != parent_state.contract_epoch
                or current.contract_digest != parent_state.contract_digest
                or current.policy_version != parent_state.policy_version
                or current.canonical_runtime_digest != parent_state.canonical_runtime_digest
            ):
                raise JournalConflictError(
                    "coordinator parent differs from durable journal state"
                )
            delta = self._build_state_delta(
                parent_state=parent_state,
                next_state=next_state,
                transaction_id=transaction_id,
                event=event,
            )
            parent_hash = self._state_hashes[int(session_id)]
            next_hash = self._transition_state_hash(parent_hash, delta)
            event_to_persist = dict(event)
            # perf_counter values belong to one process incarnation. Persist the
            # certificate/event semantics; the live caller adds timings after
            # fsync, and recovered events are explicitly marked as recovered.
            event_to_persist["committed_perf"] = None
            event_to_persist["actual_commit_latency_seconds"] = None
            return {
                "kind": "commit",
                "schema_version": _SCHEMA_VERSION,
                "session_id": int(session_id),
                "transaction_id": str(transaction_id),
                "request_sha256": str(request_sha256),
                "parent_checkpoint_id": parent_state.checkpoint_id,
                "parent_state_sha256": parent_hash,
                "state_delta": delta,
                "next_state_sha256": next_hash,
                "event": event_to_persist,
            }

    def states(self) -> list[FeedbackTransactionState]:
        with self._mutex:
            self._ensure_healthy()
            return [self._states[sid] for sid in sorted(self._states)]

    def events(self) -> list[dict[str, Any]]:
        with self._mutex:
            self._ensure_healthy()
            return [dict(event) for event in self._events]

    def _ensure_healthy(self) -> None:
        if self._closed:
            raise JournalError("journal is closed")
        if self._poisoned:
            raise JournalError("journal is poisoned after an uncertain write")

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        fd = getattr(self, "_fd", None)
        if fd is not None:
            os.close(fd)
            self._fd = None
        self._release_lock()

    def __enter__(self) -> "DurableCommitJournal":
        return self

    def __exit__(self, *_: Any) -> None:
        self.close()

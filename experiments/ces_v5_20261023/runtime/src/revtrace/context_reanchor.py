"""MVCC semantics for safe context reanchoring.

Context capsules carry canonical feedback state across a bounded audio
frontier.  The user-visible provisional transcript is intentionally outside
the authority state: installing a capsule may replace feedback lineage but
must never rewrite what has already been displayed.
"""

from __future__ import annotations

import hashlib
import json
import re
from difflib import SequenceMatcher
from dataclasses import dataclass, replace
from typing import Sequence


_WORD = re.compile(r"[A-Za-z0-9']+")


def asymmetric_context_conflict(
    provisional_token_count: int,
    replay_token_count: int,
    *,
    short_limit: int = 2,
    long_floor: int = 8,
) -> bool:
    """Flag a short acoustic boundary contradicted by a long replay suffix.

    This is a scheduling predicate only.  The conflict is resolved by a
    canonical empty-prompt cutset from the current raw-audio window; neither
    side of the disagreement is granted authority by this predicate.
    """

    if min(provisional_token_count, replay_token_count) < 0:
        raise ValueError("token counts cannot be negative")
    if short_limit < 0 or long_floor <= short_limit:
        raise ValueError("invalid asymmetric conflict limits")
    return (
        provisional_token_count <= short_limit
        and replay_token_count >= long_floor
    )


def safe_display_override_candidate(
    *,
    terminated_by_eos: bool,
    generation_steps: int,
    maximum_generation_steps: int,
    compression_ratio: float | None,
    longest_repetition_run: int,
) -> bool:
    """Reject structurally invalid provisional text from display arbitration."""

    return (
        terminated_by_eos
        and generation_steps < maximum_generation_steps
        and float(compression_ratio or 0.0) < 2.4
        and longest_repetition_run < 4
    )


def bound_feedback_prompt(
    prompt: Sequence[int],
    *,
    start_of_previous_token: int,
    maximum_content_tokens: int,
) -> tuple[int, ...]:
    """Keep a causal replay suffix without restoring rejected ancestry.

    The replay lane is derived only from raw audio.  Bounding its history is
    therefore a context checkpoint, not a copy from the unsafe proposer
    state.  Whisper's ``<|startofprev|>`` marker is preserved separately from
    the content-token budget.
    """

    if maximum_content_tokens < 0:
        raise ValueError("maximum_content_tokens cannot be negative")
    values = tuple(int(token) for token in prompt)
    if not values or maximum_content_tokens == 0:
        return ()
    content = (
        values[1:]
        if values[0] == int(start_of_previous_token)
        else values
    )
    bounded = content[-maximum_content_tokens:]
    if not bounded:
        return ()
    return (int(start_of_previous_token), *bounded)


def _token_digest(token_ids: Sequence[int]) -> str:
    return hashlib.sha256(
        json.dumps(
            [int(value) for value in token_ids], separators=(",", ":")
        ).encode("utf-8")
    ).hexdigest()


def extract_bounded_audio_delta(
    previous_text: str,
    overlapping_text: str,
    *,
    minimum_match_words: int = 4,
    prefix_slack_words: int = 2,
    tail_slack_words: int = 2,
) -> str | None:
    """Extract the new suffix from a two-window acoustic reanchor.

    The overlapping decode must contain a substantial match between its
    beginning and the tail of the already displayed previous window.  This is
    deliberately fail-closed: without that audio-frontier witness the system
    keeps the single-window result instead of guessing a textual boundary.
    """

    previous_spans = list(_WORD.finditer(previous_text))
    overlap_spans = list(_WORD.finditer(overlapping_text))
    if (
        len(previous_spans) < minimum_match_words
        or len(overlap_spans) <= minimum_match_words
    ):
        return None
    previous_words = [match.group(0).lower() for match in previous_spans]
    overlap_words = [match.group(0).lower() for match in overlap_spans]
    blocks = SequenceMatcher(
        None, previous_words, overlap_words, autojunk=False
    ).get_matching_blocks()
    candidates = [
        block for block in blocks
        if block.size >= minimum_match_words
        and block.b <= prefix_slack_words
        and len(previous_words) - (block.a + block.size)
        <= tail_slack_words
        and block.b + block.size < len(overlap_spans)
    ]
    if not candidates:
        return None
    block = max(candidates, key=lambda item: (item.size, item.b + item.size))
    boundary = overlap_spans[block.b + block.size - 1].end()
    delta = overlapping_text[boundary:].lstrip(" \t\r\n,.;:!?-")
    return delta or None


@dataclass(frozen=True)
class RecoveryVersion:
    """Independent MVCC clocks for one revision-generative session."""

    session_id: str
    contract_epoch: int
    policy_version: int
    revision_version: int
    feedback_lineage_version: int
    audio_frontier_version: int
    anchor_id: str

    def __post_init__(self) -> None:
        if not self.session_id or not self.anchor_id:
            raise ValueError("session and anchor identifiers must be non-empty")
        if min(
            self.contract_epoch,
            self.policy_version,
            self.revision_version,
            self.feedback_lineage_version,
            self.audio_frontier_version,
        ) < 0:
            raise ValueError("MVCC versions must be non-negative")


@dataclass(frozen=True)
class ContextCapsule:
    """Operation-scoped canonical feedback snapshot.

    The capsule is bound to the session, contract, policy, parent lineage and
    the exact audio frontier from which it was produced.  Its token digest is
    checked again at installation, preventing an otherwise valid header from
    authorizing modified feedback content.
    """

    capsule_id: str
    session_id: str
    contract_epoch: int
    policy_version: int
    parent_anchor_id: str
    parent_feedback_lineage_version: int
    audio_start_version: int
    audio_end_version: int
    expires_after_audio_frontier: int
    prompt_token_ids: tuple[int, ...]
    prompt_text: str
    token_sha256: str
    canonical_runtime_digest: str

    @classmethod
    def create(
        cls,
        *,
        capsule_id: str,
        parent: RecoveryVersion,
        audio_start_version: int,
        audio_end_version: int,
        expires_after_audio_frontier: int,
        prompt_token_ids: Sequence[int],
        prompt_text: str,
        canonical_runtime_digest: str,
    ) -> "ContextCapsule":
        tokens = tuple(int(value) for value in prompt_token_ids)
        return cls(
            capsule_id=capsule_id,
            session_id=parent.session_id,
            contract_epoch=parent.contract_epoch,
            policy_version=parent.policy_version,
            parent_anchor_id=parent.anchor_id,
            parent_feedback_lineage_version=(
                parent.feedback_lineage_version
            ),
            audio_start_version=audio_start_version,
            audio_end_version=audio_end_version,
            expires_after_audio_frontier=expires_after_audio_frontier,
            prompt_token_ids=tokens,
            prompt_text=prompt_text,
            token_sha256=_token_digest(tokens),
            canonical_runtime_digest=canonical_runtime_digest,
        )


@dataclass(frozen=True)
class RecoveryState:
    version: RecoveryVersion
    prompt_token_ids: tuple[int, ...]
    prompt_text: str
    provisional_display: str


class CapsuleRejected(ValueError):
    """Raised when a capsule cannot safely acquire feedback authority."""


def advance_audio_frontier(
    state: RecoveryState, *, new_frontier: int
) -> RecoveryState:
    """Advance available audio without changing feedback authority."""

    if new_frontier <= state.version.audio_frontier_version:
        raise ValueError("audio frontier must advance monotonically")
    return replace(
        state,
        version=replace(
            state.version,
            audio_frontier_version=new_frontier,
        ),
    )


def publish_provisional(
    state: RecoveryState, provisional_display: str
) -> RecoveryState:
    """Update display-only state without changing any authority version."""

    return replace(state, provisional_display=provisional_display)


def install_context_capsule(
    state: RecoveryState,
    capsule: ContextCapsule,
) -> RecoveryState:
    """Atomically replace feedback lineage with a verified context capsule.

    Reinstalling the current capsule is an idempotent no-op.  Every other
    replay, cross-session use, stale lineage, future-audio capsule, expired
    capsule, or modified token payload fails closed.
    """

    current = state.version
    if capsule.capsule_id == current.anchor_id:
        if (
            capsule.prompt_token_ids == state.prompt_token_ids
            and capsule.prompt_text == state.prompt_text
            and capsule.token_sha256 == _token_digest(
                capsule.prompt_token_ids
            )
        ):
            return state
        raise CapsuleRejected("capsule-id replay carries different content")
    if capsule.session_id != current.session_id:
        raise CapsuleRejected("cross-session capsule")
    if capsule.contract_epoch != current.contract_epoch:
        raise CapsuleRejected("contract epoch mismatch")
    if capsule.policy_version != current.policy_version:
        raise CapsuleRejected("policy version mismatch")
    if capsule.parent_anchor_id != current.anchor_id:
        raise CapsuleRejected("stale or foreign parent anchor")
    if (
        capsule.parent_feedback_lineage_version
        != current.feedback_lineage_version
    ):
        raise CapsuleRejected("stale feedback lineage")
    if capsule.audio_start_version < 0:
        raise CapsuleRejected("invalid audio start")
    if capsule.audio_end_version < capsule.audio_start_version:
        raise CapsuleRejected("invalid audio range")
    if capsule.audio_end_version > current.audio_frontier_version:
        raise CapsuleRejected("capsule depends on unavailable future audio")
    if current.audio_frontier_version > capsule.expires_after_audio_frontier:
        raise CapsuleRejected("capsule freshness window expired")
    if not capsule.canonical_runtime_digest:
        raise CapsuleRejected("canonical runtime provenance is missing")
    if capsule.token_sha256 != _token_digest(capsule.prompt_token_ids):
        raise CapsuleRejected("capsule token digest mismatch")

    return RecoveryState(
        version=RecoveryVersion(
            session_id=current.session_id,
            contract_epoch=current.contract_epoch,
            policy_version=current.policy_version,
            revision_version=current.revision_version + 1,
            feedback_lineage_version=(
                current.feedback_lineage_version + 1
            ),
            audio_frontier_version=current.audio_frontier_version,
            anchor_id=capsule.capsule_id,
        ),
        prompt_token_ids=capsule.prompt_token_ids,
        prompt_text=capsule.prompt_text,
        provisional_display=state.provisional_display,
    )

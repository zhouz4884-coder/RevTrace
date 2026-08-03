"""Dual-granularity feedback-state transaction primitives.

The helpers in this module are deliberately model agnostic.  They define the
audio frontier and version checks that a canonical segment must satisfy before
it may replace a speculative revision branch.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from difflib import SequenceMatcher
from hashlib import sha256
import math
import re
from typing import Iterable, Sequence

import numpy as np


_WORD = re.compile(r"[A-Za-z0-9']+")


def digest_tokens(values: Sequence[int]) -> str:
    payload = ",".join(str(int(value)) for value in values).encode("ascii")
    return sha256(payload).hexdigest()


def digest_bytes(value: bytes) -> str:
    return sha256(value).hexdigest()


def cross_granularity_coverage_deficit(
    fine_text: str, coarse_text: str
) -> float:
    """Fraction of the fine-grained witness not covered in coarse order.

    The value is a scheduling signal, not an exactness certificate.  It is
    reference-free: both strings are model outputs over the same raw audio.
    Order-preserving ``SequenceMatcher`` coverage is directional because the
    observed R9 failure is coarse authority omitting content present in fine
    revisions.  This is not a strict longest-common-subsequence algorithm.
    """

    fine = [match.group(0).lower() for match in _WORD.finditer(fine_text)]
    coarse = [match.group(0).lower() for match in _WORD.finditer(coarse_text)]
    if not fine:
        return 0.0
    matched = sum(
        block.size
        for block in SequenceMatcher(
            None, fine, coarse, autojunk=False
        ).get_matching_blocks()
    )
    return 1.0 - matched / len(fine)


def boundary_adjusted_coverage_deficit(
    fine_segments: Sequence[str],
    coarse_segments: Sequence[str],
    index: int,
) -> tuple[float, int, int]:
    """Return residual directional loss after adjacent-boundary transport.

    Adaptive audio cuts need not assign the same words to the same segment as
    the fine-grained revision path.  A phrase that is extra in coarse segment
    ``i-1`` and missing from coarse segment ``i`` is boundary transport, not a
    semantic omission.  We therefore compare the current segment alone and in
    a two-segment neighborhood, retaining the smallest *absolute* unmatched
    fine-token count.  A real omission remains unmatched after concatenation;
    a boundary displacement cancels.  The denominator stays local so a long
    neighbor cannot dilute a true current-segment omission.

    Returns ``(adjusted_deficit, raw_missing_tokens, residual_missing_tokens)``.
    This is still a reference-free scheduling witness, not an exactness proof.
    """

    if len(fine_segments) != len(coarse_segments):
        raise ValueError("fine and coarse segment lists must have equal length")
    if not 0 <= index < len(fine_segments):
        raise IndexError("segment index out of range")

    def tokens(value: str) -> list[str]:
        return [match.group(0).lower() for match in _WORD.finditer(value)]

    def missing(fine: Sequence[str], coarse: Sequence[str]) -> int:
        matched = sum(
            block.size for block in SequenceMatcher(
                None, list(fine), list(coarse), autojunk=False
            ).get_matching_blocks()
        )
        return max(0, len(fine) - matched)

    local_fine = tokens(fine_segments[index])
    local_coarse = tokens(coarse_segments[index])
    if not local_fine:
        return 0.0, 0, 0
    raw_missing = missing(local_fine, local_coarse)
    residual = raw_missing
    for neighbor in (index - 1, index + 1):
        if not 0 <= neighbor < len(fine_segments):
            continue
        low, high = sorted((index, neighbor))
        pair_fine = tokens(" ".join(fine_segments[low:high + 1]))
        pair_coarse = tokens(" ".join(coarse_segments[low:high + 1]))
        residual = min(residual, missing(pair_fine, pair_coarse))
    return residual / len(local_fine), raw_missing, residual


def repeated_ngram_fraction(text: str, *, n: int = 4) -> float:
    """Fraction of word n-grams attributable to repeated occurrences.

    This detects self-degenerate salvage such as a phrase loop.  It is a local
    structural signal and must not be interpreted as transcript correctness.
    """

    if n <= 0:
        raise ValueError("n must be positive")
    words = [match.group(0).lower() for match in _WORD.finditer(text)]
    grams = [tuple(words[index:index + n]) for index in range(len(words) - n + 1)]
    if not grams:
        return 0.0
    return 1.0 - len(set(grams)) / len(grams)


@dataclass(frozen=True)
class CoverageConflict:
    deficit: float
    threshold: float
    fallback_required: bool


@dataclass(frozen=True)
class AsymmetricOmissionConflict:
    forward_deficit: float
    reverse_deficit: float
    forward_threshold: float
    reverse_ceiling: float
    fallback_required: bool


def classify_coverage_conflict(
    fine_text: str,
    coarse_text: str,
    *,
    threshold: float,
) -> CoverageConflict:
    if not 0.0 <= threshold <= 1.0:
        raise ValueError("coverage threshold must be within [0, 1]")
    deficit = cross_granularity_coverage_deficit(fine_text, coarse_text)
    return CoverageConflict(
        deficit=deficit,
        threshold=threshold,
        fallback_required=deficit >= threshold,
    )


def classify_asymmetric_omission_conflict(
    fine_text: str,
    candidate_text: str,
    *,
    forward_threshold: float,
    reverse_ceiling: float,
) -> AsymmetricOmissionConflict:
    """Detect unilateral candidate omission after checkpoint replay.

    A large deficit in both directions is mutual disagreement and does not by
    itself identify which path lost evidence.  Escalation is reserved for the
    asymmetric case where the fine witness contains substantial ordered
    content absent from the candidate, while the reverse deficit stays small.
    This remains a reference-free scheduling signal rather than a certificate.
    """

    if not 0.0 <= forward_threshold <= 1.0:
        raise ValueError("forward threshold must be within [0, 1]")
    if not 0.0 <= reverse_ceiling <= 1.0:
        raise ValueError("reverse ceiling must be within [0, 1]")
    forward = cross_granularity_coverage_deficit(fine_text, candidate_text)
    reverse = cross_granularity_coverage_deficit(candidate_text, fine_text)
    return AsymmetricOmissionConflict(
        forward_deficit=forward,
        reverse_deficit=reverse,
        forward_threshold=forward_threshold,
        reverse_ceiling=reverse_ceiling,
        fallback_required=(
            forward >= forward_threshold and reverse <= reverse_ceiling
        ),
    )


def fixed_segment_plan(
    *, windows: int, windows_per_segment: int
) -> tuple[tuple[int, int], ...]:
    """Return a gap-free half-open plan over revision windows."""

    if windows <= 0 or windows_per_segment <= 0:
        raise ValueError("window counts must be positive")
    return tuple(
        (start, min(windows, start + windows_per_segment))
        for start in range(0, windows, windows_per_segment)
    )


def balanced_replay_plan(
    *, start_sample: int, end_sample: int, maximum_samples: int
) -> tuple[tuple[int, int], ...]:
    """Partition a replay interval without a pathological short tail."""

    if not 0 <= start_sample < end_sample:
        raise ValueError("replay interval must be positive")
    if maximum_samples <= 0:
        raise ValueError("maximum samples must be positive")
    count = max(1, math.ceil((end_sample - start_sample) / maximum_samples))
    boundaries = [
        start_sample + ((end_sample - start_sample) * index) // count
        for index in range(count + 1)
    ]
    return tuple(zip(boundaries[:-1], boundaries[1:]))


def adaptive_audio_plan(
    audio: np.ndarray,
    *,
    sample_rate: int,
    minimum_seconds: float,
    maximum_seconds: float,
    frame_seconds: float = 0.05,
) -> tuple[tuple[int, int], ...]:
    """Select gap-free raw-audio energy minima without transcript feedback."""

    if not 0 < minimum_seconds < maximum_seconds <= 30.0:
        raise ValueError("adaptive bounds must satisfy 0 < min < max <= 30")
    frame = max(1, int(frame_seconds * sample_rate))
    total = int(audio.size)
    minimum = int(minimum_seconds * sample_rate)
    maximum = int(maximum_seconds * sample_rate)
    start = 0
    plan: list[tuple[int, int]] = []
    values = np.asarray(audio, dtype=np.float64)
    squared = values * values
    prefix = np.concatenate(([0.0], np.cumsum(squared)))
    while total - start > maximum:
        low = start + minimum
        # Reserve a full minimum-length tail.  Without this constraint a
        # near-maximum cut can create a sub-second final fragment.
        high = min(start + maximum, total - minimum)
        if high < low:
            plan.append((start, total))
            return tuple(plan)
        candidates = np.arange(low, high + 1, frame, dtype=np.int64)
        half = frame
        left = np.maximum(start, candidates - half)
        right = np.minimum(total, candidates + half)
        energy = (prefix[right] - prefix[left]) / np.maximum(1, right - left)
        minimum_energy = float(np.min(energy))
        tolerance = max(1e-12, minimum_energy * 1.05)
        eligible = candidates[energy <= tolerance]
        end = int(eligible[-1])
        plan.append((start, end))
        start = end
    plan.append((start, total))
    return tuple(plan)


@dataclass(frozen=True)
class CanonicalSegmentJob:
    session_id: int
    contract_epoch: int
    policy_version: str
    parent_checkpoint_id: int
    audio_start_window: int
    audio_end_window: int
    segment_id: str
    prompt_digest: str
    contract_digest: str = ""
    canonical_runtime_digest: str = ""
    audio_sha256: str = ""


@dataclass(frozen=True)
class FeedbackTransactionState:
    session_id: int
    contract_epoch: int
    policy_version: str
    contract_digest: str = ""
    canonical_runtime_digest: str = ""
    checkpoint_id: int = 0
    audio_frontier_window: int = 0
    prompt_tokens: tuple[int, ...] = ()
    stable_token_segments: tuple[tuple[int, ...], ...] = ()
    committed_segment_ids: tuple[str, ...] = ()
    checkpoint_audio_frontiers: tuple[int, ...] = (0,)
    speculative_version: int = 0


@dataclass(frozen=True)
class CommitResult:
    accepted: bool
    reason: str
    state: FeedbackTransactionState
    invalidated_speculative_versions: tuple[int, ...] = ()


@dataclass(frozen=True)
class DualAxisCommitCertificate:
    session_id: int
    contract_digest: str
    policy_version: str
    segment_id: str
    parent_checkpoint_id: int
    audio_start_window: int
    audio_end_window: int
    prompt_sha256: str
    audio_sha256: str
    display_sha256: str
    feedback_state_sha256: str
    canonical_runtime_sha256: str


@dataclass(frozen=True)
class TerminalFallbackCertificate:
    session_id: int
    contract_digest: str
    policy_version: str
    parent_checkpoint_id: int
    fallback_id: str
    audio_sha256: str
    replacement_segments_sha256: str
    feedback_state_sha256: str
    canonical_runtime_sha256: str


def digest_token_segments(values: Sequence[Sequence[int]]) -> str:
    return sha256("|".join(
        ",".join(str(int(value)) for value in segment)
        for segment in values
    ).encode("ascii")).hexdigest()


def build_terminal_fallback_certificate(
    *,
    state: FeedbackTransactionState,
    fallback_id: str,
    audio: bytes,
    replacement_segments: Sequence[Sequence[int]],
    feedback_state_tokens: Sequence[int],
) -> TerminalFallbackCertificate:
    return TerminalFallbackCertificate(
        session_id=state.session_id,
        contract_digest=state.contract_digest,
        policy_version=state.policy_version,
        parent_checkpoint_id=state.checkpoint_id,
        fallback_id=fallback_id,
        audio_sha256=digest_bytes(audio),
        replacement_segments_sha256=digest_token_segments(
            replacement_segments
        ),
        feedback_state_sha256=digest_tokens(feedback_state_tokens),
        canonical_runtime_sha256=state.canonical_runtime_digest,
    )


def build_dual_axis_certificate(
    *,
    job: CanonicalSegmentJob,
    audio: bytes,
    display_tokens: Sequence[int],
    feedback_state_tokens: Sequence[int],
    canonical_runtime_digest: str,
) -> DualAxisCommitCertificate:
    return DualAxisCommitCertificate(
        session_id=job.session_id,
        contract_digest=job.contract_digest,
        policy_version=job.policy_version,
        segment_id=job.segment_id,
        parent_checkpoint_id=job.parent_checkpoint_id,
        audio_start_window=job.audio_start_window,
        audio_end_window=job.audio_end_window,
        prompt_sha256=job.prompt_digest,
        audio_sha256=(job.audio_sha256 or digest_bytes(audio)),
        display_sha256=digest_tokens(display_tokens),
        feedback_state_sha256=digest_tokens(feedback_state_tokens),
        canonical_runtime_sha256=str(canonical_runtime_digest),
    )


def validate_segment_job(
    state: FeedbackTransactionState,
    job: CanonicalSegmentJob,
) -> str | None:
    """Return a fail-closed rejection reason, or ``None`` when installable."""

    checks = (
        (job.session_id == state.session_id, "cross-session"),
        (job.contract_epoch == state.contract_epoch, "stale-epoch"),
        (job.policy_version == state.policy_version, "stale-policy"),
        (job.contract_digest == state.contract_digest, "contract-digest-mismatch"),
        (
            job.canonical_runtime_digest == state.canonical_runtime_digest,
            "runtime-digest-mismatch",
        ),
        (
            job.parent_checkpoint_id == state.checkpoint_id,
            "stale-parent-checkpoint",
        ),
        (
            job.audio_start_window == state.audio_frontier_window,
            "audio-gap-or-overlap",
        ),
        (
            job.audio_end_window > job.audio_start_window,
            "empty-segment",
        ),
        (len(job.audio_sha256) == 64, "missing-audio-digest"),
        (
            job.prompt_digest == digest_tokens(state.prompt_tokens),
            "prompt-digest-mismatch",
        ),
        (
            job.segment_id not in state.committed_segment_ids,
            "duplicate-segment",
        ),
    )
    for valid, reason in checks:
        if not valid:
            return reason
    return None


def validate_dual_axis_certificate(
    state: FeedbackTransactionState,
    job: CanonicalSegmentJob,
    certificate: DualAxisCommitCertificate,
    *,
    display_tokens: Sequence[int],
    feedback_state_tokens: Sequence[int],
) -> str | None:
    """Validate that a certificate binds the exact state transition.

    Certificate validation is intentionally inside the commit primitive.  A
    caller cannot install a transition merely because it constructed a
    certificate object earlier in the pipeline.
    """

    checks = (
        (certificate.session_id == state.session_id, "certificate-session"),
        (
            certificate.contract_digest == state.contract_digest,
            "certificate-contract",
        ),
        (
            certificate.policy_version == state.policy_version,
            "certificate-policy",
        ),
        (certificate.segment_id == job.segment_id, "certificate-segment"),
        (
            certificate.parent_checkpoint_id == state.checkpoint_id,
            "certificate-parent",
        ),
        (
            certificate.audio_start_window == job.audio_start_window
            and certificate.audio_end_window == job.audio_end_window,
            "certificate-frontier",
        ),
        (
            certificate.prompt_sha256 == digest_tokens(state.prompt_tokens),
            "certificate-prompt",
        ),
        (
            certificate.audio_sha256 == job.audio_sha256,
            "certificate-audio",
        ),
        (
            certificate.display_sha256 == digest_tokens(display_tokens),
            "certificate-display",
        ),
        (
            certificate.feedback_state_sha256
            == digest_tokens(feedback_state_tokens),
            "certificate-feedback-state",
        ),
        (
            certificate.canonical_runtime_sha256
            == state.canonical_runtime_digest,
            "certificate-runtime",
        ),
    )
    for valid, reason in checks:
        if not valid:
            return reason
    return None


def commit_canonical_segment(
    state: FeedbackTransactionState,
    job: CanonicalSegmentJob,
    *,
    certificate: DualAxisCommitCertificate,
    display_tokens: Sequence[int],
    segment_tokens: Sequence[int],
    next_prompt_tokens: Sequence[int],
    descendant_versions: Iterable[int] = (),
) -> CommitResult:
    """Atomically advance prompt, transcript and audio frontier."""

    reason = validate_segment_job(state, job)
    if reason is not None:
        return CommitResult(False, reason, state)
    reason = validate_dual_axis_certificate(
        state,
        job,
        certificate,
        display_tokens=display_tokens,
        feedback_state_tokens=next_prompt_tokens,
    )
    if reason is not None:
        return CommitResult(False, reason, state)
    invalidated = tuple(
        sorted(
            int(value)
            for value in descendant_versions
            if int(value) > state.speculative_version
        )
    )
    installed = replace(
        state,
        checkpoint_id=state.checkpoint_id + 1,
        audio_frontier_window=job.audio_end_window,
        prompt_tokens=tuple(int(value) for value in next_prompt_tokens),
        stable_token_segments=(
            *state.stable_token_segments,
            tuple(int(value) for value in segment_tokens),
        ),
        committed_segment_ids=(
            *state.committed_segment_ids, job.segment_id
        ),
        checkpoint_audio_frontiers=(
            *state.checkpoint_audio_frontiers, job.audio_end_window
        ),
        speculative_version=max(
            (state.speculative_version, *invalidated)
        ),
    )
    return CommitResult(True, "committed", installed, invalidated)


def commit_session_fallback(
    state: FeedbackTransactionState,
    *,
    expected_contract_epoch: int,
    expected_policy_version: str,
    final_audio_frontier: int,
    replacement_segments: Sequence[Sequence[int]],
    next_prompt_tokens: Sequence[int],
    fallback_id: str,
    certificate: TerminalFallbackCertificate,
    audio: bytes,
    descendant_versions: Iterable[int] = (),
) -> CommitResult:
    """Atomically replace a conflicted coarse branch at terminal authority."""

    if expected_contract_epoch != state.contract_epoch:
        return CommitResult(False, "stale-epoch", state)
    if expected_policy_version != state.policy_version:
        return CommitResult(False, "stale-policy", state)
    if fallback_id in state.committed_segment_ids:
        return CommitResult(False, "duplicate-segment", state)
    if final_audio_frontier < state.audio_frontier_window:
        return CommitResult(False, "fallback-frontier-regression", state)
    certificate_checks = (
        (certificate.session_id == state.session_id, "certificate-session"),
        (
            certificate.contract_digest == state.contract_digest,
            "certificate-contract",
        ),
        (
            certificate.policy_version == state.policy_version,
            "certificate-policy",
        ),
        (
            certificate.parent_checkpoint_id == state.checkpoint_id,
            "certificate-parent",
        ),
        (certificate.fallback_id == fallback_id, "certificate-fallback"),
        (certificate.audio_sha256 == digest_bytes(audio), "certificate-audio"),
        (
            certificate.replacement_segments_sha256
            == digest_token_segments(replacement_segments),
            "certificate-replacement",
        ),
        (
            certificate.feedback_state_sha256
            == digest_tokens(next_prompt_tokens),
            "certificate-feedback-state",
        ),
        (
            certificate.canonical_runtime_sha256
            == state.canonical_runtime_digest,
            "certificate-runtime",
        ),
    )
    for valid, reason in certificate_checks:
        if not valid:
            return CommitResult(False, reason, state)
    invalidated = tuple(sorted(
        int(value) for value in descendant_versions
        if int(value) > state.speculative_version
    ))
    installed = replace(
        state,
        checkpoint_id=state.checkpoint_id + 1,
        audio_frontier_window=int(final_audio_frontier),
        prompt_tokens=tuple(int(value) for value in next_prompt_tokens),
        stable_token_segments=tuple(
            tuple(int(value) for value in segment)
            for segment in replacement_segments
        ),
        committed_segment_ids=(
            *state.committed_segment_ids, fallback_id
        ),
        checkpoint_audio_frontiers=(
            *state.checkpoint_audio_frontiers, int(final_audio_frontier)
        ),
        speculative_version=max(
            (state.speculative_version, *invalidated)
        ),
    )
    return CommitResult(True, "fallback-committed", installed, invalidated)


def commit_checkpoint_rebase(
    state: FeedbackTransactionState,
    *,
    expected_contract_epoch: int,
    expected_policy_version: str,
    rebase_checkpoint_id: int,
    audio_start_frontier: int,
    final_audio_frontier: int,
    replacement_segments: Sequence[Sequence[int]],
    next_prompt_tokens: Sequence[int],
    fallback_id: str,
    descendant_versions: Iterable[int] = (),
) -> CommitResult:
    """Invalidate a coarse suffix and atomically install canonical replay.

    Checkpoints before ``rebase_checkpoint_id`` remain authoritative.  Every
    later segment is discarded because it may descend from the conflicted
    feedback state.
    """

    if expected_contract_epoch != state.contract_epoch:
        return CommitResult(False, "stale-epoch", state)
    if expected_policy_version != state.policy_version:
        return CommitResult(False, "stale-policy", state)
    if not 0 <= rebase_checkpoint_id <= state.checkpoint_id:
        return CommitResult(False, "invalid-rebase-checkpoint", state)
    if rebase_checkpoint_id > len(state.stable_token_segments):
        return CommitResult(False, "missing-rebase-state", state)
    if rebase_checkpoint_id >= len(state.checkpoint_audio_frontiers):
        return CommitResult(False, "missing-rebase-frontier", state)
    if fallback_id in state.committed_segment_ids:
        return CommitResult(False, "duplicate-segment", state)
    if not 0 <= audio_start_frontier <= final_audio_frontier:
        return CommitResult(False, "invalid-rebase-frontier", state)
    if audio_start_frontier != state.checkpoint_audio_frontiers[
        rebase_checkpoint_id
    ]:
        return CommitResult(False, "rebase-frontier-mismatch", state)
    invalidated = tuple(sorted(
        int(value) for value in descendant_versions
        if int(value) > state.speculative_version
    ))
    installed = replace(
        state,
        checkpoint_id=rebase_checkpoint_id + len(replacement_segments),
        audio_frontier_window=int(final_audio_frontier),
        prompt_tokens=tuple(int(value) for value in next_prompt_tokens),
        stable_token_segments=(
            *state.stable_token_segments[:rebase_checkpoint_id],
            *(
                tuple(int(value) for value in segment)
                for segment in replacement_segments
            ),
        ),
        committed_segment_ids=(
            *state.committed_segment_ids[:rebase_checkpoint_id],
            *(
                fallback_id if index == 0 else f"{fallback_id}:{index}"
                for index, _ in enumerate(replacement_segments)
            ),
        ),
        checkpoint_audio_frontiers=(
            *state.checkpoint_audio_frontiers[:rebase_checkpoint_id + 1],
            *(
                int(final_audio_frontier)
                for _ in replacement_segments
            ),
        ),
        speculative_version=max(
            (state.speculative_version, *invalidated)
        ),
    )
    return CommitResult(True, "checkpoint-rebased", installed, invalidated)

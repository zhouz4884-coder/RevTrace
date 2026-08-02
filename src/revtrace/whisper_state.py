"""Whisper prompt-state contracts used by the cross-architecture closure.

The user-visible transcript and the feedback state are deliberately separate.
Only ``prompt_token_ids`` can affect the next Whisper window.  A provisional
display therefore has no state authority until the corresponding transition
is committed under the current session/contract/policy version.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from enum import Enum
from typing import Iterable, Sequence


def paired_slo_goodput_speedup(
    baseline_latencies: Sequence[float],
    baseline_wall_seconds: float,
    method_latencies: Sequence[float],
    method_wall_seconds: float,
    slo_seconds: float,
) -> tuple[float, float, float]:
    """Return paired baseline/method goodput and their speedup.

    Both sides consume event sets with the same semantic scope.  Keeping the
    pairing in one function prevents a terminal display event from being
    included only on the method side, which previously inflated the reported
    display-SLO speedup by ``windows / (windows - 1)``.
    """

    if baseline_wall_seconds <= 0 or method_wall_seconds <= 0:
        raise ValueError("wall-clock durations must be positive")
    baseline = sum(
        float(value) <= slo_seconds for value in baseline_latencies
    ) / baseline_wall_seconds
    method = sum(
        float(value) <= slo_seconds for value in method_latencies
    ) / method_wall_seconds
    return baseline, method, method / baseline if baseline > 0 else float("inf")


def checkpoint_due_for_session(
    window_index: int,
    session_id: int,
    *,
    revisions: int,
    phase_policy: str,
    terminal: bool,
    total_nonterminal_revisions: int | None = None,
) -> bool:
    """Schedule bounded checkpoints without forcing a synchronized burst.

    A naive ``session_id % revisions`` phase increases the number of
    checkpoints in a finite trace.  When the nonterminal horizon is known, the
    staggered policy instead chooses among the phases that (1) preserve the
    maximum ``revisions``-step authority age and (2) use the same minimum
    number of checkpoints per session as the synchronized policy.
    """

    if revisions <= 0 or window_index < 0 or session_id < 0:
        raise ValueError("checkpoint indices and period must be valid")
    if phase_policy not in {"synchronized", "session-staggered"}:
        raise ValueError("unsupported checkpoint phase policy")
    if terminal:
        return False
    revision_number = window_index + 1
    if phase_policy == "synchronized":
        return revision_number % revisions == 0
    if total_nonterminal_revisions is None:
        raise ValueError(
            "staggered checkpoints require the finite nonterminal horizon"
        )
    if total_nonterminal_revisions < 0:
        raise ValueError("nonterminal revision horizon must be non-negative")
    checkpoint_count = total_nonterminal_revisions // revisions
    if checkpoint_count == 0:
        return False
    first_phase = max(
        1,
        total_nonterminal_revisions - checkpoint_count * revisions + 1,
    )
    phase_slots = revisions - first_phase + 1
    phase = first_phase + (session_id % phase_slots)
    return (
        revision_number >= phase
        and (revision_number - phase) % revisions == 0
    )


def cuda_device_index(device: str) -> int:
    """Return the process-local CUDA index for a configured device.

    ``cuda`` and ``cuda:0`` refer to the same physical device inside the
    process.  Resource accounting must canonicalize that alias, otherwise a
    colocated proposer/verifier is incorrectly charged as two GPUs.
    """

    value = str(device).strip().lower()
    if value == "cuda":
        return 0
    if value.startswith("cuda:"):
        return int(value.split(":", 1)[1])
    raise ValueError(f"not a CUDA device: {device}")


def physical_cuda_device_count(devices: Sequence[str]) -> int:
    """Count distinct process-visible CUDA devices, not logical roles."""

    return len({cuda_device_index(device) for device in devices})


def append_prompt_tokens(
    current: Sequence[int],
    segment: Sequence[int],
    *,
    start_of_previous_token: int,
    maximum_tokens: int,
) -> tuple[int, ...]:
    """Append raw Whisper segment tokens to its bounded feedback state.

    Long-form Whisper reuses generated segment token IDs rather than decoding
    and re-tokenizing text.  The actual decoder prompt contains one
    ``<|startofprev|>`` marker followed by the newest suffix that fits the
    frozen prompt budget.
    """

    if maximum_tokens < 2:
        raise ValueError("maximum_tokens must leave room for history")
    values = tuple(int(value) for value in current)
    history = (
        values[1:]
        if values and values[0] == int(start_of_previous_token)
        else values
    )
    merged = (*history, *(int(value) for value in segment))
    if not merged:
        return ()
    return (
        int(start_of_previous_token),
        *merged[-(maximum_tokens - 1) :],
    )


def token_digest(token_ids: Sequence[int]) -> str:
    return hashlib.sha256(
        json.dumps(
            [int(value) for value in token_ids],
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()


def longest_common_prefix(
    left: Sequence[int],
    right: Sequence[int],
) -> tuple[int, ...]:
    prefix: list[int] = []
    for lhs, rhs in zip(left, right):
        if int(lhs) != int(rhs):
            break
        prefix.append(int(lhs))
    return tuple(prefix)


@dataclass(frozen=True)
class WhisperVersion:
    session_id: str
    contract_epoch: int
    policy_version: int
    state_version: int

    def child(self) -> "WhisperVersion":
        return WhisperVersion(
            session_id=self.session_id,
            contract_epoch=self.contract_epoch,
            policy_version=self.policy_version,
            state_version=self.state_version + 1,
        )


@dataclass(frozen=True)
class PromptState:
    version: WhisperVersion
    prompt_token_ids: tuple[int, ...]
    prompt_text: str

    @property
    def sha256(self) -> str:
        return token_digest(self.prompt_token_ids)


@dataclass(frozen=True)
class PromptTransition:
    parent: WhisperVersion
    selected_token_ids: tuple[int, ...]
    selected_text: str
    source: str
    terminal: bool
    minimum_margin: float | None


class StalePromptTransition(ValueError):
    """Raised when a result no longer owns the current prompt state."""


class WhisperStateAction(str, Enum):
    """Authority decision for one architecture-specific state projection."""

    FAST_COMMIT = "fast-commit"
    RISK_AUTHORITY = "risk-canonical-authority"
    CHECKPOINT_AUTHORITY = "checkpoint-authority"
    TERMINAL_AUTHORITY = "terminal-canonical-authority"


def capacity_rebase_required(
    prompt_tokens: int,
    *,
    declared_next_segment_tokens: int,
    maximum_prompt_tokens: int,
) -> bool:
    """Return whether feedback must be discarded before the next decode.

    The trigger is derived entirely from declared decoder bounds.  Rebase
    removes prior write authority and therefore cannot introduce an
    uncertified token into the next prompt.
    """

    if prompt_tokens < 0 or declared_next_segment_tokens < 1:
        raise ValueError("prompt and segment token bounds must be positive")
    if maximum_prompt_tokens < 2:
        raise ValueError("maximum prompt tokens must leave history capacity")
    return (
        prompt_tokens + declared_next_segment_tokens
        > maximum_prompt_tokens
    )


def work_budget_requires_authority(
    generation_step_count: int,
    *,
    proposer_max_new_tokens: int,
    authority_max_new_tokens: int,
) -> bool:
    """Return whether a capped proposal needs extended canonical work.

    Exhausting a smaller proposer budget means the proposal did not reach its
    own terminal decision.  It may be displayed provisionally, but it cannot
    define the target canonical state or final-output contract.
    """

    if generation_step_count < 0:
        raise ValueError("generation step count must be non-negative")
    if proposer_max_new_tokens <= 0 or authority_max_new_tokens <= 0:
        raise ValueError("work budgets must be positive")
    return (
        authority_max_new_tokens > proposer_max_new_tokens
        and generation_step_count >= proposer_max_new_tokens
    )


def terminal_frontier_reached(
    next_windows: Sequence[int],
    *,
    windows_per_session: int,
) -> bool:
    """Return whether no session can release another nonterminal proposal."""

    if windows_per_session < 1:
        raise ValueError("windows_per_session must be positive")
    return bool(next_windows) and all(
        int(window) >= windows_per_session - 1
        for window in next_windows
    )


def proposer_terminal_spillover_eligible(
    *,
    terminal: bool,
    ready_sessions: Sequence[int],
) -> bool:
    """Return whether the proposer device is presently reclaimable.

    A global terminal frontier is too strict for asynchronously advancing
    sessions: early terminal jobs arrive while another session is waiting for
    canonical state authority. The useful safety condition is instead that no
    proposal is ready *now*. A device-level execution lock in the runtime
    serializes this terminal-only canonical work with any proposal that becomes
    ready later, preserving the isolated singleton arithmetic path.
    """

    return bool(terminal) and not bool(ready_sessions)


def proposer_authority_spillover_eligible(
    *,
    ready_sessions: Sequence[int],
) -> bool:
    """Return whether canonical work may reclaim the proposer device now.

    The runtime lock is the correctness mechanism. This predicate is the
    work-conservation policy: reclaim only an otherwise idle proposer epoch.
    """

    return not bool(ready_sessions)


@dataclass(frozen=True)
class WhisperStateRiskPolicy:
    """Contract-scoped admission boundary for Whisper feedback writes.

    A single global margin is insufficient when numerical flips become more
    consequential after a long feedback history. Optional state-age and
    prompt-load clauses raise the required margin only in empirically exposed
    regions, retaining the low-risk fast path.
    """

    margin_threshold: float
    age_window_index: int | None = None
    age_margin_threshold: float | None = None
    late_window_index: int | None = None
    late_margin_threshold: float | None = None
    high_load_prompt_tokens: int | None = None
    high_load_margin_threshold: float | None = None
    window_margin_rules: tuple[tuple[int, float], ...] = ()

    def __post_init__(self) -> None:
        if (self.age_window_index is None) != (
            self.age_margin_threshold is None
        ):
            raise ValueError(
                "state-age window and margin must be specified together"
            )
        if self.age_window_index is not None and self.age_window_index < 0:
            raise ValueError("state-age window index must be non-negative")
        if (
            self.age_margin_threshold is not None
            and self.age_margin_threshold < self.margin_threshold
        ):
            raise ValueError(
                "state-age margin cannot be lower than the base margin"
            )
        if (self.late_window_index is None) != (
            self.late_margin_threshold is None
        ):
            raise ValueError(
                "late window and late margin must be specified together"
            )
        if self.late_window_index is not None and self.late_window_index < 0:
            raise ValueError("late window index must be non-negative")
        if (
            self.late_margin_threshold is not None
            and self.late_margin_threshold < self.margin_threshold
        ):
            raise ValueError(
                "late margin cannot be lower than the base margin"
            )
        if (self.high_load_prompt_tokens is None) != (
            self.high_load_margin_threshold is None
        ):
            raise ValueError(
                "high-load prompt and margin must be specified together"
            )
        if (
            self.high_load_prompt_tokens is not None
            and self.high_load_prompt_tokens < 1
        ):
            raise ValueError("high-load prompt threshold must be positive")
        if (
            self.high_load_margin_threshold is not None
            and self.high_load_margin_threshold < self.margin_threshold
        ):
            raise ValueError(
                "high-load margin cannot be lower than the base margin"
            )
        seen_windows: set[int] = set()
        for window_index, threshold in self.window_margin_rules:
            if window_index < 0:
                raise ValueError("window margin index must be non-negative")
            if threshold < self.margin_threshold:
                raise ValueError(
                    "window margin cannot be lower than the base margin"
                )
            if window_index in seen_windows:
                raise ValueError("window margin indices must be unique")
            seen_windows.add(window_index)

    def reason(
        self,
        minimum_margin: float | None,
        *,
        window_index: int,
        prompt_tokens: int = 0,
    ) -> str | None:
        if minimum_margin is None:
            return "missing-margin"
        if minimum_margin <= self.margin_threshold:
            return "base-margin"
        for rule_window, rule_threshold in self.window_margin_rules:
            if (
                window_index == rule_window
                and minimum_margin <= rule_threshold
            ):
                return "window-state-margin"
        if (
            self.age_window_index is not None
            and self.age_margin_threshold is not None
            and window_index == self.age_window_index
            and minimum_margin <= self.age_margin_threshold
        ):
            return "state-age-margin"
        if (
            self.late_window_index is not None
            and self.late_margin_threshold is not None
            and window_index >= self.late_window_index
            and minimum_margin <= self.late_margin_threshold
        ):
            return "late-state-margin"
        if (
            self.high_load_prompt_tokens is not None
            and self.high_load_margin_threshold is not None
            and prompt_tokens >= self.high_load_prompt_tokens
            and minimum_margin <= self.high_load_margin_threshold
        ):
            return "high-load-state-margin"
        return None

    def requires_canonical(
        self,
        minimum_margin: float | None,
        *,
        window_index: int,
        prompt_tokens: int = 0,
    ) -> bool:
        return self.reason(
            minimum_margin,
            window_index=window_index,
            prompt_tokens=prompt_tokens,
        ) is not None


def prompt_state_action(
    policy: WhisperStateRiskPolicy,
    minimum_margin: float | None,
    *,
    window_index: int,
    prompt_tokens: int = 0,
    terminal: bool,
    checkpoint_due: bool,
) -> WhisperStateAction:
    """Choose fast entry or one of the canonical authority paths.

    Terminal output has no successor state, but its stable user-visible value
    still requires output authority.  A checkpoint takes precedence over the
    risk gate because it explicitly refreshes state authority.  Risky and
    terminal batched proposals remain provisional until singleton canonical
    execution supplies the relevant authority.
    """

    if terminal:
        return WhisperStateAction.TERMINAL_AUTHORITY
    if checkpoint_due:
        return WhisperStateAction.CHECKPOINT_AUTHORITY
    if policy.reason(
        minimum_margin,
        window_index=window_index,
        prompt_tokens=prompt_tokens,
    ) is not None:
        return WhisperStateAction.RISK_AUTHORITY
    return WhisperStateAction.FAST_COMMIT


def commit_prompt_transition(
    current: PromptState,
    transition: PromptTransition,
) -> PromptState:
    if transition.parent != current.version:
        raise StalePromptTransition(
            "transition parent does not match the current prompt version"
        )
    return PromptState(
        version=current.version.child(),
        prompt_token_ids=transition.selected_token_ids,
        prompt_text=transition.selected_text,
    )


class LocalAgreement2:
    """Token-level LocalAgreement-2 confirmed-prefix baseline.

    Two successive hypotheses for the same growing audio buffer are compared.
    Only their longest common prefix is newly confirmed.  This models the
    confirmed/unconfirmed text boundary of Whisper-Streaming; it does *not*
    certify equality with a singleton-canonical feedback state.
    """

    def __init__(self) -> None:
        self.confirmed: tuple[int, ...] = ()
        self.previous: tuple[int, ...] | None = None

    def update(self, hypothesis: Iterable[int]) -> tuple[int, ...]:
        current = tuple(int(value) for value in hypothesis)
        if self.previous is None:
            self.previous = current
            return self.confirmed
        agreed = longest_common_prefix(self.previous, current)
        if len(agreed) > len(self.confirmed):
            self.confirmed = agreed
        self.previous = current
        return self.confirmed

    def flush(self, hypothesis: Iterable[int]) -> tuple[int, ...]:
        self.confirmed = tuple(int(value) for value in hypothesis)
        self.previous = self.confirmed
        return self.confirmed

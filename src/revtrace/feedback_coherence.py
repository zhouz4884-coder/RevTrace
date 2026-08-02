"""Elastic feedback-state coherence for revision-generative serving.

The controller in this module is deliberately architecture independent.  A
model adapter owns the mapping from a candidate output to the feedback state
used by the next revision; the controller only decides whether that mapping is
allowed to acquire state authority.

The central safety distinction is between display and feedback ancestry.  A
provisional result may be shown immediately, but HOLD, DECAY, and RESET never
add that result to the ancestry of a future model input.  A periodic hard reset
is required for a bounded influence horizon: truncating tokens alone does not
remove the causal dependence of a new token on an older prompt that generated
it.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field, replace
from enum import Enum
from typing import Protocol, Sequence


class CoherenceMode(str, Enum):
    COHERENT = "coherent"
    QUARANTINE = "quarantine"
    REANCHOR = "reanchor"


class FeedbackAction(str, Enum):
    FAST_COMMIT = "fast-commit"
    PROVISIONAL_HOLD = "provisional-hold"
    DECAY_SUFFIX = "decay-suffix"
    SAFE_RESET = "safe-reset"


@dataclass(frozen=True)
class FeedbackAtom:
    """One feedback token and the revisions that can causally affect it."""

    token_id: int
    ancestor_versions: frozenset[int]

    def __post_init__(self) -> None:
        if any(value < 0 for value in self.ancestor_versions):
            raise ValueError("ancestor versions must be non-negative")


@dataclass(frozen=True)
class FeedbackIdentity:
    session_id: str
    contract_epoch: int
    policy_version: int
    state_version: int

    def __post_init__(self) -> None:
        if not self.session_id:
            raise ValueError("session_id must be non-empty")
        if min(
            self.contract_epoch,
            self.policy_version,
            self.state_version,
        ) < 0:
            raise ValueError("versions must be non-negative")

    def child(self) -> "FeedbackIdentity":
        return replace(self, state_version=self.state_version + 1)


@dataclass(frozen=True)
class ElasticFeedbackState:
    identity: FeedbackIdentity
    atoms: tuple[FeedbackAtom, ...] = ()
    mode: CoherenceMode = CoherenceMode.COHERENT
    feedback_debt: int = 0
    hold_age: int = 0
    safe_streak: int = 0
    last_reset_version: int = 0

    def __post_init__(self) -> None:
        if min(
            self.feedback_debt,
            self.hold_age,
            self.safe_streak,
            self.last_reset_version,
        ) < 0:
            raise ValueError("state counters must be non-negative")
        if self.last_reset_version > self.identity.state_version:
            raise ValueError("reset version cannot be in the future")

    @property
    def prompt_load(self) -> int:
        return len(self.atoms)

    @property
    def ancestors(self) -> frozenset[int]:
        return frozenset(
            version
            for atom in self.atoms
            for version in atom.ancestor_versions
        )

    @property
    def oldest_ancestor_age(self) -> int:
        if not self.ancestors:
            return 0
        return self.identity.state_version - min(self.ancestors)


@dataclass(frozen=True)
class FeedbackCandidate:
    session_id: str
    contract_epoch: int
    policy_version: int
    parent_state_version: int
    token_ids: tuple[int, ...]
    minimum_margin: float | None
    terminal: bool = False

    def __post_init__(self) -> None:
        if not self.session_id:
            raise ValueError("session_id must be non-empty")
        if min(
            self.contract_epoch,
            self.policy_version,
            self.parent_state_version,
        ) < 0:
            raise ValueError("candidate versions must be non-negative")
        if self.minimum_margin is not None and not math.isfinite(
            self.minimum_margin
        ):
            raise ValueError("minimum_margin must be finite")


@dataclass(frozen=True)
class EFSCContract:
    """Frozen debt-and-hysteresis contract for one policy epoch."""

    enter_margin: float
    exit_margin: float
    minimum_hold_windows: int = 1
    safe_streak_required: int = 2
    maximum_quarantine_windows: int = 3
    maximum_feedback_debt: int = 3
    maximum_influence_windows: int = 3
    maximum_prompt_tokens: int = 224
    decay_suffix_tokens: int = 32

    def __post_init__(self) -> None:
        if not math.isfinite(self.enter_margin) or not math.isfinite(
            self.exit_margin
        ):
            raise ValueError("margin thresholds must be finite")
        if self.exit_margin <= self.enter_margin:
            raise ValueError("exit margin must exceed enter margin")
        if min(
            self.minimum_hold_windows,
            self.safe_streak_required,
            self.maximum_quarantine_windows,
            self.maximum_feedback_debt,
            self.maximum_influence_windows,
            self.maximum_prompt_tokens,
            self.decay_suffix_tokens,
        ) < 1:
            raise ValueError("all EFSC bounds must be positive")
        if self.minimum_hold_windows > self.maximum_quarantine_windows:
            raise ValueError("minimum hold cannot exceed quarantine horizon")
        if self.decay_suffix_tokens >= self.maximum_prompt_tokens:
            raise ValueError("decay suffix must be below prompt capacity")


class FeedbackProjectionAdapter(Protocol):
    """Architecture-specific feedback projection behind a shared policy."""

    name: str

    def fast_commit(
        self,
        current: ElasticFeedbackState,
        candidate: FeedbackCandidate,
        *,
        next_version: int,
    ) -> tuple[FeedbackAtom, ...]: ...

    def decay(
        self,
        current: ElasticFeedbackState,
        *,
        suffix_tokens: int,
    ) -> tuple[FeedbackAtom, ...]: ...


@dataclass(frozen=True)
class WhisperHistoryAdapter:
    """Whisper previous-text history: append the newest authorized segment."""

    maximum_history_tokens: int
    name: str = "whisper-previous-text"

    def __post_init__(self) -> None:
        if self.maximum_history_tokens < 1:
            raise ValueError("Whisper history capacity must be positive")

    def fast_commit(
        self,
        current: ElasticFeedbackState,
        candidate: FeedbackCandidate,
        *,
        next_version: int,
    ) -> tuple[FeedbackAtom, ...]:
        inherited = current.ancestors | {next_version}
        additions = tuple(
            FeedbackAtom(int(token), frozenset(inherited))
            for token in candidate.token_ids
        )
        return (*current.atoms, *additions)[-self.maximum_history_tokens :]

    def decay(
        self,
        current: ElasticFeedbackState,
        *,
        suffix_tokens: int,
    ) -> tuple[FeedbackAtom, ...]:
        return current.atoms[-suffix_tokens:]


@dataclass(frozen=True)
class QwenRollbackAdapter:
    """Qwen rollback projection supplied by the official tokenizer path.

    ``candidate.token_ids`` must already be the exact next-state projection
    (the output of ``state_projection_record``), not raw generated tokens.
    The projection replaces the previous rollback prefix.  Every projected
    token conservatively inherits all ancestors of the prompt that generated
    it.
    """

    name: str = "qwen-rollback-prefix"

    def fast_commit(
        self,
        current: ElasticFeedbackState,
        candidate: FeedbackCandidate,
        *,
        next_version: int,
    ) -> tuple[FeedbackAtom, ...]:
        inherited = current.ancestors | {next_version}
        return tuple(
            FeedbackAtom(int(token), frozenset(inherited))
            for token in candidate.token_ids
        )

    def decay(
        self,
        current: ElasticFeedbackState,
        *,
        suffix_tokens: int,
    ) -> tuple[FeedbackAtom, ...]:
        return current.atoms[-suffix_tokens:]


@dataclass(frozen=True)
class EFSCDecision:
    action: FeedbackAction
    reason: str
    display_token_ids: tuple[int, ...]
    state_changed: bool
    candidate_became_ancestor: bool


@dataclass(frozen=True)
class EFSCPreparation:
    action: FeedbackAction | None
    reason: str
    state_changed: bool


class StaleFeedbackCandidate(ValueError):
    """Raised when a candidate does not own the current policy state."""


class ElasticFeedbackController:
    """Debt-bounded hysteresis controller with no critical-path authority."""

    def __init__(self, contract: EFSCContract) -> None:
        self.contract = contract

    def prepare_for_proposal(
        self,
        state: ElasticFeedbackState,
        adapter: FeedbackProjectionAdapter,
    ) -> tuple[ElasticFeedbackState, EFSCPreparation]:
        """Apply age/debt/load recovery before a candidate reads feedback.

        A post-generation reset cannot bound how long an old ancestor affects
        model outputs because the candidate has already read that state.  This
        method is therefore a mandatory pre-inference boundary.  Any state
        change increments the version and invalidates candidates constructed
        from the prior feedback state.
        """

        action: FeedbackAction | None = None
        reason = "feedback-state-ready"
        if (
            state.ancestors
            and state.oldest_ancestor_age
            >= self.contract.maximum_influence_windows
        ):
            action = FeedbackAction.SAFE_RESET
            reason = "bounded-influence-horizon"
        elif state.feedback_debt >= self.contract.maximum_feedback_debt:
            action = FeedbackAction.SAFE_RESET
            reason = "feedback-debt-bound"
        elif state.prompt_load >= self.contract.maximum_prompt_tokens:
            action = FeedbackAction.DECAY_SUFFIX
            reason = "prompt-load-bound"

        if action is None:
            return state, EFSCPreparation(None, reason, False)

        next_identity = state.identity.child()
        if action == FeedbackAction.SAFE_RESET:
            next_state = ElasticFeedbackState(
                identity=next_identity,
                atoms=(),
                mode=CoherenceMode.REANCHOR,
                feedback_debt=0,
                hold_age=0,
                safe_streak=0,
                last_reset_version=next_identity.state_version,
            )
        else:
            atoms = adapter.decay(
                state, suffix_tokens=self.contract.decay_suffix_tokens
            )
            next_state = ElasticFeedbackState(
                identity=next_identity,
                atoms=atoms,
                mode=CoherenceMode.REANCHOR,
                feedback_debt=min(
                    state.feedback_debt,
                    len({v for atom in atoms for v in atom.ancestor_versions}),
                ),
                hold_age=0,
                safe_streak=0,
                last_reset_version=state.last_reset_version,
            )
        if not next_state.ancestors.issubset(state.ancestors):
            raise AssertionError("pre-proposal recovery expanded ancestry")
        return next_state, EFSCPreparation(action, reason, True)

    def _assert_prepared(self, state: ElasticFeedbackState) -> None:
        if (
            state.ancestors
            and state.oldest_ancestor_age
            >= self.contract.maximum_influence_windows
        ):
            raise RuntimeError(
                "prepare_for_proposal must reset the influence horizon"
            )
        if state.feedback_debt >= self.contract.maximum_feedback_debt:
            raise RuntimeError(
                "prepare_for_proposal must retire feedback debt"
            )
        if state.prompt_load >= self.contract.maximum_prompt_tokens:
            raise RuntimeError(
                "prepare_for_proposal must enforce prompt capacity"
            )

    @staticmethod
    def _check_identity(
        state: ElasticFeedbackState,
        candidate: FeedbackCandidate,
    ) -> None:
        identity = state.identity
        if (
            candidate.session_id != identity.session_id
            or candidate.contract_epoch != identity.contract_epoch
            or candidate.policy_version != identity.policy_version
            or candidate.parent_state_version != identity.state_version
        ):
            raise StaleFeedbackCandidate(
                "candidate session/contract/policy/parent does not own state"
            )

    def _choose_action(
        self,
        state: ElasticFeedbackState,
        candidate: FeedbackCandidate,
    ) -> tuple[FeedbackAction, str, int]:
        margin = candidate.minimum_margin
        safe_enter = margin is not None and margin > self.contract.enter_margin
        safe_exit = margin is not None and margin >= self.contract.exit_margin
        new_streak = state.safe_streak + 1 if safe_exit else 0

        # Terminal output has no successor feedback state.  It can be displayed
        # under the output-quality contract without acquiring prompt authority.
        if candidate.terminal:
            return (
                FeedbackAction.PROVISIONAL_HOLD,
                "terminal-has-no-successor-feedback-state",
                new_streak,
            )

        if state.mode == CoherenceMode.COHERENT:
            if safe_enter:
                return FeedbackAction.FAST_COMMIT, "certified-fast-entry", 0
            return FeedbackAction.PROVISIONAL_HOLD, "enter-quarantine", new_streak

        if state.mode == CoherenceMode.QUARANTINE:
            next_hold_age = state.hold_age + 1
            if (
                next_hold_age >= self.contract.minimum_hold_windows
                and new_streak >= self.contract.safe_streak_required
            ):
                return FeedbackAction.DECAY_SUFFIX, "hysteresis-reanchor", 0
            if next_hold_age >= self.contract.maximum_quarantine_windows:
                return FeedbackAction.SAFE_RESET, "quarantine-horizon", 0
            return FeedbackAction.PROVISIONAL_HOLD, "quarantine-hold", new_streak

        # REANCHOR never appends a candidate to a stale chain.  The preceding
        # DECAY/RESET has already moved down the state lattice; a fresh safe
        # observation is required before write authority resumes.
        if safe_exit:
            return FeedbackAction.FAST_COMMIT, "reanchor-safe-entry", 0
        return FeedbackAction.PROVISIONAL_HOLD, "reanchor-not-yet-safe", new_streak

    def step(
        self,
        state: ElasticFeedbackState,
        candidate: FeedbackCandidate,
        adapter: FeedbackProjectionAdapter,
    ) -> tuple[ElasticFeedbackState, EFSCDecision]:
        self._check_identity(state, candidate)
        self._assert_prepared(state)
        action, reason, new_streak = self._choose_action(state, candidate)
        next_identity = state.identity.child()
        candidate_version = next_identity.state_version

        if action == FeedbackAction.FAST_COMMIT:
            atoms = adapter.fast_commit(
                state, candidate, next_version=candidate_version
            )
            if len(atoms) > self.contract.maximum_prompt_tokens:
                raise AssertionError(
                    "adapter projection exceeded the frozen prompt capacity"
                )
            next_state = ElasticFeedbackState(
                identity=next_identity,
                atoms=atoms,
                mode=CoherenceMode.COHERENT,
                feedback_debt=state.feedback_debt + 1,
                hold_age=0,
                safe_streak=0,
                last_reset_version=state.last_reset_version,
            )
            became_ancestor = candidate_version in next_state.ancestors
        elif action == FeedbackAction.PROVISIONAL_HOLD:
            next_state = ElasticFeedbackState(
                identity=next_identity,
                atoms=state.atoms,
                mode=(
                    state.mode
                    if candidate.terminal
                    else CoherenceMode.QUARANTINE
                ),
                feedback_debt=state.feedback_debt,
                hold_age=state.hold_age + int(not candidate.terminal),
                safe_streak=new_streak,
                last_reset_version=state.last_reset_version,
            )
            became_ancestor = False
        elif action == FeedbackAction.DECAY_SUFFIX:
            atoms = adapter.decay(
                state, suffix_tokens=self.contract.decay_suffix_tokens
            )
            next_state = ElasticFeedbackState(
                identity=next_identity,
                atoms=atoms,
                mode=CoherenceMode.REANCHOR,
                feedback_debt=min(
                    state.feedback_debt,
                    len({v for atom in atoms for v in atom.ancestor_versions}),
                ),
                hold_age=0,
                safe_streak=0,
                last_reset_version=state.last_reset_version,
            )
            became_ancestor = False
        else:
            next_state = ElasticFeedbackState(
                identity=next_identity,
                atoms=(),
                mode=CoherenceMode.REANCHOR,
                feedback_debt=0,
                hold_age=0,
                safe_streak=0,
                last_reset_version=next_identity.state_version,
            )
            became_ancestor = False

        if not next_state.ancestors.issuperset(state.ancestors) and action in {
            FeedbackAction.PROVISIONAL_HOLD,
        }:
            raise AssertionError("HOLD changed authorized feedback ancestry")
        if action in {
            FeedbackAction.PROVISIONAL_HOLD,
            FeedbackAction.DECAY_SUFFIX,
            FeedbackAction.SAFE_RESET,
        } and not next_state.ancestors.issubset(state.ancestors):
            raise AssertionError("non-commit action expanded feedback ancestry")
        if next_state.feedback_debt > self.contract.maximum_feedback_debt:
            raise AssertionError("feedback debt exceeded frozen contract")
        if (
            next_state.ancestors
            and next_state.oldest_ancestor_age
            > self.contract.maximum_influence_windows
        ):
            raise AssertionError("feedback influence horizon exceeded")

        return next_state, EFSCDecision(
            action=action,
            reason=reason,
            display_token_ids=candidate.token_ids,
            state_changed=(next_state.atoms != state.atoms),
            candidate_became_ancestor=became_ancestor,
        )


@dataclass(frozen=True)
class HysteresisCalibration:
    enter_margin: float
    exit_margin: float
    known_failure_ceiling: float
    eligible_quantile: float


def calibrate_hysteresis_margins(
    eligible_margins: Sequence[float],
    known_failure_margins: Sequence[float],
    *,
    exit_quantile: float = 0.75,
    minimum_gap: float = 1e-6,
) -> HysteresisCalibration:
    """Derive model-specific thresholds without model-specific policy code.

    The enter boundary fail-closes over every calibration failure root.  The
    exit boundary is a higher empirical quantile, producing real hysteresis.
    One subsequent adaptation epoch may replace this frozen result, but an
    audit epoch must never tune itself from its own outcomes.
    """

    values = sorted(float(value) for value in eligible_margins)
    failures = tuple(float(value) for value in known_failure_margins)
    if not values or not failures:
        raise ValueError("calibration requires eligible and failure margins")
    if not 0.0 < exit_quantile < 1.0:
        raise ValueError("exit_quantile must lie in (0,1)")
    if minimum_gap <= 0:
        raise ValueError("minimum_gap must be positive")
    if any(not math.isfinite(value) for value in (*values, *failures)):
        raise ValueError("calibration margins must be finite")
    failure_ceiling = max(failures)
    index = min(len(values) - 1, math.ceil(exit_quantile * len(values)) - 1)
    exit_margin = max(values[index], failure_ceiling + minimum_gap)
    return HysteresisCalibration(
        enter_margin=failure_ceiling,
        exit_margin=exit_margin,
        known_failure_ceiling=failure_ceiling,
        eligible_quantile=exit_quantile,
    )


class ProfilerChannel(str, Enum):
    NONE = "none"
    RANDOM_SENTINEL = "random-sentinel"
    TRIGGERED_DIAGNOSTIC = "triggered-diagnostic"


@dataclass(frozen=True)
class ProfilerDecision:
    epoch: int
    channel: ProfilerChannel
    certifies_current_epoch: bool


@dataclass
class EpochEvidence:
    eligible_fast_commits: int = 0
    sentinel_audits: int = 0
    caught_state_errors: int = 0
    diagnostic_probes: int = 0
    diagnostic_errors: int = 0


class EpochFencedBackgroundProfiler:
    """Separate formal random audits from biased diagnostic probes."""

    def __init__(
        self,
        *,
        epoch: int,
        sentinel_probability: float,
        seed: int = 20260802,
    ) -> None:
        if epoch < 1:
            raise ValueError("epoch must be positive")
        if not 0.0 < sentinel_probability < 1.0:
            raise ValueError("sentinel_probability must lie in (0,1)")
        self.epoch = epoch
        self.sentinel_probability = sentinel_probability
        self._rng = random.Random(seed)
        self.evidence = EpochEvidence()

    def decide(
        self,
        action: FeedbackAction,
        *,
        draw: float | None = None,
        diagnostics_enabled: bool = True,
    ) -> ProfilerDecision:
        if action == FeedbackAction.FAST_COMMIT:
            self.evidence.eligible_fast_commits += 1
            coin = self._rng.random() if draw is None else draw
            if not 0.0 <= coin < 1.0:
                raise ValueError("audit draw must lie in [0,1)")
            if coin < self.sentinel_probability:
                return ProfilerDecision(
                    self.epoch,
                    ProfilerChannel.RANDOM_SENTINEL,
                    True,
                )
        elif diagnostics_enabled:
            return ProfilerDecision(
                self.epoch,
                ProfilerChannel.TRIGGERED_DIAGNOSTIC,
                False,
            )
        return ProfilerDecision(self.epoch, ProfilerChannel.NONE, False)

    def observe(
        self,
        decision: ProfilerDecision,
        *,
        state_error: bool,
    ) -> None:
        if decision.epoch != self.epoch:
            raise ValueError("profiler outcome belongs to a stale epoch")
        if decision.channel == ProfilerChannel.RANDOM_SENTINEL:
            self.evidence.sentinel_audits += 1
            self.evidence.caught_state_errors += int(state_error)
        elif decision.channel == ProfilerChannel.TRIGGERED_DIAGNOSTIC:
            self.evidence.diagnostic_probes += 1
            self.evidence.diagnostic_errors += int(state_error)

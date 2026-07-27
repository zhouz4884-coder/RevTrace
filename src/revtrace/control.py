"""Adaptive state-certification control for RevTrace.

The controller deliberately separates three concepts:

* a versioned execution contract (``ContractFingerprint``);
* a simultaneous, anytime-valid envelope over a preregistered policy family;
* a queue-aware policy choice made only inside the certified envelope.

The formal evidence channel is a fixed-probability random base audit.  Idle
audits are useful diagnostics, but never enter the confidence sequence.
"""

from __future__ import annotations

import hashlib
import json
import random
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Iterable, Mapping

from .risk import AuditRiskBound


@dataclass(frozen=True)
class ContractFingerprint:
    """Everything that can change the arithmetic or revision contract."""

    model_sha256: str
    tokenizer_sha256: str
    runtime: str
    precision: str
    kernel_backend: str
    concurrency_class: str
    chunk_policy: str
    canonical_path: str

    def __post_init__(self) -> None:
        for name, value in asdict(self).items():
            if not value:
                raise ValueError(f"contract field {name} must be non-empty")

    @property
    def digest(self) -> str:
        payload = json.dumps(
            asdict(self), sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
        return hashlib.sha256(payload).hexdigest()


class AuditChannel(str, Enum):
    NONE = "none"
    BASE = "base"
    IDLE = "idle"


class ControlMode(str, Enum):
    WARMUP = "warmup_all_verify"
    ACTIVE = "active_certified"
    DRIFT_QUARANTINE = "drift_quarantine"
    FAIL_CLOSED = "fail_closed_all_verify"


@dataclass
class PolicyEvidence:
    threshold: float
    eligible_entries: int = 0
    base_audits: int = 0
    caught_state_errors: int = 0
    idle_audits: int = 0
    idle_state_errors: int = 0


@dataclass(frozen=True)
class PolicyCertificate:
    threshold: float
    eligible_entries: int
    base_audits: int
    caught_state_errors: int
    upper_error_count: int
    upper_risk: float
    frozen_failure_excluded: bool
    certified: bool


@dataclass(frozen=True)
class ControlDecision:
    epoch: int
    fingerprint: str
    mode: ControlMode
    threshold: float | None
    verify: bool
    terminal: bool
    base_audit_coin: bool
    idle_audit: bool
    audit_channel: AuditChannel
    minimum_margin: float | None
    state_amplification: float
    verifier_cost: float
    queue_depth: int
    risk_price: float
    queue_price: float
    reason: str


@dataclass(frozen=True)
class ControllerConfig:
    """Frozen control and evidence contract.

    ``policy_thresholds`` is a preregistered numerical approximation to a
    continuous monotone margin policy.  Simultaneous validity is preserved by
    splitting alpha over all thresholds before observing outcomes.
    """

    delta: float = 0.005
    alpha: float = 0.05
    audit_probability: float = 0.021
    minimum_base_audits: int = 500
    policy_thresholds: tuple[float, ...] = (
        0.0,
        0.025,
        0.05,
        0.075,
        0.10,
        0.15,
        0.20,
        0.30,
        0.50,
        0.75,
        1.0,
    )
    initial_risk_price: float = 1.0
    initial_queue_price: float = 1.0
    risk_price_step: float = 0.25
    queue_price_step: float = 0.05
    target_queue_depth: int = 0
    drift_quarantine_events: int = 64
    control_interval_events: int = 256

    def __post_init__(self) -> None:
        if not 0.0 < self.delta < 1.0:
            raise ValueError("delta must lie in (0,1)")
        if not 0.0 < self.alpha < 1.0:
            raise ValueError("alpha must lie in (0,1)")
        if not 0.0 < self.audit_probability < 1.0:
            raise ValueError("audit_probability must lie in (0,1)")
        if self.minimum_base_audits < 1:
            raise ValueError("minimum_base_audits must be positive")
        if not self.policy_thresholds:
            raise ValueError("at least one policy threshold is required")
        if tuple(sorted(set(self.policy_thresholds))) != self.policy_thresholds:
            raise ValueError("policy thresholds must be unique and sorted")
        if self.policy_thresholds[0] < 0:
            raise ValueError("policy thresholds cannot be negative")
        if min(
            self.initial_risk_price,
            self.initial_queue_price,
            self.risk_price_step,
            self.queue_price_step,
        ) < 0:
            raise ValueError("prices and price steps cannot be negative")
        if self.target_queue_depth < 0:
            raise ValueError("target queue depth cannot be negative")
        if self.drift_quarantine_events < 0:
            raise ValueError("drift quarantine cannot be negative")
        if self.control_interval_events < 1:
            raise ValueError("control interval must be positive")


@dataclass
class ControllerSnapshot:
    epoch: int
    fingerprint: str
    mode: str
    selected_threshold: float | None
    risk_price: float
    queue_price: float
    quarantine_remaining: int
    decisions: int
    verified: int
    fast_path: int
    base_audits: int
    idle_audits: int
    caught_base_state_errors: int
    caught_idle_state_errors: int
    frozen_failure_margin_floor: float | None
    certificates: list[dict[str, Any]] = field(default_factory=list)


@dataclass(frozen=True)
class IdleAuditCandidate:
    revision_id: str
    confidence_width: float
    state_amplification: float
    traffic_weight: float
    verifier_cost: float
    terminal: bool = False
    mandatory: bool = False
    base_audit: bool = False

    @property
    def value_of_information(self) -> float:
        if self.verifier_cost <= 0:
            raise ValueError("verifier cost must be positive")
        if min(
            self.confidence_width,
            self.state_amplification,
            self.traffic_weight,
        ) < 0:
            raise ValueError("VOI components cannot be negative")
        return (
            self.confidence_width
            * self.state_amplification
            * self.traffic_weight
            / self.verifier_cost
        )


def select_idle_audits(
    candidates: Iterable[IdleAuditCandidate],
    *,
    capacity_seconds: float,
) -> tuple[IdleAuditCandidate, ...]:
    """Greedy cancellable VOI schedule for strictly idle verifier capacity.

    Terminal, state-blocking, and base-audit work belongs to higher-priority
    queues and is therefore never selected as opportunistic work here.
    """

    if capacity_seconds < 0:
        raise ValueError("idle capacity cannot be negative")
    remaining = capacity_seconds
    selected: list[IdleAuditCandidate] = []
    eligible = [
        item
        for item in candidates
        if not (item.terminal or item.mandatory or item.base_audit)
    ]
    for item in sorted(
        eligible,
        key=lambda candidate: (
            -candidate.value_of_information,
            candidate.revision_id,
        ),
    ):
        if item.verifier_cost <= remaining + 1e-12:
            selected.append(item)
            remaining -= item.verifier_cost
    return tuple(selected)


class AdaptiveCertificationController:
    """Risk-priced controller with fail-closed epoch transitions."""

    def __init__(
        self,
        config: ControllerConfig,
        *,
        seed: int = 20260728,
    ) -> None:
        self.config = config
        self._rng = random.Random(seed)
        self._fingerprint: ContractFingerprint | None = None
        self._epoch = 0
        self._mode = ControlMode.FAIL_CLOSED
        self._evidence: dict[float, PolicyEvidence] = {}
        self._risk_price = config.initial_risk_price
        self._queue_price = config.initial_queue_price
        self._selected_threshold: float | None = None
        self._quarantine_remaining = 0
        self._decisions = 0
        self._verified = 0
        self._fast_path = 0
        self._base_audits = 0
        self._idle_audits = 0
        self._caught_base = 0
        self._caught_idle = 0
        self._last_recompute_decision = 0
        self._force_recompute = True
        self._failure_ledger: dict[str, float] = {}

    @property
    def fingerprint(self) -> ContractFingerprint:
        if self._fingerprint is None:
            raise RuntimeError("controller epoch has not been started")
        return self._fingerprint

    @property
    def epoch(self) -> int:
        return self._epoch

    @property
    def mode(self) -> ControlMode:
        return self._mode

    def start_epoch(
        self,
        fingerprint: ContractFingerprint,
        *,
        reason: str,
    ) -> int:
        """Invalidate old evidence and enter a fresh fail-closed epoch."""

        if not reason:
            raise ValueError("epoch transition reason must be non-empty")
        self._epoch += 1
        self._fingerprint = fingerprint
        self._evidence = {
            threshold: PolicyEvidence(threshold)
            for threshold in self.config.policy_thresholds
        }
        self._mode = ControlMode.WARMUP
        self._selected_threshold = None
        self._quarantine_remaining = 0
        self._risk_price = self.config.initial_risk_price
        self._queue_price = self.config.initial_queue_price
        self._decisions = 0
        self._verified = 0
        self._fast_path = 0
        self._base_audits = 0
        self._idle_audits = 0
        self._caught_base = 0
        self._caught_idle = 0
        self._last_recompute_decision = 0
        self._force_recompute = True
        return self._epoch

    def load_frozen_evidence(
        self,
        evidence: Mapping[float, Mapping[str, int]],
    ) -> None:
        """Load preregistered evidence for the current exact fingerprint.

        This is intended for deployment from a frozen certificate artifact,
        not for reusing evidence after a contract change.  It is permitted
        only before the controller has issued a decision.
        """

        if self._fingerprint is None:
            raise RuntimeError("start_epoch must precede evidence loading")
        if self._decisions:
            raise RuntimeError("cannot load evidence after control begins")
        unknown = set(evidence) - set(self._evidence)
        if unknown:
            raise ValueError(f"unknown policy thresholds: {sorted(unknown)}")
        for threshold, counts in evidence.items():
            target = self._evidence[threshold]
            target.eligible_entries = int(counts["eligible_entries"])
            target.base_audits = int(counts["base_audits"])
            target.caught_state_errors = int(
                counts["caught_state_errors"]
            )
            if min(
                target.eligible_entries,
                target.base_audits,
                target.caught_state_errors,
            ) < 0:
                raise ValueError("evidence counts cannot be negative")
            if target.base_audits > target.eligible_entries:
                raise ValueError("audits cannot exceed eligible entries")
            if target.caught_state_errors > target.base_audits:
                raise ValueError("caught errors cannot exceed audits")

    def _certificate(self, evidence: PolicyEvidence) -> PolicyCertificate:
        simultaneous_alpha = self.config.alpha / len(self._evidence)
        bound = AuditRiskBound(
            self.config.audit_probability, simultaneous_alpha
        )
        upper_count = bound.upper_error_count(
            evidence.eligible_entries,
            evidence.caught_state_errors,
        )
        upper_risk = (
            upper_count / evidence.eligible_entries
            if evidence.eligible_entries
            else 1.0
        )
        failure_floor = self._failure_ledger.get(self.fingerprint.digest)
        excluded = (
            failure_floor is not None
            and evidence.threshold < failure_floor
        )
        return PolicyCertificate(
            threshold=evidence.threshold,
            eligible_entries=evidence.eligible_entries,
            base_audits=evidence.base_audits,
            caught_state_errors=evidence.caught_state_errors,
            upper_error_count=upper_count,
            upper_risk=upper_risk,
            frozen_failure_excluded=excluded,
            certified=(
                not excluded
                and evidence.base_audits
                >= self.config.minimum_base_audits
                and upper_risk <= self.config.delta
            ),
        )

    def certificates(self) -> tuple[PolicyCertificate, ...]:
        return tuple(
            self._certificate(self._evidence[threshold])
            for threshold in self.config.policy_thresholds
        )

    def _select_threshold(
        self,
        *,
        state_amplification: float,
        verifier_cost: float,
        queue_depth: int,
    ) -> float | None:
        certified = [item for item in self.certificates() if item.certified]
        if not certified:
            return None
        total = max(
            evidence.eligible_entries
            for evidence in self._evidence.values()
        )
        candidates: list[tuple[float, float]] = []
        for certificate in certified:
            admitted_fraction = (
                certificate.eligible_entries / total if total else 0.0
            )
            verify_fraction = 1.0 - admitted_fraction
            objective = (
                self._risk_price
                * certificate.upper_risk
                * state_amplification
                + self._queue_price * verifier_cost * verify_fraction
            )
            candidates.append((objective, certificate.threshold))
        return min(candidates)[1]

    def decide(
        self,
        *,
        minimum_margin: float | None,
        terminal: bool,
        state_amplification: float = 1.0,
        verifier_cost: float = 1.0,
        queue_depth: int = 0,
        idle_capacity: bool = False,
        base_audit_draw: float | None = None,
    ) -> ControlDecision:
        if self._fingerprint is None:
            raise RuntimeError("start_epoch must be called before decide")
        if state_amplification < 0 or verifier_cost < 0 or queue_depth < 0:
            raise ValueError("cost, amplification, and queue must be nonnegative")

        self._decisions += 1
        draw = self._rng.random() if base_audit_draw is None else base_audit_draw
        if not 0.0 <= draw < 1.0:
            raise ValueError("base audit draw must lie in [0,1)")
        base_coin = (
            not terminal
            and minimum_margin is not None
            and draw < self.config.audit_probability
        )

        queue_error = queue_depth - self.config.target_queue_depth
        self._queue_price = max(
            0.0,
            self._queue_price + self.config.queue_price_step * queue_error,
        )
        if (
            self._force_recompute
            or self._decisions - self._last_recompute_decision
            >= self.config.control_interval_events
        ):
            self._selected_threshold = self._select_threshold(
                state_amplification=state_amplification,
                verifier_cost=verifier_cost,
                queue_depth=queue_depth,
            )
            self._last_recompute_decision = self._decisions
            self._force_recompute = False

        if terminal:
            verify = True
            reason = "terminal transitions are always canonical"
        elif self._quarantine_remaining > 0:
            verify = True
            reason = "short-horizon drift quarantine"
            self._quarantine_remaining -= 1
            self._mode = ControlMode.DRIFT_QUARANTINE
        elif self._selected_threshold is None:
            verify = True
            reason = "no simultaneously certified policy; fail closed"
            self._mode = ControlMode.WARMUP
        else:
            self._mode = ControlMode.ACTIVE
            risk_verify = (
                minimum_margin is None
                or minimum_margin <= self._selected_threshold
            )
            verify = risk_verify or base_coin
            reason = (
                "risk-priced policy verification"
                if risk_verify
                else (
                    "independent base audit"
                    if base_coin
                    else "certified fast path"
                )
            )

        idle_audit = (
            idle_capacity
            and not terminal
            and not verify
            and not base_coin
        )
        if idle_audit:
            verify = True
            reason = "opportunistic idle audit excluded from formal evidence"
        channel = (
            AuditChannel.BASE
            if base_coin
            else AuditChannel.IDLE
            if idle_audit
            else AuditChannel.NONE
        )
        self._verified += int(verify)
        self._fast_path += int(not verify)
        return ControlDecision(
            epoch=self._epoch,
            fingerprint=self.fingerprint.digest,
            mode=self._mode,
            threshold=self._selected_threshold,
            verify=verify,
            terminal=terminal,
            base_audit_coin=base_coin,
            idle_audit=idle_audit,
            audit_channel=channel,
            minimum_margin=minimum_margin,
            state_amplification=state_amplification,
            verifier_cost=verifier_cost,
            queue_depth=queue_depth,
            risk_price=self._risk_price,
            queue_price=self._queue_price,
            reason=reason,
        )

    def observe(
        self,
        decision: ControlDecision,
        *,
        state_error: bool | None,
    ) -> None:
        """Record an observed canonical comparison.

        Every nonterminal decision is an opportunity for all threshold
        policies whose fast path contains its margin.  Only a BASE audit can
        add a caught error to the formal confidence sequence.
        """

        if decision.epoch != self._epoch:
            raise ValueError("stale decision from an old contract epoch")
        if decision.fingerprint != self.fingerprint.digest:
            raise ValueError("decision fingerprint does not match epoch")
        if decision.audit_channel != AuditChannel.NONE and state_error is None:
            raise ValueError("audited decisions require a canonical outcome")
        observed_error = bool(state_error)
        margin = decision.minimum_margin
        if not decision.terminal and margin is not None:
            for threshold, evidence in self._evidence.items():
                if margin > threshold:
                    evidence.eligible_entries += 1
                    if decision.audit_channel == AuditChannel.BASE:
                        evidence.base_audits += 1
                        evidence.caught_state_errors += int(observed_error)
                    elif decision.audit_channel == AuditChannel.IDLE:
                        evidence.idle_audits += 1
                        evidence.idle_state_errors += int(observed_error)

        if decision.audit_channel == AuditChannel.BASE:
            self._base_audits += 1
            self._caught_base += int(observed_error)
            if observed_error:
                margin = decision.minimum_margin
                if margin is not None:
                    digest = self.fingerprint.digest
                    self._failure_ledger[digest] = max(
                        margin,
                        self._failure_ledger.get(digest, margin),
                    )
                self._risk_price += self.config.risk_price_step
                self._quarantine_remaining = (
                    self.config.drift_quarantine_events
                )
                self._mode = ControlMode.DRIFT_QUARANTINE
                self._selected_threshold = None
                self._force_recompute = True
        elif decision.audit_channel == AuditChannel.IDLE:
            self._idle_audits += 1
            self._caught_idle += int(observed_error)

    def snapshot(self) -> ControllerSnapshot:
        return ControllerSnapshot(
            epoch=self._epoch,
            fingerprint=self.fingerprint.digest,
            mode=self._mode.value,
            selected_threshold=self._selected_threshold,
            risk_price=self._risk_price,
            queue_price=self._queue_price,
            quarantine_remaining=self._quarantine_remaining,
            decisions=self._decisions,
            verified=self._verified,
            fast_path=self._fast_path,
            base_audits=self._base_audits,
            idle_audits=self._idle_audits,
            caught_base_state_errors=self._caught_base,
            caught_idle_state_errors=self._caught_idle,
            frozen_failure_margin_floor=self._failure_ledger.get(
                self.fingerprint.digest
            ),
            certificates=[asdict(item) for item in self.certificates()],
        )


def replay_controller(
    controller: AdaptiveCertificationController,
    events: Iterable[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """Deterministic semantic replay helper used by gates and regression tests."""

    records: list[dict[str, Any]] = []
    for index, event in enumerate(events):
        decision = controller.decide(
            minimum_margin=event.get("minimum_margin"),
            terminal=bool(event.get("terminal", False)),
            state_amplification=float(event.get("state_amplification", 1.0)),
            verifier_cost=float(event.get("verifier_cost", 1.0)),
            queue_depth=int(event.get("queue_depth", 0)),
            idle_capacity=bool(event.get("idle_capacity", False)),
            base_audit_draw=float(event.get("base_audit_draw", 0.999999)),
        )
        controller.observe(
            decision,
            state_error=(
                bool(event.get("state_error", False))
                if decision.verify
                else None
            ),
        )
        records.append(
            {
                "index": index,
                "decision": asdict(decision),
                "snapshot": asdict(controller.snapshot()),
            }
        )
    return records

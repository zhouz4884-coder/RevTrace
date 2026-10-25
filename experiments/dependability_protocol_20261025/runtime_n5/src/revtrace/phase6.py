"""Phase 6 evidence lifecycle and joint admission contracts.

Positive statistical evidence is restored only for an exact contract. A
covering execution envelope may provide a conservative warm start, but never
an immediately certified fast path. Counterexamples persist whenever their
recorded execution signature remains inside the target contract.
"""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import asdict, dataclass
from enum import Enum
from typing import Iterable


def _digest(payload: object) -> str:
    encoded = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


@dataclass(frozen=True)
class ExecutionIdentity:
    model_sha256: str
    tokenizer_processor_sha256: str
    runtime_commit: str
    driver_kernel: str
    dtype: str
    gpu_architecture: str
    canonical_version: str

    def __post_init__(self) -> None:
        if any(not value for value in asdict(self).values()):
            raise ValueError("execution identity fields must be non-empty")

    @property
    def digest(self) -> str:
        return _digest(asdict(self))


@dataclass(frozen=True)
class ExecutionSignature:
    batch_size: int
    sequence_bucket: int
    padding_bucket: str
    composition_signature: str
    language_class: str
    revision_depth_bucket: str

    def __post_init__(self) -> None:
        if self.batch_size < 1 or self.sequence_bucket < 1:
            raise ValueError("execution dimensions must be positive")
        if any(
            not value
            for value in (
                self.padding_bucket,
                self.composition_signature,
                self.language_class,
                self.revision_depth_bucket,
            )
        ):
            raise ValueError("execution signature fields must be non-empty")


@dataclass(frozen=True)
class ShapeEnvelope:
    """A finite set of complete, observed execution signatures.

    Keeping dimensions in separate sets accidentally denotes their Cartesian
    product.  That can transfer evidence to an execution combination that was
    never observed.  Membership and coverage are therefore exact set
    operations over complete signatures.
    """

    signatures: tuple[ExecutionSignature, ...]

    def __post_init__(self) -> None:
        if not self.signatures:
            raise ValueError("shape envelope signatures cannot be empty")
        if len(set(self.signatures)) != len(self.signatures):
            raise ValueError("shape envelope signatures must be unique")

    @property
    def batch_sizes(self) -> tuple[int, ...]:
        return tuple(sorted({item.batch_size for item in self.signatures}))

    @property
    def language_classes(self) -> tuple[str, ...]:
        return tuple(
            sorted({item.language_class for item in self.signatures})
        )

    def contains(self, signature: ExecutionSignature) -> bool:
        return signature in self.signatures

    def covers(self, other: "ShapeEnvelope") -> bool:
        """Return explicit signature-set inclusion."""

        return set(other.signatures).issubset(set(self.signatures))


@dataclass(frozen=True)
class PopulationContract:
    language_distribution: str
    arrival_regime: str
    duration_bucket: str
    queue_depth_bucket: str
    session_age_bucket: str

    def __post_init__(self) -> None:
        if any(not value for value in asdict(self).values()):
            raise ValueError("population contract fields must be non-empty")


@dataclass(frozen=True)
class ServiceContract:
    deadline_seconds: float = 2.0
    allowed_risk: float = 0.005
    p99_guard_seconds: float = 0.1

    def __post_init__(self) -> None:
        if not math.isfinite(self.deadline_seconds) or self.deadline_seconds <= 0:
            raise ValueError("deadline must be finite and positive")
        if not 0 <= self.allowed_risk < 1:
            raise ValueError("allowed risk must lie in [0,1)")
        if (
            not math.isfinite(self.p99_guard_seconds)
            or self.p99_guard_seconds < 0
        ):
            raise ValueError("P99 guard must be finite and non-negative")


@dataclass(frozen=True)
class RuntimeContract:
    identity: ExecutionIdentity
    envelope: ShapeEnvelope
    population: PopulationContract
    service: ServiceContract
    chunk_policy: str
    maximum_generation_tokens: int

    def __post_init__(self) -> None:
        if not self.chunk_policy or self.maximum_generation_tokens < 1:
            raise ValueError("invalid revision contract")

    @property
    def digest(self) -> str:
        return _digest(asdict(self))


@dataclass(frozen=True)
class PositiveCertificate:
    contract_digest: str
    threshold: float
    upper_risk: float
    evidence_count: int
    identity_digest: str
    issued_policy_epoch: int

    def __post_init__(self) -> None:
        if self.threshold < 0 or not 0 <= self.upper_risk <= 1:
            raise ValueError("invalid certificate")
        if self.evidence_count < 1 or self.issued_policy_epoch < 1:
            raise ValueError("certificate metadata must be positive")


@dataclass(frozen=True)
class FailureRecord:
    failure_id: str
    identity_digest: str
    signature: ExecutionSignature
    margin: float
    batched_projection_hash: str
    canonical_projection_hash: str
    source_contract_digest: str

    def __post_init__(self) -> None:
        if not self.failure_id or not self.source_contract_digest:
            raise ValueError("failure identity must be non-empty")
        if self.margin < 0:
            raise ValueError("failure margin cannot be negative")
        if self.batched_projection_hash == self.canonical_projection_hash:
            raise ValueError("failure projections must disagree")

    def applies_to(self, contract: RuntimeContract) -> bool:
        return (
            self.identity_digest == contract.identity.digest
            and contract.envelope.contains(self.signature)
        )


class EvidenceStatus(str, Enum):
    EXACT_RESTORE = "exact_restore_canary"
    WARM_START = "conservative_warm_start"
    QUARANTINE = "quarantine_all_verify"


@dataclass(frozen=True)
class EvidenceDecision:
    status: EvidenceStatus
    contract_digest: str
    initial_threshold: float | None
    failure_floor: float | None
    source_contract_digest: str | None
    certified: bool
    reason: str


class ContractEvidenceMemory:
    """Asymmetric certificate cache and contextual counterexample ledger."""

    def __init__(
        self,
        *,
        failure_epsilon: float = 1e-6,
        renewal_canaries: int = 64,
    ) -> None:
        if failure_epsilon <= 0 or renewal_canaries < 1:
            raise ValueError("invalid evidence lifecycle configuration")
        self.failure_epsilon = failure_epsilon
        self.renewal_canaries = renewal_canaries
        self._contracts: dict[str, RuntimeContract] = {}
        self._certificates: dict[str, PositiveCertificate] = {}
        self._failures: dict[str, FailureRecord] = {}
        self._canaries_remaining: dict[str, int] = {}
        self.unsafe_positive_reuse_attempts = 0

    def remember_contract(self, contract: RuntimeContract) -> None:
        self._contracts[contract.digest] = contract

    def store_certificate(
        self,
        contract: RuntimeContract,
        certificate: PositiveCertificate,
    ) -> None:
        if certificate.contract_digest != contract.digest:
            raise ValueError("certificate is not bound to this exact contract")
        if certificate.identity_digest != contract.identity.digest:
            raise ValueError("certificate execution identity mismatch")
        self.remember_contract(contract)
        self._certificates[contract.digest] = certificate

    def record_failure(self, failure: FailureRecord) -> None:
        self._failures[failure.failure_id] = failure

    def applicable_failures(
        self, contract: RuntimeContract
    ) -> tuple[FailureRecord, ...]:
        return tuple(
            failure
            for failure in self._failures.values()
            if failure.applies_to(contract)
        )

    def failure_floor(self, contract: RuntimeContract) -> float | None:
        applicable = self.applicable_failures(contract)
        if not applicable:
            return None
        return max(item.margin for item in applicable) + self.failure_epsilon

    def enter(self, contract: RuntimeContract) -> EvidenceDecision:
        self.remember_contract(contract)
        floor = self.failure_floor(contract)
        exact = self._certificates.get(contract.digest)
        if exact is not None:
            threshold = max(
                exact.threshold,
                floor if floor is not None else exact.threshold,
            )
            self._canaries_remaining[contract.digest] = self.renewal_canaries
            return EvidenceDecision(
                EvidenceStatus.EXACT_RESTORE,
                contract.digest,
                threshold,
                floor,
                exact.contract_digest,
                False,
                "exact certificate restored as a canary-gated warm state",
            )

        covering: list[tuple[PositiveCertificate, RuntimeContract]] = []
        for digest, certificate in self._certificates.items():
            donor = self._contracts[digest]
            if (
                donor.identity.digest == contract.identity.digest
                and donor.envelope.covers(contract.envelope)
            ):
                covering.append((certificate, donor))
        if covering:
            donor_certificate, donor_contract = min(
                covering,
                key=lambda item: (
                    item[0].threshold,
                    item[0].upper_risk,
                    item[0].contract_digest,
                ),
            )
            threshold = max(
                donor_certificate.threshold,
                floor
                if floor is not None
                else donor_certificate.threshold,
            )
            self._canaries_remaining[contract.digest] = self.renewal_canaries
            return EvidenceDecision(
                EvidenceStatus.WARM_START,
                contract.digest,
                threshold,
                floor,
                donor_contract.digest,
                False,
                "covering evidence supplies only a conservative warm start",
            )

        self._canaries_remaining[contract.digest] = self.renewal_canaries
        return EvidenceDecision(
            EvidenceStatus.QUARANTINE,
            contract.digest,
            floor,
            floor,
            None,
            False,
            "unknown contract is isolated and all state entries are verified",
        )

    def observe_canary(
        self,
        contract: RuntimeContract,
        *,
        state_error: bool,
        margin: float,
        signature: ExecutionSignature | None = None,
    ) -> int:
        if state_error:
            if signature is None:
                raise ValueError(
                    "a failed canary requires its observed execution signature"
                )
            if not contract.envelope.contains(signature):
                raise ValueError(
                    "failed canary signature is outside the active contract"
                )
            failure = FailureRecord(
                failure_id=_digest(
                    {
                        "contract": contract.digest,
                        "margin": margin,
                        "signature": asdict(signature),
                        "count": len(self._failures),
                    }
                ),
                identity_digest=contract.identity.digest,
                signature=signature,
                margin=margin,
                batched_projection_hash="observed-batched",
                canonical_projection_hash="observed-canonical",
                source_contract_digest=contract.digest,
            )
            self.record_failure(failure)
            self._canaries_remaining[contract.digest] = self.renewal_canaries
        else:
            self._canaries_remaining[contract.digest] = max(
                0, self._canaries_remaining.get(contract.digest, 0) - 1
            )
        return self._canaries_remaining[contract.digest]

    def canaries_remaining(self, contract: RuntimeContract) -> int:
        return self._canaries_remaining.get(
            contract.digest, self.renewal_canaries
        )


class AdmissionLevel(str, Enum):
    RISK_LIMITED = "risk_limited_fast_path"
    STRICT = "canonical_consistent_strict"
    RESHAPE = "capacity_reshape"
    REJECT = "backpressure_reject"


@dataclass(frozen=True)
class AdmissionDecision:
    level: AdmissionLevel
    admitted: bool
    predicted_p99_seconds: float
    guarded_p99_seconds: float
    upper_risk: float
    admitted_concurrency: int | None
    reason: str


@dataclass(frozen=True)
class ReshapeCandidate:
    """A measured capacity region bound to an exact risk certificate."""

    contract_digest: str
    concurrency: int
    predicted_p99_seconds: float
    certificate: PositiveCertificate

    def __post_init__(self) -> None:
        if not self.contract_digest:
            raise ValueError("reshape contract digest must be non-empty")
        if self.concurrency < 1 or self.predicted_p99_seconds < 0:
            raise ValueError("invalid reshape capacity estimate")
        if self.certificate.contract_digest != self.contract_digest:
            raise ValueError(
                "reshape certificate is not bound to the candidate contract"
            )


def joint_risk_slo_admission(
    contract: RuntimeContract,
    *,
    predicted_p99_seconds: float,
    upper_risk: float,
    strict_predicted_p99_seconds: float | None = None,
    reshape_candidates: Iterable[ReshapeCandidate] = (),
) -> AdmissionDecision:
    """Four-level degradation funnel with safety before throughput."""

    if predicted_p99_seconds < 0 or not 0 <= upper_risk <= 1:
        raise ValueError("invalid admission estimate")
    guarded = predicted_p99_seconds + contract.service.p99_guard_seconds
    if (
        upper_risk <= contract.service.allowed_risk
        and guarded <= contract.service.deadline_seconds
    ):
        return AdmissionDecision(
            AdmissionLevel.RISK_LIMITED,
            True,
            predicted_p99_seconds,
            guarded,
            upper_risk,
            max(contract.envelope.batch_sizes),
            "risk and guarded P99 budgets both hold",
        )
    if strict_predicted_p99_seconds is not None:
        strict_guarded = (
            strict_predicted_p99_seconds + contract.service.p99_guard_seconds
        )
        if strict_guarded <= contract.service.deadline_seconds:
            return AdmissionDecision(
                AdmissionLevel.STRICT,
                True,
                strict_predicted_p99_seconds,
                strict_guarded,
                0.0,
                max(contract.envelope.batch_sizes),
                "risk evidence unavailable; canonical-consistent strict path",
            )
    feasible = sorted(
        (
            candidate
            for candidate in reshape_candidates
            if candidate.certificate.upper_risk
            <= contract.service.allowed_risk
            and candidate.predicted_p99_seconds
            + contract.service.p99_guard_seconds
            <= contract.service.deadline_seconds
        ),
        key=lambda candidate: (
            candidate.concurrency,
            -candidate.predicted_p99_seconds,
        ),
        reverse=True,
    )
    if feasible:
        candidate = feasible[0]
        concurrency = candidate.concurrency
        p99 = candidate.predicted_p99_seconds
        return AdmissionDecision(
            AdmissionLevel.RESHAPE,
            True,
            p99,
            p99 + contract.service.p99_guard_seconds,
            candidate.certificate.upper_risk,
            concurrency,
            "offered contract exceeds capacity; reshape to a risk-certified "
            "measured region",
        )
    return AdmissionDecision(
        AdmissionLevel.REJECT,
        False,
        predicted_p99_seconds,
        guarded,
        upper_risk,
        None,
        "no safe capacity region remains; apply backpressure",
    )


@dataclass(frozen=True)
class EpochTicket:
    session_id: str
    revision_id: str
    parent_version: int
    next_version: int
    contract_epoch: int
    policy_epoch: int


class EpochFencedCommitLedger:
    """Session, contract, and policy version fence for state entry."""

    def __init__(self) -> None:
        self._session_versions: dict[str, int] = {}
        self._issued: set[str] = set()
        self._committed: set[str] = set()
        self.contract_epoch = 0
        self.policy_epoch = 0

    def register(self, session_id: str) -> None:
        if not session_id or session_id in self._session_versions:
            raise ValueError("session must be new and non-empty")
        self._session_versions[session_id] = 0

    def change_contract(self) -> tuple[int, int]:
        self.contract_epoch += 1
        self.policy_epoch += 1
        return self.contract_epoch, self.policy_epoch

    def change_policy(self) -> int:
        self.policy_epoch += 1
        return self.policy_epoch

    def issue(self, session_id: str, revision_id: str) -> EpochTicket:
        if session_id not in self._session_versions:
            raise KeyError(session_id)
        if not revision_id or revision_id in self._issued:
            raise ValueError("revision must be new and non-empty")
        parent = self._session_versions[session_id]
        self._issued.add(revision_id)
        return EpochTicket(
            session_id,
            revision_id,
            parent,
            parent + 1,
            self.contract_epoch,
            self.policy_epoch,
        )

    def can_commit(self, ticket: EpochTicket) -> bool:
        return (
            ticket.revision_id in self._issued
            and ticket.revision_id not in self._committed
            and self._session_versions.get(ticket.session_id)
            == ticket.parent_version
            and ticket.contract_epoch == self.contract_epoch
            and ticket.policy_epoch == self.policy_epoch
        )

    def commit(self, ticket: EpochTicket) -> int:
        if not self.can_commit(ticket):
            raise ValueError("stale session, contract, or policy result")
        self._session_versions[ticket.session_id] = ticket.next_version
        self._committed.add(ticket.revision_id)
        return ticket.next_version

    def version(self, session_id: str) -> int:
        """Return the committed session version, never a speculative version."""

        if session_id not in self._session_versions:
            raise KeyError(session_id)
        return self._session_versions[session_id]

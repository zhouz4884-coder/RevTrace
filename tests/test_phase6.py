from __future__ import annotations

import pytest

from revtrace.phase6 import (
    AdmissionLevel,
    ContractEvidenceMemory,
    EpochFencedCommitLedger,
    EvidenceStatus,
    ExecutionIdentity,
    ExecutionSignature,
    FailureRecord,
    PopulationContract,
    PositiveCertificate,
    ReshapeCandidate,
    RuntimeContract,
    ServiceContract,
    ShapeEnvelope,
    joint_risk_slo_admission,
)


def identity() -> ExecutionIdentity:
    return ExecutionIdentity(
        "model", "processor", "runtime", "driver-kernel", "float16",
        "sm86", "fp16-singleton-v1",
    )


def contract(
    *,
    batch: tuple[int, ...] = (16,),
    language: tuple[str, ...] = ("English",),
    arrival: str = "poisson",
) -> RuntimeContract:
    return RuntimeContract(
        identity(),
        ShapeEnvelope(
            tuple(
                ExecutionSignature(
                    batch_size,
                    4096,
                    "p25",
                    "homogeneous",
                    language_class,
                    "r0-r16",
                )
                for batch_size in batch
                for language_class in language
            )
        ),
        PopulationContract(
            "+".join(language), arrival, "d30", "q0-q16", "young",
        ),
        ServiceContract(2.0, 0.005, 0.1),
        "2s-k5",
        32,
    )


def certificate(item: RuntimeContract, threshold: float = 0.05):
    return PositiveCertificate(
        item.digest, threshold, 0.004, 1500, item.identity.digest, 1
    )


def failure(item: RuntimeContract, margin: float = 0.109375):
    return FailureRecord(
        "known-c32-zh",
        item.identity.digest,
        ExecutionSignature(
            max(item.envelope.batch_sizes),
            4096,
            "p25",
            "homogeneous",
            item.envelope.language_classes[0],
            "r0-r16",
        ),
        margin,
        "batch",
        "canonical",
        item.digest,
    )


def test_exact_certificate_restores_only_behind_canaries() -> None:
    memory = ContractEvidenceMemory(renewal_canaries=2)
    c16 = contract()
    memory.store_certificate(c16, certificate(c16))
    decision = memory.enter(c16)
    assert decision.status == EvidenceStatus.EXACT_RESTORE
    assert not decision.certified
    assert memory.observe_canary(c16, state_error=False, margin=1.0) == 1
    assert memory.observe_canary(c16, state_error=False, margin=1.0) == 0


def test_positive_evidence_is_not_unsafely_reused() -> None:
    memory = ContractEvidenceMemory()
    c16 = contract()
    c32_zh = contract(batch=(32,), language=("Chinese",), arrival="burst")
    memory.store_certificate(c16, certificate(c16))
    decision = memory.enter(c32_zh)
    assert decision.status == EvidenceStatus.QUARANTINE
    assert decision.source_contract_digest is None
    assert memory.unsafe_positive_reuse_attempts == 0


def test_covering_evidence_is_only_a_warm_start() -> None:
    memory = ContractEvidenceMemory()
    covering = contract(batch=(8, 16), language=("English",))
    target = contract(batch=(8,), language=("English",))
    memory.store_certificate(covering, certificate(covering, 0.075))
    decision = memory.enter(target)
    assert decision.status == EvidenceStatus.WARM_START
    assert not decision.certified
    assert decision.initial_threshold == 0.075


def test_contextual_failure_persists_only_in_applicability_cone() -> None:
    memory = ContractEvidenceMemory(failure_epsilon=1e-6)
    c32_zh = contract(batch=(32,), language=("Chinese",), arrival="burst")
    c16_en = contract()
    memory.record_failure(failure(c32_zh))
    assert memory.failure_floor(c32_zh) == pytest.approx(0.109376)
    assert memory.failure_floor(c16_en) is None


def test_failed_canary_requires_the_observed_signature() -> None:
    memory = ContractEvidenceMemory(renewal_canaries=2)
    c32_zh = contract(batch=(32,), language=("Chinese",), arrival="burst")
    memory.enter(c32_zh)
    with pytest.raises(ValueError, match="execution signature"):
        memory.observe_canary(c32_zh, state_error=True, margin=0.109375)
    signature = ExecutionSignature(
        32, 4096, "p25", "homogeneous", "Chinese", "r0-r16"
    )
    assert (
        memory.observe_canary(
            c32_zh,
            state_error=True,
            margin=0.109375,
            signature=signature,
        )
        == 2
    )
    assert memory.failure_floor(c32_zh) == pytest.approx(0.109376)


def test_joint_admission_reshapes_overload() -> None:
    c64 = contract(batch=(64,))
    c16 = contract(batch=(16,))
    c32 = contract(batch=(32,))
    decision = joint_risk_slo_admission(
        c64,
        predicted_p99_seconds=2.889,
        upper_risk=0.0049,
        reshape_candidates=(
            ReshapeCandidate(c16.digest, 16, 1.406, certificate(c16)),
            ReshapeCandidate(c32.digest, 32, 2.7, certificate(c32)),
        ),
    )
    assert decision.level == AdmissionLevel.RESHAPE
    assert decision.admitted_concurrency == 16
    assert decision.guarded_p99_seconds < 2.0


def test_unobserved_cartesian_combination_cannot_warm_start() -> None:
    memory = ContractEvidenceMemory()
    observed = RuntimeContract(
        identity(),
        ShapeEnvelope(
            (
                ExecutionSignature(
                    16, 4096, "p25", "homogeneous", "English", "r0-r16"
                ),
                ExecutionSignature(
                    32, 4096, "p25", "homogeneous", "Chinese", "r0-r16"
                ),
            )
        ),
        PopulationContract("EN+ZH", "mixed", "d30", "q0-q32", "young"),
        ServiceContract(2.0, 0.005, 0.1),
        "2s-k5",
        32,
    )
    unseen = contract(batch=(16,), language=("Chinese",))
    memory.store_certificate(observed, certificate(observed))
    decision = memory.enter(unseen)
    assert decision.status == EvidenceStatus.QUARANTINE


def test_uncertified_reshape_candidate_cannot_admit() -> None:
    offered = contract(batch=(64,))
    c16 = contract(batch=(16,))
    unsafe = PositiveCertificate(
        c16.digest, 0.05, 0.02, 1500, c16.identity.digest, 1
    )
    decision = joint_risk_slo_admission(
        offered,
        predicted_p99_seconds=2.889,
        upper_risk=0.0049,
        reshape_candidates=(
            ReshapeCandidate(c16.digest, 16, 1.406, unsafe),
        ),
    )
    assert decision.level == AdmissionLevel.REJECT


def test_joint_admission_rejects_when_no_capacity_exists() -> None:
    c64 = contract(batch=(64,))
    decision = joint_risk_slo_admission(
        c64,
        predicted_p99_seconds=2.889,
        upper_risk=0.0049,
    )
    assert decision.level == AdmissionLevel.REJECT
    assert not decision.admitted


def test_contract_and_policy_epoch_fence_stale_results() -> None:
    ledger = EpochFencedCommitLedger()
    ledger.register("s0")
    ledger.change_contract()
    stale_contract = ledger.issue("s0", "r0")
    ledger.change_contract()
    assert not ledger.can_commit(stale_contract)

    current = ledger.issue("s0", "r1")
    ledger.change_policy()
    assert not ledger.can_commit(current)
    with pytest.raises(ValueError, match="stale"):
        ledger.commit(current)


def test_competing_results_linearize_at_one_parent_version() -> None:
    ledger = EpochFencedCommitLedger()
    ledger.register("s-linear")
    first = ledger.issue("s-linear", "r-first")
    competing = ledger.issue("s-linear", "r-competing")

    assert first.parent_version == competing.parent_version == 0
    assert ledger.commit(first) == 1
    assert ledger.version("s-linear") == 1
    assert not ledger.can_commit(competing)
    with pytest.raises(ValueError, match="stale"):
        ledger.commit(competing)

    successor = ledger.issue("s-linear", "r-successor")
    assert successor.parent_version == 1
    assert ledger.commit(successor) == 2
    assert ledger.version("s-linear") == 2

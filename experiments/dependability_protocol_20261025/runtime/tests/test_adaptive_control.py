from __future__ import annotations

from dataclasses import asdict

import pytest

from revtrace.control import (
    AdaptiveCertificationController,
    AuditChannel,
    ContractFingerprint,
    ControlMode,
    ControllerConfig,
    IdleAuditCandidate,
    select_idle_audits,
)


def fingerprint(*, model: str = "model-a", concurrency: str = "c16"):
    return ContractFingerprint(
        model_sha256=model,
        tokenizer_sha256="tokenizer-a",
        runtime="vllm-test",
        precision="float16",
        kernel_backend="flash-attention",
        concurrency_class=concurrency,
        chunk_policy="2s-k5",
        canonical_path="fp16-singleton",
    )


def controller(*, quarantine: int = 0):
    return AdaptiveCertificationController(
        ControllerConfig(
            delta=0.20,
            alpha=0.05,
            audit_probability=0.50,
            minimum_base_audits=20,
            policy_thresholds=(0.0, 0.10),
            drift_quarantine_events=quarantine,
            control_interval_events=1,
        ),
        seed=7,
    )


def calibrate(ctrl: AdaptiveCertificationController) -> None:
    for index in range(100):
        decision = ctrl.decide(
            minimum_margin=0.20,
            terminal=False,
            base_audit_draw=0.0 if index % 2 == 0 else 0.9,
        )
        ctrl.observe(
            decision,
            state_error=False if decision.verify else None,
        )


def test_fingerprint_is_stable_and_epoch_change_invalidates_evidence() -> None:
    ctrl = controller()
    first = fingerprint()
    assert first.digest == fingerprint().digest
    ctrl.start_epoch(first, reason="initial")
    calibrate(ctrl)
    assert any(item.certified for item in ctrl.certificates())

    ctrl.start_epoch(
        fingerprint(concurrency="c64"), reason="concurrency contract changed"
    )
    snapshot = ctrl.snapshot()
    assert snapshot.epoch == 2
    assert snapshot.mode == ControlMode.WARMUP.value
    assert snapshot.base_audits == 0
    assert not any(item["certified"] for item in snapshot.certificates)


def test_idle_audits_never_enter_formal_confidence_sequence() -> None:
    ctrl = controller()
    ctrl.start_epoch(fingerprint(), reason="initial")
    calibrate(ctrl)
    before = ctrl.snapshot()

    decision = ctrl.decide(
        minimum_margin=0.20,
        terminal=False,
        idle_capacity=True,
        base_audit_draw=0.9,
    )
    assert decision.audit_channel == AuditChannel.IDLE
    ctrl.observe(decision, state_error=True)
    after = ctrl.snapshot()

    assert after.idle_audits == before.idle_audits + 1
    assert after.caught_idle_state_errors == 1
    assert after.base_audits == before.base_audits
    for old, new in zip(before.certificates, after.certificates):
        assert new["caught_state_errors"] == old["caught_state_errors"]


def test_caught_drift_automatically_removes_unsafe_policy() -> None:
    ctrl = controller()
    ctrl.start_epoch(fingerprint(), reason="initial")
    calibrate(ctrl)
    safe = ctrl.decide(
        minimum_margin=0.20,
        terminal=False,
        base_audit_draw=0.9,
    )
    assert safe.mode == ControlMode.ACTIVE
    assert safe.threshold == 0.0
    ctrl.observe(safe, state_error=None)

    caught = ctrl.decide(
        minimum_margin=0.05,
        terminal=False,
        base_audit_draw=0.0,
    )
    assert caught.audit_channel == AuditChannel.BASE
    ctrl.observe(caught, state_error=True)

    repaired = ctrl.decide(
        minimum_margin=0.20,
        terminal=False,
        base_audit_draw=0.9,
    )
    assert repaired.threshold == 0.10
    assert repaired.mode == ControlMode.ACTIVE
    assert ctrl.snapshot().caught_base_state_errors == 1

    ctrl.start_epoch(fingerprint(), reason="same contract restarted")
    calibrate(ctrl)
    repeated = ctrl.decide(
        minimum_margin=0.20,
        terminal=False,
        base_audit_draw=0.9,
    )
    assert repeated.threshold == 0.10
    assert ctrl.snapshot().frozen_failure_margin_floor == 0.05


def test_terminal_and_uncertified_epochs_fail_closed() -> None:
    ctrl = controller()
    ctrl.start_epoch(fingerprint(), reason="initial")
    warmup = ctrl.decide(
        minimum_margin=1.0,
        terminal=False,
        base_audit_draw=0.9,
    )
    terminal = ctrl.decide(
        minimum_margin=1.0,
        terminal=True,
        base_audit_draw=0.9,
    )
    assert warmup.verify
    assert "fail closed" in warmup.reason
    assert terminal.verify
    assert "terminal" in terminal.reason


def test_stale_epoch_decision_is_rejected() -> None:
    ctrl = controller()
    ctrl.start_epoch(fingerprint(), reason="initial")
    stale = ctrl.decide(
        minimum_margin=0.2,
        terminal=False,
        base_audit_draw=0.0,
    )
    ctrl.start_epoch(fingerprint(model="model-b"), reason="model changed")
    with pytest.raises(ValueError, match="stale decision"):
        ctrl.observe(stale, state_error=False)


def test_snapshot_is_machine_serializable() -> None:
    ctrl = controller()
    ctrl.start_epoch(fingerprint(), reason="initial")
    payload = asdict(ctrl.snapshot())
    assert payload["fingerprint"] == fingerprint().digest
    assert payload["certificates"][0]["upper_risk"] == 1.0


def test_idle_audit_scheduler_respects_priority_and_voi() -> None:
    candidates = [
        IdleAuditCandidate("low", 0.1, 1.0, 1.0, 1.0),
        IdleAuditCandidate("high", 0.8, 2.0, 1.0, 1.0),
        IdleAuditCandidate(
            "base", 1.0, 5.0, 1.0, 0.5, base_audit=True
        ),
        IdleAuditCandidate(
            "terminal", 1.0, 5.0, 1.0, 0.5, terminal=True
        ),
    ]
    selected = select_idle_audits(candidates, capacity_seconds=1.0)
    assert [item.revision_id for item in selected] == ["high"]

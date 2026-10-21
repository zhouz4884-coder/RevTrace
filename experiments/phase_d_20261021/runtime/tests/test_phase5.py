from __future__ import annotations

from revtrace.phase5 import (
    AsymmetricLiveRiskWindowController,
    LiveRiskWindowController,
    adaptation_regret,
    contamination_damage,
    pair_digest,
    release_aware_audit_admissible,
    summarize_energy,
)


def test_contract_switch_invalidates_old_evidence() -> None:
    controller = LiveRiskWindowController(minimum_audits=4)
    first = controller.switch("c16")
    for margin in (1.0, 1.1, 1.2, 1.3):
        controller.observe(minimum_margin=margin, state_error=False)
    assert first.audit_records
    second = controller.switch("c64")
    assert controller.fail_closed
    assert second.audit_records == []
    assert second.threshold is None
    assert controller.requires_verification(
        minimum_margin=100.0, terminal=False
    )


def test_terminal_is_always_verified() -> None:
    controller = LiveRiskWindowController(minimum_audits=4)
    controller.switch("c16")
    for margin in (1.0, 1.1, 1.2, 1.3):
        controller.observe(minimum_margin=margin, state_error=False)
    assert controller.requires_verification(
        minimum_margin=100.0, terminal=True
    )


def test_asymmetric_memory_restores_exact_contract_only() -> None:
    controller = AsymmetricLiveRiskWindowController(
        minimum_audits=4, renewal_canaries=2, delta=0.9
    )
    first = controller.switch("c16-en")
    for margin in (1.0, 1.1, 1.2, 1.3):
        controller.observe(minimum_margin=margin, state_error=False)
    assert first.certificate is not None

    controller.switch("c16-zh")
    assert controller.fail_closed
    assert controller.switch_status == "new_contract_quarantine"

    returned = controller.switch("c16-en")
    assert controller.fail_closed
    assert controller.switch_status == "exact_restore_canary"
    controller.observe(minimum_margin=1.0, state_error=False)
    assert controller.fail_closed
    controller.observe(minimum_margin=1.0, state_error=False)
    assert returned.certificate is not None
    assert controller.switch_status == "exact_restore_promoted"
    assert controller.cross_contract_certificate_reuse == 0


def test_asymmetric_failure_floor_persists_per_contract() -> None:
    controller = AsymmetricLiveRiskWindowController(
        minimum_audits=4, renewal_canaries=2, failure_epsilon=1e-6
    )
    controller.seed_failure("c32-zh", 0.109375)
    assert controller.failure_floor("c32-zh") == 0.109376
    assert controller.failure_floor("c16-en") is None


def test_active_counterexample_tightens_a_still_valid_certificate() -> None:
    controller = AsymmetricLiveRiskWindowController(
        minimum_audits=4, renewal_canaries=2, delta=0.9
    )
    epoch = controller.switch("c16-en")
    for margin in (1.0, 1.1, 1.2, 1.3):
        controller.observe(minimum_margin=margin, state_error=False)
    assert epoch.certificate is not None

    adjusted = controller.observe(
        minimum_margin=0.2, state_error=True
    )
    assert adjusted is not None
    assert adjusted.certified
    assert not controller.fail_closed
    assert epoch.certificate is adjusted
    assert epoch.threshold is not None and epoch.threshold > 0.2
    assert controller.failure_floor("c16-en") == 0.200001


def test_restore_canary_failure_removes_cached_certificate() -> None:
    controller = AsymmetricLiveRiskWindowController(
        minimum_audits=4, renewal_canaries=2, delta=0.9
    )
    controller.switch("c16-en")
    for margin in (1.0, 1.1, 1.2, 1.3):
        controller.observe(minimum_margin=margin, state_error=False)
    controller.switch("c16-zh")
    returned = controller.switch("c16-en")
    assert controller.switch_status == "exact_restore_canary"
    controller.observe(minimum_margin=0.2, state_error=True)
    assert returned.certificate is None
    assert controller.fail_closed
    controller.switch("c16-zh")
    controller.switch("c16-en")
    assert controller.switch_status == "new_contract_quarantine"


def test_quarantine_counterexample_is_retained_as_learning_evidence() -> None:
    controller = AsymmetricLiveRiskWindowController(
        minimum_audits=4, renewal_canaries=2, delta=0.9
    )
    epoch = controller.switch("c16-zh")
    controller.observe(minimum_margin=0.2, state_error=True)
    assert epoch.audit_records == [
        {"minimum_margin": 0.2, "state_error": True}
    ]
    for margin in (1.0, 1.1, 1.2):
        controller.observe(minimum_margin=margin, state_error=False)
    assert len(epoch.audit_records) == 4
    assert epoch.certificate is not None
    assert epoch.threshold is not None
    assert epoch.threshold > 0.2


def test_slack_admission_is_strict() -> None:
    assert release_aware_audit_admissible(
        now=1.0,
        verifier_backlog_seconds=0.1,
        audit_p99_seconds=0.3,
        guard_seconds=0.1,
        next_mandatory_release=2.0,
    )
    assert not release_aware_audit_admissible(
        now=1.0,
        verifier_backlog_seconds=0.5,
        audit_p99_seconds=0.4,
        guard_seconds=0.1,
        next_mandatory_release=2.0,
    )


def test_phase5_metrics() -> None:
    assert adaptation_regret([2.0], [3.0], [4.0]) == 4.0
    assert contamination_damage(
        state_disagreement=True,
        raf=3.0,
        persistent=True,
        terminal_difference=True,
    ) == 12.0
    assert pair_digest({"b": 2, "a": 1}) == pair_digest(
        {"a": 1, "b": 2}
    )
    energy = summarize_energy(
        [
            {"time": 0.0, "power_watts": 100.0},
            {"time": 2.0, "power_watts": 100.0},
        ],
        completed_audio_seconds=20.0,
    )
    assert energy["joules"] == 200.0
    assert energy["joules_per_audio_second"] == 10.0

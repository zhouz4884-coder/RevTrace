from __future__ import annotations

from revtrace.phase5 import (
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

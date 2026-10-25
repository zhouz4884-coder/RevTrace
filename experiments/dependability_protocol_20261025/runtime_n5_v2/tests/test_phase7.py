from revtrace.phase7 import (
    LLM42StyleRevisionPolicy,
    MarginGateInspiredRevisionPolicy,
    OwnerVersionOnlyState,
    ablation_rows,
    evaluate_threshold,
    failure_floor_threshold,
    minimum_zero_error_samples,
    one_sided_binomial_upper,
    sota_rows,
)


def test_risk_sample_sizes() -> None:
    assert minimum_zero_error_samples(0.0025) == 1197
    assert minimum_zero_error_samples(0.005) == 598
    assert minimum_zero_error_samples(0.01) == 299
    assert one_sided_binomial_upper(1, 960) < 0.005


def test_failure_floor_catches_known_counterexample() -> None:
    threshold = failure_floor_threshold(
        [{"minimum_margin": 0.109375, "state_error": True}]
    )
    result = evaluate_threshold(
        [
            {"minimum_margin": 0.109375, "state_error": True},
            {"minimum_margin": 1.0, "state_error": False},
        ],
        threshold,
    )
    assert result["unsafe_fast_path_events"] == 0


def test_sota_guarantees_are_not_conflated() -> None:
    rows = {row["mechanism"]: row for row in sota_rows()}
    assert rows["owner/version-only state"]["rejects_stale_or_wrong_epoch"]
    assert not rows["owner/version-only state"]["replay_determinism"]
    assert rows["RevTrace risk-limited"]["adaptive_evidence"]
    assert not rows["RevTrace risk-limited"]["replay_determinism"]


def test_ablation_is_monotone_on_frozen_counterexamples() -> None:
    rows = ablation_rows()
    assert rows[0]["known_failure_recurrence"] == 1
    assert rows[-1]["known_failure_recurrence"] == 0
    assert rows[-1]["stale_commit"] == 0


def test_margin_gate_inspired_misses_known_legal_flip() -> None:
    policy = MarginGateInspiredRevisionPolicy(threshold=0.05)
    assert not policy.requires_canonical(margin=0.109375, terminal=False)


def test_owner_version_accepts_legal_numerical_flip() -> None:
    state = OwnerVersionOnlyState(owner="session-1")
    assert state.commit(owner="session-1", parent_version=0)


def test_llm42_style_verifies_every_feedback_transition() -> None:
    policy = LLM42StyleRevisionPolicy()
    assert policy.requires_canonical(terminal=False)

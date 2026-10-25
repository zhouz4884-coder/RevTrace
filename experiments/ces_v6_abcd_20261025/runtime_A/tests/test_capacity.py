from __future__ import annotations

from revtrace.capacity import (
    age_bucket_summary,
    build_cluster_aware_certificate,
    classify_slow_round,
    one_sided_t_upper,
)


def test_cross_seed_upper_bound_exceeds_mean() -> None:
    values = [1.80, 1.82, 1.84, 1.86, 1.88]
    assert one_sided_t_upper(values) > sum(values) / len(values)


def test_cluster_aware_certificate_accepts_guarded_contract() -> None:
    seeds = []
    for seed, p99 in enumerate([1.70, 1.72, 1.74, 1.71, 1.73]):
        rounds = [
            {
                "state_entry_latency_seconds": p99 - 0.05,
                "terminal": index == 1,
                "verified_count": 12 if index == 1 else 2,
                "verification_overlap_fraction": 1.0 if index == 1 else 1 / 6,
            }
            for index in range(2)
        ]
        seeds.append(
            {
                "seed": seed,
                "p99_seconds": p99,
                "deadline_miss_rounds": 0,
                "deadline_miss_events": 0,
                "events": 360,
                "rounds_detail": rounds,
                "online_selection_authority_violations": 0,
            }
        )
    certificate = build_cluster_aware_certificate(
        seeds,
        contract_digest="c12",
        risk_upper_bound=0.004,
    )
    assert certificate.accepted
    assert certificate.maximum_verified_count == 12
    assert certificate.terminal_round_p99_seconds is not None
    assert certificate.terminal_seed_p99_upper_95_seconds is not None
    assert certificate.nonterminal_seed_p99_upper_95_seconds is not None
    assert len(certificate.terminal_seed_p99_seconds) == 5
    assert len(certificate.nonterminal_seed_p99_seconds) == 5


def test_cluster_aware_certificate_rejects_stratified_tail() -> None:
    seeds = []
    for seed in range(5):
        seeds.append(
            {
                "seed": seed,
                "p99_seconds": 1.7,
                "deadline_miss_rounds": 0,
                "deadline_miss_events": 0,
                "events": 10,
                "rounds_detail": [
                    {
                        "state_entry_latency_seconds": 1.6,
                        "terminal": False,
                        "verified_count": 0,
                        "verification_overlap_fraction": 0.0,
                    },
                    {
                        "state_entry_latency_seconds": 1.95,
                        "terminal": True,
                        "verified_count": 1,
                        "verification_overlap_fraction": 1.0,
                    },
                ],
                "online_selection_authority_violations": 0,
            }
        )
    certificate = build_cluster_aware_certificate(
        seeds,
        contract_digest="stratified-tail",
        risk_upper_bound=0.004,
    )
    assert not certificate.accepted
    assert (
        "maximum_terminal_seed_p99_exceeds_guarded_deadline"
        in certificate.rejection_reasons
    )


def test_cluster_aware_certificate_rejects_observed_tail() -> None:
    seeds = [
        {
            "p99_seconds": value,
            "deadline_miss_rounds": int(value > 2.0),
            "deadline_miss_events": 14 if value > 2.0 else 0,
            "events": 1260,
            "rounds": 90,
        }
        for value in (2.0277, 1.8590, 1.8611)
    ]
    certificate = build_cluster_aware_certificate(
        seeds,
        contract_digest="c14",
        risk_upper_bound=0.004,
    )
    assert not certificate.accepted
    assert "observed_deadline_miss_rounds" in certificate.rejection_reasons
    assert certificate.rounds == 270


def test_slow_round_classification_finds_serial_verification() -> None:
    assert (
        classify_slow_round(
            {
                "deadline_miss": True,
                "proposal_executed": True,
                "preverify_all": False,
                "verified_count": 2,
                "proposal_seconds": 0.8,
                "canonical_execution_seconds": 1.3,
                "verifier_collect_wall_seconds": 1.3,
            }
        )
        == "serial_proposer_then_selective_canonical"
    )


def test_age_bucket_summary_keeps_round_as_statistical_unit() -> None:
    rounds = [
        {
            "session_age_start_seconds": age,
            "state_entry_latency_seconds": 1.0 + age / 100.0,
            "deadline_miss": False,
            "verified_count": 1,
            "proposal_seconds": 0.5,
            "canonical_execution_seconds": 0.25,
            "commit_seconds": 0.01,
            "mean_selected_token_count": 8.0,
            "maximum_selected_token_count": 10,
        }
        for age in (0, 2, 30, 32, 60, 62)
    ]
    rows = age_bucket_summary(rounds)
    assert [row["age_start_seconds"] for row in rows] == [0, 30, 60]
    assert all(row["rounds"] == 2 for row in rows)
    assert all(row["mean_proposal_seconds"] == 0.5 for row in rows)
    assert all(row["maximum_selected_token_count"] == 10 for row in rows)

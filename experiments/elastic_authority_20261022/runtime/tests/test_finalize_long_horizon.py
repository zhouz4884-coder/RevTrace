from scripts.finalize_long_horizon_repair import (
    classify_rebase_decision,
    one_sided_binomial_upper,
    service_summary,
)


def test_zero_failure_upper_bound_matches_closed_form() -> None:
    observed = one_sided_binomial_upper(0, 720)
    expected = 1.0 - 0.05 ** (1.0 / 720)
    assert observed == expected
    assert observed < 0.005


def test_one_failure_exceeds_half_percent_contract() -> None:
    observed = one_sided_binomial_upper(1, 720)
    assert 0.0065 < observed < 0.0067


def test_rebase_decision_preserves_guard_failure_boundary() -> None:
    observed = classify_rebase_decision(
        strict_gate_pass=False,
        two_second_slo_pass=True,
        risk_pass=True,
        safety_pass=True,
        quality_pass=True,
    )
    assert observed == "CHECKPOINT_REBASE_SLO_RISK_PASS_GUARD_FAIL"


def test_rebase_decision_does_not_hide_other_failures() -> None:
    observed = classify_rebase_decision(
        strict_gate_pass=False,
        two_second_slo_pass=True,
        risk_pass=False,
        safety_pass=True,
        quality_pass=True,
    )
    assert observed == "CHECKPOINT_AND_REBASE_GATE_FAIL"


def test_service_summary_accepts_chunk_index_for_peak_round() -> None:
    row = {
        "chunk_index": 4,
        "state_entry_latency_seconds": 1.2,
        "session_age_end_seconds": 10,
        "terminal": False,
        "checkpoint_boundary": False,
        "verified_count": 2,
        "low_margin_count": 2,
        "prepare_seconds": 0.01,
        "proposal_seconds": 0.4,
        "canonical_execution_seconds": 0.7,
        "projection_seconds": 0.01,
        "apply_seconds": 0.01,
        "commit_seconds": 0.01,
        "critical_path_residual_seconds": 0.06,
        "cross_round_verifier_backlog": False,
        "maximum_accumulated_audio_samples": 160000,
        "maximum_model_input_token_count": 100,
        "gpu_telemetry": {},
        "deadline_miss": False,
    }
    stage = {
        "label": "heldout",
        "audit_root_state_mismatches": 0,
        "audit_events": 4,
        "threshold": 0.1,
        "risk_bound_source": "test",
        "verification_fraction": 1.0,
        "risk_upper_bound": 0.1,
        "state_entry_latency_seconds_p50": 1.2,
        "state_entry_latency_seconds_p95": 1.2,
        "state_entry_latency_seconds_p99": 1.2,
        "deadline_miss_events": 0,
        "output_violations": 0,
        "state_violations": 0,
        "online_selection_authority_violations": 0,
        "energy": {"joules_per_audio_second": 1.0},
        "rounds_detail": [
            {
                **row,
                "chunk_index": index,
                "session_age_end_seconds": age,
                "state_entry_latency_seconds": 1.2 - index * 0.1,
            }
            for index, age in enumerate((10, 40, 70, 100), start=4)
        ],
    }
    observed = service_summary(
        {"decision": "test", "stages": [stage]},
        "test",
    )
    assert observed["peak_round_decomposition"]["round_index"] == 5

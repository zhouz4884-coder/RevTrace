import importlib.util
from pathlib import Path

import pytest

from revtrace.evidence_audit import (
    audit_provisional_events,
    audit_quality_dependencies,
    validate_resume_quality,
)


RUNNER = (
    Path(__file__).resolve().parents[1]
    / "scripts"
    / "remote"
    / "run_deployed_checkpoint20_quality.py"
)
SPEC = importlib.util.spec_from_file_location("deployed_quality", RUNNER)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_append_only_resolution_has_zero_overwrite() -> None:
    assert (
        MODULE.provisional_overwrite_fraction(
            "the quick fox",
            "the quick fox jumps",
            "English",
        )
        == 0.0
    )


def test_overwrite_is_bounded() -> None:
    value = MODULE.provisional_overwrite_fraction(
        "short",
        "a completely different and longer sentence",
        "English",
    )
    assert value == 1.0


def test_empty_provisional_has_zero_overwrite() -> None:
    assert (
        MODULE.provisional_overwrite_fraction(
            "",
            "new authoritative text",
            "English",
        )
        == 0.0
    )


def test_continuous_provisional_audit_tracks_each_visible_transition() -> None:
    rows = [
        {
            "session_id": "English-00",
            "language": "English",
            "start_age_seconds": 2,
            "provisional_text": "the quick",
            "resolution_age_seconds": 6,
            "resolution": "next_high_margin",
            "authoritative_text": "the slow fox",
        },
        {
            "session_id": "English-00",
            "language": "English",
            "start_age_seconds": 4,
            "provisional_text": "the quick fox",
            "resolution_age_seconds": 6,
            "resolution": "next_high_margin",
            "authoritative_text": "the slow fox",
        },
    ]
    audit = audit_provisional_events(rows)
    assert audit["holdback_events"] == 2
    assert audit["resolution_episodes"] == 1
    assert audit["multi_holdback_episodes"] == 1
    assert audit["transition_counts"] == {
        "all": 2,
        "provisional_to_provisional": 1,
        "provisional_to_authority": 1,
    }
    assert audit["episode_burst_length"]["maximum"] == 2.0
    assert audit["episodes"][0]["cumulative_churn"] == pytest.approx(2 / 3)


def test_quality_dependency_audit_exposes_cross_session_reuse() -> None:
    audit = audit_quality_dependencies(
        [
            {
                "session_id": "English-00",
                "language": "English",
                "source_ids": ["a", "b"],
            },
            {
                "session_id": "English-01",
                "language": "English",
                "source_ids": ["b", "c"],
            },
        ]
    )
    row = audit["languages"]["English"]
    assert audit["cross_session_source_dependence"]
    assert row["within_session_duplicate_source_events"] == 0
    assert row["sources_reused_across_sessions"] == 1
    assert row["component_sizes"] == [2]
    assert (
        audit["cluster_bootstrap_status"]
        == "NOT_IDENTIFIABLE_FROM_THIS_DESIGN"
    )


def resume_fixture() -> tuple[dict, list[dict], dict]:
    deployment = {
        "proposer": "p",
        "authority": "a",
        "duration_seconds": 120,
        "checkpoint_seconds": 20,
        "margin_threshold": 0.031251,
        "sessions_per_language": 1,
    }
    expected = [
        {
            "session_id": "English-00",
            "language": "English",
            "source_ids": ["a"],
            "reference": "hello",
        }
    ]
    resumed = {
        "mechanism_digest": "m" * 64,
        "contract_manifest_sha256": "c" * 64,
        "deployment": deployment,
        "paired_sessions": [
            {
                **expected[0],
                "transcripts": {
                    "continuous": "hello",
                    "checkpoint_verify": "hello",
                },
            }
        ],
        "rounds": {"continuous": [], "checkpoint_verify": []},
        "mode_wall_seconds": {
            "continuous": 1.0,
            "checkpoint_verify": 1.0,
        },
    }
    return resumed, expected, deployment


def test_resume_quality_validation_accepts_exact_lineage() -> None:
    resumed, expected, deployment = resume_fixture()
    result = validate_resume_quality(
        resumed=resumed,
        expected_sessions=expected,
        mechanism_digest="m" * 64,
        contract_manifest_sha256="c" * 64,
        expected_deployment=deployment,
    )
    assert result["decision"] == "RESUME_QUALITY_ATTESTATION_PASS"
    assert all(result["checks"].values())


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("mechanism_digest", "x" * 64),
        ("contract_manifest_sha256", "x" * 64),
    ],
)
def test_resume_quality_validation_rejects_contract_drift(
    field: str,
    value: str,
) -> None:
    resumed, expected, deployment = resume_fixture()
    resumed[field] = value
    with pytest.raises(ValueError, match="failed checks"):
        validate_resume_quality(
            resumed=resumed,
            expected_sessions=expected,
            mechanism_digest="m" * 64,
            contract_manifest_sha256="c" * 64,
            expected_deployment=deployment,
        )


def test_resume_quality_validation_rejects_source_drift() -> None:
    resumed, expected, deployment = resume_fixture()
    resumed["paired_sessions"][0]["source_ids"] = ["other"]
    with pytest.raises(ValueError, match="source_ids_and_references"):
        validate_resume_quality(
            resumed=resumed,
            expected_sessions=expected,
            mechanism_digest="m" * 64,
            contract_manifest_sha256="c" * 64,
            expected_deployment=deployment,
        )


def test_chinese_append_is_not_revision() -> None:
    assert MODULE.provisional_overwrite_fraction("配置", "配置文件", "Chinese") == 0.0

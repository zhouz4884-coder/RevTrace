#!/usr/bin/env python3
"""Fail-closed P0-P3 attribution, c8 boundary and c16 headline finalizer."""

from __future__ import annotations

import argparse
import hashlib
import json
import statistics
from pathlib import Path
from typing import Any


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def completed_jsons(directory: Path, pattern: str) -> list[Path]:
    """Return final payloads only; resumable checkpoints are not evidence."""

    return sorted(
        path
        for path in directory.glob(pattern)
        if not path.name.endswith(".checkpoint.json")
    )


def percentile(values: list[float], fraction: float) -> float:
    values = sorted(values)
    if not values:
        raise ValueError("empty percentile input")
    index = (len(values) - 1) * fraction
    lower = int(index)
    upper = min(lower + 1, len(values) - 1)
    weight = index - lower
    return values[lower] * (1 - weight) + values[upper] * weight


def policy_contract(path: Path) -> tuple[str, dict[str, Any]]:
    row = load(path)
    return sha256(path), row["selected_policy"]


def assert_bound(
    row: dict[str, Any],
    *,
    digest: str,
    policy: dict[str, Any],
    duration: int,
    concurrency: int,
    holdback: bool,
    low_margin_policy: str | None = None,
    checkpoint_phase_policy: str = "synchronized",
) -> None:
    config = row["config"]
    assert config["policy_sha256"] == digest
    assert Path(config["policy_source"]).name
    assert int(config["duration_seconds"]) == duration
    assert int(config["concurrency"]) == concurrency
    assert config["margin_threshold"] == policy["threshold"]
    for key in (
        "age_window_index",
        "age_margin_threshold",
        "late_window_index",
        "late_margin_threshold",
        "high_load_prompt_tokens",
        "high_load_margin_threshold",
    ):
        assert config.get(key) == policy.get(key)
    assert config.get("window_margin_rules", []) == policy.get(
        "window_margin_rules", []
    )
    assert config["low_margin_policy"] == (
        low_margin_policy
        if low_margin_policy is not None
        else ("holdback" if holdback else "verify")
    )
    assert config.get(
        "checkpoint_phase_policy", "synchronized"
    ) == checkpoint_phase_policy
    assert row["metrics"]["baseline_display_goodput"] > 0


def summarize_runs(rows: list[dict[str, Any]]) -> dict[str, Any]:
    metrics = [row["metrics"] for row in rows]
    counts = [row["counts"] for row in rows]
    sched = [row["scheduler"] for row in rows]
    return {
        "runs": len(rows),
        "median_wall_speedup": statistics.median(
            row["wall_speedup"] for row in metrics
        ),
        "minimum_wall_speedup": min(row["wall_speedup"] for row in metrics),
        "median_gpu_normalized_speedup": statistics.median(
            row["gpu_normalized_speedup"] for row in metrics
        ),
        "median_display_slo_goodput_speedup": statistics.median(
            row["display_slo_goodput_speedup"] for row in metrics
        ),
        "maximum_display_p99_seconds": max(
            row["display_latency_p99"] for row in metrics
        ),
        "maximum_state_p99_seconds": max(
            row["latency_p99"] for row in metrics
        ),
        "median_energy_reduction": statistics.median(
            row["energy_reduction"] for row in metrics
        ),
        "minimum_energy_reduction": min(
            row["energy_reduction"] for row in metrics
        ),
        "maximum_verification_fraction": max(
            row["verification_fraction"] for row in metrics
        ),
        "low_margin_holdbacks": sum(
            row["low_margin_holdbacks"] for row in counts
        ),
        "state_violations": sum(row["state_violations"] for row in counts),
        "stale_commits": sum(row["stale_commits"] for row in counts),
        "deadline_misses": sum(row["deadline_misses"] for row in counts),
        "display_deadline_misses": sum(
            row["display_deadline_misses"] for row in counts
        ),
        "median_batch_occupancy": statistics.median(
            row["mean_occupancy_fraction"] for row in sched
        ),
        "maximum_pending_authorities": max(
            row["maximum_pending_authorities"] for row in sched
        ),
        "total_unfilled_batch_slots": sum(
            row["unfilled_batch_slots"] for row in sched
        ),
    }


def classify_closure(
    *, c8_gate: bool, c16_w1_gate: bool, c16_w2_gate: bool,
    c16_risk_gate: bool = True,
) -> str:
    """Keep the headline and disclosed capacity boundary logically separate."""

    if c16_w1_gate and c16_w2_gate and c16_risk_gate and c8_gate:
        return "P0_P3_STRONG_CROSS_ARCHITECTURE_CLOSURE"
    if c16_w1_gate and c16_w2_gate and c16_risk_gate:
        return "P0_P3_HEADLINE_PASS_C8_CAPACITY_BOUNDARY"
    if c16_w1_gate and c16_w2_gate:
        return "P0_P3_C16_PERFORMANCE_PASS_RISK_CONTRACT_FAIL"
    return "P0_P3_PAPER_THREATENING_C16_HEADLINE_FAIL"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir", type=Path, required=True)
    parser.add_argument("--c8-policy", type=Path, required=True)
    parser.add_argument("--c8-original-policy", type=Path)
    parser.add_argument("--c16-policy", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    parser.add_argument("--output-md", type=Path, required=True)
    args = parser.parse_args()
    root = args.input_dir
    d8, p8 = policy_contract(args.c8_policy)
    d8_original, p8_original = policy_contract(
        args.c8_original_policy or args.c8_policy
    )
    d16, p16 = policy_contract(args.c16_policy)
    final_identity = {
        Path(row["path"]).name: row["sha256"]
        for row in load(
            root / "p0" / "final_runtime_code_identity.json"
        )["files"]
    }

    p1_names = (
        "unprotected", "feedback-off", "checkpoint-only", "risk-only",
        "full-verify", "holdback-dual", "holdback-colocated",
    )
    p1 = {name: load(root / "p1" / f"{name}.json") for name in p1_names}
    for name, row in p1.items():
        assert_bound(
            row, digest=d8_original, policy=p8_original,
            duration=180, concurrency=8,
            holdback=name.startswith("holdback"),
        )
    if p1["unprotected"]["metrics"]["wall_speedup"] < 2.0:
        ceiling = "EXECUTOR_LIMIT"
    elif (
        p1["full-verify"]["metrics"]["wall_speedup"]
        < 0.8 * p1["unprotected"]["metrics"]["wall_speedup"]
    ):
        ceiling = "AUTHORITY_QUEUE_AND_BATCH_FRAGMENTATION"
    elif (
        p1["feedback-off"]["metrics"]["wall_speedup"]
        > 1.2 * p1["unprotected"]["metrics"]["wall_speedup"]
    ):
        ceiling = "FEEDBACK_STATE_COST"
    else:
        ceiling = "RESIDUAL_SCHEDULER_LOSS"
    p1_summary = {
        name: {
            "wall_speedup": row["metrics"]["wall_speedup"],
            "gpu_normalized_speedup": row["metrics"]["gpu_normalized_speedup"],
            "display_slo_goodput_speedup": row["metrics"]["display_slo_goodput_speedup"],
            "state_p99_seconds": row["metrics"]["latency_p99"],
            "display_p99_seconds": row["metrics"]["display_latency_p99"],
            "energy_reduction": row["metrics"]["energy_reduction"],
            "verification_fraction": row["metrics"]["verification_fraction"],
            "mean_batch_occupancy": row["scheduler"]["mean_occupancy_fraction"],
            "maximum_pending_authorities": row["scheduler"]["maximum_pending_authorities"],
            "unfilled_batch_slots": row["scheduler"]["unfilled_batch_slots"],
            "state_violations": row["counts"]["state_violations"],
        }
        for name, row in p1.items()
    }

    selection = load(root / "p2_staggered" / "selection.json")
    selected_topology = selection["selected"]
    staggered = {}
    for name in ("dual", "colocated"):
        path = root / "p2_staggered" / f"{name}.json"
        if path.exists():
            staggered[name] = load(path)
    for row in staggered.values():
        assert_bound(
            row, digest=d8, policy=p8, duration=180, concurrency=8,
            holdback=True, checkpoint_phase_policy="session-staggered",
        )
    for name, row in staggered.items():
        p1_summary[f"holdback-staggered-{name}"] = {
            "wall_speedup": row["metrics"]["wall_speedup"],
            "gpu_normalized_speedup": row["metrics"]["gpu_normalized_speedup"],
            "display_slo_goodput_speedup": row["metrics"]["display_slo_goodput_speedup"],
            "state_p99_seconds": row["metrics"]["latency_p99"],
            "display_p99_seconds": row["metrics"]["display_latency_p99"],
            "energy_reduction": row["metrics"]["energy_reduction"],
            "verification_fraction": row["metrics"]["verification_fraction"],
            "mean_batch_occupancy": row["scheduler"]["mean_occupancy_fraction"],
            "maximum_pending_authorities": row["scheduler"]["maximum_pending_authorities"],
            "unfilled_batch_slots": row["scheduler"]["unfilled_batch_slots"],
            "state_violations": row["counts"]["state_violations"],
        }
    c8_paths = sorted((root / "p3" / "c8_staggered").glob("seed*.json"))
    c16_w1_dir = root / "p3" / "c16_w1_lane2_final_r6"
    if not c16_w1_dir.exists():
        c16_w1_dir = root / "p3" / "c16_w1_lane2_final_r5"
    if not c16_w1_dir.exists():
        c16_w1_dir = root / "p3" / "c16_w1_lane2_final"
    if not c16_w1_dir.exists():
        c16_w1_dir = root / "p3" / "c16_w1_renewed"
    if not c16_w1_dir.exists():
        c16_w1_dir = root / "p3" / "c16_w1_final"
    c16_w2_dir = root / "p3" / "c16_w2_lane2_final_r6"
    if not c16_w2_dir.exists():
        c16_w2_dir = root / "p3" / "c16_w2_lane2_final_r5"
    if not c16_w2_dir.exists():
        c16_w2_dir = root / "p3" / "c16_w2_lane2_final"
    if not c16_w2_dir.exists():
        c16_w2_dir = root / "p3" / "c16_w2_renewed"
    if not c16_w2_dir.exists():
        c16_w2_dir = root / "p3" / "c16_w2"
    c16_w1_paths = sorted(c16_w1_dir.glob("seed*.json"))
    c16_w2_paths = sorted(c16_w2_dir.glob("seed*.json"))
    c8_rows = [load(path) for path in c8_paths]
    c16_w1_rows = [load(path) for path in c16_w1_paths]
    c16_w2_rows = [load(path) for path in c16_w2_paths]
    # c8/180 s is a pre-declared capacity-boundary cell, not a dependency of
    # the c16 Whisper headline.  A blocked staggered topology therefore makes
    # the strict c8 gate false; it must not prevent a fail-closed c16 verdict.
    assert len(c8_rows) in {0, 5}
    assert len(c16_w1_rows) == 5
    assert len(c16_w2_rows) == 5
    for row in c8_rows:
        assert_bound(
            row, digest=d8, policy=p8, duration=180, concurrency=8,
            holdback=True, checkpoint_phase_policy="session-staggered",
        )
        assert row["config"]["runtime_source_identity"] == final_identity
    for row in (*c16_w1_rows, *c16_w2_rows):
        assert_bound(
            row, digest=d16, policy=p16, duration=90, concurrency=16,
            holdback=False, low_margin_policy="verify",
        )
        assert row["config"]["verifier_lanes"] == 2
        assert row["config"]["speculative_prefetch_depth"] == 0
        assert row["config"]["pad_proposals_to_concurrency"] is False
        assert row["config"]["cohort_commit_barrier"] is False
        assert row["config"]["authority_spillover_on_proposer"] is False
        assert row["config"]["share_verifier_weights"] is False
        assert row["config"]["terminal_contract"] == "state-only"
        assert row["config"]["runtime_source_identity"] == final_identity
    c8 = summarize_runs(c8_rows) if c8_rows else None
    c16_w1 = summarize_runs(c16_w1_rows)
    c16_w2 = summarize_runs(c16_w2_rows)

    c8_risk_paths = completed_jsons(
        root / "p3" / "risk_staggered", "c8-*.json"
    )
    c16_risk_dir = root / "p3" / "risk_c16_lane2_final_r6"
    if not c16_risk_dir.exists():
        c16_risk_dir = root / "p3" / "risk_c16_lane2_final_r5"
    if not c16_risk_dir.exists():
        c16_risk_dir = root / "p3" / "risk_c16_lane2_final"
    if not c16_risk_dir.exists():
        c16_risk_dir = root / "p3" / "risk_c16_renewed"
    if not c16_risk_dir.exists():
        c16_risk_dir = root / "p3" / "risk"
    c16_risk_paths = completed_jsons(c16_risk_dir, "c16-*.json")
    c16_risk_early_fail_path = c16_risk_dir / "early-fail.json"
    c16_risk_early_fail = (
        load(c16_risk_early_fail_path)
        if c16_risk_early_fail_path.exists() else None
    )
    if c16_risk_early_fail is not None:
        assert c16_risk_early_fail["counts"]["caught_state_errors"] > 0
        policy_sources = [
            row for row in c16_risk_early_fail["source_files"]
            if row["role"] == "policy"
        ]
        assert len(policy_sources) == 1
        assert policy_sources[0]["sha256"] == d16
    assert len(c8_risk_paths) in {0, 2}
    assert (
        len(c16_risk_paths) == 2
        or (
            len(c16_risk_paths) == 0
            and c16_risk_early_fail is not None
            and c16_risk_early_fail["decision"] == "RISK_GATE_EARLY_FAIL"
        )
    )
    risk_paths = c8_risk_paths + c16_risk_paths
    risks = [load(path) for path in risk_paths]
    c8_risk_gate = len(c8_risk_paths) == 2
    c16_risk_gate = (
        len(c16_risk_paths) == 2 and c16_risk_early_fail is None
    )
    for path, row in zip(risk_paths, risks):
        is_c8 = "c8-" in path.name
        if is_c8:
            c8_risk_gate = c8_risk_gate and (
                row["decision"] == "W4_RISK_CERTIFICATE_PASS"
                and row["counts"]["risk_eligible_entries"] >= 30_000
                and row["counts"]["pre_outcome_randomized_audits"] >= 500
                and row["counts"]["caught_state_errors"] == 0
                and row["risk_certificate"]["upper_risk"] <= 0.005
            )
        else:
            c16_risk_gate = c16_risk_gate and (
                row["decision"] == "W4_RISK_CERTIFICATE_PASS"
                and row["counts"]["risk_eligible_entries"] >= 30_000
                and row["counts"]["pre_outcome_randomized_audits"] >= 500
                and row["counts"]["caught_state_errors"] == 0
                and row["risk_certificate"]["upper_risk"] <= 0.005
            )
        assert row["config"]["low_margin_policy"] == (
            "holdback" if is_c8 else "verify"
        )
        assert row["config"]["runtime_source_identity"] == final_identity
        assert row["config"]["policy_sha256"] == (d8 if is_c8 else d16)
        expected_policy = p8 if is_c8 else p16
        assert row["config"].get("window_margin_rules", []) == (
            expected_policy.get("window_margin_rules", [])
        )
        assert row["config"].get(
            "checkpoint_phase_policy", "synchronized"
        ) == ("session-staggered" if is_c8 else "synchronized")
        if not is_c8:
            assert row["counts"]["risk_eligible_entries"] >= 30_000
            assert row["counts"]["pre_outcome_randomized_audits"] >= 500
            assert row["counts"]["caught_state_errors"] == 0
            assert row["risk_certificate"]["upper_risk"] <= 0.005
    quality_path = (
        root / "p3" / "quality_staggered" / "c8-holdback.json"
    )
    quality = load(quality_path) if quality_path.exists() else None
    if quality is not None:
        assert quality["config"]["checkpoint_phase_policy"] == "session-staggered"
        assert quality["config"]["checkpoint_revisions"] == 10
        assert quality["config"]["deferred_risk_authority"] is False
        assert quality["config"]["deferred_terminal_authority"] is False
        assert quality["config"]["policy_sha256"] == d8
        quality_identity = quality["config"]["runtime_source_identity"]
        assert quality_identity["whisper_state.py"] == final_identity["whisper_state.py"]
        for key in (
            "margin_threshold", "age_window_index", "age_margin_threshold",
            "late_window_index", "late_margin_threshold",
            "high_load_prompt_tokens", "high_load_margin_threshold",
        ):
            assert quality["config"].get(key) == p8.get(
                "threshold" if key == "margin_threshold" else key
            )

    c16_quality_path = (
        root / "p3" / "quality_c16_lane2_final_r6" / "c16-verify.json"
    )
    if not c16_quality_path.exists():
        c16_quality_path = (
            root / "p3" / "quality_c16_lane2_final_r5" / "c16-verify.json"
        )
    if not c16_quality_path.exists():
        c16_quality_path = (
            root / "p3" / "quality_c16_lane2_final" / "c16-verify.json"
        )
    if not c16_quality_path.exists():
        c16_quality_path = (
            root / "p3" / "quality_c16_renewed" / "c16-holdback.json"
        )
    c16_quality = load(c16_quality_path) if c16_quality_path.exists() else None
    c16_quality_gate = c16_quality is not None
    if c16_quality is not None:
        config = c16_quality["config"]
        assert config["checkpoint_phase_policy"] == "synchronized"
        assert config["checkpoint_revisions"] == 10
        assert config["deferred_risk_authority"] is True
        assert config["deferred_terminal_authority"] is False
        assert config["low_margin_policy"] == "verify"
        assert config["policy_sha256"] == d16
        assert config["runtime_source_identity"]["whisper_state.py"] == final_identity["whisper_state.py"]
        for key in (
            "margin_threshold", "age_window_index", "age_margin_threshold",
            "late_window_index", "late_margin_threshold",
            "high_load_prompt_tokens", "high_load_margin_threshold",
        ):
            assert config.get(key) == p16.get(
                "threshold" if key == "margin_threshold" else key
            )
        assert config.get("window_margin_rules", []) == p16.get(
            "window_margin_rules", []
        )
        c16_quality_gate = (
            c16_quality["decision"] == "W6_QUALITY_UX_PASS"
            and c16_quality["metrics"]["mean_wer_delta_pp"] <= 1.0
            and c16_quality["metrics"]["paired_bootstrap_95_upper_pp"] <= 2.0
            and c16_quality["counts"]["catastrophic_outliers"] == 0
        )

    c8_gate = (
        c8 is not None
        and quality is not None
        and c8_risk_gate
        and c8["median_wall_speedup"] >= 2.2
        and c8["median_gpu_normalized_speedup"] >= 1.1
        and c8["median_energy_reduction"] >= 0.20
        and c8["maximum_display_p99_seconds"] <= 1.9
        and c8["maximum_state_p99_seconds"] <= 2.5
        and c8["deadline_misses"] == 0
        and c8["display_deadline_misses"] == 0
        and c8["state_violations"] == 0
        and c8["stale_commits"] == 0
        and quality["decision"] == "W6_QUALITY_UX_PASS"
        and quality["metrics"]["mean_wer_delta_pp"] <= 1.0
        and quality["metrics"]["paired_bootstrap_95_upper_pp"] <= 2.0
        and quality["counts"]["catastrophic_outliers"] == 0
    )

    def headline_gate(row: dict[str, Any]) -> bool:
        return (
            row["median_wall_speedup"] >= 2.0
            and row["median_gpu_normalized_speedup"] >= 1.0
            and row["median_display_slo_goodput_speedup"] >= 2.0
            and row["minimum_energy_reduction"] >= 0.15
            and row["maximum_display_p99_seconds"] <= 1.9
            and row["maximum_state_p99_seconds"] <= 4.0
            and row["state_violations"] == 0
            and row["stale_commits"] == 0
            and row["display_deadline_misses"] == 0
        )

    c16_w1_gate = headline_gate(c16_w1) and c16_quality_gate
    c16_w2_gate = headline_gate(c16_w2) and c16_quality_gate
    decision = classify_closure(
        c8_gate=c8_gate,
        c16_w1_gate=c16_w1_gate,
        c16_w2_gate=c16_w2_gate,
        c16_risk_gate=c16_risk_gate,
    )
    summary = {
        "schema_version": 1,
        "decision": decision,
        "p0": {
            "metric_repair": "paired terminal scope",
            "audit_distribution_repair": "true low-margin prompt-state holdback",
            "policy_binding": "path+sha256+runtime-parameter equality",
            "telemetry": "batch occupancy, pending authority, unfilled slots",
            "c8_policy_sha256": d8,
            "c8_original_policy_sha256": d8_original,
            "c16_policy_sha256": d16,
        },
        "p1": {"attribution": ceiling, "variants": p1_summary},
        "p2": {
            "selected_topology": selected_topology,
            "holdback_improves_over_full_verify": (
                selected_topology is not None
                and selected_topology in staggered
                and staggered[selected_topology]["metrics"]["wall_speedup"]
                > p1["full-verify"]["metrics"]["wall_speedup"]
            ),
            "checkpoint_phase_policy": "session-staggered",
        },
        "p3": {
            "c8": c8,
            "c8_gate_pass": c8_gate,
            "c16_W1_sync": c16_w1,
            "c16_W1_gate_pass": c16_w1_gate,
            "c16_W2_poisson": c16_w2,
            "c16_W2_gate_pass": c16_w2_gate,
            "c16_risk_gate_pass": c16_risk_gate,
            "c16_quality_gate_pass": c16_quality_gate,
            "risk": {
                "status": (
                    "EARLY_FAIL" if c16_risk_early_fail is not None
                    else "COMPLETE"
                ),
                "streams": (
                    len(risks)
                    + (
                        int(c16_risk_early_fail["counts"]["streams"])
                        if c16_risk_early_fail is not None else 0
                    )
                ),
                "risk_entries": (
                    sum(r["counts"]["risk_eligible_entries"] for r in risks)
                    + (
                        int(c16_risk_early_fail["counts"]["risk_eligible_entries"])
                        if c16_risk_early_fail is not None else 0
                    )
                ),
                "audits": (
                    sum(r["counts"]["pre_outcome_randomized_audits"] for r in risks)
                    + (
                        int(c16_risk_early_fail["counts"]["pre_outcome_randomized_audits"])
                        if c16_risk_early_fail is not None else 0
                    )
                ),
                "caught_errors": (
                    sum(r["counts"]["caught_state_errors"] for r in risks)
                    + (
                        int(c16_risk_early_fail["counts"]["caught_state_errors"])
                        if c16_risk_early_fail is not None else 0
                    )
                ),
                "maximum_time_uniform_upper_risk": (
                    max(
                        r["risk_certificate"]["upper_risk"]
                        for r in risks
                    ) if risks else None
                ),
                "early_fail_artifact": (
                    c16_risk_early_fail_path.relative_to(root).as_posix()
                    if c16_risk_early_fail is not None else None
                ),
            },
            "c8_risk_gate_pass": c8_risk_gate,
            "quality": (
                {
                    "mean_wer_delta_pp": quality["metrics"]["mean_wer_delta_pp"],
                    "paired_bootstrap_95_upper_pp": quality["metrics"]["paired_bootstrap_95_upper_pp"],
                    "catastrophic_outliers": quality["counts"]["catastrophic_outliers"],
                }
                if quality is not None else None
            ),
            "c16_quality": (
                {
                    "mean_wer_delta_pp": c16_quality["metrics"]["mean_wer_delta_pp"],
                    "paired_bootstrap_95_upper_pp": c16_quality["metrics"]["paired_bootstrap_95_upper_pp"],
                    "catastrophic_outliers": c16_quality["counts"]["catastrophic_outliers"],
                }
                if c16_quality is not None else None
            ),
        },
        "claim_boundary": (
            "c16 W1/W2 are the Whisper headline. c8/180 s is reported as a "
            "capacity boundary unless its stricter resource-positive gate passes."
        ),
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_bytes(
        (json.dumps(summary, indent=2, sort_keys=True) + "\n").encode("utf-8")
    )

    lines = [
        "# Whisper P0-P3 closure", "", f"Decision: `{decision}`.", "",
        "## P0 protocol repair", "",
        "- Display and state goodput now use matched event scopes.",
        "- Risk audits now execute the actual holdback transition instead of canonical state replacement.",
        "- Every formal workload binds the policy path, SHA-256 and all runtime thresholds.",
        "- Scheduler telemetry records occupancy, pending authority and lost batch slots.", "",
        "## P1 causal decomposition", "", f"Attribution: `{ceiling}`.", "",
        "| Variant | Wall | GPU norm | Display | State P99 | Energy | Verify | Occupancy | Pending max |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for name, row in p1_summary.items():
        lines.append(
            f"| {name} | {row['wall_speedup']:.3f}x | {row['gpu_normalized_speedup']:.3f}x | "
            f"{row['display_slo_goodput_speedup']:.3f}x | {row['state_p99_seconds']:.3f}s | "
            f"{100*row['energy_reduction']:.1f}% | {100*row['verification_fraction']:.1f}% | "
            f"{100*row['mean_batch_occupancy']:.1f}% | {row['maximum_pending_authorities']} |"
        )
    lines += ["", "## P2 holdback", "", f"Selected topology: `{selected_topology}`.", ""]
    lines += [
        "## P3 independent validation", "",
        "| Cell | Runs | Wall median | Wall min | GPU norm | Display | State P99 max | Energy median/min | Violations | Gate |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|:---:|",
    ]
    report_rows = [
        ("base/c16 W1 sync", c16_w1, c16_w1_gate),
        ("base/c16 W2 poisson", c16_w2, c16_w2_gate),
    ]
    if c8 is not None:
        report_rows.insert(0, ("base/c8 180s", c8, c8_gate))
    for name, row, passed in report_rows:
        lines.append(
            f"| {name} | {row['runs']} | {row['median_wall_speedup']:.3f}x | "
            f"{row['minimum_wall_speedup']:.3f}x | {row['median_gpu_normalized_speedup']:.3f}x | "
            f"{row['median_display_slo_goodput_speedup']:.3f}x | {row['maximum_state_p99_seconds']:.3f}s | "
            f"{100*row['median_energy_reduction']:.1f}% / {100*row['minimum_energy_reduction']:.1f}% | "
            f"{row['state_violations'] + row['stale_commits']} | {'PASS' if passed else 'FAIL'} |"
        )
    lines += [
        "", "## Statistical contracts", "",
        (
            f"- Risk gate EARLY FAIL: {summary['p3']['risk']['streams']} streams, "
            f"{summary['p3']['risk']['risk_entries']:,} eligible entries, "
            f"{summary['p3']['risk']['audits']:,} pre-outcome audits, "
            f"{summary['p3']['risk']['caught_errors']} repeat-stable caught error(s). "
            "The zero-error gate was irreversibly violated, so the 30k target was stopped."
            if summary["p3"]["risk"]["status"] == "EARLY_FAIL"
            else (
                f"- {summary['p3']['risk']['streams']} independent streams: "
                f"{summary['p3']['risk']['risk_entries']:,} eligible entries, "
                f"{summary['p3']['risk']['audits']:,} pre-outcome audits, 0 caught errors, "
                f"maximum time-uniform upper risk "
                f"{100*summary['p3']['risk']['maximum_time_uniform_upper_risk']:.4f}%."
            )
        ),
        (
            f"- Paired quality: mean WER delta {summary['p3']['quality']['mean_wer_delta_pp']:.3f} pp; "
            f"bootstrap 95% upper {summary['p3']['quality']['paired_bootstrap_95_upper_pp']:.3f} pp; "
            f"catastrophic outliers {summary['p3']['quality']['catastrophic_outliers']}."
            if summary["p3"]["quality"] is not None
            else "- Paired c8 quality was not run because the c8 staggered topology failed its pre-run eligibility gate."
        ),
        (
            f"- c16 paired quality: mean WER delta {summary['p3']['c16_quality']['mean_wer_delta_pp']:.3f} pp; "
            f"bootstrap 95% upper {summary['p3']['c16_quality']['paired_bootstrap_95_upper_pp']:.3f} pp; "
            f"catastrophic outliers {summary['p3']['c16_quality']['catastrophic_outliers']}."
            if summary["p3"]["c16_quality"] is not None
            else "- c16 paired quality was not completed; the c16 headline remains fail-closed."
        ), "",
        "The c16 cells decide whether Whisper remains a headline performance leg. The c8 cell is a disclosed low-load long-session boundary unless its stricter resource-positive gate passes.",
    ]
    args.output_md.write_bytes(("\n".join(lines) + "\n").encode("utf-8"))
    print(json.dumps({"decision": decision, "c8": c8_gate, "c16_w1": c16_w1_gate, "c16_w2": c16_w2_gate}, sort_keys=True))
    return 0 if c16_w1_gate and c16_w2_gate and c16_risk_gate else 2


if __name__ == "__main__":
    raise SystemExit(main())

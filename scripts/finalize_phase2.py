from __future__ import annotations

import csv
import hashlib
import json
import math
import statistics
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
PHASE = ROOT / "results" / "phase2"
RISK = PHASE / "risk_v1"
RISK_V2 = PHASE / "risk_v2"


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def write_paper_tables(
    path: Path,
    *,
    decision: str,
    system_rows: list[dict[str, Any]],
    replicate_stats: list[dict[str, Any]],
    risk_rows: list[dict[str, Any]],
    policy_repair_rows: list[dict[str, Any]],
) -> None:
    lines = [
        "# RevTrace Phase 2 paper-facing tables",
        "",
        f"Decision: `{decision}`",
        "",
        "## Active deployed policy",
        "",
        "| Model | Wall | GPU-normalized | SLO goodput | Miss | P99 | Output/state/stale |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for row in system_rows:
        lines.append(
            f"| {row['model']} | {row['wall_speedup']:.3f}x | "
            f"{row['gpu_normalized_speedup']:.3f}x | "
            f"{row['slo_goodput_speedup']:.3f}x | "
            f"{row['deadline_misses']}/{row['events']} | "
            f"{row['p99_state_entry_seconds']:.3f} s | "
            f"{row['output_violations']}/{row['state_violations']}/"
            f"{row['stale_or_replayed']} |"
        )
    lines.extend(
        [
            "",
            "## Five-run replication",
            "",
            "| Model | Runs | Wall mean +/- 95% CI | Wall min | GPU min | SLO min | P99 max | Miss/output/state/stale | Cross-run output/state mismatch |",
            "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for row in replicate_stats:
        lines.append(
            f"| {row['model']} | {row['runs']} | "
            f"{row['wall_speedup_mean']:.3f} +/- "
            f"{row['wall_speedup_ci95_halfwidth']:.3f}x (95% CI) | "
            f"{row['wall_speedup_min']:.3f}x | "
            f"{row['gpu_normalized_speedup_min']:.3f}x | "
            f"{row['slo_goodput_speedup_min']:.3f}x | "
            f"{row['p99_seconds_max']:.3f} s | "
            f"{row['total_deadline_misses']}/"
            f"{row['total_output_violations']}/"
            f"{row['total_state_violations']}/"
            f"{row['total_stale_or_replayed']} | "
            f"{row['total_output_mismatches_vs_run0']}/"
            f"{row['total_state_mismatches_vs_run0']} |"
        )
    lines.extend(
        [
            "",
            "## Active anytime-risk audit",
            "",
            "| Model/policy | Eligible entries | Base audits | Unique job hashes | Caught output/state errors | 95% anytime state-risk upper | Decision |",
            "|---|---:|---:|---:|---:|---:|---|",
        ]
    )
    for row in risk_rows:
        lines.append(
            f"| {row['model']} / {row['policy_version']} | "
            f"{row['risk_eligible_entries']:,} | "
            f"{row['base_audits']:,} | "
            f"{row['unique_audited_jobs']:,} | "
            f"{row['caught_output_errors']}/"
            f"{row['caught_state_errors']} | "
            f"{100.0 * row['upper_risk']:.3f}% | "
            f"`{row['decision']}` |"
        )
    lines.extend(
        [
            "",
            "## Frozen 1.7B policy repair",
            "",
            "| Policy | Tau | Seed | Caught state errors | Upper risk | Verify fraction | Wall | GPU-normalized | Miss | Decision |",
            "|---|---:|---:|---:|---:|---:|---:|---:|---:|---|",
        ]
    )
    for row in policy_repair_rows:
        lines.append(
            f"| {row['policy_version']} | {row['margin_threshold']:.2f} | "
            f"{row['risk_seed']} | {row['caught_state_errors']} | "
            f"{100.0 * row['upper_risk']:.3f}% | "
            f"{100.0 * row['verification_fraction']:.2f}% | "
            f"{row['wall_speedup']:.3f}x | "
            f"{row['gpu_normalized_speedup']:.3f}x | "
            f"{100.0 * row['deadline_miss_rate']:.2f}% | "
            f"`{row['risk_decision']}` |"
        )
    lines.extend(
        [
            "",
            "Boundaries: entries are repeated execution events, not independent "
            "utterances; the risk target is disagreement with the frozen "
            "canonical execution; zero observed disagreement is not a "
            "deterministic arithmetic certificate.",
            "",
        ]
    )
    path.write_text(
        "\n".join(lines),
        encoding="utf-8",
        newline="\n",
    )


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def event_trace_sha256(
    record: dict[str, Any],
    *,
    terminal_only: bool,
) -> str:
    events = []
    for event in record["events"]:
        if terminal_only and not event["terminal"]:
            continue
        projection = event["selected_state_projection"]
        events.append(
            {
                "session_id": event["session_id"],
                "chunk_id": event["chunk_id"],
                "selected_token_ids": event["selected_token_ids"],
                "projection_token_ids": projection[
                    "projection_token_ids"
                ],
            }
        )
    events.sort(key=lambda item: (item["session_id"], item["chunk_id"]))
    payload = json.dumps(
        events,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def cross_run_mismatches(
    reference: dict[str, Any],
    candidate: dict[str, Any],
    *,
    terminal_only: bool,
) -> tuple[int, int]:
    def index(record: dict[str, Any]) -> dict[tuple[str, int], dict[str, Any]]:
        return {
            (event["session_id"], event["chunk_id"]): event
            for event in record["events"]
            if not terminal_only or event["terminal"]
        }

    reference_events = index(reference)
    candidate_events = index(candidate)
    if reference_events.keys() != candidate_events.keys():
        raise ValueError("replicate event identities do not match")
    output_mismatches = 0
    state_mismatches = 0
    for key, reference_event in reference_events.items():
        candidate_event = candidate_events[key]
        output_mismatches += (
            reference_event["selected_token_ids"]
            != candidate_event["selected_token_ids"]
        )
        state_mismatches += (
            reference_event["selected_state_projection"][
                "projection_token_ids"
            ]
            != candidate_event["selected_state_projection"][
                "projection_token_ids"
            ]
        )
    return output_mismatches, state_mismatches


def main() -> int:
    expected_policy = {
        "Qwen3-ASR-0.6B": {
            "margin_threshold": 0.05,
            "risk_seed": 20260728,
        },
        "Qwen3-ASR-1.7B": {
            "margin_threshold": 0.10,
            "risk_seed": 20260730,
        },
    }
    model_files = {
        "Qwen3-ASR-0.6B": (
            PHASE / "terminal_canonical",
            "terminal-canonical-Qwen3-ASR-0.6B-d30-c16.json",
        ),
        "Qwen3-ASR-1.7B": (
            PHASE / "terminal_canonical_v2",
            "terminal-canonical-Qwen3-ASR-1.7B-tau0.10-d30-c16.json",
        ),
    }
    phase1 = load(
        ROOT / "results" / "phase1" / "deployed_v1" / "summary.json"
    )
    phase1_rows = {row["model"]: row for row in phase1["rows"]}
    system_rows: list[dict[str, Any]] = []
    replicate_rows: list[dict[str, Any]] = []
    replicate_stats: list[dict[str, Any]] = []
    system_pass = True
    for model, (system_dir, name) in model_files.items():
        record = load(system_dir / name)
        if (
            record["margin_threshold"]
            != expected_policy[model]["margin_threshold"]
            or record["concurrency"] != 16
            or record["duration_seconds"] != 30
        ):
            raise ValueError(f"unexpected active system policy for {model}")
        summary = record["summary"]
        row = {
            "model": model,
            "events": summary["event_count"],
            "verified_events": summary["verified_events"],
            "verification_fraction": summary["verification_fraction"],
            "wall_speedup": summary["deployed_two_gpu_wall_speedup"],
            "gpu_normalized_speedup": summary[
                "gpu_normalized_throughput_speedup"
            ],
            "slo_goodput_speedup": summary["slo_goodput_speedup"],
            "deadline_misses": summary["state_entry_deadline_miss_events"],
            "deadline_miss_rate": summary[
                "state_entry_deadline_miss_rate"
            ],
            "p99_state_entry_seconds": summary[
                "state_entry_latency_seconds_p99"
            ],
            "output_violations": summary["output_violation_events"],
            "state_violations": summary[
                "state_projection_violation_events"
            ],
            "stale_or_replayed": summary[
                "stale_or_replayed_result_events"
            ],
            "wall_improvement_over_phase1": (
                summary["deployed_two_gpu_wall_speedup"]
                / phase1_rows[model]["wall_speedup"]
                - 1.0
            ),
            "p99_reduction_over_phase1": (
                1.0
                - summary["state_entry_latency_seconds_p99"]
                / phase1_rows[model]["state_entry_p99_seconds"]
            ),
            "gate": record["decision"],
        }
        system_rows.append(row)
        system_pass = system_pass and record["decision"].endswith(
            "_GATE_PASS"
        )
        run_records = [record]
        replicate_dir = system_dir / "replicates"
        replicate_pattern = f"terminal-canonical-{model}-r*.json"
        if model == "Qwen3-ASR-1.7B":
            replicate_pattern = (
                f"terminal-canonical-{model}-tau0.10-r*.json"
            )
        run_records.extend(
            load(path)
            for path in sorted(
                replicate_dir.glob(replicate_pattern)
            )
        )
        model_replicates: list[dict[str, Any]] = []
        for run_index, run_record in enumerate(run_records):
            if (
                run_record["margin_threshold"]
                != expected_policy[model]["margin_threshold"]
                or run_record["concurrency"] != 16
                or run_record["duration_seconds"] != 30
            ):
                raise ValueError(
                    f"unexpected replicate policy for {model} run {run_index}"
                )
            run_summary = run_record["summary"]
            full_output_mismatches, full_state_mismatches = (
                cross_run_mismatches(
                    run_records[0],
                    run_record,
                    terminal_only=False,
                )
            )
            terminal_output_mismatches, terminal_state_mismatches = (
                cross_run_mismatches(
                    run_records[0],
                    run_record,
                    terminal_only=True,
                )
            )
            replicate_row = {
                "model": model,
                "run": run_index,
                "events": run_summary["event_count"],
                "decision": run_record["decision"],
                "wall_speedup": run_summary[
                    "deployed_two_gpu_wall_speedup"
                ],
                "gpu_normalized_speedup": run_summary[
                    "gpu_normalized_throughput_speedup"
                ],
                "slo_goodput_speedup": run_summary[
                    "slo_goodput_speedup"
                ],
                "deadline_miss_rate": run_summary[
                    "state_entry_deadline_miss_rate"
                ],
                "p99_state_entry_seconds": run_summary[
                    "state_entry_latency_seconds_p99"
                ],
                "output_violations": run_summary[
                    "output_violation_events"
                ],
                "state_violations": run_summary[
                    "state_projection_violation_events"
                ],
                "stale_or_replayed": run_summary[
                    "stale_or_replayed_result_events"
                ],
                "output_mismatches_vs_run0": full_output_mismatches,
                "state_mismatches_vs_run0": full_state_mismatches,
                "terminal_output_mismatches_vs_run0": (
                    terminal_output_mismatches
                ),
                "terminal_state_mismatches_vs_run0": (
                    terminal_state_mismatches
                ),
                "terminal_trace_sha256": event_trace_sha256(
                    run_record, terminal_only=True
                ),
                "full_trace_sha256": event_trace_sha256(
                    run_record, terminal_only=False
                ),
            }
            replicate_rows.append(replicate_row)
            model_replicates.append(replicate_row)
        wall_values = [item["wall_speedup"] for item in model_replicates]
        gpu_values = [
            item["gpu_normalized_speedup"] for item in model_replicates
        ]
        slo_values = [
            item["slo_goodput_speedup"] for item in model_replicates
        ]
        p99_values = [
            item["p99_state_entry_seconds"] for item in model_replicates
        ]
        all_replicates_pass = all(
            item["decision"].endswith("_GATE_PASS")
            for item in model_replicates
        )
        terminal_trace_digests = {
            item["terminal_trace_sha256"] for item in model_replicates
        }
        full_trace_digests = {
            item["full_trace_sha256"] for item in model_replicates
        }
        replicate_stats.append(
            {
                "model": model,
                "runs": len(model_replicates),
                "wall_speedup_mean": statistics.mean(wall_values),
                "wall_speedup_stddev": (
                    statistics.stdev(wall_values)
                    if len(wall_values) > 1
                    else 0.0
                ),
                "wall_speedup_ci95_halfwidth": (
                    2.776
                    * statistics.stdev(wall_values)
                    / math.sqrt(len(wall_values))
                ),
                "wall_speedup_min": min(wall_values),
                "wall_speedup_max": max(wall_values),
                "gpu_normalized_speedup_mean": statistics.mean(gpu_values),
                "gpu_normalized_speedup_min": min(gpu_values),
                "slo_goodput_speedup_mean": statistics.mean(slo_values),
                "slo_goodput_speedup_min": min(slo_values),
                "p99_seconds_mean": statistics.mean(p99_values),
                "p99_seconds_max": max(p99_values),
                "total_deadline_misses": sum(
                    round(item["deadline_miss_rate"] * item["events"])
                    for item in model_replicates
                ),
                "total_output_violations": sum(
                    item["output_violations"] for item in model_replicates
                ),
                "total_state_violations": sum(
                    item["state_violations"] for item in model_replicates
                ),
                "total_stale_or_replayed": sum(
                    item["stale_or_replayed"]
                    for item in model_replicates
                ),
                "total_output_mismatches_vs_run0": sum(
                    item["output_mismatches_vs_run0"]
                    for item in model_replicates
                ),
                "total_state_mismatches_vs_run0": sum(
                    item["state_mismatches_vs_run0"]
                    for item in model_replicates
                ),
                "total_terminal_output_mismatches_vs_run0": sum(
                    item["terminal_output_mismatches_vs_run0"]
                    for item in model_replicates
                ),
                "total_terminal_state_mismatches_vs_run0": sum(
                    item["terminal_state_mismatches_vs_run0"]
                    for item in model_replicates
                ),
                "all_runs_pass": all_replicates_pass,
                "unique_terminal_trace_digests": len(
                    terminal_trace_digests
                ),
                "unique_full_trace_digests": len(full_trace_digests),
            }
        )
        system_pass = (
            system_pass
            and len(model_replicates) == 5
            and all_replicates_pass
        )

    simulation = load(RISK / "simulation-500.json")
    risk_rows: list[dict[str, Any]] = []
    stratum_rows: list[dict[str, Any]] = []
    calibration_rows: list[dict[str, Any]] = []
    for model in model_files:
        calibration_path = (
            RISK / f"calibration-c64-{model}.json"
        )
        if not calibration_path.is_file():
            continue
        calibration = load(calibration_path)
        caught_records = [
            item
            for item in calibration["audit_records"]
            if item["state_error"] or item["output_error"]
        ]
        calibration_rows.append(
            {
                "model": model,
                "concurrency": calibration["config"]["concurrency"],
                "risk_eligible_entries": calibration["counts"][
                    "risk_eligible_state_entries"
                ],
                "base_audits": calibration["counts"]["base_audits"],
                "audit_fraction": (
                    calibration["counts"]["base_audits"]
                    / calibration["counts"][
                        "risk_eligible_state_entries"
                    ]
                ),
                "caught_state_errors": calibration["counts"][
                    "caught_state_errors"
                ],
                "caught_error_margins": ";".join(
                    str(item["minimum_margin"])
                    for item in caught_records
                ),
                "upper_error_count": calibration["risk_certificate"][
                    "upper_error_count"
                ],
                "upper_risk": calibration["risk_certificate"][
                    "upper_risk"
                ],
                "decision": calibration["decision"],
                "claim_scope": "calibration/stress only; not c16 validation",
            }
        )
    v1_repair_path = RISK / "natural-shadow-Qwen3-ASR-1.7B.json"
    if v1_repair_path.is_file():
        v1_repair = load(v1_repair_path)
        caught_records = [
            item
            for item in v1_repair["audit_records"]
            if item["state_error"] or item["output_error"]
        ]
        calibration_rows.append(
            {
                "model": "Qwen3-ASR-1.7B",
                "concurrency": v1_repair["config"]["concurrency"],
                "risk_eligible_entries": v1_repair["counts"][
                    "risk_eligible_state_entries"
                ],
                "base_audits": v1_repair["counts"]["base_audits"],
                "audit_fraction": (
                    v1_repair["counts"]["base_audits"]
                    / v1_repair["counts"][
                        "risk_eligible_state_entries"
                    ]
                ),
                "caught_state_errors": v1_repair["counts"][
                    "caught_state_errors"
                ],
                "caught_error_margins": ";".join(
                    str(item["minimum_margin"])
                    for item in caught_records
                ),
                "upper_error_count": v1_repair["risk_certificate"][
                    "upper_error_count"
                ],
                "upper_risk": v1_repair["risk_certificate"][
                    "upper_risk"
                ],
                "decision": v1_repair["decision"],
                "claim_scope": (
                    "frozen c16 v1 failure used to preregister v2; "
                    "not v2 validation"
                ),
            }
        )
    natural_pass = True
    active_risk_files = {
        "Qwen3-ASR-0.6B": (
            RISK / "natural-shadow-Qwen3-ASR-0.6B.json"
        ),
        "Qwen3-ASR-1.7B": (
            RISK_V2
            / "natural-shadow-Qwen3-ASR-1.7B-tau0.10.json"
        ),
    }
    for model, path in active_risk_files.items():
        record = load(path)
        if (
            record["config"]["margin_threshold"]
            != expected_policy[model]["margin_threshold"]
            or record["config"]["seed"]
            != expected_policy[model]["risk_seed"]
            or record["config"]["concurrency"] != 16
        ):
            raise ValueError(f"unexpected active risk policy for {model}")
        counts = record["counts"]
        risk = record["risk_certificate"]
        row = {
            "model": model,
            "policy_version": (
                "v1_tau0.05"
                if model == "Qwen3-ASR-0.6B"
                else "v2_tau0.10"
            ),
            "source": path.relative_to(ROOT).as_posix(),
            "risk_eligible_entries": counts[
                "risk_eligible_state_entries"
            ],
            "base_audits": counts["base_audits"],
            "unique_audited_jobs": len(
                {
                    item["job_sha256"]
                    for item in record["audit_records"]
                }
            ),
            "audit_fraction": (
                counts["base_audits"]
                / counts["risk_eligible_state_entries"]
            ),
            "caught_output_errors": counts["caught_output_errors"],
            "caught_state_errors": counts["caught_state_errors"],
            "observed_verified_selection_output_violations": counts[
                "selected_output_violations"
            ],
            "observed_verified_selection_state_violations": counts[
                "selected_state_violations"
            ],
            "upper_error_count": risk["upper_error_count"],
            "upper_risk": risk["upper_risk"],
            "confidence": risk["confidence"],
            "decision": record["decision"],
        }
        risk_rows.append(row)
        for stratum, stratum_counts in record.get(
            "margin_strata", {}
        ).items():
            stratum_rows.append(
                {
                    "model": model,
                    "stratum": stratum,
                    "entries": stratum_counts["entries"],
                    "audits": stratum_counts["audits"],
                    "audit_fraction": (
                        stratum_counts["audits"]
                        / stratum_counts["entries"]
                        if stratum_counts["entries"]
                        else 0.0
                    ),
                    "caught_state_errors": stratum_counts[
                        "caught_state_errors"
                    ],
                }
            )
        natural_pass = natural_pass and record["decision"].endswith(
            "_PASS"
        )

    interventions = [
        {
            "intervention": "c64 calibration shadow audit",
            "model": "both",
            "decision": "CALIBRATION_ONLY",
            "evidence": (
                "different batch shape from deployed c16; retained for "
                "stress diagnosis and excluded from the c16 risk claim"
            ),
        },
        {
            "intervention": "two FP16 singleton verifier processes",
            "model": "Qwen3-ASR-0.6B",
            "decision": "FAIL",
            "evidence": "3.33% deadline miss without MPS",
        },
        {
            "intervention": "two FP16 singleton verifier processes with MPS",
            "model": "Qwen3-ASR-0.6B",
            "decision": "FAIL",
            "evidence": "3.75% deadline miss; MPS did not remove terminal burst",
        },
        {
            "intervention": "FP32 fixed-shape terminal canonical",
            "model": "Qwen3-ASR-1.7B",
            "decision": "FAIL",
            "evidence": "6.67% deadline miss; P99 2.701 s",
        },
        {
            "intervention": "FP16 batch-invariant same-input",
            "model": "Qwen3-ASR-0.6B",
            "decision": "BOUNDARY",
            "evidence": "1/240 output mismatch, 0/240 state mismatch",
        },
        {
            "intervention": "FP16 batch-invariant same-input",
            "model": "Qwen3-ASR-1.7B",
            "decision": "FAIL",
            "evidence": "1/240 output and state mismatch",
        },
        {
            "intervention": "FP16 fixed-shape invariance",
            "model": "Qwen3-ASR-0.6B",
            "decision": "PASS",
            "evidence": "0 repeat/permutation/replication/composition mismatches",
        },
        {
            "intervention": "FP16 fixed-shape invariance",
            "model": "Qwen3-ASR-1.7B",
            "decision": "FAIL",
            "evidence": "7 replicated-row and 1 composition mismatches",
        },
        {
            "intervention": "FP32 fixed-shape invariance",
            "model": "both",
            "decision": "PASS",
            "evidence": "0 mismatches in all four invariance checks",
        },
    ]
    policy_repair_rows: list[dict[str, Any]] = []
    for version, threshold, risk_path, system_path in (
        (
            "v1_frozen_failure",
            0.05,
            RISK / "natural-shadow-Qwen3-ASR-1.7B.json",
            PHASE
            / "terminal_canonical"
            / "terminal-canonical-Qwen3-ASR-1.7B-d30-c16.json",
        ),
        (
            "v2_independent_validation",
            0.10,
            RISK_V2
            / "natural-shadow-Qwen3-ASR-1.7B-tau0.10.json",
            PHASE
            / "terminal_canonical_v2"
            / "terminal-canonical-Qwen3-ASR-1.7B-tau0.10-d30-c16.json",
        ),
    ):
        risk_record = load(risk_path)
        system_record = load(system_path)
        risk_counts = risk_record["counts"]
        risk_certificate = risk_record["risk_certificate"]
        system_summary = system_record["summary"]
        policy_repair_rows.append(
            {
                "policy_version": version,
                "margin_threshold": threshold,
                "risk_seed": risk_record["config"]["seed"],
                "risk_eligible_entries": risk_counts[
                    "risk_eligible_state_entries"
                ],
                "base_audits": risk_counts["base_audits"],
                "caught_state_errors": risk_counts[
                    "caught_state_errors"
                ],
                "upper_risk": risk_certificate["upper_risk"],
                "risk_decision": risk_record["decision"],
                "verification_fraction": system_summary[
                    "verification_fraction"
                ],
                "wall_speedup": system_summary[
                    "deployed_two_gpu_wall_speedup"
                ],
                "gpu_normalized_speedup": system_summary[
                    "gpu_normalized_throughput_speedup"
                ],
                "slo_goodput_speedup": system_summary[
                    "slo_goodput_speedup"
                ],
                "deadline_miss_rate": system_summary[
                    "state_entry_deadline_miss_rate"
                ],
                "p99_state_entry_seconds": system_summary[
                    "state_entry_latency_seconds_p99"
                ],
                "system_decision": system_record["decision"],
            }
        )

    for path, rows in (
        (PHASE / "system_metrics.csv", system_rows),
        (PHASE / "system_replicates.csv", replicate_rows),
        (PHASE / "policy_repair.csv", policy_repair_rows),
        (RISK / "risk_metrics.csv", risk_rows),
        (RISK / "risk_strata.csv", stratum_rows),
        (RISK / "calibration_metrics.csv", calibration_rows),
        (PHASE / "intervention_matrix.csv", interventions),
    ):
        if not rows:
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=list(rows[0]),
                lineterminator="\n",
            )
            writer.writeheader()
            writer.writerows(rows)

    decision = (
        "PHASE2_RISK_AND_TAIL_GATE_PASS_"
        "DETERMINISTIC_CERTIFICATE_UNRESOLVED"
        if system_pass
        and natural_pass
        and simulation["decision"].endswith("_PASS")
        else "PHASE2_RISK_AND_TAIL_GATE_FAIL"
    )
    write_paper_tables(
        PHASE / "PAPER_TABLES.md",
        decision=decision,
        system_rows=system_rows,
        replicate_stats=replicate_stats,
        risk_rows=risk_rows,
        policy_repair_rows=policy_repair_rows,
    )
    source_files = sorted(
        path
        for folder in (
            PHASE / "terminal_canonical",
            PHASE / "terminal_reserved",
            PHASE / "batch_invariant",
            PHASE / "fixed_shape",
            PHASE / "fixed_shape_fp32",
            RISK,
            RISK_V2,
        )
        for path in folder.rglob("*")
        if path.is_file()
        and path.name not in {"summary.json", "MANIFEST.json"}
    )
    manifest = {
        "schema_version": 1,
        "files": [
            {
                "path": path.relative_to(ROOT).as_posix(),
                "bytes": path.stat().st_size,
                "sha256": sha256(path),
            }
            for path in source_files
        ],
    }
    summary = {
        "schema_version": 1,
        "decision": decision,
        "system_rows": system_rows,
        "replicate_stats": replicate_stats,
        "policy_repair_rows": policy_repair_rows,
        "risk_rows": risk_rows,
        "risk_strata": stratum_rows,
        "calibration_rows": calibration_rows,
        "simulation": {
            "decision": simulation["decision"],
            "trajectories": sum(
                row["repetitions"] for row in simulation["scenarios"]
            ),
            "overall_violation_rate": simulation[
                "overall_coverage_violation_rate"
            ],
            "zero_caught_error_upper_risk": simulation[
                "zero_caught_error_upper_risk"
            ],
        },
        "gates": {
            "S1_anytime_simulation": simulation["decision"],
            "S1_natural_shadow_audit": (
                "PASS" if natural_pass else "FAIL"
            ),
            "S2_terminal_tail": "PASS" if system_pass else "FAIL",
            "deterministic_intermediate_certificate": "UNRESOLVED",
        },
        "boundaries": {
            "natural_entries": (
                "execution events on repeated natural traces, not "
                "independent utterances"
            ),
            "active_policy": (
                "model- and concurrency-specific: tau=0.05 for 0.6B/c16 "
                "and independently validated tau=0.10 for 1.7B/c16"
            ),
            "risk": (
                "time-uniform upper bound on disagreement with the frozen "
                "canonical execution, not deterministic arithmetic "
                "equivalence or transcript ground-truth correctness"
            ),
            "raw_selection_counters": (
                "selected_*_violations cover mandatory/audited canonical "
                "checks only; unaudited disagreement is not directly "
                "observed and is controlled by the risk bound"
            ),
            "terminal": (
                "versioned fixed-shape canonical contract; singleton "
                "equivalence not claimed"
            ),
            "performance": (
                "real two-RTX-3090 wall-clock results; audit replay excluded "
                "from service timing"
            ),
        },
    }
    write_json(RISK / "summary.json", summary)
    write_json(PHASE / "terminal_canonical" / "summary.json", {
        "schema_version": 1,
        "decision": (
            "PHASE2_TERMINAL_TAIL_GATE_PASS"
            if system_pass
            else "PHASE2_TERMINAL_TAIL_GATE_FAIL"
        ),
        "rows": system_rows,
    })
    write_json(PHASE / "MANIFEST.json", manifest)
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if decision.startswith("PHASE2_RISK_AND_TAIL_GATE_PASS") else 2


if __name__ == "__main__":
    raise SystemExit(main())

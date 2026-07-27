from __future__ import annotations

import csv
import hashlib
import json
import statistics
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
PHASE = ROOT / "results" / "phase2"
RISK = PHASE / "risk_v1"


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> int:
    model_files = {
        "Qwen3-ASR-0.6B": "terminal-canonical-Qwen3-ASR-0.6B-d30-c16.json",
        "Qwen3-ASR-1.7B": "terminal-canonical-Qwen3-ASR-1.7B-d30-c16.json",
    }
    phase1 = load(
        ROOT / "results" / "phase1" / "deployed_v1" / "summary.json"
    )
    phase1_rows = {row["model"]: row for row in phase1["rows"]}
    system_rows: list[dict[str, Any]] = []
    replicate_rows: list[dict[str, Any]] = []
    replicate_stats: list[dict[str, Any]] = []
    system_pass = True
    for model, name in model_files.items():
        record = load(PHASE / "terminal_canonical" / name)
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
        replicate_dir = PHASE / "terminal_canonical" / "replicates"
        run_records.extend(
            load(path)
            for path in sorted(
                replicate_dir.glob(
                    f"terminal-canonical-{model}-r*.json"
                )
            )
        )
        model_replicates: list[dict[str, Any]] = []
        for run_index, run_record in enumerate(run_records):
            run_summary = run_record["summary"]
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
            }
            replicate_rows.append(replicate_row)
            model_replicates.append(replicate_row)
        wall_values = [item["wall_speedup"] for item in model_replicates]
        p99_values = [
            item["p99_state_entry_seconds"] for item in model_replicates
        ]
        all_replicates_pass = all(
            item["decision"].endswith("_GATE_PASS")
            for item in model_replicates
        )
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
                "wall_speedup_min": min(wall_values),
                "wall_speedup_max": max(wall_values),
                "p99_seconds_mean": statistics.mean(p99_values),
                "p99_seconds_max": max(p99_values),
                "total_deadline_misses": sum(
                    round(item["deadline_miss_rate"] * item["events"])
                    for item in model_replicates
                ),
                "all_runs_pass": all_replicates_pass,
            }
        )
        system_pass = (
            system_pass
            and len(model_replicates) >= 5
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
        calibration_rows.append(
            {
                "model": model,
                "concurrency": calibration["config"]["concurrency"],
                "risk_eligible_entries": calibration["counts"][
                    "risk_eligible_state_entries"
                ],
                "base_audits": calibration["counts"]["base_audits"],
                "caught_state_errors": calibration["counts"][
                    "caught_state_errors"
                ],
                "decision": calibration["decision"],
                "claim_scope": "calibration/stress only; not c16 validation",
            }
        )
    natural_pass = True
    for model in model_files:
        path = RISK / f"natural-shadow-{model}.json"
        record = load(path)
        counts = record["counts"]
        risk = record["risk_certificate"]
        row = {
            "model": model,
            "risk_eligible_entries": counts[
                "risk_eligible_state_entries"
            ],
            "base_audits": counts["base_audits"],
            "audit_fraction": (
                counts["base_audits"]
                / counts["risk_eligible_state_entries"]
            ),
            "caught_output_errors": counts["caught_output_errors"],
            "caught_state_errors": counts["caught_state_errors"],
            "selected_output_violations": counts[
                "selected_output_violations"
            ],
            "selected_state_violations": counts[
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

    for path, rows in (
        (PHASE / "system_metrics.csv", system_rows),
        (PHASE / "system_replicates.csv", replicate_rows),
        (RISK / "risk_metrics.csv", risk_rows),
        (RISK / "risk_strata.csv", stratum_rows),
        (PHASE / "intervention_matrix.csv", interventions),
    ):
        if not rows:
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
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
    source_files = sorted(
        path
        for folder in (
            PHASE / "terminal_canonical",
            PHASE / "terminal_reserved",
            PHASE / "batch_invariant",
            PHASE / "fixed_shape",
            PHASE / "fixed_shape_fp32",
            RISK,
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
            "risk": (
                "time-uniform statistical upper bound, not deterministic "
                "arithmetic equivalence"
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

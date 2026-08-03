#!/usr/bin/env python3
"""Fail-closed aggregation for the R10 Qwen DGFT cross-adapter matrix."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


EXPECTED = {
    ("Qwen3-ASR-0.6B", "dgft"): "qwen06-dgft-fp32batch.json",
    ("Qwen3-ASR-0.6B", "hybrid"): "qwen06-hybrid-fp32batch.json",
    ("Qwen3-ASR-1.7B", "dgft"): "qwen17-dgft-fp32batch.json",
    ("Qwen3-ASR-1.7B", "hybrid"): "qwen17-hybrid-fp32batch.json",
}


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def audit_cell(
    path: Path,
    expected_model: str,
    expected_mode: str,
    gates: dict[str, Any],
) -> dict[str, Any]:
    payload = load_json(path)
    summary = payload["summary"]
    environment = payload["environment"]
    contract = payload["contract"]

    checks = {
        "model_matches": payload["model"] == expected_model,
        "mode_matches": payload["mode"] == expected_mode,
        "runner_decision_pass": payload["decision"]
        == "PASS_QWEN_CROSS_ADAPTER_GATE",
        "transaction_install_violations": int(
            summary["transaction_install_violations"]
        )
        == int(gates["transaction_install_violations"]),
        "authority_batch_repeat_mismatches": int(
            summary["authority_batch_repeat_mismatches"]
        )
        == int(gates["authority_batch_repeat_mismatches"]),
        "authority_batch_vs_singleton_mismatches": int(
            summary["authority_batch_vs_singleton_mismatches"]
        )
        == int(gates["authority_batch_vs_singleton_mismatches"]),
        "wall_speedup": float(summary["deployed_wall_speedup"])
        >= float(gates["minimum_wall_speedup"]),
        "gpu_normalized_speedup": float(summary["gpu_normalized_speedup"])
        >= float(gates["minimum_gpu_normalized_speedup"]),
        "median_unit_edit_rate": float(summary["final_unit_edit_rate_median"])
        <= float(gates["maximum_median_unit_edit_rate"]),
        "p95_unit_edit_rate": float(summary["final_unit_edit_rate_p95"])
        <= float(gates["maximum_p95_unit_edit_rate"]),
        "catastrophic_sessions": int(summary["catastrophic_sessions_over_0_25"])
        == int(gates["maximum_catastrophic_sessions_over_0_25"]),
        "authority_is_fp32_batch": environment["authority_dtype"] == "float32"
        and environment["authority_execution"] == "batch",
        "invariance_preflight_enabled": bool(
            contract["authority_first_segment_invariance_audit"]
        ),
        "preflight_excluded_from_service": float(
            summary["authority_preflight_seconds_excluded_from_service"]
        )
        > 0.0,
    }
    return {
        "model": expected_model,
        "mode": expected_mode,
        "path": path.as_posix(),
        "sha256": sha256(path),
        "code_commit": environment["code_commit"],
        "contract_digest": payload["contract_digest"],
        "checks": checks,
        "pass": all(checks.values()),
        "metrics": {
            "events": int(summary["events"]),
            "final_sessions": int(summary["final_sessions"]),
            "final_exact_sessions": int(summary["final_exact_sessions"]),
            "deployed_wall_speedup": float(summary["deployed_wall_speedup"]),
            "gpu_normalized_speedup": float(
                summary["gpu_normalized_speedup"]
            ),
            "energy_reduction_fraction": float(
                summary["energy_reduction_fraction"]
            ),
            "display_latency_seconds_p99": float(
                summary["display_latency_seconds_p99"]
            ),
            "segment_commit_latency_seconds_p99": float(
                summary["segment_commit_latency_seconds_p99"]
            ),
            "final_unit_edit_rate_median": float(
                summary["final_unit_edit_rate_median"]
            ),
            "final_unit_edit_rate_p95": float(
                summary["final_unit_edit_rate_p95"]
            ),
            "final_unit_edit_rate_max": float(
                summary["final_unit_edit_rate_max"]
            ),
            "fine_replay_fraction": float(summary["fine_replay_fraction"]),
            "authority_to_proposer_ratio": float(
                summary["authority_to_proposer_ratio"]
            ),
            "transaction_install_violations": int(
                summary["transaction_install_violations"]
            ),
            "authority_batch_repeat_mismatches": int(
                summary["authority_batch_repeat_mismatches"]
            ),
            "authority_batch_vs_singleton_mismatches": int(
                summary["authority_batch_vs_singleton_mismatches"]
            ),
        },
    }


def build_markdown(result: dict[str, Any]) -> str:
    rows = []
    for cell in result["cells"]:
        m = cell["metrics"]
        rows.append(
            "| {model} | {mode} | {wall:.2f}x | {gpu:.2f}x | {energy:.1f}% | "
            "{replay:.2f}% | {exact}/{sessions} | {p95:.2f}% | {worst:.2f}% | "
            "{tx} | {inv} |".format(
                model=cell["model"].replace("Qwen3-ASR-", ""),
                mode=cell["mode"],
                wall=m["deployed_wall_speedup"],
                gpu=m["gpu_normalized_speedup"],
                energy=100.0 * m["energy_reduction_fraction"],
                replay=100.0 * m["fine_replay_fraction"],
                exact=m["final_exact_sessions"],
                sessions=m["final_sessions"],
                p95=100.0 * m["final_unit_edit_rate_p95"],
                worst=100.0 * m["final_unit_edit_rate_max"],
                tx=m["transaction_install_violations"],
                inv=(
                    m["authority_batch_repeat_mismatches"]
                    + m["authority_batch_vs_singleton_mismatches"]
                ),
            )
        )
    return "\n".join(
        [
            "# R10 Qwen cross-adapter machine summary",
            "",
            f"Decision: **{result['decision']}**",
            "",
            "| Model | Adapter | Wall | GPU-normalized | Energy reduction | "
            "Fine replay | Exact sessions | Edit P95 | Edit max | Tx violations | "
            "Authority mismatches |",
            "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
            *rows,
            "",
            "The FP32 batched authority establishes a new concurrency-invariant "
            "canonical path; it is not claimed to reproduce the original FP16 "
            "singleton trajectory bit-for-bit.",
            "",
        ]
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir", type=Path, required=True)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    parser.add_argument("--output-md", type=Path, required=True)
    args = parser.parse_args()

    config = load_json(args.config)
    gates = config["gates"]
    missing = [
        filename
        for filename in EXPECTED.values()
        if not (args.input_dir / filename).is_file()
    ]
    if missing:
        raise SystemExit(f"missing required R10 result files: {missing}")

    cells = [
        audit_cell(args.input_dir / filename, model, mode, gates)
        for (model, mode), filename in EXPECTED.items()
    ]
    commits = sorted({cell["code_commit"] for cell in cells})
    common_checks = {
        "all_four_cells_present": len(cells) == 4,
        "single_code_commit": len(commits) == 1,
        "all_cells_pass": all(cell["pass"] for cell in cells),
    }
    decision = (
        "PASS_R10_QWEN_CROSS_ADAPTER_MATRIX"
        if all(common_checks.values())
        else "FAIL_R10_QWEN_CROSS_ADAPTER_MATRIX"
    )
    result = {
        "schema_version": 1,
        "decision": decision,
        "common_checks": common_checks,
        "code_commits": commits,
        "cells": cells,
        "aggregate": {
            "total_events": sum(cell["metrics"]["events"] for cell in cells),
            "minimum_wall_speedup": min(
                cell["metrics"]["deployed_wall_speedup"] for cell in cells
            ),
            "maximum_wall_speedup": max(
                cell["metrics"]["deployed_wall_speedup"] for cell in cells
            ),
            "minimum_gpu_normalized_speedup": min(
                cell["metrics"]["gpu_normalized_speedup"] for cell in cells
            ),
            "maximum_energy_reduction_fraction": max(
                cell["metrics"]["energy_reduction_fraction"] for cell in cells
            ),
            "minimum_energy_reduction_fraction": min(
                cell["metrics"]["energy_reduction_fraction"] for cell in cells
            ),
            "maximum_p95_unit_edit_rate": max(
                cell["metrics"]["final_unit_edit_rate_p95"] for cell in cells
            ),
            "maximum_unit_edit_rate": max(
                cell["metrics"]["final_unit_edit_rate_max"] for cell in cells
            ),
            "total_transaction_violations": sum(
                cell["metrics"]["transaction_install_violations"]
                for cell in cells
            ),
            "total_authority_invariance_mismatches": sum(
                cell["metrics"]["authority_batch_repeat_mismatches"]
                + cell["metrics"]["authority_batch_vs_singleton_mismatches"]
                for cell in cells
            ),
        },
        "claim_boundary": (
            "The common RevTrace transaction core admits DGFT-style coarse "
            "authority and hybrid native replay on two Qwen3-ASR scales. The "
            "FP32 authority is a versioned canonical execution path, not a "
            "bitwise repair of the original FP16 singleton trajectory."
        ),
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    args.output_md.write_text(build_markdown(result), encoding="utf-8")
    print(json.dumps({"decision": decision, **result["aggregate"]}, indent=2))
    return 0 if decision.startswith("PASS") else 2


if __name__ == "__main__":
    raise SystemExit(main())

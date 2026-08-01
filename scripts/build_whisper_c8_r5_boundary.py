#!/usr/bin/env python3
"""Freeze the Whisper base/c8 r5 risk and performance boundary evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir", type=Path, required=True)
    parser.add_argument("--summary", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    return parser.parse_args()


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    args = parse_args()
    root = args.input_dir
    policy_path = root / "w4-state-age-policy-base-c8-m80-recovery-r5.json"
    certificate_paths = [
        root / "w4-risk-base-c8-m80-workv1-fixed-r5-seed20273400.json",
        root / "w4-risk-base-c8-m80-workv1-fixed-r5-seed20273450.json",
    ]
    variant_paths = {
        "dual_lane1": root / "w5-base-c8-r5-fixed-preflight-seed20273519.json",
        "dual_lane2": root / "w5-base-c8-r5-lanes2-seed20273519.json",
        "dual_lane4": root / "w5-base-c8-r5-lanes4-seed20273519.json",
        "colocated_lane1": (
            root / "w5-base-c8-r5-colocated-accountingfix-seed20273519.json"
        ),
    }

    policy = load(policy_path)
    selected = policy["selected_policy"]
    certificates = [load(path) for path in certificate_paths]
    for row in certificates:
        assert row["decision"] == "W4_RISK_CERTIFICATE_PASS"
        assert row["counts"]["risk_eligible_entries"] >= 30_000
        assert row["counts"]["pre_outcome_randomized_audits"] >= 500
        assert row["counts"]["caught_state_errors"] == 0
        assert row["risk_certificate"]["upper_risk"] <= 0.005
        assert Path(row["config"]["policy_source"]).name == policy_path.name

    variants: dict[str, dict[str, Any]] = {}
    for name, path in variant_paths.items():
        row = load(path)
        counts = row["counts"]
        metrics = row["metrics"]
        assert counts["state_violations"] == 0
        assert counts["stale_commits"] == 0
        assert counts["post_timing_stable_output_mismatches"] == 0
        assert counts["post_timing_stable_state_mismatches"] == 0
        variants[name] = {
            "wall_speedup": metrics["wall_speedup"],
            "gpu_normalized_speedup": metrics["gpu_normalized_speedup"],
            "display_slo_goodput_speedup": (
                metrics["display_slo_goodput_speedup"]
            ),
            "state_latency_p99_seconds": metrics["latency_p99"],
            "display_latency_p99_seconds": metrics["display_latency_p99"],
            "verification_fraction": metrics["verification_fraction"],
            "energy_reduction": metrics["energy_reduction"],
            "physical_gpu_count": (
                1 if name == "colocated_lane1" else 2
            ),
            "source": str(path),
            "source_sha256": sha256(path),
        }

    production_gate = {
        "wall_speedup_min": 2.0,
        "gpu_normalized_speedup_min": 1.0,
        "display_slo_goodput_speedup_min": 2.0,
        "state_latency_p99_seconds_max": 4.0,
        "verification_fraction_max": 0.20,
        "energy_reduction_min": 0.15,
    }

    def passes(row: dict[str, Any]) -> bool:
        return (
            row["wall_speedup"] >= production_gate["wall_speedup_min"]
            and row["gpu_normalized_speedup"]
            >= production_gate["gpu_normalized_speedup_min"]
            and row["display_slo_goodput_speedup"]
            >= production_gate["display_slo_goodput_speedup_min"]
            and row["state_latency_p99_seconds"]
            <= production_gate["state_latency_p99_seconds_max"]
            and row["verification_fraction"]
            <= production_gate["verification_fraction_max"]
            and row["energy_reduction"]
            >= production_gate["energy_reduction_min"]
        )

    pass_map = {name: passes(row) for name, row in variants.items()}
    summary = {
        "schema_version": 1,
        "study": "Whisper base/c8 r5 risk closure and capacity boundary",
        "decision": "R5_RISK_PASS_C8_PERFORMANCE_BOUNDARY",
        "risk": {
            "policy_sha256": sha256(policy_path),
            "adaptation_roots": policy["counts"]["adaptation_roots"],
            "calibration_verification_fraction": selected[
                "verification_fraction"
            ],
            "risk_entries": sum(
                row["counts"]["risk_eligible_entries"]
                for row in certificates
            ),
            "random_audits": sum(
                row["counts"]["pre_outcome_randomized_audits"]
                for row in certificates
            ),
            "caught_state_errors": 0,
            "maximum_time_uniform_upper_risk": max(
                row["risk_certificate"]["upper_risk"]
                for row in certificates
            ),
            "certificate_sources": [
                {"path": str(path), "sha256": sha256(path)}
                for path in certificate_paths
            ],
        },
        "production_gate": production_gate,
        "variants": variants,
        "variant_pass": pass_map,
        "claim_boundary": (
            "The frozen r5 state-risk contract passes two independent "
            "certificates. No tested c8 deployment topology passes the "
            "complete production performance gate; c8 is a low-load "
            "capacity boundary, not a Whisper-wide or RevTrace-wide failure."
        ),
    }
    args.summary.parent.mkdir(parents=True, exist_ok=True)
    args.summary.write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    lines = [
        "# Whisper base/c8 r5 closure",
        "",
        "Decision: `R5_RISK_PASS_C8_PERFORMANCE_BOUNDARY`.",
        "",
        "## Risk contract",
        "",
        f"- Frozen policy SHA-256: `{summary['risk']['policy_sha256']}`.",
        f"- Adaptation-only roots covered: {summary['risk']['adaptation_roots']}.",
        f"- Independent risk entries: {summary['risk']['risk_entries']:,}.",
        f"- Pre-outcome randomized canonical audits: {summary['risk']['random_audits']:,}.",
        "- Caught state-entry errors: 0.",
        (
            "- Maximum time-uniform 95% upper risk: "
            f"{100 * summary['risk']['maximum_time_uniform_upper_risk']:.4f}%."
        ),
        (
            "- Calibration verification fraction: "
            f"{100 * summary['risk']['calibration_verification_fraction']:.2f}%."
        ),
        "",
        "## Performance boundary",
        "",
        "| Variant | GPUs | Wall | GPU-normalized | Display-SLO | State P99 | Verify | Energy reduction | Full gate |",
        "|---|---:|---:|---:|---:|---:|---:|---:|:---:|",
    ]
    for name, row in variants.items():
        lines.append(
            f"| {name} | {row['physical_gpu_count']} | "
            f"{row['wall_speedup']:.3f}x | "
            f"{row['gpu_normalized_speedup']:.3f}x | "
            f"{row['display_slo_goodput_speedup']:.3f}x | "
            f"{row['state_latency_p99_seconds']:.3f}s | "
            f"{100 * row['verification_fraction']:.2f}% | "
            f"{100 * row['energy_reduction']:.2f}% | "
            f"{'PASS' if pass_map[name] else 'FAIL'} |"
        )
    lines.extend([
        "",
        "The risk mechanism succeeds, but no tested c8 topology achieves the",
        "complete production gate. Extra verifier lanes degrade performance;",
        "physical-GPU colocation fixes resource efficiency but not wall/SLO",
        "speedup. The defensible conclusion is a c8 low-load capacity boundary.",
        "",
        "## Accounting repair",
        "",
        "The colocated run exposed a resource-accounting defect: logical",
        "proposer/verifier roles on the same CUDA device were charged as two",
        "physical GPUs and their power was sampled twice. The runner now",
        "deduplicates process-visible CUDA indices. Dual-GPU results are",
        "unchanged; only colocated accounting required a rerun.",
        "",
    ])
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps({
        "decision": summary["decision"],
        "risk_entries": summary["risk"]["risk_entries"],
        "random_audits": summary["risk"]["random_audits"],
        "variant_pass": pass_map,
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

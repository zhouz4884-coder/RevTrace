#!/usr/bin/env python3
"""Freeze the auditable Phase R8 evidence summary.

This finalizer never upgrades an observed-zero result to a mathematical
certificate and keeps the preregistered service gate separate from the best
observed operating point.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import statistics
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--results", type=Path, default=Path("results/r8_csdr"))
    p.add_argument(
        "--service-dir",
        type=Path,
        default=Path("results/r8_csdr/service-budgeted-cutset-p32r48"),
    )
    p.add_argument(
        "--output", type=Path,
        default=Path("results/r8_csdr/phase_r8_summary.json"),
    )
    return p.parse_args()


def read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def quantile(values: list[float], q: float) -> float:
    rows = sorted(values)
    if not rows:
        raise ValueError("quantile requires non-empty values")
    position = (len(rows) - 1) * q
    lower = int(position)
    upper = min(lower + 1, len(rows) - 1)
    weight = position - lower
    return rows[lower] * (1.0 - weight) + rows[upper] * weight


def service_summary(paths: list[Path]) -> dict[str, Any]:
    rows = []
    for path in paths:
        payload = read(path)
        metrics = payload["metrics"]
        rows.append({
            "file": path.name,
            "arrival": payload["config"]["arrival"],
            "seed": payload["config"]["seed"],
            **metrics,
        })
    def aggregate(key: str) -> dict[str, float]:
        values = [float(row[key]) for row in rows]
        return {
            "minimum": min(values),
            "median": statistics.median(values),
            "maximum": max(values),
            "q25": quantile(values, 0.25),
            "q75": quantile(values, 0.75),
        }

    formal_pass = bool(rows) and (
        aggregate("wall_speedup")["median"] >= 2.5
        and aggregate("display_latency_p99")["maximum"] <= 1.9
        and aggregate("state_latency_p99")["maximum"] <= 1.9
        and aggregate("energy_reduction")["minimum"] >= 0.40
        and sum(int(row["stale_installs"]) for row in rows) == 0
        and sum(int(row["lineage_violations"]) for row in rows) == 0
    )
    return {
        "formal_gate": "PASS_R8_5_SERVICE" if formal_pass else "FAIL_R8_5_SERVICE",
        "runs": len(rows),
        "wall_speedup": aggregate("wall_speedup"),
        "gpu_normalized_speedup": aggregate("gpu_normalized_speedup"),
        "display_latency_p99_seconds": aggregate("display_latency_p99"),
        "state_latency_p99_seconds": aggregate("state_latency_p99"),
        "energy_reduction": aggregate("energy_reduction"),
        "total_stale_installs": sum(int(row["stale_installs"]) for row in rows),
        "total_lineage_violations": sum(int(row["lineage_violations"]) for row in rows),
        "total_cutset_singleton_replays": sum(
            int(row["cutset_singleton_replays"]) for row in rows
        ),
        "total_proposal_authority_holds": sum(
            int(row.get("proposal_authority_holds", 0)) for row in rows
        ),
        "best_observed": max(rows, key=lambda row: row["wall_speedup"]),
        "rows": rows,
    }


def main() -> int:
    args = parse_args()
    result_files = {
        "information_gate": args.results / "budgeted-oracle.json",
        "csm": args.results / "csm-frozen-forest.json",
        "primary_quality": args.results / "r8-pristine-dev-budget48-fullcontext.json",
        "confirmatory_quality": (
            args.results / "r8-pristine-confirm-budget48-fullcontext.json"
        ),
        "risk_audit": args.results / "r8-replay-audit-30k-v2.json",
    }
    missing = [str(path) for path in result_files.values() if not path.exists()]
    if missing:
        raise FileNotFoundError(f"missing final R8 evidence: {missing}")

    information = read(result_files["information_gate"])
    csm = read(result_files["csm"])
    primary = read(result_files["primary_quality"])
    confirmatory = read(result_files["confirmatory_quality"])
    audit = read(result_files["risk_audit"])
    services = service_summary(sorted(args.service_dir.glob("w[12]-seed*.json")))
    small_quality_path = (
        args.results / "r8-pristine-small-confirm-budget48-fullcontext.json"
    )
    small_service_path = args.service_dir / "small-transfer-seed2026083001.json"
    small_transfer = None
    if small_quality_path.exists() and small_service_path.exists():
        small_quality = read(small_quality_path)
        small_service = read(small_service_path)
        small_transfer = {
            "quality_decision": small_quality["decision"],
            "quality_metrics": small_quality["metrics"],
            "service_decision": small_service["decision"],
            "service_metrics": small_service["metrics"],
            "quality_sha256": sha256(small_quality_path),
            "service_sha256": sha256(small_service_path),
            "boundary": (
                "zero-shot scale transfer using the base frozen control "
                "policy; not pooled with the base confirmatory gate"
            ),
        }

    deterministic = (
        services["total_stale_installs"] == 0
        and services["total_lineage_violations"] == 0
        and primary["metrics"]["semantic_violations"] == 0
        and confirmatory["metrics"]["semantic_violations"] == 0
    )
    quality_pass = all(
        payload["decision"] == "PASS_R8_4_FROZEN_QUALITY"
        for payload in (primary, confirmatory)
    )
    payload = {
        "schema_version": 1,
        "study": "RevTrace Phase R8 Safe Context Reanchoring",
        "decision": (
            "R8_CORE_QUALITY_RISK_PASS_SERVICE_BOUNDARY_DISCLOSED"
            if quality_pass and deterministic
            else "R8_NOT_READY"
        ),
        "gates": {
            "information": information["decision"],
            "sufficiency_monitor": csm["decision"],
            "primary_quality": primary["decision"],
            "confirmatory_quality": confirmatory["decision"],
            "service": services["formal_gate"],
            "risk_audit": audit["decision"],
        },
        "information_metrics": information["metrics"],
        "csm_metrics": csm["cross_validation"],
        "primary_quality_metrics": primary["metrics"],
        "confirmatory_quality_metrics": confirmatory["metrics"],
        "service_metrics": services,
        "risk_metrics": audit["metrics"],
        "whisper_small_transfer": small_transfer,
        "claim_boundaries": {
            "margin": "empirical scheduling signal, not deterministic certificate",
            "csm": "high-recall scheduler, never feedback authority",
            "ordinary_batch": "not claimed bitwise singleton exact",
            "service": (
                "report best and matrix distribution; do not promote a failed "
                "preregistered energy gate to PASS"
            ),
            "observed_zero": "reported with time-uniform statistical UCB",
        },
        "evidence_sha256": {
            key: sha256(path) for key, path in result_files.items()
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "decision": payload["decision"],
        "service_gate": services["formal_gate"],
        "service_runs": services["runs"],
        "service_wall_median": services["wall_speedup"]["median"],
        "service_energy_median": services["energy_reduction"]["median"],
    }))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

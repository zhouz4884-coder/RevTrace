#!/usr/bin/env python3
"""Merge Qwen and Whisper evidence into one paper-level audit artifact."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--qwen-performance",
        type=Path,
        default=Path("results/phase7_1/performance_comparison.json"),
    )
    parser.add_argument(
        "--qwen-tail",
        type=Path,
        default=Path("results/tail_robust/summary.json"),
    )
    parser.add_argument(
        "--qwen-submission",
        type=Path,
        default=Path(
            "results/checkpoint20_holdback_authority/final_summary_v2.json"
        ),
    )
    parser.add_argument(
        "--whisper",
        type=Path,
        default=Path("results/whisper_w0_w7/w7-summary.json"),
    )
    parser.add_argument(
        "--output-json",
        type=Path,
        default=Path("results/paper_evidence/summary.json"),
    )
    parser.add_argument(
        "--output-md",
        type=Path,
        default=Path("results/paper_evidence/REPORT.md"),
    )
    return parser.parse_args()


def read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def finite(values: list[float | None]) -> list[float]:
    return [
        float(value) for value in values
        if value is not None and math.isfinite(float(value))
    ]


def fmt(value: float | None, digits: int = 3) -> str:
    if value is None or not math.isfinite(float(value)):
        return "NA"
    return f"{float(value):.{digits}f}"


def whisper_headline(row: dict[str, Any], model: str) -> dict[str, Any]:
    cells = [
        row["matrix"][model][cell]["revtrace"]
        for cell in ("W1", "W2", "W3", "W4")
    ]
    wall = finite([cell["median_wall_speedup"] for cell in cells])
    gpu = finite([
        cell["median_gpu_normalized_speedup"] for cell in cells
    ])
    goodput = finite([
        cell["median_slo_goodput_speedup"] for cell in cells
    ])
    p99 = finite([cell["maximum_p99_seconds"] for cell in cells])
    energy = finite([
        cell["minimum_energy_reduction"] for cell in cells
    ])
    verification = finite([
        cell["maximum_verification_fraction"] for cell in cells
    ])
    return {
        "production_cells_passed": sum(
            bool(cell["joint_gate_pass"]) for cell in cells
        ),
        "production_cells": 4,
        "minimum_wall_speedup": min(wall) if wall else None,
        "minimum_gpu_normalized_speedup": min(gpu) if gpu else None,
        "minimum_slo_goodput_speedup": min(goodput) if goodput else None,
        "maximum_p99_seconds": max(p99) if p99 else None,
        "minimum_energy_reduction": min(energy) if energy else None,
        "maximum_verification_fraction": (
            max(verification) if verification else None
        ),
        "state_violations": sum(
            int(cell["state_violations"]) for cell in cells
        ),
        "stale_commits": sum(
            int(cell["stale_commits"]) for cell in cells
        ),
        "quality": row["quality"][model],
    }


def main() -> int:
    args = parse_args()
    qwen_performance = read(args.qwen_performance)
    qwen_tail = read(args.qwen_tail)
    qwen_submission = read(args.qwen_submission)
    whisper = read(args.whisper)

    qwen_rows = []
    replications = qwen_performance["five_run_replication"]
    risk_by_model = {
        row["model"]: row
        for row in qwen_performance["formal_anytime_risk"]
    }
    for row in qwen_performance["headline_revtrace"]:
        model = row["model"]
        qwen_rows.append({
            **row,
            "five_run": replications[model],
            "formal_risk": risk_by_model[model],
        })

    whisper_rows = {
        model: whisper_headline(whisper, model)
        for model in ("whisper-base.en", "whisper-small.en")
    }
    complete = (
        whisper.get("decision") == "W7_CROSS_FAMILY_STRONG_PASS"
        and qwen_submission.get("decision")
        == "REVTRACE_EXPERIMENTAL_EVIDENCE_COMPLETE_FOR_FGCS_SUBMISSION"
        and qwen_tail.get("decision")
        == "TAIL_ROBUST_C12_PASS_WITH_120S_AGE_BOUNDARY"
    )
    output = {
        "schema_version": 1,
        "study": "RevTrace whole-paper evidence synthesis",
        "decision": (
            "PAPER_EVIDENCE_COMPLETE"
            if complete else "PAPER_EVIDENCE_INCOMPLETE_OR_BOUNDARY"
        ),
        "thesis": (
            "Generated output has no authority to mutate future feedback "
            "state until an architecture-specific state-entry contract "
            "admits or canonically resolves the transition."
        ),
        "method_contributions": [
            "architecture-specific state-entry projection",
            "contract-scoped dynamic risk control",
            "canonical state authority",
            "versioned revision transactions with stale-result rejection",
            "checkpoint, rebase and provisional holdback",
        ],
        "engineering_substrate_not_claimed_as_novelty": [
            "ordinary batching",
            "dtype selection",
            "model adapter code",
            "queue implementation",
        ],
        "generality": {
            "families": 2,
            "headline_checkpoints": 4,
            "qwen_projection": "rollback and globally retokenized revision state",
            "whisper_projection": (
                "bounded raw previous-segment token prompt state"
            ),
            "whisper_role": (
                "independent architecture and scale evidence, not paper identity"
            ),
        },
        "qwen": {
            "headline": qwen_rows,
            "overlap_ablation": qwen_performance[
                "live_overlap_ablation"
            ],
            "dynamic_contract_sequence": qwen_performance[
                "live_dynamic_contract_sequence"
            ],
            "tail_boundary": qwen_tail["decision"],
            "submission_decision": qwen_submission["decision"],
        },
        "whisper": {
            "decision": whisper["decision"],
            "production_cells_passed": whisper[
                "production_cells_passed"
            ],
            "production_cells_total": whisper[
                "production_cells_total"
            ],
            "w3_feedback_mechanism": whisper[
                "w3_feedback_mechanism"
            ],
            "risk": whisper["risk"],
            "headline": whisper_rows,
        },
        "causal_attribution": [
            (
                "Same-executor comparisons hold model, dtype, decoder, "
                "hardware, input and arrival trace fixed."
            ),
            (
                "Feedback-OFF isolates the physical cost of the feedback "
                "dependency but is not a functionally equivalent baseline."
            ),
            (
                "Unsafe batch measures the throughput opportunity; "
                "all-canonical measures the safe cost ceiling."
            ),
            (
                "Fixed verification and LocalAgreement separate state-write "
                "authority from a scalar gate and display stabilization."
            ),
        ],
        "claim_boundaries": [
            "risk-bounded semantic conformance is not floating-point determinism",
            "zero observed failures is always paired with an upper bound",
            "120-second Qwen traces retain an explicit age boundary",
            "published text-LLM systems are contextual, not direct leaderboard rows",
        ],
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(
        json.dumps(output, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    lines = [
        "# RevTrace whole-paper evidence",
        "",
        f"Decision: `{output['decision']}`.",
        "",
        "## Paper thesis",
        "",
        output["thesis"],
        "",
        "## Qwen3-ASR headline",
        "",
        "| Model | Wall | GPU-normalized | P99 | Five-run mean | Risk UCB |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for row in qwen_rows:
        lines.append(
            f"| {row['model']} | {float(row['wall_speedup']):.3f}x | "
            f"{float(row['gpu_normalized_speedup']):.3f}x | "
            f"{float(row['p99_state_entry_seconds']):.3f}s | "
            f"{row['five_run']['wall_speedup_mean']:.3f}x | "
            f"{100 * row['formal_risk']['time_uniform_upper_risk']:.3f}% |"
        )
    lines.extend([
        "",
        "## Whisper cross-family closure",
        "",
        "| Model | Cells | Min wall | Min GPU-normalized | Max P99 | Min energy reduction | Max verify |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ])
    for model, row in whisper_rows.items():
        lines.append(
            f"| {model} | {row['production_cells_passed']}/4 | "
            f"{fmt(row['minimum_wall_speedup'])}x | "
            f"{fmt(row['minimum_gpu_normalized_speedup'])}x | "
            f"{fmt(row['maximum_p99_seconds'])}s | "
            f"{fmt(100 * row['minimum_energy_reduction'], 1) if row['minimum_energy_reduction'] is not None else 'NA'}% | "
            f"{fmt(100 * row['maximum_verification_fraction'], 1) if row['maximum_verification_fraction'] is not None else 'NA'}% |"
        )
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return 0 if complete else 2


if __name__ == "__main__":
    raise SystemExit(main())

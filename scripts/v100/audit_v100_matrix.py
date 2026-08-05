#!/usr/bin/env python3
"""Independently audit a completed RevTrace V100 V1--V4 matrix.

This script deliberately reloads every raw cell and recomputes the paper-facing
counts and headline quantities.  It does not trust the runner's aggregate
fields beyond checking that they agree with the raw records.
"""

from __future__ import annotations

import argparse
import json
import math
from collections import Counter
from pathlib import Path
from typing import Any


EXPECTED_PHASE_COUNTS = {"V1": 24, "V2": 16, "V3": 32, "V4": 12}
MODELS = ("Qwen3-ASR-0.6B", "Qwen3-ASR-1.7B")


def read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path: Path, payload: Any) -> None:
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def finite_numbers(value: Any, where: str, errors: list[str]) -> None:
    if isinstance(value, float) and not math.isfinite(value):
        errors.append(f"non-finite number at {where}: {value!r}")
    elif isinstance(value, dict):
        for key, child in value.items():
            finite_numbers(child, f"{where}.{key}", errors)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            finite_numbers(child, f"{where}[{index}]", errors)


def by_cell(cells: list[dict[str, Any]], cell_id: str) -> dict[str, Any]:
    matches = [cell for cell in cells if cell["cell_id"] == cell_id]
    if len(matches) != 1:
        raise AssertionError(f"expected one cell {cell_id}, found {len(matches)}")
    return matches[0]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", type=Path, required=True)
    args = parser.parse_args()
    run_dir = args.run_dir.resolve()
    summary_path = run_dir / "v1_v4_summary.json"
    raw_dir = run_dir / "raw"

    errors: list[str] = []
    checks: list[dict[str, Any]] = []

    def check(name: str, condition: bool, detail: Any) -> None:
        checks.append({"name": name, "pass": bool(condition), "detail": detail})
        if not condition:
            errors.append(f"{name}: {detail}")

    summary = read_json(summary_path)
    raw_files = sorted(raw_dir.glob("*.json"))
    failure_files = sorted(raw_dir.glob("*.failure.json"))
    cells = [read_json(path) for path in raw_files if not path.name.endswith(".failure.json")]
    ids = [str(cell.get("cell_id")) for cell in cells]
    phase_counts = dict(sorted(Counter(str(cell.get("phase")) for cell in cells).items()))

    check("raw_cell_count", len(cells) == 84, len(cells))
    check("failure_file_count", not failure_files, [path.name for path in failure_files])
    check("unique_cell_ids", len(set(ids)) == len(ids), len(ids) - len(set(ids)))
    check("phase_counts", phase_counts == EXPECTED_PHASE_COUNTS, phase_counts)
    check("summary_completed", summary.get("completed_cells") == 84, summary.get("completed_cells"))
    check("summary_failed", summary.get("failed_cells") == 0, summary.get("failed_cells"))
    check("summary_phase_counts", summary.get("phase_counts") == EXPECTED_PHASE_COUNTS, summary.get("phase_counts"))

    summary_cells = {str(cell["cell_id"]): cell for cell in summary.get("cells", [])}
    check("summary_cell_ids", set(summary_cells) == set(ids), {
        "missing": sorted(set(ids) - set(summary_cells)),
        "extra": sorted(set(summary_cells) - set(ids)),
    })
    raw_summary_equal = all(summary_cells.get(str(cell["cell_id"])) == cell for cell in cells)
    check("raw_summary_bitwise_json_equality", raw_summary_equal, raw_summary_equal)

    for path, cell in zip([p for p in raw_files if not p.name.endswith(".failure.json")], cells):
        finite_numbers(cell, path.name, errors)
        check(f"filename_matches:{path.name}", path.stem == cell.get("cell_id"), cell.get("cell_id"))
        power = cell.get("power", {})
        check(f"positive_energy:{path.name}", float(power.get("energy_joules", 0)) > 0, power.get("energy_joules"))

        phase = cell["phase"]
        if phase == "V2":
            check(f"v2_display_denominator:{path.name}", cell.get("display_events") == 240, cell.get("display_events"))
            if "reference_final_sessions" in cell:
                check(f"v2_session_denominator:{path.name}", cell.get("reference_final_sessions") == 16, cell.get("reference_final_sessions"))
            check(f"v2_state_count:{path.name}", len(cell.get("final_states", [])) == 16, len(cell.get("final_states", [])))
            check(f"v2_transaction_invariant:{path.name}", cell.get("transaction_install_violations") == 0, cell.get("transaction_install_violations"))
            if "uncertified_risky_commits" in cell:
                check(f"v2_risky_commit_invariant:{path.name}", cell.get("uncertified_risky_commits") == 0, cell.get("uncertified_risky_commits"))
            if "uncertified_ancestry_violations" in cell:
                check(f"v2_ancestry_invariant:{path.name}", cell.get("uncertified_ancestry_violations") == 0, cell.get("uncertified_ancestry_violations"))
            if "directional_omission_events" in cell:
                check(f"v2_direction_invariant:{path.name}", cell.get("directional_omission_events") == 0, cell.get("directional_omission_events"))
        elif phase == "V3":
            expected_events = int(cell["concurrency"]) * 15
            check(f"v3_display_denominator:{path.name}", cell.get("display_events") == expected_events, cell.get("display_events"))
            check(f"v3_state_count:{path.name}", len(cell.get("final_states", [])) == int(cell["concurrency"]), len(cell.get("final_states", [])))
            check(f"v3_transaction_invariant:{path.name}", cell.get("transaction_install_violations") == 0, cell.get("transaction_install_violations"))
            check(f"v3_ancestry_invariant:{path.name}", cell.get("uncertified_ancestry_violations") == 0, cell.get("uncertified_ancestry_violations"))
            check(f"v3_direction_invariant:{path.name}", cell.get("directional_omission_events") == 0, cell.get("directional_omission_events"))
        elif phase == "V4":
            check(f"v4_display_denominator:{path.name}", cell.get("display_events") == 240, cell.get("display_events"))
            check(f"v4_state_count:{path.name}", len(cell.get("final_states", [])) == 16, len(cell.get("final_states", [])))
            check(f"v4_transaction_invariant:{path.name}", cell.get("transaction_install_violations") == 0, cell.get("transaction_install_violations"))
            check(f"v4_ancestry_invariant:{path.name}", cell.get("uncertified_ancestry_violations") == 0, cell.get("uncertified_ancestry_violations"))
            check(f"v4_direction_invariant:{path.name}", cell.get("directional_omission_events") == 0, cell.get("directional_omission_events"))

    headlines: dict[str, Any] = {}
    for model in MODELS:
        singleton = by_cell(cells, f"v2-{model}-all-singleton-c16")
        sg = by_cell(cells, f"v2-{model}-revtrace-sg-c16")
        coarse = by_cell(cells, f"v2-{model}-coarse-dgft-c16")
        hybrid = by_cell(cells, f"v2-{model}-hybrid-dgft-c16")
        p1_c64 = by_cell(cells, f"v3-{model}-p1a1-c64")
        p4_c64 = by_cell(cells, f"v3-{model}-p4a4-c64")
        p4_c128 = by_cell(cells, f"v3-{model}-p4a4-c128")
        v3_model = [cell for cell in cells if cell["phase"] == "V3" and cell["model"] == model]
        p4_cells = sorted(
            (cell for cell in v3_model if cell["proposer_replicas"] == 4 and cell["authority_replicas"] == 4),
            key=lambda cell: int(cell["concurrency"]),
        )
        passing = [cell for cell in p4_cells if float(cell["display_latency_p99_seconds"]) <= 2.0]
        honest_capacity = max((int(cell["concurrency"]) for cell in passing), default=0)

        headlines[model] = {
            "v2_sg_wall_speedup_vs_singleton": singleton["wall_seconds"] / sg["wall_seconds"],
            "v2_coarse_wall_speedup_vs_singleton": singleton["wall_seconds"] / coarse["wall_seconds"],
            "v2_hybrid_wall_speedup_vs_singleton": singleton["wall_seconds"] / hybrid["wall_seconds"],
            "v2_sg_display_p99_seconds": sg["display_latency_p99_seconds"],
            "v2_sg_verification_fraction": sg["verification_fraction"],
            "v2_sg_edit_p95": sg["reference_final_edit_rate_p95"],
            "v3_p4a4_c64_audio_xrt": p4_c64["audio_throughput_x_realtime"],
            "v3_p4a4_c64_display_p99_seconds": p4_c64["display_latency_p99_seconds"],
            "v3_p4a4_c64_scale_efficiency_vs_p1a1": (
                p4_c64["audio_throughput_x_realtime"]
                / p1_c64["audio_throughput_x_realtime"]
                / 4
            ),
            "v3_honest_capacity_at_display_p99_le_2s": honest_capacity,
            "v3_p4a4_c128_audio_xrt": p4_c128["audio_throughput_x_realtime"],
            "v3_p4a4_c128_display_p99_seconds": p4_c128["display_latency_p99_seconds"],
            "v1_max_fp16_requests_per_second": max(
                cell["requests_per_second"] for cell in cells
                if cell["phase"] == "V1" and cell["model"] == model and cell["dtype"] == "float16"
            ),
            "v1_batch_repeat_mismatches_total": sum(
                cell["batch_repeat_token_mismatches"] for cell in cells
                if cell["phase"] == "V1" and cell["model"] == model
            ),
            "v1_batch_vs_singleton_mismatches_total": sum(
                cell["batch_vs_singleton_token_mismatches"] for cell in cells
                if cell["phase"] == "V1" and cell["model"] == model
            ),
        }

    audit = {
        "schema_version": 1,
        "decision": "PASS" if not errors else "FAIL",
        "run_dir": str(run_dir),
        "checks_total": len(checks),
        "checks_passed": sum(item["pass"] for item in checks),
        "errors": errors,
        "phase_counts": phase_counts,
        "headlines": headlines,
        "checks": checks,
        "claim_boundary": (
            "Independent RHEL7/8xV100 Transformers-eager contract; do not pool "
            "absolute results with RTX3090/vLLM. V3 is single-node scale-out."
        ),
    }
    write_json(run_dir / "AUDIT.json", audit)

    lines = [
        "# Independent V100 matrix audit",
        "",
        f"- Decision: **{audit['decision']}**",
        f"- Checks: **{audit['checks_passed']}/{audit['checks_total']}**",
        f"- Phase counts: `{phase_counts}`",
        f"- Errors: **{len(errors)}**",
        "",
        "## Recomputed headline results",
        "",
        "| Model | SG speedup | Hybrid speedup | c64 xRT | c64 P99 | scale efficiency | SLO capacity | c128 P99 |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for model, row in headlines.items():
        lines.append(
            f"| {model} | {row['v2_sg_wall_speedup_vs_singleton']:.3f}x | "
            f"{row['v2_hybrid_wall_speedup_vs_singleton']:.3f}x | "
            f"{row['v3_p4a4_c64_audio_xrt']:.3f} | "
            f"{row['v3_p4a4_c64_display_p99_seconds']:.3f}s | "
            f"{100 * row['v3_p4a4_c64_scale_efficiency_vs_p1a1']:.1f}% | "
            f"c{row['v3_honest_capacity_at_display_p99_le_2s']} | "
            f"{row['v3_p4a4_c128_display_p99_seconds']:.3f}s |"
        )
    lines.extend([
        "",
        "## Boundary",
        "",
        audit["claim_boundary"],
        "Observed zero protocol violations is an empirical result over this matrix, not a mathematical zero-risk claim.",
    ])
    (run_dir / "AUDIT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({
        "decision": audit["decision"],
        "checks": f"{audit['checks_passed']}/{audit['checks_total']}",
        "errors": len(errors),
        "headlines": headlines,
    }, indent=2, ensure_ascii=False))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())

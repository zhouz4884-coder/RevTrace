#!/usr/bin/env python3
"""Audit and render a compact report for the repeated V100 headline matrix."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any


EXPECTED_KEYS = {
    (model, allocation, concurrency)
    for model in ("Qwen3-ASR-0.6B", "Qwen3-ASR-1.7B")
    for allocation, concurrencies in (
        ("p1a1", (64,)),
        ("p4a4", (32, 64, 128)),
        ("p3a5", (64,)),
    )
    for concurrency in concurrencies
}


def finite_metric(block: dict[str, Any], name: str) -> None:
    metric = block[name]
    for field in ("median", "min", "max"):
        value = float(metric[field])
        if not math.isfinite(value):
            raise AssertionError(f"non-finite {name}.{field}: {value}")
    if not (float(metric["min"]) <= float(metric["median"]) <= float(metric["max"])):
        raise AssertionError(f"invalid range ordering for {name}: {metric}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("summary", type=Path)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()

    payload = json.loads(args.summary.read_text(encoding="utf-8"))
    if payload["decision"] != "V5_REPEAT_MATRIX_COMPLETE":
        raise AssertionError(payload["decision"])
    if payload["failed_cells"] != 0 or payload["completed_cells"] != 30:
        raise AssertionError({
            "completed": payload["completed_cells"],
            "failed": payload["failed_cells"],
        })

    rows = {
        (row["model"], row["allocation"], int(row["concurrency"])): row
        for row in payload["aggregates"]
    }
    if set(rows) != EXPECTED_KEYS:
        raise AssertionError({
            "missing": sorted(EXPECTED_KEYS - set(rows)),
            "unexpected": sorted(set(rows) - EXPECTED_KEYS),
        })

    for key, row in rows.items():
        if row["repeats_completed"] != 3 or row["repeat_indices"] != [1, 2, 3]:
            raise AssertionError(f"repeat contract failed for {key}: {row}")
        if row["transaction_install_violations"] != 0:
            raise AssertionError(f"transaction violation in {key}")
        if row["uncertified_ancestry_violations"] != 0:
            raise AssertionError(f"ancestry violation in {key}")
        for metric in (
            "wall_seconds",
            "audio_throughput_x_realtime",
            "display_latency_p99_seconds",
            "commit_latency_p99_seconds",
            "authority_to_proposer_ratio",
            "energy_joules",
            "joules_per_audio_second",
        ):
            finite_metric(row, metric)

    lines = [
        "# RevTrace V5 repeated V100 headline audit",
        "",
        "Decision: **PASS** (30/30 cells, three repeats per configuration).",
        "",
        "| Model | Allocation | c | Audio xRT median [min,max] | Display P99 median [min,max] | Commit P99 median [min,max] | A/P median [min,max] | 2s display misses |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for key in sorted(rows):
        row = rows[key]
        def fmt(name: str, digits: int = 3) -> str:
            value = row[name]
            return (
                f"{float(value['median']):.{digits}f} "
                f"[{float(value['min']):.{digits}f},{float(value['max']):.{digits}f}]"
            )
        lines.append(
            f"| {row['model']} | {row['allocation']} | {row['concurrency']} | "
            f"{fmt('audio_throughput_x_realtime')} | "
            f"{fmt('display_latency_p99_seconds')} s | "
            f"{fmt('commit_latency_p99_seconds')} s | "
            f"{fmt('authority_to_proposer_ratio')} | "
            f"{row['display_slo_2s_misses']}/{row['display_events']} |"
        )

    lines.extend([
        "",
        "## Evidence boundary",
        "",
        "- Display and certified-commit latency are distinct estimands.",
        "- Three deterministic repeats support a median/range report; they do not support a high-powered significance claim.",
        "- The p3a5 cell is an allocation sensitivity derived from the two-stage service model.",
        "- This is single-node V100 evidence and does not establish multi-node scaling or an unbounded asynchronous queue.",
    ])
    report = "\n".join(lines) + "\n"
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(report, encoding="utf-8")
    print(report, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

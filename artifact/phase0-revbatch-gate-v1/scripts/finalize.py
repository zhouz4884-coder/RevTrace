#!/usr/bin/env python3
"""Aggregate live RevBatch results and enforce the sequential gate."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


MODEL_FILES = {
    "Qwen3-ASR-0.6B": "formal-qwen3-asr-0.6b.json",
    "Qwen3-ASR-1.7B": "formal-qwen3-asr-1.7b.json",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--probe-root",
        type=Path,
        default=Path("results/revbatch/probe"),
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=Path("results/revbatch/revbatch_v1"),
    )
    parser.add_argument("--gate-c", type=Path)
    return parser.parse_args()


def gate_a_model(payload: dict[str, Any]) -> dict[str, Any]:
    cells = payload["cells"]
    throughput = max(cell["audio_throughput_speedup"] for cell in cells)
    goodput_values = [
        cell["slo_goodput_speedup"]
        for cell in cells
        if cell["slo_goodput_speedup"] is not None
    ]
    goodput = max(goodput_values) if goodput_values else 0.0
    p99 = max(cell["p99_reduction_fraction"] for cell in cells)
    passed = throughput >= 1.5 or goodput >= 1.5 or p99 >= 0.30
    return {
        "pass": passed,
        "max_audio_throughput_speedup": throughput,
        "max_slo_goodput_speedup": goodput,
        "max_p99_reduction_fraction": p99,
    }


def gate_b_model(payload: dict[str, Any]) -> dict[str, Any]:
    aggregate = payload["aggregate"]
    event_count = int(aggregate["event_count"])
    passed = (
        payload["official_semantics_smoke"]["exact"]
        and event_count >= 1000
        and aggregate["token_exact_match_rate"] == 1.0
        and aggregate["transcript_exact_match_rate"] == 1.0
        and aggregate["final_exact_match_rate"] == 1.0
    )
    return {
        "pass": passed,
        "official_semantics_smoke": payload["official_semantics_smoke"]["exact"],
        "event_count": event_count,
        "token_exact_match_rate": aggregate["token_exact_match_rate"],
        "transcript_exact_match_rate": aggregate["transcript_exact_match_rate"],
        "final_exact_match_rate": aggregate["final_exact_match_rate"],
    }


def compact_cell(model: str, cell: dict[str, Any]) -> dict[str, Any]:
    return {
        "model": model,
        "duration_seconds": cell["duration_seconds"],
        "concurrency": cell["concurrency"],
        "languages": cell["languages"],
        "audio_throughput_speedup": cell["audio_throughput_speedup"],
        "slo_goodput_speedup": cell["slo_goodput_speedup"],
        "p99_reduction_fraction": cell["p99_reduction_fraction"],
        "event_count": cell["comparison"]["event_count"],
        "token_exact_match_rate": cell["comparison"]["token_exact_match_rate"],
        "transcript_exact_match_rate": cell["comparison"][
            "transcript_exact_match_rate"
        ],
        "final_exact_match_rate": cell["comparison"]["final_exact_match_rate"],
        "singleton_audio_throughput": cell["singleton"]["audio_throughput"],
        "batched_audio_throughput": cell["batched"]["audio_throughput"],
        "singleton_p99_seconds": cell["singleton"][
            "p99_event_latency_seconds"
        ],
        "batched_p99_seconds": cell["batched"]["p99_event_latency_seconds"],
    }


def main() -> int:
    args = parse_args()
    payloads = {
        model: json.loads((args.probe_root / filename).read_text(encoding="utf-8"))
        for model, filename in MODEL_FILES.items()
    }
    gate_a_models = {model: gate_a_model(data) for model, data in payloads.items()}
    gate_b_models = {model: gate_b_model(data) for model, data in payloads.items()}
    gate_a_pass = all(item["pass"] for item in gate_a_models.values())
    gate_b_pass = all(item["pass"] for item in gate_b_models.values())

    gate_c: dict[str, Any]
    if gate_a_pass and gate_b_pass:
        if args.gate_c is None or not args.gate_c.exists():
            gate_c = {
                "status": "REQUIRED_NOT_RUN",
                "pass": False,
                "reason": "Gate A and Gate B passed; Gate C static-policy sufficiency is required.",
            }
            decision = "GATE_AB_PASS_GATE_C_REQUIRED"
        else:
            gate_c = json.loads(args.gate_c.read_text(encoding="utf-8"))
            decision = (
                "REV_BATCH_PERFORMANCE_GATE_PASS"
                if gate_c["pass"]
                else "NO_GO_FOR_REVBATCH_STATIC_BATCHING_SUFFICIENT"
            )
    else:
        gate_c = {
            "status": "NOT_RUN_SEQUENTIAL_STOP",
            "pass": False,
            "reason": "Gate A or Gate B failed.",
        }
        if not gate_a_pass and not gate_b_pass:
            decision = "NO_GO_FOR_REVBATCH_GATE_A_AND_B"
        elif not gate_a_pass:
            decision = "NO_GO_FOR_REVBATCH_PERFORMANCE_GATE_A"
        else:
            decision = "NO_GO_FOR_REVBATCH_EXACT_REVISION_GATE_B"

    args.output_root.mkdir(parents=True, exist_ok=True)
    cells = [
        compact_cell(model, cell)
        for model, payload in payloads.items()
        for cell in payload["cells"]
    ]
    summary = {
        "schema_version": 1,
        "decision": decision,
        "gate_a": {"pass": gate_a_pass, "models": gate_a_models},
        "gate_b": {"pass": gate_b_pass, "models": gate_b_models},
        "gate_c": gate_c,
        "cells": cells,
        "evidence_boundary": (
            "Gate A/B are live RTX 3090 measurements. Gate C is evaluated only "
            "after A/B pass and is not inferred from absent data."
        ),
    }
    (args.output_root / "summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"decision": decision, "gate_a": gate_a_pass, "gate_b": gate_b_pass}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

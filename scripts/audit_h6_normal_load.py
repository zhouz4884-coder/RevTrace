#!/usr/bin/env python3
"""Recompute the H6 normal-load V100 comparison from frozen raw cells."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "results/v100_v1_v4/results/v1_v4/178168.manager/raw"
OUT = ROOT / "Paper/audits/h6_normal_load_v100.json"

MODE_NAMES = {
    "margingate": "MarginGate-inspired",
    "llm42": "LLM-42-style revision",
    "revtrace-sg": "RevTrace SG",
    "coarse-dgft": "RevTrace Coarse",
    "hybrid-dgft": "RevTrace Hybrid",
}


def load_cell(model: str, mode: str) -> dict:
    path = RAW / f"v2-{model}-{mode}-c16.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    return {
        "source": str(path.relative_to(ROOT)).replace("\\", "/"),
        "mechanism": MODE_NAMES[mode],
        "audio_xrt": payload["audio_throughput_x_realtime"],
        "display_p99_s": payload["display_latency_p99_seconds"],
        "commit_p99_s": payload["commit_latency_p99_seconds"],
        "verification_fraction": payload.get("verification_fraction"),
        "p95_final_edit_rate": payload["reference_final_edit_rate_p95"],
        "exact_sessions": payload["reference_final_exact_sessions"],
        "sessions": payload["reference_final_sessions"],
        "display_events": payload["display_events"],
        "display_slo_2s_misses": payload["display_slo_2s_misses"],
        "transaction_install_violations": payload["transaction_install_violations"],
    }


def main() -> None:
    models = ["Qwen3-ASR-0.6B", "Qwen3-ASR-1.7B"]
    modes = list(MODE_NAMES)
    cells = {model: {mode: load_cell(model, mode) for mode in modes} for model in models}

    assertions = []
    for model, model_cells in cells.items():
        for mode, cell in model_cells.items():
            assertions.append(
                {
                    "cell": f"{model}/{mode}",
                    "display_events_240": cell["display_events"] == 240,
                    "display_slo_misses_zero": cell["display_slo_2s_misses"] == 0,
                    "install_violations_zero": cell["transaction_install_violations"] == 0,
                }
            )

    ratios = {}
    for model, model_cells in cells.items():
        xrt = {mode: cell["audio_xrt"] for mode, cell in model_cells.items()}
        ratios[model] = {
            "coarse_vs_llm42": xrt["coarse-dgft"] / xrt["llm42"],
            "hybrid_vs_llm42": xrt["hybrid-dgft"] / xrt["llm42"],
            "coarse_vs_margingate": xrt["coarse-dgft"] / xrt["margingate"],
            "hybrid_vs_margingate": xrt["hybrid-dgft"] / xrt["margingate"],
        }

    passed = all(
        check
        for assertion in assertions
        for key, check in assertion.items()
        if key != "cell"
    )
    report = {
        "decision": "PASS_H6_NORMAL_LOAD_RECOMPUTE" if passed else "FAIL",
        "scope": "single-node 8xV100, c16, 16 bilingual 30 s sessions per cell",
        "cells": cells,
        "throughput_ratios": ratios,
        "assertions": assertions,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"decision": report["decision"], "output": str(OUT)}))
    if not passed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Validate frozen RevGuard mechanism-gate records and claim boundaries."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path("."))
    args = parser.parse_args()
    root = args.root.resolve()
    summary = load(
        root / "results" / "revguard" / "revguard_v1" / "summary.json"
    )
    gates = summary["gates"]
    expected = {
        "m1_same_input_mechanism": "PASS",
        "m1_fp32_shape_stability": "PASS",
        "m2_empirical_margin_partition": "PASS",
        "m2_deterministic_margin_certificate": "NOT_ESTABLISHED",
        "m3_live_selective_oracle": "PASS",
        "m4_verifier_fully_hidden": "FAIL",
        "m5_dynamic_rollback": "NOT_RUN_SEQUENTIAL_STOP",
    }
    if gates != expected:
        raise AssertionError(f"unexpected gates: {gates}")
    for model in summary["models"]:
        if model["calibration"]["singleton_repeat_exact"] != 1.0:
            raise AssertionError("calibration singleton is not repeatable")
        if model["held_out_shape"]["singleton_repeat_exact"] != 1.0:
            raise AssertionError("held-out singleton is not repeatable")
        if model["held_out_shape"]["threshold_1_false_safe"] != 0:
            raise AssertionError("held-out margin partition has false-safe events")
        if model["held_out_shape"]["threshold_1_coverage"] < 0.5:
            raise AssertionError("held-out margin coverage is below the gate")
        oracle = model["selective_live_oracle"]
        if oracle["policy_violation_events"] != 0:
            raise AssertionError("selective oracle has a violation")
        if oracle["single_gpu_policy_speedup"] < 2.0:
            raise AssertionError("selective oracle speedup is below the gate")
        if oracle["verifier_to_proposer_service_ratio"] <= 0.8:
            raise AssertionError("M4 should not have passed")

    probe = root / "results" / "revguard" / "probe"
    for suffix in ("qwen3-asr-0.6b", "qwen3-asr-1.7b"):
        for stem in (
            "same-input-d30-c8",
            "same-input-d30-c16",
            "selective-d30-c16-m1.0",
            "same-input-float32-d30-c8",
            "same-input-float32-d30-c16",
        ):
            path = probe / f"{stem}-{suffix}.json"
            if not path.is_file():
                raise FileNotFoundError(path)
        fp32_c8 = load(probe / f"same-input-float32-d30-c8-{suffix}.json")
        fp32_c16 = load(probe / f"same-input-float32-d30-c16-{suffix}.json")
        for payload in (fp32_c8, fp32_c16):
            if payload["summary"]["singleton_repeat_token_exact_rate"] != 1.0:
                raise AssertionError("FP32 singleton repeat failed")
            if payload["summary"]["batch_repeat_token_exact_rate"] != 1.0:
                raise AssertionError("FP32 batch repeat failed")
            if (
                payload["summary"]["same_input_cross_shape_token_exact_rate"]
                != 1.0
            ):
                raise AssertionError("FP32 cross-shape exactness failed")

    print(
        json.dumps(
            {
                "decision": summary["decision"],
                "models": len(summary["models"]),
                "status": "PASS",
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

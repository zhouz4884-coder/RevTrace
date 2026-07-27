#!/usr/bin/env python3
"""Validate the frozen RevBatch gate artifact and sequential-stop boundary."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path("."))
    args = parser.parse_args()
    root = args.root.resolve()
    config = json.loads(
        (root / "configs" / "revbatch_gate.json").read_text(encoding="utf-8")
    )
    d0 = json.loads(
        (
            root
            / "results"
            / "phase0"
            / "revbatch"
            / "d0"
            / "source_audit.json"
        ).read_text(
            encoding="utf-8"
        )
    )
    summary = json.loads(
        (
            root
            / "results"
            / "phase0"
            / "revbatch"
            / "revbatch_v1"
            / "summary.json"
        ).read_text(encoding="utf-8")
    )
    if d0["decision"] != "D0_PASS_PROCEED_TO_PERFORMANCE_GATE":
        raise AssertionError("D0 decision changed")
    if not config["sequential_stop"]:
        raise AssertionError("sequential stop must remain enabled")
    models = {model.rsplit("/", 1)[-1] for model in config["models"]}
    if set(summary["gate_a"]["models"]) != models:
        raise AssertionError("Gate A model set differs from the contract")
    if set(summary["gate_b"]["models"]) != models:
        raise AssertionError("Gate B model set differs from the contract")
    if summary["gate_a"]["pass"] and summary["gate_b"]["pass"]:
        if summary["gate_c"]["status"] == "NOT_RUN_SEQUENTIAL_STOP":
            raise AssertionError("Gate C cannot be skipped after A and B pass")
    else:
        if summary["gate_c"]["status"] != "NOT_RUN_SEQUENTIAL_STOP":
            raise AssertionError("Gate C must stop after an earlier failure")
    if summary["decision"].startswith("REV_BATCH_PERFORMANCE_GATE_PASS"):
        if not all(
            [
                summary["gate_a"]["pass"],
                summary["gate_b"]["pass"],
                summary["gate_c"]["pass"],
            ]
        ):
            raise AssertionError("GO decision lacks all three passing gates")
    print(
        json.dumps(
            {
                "decision": summary["decision"],
                "models": len(models),
                "cells": len(summary["cells"]),
                "status": "PASS",
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

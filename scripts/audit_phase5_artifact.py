#!/usr/bin/env python3
"""Audit the bounded RevTrace Phase 5 artifact and evidence boundaries."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
PHASE5 = ROOT / "results" / "phase5"
ARTIFACT = ROOT / "artifact" / "phase5-system-hardening-v1"


def read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> int:
    manifest_path = ARTIFACT / "MANIFEST.json"
    summary_path = PHASE5 / "summary.json"
    manifest = read(manifest_path)
    summary = read(summary_path)

    failures: list[str] = []
    for record in manifest["files"]:
        path = ARTIFACT / record["path"]
        if not path.is_file():
            failures.append(f"missing:{record['path']}")
            continue
        if path.stat().st_size != record["bytes"]:
            failures.append(f"size:{record['path']}")
        if sha256(path) != record["sha256"]:
            failures.append(f"sha256:{record['path']}")

    if summary["phase5c"]["cell_count"] != 8:
        failures.append("phase5c-cell-count")
    if len(summary["phase5b"]["models"]) != 2:
        failures.append("phase5b-protected-model-count")
    if len(summary["phase5b"]["feedback_off"]) != 2:
        failures.append("phase5b-feedback-off-model-count")
    if summary["phase5e"]["distinct_records"] != 72:
        failures.append("phase5e-distinct-record-count")
    if summary["all_hard_gates_pass"]:
        failures.append("claim-boundary:hard-gates-must-not-be-marked-pass")
    if not summary["phase5c"]["safety_failures"]:
        failures.append("claim-boundary:missing-c32-safety-failure")
    if (
        summary["phase5d"]["decision"]
        != "PHASE5D_LIVE_SLACK_PACKING_NO_GO"
    ):
        failures.append("claim-boundary:phase5d-decision")

    payload = {
        "artifact": str(ARTIFACT),
        "manifest_files": len(manifest["files"]),
        "phase5_decision": summary["decision"],
        "failures": failures,
        "valid": not failures,
    }
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if not failures else 2


if __name__ == "__main__":
    raise SystemExit(main())

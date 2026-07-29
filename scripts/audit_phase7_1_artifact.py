#!/usr/bin/env python3
"""Verify the Phase 7.1 artifact byte-for-byte."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "artifact" / "phase7-1-evidence-repair-v1"


def main() -> int:
    manifest = json.loads(
        (ARTIFACT / "MANIFEST.json").read_text(encoding="utf-8")
    )
    failures: list[str] = []
    for relative, expected in manifest["files"].items():
        path = ARTIFACT / relative
        if not path.exists():
            failures.append(f"missing: {relative}")
            continue
        if path.stat().st_size != expected["bytes"]:
            failures.append(f"size: {relative}")
        if hashlib.sha256(path.read_bytes()).hexdigest() != expected["sha256"]:
            failures.append(f"hash: {relative}")
    declared = set(manifest["files"])
    actual = {
        str(path.relative_to(ARTIFACT)).replace("\\", "/")
        for path in ARTIFACT.rglob("*")
        if path.is_file() and path.name != "MANIFEST.json"
    }
    failures.extend(f"undeclared: {item}" for item in sorted(actual - declared))
    failures.extend(
        f"declared-but-absent: {item}" for item in sorted(declared - actual)
    )
    print(
        json.dumps(
            {
                "artifact": str(ARTIFACT),
                "files": len(declared),
                "failures": failures,
                "valid": not failures,
            },
            indent=2,
        )
    )
    return 0 if not failures else 2


if __name__ == "__main__":
    raise SystemExit(main())

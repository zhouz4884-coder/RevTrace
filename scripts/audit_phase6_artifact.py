#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "artifact/phase6-submission-repairs-v1"


def sha256(path: Path) -> str:
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    return digest


def main() -> int:
    manifest = json.loads(
        (ARTIFACT / "MANIFEST.json").read_text(encoding="utf-8")
    )
    failures = []
    for relative, expected in manifest["files"].items():
        path = ARTIFACT / relative
        if not path.exists():
            failures.append(f"missing: {relative}")
        elif path.stat().st_size != expected["bytes"]:
            failures.append(f"size: {relative}")
        elif sha256(path) != expected["sha256"]:
            failures.append(f"hash: {relative}")
    declared = set(manifest["files"])
    actual = {
        str(path.relative_to(ARTIFACT)).replace("\\", "/")
        for path in ARTIFACT.rglob("*")
        if path.is_file() and path.name != "MANIFEST.json"
    }
    for relative in sorted(actual - declared):
        failures.append(f"undeclared: {relative}")
    for relative in sorted(declared - actual):
        failures.append(f"declared-but-absent: {relative}")
    result = {
        "artifact": str(ARTIFACT),
        "files": len(manifest["files"]),
        "failures": failures,
        "valid": not failures,
    }
    print(json.dumps(result, indent=2))
    return 0 if not failures else 2


if __name__ == "__main__":
    raise SystemExit(main())

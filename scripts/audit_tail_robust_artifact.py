#!/usr/bin/env python3
"""Audit every byte listed by the tail-robust closure manifest."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "artifact" / "tail-robust-admission-closure-v1"


def main() -> int:
    manifest = json.loads(
        (ARTIFACT / "MANIFEST.json").read_text(encoding="utf-8")
    )
    failures = []
    for relative, expected in manifest["files"].items():
        path = ARTIFACT / relative
        if not path.is_file():
            failures.append(f"missing:{relative}")
            continue
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        if actual != expected["sha256"]:
            failures.append(f"sha256:{relative}")
        if path.stat().st_size != int(expected["bytes"]):
            failures.append(f"bytes:{relative}")
    extras = sorted(
        str(path.relative_to(ARTIFACT)).replace("\\", "/")
        for path in ARTIFACT.rglob("*")
        if path.is_file() and path.name != "MANIFEST.json"
        and str(path.relative_to(ARTIFACT)).replace("\\", "/")
        not in manifest["files"]
    )
    failures.extend(f"unlisted:{relative}" for relative in extras)
    print(
        json.dumps(
            {
                "artifact": str(ARTIFACT),
                "audited_files": len(manifest["files"]),
                "failures": failures,
            }
        )
    )
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())

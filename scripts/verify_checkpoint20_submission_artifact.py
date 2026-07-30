#!/usr/bin/env python3
"""Verify a bounded checkpoint-20 artifact without trusting its builder."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "artifact",
        type=Path,
        nargs="?",
        default=Path("artifact/checkpoint20-submission-closure-v2"),
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = args.artifact.resolve()
    manifest_path = root / "MANIFEST.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    declared = set(manifest["files"])
    observed = {
        path.relative_to(root).as_posix()
        for path in root.rglob("*")
        if path.is_file() and path != manifest_path
    }
    if observed != declared:
        raise ValueError(
            f"artifact file-set mismatch missing={declared - observed} "
            f"extra={observed - declared}"
        )
    for relative, record in manifest["files"].items():
        path = root / relative
        if path.stat().st_size != int(record["bytes"]):
            raise ValueError(f"byte-count mismatch: {relative}")
        if sha256(path) != record["sha256"]:
            raise ValueError(f"SHA-256 mismatch: {relative}")
    final = json.loads(
        (
            root
            / "results/checkpoint20_holdback_authority/final_summary_v2.json"
        ).read_text(encoding="utf-8")
    )
    for field in ("decision", "mechanism_digest"):
        if manifest[field] != final[field]:
            raise ValueError(f"manifest/final mismatch: {field}")
    if (
        manifest["identity_extension_digest"]
        != final["artifact_identity_extension"][
            "identity_extension_digest"
        ]
    ):
        raise ValueError("manifest/final mismatch: identity extension")
    print(
        json.dumps(
            {
                "decision": "CHECKPOINT20_ARTIFACT_VERIFY_PASS",
                "files": len(declared),
                "manifest_sha256": sha256(manifest_path),
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

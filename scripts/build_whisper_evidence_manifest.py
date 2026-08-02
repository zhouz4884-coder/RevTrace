#!/usr/bin/env python3
"""Build a content-addressed manifest for the Whisper P0-P3 evidence tree.

The manifest is deliberately generated before packaging so that large remote-only
intermediate search artifacts remain independently auditable without being added
to Git.  The manifest itself is excluded from its file list to avoid recursion.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument(
        "--remote-only-threshold-bytes",
        type=int,
        default=40 * 1024 * 1024,
    )
    args = parser.parse_args()

    root = args.root.resolve()
    output = (args.output or root / "MANIFEST.json").resolve()
    if not root.is_dir():
        raise FileNotFoundError(root)
    if root not in output.parents:
        raise ValueError("manifest output must be inside the evidence root")

    files: list[dict[str, object]] = []
    total_bytes = 0
    remote_only_bytes = 0
    for path in sorted(p for p in root.rglob("*") if p.is_file()):
        if path.resolve() == output:
            continue
        size = path.stat().st_size
        remote_only = size > args.remote_only_threshold_bytes
        files.append(
            {
                "path": path.relative_to(root).as_posix(),
                "bytes": size,
                "sha256": file_sha256(path),
                "remote_only": remote_only,
            }
        )
        total_bytes += size
        if remote_only:
            remote_only_bytes += size

    payload = {
        "schema_version": 1,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "root_name": root.name,
        "remote_only_threshold_bytes": args.remote_only_threshold_bytes,
        "file_count": len(files),
        "total_bytes": total_bytes,
        "remote_only_file_count": sum(bool(row["remote_only"]) for row in files),
        "remote_only_bytes": remote_only_bytes,
        "files": files,
    }
    output.write_bytes((json.dumps(payload, indent=2) + "\n").encode("utf-8"))
    print(json.dumps({key: value for key, value in payload.items() if key != "files"}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Build a deterministic Phase 3C manifest from extracted speech audio."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--audio-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--limit", type=int, default=64)
    args = parser.parse_args()
    paths = sorted(args.audio_root.rglob("*.flac"))[: args.limit]
    if len(paths) < args.limit:
        raise RuntimeError(
            f"found {len(paths)} FLAC files, expected {args.limit}"
        )
    records = [
        {
            "path": str(path.resolve()),
            "language": "English",
            "bytes": path.stat().st_size,
            "sha256": digest(path),
            "source": "LibriSpeech test-clean",
        }
        for path in paths
    ]
    payload = {
        "schema_version": 1,
        "scope": (
            "Phase 3C independent-utterance numerical stress; "
            "not a production prevalence or ASR quality benchmark"
        ),
        "records": records,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "output": str(args.output),
                "records": len(records),
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

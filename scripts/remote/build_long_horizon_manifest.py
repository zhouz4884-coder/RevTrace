#!/usr/bin/env python3
"""Build a deterministic bilingual manifest for natural long-horizon runs."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--english-root", type=Path, required=True)
    parser.add_argument("--chinese-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--per-language", type=int, default=128)
    return parser.parse_args()


def collect(root: Path, limit: int) -> list[Path]:
    paths = sorted(
        path.resolve()
        for pattern in ("*.flac", "*.wav")
        for path in root.rglob(pattern)
    )
    if len(paths) < limit:
        raise RuntimeError(
            f"{root} has only {len(paths)} audio files; need {limit}"
        )
    return paths[:limit]


def main() -> int:
    args = parse_args()
    records = []
    for language, root in (
        ("English", args.english_root),
        ("Chinese", args.chinese_root),
    ):
        for path in collect(root, args.per_language):
            records.append({"language": language, "path": str(path)})
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "construction": "deterministic_distinct_natural_audio_pool",
                "records": records,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"output": str(args.output), "records": len(records)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

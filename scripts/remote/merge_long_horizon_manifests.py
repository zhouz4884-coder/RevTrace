#!/usr/bin/env python3
"""Merge annotated English and Chinese manifests for long-horizon studies."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--english", type=Path, required=True)
    parser.add_argument("--chinese", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--per-language", type=int, default=64)
    return parser.parse_args()


def records(path: Path, language: str, limit: int) -> list[dict[str, object]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    selected = [
        dict(record)
        for record in payload["records"]
        if record.get("language") == language
    ][:limit]
    if len(selected) < limit:
        raise RuntimeError(
            f"{path} has only {len(selected)} {language} records; need {limit}"
        )
    if any(not record.get("reference") for record in selected):
        raise RuntimeError(f"{path} contains records without references")
    return selected


def main() -> int:
    args = parse_args()
    merged = records(
        args.english, "English", args.per_language
    ) + records(args.chinese, "Chinese", args.per_language)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "study": "RevTrace natural long-horizon annotated pool",
                "records": merged,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"output": str(args.output), "records": len(merged)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Build an utterance-disjoint R8 quality manifest."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument(
        "--development-quality", type=Path, nargs="+", required=True
    )
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    excluded = {
        str(utterance)
        for path in args.development_quality
        for session in json.loads(path.read_text(encoding="utf-8"))["sessions"]
        for utterance in session["utterance_ids"]
    }
    records = [
        row for row in manifest["records"]
        if str(row["utterance_id"]) not in excluded
    ]
    output = {
        "schema_version": 1,
        "study": "RevTrace R8 utterance-disjoint quality holdout",
        "source_manifest_sha256": hashlib.sha256(
            args.manifest.read_bytes()
        ).hexdigest(),
        "development_quality_sha256": [
            hashlib.sha256(path.read_bytes()).hexdigest()
            for path in args.development_quality
        ],
        "excluded_utterances": len(excluded),
        "records": records,
        "counts": {
            split: sum(row["split"] == split for row in records)
            for split in sorted({row["split"] for row in records})
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(output, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "excluded": len(excluded),
        "remaining": len(records),
        "counts": output["counts"],
    }))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Build a deterministic held-out ASR-quality manifest.

The builder deliberately selects by a SHA-256 ordering rather than filesystem
order.  This makes the sample list auditable and prevents convenient examples
from being hand picked after seeing model outputs.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--librispeech-root", type=Path, required=True)
    parser.add_argument("--english-count", type=int, default=64)
    parser.add_argument("--seed", default="revtrace-final-quality-v1")
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def transcript_index(root: Path) -> dict[str, str]:
    index: dict[str, str] = {}
    for path in root.rglob("*.trans.txt"):
        for line in path.read_text(encoding="utf-8").splitlines():
            fields = line.strip().split(maxsplit=1)
            if len(fields) == 2:
                index[fields[0]] = fields[1]
    return index


def main() -> int:
    args = parse_args()
    references = transcript_index(args.librispeech_root)
    candidates = []
    for path in args.librispeech_root.rglob("*.flac"):
        sample_id = path.stem
        if sample_id not in references:
            continue
        digest = hashlib.sha256(
            f"{args.seed}:{sample_id}".encode("utf-8")
        ).hexdigest()
        candidates.append((digest, sample_id, path.resolve()))
    candidates.sort()
    if len(candidates) < args.english_count:
        raise RuntimeError(
            f"only {len(candidates)} English examples are available"
        )
    records = [
        {
            "sample_id": sample_id,
            "language": "English",
            "path": str(path),
            "reference": references[sample_id],
            "selection_digest": digest,
        }
        for digest, sample_id, path in candidates[: args.english_count]
    ]
    payload = {
        "schema_version": 1,
        "study": "RevTrace independent ASR quality holdout",
        "selection": {
            "method": "ascending SHA-256(seed:sample_id)",
            "seed": args.seed,
            "english_count": args.english_count,
        },
        "records": records,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"output": str(args.output), "records": len(records)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

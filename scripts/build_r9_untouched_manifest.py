#!/usr/bin/env python3
"""Build a holdout excluding every utterance found in prior result sessions."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--manifest", type=Path, required=True)
    p.add_argument("--results-root", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    return p.parse_args()


def collect_utterance_ids(value: object, used: set[str]) -> None:
    """Recursively collect session identities from every result schema.

    R8 stores sessions at the payload root, whereas R9 nests them below a
    mode.  Restricting the scan to ``payload['sessions']`` can silently reuse
    an R9 cohort when constructing a later confirmation set.
    """

    if isinstance(value, dict):
        identifiers = value.get("utterance_ids")
        if isinstance(identifiers, list):
            used.update(str(item) for item in identifiers)
        for child in value.values():
            collect_utterance_ids(child, used)
    elif isinstance(value, list):
        for child in value:
            collect_utterance_ids(child, used)


def main() -> int:
    args = parse_args()
    source = json.loads(args.manifest.read_text(encoding="utf-8"))
    used: set[str] = set()
    scanned: list[dict[str, str | int]] = []
    for path in sorted(args.results_root.rglob("*.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        before = len(used)
        collect_utterance_ids(payload, used)
        if len(used) != before:
            scanned.append({
                "path": str(path),
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                "new_exclusions": len(used) - before,
            })
    records = [
        row for row in source["records"]
        if str(row["utterance_id"]) not in used
    ]
    counts = {
        split: sum(row["split"] == split for row in records)
        for split in ("test-clean", "test-other")
    }
    seconds = {
        split: sum(
            int(row["samples"]) / int(row.get("sample_rate", 16_000))
            for row in records if row["split"] == split
        )
        for split in counts
    }
    output = {
        "schema_version": 1,
        "study": "R9 untouched utterance-disjoint holdout",
        "source_manifest_sha256": hashlib.sha256(
            args.manifest.read_bytes()
        ).hexdigest(),
        "results_root": str(args.results_root),
        "excluded_utterances": len(used),
        "scanned_result_files": scanned,
        "counts": counts,
        "seconds": seconds,
        "records": records,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(output, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "excluded": len(used), "counts": counts, "seconds": seconds
    }))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

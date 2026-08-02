#!/usr/bin/env python3
"""Audit a holdout manifest against prior results and on-disk audio."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import soundfile as sf

from build_r9_untouched_manifest import collect_utterance_ids


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--results-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    prior_ids: set[str] = set()
    scanned = 0
    for result in sorted(args.results_root.rglob("*.json")):
        # The holdout's own result directory must not exist before this audit.
        try:
            payload = json.loads(result.read_text(encoding="utf-8"))
        except Exception:
            continue
        collect_utterance_ids(payload, prior_ids)
        scanned += 1
    manifest_ids: set[str] = set()
    duplicate_ids: list[str] = []
    missing_files: list[str] = []
    hash_mismatches: list[str] = []
    metadata_mismatches: list[str] = []
    seconds: dict[str, float] = {}
    counts: dict[str, int] = {}
    for row in manifest["records"]:
        utterance = str(row["utterance_id"])
        if utterance in manifest_ids:
            duplicate_ids.append(utterance)
        manifest_ids.add(utterance)
        split = str(row["split"])
        counts[split] = counts.get(split, 0) + 1
        path = Path(str(row["path"]))
        if not path.is_file():
            missing_files.append(str(path))
            continue
        if digest(path) != str(row["sha256"]):
            hash_mismatches.append(utterance)
        info = sf.info(path)
        if (
            int(info.frames) != int(row["samples"])
            or int(info.samplerate) != int(row["sample_rate"])
        ):
            metadata_mismatches.append(utterance)
        seconds[split] = seconds.get(split, 0.0) + (
            int(info.frames) / int(info.samplerate)
        )
    overlap = sorted(manifest_ids & prior_ids)
    passed = not any((
        duplicate_ids, missing_files, hash_mismatches,
        metadata_mismatches, overlap,
    ))
    output = {
        "schema_version": 1,
        "decision": "PASS_R9_HOLDOUT_AUDIT" if passed else "FAIL_R9_HOLDOUT_AUDIT",
        "manifest": str(args.manifest),
        "manifest_sha256": digest(args.manifest),
        "results_root": str(args.results_root),
        "result_json_files_scanned": scanned,
        "counts": counts,
        "seconds": seconds,
        "prior_utterance_ids": len(prior_ids),
        "overlap_count": len(overlap),
        "overlap_ids": overlap,
        "duplicate_ids": duplicate_ids,
        "missing_files": missing_files,
        "hash_mismatches": hash_mismatches,
        "metadata_mismatches": metadata_mismatches,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(output, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(output, sort_keys=True))
    return 0 if passed else 2


if __name__ == "__main__":
    raise SystemExit(main())


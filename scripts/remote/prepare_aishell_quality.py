#!/usr/bin/env python3
"""Materialize a deterministic AISHELL quality subset from ModelScope."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path
from typing import Any

from modelscope.msdatasets import MsDataset


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--count", type=int, default=64)
    parser.add_argument("--seed", default="revtrace-final-quality-v1")
    return parser.parse_args()


def find_value(row: dict[str, Any], names: tuple[str, ...]) -> Any:
    for name in names:
        if name in row and row[name] not in (None, ""):
            return row[name]
    return None


def main() -> int:
    args = parse_args()
    dataset = MsDataset.load(
        "speech_asr_aishell1_testsets",
        subset_name="default",
        namespace="modelscope",
        split="train",
    )
    rows = []
    for index, raw in enumerate(dataset):
        row = dict(raw)
        audio_value = find_value(
            row,
            (
                "audio",
                "audio_path",
                "wav",
                "wav_path",
                "file",
                "Audio:FILE",
            ),
        )
        reference = find_value(
            row, ("text", "transcript", "sentence", "label", "Text:LABEL")
        )
        if isinstance(audio_value, dict):
            audio_value = audio_value.get("path") or audio_value.get("array")
        if not isinstance(audio_value, (str, Path)) or reference is None:
            if index == 0:
                print(
                    json.dumps(
                        {"first_row_keys": sorted(row), "first_row": row},
                        ensure_ascii=False,
                        default=str,
                    )
                )
            continue
        source = Path(audio_value)
        if not source.exists():
            continue
        sample_id = str(
            find_value(row, ("id", "key", "utt_id", "audio_id"))
            or source.stem
        )
        digest = hashlib.sha256(
            f"{args.seed}:{sample_id}".encode("utf-8")
        ).hexdigest()
        rows.append((digest, sample_id, source, str(reference)))
    rows.sort()
    if len(rows) < args.count:
        raise RuntimeError(
            f"only {len(rows)} usable AISHELL rows were materialized"
        )
    audio_dir = args.output_dir / "audio"
    audio_dir.mkdir(parents=True, exist_ok=True)
    records = []
    for digest, sample_id, source, reference in rows[: args.count]:
        target = audio_dir / f"{sample_id}{source.suffix}"
        shutil.copy2(source, target)
        records.append(
            {
                "sample_id": f"aishell-{sample_id}",
                "language": "Chinese",
                "path": str(target.resolve()),
                "reference": reference,
                "selection_digest": digest,
            }
        )
    manifest = {
        "schema_version": 1,
        "study": "RevTrace independent AISHELL quality holdout",
        "selection": {
            "source": "ModelScope speech_asr_aishell1_testsets",
            "method": "ascending SHA-256(seed:sample_id)",
            "seed": args.seed,
            "chinese_count": args.count,
        },
        "records": records,
    }
    output = args.output_dir / "manifest.json"
    output.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"output": str(output), "records": len(records)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

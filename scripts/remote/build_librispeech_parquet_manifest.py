#!/usr/bin/env python3
"""Extract two LibriSpeech parquet shards into an auditable manifest."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import pyarrow.parquet as pq
import soundfile as sf


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def extract_records(
    parquet_path: Path,
    audio_root: Path,
    split: str,
) -> list[dict[str, Any]]:
    audio_root.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, Any]] = []
    for record in pq.read_table(parquet_path).to_pylist():
        utterance = str(record.get("id") or Path(record["file"]).stem)
        audio = record["audio"]
        suffix = Path(
            str(audio.get("path") or record.get("file") or "")
        ).suffix or ".flac"
        path = audio_root / f"{utterance}{suffix}"
        if not path.exists():
            path.write_bytes(audio["bytes"])
        info = sf.info(path)
        rows.append({
            "split": split,
            "utterance_id": utterance,
            "speaker_id": str(record.get("speaker_id", "") or ""),
            "path": str(path.resolve()),
            "text": str(record["text"]),
            "samples": int(info.frames),
            "sample_rate": int(info.samplerate),
            "sha256": digest(path),
        })
    return rows


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--clean-parquet", type=Path, required=True)
    parser.add_argument("--other-parquet", type=Path, required=True)
    parser.add_argument("--audio-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    clean = extract_records(
        args.clean_parquet, args.audio_root / "validation-clean", "test-clean"
    )
    other = extract_records(
        args.other_parquet, args.audio_root / "validation-other", "test-other"
    )
    payload = {
        "schema_version": 1,
        "study": "RevTrace R8 untouched LibriSpeech validation holdout",
        "source_sha256": {
            "clean": digest(args.clean_parquet),
            "other": digest(args.other_parquet),
        },
        "counts": {"test-clean": len(clean), "test-other": len(other)},
        "records": clean + other,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(payload["counts"], sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Build transcript-bearing clean/other manifests for W6 quality."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import pyarrow.parquet as pq
import soundfile as sf


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--clean-root", type=Path, required=True)
    parser.add_argument("--other-parquet", type=Path, required=True)
    parser.add_argument("--other-audio-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def clean_records(root: Path) -> list[dict[str, Any]]:
    transcripts: dict[str, str] = {}
    for path in root.rglob("*.trans.txt"):
        for line in path.read_text(encoding="utf-8").splitlines():
            utterance, text = line.split(" ", 1)
            transcripts[utterance] = text
    rows = []
    for path in sorted(root.rglob("*.flac")):
        utterance = path.stem
        speaker = utterance.split("-", 1)[0]
        info = sf.info(path)
        rows.append({
            "split": "test-clean",
            "utterance_id": utterance,
            "speaker_id": speaker,
            "path": str(path.resolve()),
            "text": transcripts[utterance],
            "samples": int(info.frames),
            "sample_rate": int(info.samplerate),
            "sha256": digest(path),
        })
    return rows


def other_records(
    parquet_path: Path,
    audio_root: Path,
) -> list[dict[str, Any]]:
    audio_root.mkdir(parents=True, exist_ok=True)
    table = pq.read_table(parquet_path)
    rows = []
    for record in table.to_pylist():
        utterance = str(record.get("id") or Path(
            record["file"]
        ).stem)
        audio = record["audio"]
        suffix = Path(
            str(audio.get("path") or record.get("file") or "")
        ).suffix or ".flac"
        path = audio_root / f"{utterance}{suffix}"
        if not path.exists():
            path.write_bytes(audio["bytes"])
        info = sf.info(path)
        rows.append({
            "split": "test-other",
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
    args = parse_args()
    clean = clean_records(args.clean_root)
    other = other_records(
        args.other_parquet, args.other_audio_root
    )
    payload = {
        "schema_version": 1,
        "study": "W6 LibriSpeech quality source manifest",
        "counts": {
            "test-clean": len(clean),
            "test-other": len(other),
        },
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

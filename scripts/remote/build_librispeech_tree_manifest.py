#!/usr/bin/env python3
"""Build a transcript-bearing manifest from two LibriSpeech directory trees."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import soundfile as sf


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def records(root: Path, split: str) -> list[dict[str, object]]:
    transcripts: dict[str, str] = {}
    for transcript in root.rglob("*.trans.txt"):
        for line in transcript.read_text(encoding="utf-8").splitlines():
            utterance, text = line.split(" ", 1)
            transcripts[utterance] = text
    rows = []
    for audio in sorted(root.rglob("*.flac")):
        utterance = audio.stem
        info = sf.info(audio)
        rows.append({
            "split": split,
            "utterance_id": utterance,
            "speaker_id": utterance.split("-", 1)[0],
            "path": str(audio.resolve()),
            "text": transcripts[utterance],
            "samples": int(info.frames),
            "sample_rate": int(info.samplerate),
            "sha256": digest(audio),
        })
    return rows


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--clean-root", type=Path, required=True)
    p.add_argument("--other-root", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    clean = records(args.clean_root, "test-clean")
    other = records(args.other_root, "test-other")
    payload = {
        "schema_version": 1,
        "study": "RevTrace R8 untouched LibriSpeech development holdout",
        "counts": {"test-clean": len(clean), "test-other": len(other)},
        "records": clean + other,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(payload["counts"], sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

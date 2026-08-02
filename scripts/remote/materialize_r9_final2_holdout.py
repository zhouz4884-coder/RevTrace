#!/usr/bin/env python3
"""Materialize a small, auditable LibriSpeech train holdout from HF streaming.

R9's first confirmation cohort became validation evidence after a miss exposed
an under-sensitive directional-coverage threshold.  This script draws from
previously unused train partitions so the second confirmation remains
utterance-disjoint from every earlier test/dev experiment.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import soundfile as sf
from datasets import Audio, load_dataset


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def materialize(
    *, config: str, source_split: str, output_split: str,
    minimum_seconds: float, root: Path,
) -> list[dict[str, object]]:
    stream = load_dataset(
        "openslr/librispeech_asr", config, split=source_split,
        streaming=True,
    ).cast_column("audio", Audio(decode=False))
    target = root / output_split
    target.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, object]] = []
    seconds = 0.0
    for item in stream:
        utterance = str(item["id"])
        audio = item["audio"]
        raw = audio.get("bytes")
        if raw is None:
            raw = Path(audio["path"]).read_bytes()
        suffix = Path(str(audio.get("path") or "sample.flac")).suffix or ".flac"
        path = target / f"{utterance}{suffix}"
        if not path.exists() or path.stat().st_size != len(raw):
            path.write_bytes(raw)
        info = sf.info(path)
        duration = float(info.frames) / float(info.samplerate)
        rows.append({
            "split": output_split,
            "source_config": config,
            "source_split": source_split,
            "utterance_id": utterance,
            "speaker_id": str(item.get("speaker_id", "")),
            "path": str(path.resolve()),
            "text": str(item["text"]),
            "samples": int(info.frames),
            "sample_rate": int(info.samplerate),
            "sha256": sha256_bytes(raw),
        })
        seconds += duration
        if seconds >= minimum_seconds:
            break
    if seconds < minimum_seconds:
        raise RuntimeError(
            f"{config}/{source_split} yielded {seconds:.1f}s, "
            f"below required {minimum_seconds:.1f}s"
        )
    return rows


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--output-manifest", type=Path, required=True)
    parser.add_argument("--minimum-seconds", type=float, default=900.0)
    args = parser.parse_args()
    clean = materialize(
        config="clean", source_split="train.100", output_split="test-clean",
        minimum_seconds=args.minimum_seconds, root=args.output_root,
    )
    other = materialize(
        config="other", source_split="train.500", output_split="test-other",
        minimum_seconds=args.minimum_seconds, root=args.output_root,
    )
    records = clean + other
    payload = {
        "schema_version": 1,
        "study": "R9 second untouched LibriSpeech train-partition confirmation",
        "source": "openslr/librispeech_asr via Hugging Face streaming",
        "counts": {
            split: sum(row["split"] == split for row in records)
            for split in ("test-clean", "test-other")
        },
        "seconds": {
            split: sum(
                int(row["samples"]) / int(row["sample_rate"])
                for row in records if row["split"] == split
            )
            for split in ("test-clean", "test-other")
        },
        "records": records,
    }
    args.output_manifest.parent.mkdir(parents=True, exist_ok=True)
    args.output_manifest.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"counts": payload["counts"], "seconds": payload["seconds"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


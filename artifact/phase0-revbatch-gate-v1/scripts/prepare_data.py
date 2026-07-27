#!/usr/bin/env python3
"""Prepare the official public Qwen3-ASR bilingual speech inputs."""

from __future__ import annotations

import argparse
import hashlib
import json
import urllib.request
from pathlib import Path


QWEN_EN_URL = (
    "https://qianwen-res.oss-cn-beijing.aliyuncs.com/"
    "Qwen3-ASR-Repo/asr_en.wav"
)
QWEN_ZH_URL = (
    "https://qianwen-res.oss-cn-beijing.aliyuncs.com/"
    "Qwen3-ASR-Repo/asr_zh.wav"
)


def download(url: str, destination: Path) -> None:
    if destination.exists() and destination.stat().st_size:
        return
    destination.parent.mkdir(parents=True, exist_ok=True)
    partial = destination.with_suffix(destination.suffix + ".part")
    request = urllib.request.Request(url, headers={"User-Agent": "RevBatch/1.0"})
    with urllib.request.urlopen(request, timeout=120) as response:
        with partial.open("wb") as handle:
            while True:
                block = response.read(1024 * 1024)
                if not block:
                    break
                handle.write(block)
    partial.replace(destination)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    args = parser.parse_args()

    args.root.mkdir(parents=True, exist_ok=True)
    english = args.root / "qwen_public" / "asr_en.wav"
    chinese = args.root / "qwen_public" / "asr_zh.wav"
    download(QWEN_EN_URL, english)
    download(QWEN_ZH_URL, chinese)

    records = [
        {
            "language": "English",
            "source": "Qwen3-ASR public English sample",
            "path": str(english.resolve()),
            "bytes": english.stat().st_size,
            "sha256": sha256(english),
        }
    ]
    records.append(
        {
            "language": "Chinese",
            "source": "Qwen3-ASR public sample",
            "path": str(chinese.resolve()),
            "bytes": chinese.stat().st_size,
            "sha256": sha256(chinese),
        }
    )
    manifest = {
        "schema_version": 1,
        "records": records,
        "downloads": {
            "qwen_en_url": QWEN_EN_URL,
            "qwen_zh_url": QWEN_ZH_URL,
        },
        "scope": (
            "Bilingual public inputs for performance and revision-equivalence "
            "gates; no ASR quality or dataset-generalization claim."
        ),
    }
    (args.root / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"records": len(records), "manifest": str(args.root / "manifest.json")}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

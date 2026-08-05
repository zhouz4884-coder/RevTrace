#!/usr/bin/env python3
"""Minimal V100 legality probe for the Transformers Qwen3-ASR backend."""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import time
from pathlib import Path

import numpy as np
import soundfile as sf
import soxr
import torch


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_audio(path: Path, seconds: float = 2.0) -> np.ndarray:
    audio, sample_rate = sf.read(path, dtype="float32")
    if audio.ndim > 1:
        audio = audio.mean(axis=1)
    if sample_rate != 16000:
        audio = soxr.resample(audio, sample_rate, 16000, quality="HQ")
        sample_rate = 16000
    target = int(round(seconds * sample_rate))
    if audio.size < target:
        audio = np.tile(audio, int(np.ceil(target / audio.size)))
    return np.asarray(audio[:target], dtype=np.float32)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    from qwen_asr import Qwen3ASRModel

    audio = load_audio(args.root / "datasets/revbatch/qwen_public/asr_en.wav")
    rows = []
    for model_name in ("Qwen3-ASR-0.6B", "Qwen3-ASR-1.7B"):
        model_path = args.root / "models" / model_name
        started = time.perf_counter()
        asr = Qwen3ASRModel.from_pretrained(
            str(model_path),
            torch_dtype=torch.float16,
            device_map={"": "cuda:0"},
            attn_implementation="eager",
            low_cpu_mem_usage=True,
            local_files_only=True,
            max_inference_batch_size=1,
            max_new_tokens=16,
        )
        loaded = time.perf_counter()
        first = asr.transcribe((audio, 16000), language="English")[0]
        second = asr.transcribe((audio, 16000), language="English")[0]
        finished = time.perf_counter()
        rows.append({
            "model": model_name,
            "model_config_sha256": sha256(model_path / "config.json"),
            "load_seconds": loaded - started,
            "two_inferences_seconds": finished - loaded,
            "first_text": first.text,
            "second_text": second.text,
            "repeat_exact": first.text == second.text,
        })
        del asr
        torch.cuda.empty_cache()

    payload = {
        "schema_version": 1,
        "study": "RevTrace V100 Transformers-backend legality smoke",
        "hostname": platform.node(),
        "torch": torch.__version__,
        "torch_cuda": torch.version.cuda,
        "gpu": torch.cuda.get_device_name(0),
        "rows": rows,
        "decision": (
            "PASS_V100_HF_LEGALITY_SMOKE"
            if len(rows) == 2 and all(row["repeat_exact"] for row in rows)
            else "FAIL_V100_HF_LEGALITY_SMOKE"
        ),
        "claim_boundary": (
            "Transformers/eager V100 runtime; this establishes a separate V100 "
            "contract and is not pooled with the RTX 3090 vLLM contract."
        ),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(payload, sort_keys=True))
    return 0 if payload["decision"].startswith("PASS") else 2


if __name__ == "__main__":
    raise SystemExit(main())

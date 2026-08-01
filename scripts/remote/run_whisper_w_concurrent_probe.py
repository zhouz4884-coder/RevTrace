#!/usr/bin/env python3
"""Probe arithmetic-path-preserving concurrent singleton authority lanes."""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import time
from pathlib import Path

import numpy as np
import soundfile as sf
import torch

from whisper_batched_executor import DistinctPromptWhisper, SAMPLE_RATE


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--lanes", type=int, default=4)
    parser.add_argument("--jobs", type=int, default=32)
    parser.add_argument("--device", default="cuda:0")
    parser.add_argument("--max-new-tokens", type=int, default=96)
    return parser.parse_args()


def load(path: str) -> np.ndarray:
    audio, rate = sf.read(path, dtype="float32", always_2d=False)
    if rate != SAMPLE_RATE:
        raise ValueError(rate)
    if audio.ndim == 2:
        audio = audio.mean(axis=1)
    value = np.asarray(audio, dtype=np.float32)
    # Freeze a 10-second state-transition shape.
    target = 10 * SAMPLE_RATE
    if value.size >= target:
        return value[:target]
    return np.pad(value, (0, target - value.size))


def main() -> int:
    args = parse_args()
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    paths = [row["path"] for row in manifest["records"][: args.jobs]]
    audio = [load(path) for path in paths]
    prompts = [
        "" if index % 3 == 0 else f"Prior transcript lane {index}."
        for index in range(len(audio))
    ]
    serial_executor = DistinctPromptWhisper(
        args.model,
        device=args.device,
        max_new_tokens=args.max_new_tokens,
    )
    torch.cuda.synchronize()
    started = time.perf_counter()
    serial = [
        serial_executor.canonical(value, prompt)
        for value, prompt in zip(audio, prompts)
    ]
    serial_seconds = time.perf_counter() - started

    executors = [
        DistinctPromptWhisper(
            args.model,
            device=args.device,
            max_new_tokens=args.max_new_tokens,
        )
        for _ in range(args.lanes)
    ]
    streams = [
        torch.cuda.Stream(device=args.device) for _ in range(args.lanes)
    ]

    def invoke(index: int):
        lane = index % args.lanes
        with torch.cuda.stream(streams[lane]):
            return executors[lane].canonical(audio[index], prompts[index])

    torch.cuda.synchronize()
    started = time.perf_counter()
    with concurrent.futures.ThreadPoolExecutor(
        max_workers=args.lanes
    ) as pool:
        concurrent_rows = list(pool.map(invoke, range(len(audio))))
    torch.cuda.synchronize()
    concurrent_seconds = time.perf_counter() - started
    mismatches = [
        index for index, (left, right) in enumerate(
            zip(serial, concurrent_rows)
        ) if left.token_ids != right.token_ids
    ]
    payload = {
        "schema_version": 1,
        "study": "W arithmetic-path-preserving concurrent authority probe",
        "config": {
            "lanes": args.lanes,
            "jobs": len(audio),
            "device": args.device,
            "window_seconds": 10,
        },
        "counts": {
            "serial_concurrent_mismatches": len(mismatches),
        },
        "metrics": {
            "serial_seconds": serial_seconds,
            "concurrent_seconds": concurrent_seconds,
            "authority_throughput_speedup": (
                serial_seconds / concurrent_seconds
            ),
        },
        "mismatch_indices": mismatches,
        "claim_boundary": (
            "A passing finite probe establishes an exact deployed lane "
            "configuration, not cross-hardware bitwise determinism."
        ),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        **payload["counts"], **payload["metrics"]
    }, sort_keys=True))
    return 0 if not mismatches else 2


if __name__ == "__main__":
    raise SystemExit(main())

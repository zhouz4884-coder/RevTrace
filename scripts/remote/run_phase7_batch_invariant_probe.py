#!/usr/bin/env python3
"""Source-faithful Thinking Machines batch-invariant operator probe.

This probe has two modes.  ``operator`` measures the public mm replacement
against ordinary torch.  ``qwen-asr`` executes RevTrace's immutable-job
same-input harness while the public context manager is active.  The latter is
an integration compatibility test, not a claim that the upstream project
directly supports Qwen3-ASR.
"""

from __future__ import annotations

import argparse
import json
import runpy
import statistics
import sys
import time
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--mode", choices=("operator", "qwen-asr"), required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--revtrace-root", type=Path)
    parser.add_argument("--model", type=Path)
    parser.add_argument("--data-manifest", type=Path)
    return parser.parse_args()


def percentile(values: list[float], q: float) -> float:
    ordered = sorted(values)
    index = (len(ordered) - 1) * q
    lower = int(index)
    upper = min(len(ordered) - 1, lower + 1)
    weight = index - lower
    return ordered[lower] * (1 - weight) + ordered[upper] * weight


def operator_probe(set_batch_invariant_mode: object) -> dict[str, object]:
    import torch

    torch.set_default_device("cuda")
    torch.manual_seed(20260729)
    batch, inner, output = 16, 2048, 2048
    left = torch.randn(batch, inner, dtype=torch.float16)
    right = torch.randn(inner, output, dtype=torch.float16)

    rows: list[dict[str, object]] = []
    for enabled in (False, True):
        with set_batch_invariant_mode(enabled):
            # Compile/warm every shape before measurement.
            for _ in range(3):
                torch.mm(left[:1], right)
                torch.mm(left, right)
            torch.cuda.synchronize()
            torch.cuda.reset_peak_memory_stats()
            elapsed: list[float] = []
            diffs: list[float] = []
            for _ in range(20):
                started = time.perf_counter()
                singleton = torch.mm(left[:1], right)
                batched = torch.mm(left, right)[:1]
                torch.cuda.synchronize()
                elapsed.append(time.perf_counter() - started)
                diffs.append(float((singleton - batched).abs().max().item()))
            rows.append(
                {
                    "batch_invariant_enabled": enabled,
                    "bitwise_invariant": all(item == 0.0 for item in diffs),
                    "maximum_absolute_difference": max(diffs),
                    "pair_latency_seconds_p50": statistics.median(elapsed),
                    "pair_latency_seconds_p99": percentile(elapsed, 0.99),
                    "peak_vram_bytes": int(torch.cuda.max_memory_allocated()),
                }
            )
    return {
        "schema_version": 1,
        "study": "Thinking Machines batch_invariant_ops source operator probe",
        "device": torch.cuda.get_device_name(0),
        "torch": torch.__version__,
        "shape": [batch, inner, output],
        "rows": rows,
    }


def qwen_asr_probe(
    set_batch_invariant_mode: object,
    args: argparse.Namespace,
) -> None:
    if not args.revtrace_root or not args.model or not args.data_manifest:
        raise ValueError("qwen-asr mode requires RevTrace, model, and manifest")
    script = args.revtrace_root / "scripts/remote/run_revguard_same_input.py"
    sys.argv = [
        str(script),
        "--model",
        str(args.model),
        "--model-name",
        "Qwen3-ASR-0.6B",
        "--data-manifest",
        str(args.data_manifest),
        "--output",
        str(args.output),
        "--duration-seconds",
        "4",
        "--concurrency",
        "4",
        "--dtype",
        "float16",
        "--top-logprobs",
        "2",
        "--max-model-len",
        "4096",
    ]
    with set_batch_invariant_mode(True):
        runpy.run_path(str(script), run_name="__main__")


def main() -> int:
    args = parse_args()
    sys.path.insert(0, str(args.source))
    from batch_invariant_ops import set_batch_invariant_mode

    args.output.parent.mkdir(parents=True, exist_ok=True)
    if args.mode == "operator":
        payload = operator_probe(set_batch_invariant_mode)
        args.output.write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        print(json.dumps(payload, sort_keys=True))
        return 0
    qwen_asr_probe(set_batch_invariant_mode, args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

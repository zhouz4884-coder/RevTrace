#!/usr/bin/env python3
"""Source-faithful TBIK operator probe on the available GPU."""

from __future__ import annotations

import argparse
import importlib.util
import json
import statistics
import sys
import time
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def percentile(values: list[float], q: float) -> float:
    ordered = sorted(values)
    index = (len(ordered) - 1) * q
    lower = int(index)
    upper = min(len(ordered) - 1, lower + 1)
    weight = index - lower
    return ordered[lower] * (1 - weight) + ordered[upper] * weight


def main() -> int:
    args = parse_args()
    import torch

    module_path = args.source / "src/tbik/tree_based_matmul.py"
    spec = importlib.util.spec_from_file_location(
        "phase7_tbik_tree_based_matmul", module_path
    )
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load TBIK module: {module_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    # The public dispatcher in the supplied archive checks shape/dtype but not
    # compute capability, so on sm86 it incorrectly attempts the sm90a CUDA
    # extension despite the README promising a Triton fallback.  Exercise the
    # source's fallback kernel directly and preserve the dispatcher failure in
    # the source-probe log.
    matmul_tp_persistent = module._matmul_tp_persistent_triton

    torch.manual_seed(20260729)
    rows = 512
    inner = 2048
    output = 1024
    left = torch.randn((rows, inner), device="cuda", dtype=torch.bfloat16)
    right = torch.randn((inner, output), device="cuda", dtype=torch.bfloat16)

    payload_rows = []
    for label, kernel in (
        ("torch_matmul", torch.matmul),
        ("tbik_triton_fallback", matmul_tp_persistent),
    ):
        for _ in range(3):
            kernel(left, right)
            kernel(left[: rows // 2], right)
        torch.cuda.synchronize()
        elapsed: list[float] = []
        diffs: list[float] = []
        torch.cuda.reset_peak_memory_stats()
        for _ in range(20):
            started = time.perf_counter()
            full = kernel(left, right)[: rows // 2]
            half = kernel(left[: rows // 2], right)
            torch.cuda.synchronize()
            elapsed.append(time.perf_counter() - started)
            diffs.append(float((full - half).abs().max().item()))
        payload_rows.append(
            {
                "method": label,
                "batch_invariant": all(item == 0.0 for item in diffs),
                "maximum_absolute_difference": max(diffs),
                "pair_latency_seconds_p50": statistics.median(elapsed),
                "pair_latency_seconds_p99": percentile(elapsed, 0.99),
                "peak_vram_bytes": int(torch.cuda.max_memory_allocated()),
            }
        )
    payload = {
        "schema_version": 1,
        "study": "TBIK public-source operator probe",
        "device": torch.cuda.get_device_name(0),
        "torch": torch.__version__,
        "shape": [rows, inner, output],
        "scope": (
            "single-GPU batch-invariance operator probe; the public work "
            "targets tensor-parallel invariance and its Hopper CUDA path is "
            "unavailable on RTX 3090, so this is the documented Triton fallback"
        ),
        "rows": payload_rows,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(payload, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

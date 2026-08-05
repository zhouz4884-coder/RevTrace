#!/usr/bin/env python3
"""Build a compact auditable report from a completed V1--V4 matrix."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--summary", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    payload = json.loads(args.summary.read_text(encoding="utf-8"))
    cells = payload["cells"]
    lines = [
        "# RevTrace V100 V1--V4 matrix",
        "",
        f"- Completed cells: **{payload['completed_cells']}**",
        f"- Failed cells retained: **{payload['failed_cells']}**",
        f"- Contract: {payload['claim_boundary']}",
        "",
        "## V1 authority microprofile",
        "",
        "| Model | dtype | B | req/s | batch/singleton | repeat mismatch | singleton mismatch |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for row in cells:
        if row.get("phase") != "V1":
            continue
        lines.append(
            f"| {row['model']} | {row['dtype']} | {row['batch_size']} | "
            f"{row['requests_per_second']:.3f} | {row['batch_over_singleton_speedup']:.3f}x | "
            f"{row['batch_repeat_token_mismatches']} | {row['batch_vs_singleton_token_mismatches']} |"
        )
    lines += [
        "", "## V2 normal-load baselines", "",
        "| Model | Mode | wall (s) | audio xRT | GPU-norm | display P99 | verify | edit P95 |",
        "|---|---|---:|---:|---:|---:|---:|---:|",
    ]
    for row in cells:
        if row.get("phase") != "V2":
            continue
        lines.append(
            f"| {row['model']} | {row['mode']} | {row['wall_seconds']:.3f} | "
            f"{row['audio_throughput_x_realtime']:.3f} | {row['gpu_normalized_audio_throughput']:.3f} | "
            f"{row['display_latency_p99_seconds']:.3f} | {row.get('verification_fraction', 0):.3f} | "
            f"{row.get('reference_final_edit_rate_p95', 0):.4f} |"
        )
    lines += [
        "", "## V3 c128 scale-out", "",
        "| Model | GPUs | throughput | speedup | efficiency | display P99 |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for row in payload.get("scale_rows_c128", []):
        lines.append(
            f"| {row['model']} | {row['used_gpu_count']} | {row['throughput']:.3f} | "
            f"{row['speedup_over_smallest']:.3f}x | {100*row['scale_efficiency']:.1f}% | "
            f"{row['display_p99']:.3f} |"
        )
    lines += [
        "", "## V4 bottleneck attribution", "",
        "| Model | authority dtype | rho | throughput | authority/proposer | J/audio-s |",
        "|---|---|---:|---:|---:|---:|",
    ]
    for row in cells:
        if row.get("phase") != "V4":
            continue
        lines.append(
            f"| {row['model']} | {row['authority_dtype']} | {row['windows_per_segment']} | "
            f"{row['audio_throughput_x_realtime']:.3f} | {row['authority_to_proposer_ratio']:.3f} | "
            f"{row['power']['joules_per_audio_second']:.3f} |"
        )
    if payload.get("failures"):
        lines += ["", "## Retained failed cells", ""]
        for row in payload["failures"]:
            lines.append(f"- `{row['cell_id']}`: `{row['error']}`")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

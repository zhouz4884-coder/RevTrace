#!/usr/bin/env python3
"""Deploy policies selected by Phase 3A envelope artifacts.

The script never accepts a hand-written margin threshold.  It reads the
selected policy from a simultaneous confidence envelope and records the
selection artifact next to each real two-GPU serving result.
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import subprocess
import sys
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--project-root", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--initial-envelope", type=Path, required=True)
    parser.add_argument("--c64-envelope", type=Path, required=True)
    parser.add_argument("--model17-envelope", type=Path, required=True)
    parser.add_argument("--return-envelope", type=Path, required=True)
    return parser.parse_args()


def read_envelope(path: Path) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload["decision"] != "ADAPTIVE_POLICY_ENVELOPE_PASS":
        raise ValueError(f"uncertified policy envelope: {path}")
    if not payload.get("selected_policy"):
        raise ValueError(f"missing selected policy: {path}")
    return payload


def run_stage(
    *,
    args: argparse.Namespace,
    label: str,
    model: str,
    envelope_path: Path,
) -> dict:
    envelope = read_envelope(envelope_path)
    if envelope["source_model"] != model:
        raise ValueError(
            f"envelope/model mismatch: {envelope['source_model']} != {model}"
        )
    threshold = float(envelope["selected_policy"]["threshold"])
    output = args.output_root / f"{label}.json"
    log = args.output_root / "logs" / f"{label}.log"
    output.parent.mkdir(parents=True, exist_ok=True)
    log.parent.mkdir(parents=True, exist_ok=True)
    command = [
        sys.executable,
        str(
            args.project_root
            / "scripts"
            / "remote"
            / "run_revtrace_dual_gpu.py"
        ),
        "--model",
        str(args.data_root / "models" / model),
        "--model-name",
        model,
        "--data-manifest",
        str(args.data_root / "datasets" / "revbatch" / "manifest.json"),
        "--output",
        str(output),
        "--duration-seconds",
        "30",
        "--concurrency",
        "16",
        "--margin-threshold",
        str(threshold),
        "--dtype",
        "float16",
        "--proposer-gpu",
        "0",
        "--verifier-gpu",
        "1",
        "--verifier-lanes",
        "1",
        "--verifier-gpu-memory-utilization",
        "0.82",
        "--verifier-max-model-len",
        "4096",
        "--terminal-canonical-dtype",
        "float16",
        "--terminal-canonical-batch-size",
        "16",
        "--terminal-canonical-batch-invariant",
    ]
    with log.open("wb") as handle:
        completed = subprocess.run(
            command,
            stdout=handle,
            stderr=subprocess.STDOUT,
            check=False,
        )
    if not output.exists():
        raise RuntimeError(
            f"stage {label} produced no result (status {completed.returncode})"
        )
    result = json.loads(output.read_text(encoding="utf-8"))
    metrics = result["summary"]
    return {
        "label": label,
        "model": model,
        "selected_threshold": threshold,
        "envelope": str(envelope_path),
        "result": str(output),
        "process_status": completed.returncode,
        "decision": result["decision"],
        "wall_speedup": metrics["deployed_two_gpu_wall_speedup"],
        "gpu_normalized_speedup": metrics[
            "gpu_normalized_throughput_speedup"
        ],
        "deadline_miss_rate": metrics[
            "state_entry_deadline_miss_rate"
        ],
        "deadline_miss_events": metrics[
            "state_entry_deadline_miss_events"
        ],
        "output_violations": metrics["output_violation_events"],
        "state_projection_violations": metrics[
            "state_projection_violation_events"
        ],
        "stale_or_replayed_results": metrics[
            "stale_or_replayed_result_events"
        ],
    }


def main() -> int:
    args = parse_args()
    args.output_root.mkdir(parents=True, exist_ok=True)
    c64 = read_envelope(args.c64_envelope)
    stages = [
        run_stage(
            args=args,
            label="stage1-0p6b-c16-initial",
            model="Qwen3-ASR-0.6B",
            envelope_path=args.initial_envelope,
        ),
        {
            "label": "stage2-0p6b-c64-contract-change",
            "model": "Qwen3-ASR-0.6B",
            "selected_threshold": c64["selected_policy"]["threshold"],
            "envelope": str(args.c64_envelope),
            "decision": (
                "NEW_CONTRACT_EPOCH_FAIL_CLOSED_DURING_CERTIFICATION"
            ),
            "performance_scope": (
                "excluded: c64 terminal canonical shape is not certified; "
                "no c16 evidence is reused"
            ),
        },
        run_stage(
            args=args,
            label="stage3-1p7b-c16",
            model="Qwen3-ASR-1.7B",
            envelope_path=args.model17_envelope,
        ),
        run_stage(
            args=args,
            label="stage4-0p6b-c16-fresh-return",
            model="Qwen3-ASR-0.6B",
            envelope_path=args.return_envelope,
        ),
    ]
    deployed = [item for item in stages if "wall_speedup" in item]
    passed = (
        all(item["process_status"] == 0 for item in deployed)
        and all(item["decision"].endswith("_PASS") for item in deployed)
        and min(item["gpu_normalized_speedup"] for item in deployed) >= 2.0
        and sum(item["deadline_miss_rate"] for item in deployed) == 0
        and sum(
            item["output_violations"]
            + item["state_projection_violations"]
            + item["stale_or_replayed_results"]
            for item in deployed
        )
        == 0
    )
    summary = {
        "schema_version": 1,
        "study": "RevControl automatic policy deployment sequence",
        "decision": (
            "PHASE3A_DEPLOYED_SEQUENCE_PASS"
            if passed
            else "PHASE3A_DEPLOYED_SEQUENCE_FAIL"
        ),
        "stages": stages,
        "metrics": {
            "minimum_wall_speedup": min(
                item["wall_speedup"] for item in deployed
            ),
            "minimum_gpu_normalized_speedup": min(
                item["gpu_normalized_speedup"] for item in deployed
            ),
            "total_deadline_misses": sum(
                item["deadline_miss_events"] for item in deployed
            ),
            "total_observed_violations": sum(
                item["output_violations"]
                + item["state_projection_violations"]
                + item["stale_or_replayed_results"]
                for item in deployed
            ),
        },
        "environment": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "code_commit": os.environ.get(
                "REVTRACE_CODE_COMMIT", "WORKTREE_PHASE3A"
            ),
        },
        "claim_boundaries": {
            "controller": (
                "thresholds come from simultaneous envelope artifacts, "
                "not CLI choices"
            ),
            "c64": (
                "configuration switch is fail closed; c64 performance is "
                "not claimed without a certified terminal arithmetic path"
            ),
            "risk": (
                "statistical state-disagreement contract, not "
                "deterministic exactness"
            ),
        },
    }
    summary_path = args.output_root / "summary.json"
    summary_path.write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(summary, sort_keys=True))
    return 0 if passed else 2


if __name__ == "__main__":
    raise SystemExit(main())

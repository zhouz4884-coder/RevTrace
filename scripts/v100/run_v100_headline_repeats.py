#!/usr/bin/env python3
"""Repeat the bounded V100 headline cells for dual-plane RevTrace evidence.

V5 preserves the independent RHEL7/Transformers-eager V100 contract used by
V1--V4.  It repeats only the paper-facing allocation/concurrency cells and
records display latency, certified commit latency, energy, and the measured
authority/proposer service ratio.  The p3a5 cell is a cost-model-derived
allocation sensitivity point, not a replacement for the frozen p4a4 headline.
"""

from __future__ import annotations

import argparse
import json
import platform
import statistics
import time
import traceback
from pathlib import Path
from typing import Any

import run_v100_matrix as base


REPEATS = 3
DURATION_SECONDS = 30
WINDOWS_PER_SEGMENT = 3


def aggregate(values: list[float]) -> dict[str, float | None]:
    if not values:
        return {"median": None, "min": None, "max": None}
    return {
        "median": statistics.median(values),
        "min": min(values),
        "max": max(values),
    }


class HeadlineRepeats:
    def __init__(self, args: argparse.Namespace):
        self.args = args
        self.raw = args.output / "raw"
        self.cells: list[dict[str, Any]] = []
        self.failures: list[dict[str, Any]] = []

    def record(self, cell: dict[str, Any]) -> None:
        base.atomic_json(self.raw / f"{cell['cell_id']}.json", cell)
        self.cells.append(cell)
        print(json.dumps({
            "complete": cell["cell_id"],
            "throughput": cell.get("audio_throughput_x_realtime"),
            "display_p99": cell.get("display_latency_p99_seconds"),
            "commit_p99": cell.get("commit_latency_p99_seconds"),
            "authority_to_proposer": cell.get("authority_to_proposer_ratio"),
        }, sort_keys=True), flush=True)

    def fail(self, cell_id: str, exc: BaseException) -> None:
        payload = {
            "schema_version": 1,
            "phase": "V5",
            "cell_id": cell_id,
            "status": "FAILED_CELL_RETAINED",
            "error": repr(exc),
            "traceback": traceback.format_exc(),
        }
        base.atomic_json(self.raw / f"{cell_id}.failure.json", payload)
        self.failures.append(payload)
        print(json.dumps(payload, sort_keys=True), flush=True)

    def run_allocation(
        self,
        *,
        model_name: str,
        model_path: Path,
        manifest: Path,
        allocation: str,
        proposer_gpus: list[int],
        authority_gpus: list[int],
        concurrencies: tuple[int, ...],
    ) -> None:
        proposer = authority = None
        try:
            proposer = base.WorkerPool(
                name=f"v5-{model_name}-{allocation}-p",
                gpus=proposer_gpus,
                model_path=model_path,
                dtype="float16",
                manifest=manifest,
                microbatch=16,
            )
            authority = base.WorkerPool(
                name=f"v5-{model_name}-{allocation}-a",
                gpus=authority_gpus,
                model_path=model_path,
                dtype="float32",
                manifest=manifest,
                microbatch=8,
            )

            # Warm both planes outside every measured cell.  This V5 contract
            # is reported independently from the one-shot V3 cells.
            warm_states = base.initial_states(8)
            proposer.run(base.jobs_for(
                warm_states, audio_end_seconds=2,
                tag=f"v5-{model_name}-{allocation}-warm-p",
            ))
            authority.run(base.jobs_for(
                warm_states, audio_end_seconds=6,
                chunk_advance=WINDOWS_PER_SEGMENT,
                tag=f"v5-{model_name}-{allocation}-warm-a",
            ))

            for concurrency in concurrencies:
                for repeat in range(1, REPEATS + 1):
                    cell_id = (
                        f"v5-{model_name}-{allocation}-c{concurrency}"
                        f"-r{repeat}"
                    )
                    try:
                        cell = base.run_coarse_mode(
                            phase="V5",
                            cell_id=cell_id,
                            model=model_name,
                            mode="coarse-dgft-headline-repeat",
                            concurrency=concurrency,
                            duration=DURATION_SECONDS,
                            proposer=proposer,
                            authority=authority,
                            used_gpus=proposer_gpus + authority_gpus,
                            windows_per_segment=WINDOWS_PER_SEGMENT,
                        )
                        cell.update({
                            "allocation": allocation,
                            "proposer_replicas": len(proposer_gpus),
                            "authority_replicas": len(authority_gpus),
                            "repeat_index": repeat,
                            "repeat_count": REPEATS,
                            "warmup_excluded": True,
                            "measurement_contract": (
                                "30s bilingual cumulative-audio sessions; "
                                "2s display windows; 6s certified segments"
                            ),
                        })
                        self.record(cell)
                    except BaseException as exc:
                        self.fail(cell_id, exc)
        finally:
            for pool in (proposer, authority):
                if pool is not None:
                    pool.close()

    def finalize(self, environment: dict[str, Any]) -> dict[str, Any]:
        grouped: dict[tuple[str, str, int], list[dict[str, Any]]] = {}
        for cell in self.cells:
            key = (
                str(cell["model"]),
                str(cell["allocation"]),
                int(cell["concurrency"]),
            )
            grouped.setdefault(key, []).append(cell)

        aggregates = []
        metric_names = (
            "wall_seconds",
            "audio_throughput_x_realtime",
            "display_latency_p99_seconds",
            "commit_latency_p99_seconds",
            "authority_to_proposer_ratio",
        )
        for (model, allocation, concurrency), cells in sorted(grouped.items()):
            row: dict[str, Any] = {
                "model": model,
                "allocation": allocation,
                "concurrency": concurrency,
                "repeats_completed": len(cells),
                "repeat_indices": sorted(int(cell["repeat_index"]) for cell in cells),
                "display_events": sum(int(cell["display_events"]) for cell in cells),
                "display_slo_2s_misses": sum(
                    int(cell["display_slo_2s_misses"]) for cell in cells
                ),
                "transaction_install_violations": sum(
                    int(cell["transaction_install_violations"]) for cell in cells
                ),
                "uncertified_ancestry_violations": sum(
                    int(cell["uncertified_ancestry_violations"]) for cell in cells
                ),
            }
            for metric in metric_names:
                row[metric] = aggregate([float(cell[metric]) for cell in cells])
            row["energy_joules"] = aggregate([
                float(cell["power"]["energy_joules"]) for cell in cells
            ])
            row["joules_per_audio_second"] = aggregate([
                float(cell["power"]["joules_per_audio_second"]) for cell in cells
            ])
            aggregates.append(row)

        summary = {
            "schema_version": 1,
            "study": "RevTrace V5 repeated dual-plane V100 headline cells",
            "decision": (
                "V5_REPEAT_MATRIX_COMPLETE" if not self.failures
                else "V5_REPEAT_MATRIX_PARTIAL"
            ),
            "environment": environment,
            "contract": {
                "repeats": REPEATS,
                "duration_seconds": DURATION_SECONDS,
                "fine_window_seconds": base.FINE_SECONDS,
                "windows_per_segment": WINDOWS_PER_SEGMENT,
                "display_slo_seconds": 2.0,
                "cells": [
                    "p1a1-c64",
                    "p4a4-c32",
                    "p4a4-c64",
                    "p4a4-c128",
                    "p3a5-c64 allocation sensitivity",
                ],
            },
            "completed_cells": len(self.cells),
            "failed_cells": len(self.failures),
            "aggregates": aggregates,
            "cells": self.cells,
            "failures": self.failures,
            "claim_boundary": (
                "V5 repeats bounded single-node V100 display and certified-commit "
                "measurements. It does not establish multi-node scalability, "
                "production flip prevalence, or an unbounded asynchronous queue."
            ),
        }
        base.atomic_json(self.args.output / "v5_headline_summary.json", summary)
        return summary


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--models", nargs="*", default=[
        "Qwen3-ASR-0.6B", "Qwen3-ASR-1.7B"
    ])
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    diagnostic_dir = args.output / "worker_diagnostics"
    diagnostic_dir.mkdir(parents=True, exist_ok=True)
    base.os.environ["REVTRACE_DIAGNOSTIC_DIR"] = str(diagnostic_dir)

    import torch
    import transformers

    environment = {
        "hostname": platform.node(),
        "python": platform.python_version(),
        "torch": torch.__version__,
        "torch_cuda": torch.version.cuda,
        "transformers": transformers.__version__,
        "gpu_count": torch.cuda.device_count(),
        "gpus": [torch.cuda.get_device_name(i) for i in range(torch.cuda.device_count())],
        "pbs_jobid": base.os.environ.get("PBS_JOBID"),
        "runner_sha256": base.sha256(Path(__file__)),
        "base_runner_sha256": base.sha256(Path(base.__file__)),
        "timestamp_unix": time.time(),
    }
    base.atomic_json(args.output / "environment.json", environment)

    matrix = HeadlineRepeats(args)
    manifest = args.root / "datasets/revbatch/manifest.json"
    allocations = (
        ("p1a1", [0], [4], (64,)),
        ("p4a4", [0, 1, 2, 3], [4, 5, 6, 7], (32, 64, 128)),
        ("p3a5", [0, 1, 2], [3, 4, 5, 6, 7], (64,)),
    )
    for model_name in args.models:
        model_path = args.root / "models" / model_name
        for allocation, proposer_gpus, authority_gpus, concurrencies in allocations:
            try:
                matrix.run_allocation(
                    model_name=model_name,
                    model_path=model_path,
                    manifest=manifest,
                    allocation=allocation,
                    proposer_gpus=proposer_gpus,
                    authority_gpus=authority_gpus,
                    concurrencies=concurrencies,
                )
            except BaseException as exc:
                matrix.fail(f"v5-{model_name}-{allocation}-fatal", exc)

    summary = matrix.finalize(environment)
    print(json.dumps({
        "decision": summary["decision"],
        "completed_cells": summary["completed_cells"],
        "failed_cells": summary["failed_cells"],
    }, sort_keys=True))
    return 0 if not summary["failures"] else 2


if __name__ == "__main__":
    raise SystemExit(main())

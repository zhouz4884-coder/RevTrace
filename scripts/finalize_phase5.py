#!/usr/bin/env python3
"""Freeze Phase 5 live adaptation, protection, Pareto, and artifact evidence."""

from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
PHASE5 = ROOT / "results" / "phase5"
ARTIFACT = ROOT / "artifact" / "phase5-system-hardening-v1"


def read(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(path)
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def phase5a_summary(payload: dict[str, Any]) -> dict[str, Any]:
    stages = []
    for stage in payload["stages"]:
        stages.append(
            {
                key: stage[key]
                for key in (
                    "label",
                    "concurrency",
                    "events",
                    "certified_after_episode",
                    "certified_after_events",
                    "threshold",
                    "fast_path_window",
                    "risk_upper_bound",
                    "verification_fraction",
                    "goodput_events_per_second",
                    "state_entry_latency_seconds_p99",
                    "deadline_miss_events",
                    "output_violations",
                    "state_violations",
                    "service_wall_seconds",
                    "audit_seconds_excluded_from_service",
                    "energy",
                )
            }
        )
    return {
        "decision": payload["decision"],
        "model": payload["model"],
        "stages": stages,
        "all_switches_fail_closed": all(
            stage["switch_action"]
            == "fast_path_window=0; all state entries verified"
            for stage in payload["stages"]
        ),
        "models_persistent_across_switches": True,
        "claim_boundary": (
            "live c16-c64-c16 service with post-stage canonical replay "
            "excluded from service timing"
        ),
    }


def phase5b_summary(paths: list[Path]) -> dict[str, Any]:
    runs = [read(path) for path in paths]
    old = read(ROOT / "results" / "phase4" / "summary.json")[
        "stages"
    ]["phase4b_whisper_feedback"]
    safety = all(
        run["counts"]["output_violations"] == 0
        and run["counts"]["state_violations"] == 0
        for run in runs
    )
    performance = all(
        run["metrics"]["wall_speedup"] >= 2.0 for run in runs
    )
    return {
        "decision": (
            "PHASE5B_PROTECTION_AND_PERFORMANCE_PASS"
            if safety and performance
            else "PHASE5B_PROTECTION_PASS_PERFORMANCE_BOUNDARY"
            if safety
            else "PHASE5B_PROTECTION_FAIL"
        ),
        "feedback_on_unprotected_propagating_pairs": old[
            "feedback_on_propagating_pairs"
        ],
        "feedback_off_propagating_pairs": old[
            "feedback_off_propagating_pairs"
        ],
        "models": {
            run["model"]: {
                "events": run["counts"]["events"],
                "verified_events": run["counts"]["verified_events"],
                "known_phase4_pairs": run["counts"][
                    "known_phase4_pairs"
                ],
                "known_pairs_protected": run["counts"][
                    "known_pairs_protected"
                ],
                "output_violations": run["counts"][
                    "output_violations"
                ],
                "state_violations": run["counts"]["state_violations"],
                "verification_fraction": run["metrics"][
                    "verification_fraction"
                ],
                "wall_speedup": run["metrics"]["wall_speedup"],
                "state_violation_upper_95": run["metrics"][
                    "state_violation_upper_95"
                ],
            }
            for run in runs
        },
        "claim_boundary": (
            "Whisper is a finite cross-family protection gate; Phase 4 "
            "feedback OFF is the causal boundary"
        ),
    }


def phase5c_summary(paths: list[Path]) -> dict[str, Any]:
    runs = [read(path) for path in paths]
    cells = []
    for run, path in zip(runs, paths):
        summary = run["summary"]
        cells.append(
            {
                "cell": path.stem,
                "model": run["model_name"],
                "concurrency": run["concurrency"],
                "duration_seconds": run["duration_seconds"],
                "arrival_mode": run.get("arrival_mode", "unknown"),
                "language_mode": run.get("language_mode", "unknown"),
                "wall_speedup": summary[
                    "deployed_two_gpu_wall_speedup"
                ],
                "gpu_normalized_speedup": summary[
                    "gpu_normalized_throughput_speedup"
                ],
                "slo_goodput_events_per_second": summary[
                    "deployed_slo_goodput_events_per_second"
                ],
                "p99_seconds": summary[
                    "state_entry_latency_seconds_p99"
                ],
                "deadline_misses": summary[
                    "state_entry_deadline_miss_events"
                ],
                "verification_fraction": summary[
                    "verification_fraction"
                ],
                "output_violations": summary[
                    "output_violation_events"
                ],
                "state_violations": summary[
                    "state_projection_violation_events"
                ],
                "stale_results": summary[
                    "stale_or_replayed_result_events"
                ],
                "joules_per_audio_second": summary[
                    "service_energy"
                ]["joules_per_audio_second"],
            }
        )
    safe_cells = sum(
        row["output_violations"] == 0
        and row["state_violations"] == 0
        and row["stale_results"] == 0
        for row in cells
    )
    deadline_cells = sum(row["deadline_misses"] == 0 for row in cells)
    return {
        "decision": (
            "PHASE5C_WORKLOAD_FRONTIER_COMPLETE"
            if len(cells) >= 8
            else "PHASE5C_WORKLOAD_FRONTIER_INCOMPLETE"
        ),
        "cells": cells,
        "cell_count": len(cells),
        "safe_cells": safe_cells,
        "zero_deadline_miss_cells": deadline_cells,
        "claim_boundary": (
            "live two-GPU cells; energy integrates nvidia-smi samples over "
            "the service interval"
        ),
    }


def paper_tables(summary: dict[str, Any]) -> str:
    def number(value: object, spec: str = ".3f") -> str:
        return "NA" if value is None else format(float(value), spec)

    lines = [
        "# Phase 5 paper tables",
        "",
        "## Live adaptive c16 -> c64 -> c16",
        "",
        "| Stage | c | Events | Cert. event | Learned tau | Fast window | Risk upper | Verify | Goodput | P99 | Miss | J/audio-s |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in summary["phase5a"]["stages"]:
        lines.append(
            f"| {row['label']} | {row['concurrency']} | {row['events']} | "
            f"{row['certified_after_events']} | "
            f"{number(row['threshold'], '.6g')} | "
            f"{number(row['fast_path_window'])} | "
            f"{number(row['risk_upper_bound'], '.4%')} | "
            f"{number(row['verification_fraction'], '.2%')} | "
            f"{number(row['goodput_events_per_second'])} | "
            f"{number(row['state_entry_latency_seconds_p99'])} | "
            f"{row['deadline_miss_events']} | "
            f"{row['energy']['joules_per_audio_second']:.3f} |"
        )
    lines.extend(
        [
            "",
            "## Whisper protected feedback",
            "",
            "| Model | Events | Verify | Protected pairs | Output/state violations | Wall speedup |",
            "|---|---:|---:|---:|---:|---:|",
        ]
    )
    for model, row in summary["phase5b"]["models"].items():
        lines.append(
            f"| {model} | {row['events']} | "
            f"{row['verification_fraction']:.2%} | "
            f"{row['known_pairs_protected']}/{row['known_phase4_pairs']} | "
            f"{row['output_violations']}/{row['state_violations']} | "
            f"{row['wall_speedup']:.3f}x |"
        )
    lines.extend(
        [
            "",
            "## Workload and energy frontier",
            "",
            "| Cell | Model | c | Wall | GPU norm. | Goodput | P99 | Miss | Verify | J/audio-s |",
            "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for row in summary["phase5c"]["cells"]:
        lines.append(
            f"| {row['cell']} | {row['model']} | {row['concurrency']} | "
            f"{row['wall_speedup']:.3f}x | "
            f"{row['gpu_normalized_speedup']:.3f}x | "
            f"{row['slo_goodput_events_per_second']:.3f} | "
            f"{row['p99_seconds']:.3f} | {row['deadline_misses']} | "
            f"{row['verification_fraction']:.2%} | "
            f"{row['joules_per_audio_second']:.3f} |"
        )
    return "\n".join(lines) + "\n"


def freeze_artifact(paths: list[Path]) -> None:
    if ARTIFACT.exists():
        shutil.rmtree(ARTIFACT)
    ARTIFACT.mkdir(parents=True)
    copied = []
    for path in paths:
        relative = path.relative_to(ROOT)
        destination = ARTIFACT / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, destination)
        copied.append(destination)
    manifest = {
        "schema_version": 1,
        "artifact": "RevTrace Phase 5 system hardening",
        "scope": (
            "paper-facing summaries and consequential corpus; raw remote "
            "event traces are not redistributed"
        ),
        "files": [
            {
                "path": path.relative_to(ARTIFACT).as_posix(),
                "bytes": path.stat().st_size,
                "sha256": sha256(path),
            }
            for path in sorted(copied)
        ],
    }
    (ARTIFACT / "MANIFEST.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    live_path = PHASE5 / "live_adaptive" / "formal-c16-c64-c16.json"
    whisper_paths = sorted((PHASE5 / "whisper_protection").glob("*.json"))
    workload_paths = sorted((PHASE5 / "workload_matrix").glob("*.json"))
    if len(whisper_paths) != 2:
        raise RuntimeError("expected two Whisper protected runs")
    if len(workload_paths) != 8:
        raise RuntimeError("expected eight workload cells")
    live = phase5a_summary(read(live_path))
    whisper = phase5b_summary(whisper_paths)
    workload = phase5c_summary(workload_paths)
    slack = read(PHASE5 / "slack_packing" / "summary.json")
    corpus = read(PHASE5 / "consequential_corpus" / "corpus.json")
    baselines = read(PHASE5 / "baselines" / "summary.json")
    main_pass = (
        live["decision"] == "PHASE5A_LIVE_ADAPTIVE_CONTROL_PASS"
        and whisper["decision"]
        in {
            "PHASE5B_PROTECTION_AND_PERFORMANCE_PASS",
            "PHASE5B_PROTECTION_PASS_PERFORMANCE_BOUNDARY",
        }
        and workload["cell_count"] == 8
        and workload["safe_cells"] == 8
    )
    summary = {
        "schema_version": 1,
        "study": "RevTrace Phase 5 system hardening",
        "decision": (
            "PAPER_CORE_GO_PHASE5_SYSTEM_HARDENING"
            if main_pass
            else "PHASE5_COMPLETE_WITH_MAIN_GATE_BOUNDARY"
        ),
        "phase5a": live,
        "phase5b": whisper,
        "phase5c": workload,
        "phase5d": slack,
        "phase5e": {
            key: corpus[key]
            for key in (
                "decision",
                "candidate_records",
                "distinct_records",
                "duplicates_removed",
                "by_family",
                "by_source",
            )
        },
        "baselines": {
            "decision": baselines["decision"],
            "records": baselines["records"],
            "policies": baselines["policies"],
            "transaction_counterexample": baselines[
                "transaction_counterexample"
            ],
        },
        "claim_boundaries": [
            "zero observed failures are empirical, not deterministic proof",
            "risk certificates target frozen canonical disagreement",
            "wall and GPU-normalized performance are reported together",
            "Whisper and targeted-pair experiments do not estimate prevalence",
            "Phase 5D remains P50 replay because audit P99 was not measured",
        ],
    }
    summary_path = PHASE5 / "summary.json"
    summary_path.write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    tables_path = PHASE5 / "PAPER_TABLES.md"
    tables_path.write_text(paper_tables(summary), encoding="utf-8")
    freeze_artifact(
        [
            summary_path,
            tables_path,
            PHASE5 / "slack_packing" / "summary.json",
            PHASE5 / "consequential_corpus" / "corpus.json",
            PHASE5 / "baselines" / "summary.json",
        ]
    )
    print(json.dumps({"decision": summary["decision"]}, indent=2))
    return 0 if main_pass else 2


if __name__ == "__main__":
    raise SystemExit(main())

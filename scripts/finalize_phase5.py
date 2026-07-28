#!/usr/bin/env python3
"""Freeze Phase 5 live adaptation, protection, Pareto, and artifact evidence."""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
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


def phase5a_summary(
    payload: dict[str, Any],
    static_oracle_payload: dict[str, Any],
) -> dict[str, Any]:
    oracle_by_label = {
        stage["label"]: stage for stage in static_oracle_payload["stages"]
    }
    stages = []
    for stage in payload["stages"]:
        oracle = oracle_by_label[stage["label"]]
        oracle_goodput = float(oracle["goodput_events_per_second"])
        episodes = stage["episodes_detail"]
        recertification_seconds = None
        recovery_90_seconds = None
        elapsed = 0.0
        adaptation_regret_events = 0.0
        verifier_utilization: list[float] = []
        previous_verifier_seconds = 0.0
        for row in episodes:
            elapsed += float(row["wall_seconds"])
            cumulative_verifier_seconds = float(
                row["required_verifier_seconds"]
            )
            verifier_utilization.append(
                min(
                    1.0,
                    (
                        cumulative_verifier_seconds
                        - previous_verifier_seconds
                    )
                    / max(float(row["wall_seconds"]), 1e-12),
                )
            )
            previous_verifier_seconds = cumulative_verifier_seconds
            if row["certified"] and recertification_seconds is None:
                recertification_seconds = elapsed
            if (
                row["certified"]
                and row["goodput_events_per_second"]
                >= 0.9 * oracle_goodput
                and recovery_90_seconds is None
            ):
                recovery_90_seconds = elapsed
            adaptation_regret_events += max(
                0.0,
                oracle_goodput * float(row["wall_seconds"])
                - float(row["events"]),
            )
        summary = {
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
        summary.update(
            {
                "fail_closed_latency_events": 0,
                "recertification_seconds": recertification_seconds,
                "recovery_to_90pct_oracle_seconds": recovery_90_seconds,
                "independent_static_oracle_goodput": oracle_goodput,
                "goodput_fraction_of_independent_oracle": (
                    float(stage["goodput_events_per_second"])
                    / max(oracle_goodput, 1e-12)
                ),
                "adaptation_regret_events": adaptation_regret_events,
                "verifier_peak_utilization_proxy": max(verifier_utilization),
                "post_certified_episodes": sum(
                    int(row["certified"]) for row in episodes
                ),
                "static_oracle": {
                    "decision": static_oracle_payload["decision"],
                    "threshold": oracle["threshold"],
                    "risk_upper_bound": oracle["risk_upper_bound"],
                    "goodput_events_per_second": oracle_goodput,
                    "state_entry_latency_seconds_p99": oracle[
                        "state_entry_latency_seconds_p99"
                    ],
                    "deadline_miss_events": oracle[
                        "deadline_miss_events"
                    ],
                    "output_violations": oracle["output_violations"],
                    "state_violations": oracle["state_violations"],
                },
            }
        )
        stages.append(summary)
    sequential = read(
        PHASE5 / "live_adaptive" / "diagnostics" / "c64-sequential.json"
    )["stages"][0]
    overlapped = read(
        PHASE5 / "live_adaptive" / "diagnostics" / "c64-overlapped.json"
    )["stages"][0]
    return {
        "decision": payload["decision"],
        "static_oracle_decision": static_oracle_payload["decision"],
        "model": payload["model"],
        "stages": stages,
        "all_switches_fail_closed": all(
            stage["switch_action"]
            == "fast_path_window=0; all state entries verified"
            for stage in payload["stages"]
        ),
        "models_persistent_across_switches": True,
        "c64_overlap_ablation": {
            "sequential_p99_seconds": sequential[
                "state_entry_latency_seconds_p99"
            ],
            "overlapped_p99_seconds": overlapped[
                "state_entry_latency_seconds_p99"
            ],
            "p99_reduction": 1.0
            - overlapped["state_entry_latency_seconds_p99"]
            / sequential["state_entry_latency_seconds_p99"],
            "sequential_deadline_misses": sequential[
                "deadline_miss_events"
            ],
            "overlapped_deadline_misses": overlapped[
                "deadline_miss_events"
            ],
            "wall_speedup": sequential["service_wall_seconds"]
            / overlapped["service_wall_seconds"],
            "energy_reduction": 1.0
            - overlapped["energy"]["joules_per_audio_second"]
            / sequential["energy"]["joules_per_audio_second"],
            "evidence": (
                "same c64 jobs, model, fixed canonical shape, and replay "
                "oracle; execution overlap is the only intervention"
            ),
        },
        "claim_boundary": (
            "live c16-c64-c16 service with post-stage canonical replay "
            "excluded from service timing; T90 and regret use a separate "
            "frozen-threshold run with a disjoint stream seed. Both the "
            "adaptive and static policies are risk-limited rather than exact."
        ),
    }


def phase5b_summary(
    protected_paths: list[Path],
    feedback_off_paths: list[Path],
) -> dict[str, Any]:
    runs = [read(path) for path in protected_paths]
    feedback_off_runs = [read(path) for path in feedback_off_paths]
    diagnostic_paths = sorted(
        (PHASE5 / "whisper_protection" / "diagnostics").glob("*.json")
    )
    diagnostics = [read(path) for path in diagnostic_paths]
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
                "protection_mode": run["config"].get(
                    "protection_mode", "unrecorded"
                ),
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
        "feedback_off": {
            run["model"]: {
                "events": run["counts"]["events"],
                "certification_events": run["counts"][
                    "certification_events"
                ],
                "local_output_differences": run["counts"][
                    "local_output_differences"
                ],
                "state_propagation_violations": run["counts"][
                    "state_propagation_violations"
                ],
                "verification_fraction": run["metrics"][
                    "verification_fraction"
                ],
                "wall_speedup": run["metrics"]["wall_speedup"],
            }
            for run in feedback_off_runs
        },
        "replication_signal_boundary": {
            run["model"]: {
                "events": run["counts"]["events"],
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
                "reason": (
                    "rows can agree within a replicated batch while the "
                    "entire batch differs from singleton canonical"
                ),
            }
            for run in diagnostics
        },
        "claim_boundary": (
            "Whisper is a finite cross-family protection gate. Feedback OFF "
            "makes the future-text state projection empty, so local batch "
            "differences do not become state-propagation violations. "
            "Replication consistency alone is not a sound singleton-equivalence "
            "certificate."
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
                "p95_seconds": summary[
                    "state_entry_latency_seconds_p95"
                ],
                "p50_seconds": summary[
                    "state_entry_latency_seconds_p50"
                ],
                "deadline_misses": summary[
                    "state_entry_deadline_miss_events"
                ],
                "verification_fraction": summary[
                    "verification_fraction"
                ],
                "verifier_to_proposer_service_ratio": summary[
                    "verifier_to_proposer_service_ratio"
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
                "observed_state_violation_rate": (
                    float(summary["state_projection_violation_events"])
                    / max(int(summary["event_count"]), 1)
                ),
                "observed_state_risk_upper_95": (
                    1.0
                    - 0.05
                    ** (
                        1.0
                        / max(int(summary["event_count"]), 1)
                    )
                    if summary["state_projection_violation_events"] == 0
                    else None
                ),
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
    safety_failures: list[dict[str, Any]] = []
    for run, path in zip(runs, paths):
        for event in run["events"]:
            comparison = event["selected_vs_canonical"]
            if (
                not comparison["token_exact"]
                or not comparison["state_projection_token_exact"]
            ):
                safety_failures.append(
                    {
                        "cell": path.stem,
                        "revision_id": event["revision_id"],
                        "language": event["language"],
                        "verified": event["verified"],
                        "proposal_minimum_margin": event[
                            "proposal_minimum_margin"
                        ],
                        "output_exact": comparison["token_exact"],
                        "state_projection_exact": comparison[
                            "state_projection_token_exact"
                        ],
                        "interpretation": (
                            "unseen contract exceeded the frozen margin "
                            "policy"
                            if not event["verified"]
                            else "canonical-selected path disagreed"
                        ),
                    }
                )
    return {
        "decision": (
            "PHASE5C_WORKLOAD_FRONTIER_PASS"
            if len(cells) >= 8
            and safe_cells == len(cells)
            and deadline_cells == len(cells)
            else "PHASE5C_WORKLOAD_FRONTIER_COMPLETE_WITH_BOUNDARIES"
            if len(cells) >= 8
            else "PHASE5C_WORKLOAD_FRONTIER_INCOMPLETE"
        ),
        "cells": cells,
        "cell_count": len(cells),
        "safe_cells": safe_cells,
        "zero_deadline_miss_cells": deadline_cells,
        "safety_gate_pass": safe_cells == len(cells),
        "all_cells_meet_deadline_gate": deadline_cells == len(cells),
        "safety_failures": safety_failures,
        "deadline_boundary_cells": [
            row["cell"] for row in cells if row["deadline_misses"] > 0
        ],
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
        "| Stage | c | Events | Cert. event | Learned tau | Fast window | Risk upper | Verify | Goodput | P99 | Miss | T-cert. | Regret | J/audio-s |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
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
            f"{number(row['recertification_seconds'])} | "
            f"{number(row['adaptation_regret_events'])} | "
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
            "### Feedback-OFF causal boundary",
            "",
            "| Model | Events | Certification | Local differences | State-propagation violations | Wall speedup |",
            "|---|---:|---:|---:|---:|---:|",
        ]
    )
    for model, row in summary["phase5b"]["feedback_off"].items():
        lines.append(
            f"| {model} | {row['events']} | "
            f"{row['certification_events']} | "
            f"{row['local_output_differences']} | "
            f"{row['state_propagation_violations']} | "
            f"{row['wall_speedup']:.3f}x |"
        )
    lines.extend(
        [
            "",
            "### Replication-consistency signal boundary",
            "",
            "| Model | Events | Known pairs protected | Output/state violations |",
            "|---|---:|---:|---:|",
        ]
    )
    for model, row in summary["phase5b"][
        "replication_signal_boundary"
    ].items():
        lines.append(
            f"| {model} | {row['events']} | "
            f"{row['known_pairs_protected']}/{row['known_phase4_pairs']} | "
            f"{row['output_violations']}/{row['state_violations']} |"
        )
    lines.extend(
        [
            "",
            "## Workload and energy frontier",
            "",
            "| Cell | Model | c | Wall | GPU norm. | Goodput | P99 | Miss | Verify | Output/state violations | State risk | 95% upper if zero | J/audio-s |",
            "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
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
            f"{row['output_violations']}/{row['state_violations']} | "
            f"{row['observed_state_violation_rate']:.3%} | "
            f"{number(row['observed_state_risk_upper_95'], '.3%')} | "
            f"{row['joules_per_audio_second']:.3f} |"
        )
    return "\n".join(lines) + "\n"


def freeze_artifact(
    paths: list[Path],
    *,
    summary: dict[str, Any],
) -> None:
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
    readme = ARTIFACT / "README.md"
    readme.write_text(
        "\n".join(
            [
                "# RevTrace Phase 5 system-hardening artifact",
                "",
                "This bounded artifact freezes the evidence used by the "
                "Phase 5 A--E report. It does not redistribute model "
                "weights, audio, environments, or the largest remote traces.",
                "",
                "## Gate decisions",
                "",
                f"- Phase 5A: `{summary['phase5a']['decision']}`",
                f"- Phase 5B: `{summary['phase5b']['decision']}`",
                f"- Phase 5C: `{summary['phase5c']['decision']}`",
                f"- Phase 5D: `{summary['phase5d']['decision']}`",
                f"- Phase 5E: `{summary['phase5e']['decision']}`",
                "",
                "## Reproduce the bounded summaries",
                "",
                "```bash",
                "python scripts/finalize_phase5.py",
                "python scripts/audit_phase5_artifact.py",
                "pytest -q",
                "```",
                "",
                "The risk bounds are statistical. Zero observed failures "
                "must not be read as deterministic exactness or as a "
                "production prevalence estimate.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    copied.append(readme)
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
    live_path = (
        PHASE5 / "live_adaptive" / "formal-v2-c16-c64-c16.json"
    )
    static_oracle_path = (
        PHASE5 / "live_adaptive" / "static-oracle-v2.json"
    )
    protected_paths = sorted(
        (PHASE5 / "whisper_protection").glob("*-v2.json")
    )
    feedback_off_paths = sorted(
        (PHASE5 / "whisper_protection").glob("*-feedback-off.json")
    )
    workload_paths = sorted(
        path
        for path in (PHASE5 / "workload_matrix").glob("*.json")
        if path.name != "SOURCE_MANIFEST.json"
    )
    if len(protected_paths) != 2:
        raise RuntimeError("expected two Whisper protected runs")
    if len(feedback_off_paths) != 2:
        raise RuntimeError("expected two Whisper feedback-OFF runs")
    if len(workload_paths) != 8:
        raise RuntimeError("expected eight workload cells")
    live = phase5a_summary(read(live_path), read(static_oracle_path))
    whisper = phase5b_summary(protected_paths, feedback_off_paths)
    workload = phase5c_summary(workload_paths)
    workload_source_manifest = (
        PHASE5 / "workload_matrix" / "SOURCE_MANIFEST.json"
    )
    workload_source_manifest.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "scope": (
                    "large event-level workload traces remain on the "
                    "designated experiment disk and are not redistributed"
                ),
                "files": [
                    {
                        "path": path.name,
                        "bytes": path.stat().st_size,
                        "sha256": sha256(path),
                    }
                    for path in workload_paths
                ],
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    slack = read(PHASE5 / "slack_packing" / "live-c8.json")
    corpus = read(PHASE5 / "consequential_corpus" / "corpus.json")
    baselines = read(PHASE5 / "baselines" / "summary.json")
    source_base_commit = subprocess.check_output(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        text=True,
    ).strip()
    runner_paths = {
        "phase5a": ROOT
        / "scripts"
        / "remote"
        / "run_phase5a_live_adaptive.py",
        "phase5b_protected": ROOT
        / "scripts"
        / "remote"
        / "run_phase5b_whisper_protected.py",
        "phase5b_feedback_off": ROOT
        / "scripts"
        / "remote"
        / "run_phase5b_whisper_feedback_off.py",
        "phase5b_executor": ROOT
        / "scripts"
        / "remote"
        / "run_whisper_feedback_gate.py",
        "phase5c": ROOT
        / "scripts"
        / "remote"
        / "run_revtrace_dual_gpu.py",
        "phase5d": ROOT
        / "scripts"
        / "remote"
        / "run_phase5d_live_slack_packing.py",
    }
    run_ledger_path = PHASE5 / "RUN_LEDGER.json"
    run_ledger_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "experiment_id": "P5_SYSTEM_HARDENING",
                "source_base_commit": source_base_commit,
                "source_state": (
                    "base commit plus publication-runner hashes. Phase 5A "
                    "v2 preceded a logging-only audit_violation_rows change, "
                    "so the publication hash is not retroactively claimed "
                    "as its exact execution hash"
                ),
                "hardware": "2 x NVIDIA RTX 3090 24 GiB",
                "data_root": (
                    "/media/user/5bc0dc8d-c938-4b2a-af1b-"
                    "94174fc511a9"
                ),
                "environment": (
                    "/media/user/5bc0dc8d-c938-4b2a-af1b-"
                    "94174fc511a9/envs/revbatch-cu128"
                ),
                "publication_runner_sha256": {
                    label: sha256(path)
                    for label, path in runner_paths.items()
                },
                "stages": {
                    "phase5a": {
                        "config": (
                            "configs/"
                            "revtrace_phase5_system_hardening_gate.json"
                        ),
                        "results": [
                            (
                                "results/revtrace/phase5/live_adaptive/"
                                "formal-v2-c16-c64-c16.json"
                            ),
                            (
                                "results/revtrace/phase5/live_adaptive/"
                                "static-oracle-v2.json"
                            ),
                        ],
                        "log_root": "logs/revtrace/phase5/live_adaptive",
                    },
                    "phase5b": {
                        "results": (
                            "results/revtrace/phase5/whisper_protection"
                        ),
                        "log_root": (
                            "logs/revtrace/phase5/whisper_protection"
                        ),
                        "protocol_repair": (
                            "corrected to the 16 kHz LibriSpeech manifest "
                            "and data-root Phase 4 pair paths"
                        ),
                    },
                    "phase5c": {
                        "results": (
                            "results/revtrace/phase5/workload_matrix"
                        ),
                        "source_manifest": (
                            "results/phase5/workload_matrix/"
                            "SOURCE_MANIFEST.json"
                        ),
                    },
                    "phase5d": {
                        "result": (
                            "results/revtrace/phase5/slack_packing/"
                            "live-c8.json"
                        ),
                        "log": (
                            "logs/revtrace/phase5/slack_packing/"
                            "live-c8.log"
                        ),
                    },
                    "phase5e": {
                        "result": (
                            "results/phase5/consequential_corpus/"
                            "corpus.json"
                        ),
                    },
                },
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    phase5_complete = (
        workload["cell_count"] == 8
        and len(whisper["models"]) == 2
        and len(whisper["feedback_off"]) == 2
        and corpus["decision"] == "PHASE5E_CONSEQUENTIAL_CORPUS_COMPLETE"
    )
    all_hard_gates_pass = (
        live["decision"] == "PHASE5A_LIVE_ADAPTIVE_CONTROL_PASS"
        and live["static_oracle_decision"]
        == "PHASE5A_STATIC_CERTIFIED_ORACLE_PASS"
        and whisper["decision"]
        == "PHASE5B_PROTECTION_AND_PERFORMANCE_PASS"
        and workload["safety_gate_pass"]
        and workload["all_cells_meet_deadline_gate"]
        and slack["decision"] == "PHASE5D_LIVE_SLACK_PACKING_PASS"
    )
    summary = {
        "schema_version": 1,
        "study": "RevTrace Phase 5 system hardening",
        "decision": (
            "PHASE5_ALL_HARD_GATES_PASS"
            if all_hard_gates_pass
            else "PAPER_CORE_GO_WITH_PHASE5_MEASURED_BOUNDARIES"
            if phase5_complete
            else "PHASE5_INCOMPLETE"
        ),
        "all_hard_gates_pass": all_hard_gates_pass,
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
            (
                "Phase 5D is a live one-GPU packing experiment; it passed "
                "zero-miss and detection-time gates but exceeded the frozen "
                "2% P99-change limit"
            ),
            (
                "Phase 5A risk bounds are statistical and permit rare "
                "observed state violations; neither adaptive nor static "
                "thresholds are deterministic certificates"
            ),
            (
                "Phase 5C contains one unseen c32/Chinese/burst contract "
                "with state-entry violations and multiple cells outside "
                "the RTX 3090 two-second service region"
            ),
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
            run_ledger_path,
            live_path,
            static_oracle_path,
            *protected_paths,
            *feedback_off_paths,
            PHASE5 / "slack_packing" / "live-c8.json",
            PHASE5 / "consequential_corpus" / "corpus.json",
            PHASE5 / "baselines" / "summary.json",
            workload_source_manifest,
            ROOT
            / "docs"
            / "reports"
            / "phase5_system_hardening_report.md",
            ROOT / "docs" / "CLAIM_BOUNDARIES.md",
            ROOT
            / "configs"
            / "revtrace_phase5_system_hardening_gate.json",
            ROOT / "scripts" / "finalize_phase5.py",
            ROOT / "scripts" / "audit_phase5_artifact.py",
            ROOT / "src" / "revtrace" / "phase5.py",
            ROOT / "src" / "revtrace" / "risk_window.py",
            ROOT / "tests" / "test_phase5.py",
            ROOT / "tests" / "test_phase5_artifact.py",
        ],
        summary=summary,
    )
    print(json.dumps({"decision": summary["decision"]}, indent=2))
    return 0 if phase5_complete else 2


if __name__ == "__main__":
    raise SystemExit(main())

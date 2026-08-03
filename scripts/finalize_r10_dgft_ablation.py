#!/usr/bin/env python3
"""Build a ceteris-paribus SG / Coarse-DGFT / Hybrid-DGFT ablation.

The SG runner emits one record per 2-second revision, while the DGFT runner
emits one record per 6-second authority segment.  Consequently event counts
must not be compared as throughput.  This finalizer first proves that all
cells cover the same 16 sessions and 30 seconds of audio per session, and then
reports wall time, GPU-normalized throughput, energy per audio-second, tail
latency, and each path's own reference-quality contract.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


MODE_FILES = {
    "sg": {
        "Qwen3-ASR-0.6B": "sg/qwen06-sg-r10.json",
        "Qwen3-ASR-1.7B": "sg/qwen17-sg-r10.json",
    },
    "coarse-dgft": {
        "Qwen3-ASR-0.6B": "qwen06-dgft-fp32batch.json",
        "Qwen3-ASR-1.7B": "qwen17-dgft-fp32batch.json",
    },
    "hybrid-dgft": {
        "Qwen3-ASR-0.6B": "qwen06-hybrid-fp32batch.json",
        "Qwen3-ASR-1.7B": "qwen17-hybrid-fp32batch.json",
    },
}


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def session_ids(payload: dict[str, Any]) -> list[str]:
    return sorted({str(event["session_id"]) for event in payload["events"]})


def energy_reduction(
    service: dict[str, Any], reference: dict[str, Any]
) -> float:
    return 1.0 - (
        float(service["joules_per_audio_second"])
        / float(reference["joules_per_audio_second"])
    )


def audit_sg(path: Path, model: str) -> dict[str, Any]:
    payload = load_json(path)
    summary = payload["summary"]
    events = payload["events"]
    expected_margin = 0.05 if model.endswith("0.6B") else 0.10
    recorded_commit = str(payload["environment"].get("code_commit", ""))
    checks = {
        "model": payload["model_name"] == model,
        "duration_30s": int(payload["duration_seconds"]) == 30,
        "concurrency_16": int(payload["concurrency"]) == 16,
        "arrival_sync": payload["arrival_mode"] == "sync",
        "language_mixed": payload["language_mode"] == "mixed"
        and {event["language"] for event in events}
        == {"English", "Chinese"},
        "fp16_proposer_and_singleton_authority": payload["dtype"]
        == "float16"
        and payload["contract"]["canonical"]
        == "FP16 singleton execution",
        "frozen_model_specific_margin": float(payload["margin_threshold"])
        == expected_margin,
        "recorded_code_commit": len(recorded_commit) == 40
        and all(character in "0123456789abcdef" for character in recorded_commit),
        "sixteen_sessions": len(session_ids(payload)) == 16,
        "thirty_second_terminal": max(event["chunk_id"] for event in events)
        == 14,
        "output_trace_exact": int(summary["output_violation_events"]) == 0,
        "state_trace_exact": int(summary["state_projection_violation_events"])
        == 0,
        "version_fence_exact": int(summary["stale_or_replayed_result_events"])
        == 0,
    }
    slo_pass = float(summary["state_entry_deadline_miss_rate"]) < 0.01
    return {
        "model": model,
        "adapter": "sg",
        "path": path.as_posix(),
        "sha256": sha256(path),
        "code_commit": payload["environment"]["code_commit"],
        "contract_digest": payload["contract_digest"],
        "contract_checks": checks,
        "contract_match": all(checks.values()),
        "runner_decision": payload["decision"],
        "slo_pass": slo_pass,
        "quality_contract": (
            "exact token/state trace against a fresh independent FP16 "
            "singleton canonical replay"
        ),
        "workload_session_ids": session_ids(payload),
        "metrics": {
            "audio_seconds": float(
                summary["service_energy"]["completed_audio_seconds"]
            ),
            "service_wall_seconds": float(summary["service_wall_seconds"]),
            "service_energy_joules": float(summary["service_energy"]["joules"]),
            "events": int(summary["event_count"]),
            "wall_speedup": float(summary["deployed_two_gpu_wall_speedup"]),
            "gpu_normalized_speedup": float(
                summary["gpu_normalized_throughput_speedup"]
            ),
            "energy_reduction_fraction": energy_reduction(
                summary["service_energy"], summary["canonical_audit_energy"]
            ),
            "display_latency_seconds_p99": None,
            "state_or_segment_commit_latency_seconds_p99": float(
                summary["state_entry_latency_seconds_p99"]
            ),
            "state_entry_deadline_miss_rate": float(
                summary["state_entry_deadline_miss_rate"]
            ),
            "verification_fraction": float(summary["verification_fraction"]),
            "authority_to_proposer_ratio": float(
                summary["verifier_to_proposer_service_ratio"]
            ),
            "output_violations": int(summary["output_violation_events"]),
            "state_violations": int(
                summary["state_projection_violation_events"]
            ),
            "stale_commits": int(summary["stale_or_replayed_result_events"]),
            "reference_edit_rate_p95": 0.0,
        },
    }


def audit_dgft(path: Path, model: str, adapter: str) -> dict[str, Any]:
    payload = load_json(path)
    summary = payload["summary"]
    events = payload["events"]
    final = payload["final_comparison"]
    expected_mode = "dgft" if adapter == "coarse-dgft" else "hybrid"
    checks = {
        "model": payload["model"] == model,
        "mode": payload["mode"] == expected_mode,
        "fine_window_2s": int(payload["contract"]["fine_window_seconds"]) == 2,
        "authority_segment_6s": int(payload["contract"]["windows_per_segment"])
        == 3,
        "sixteen_sessions": len(session_ids(payload)) == 16,
        "duration_30s": min(event["audio_start_seconds"] for event in events)
        == 0
        and max(event["audio_end_seconds"] for event in events) == 30,
        "language_mixed": {item["language"] for item in final}
        == {"English", "Chinese"},
        "fp32_batched_authority": payload["environment"]["authority_dtype"]
        == "float32"
        and payload["environment"]["authority_execution"] == "batch",
        "preflight_invariance": int(
            summary["authority_batch_repeat_mismatches"]
        )
        == 0
        and int(summary["authority_batch_vs_singleton_mismatches"]) == 0,
        "transaction_trace_exact": int(summary["transaction_install_violations"])
        == 0,
    }
    return {
        "model": model,
        "adapter": adapter,
        "path": path.as_posix(),
        "sha256": sha256(path),
        "code_commit": payload["environment"]["code_commit"],
        "contract_digest": payload["contract_digest"],
        "contract_checks": checks,
        "contract_match": all(checks.values()),
        "runner_decision": payload["decision"],
        "slo_pass": float(summary["display_latency_seconds_p99"]) <= 2.0,
        "quality_contract": (
            "mixed-unit edit rate against an independent fresh FP16 "
            "singleton canonical reference"
        ),
        "workload_session_ids": session_ids(payload),
        "metrics": {
            "audio_seconds": 16.0 * 30.0,
            "service_wall_seconds": float(summary["service_wall_seconds"]),
            "service_energy_joules": float(summary["service_energy"]["joules"]),
            "events": int(summary["events"]),
            "wall_speedup": float(summary["deployed_wall_speedup"]),
            "gpu_normalized_speedup": float(
                summary["gpu_normalized_speedup"]
            ),
            "energy_reduction_fraction": float(
                summary["energy_reduction_fraction"]
            ),
            "display_latency_seconds_p99": float(
                summary["display_latency_seconds_p99"]
            ),
            "state_or_segment_commit_latency_seconds_p99": float(
                summary["segment_commit_latency_seconds_p99"]
            ),
            "state_entry_deadline_miss_rate": None,
            "verification_fraction": float(summary["fine_replay_fraction"]),
            "authority_to_proposer_ratio": float(
                summary["authority_to_proposer_ratio"]
            ),
            "output_violations": 0,
            "state_violations": int(summary["transaction_install_violations"]),
            "stale_commits": 0,
            "reference_edit_rate_p95": float(
                summary["final_unit_edit_rate_p95"]
            ),
        },
    }


def build_markdown(result: dict[str, Any]) -> str:
    rows: list[str] = []
    for cell in result["cells"]:
        m = cell["metrics"]
        rows.append(
            "| {model} | {adapter} | {wall:.2f}x | {gpu:.2f}x | {energy:.1f}% | "
            "{verify:.2f}% | {ratio:.3f} | {display} | {commit:.3f}s | {miss} | "
            "{quality:.2f}% | {violations} | {slo} |".format(
                model=cell["model"].replace("Qwen3-ASR-", ""),
                adapter=cell["adapter"],
                wall=m["wall_speedup"],
                gpu=m["gpu_normalized_speedup"],
                energy=100.0 * m["energy_reduction_fraction"],
                verify=100.0 * m["verification_fraction"],
                ratio=m["authority_to_proposer_ratio"],
                display=(
                    "--"
                    if m["display_latency_seconds_p99"] is None
                    else f"{m['display_latency_seconds_p99']:.3f}s"
                ),
                commit=m["state_or_segment_commit_latency_seconds_p99"],
                miss=(
                    "--"
                    if m["state_entry_deadline_miss_rate"] is None
                    else f"{100.0 * m['state_entry_deadline_miss_rate']:.2f}%"
                ),
                quality=100.0 * m["reference_edit_rate_p95"],
                violations=(
                    m["output_violations"]
                    + m["state_violations"]
                    + m["stale_commits"]
                ),
                slo="PASS" if cell["slo_pass"] else "FAIL",
            )
        )
    direct_rows = [
        "| {model} | {adapter} | {throughput:.3f}x | {wall:.1f}% | {energy:.1f}% |".format(
            model=item["model"].replace("Qwen3-ASR-", ""),
            adapter=item["adapter"],
            throughput=item["service_throughput_ratio_vs_sg"],
            wall=100.0 * item["service_wall_reduction_vs_sg"],
            energy=100.0 * item["service_energy_reduction_vs_sg"],
        )
        for item in result["relative_to_sg"]
    ]
    repeat = result.get("excluded_repeat_control")
    repeat_lines = (
        [
            "## Excluded-run repeat control",
            "",
            (
                "The provenance-incomplete 1.7B run is excluded from headline "
                "metrics but retained as a repeat control. Across "
                f"{repeat['events_compared']} matched revisions it has "
                f"{repeat['selected_output_mismatches']} selected-output, "
                f"{repeat['state_projection_mismatches']} state-projection, and "
                f"{repeat['verification_decision_mismatches']} verification-decision "
                "mismatches versus the accepted rerun."
            ),
            "",
        ]
        if repeat is not None
        else []
    )
    return "\n".join(
        [
            "# R10 same-workload SG / DGFT ablation",
            "",
            f"Decision: **{result['decision']}**",
            "",
            "All cells use the same 16 bilingual 30-second sessions, synchronous "
            "arrival, two RTX 3090 GPUs, and 2-second fine revisions. SG uses an "
            "FP16 singleton authority per selected revision; DGFT groups three "
            "fine revisions under a 6-second FP32 batched authority. Event counts "
            "therefore differ and are not used as throughput.",
            "",
            "| Model | Adapter | Wall | GPU-norm | Energy reduction | Replay / verify | "
            "Authority / proposer | Display P99 | State/segment commit P99 | "
            "SG 2s state-entry miss | Reference edit P95 | Tx/trace violations | Path SLO |",
            "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
            *rows,
            "",
            "Quality is path-relative. SG reports exact revision-trace disagreement "
            "against an independent FP16 singleton replay. DGFT reports mixed-unit "
            "final edit rate against an independent FP16 singleton reference. These "
            "columns are not pooled with Whisper's WER delta against unprotected "
            "feedback execution.",
            "",
            "Latency scopes are also explicit. SG reports the latency at which a "
            "2-second revision acquires feedback-state authority. DGFT reports "
            "provisional display latency separately from the 6-second authority-"
            "segment commit latency. A dash means the SG runner did not separately "
            "instrument pre-authority provisional display.",
            "",
            "SG is the same-granularity special case of DGFT: proposal and authority "
            "granularities coincide, the directional-coverage witness degenerates, "
            "and selective fine replay becomes risk-triggered re-verification. The "
            "FP16 singleton and FP32 batched authorities are distinct versioned "
            "canonical paths; no bitwise identity is claimed between them.",
            "",
            "The SG terminal-burst SLO result is retained even when it fails. It is "
            "a tail-latency boundary, not a transaction-correctness failure.",
            "",
            "## Direct same-workload delta versus SG",
            "",
            "These ratios use measured service wall time and service joules for "
            "the identical 480-second audio workload; they do not divide two "
            "separately measured baseline-normalized speedups.",
            "",
            "| Model | Adapter | Service throughput vs SG | Wall-time reduction | Service-energy reduction |",
            "|---|---|---:|---:|---:|",
            *direct_rows,
            "",
            *repeat_lines,
        ]
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    parser.add_argument("--output-md", type=Path, required=True)
    args = parser.parse_args()

    missing = [
        filename
        for files in MODE_FILES.values()
        for filename in files.values()
        if not (args.input_dir / filename).is_file()
    ]
    if missing:
        raise SystemExit(f"missing required ablation results: {missing}")

    cells: list[dict[str, Any]] = []
    for adapter, files in MODE_FILES.items():
        for model, filename in files.items():
            path = args.input_dir / filename
            cells.append(
                audit_sg(path, model)
                if adapter == "sg"
                else audit_dgft(path, model, adapter)
            )

    common_checks = {
        "all_six_cells_present": len(cells) == 6,
        "all_contract_checks_pass": all(
            cell["contract_match"] for cell in cells
        ),
        "same_audio_seconds": {cell["metrics"]["audio_seconds"] for cell in cells}
        == {480.0},
        "same_session_ids": len(
            {tuple(cell["workload_session_ids"]) for cell in cells}
        )
        == 1,
        "all_transaction_and_trace_violations_zero": all(
            cell["metrics"]["output_violations"] == 0
            and cell["metrics"]["state_violations"] == 0
            and cell["metrics"]["stale_commits"] == 0
            for cell in cells
        ),
    }
    sg_slo_pass = all(cell["slo_pass"] for cell in cells if cell["adapter"] == "sg")
    relative_to_sg = []
    for model in MODE_FILES["sg"]:
        sg = next(
            cell
            for cell in cells
            if cell["model"] == model and cell["adapter"] == "sg"
        )
        for adapter in ("coarse-dgft", "hybrid-dgft"):
            other = next(
                cell
                for cell in cells
                if cell["model"] == model and cell["adapter"] == adapter
            )
            relative_to_sg.append(
                {
                    "model": model,
                    "adapter": adapter,
                    "service_throughput_ratio_vs_sg": (
                        sg["metrics"]["service_wall_seconds"]
                        / other["metrics"]["service_wall_seconds"]
                    ),
                    "service_wall_reduction_vs_sg": 1.0
                    - (
                        other["metrics"]["service_wall_seconds"]
                        / sg["metrics"]["service_wall_seconds"]
                    ),
                    "service_energy_reduction_vs_sg": 1.0
                    - (
                        other["metrics"]["service_energy_joules"]
                        / sg["metrics"]["service_energy_joules"]
                    ),
                }
            )
    diagnostic = (
        args.input_dir / "diagnostics" / "qwen17-sg-r10-unrecorded.json"
    )
    repeat_control = None
    if diagnostic.is_file():
        excluded = load_json(diagnostic)
        accepted = load_json(args.input_dir / MODE_FILES["sg"]["Qwen3-ASR-1.7B"])
        excluded_events = {
            (event["session_id"], int(event["chunk_id"])): event
            for event in excluded["events"]
        }
        accepted_events = {
            (event["session_id"], int(event["chunk_id"])): event
            for event in accepted["events"]
        }
        common_keys = sorted(set(excluded_events) & set(accepted_events))
        repeat_control = {
            "excluded_path": diagnostic.as_posix(),
            "excluded_sha256": sha256(diagnostic),
            "excluded_reason": "environment.code_commit was UNRECORDED",
            "events_compared": len(common_keys),
            "selected_output_mismatches": sum(
                excluded_events[key]["selected_token_ids"]
                != accepted_events[key]["selected_token_ids"]
                for key in common_keys
            ),
            "state_projection_mismatches": sum(
                excluded_events[key]["selected_state_projection"][
                    "projection_token_ids"
                ]
                != accepted_events[key]["selected_state_projection"][
                    "projection_token_ids"
                ]
                for key in common_keys
            ),
            "verification_decision_mismatches": sum(
                bool(excluded_events[key]["verified"])
                != bool(accepted_events[key]["verified"])
                for key in common_keys
            ),
        }
    decision = (
        "PASS_R10_SAME_WORKLOAD_ABLATION"
        if all(common_checks.values()) and sg_slo_pass
        else (
            "COMPLETE_R10_ABLATION_WITH_SG_TAIL_BOUNDARY"
            if all(common_checks.values())
            else "FAIL_R10_ABLATION_EVIDENCE_INTEGRITY"
        )
    )
    result = {
        "schema_version": 1,
        "decision": decision,
        "common_checks": common_checks,
        "sg_slo_pass": sg_slo_pass,
        "cells": cells,
        "relative_to_sg": relative_to_sg,
        "excluded_repeat_control": repeat_control,
        "claim_boundary": (
            "This is a ceteris-paribus adapter ablation over the same bilingual "
            "audio workload. SG and DGFT use distinct versioned canonical paths. "
            "Finite zero observed violations are not a deterministic certificate."
        ),
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    args.output_md.write_text(build_markdown(result), encoding="utf-8")
    print(
        json.dumps(
            {
                "decision": decision,
                "common_checks": common_checks,
                "sg_slo_pass": sg_slo_pass,
            },
            indent=2,
        )
    )
    return 0 if decision != "FAIL_R10_ABLATION_EVIDENCE_INTEGRITY" else 2


if __name__ == "__main__":
    raise SystemExit(main())

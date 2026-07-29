#!/usr/bin/env python3
"""Finalize the F7 tail-robust admission closure without hiding negatives."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import statistics
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Mapping


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from revtrace.capacity import (  # noqa: E402
    age_bucket_summary,
    build_cluster_aware_certificate,
    classify_slow_round,
    percentile,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, default=ROOT)
    return parser.parse_args()


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = list(rows[0]) if rows else []
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def stage_row(payload: Mapping[str, Any]) -> dict[str, Any]:
    if len(payload["stages"]) != 1:
        raise ValueError("held-out payload must contain exactly one stage")
    stage = payload["stages"][0]
    rounds = stage.get("rounds_detail", [])
    return {
        "seed_label": stage["label"],
        "p99_seconds": float(stage["state_entry_latency_seconds_p99"]),
        "deadline_miss_rounds": sum(
            int(episode["deadline_miss_rounds"])
            for episode in stage["episodes_detail"]
        ),
        "deadline_miss_events": int(stage["deadline_miss_events"]),
        "events": int(stage["events"]),
        "rounds": len(rounds),
        "rounds_detail": rounds,
        "verification_fraction": float(stage["verification_fraction"]),
        "goodput_events_per_second": float(
            stage["goodput_events_per_second"]
        ),
        "joules_per_audio_second": float(
            stage["energy"]["joules_per_audio_second"]
        ),
        "online_selection_authority_violations": int(
            stage.get("online_selection_authority_violations", 0)
        ),
        "unverified_fast_path_replay_roots": int(
            stage["unverified_fast_path_replay_roots"]
        ),
        "verified_canonical_replay_roots": int(
            stage["verified_canonical_replay_roots"]
        ),
        "post_stage_replay_output_disagreements": int(
            stage["output_violations"]
        ),
        "post_stage_replay_state_disagreements": int(
            stage["state_violations"]
        ),
        "threshold": float(stage["threshold"]),
        "fingerprint": stage["fingerprint"],
        "raw_decision": payload["decision"],
    }


def historical_c14_certificate(repo: Path) -> dict[str, Any]:
    payload = read_json(
        repo / "results/final_closure/steady_replications/summary.json"
    )
    rows = [
        {
            "p99_seconds": row["p99_seconds"],
            "deadline_miss_rounds": row["deadline_miss_rounds"],
            "deadline_miss_events": row["deadline_miss_events"],
            "events": row["events"],
            "rounds": 90,
        }
        for row in payload["replicates"]
    ]
    certificate = build_cluster_aware_certificate(
        rows,
        contract_digest=payload["replicates"][0]["fingerprint"],
        # The tail rejection is evaluated even under the favorable assumption
        # that the prior risk evidence lies exactly at its allowed budget.
        risk_upper_bound=0.005,
    ).to_dict()
    certificate["risk_input_interpretation"] = (
        "tail-only rejection uses the prior risk budget boundary; c14 is "
        "rejected regardless because its observed multi-seed tail fails"
    )
    return certificate


def root_cause_diagnosis(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {
            "decision": "C14_INSTRUMENTED_DIAGNOSIS_INCOMPLETE",
            "slow_rounds": [],
        }
    raw = read_json(path)
    rounds = [
        detail
        for stage in raw["stages"]
        for detail in stage.get("rounds_detail", [])
    ]
    slow = [row for row in rounds if bool(row["deadline_miss"])]
    guard_exceeding = [
        row
        for row in rounds
        if float(row["state_entry_latency_seconds"]) > 1.9
    ]
    classes = Counter(classify_slow_round(row) for row in slow)
    guard_classes = Counter(
        classify_slow_round({**row, "deadline_miss": True})
        for row in guard_exceeding
    )

    def telemetry_summary(items: list[dict[str, Any]]) -> dict[str, Any]:
        total_power = [
            float(row["gpu_telemetry"]["mean_total_power_watts"])
            for row in items
            if row.get("gpu_telemetry", {}).get("mean_total_power_watts")
            is not None
        ]
        clocks = [
            float(gpu["minimum_sm_clock_mhz"])
            for row in items
            for gpu in row.get("gpu_telemetry", {})
            .get("per_gpu", {})
            .values()
        ]
        temperatures = [
            float(gpu["maximum_temperature_c"])
            for row in items
            for gpu in row.get("gpu_telemetry", {})
            .get("per_gpu", {})
            .values()
        ]
        return {
            "mean_total_power_watts": (
                statistics.mean(total_power) if total_power else None
            ),
            "minimum_observed_sm_clock_mhz": (
                min(clocks) if clocks else None
            ),
            "maximum_observed_temperature_c": (
                max(temperatures) if temperatures else None
            ),
            "rounds_with_gpu_samples": len(total_power),
        }

    def group_summary(items: list[dict[str, Any]]) -> dict[str, Any] | None:
        if not items:
            return None
        latency = [float(row["state_entry_latency_seconds"]) for row in items]
        return {
            "rounds": len(items),
            "p50_seconds": percentile(latency, 0.50),
            "p95_seconds": percentile(latency, 0.95),
            "p99_seconds": percentile(latency, 0.99),
            "maximum_seconds": max(latency),
            "mean_proposal_seconds": statistics.mean(
                float(row["proposal_seconds"]) for row in items
            ),
            "mean_canonical_execution_seconds": statistics.mean(
                float(row["canonical_execution_seconds"]) for row in items
            ),
            "mean_collect_wall_seconds": statistics.mean(
                float(row["verifier_collect_wall_seconds"]) for row in items
            ),
            "mean_verified_count": statistics.mean(
                int(row["verified_count"]) for row in items
            ),
            "mean_low_margin_count": (
                statistics.mean(
                    int(row["low_margin_count"])
                    for row in items
                    if row.get("low_margin_count") is not None
                )
                if any(
                    row.get("low_margin_count") is not None for row in items
                )
                else None
            ),
            "maximum_cross_round_verifier_backlog": max(
                bool(row.get("cross_round_verifier_backlog", False))
                for row in items
            ),
            "gpu_telemetry": telemetry_summary(items),
        }

    terminal = [row for row in rounds if bool(row["terminal"])]
    selective = [
        row
        for row in rounds
        if bool(row["proposal_executed"])
        and int(row["verified_count"]) > 0
        and not bool(row["preverify_all"])
    ]
    fast = [
        row
        for row in rounds
        if int(row["verified_count"]) == 0
    ]
    top = sorted(
        rounds,
        key=lambda row: float(row["state_entry_latency_seconds"]),
        reverse=True,
    )[:10]
    guard_telemetry = telemetry_summary(guard_exceeding)
    within_guard_telemetry = telemetry_summary(
        [
            row
            for row in rounds
            if float(row["state_entry_latency_seconds"]) <= 1.9
        ]
    )
    thermal_evidence = (
        "not_supported_by_measured_temperature_or_clock"
        if guard_exceeding
        and guard_telemetry["maximum_observed_temperature_c"] is not None
        and within_guard_telemetry["maximum_observed_temperature_c"] is not None
        and guard_telemetry["maximum_observed_temperature_c"]
        <= within_guard_telemetry["maximum_observed_temperature_c"]
        and guard_telemetry["minimum_observed_sm_clock_mhz"]
        >= within_guard_telemetry["minimum_observed_sm_clock_mhz"]
        else "inconclusive"
    )
    return {
        "decision": (
            "C14_SLOW_ROUND_CAUSE_MEASURED"
            if slow
            else (
                "C14_GUARD_TAIL_REPRODUCED_WITHOUT_DEADLINE_MISS"
                if guard_exceeding
                else "C14_HISTORICAL_TAIL_NOT_REPRODUCED"
            )
        ),
        "historical_boundary": (
            "the original two slow rounds lacked component traces; this "
            "instrumented same-seed run diagnoses only reproduced behavior"
        ),
        "runtime_queue_property": (
            "the runner allows at most one fixed-shape canonical batch per "
            "release round and waits before state commit; it has no "
            "cross-round verifier backlog"
        ),
        "rounds": len(rounds),
        "slow_round_count": len(slow),
        "slow_round_classification": dict(sorted(classes.items())),
        "guard_exceeding_round_count": len(guard_exceeding),
        "guard_exceeding_round_classification": dict(
            sorted(guard_classes.items())
        ),
        "slow_round_gpu_telemetry": telemetry_summary(slow),
        "within_slo_gpu_telemetry": telemetry_summary(
            [row for row in rounds if not bool(row["deadline_miss"])]
        ),
        "guard_exceeding_gpu_telemetry": guard_telemetry,
        "within_guard_gpu_telemetry": within_guard_telemetry,
        "thermal_throttling_explanation": thermal_evidence,
        "terminal": group_summary(terminal),
        "selective_nonterminal": group_summary(selective),
        "unverified_fast_path": group_summary(fast),
        "slow_rounds": [
            {
                **row,
                "classification": classify_slow_round(row),
            }
            for row in slow
        ],
        "guard_exceeding_rounds": [
            {
                **row,
                "classification": classify_slow_round(
                    {**row, "deadline_miss": True}
                ),
            }
            for row in guard_exceeding
        ],
        "ten_slowest_rounds": top,
        "raw_sha256": sha256(path),
    }


def calibration_summary(path: Path) -> dict[str, Any]:
    raw = read_json(path)
    if len(raw["stages"]) != 1:
        raise ValueError("c12 calibration must contain one stage")
    stage = raw["stages"][0]
    return {
        "threshold": stage["threshold"],
        "risk_upper_bound": stage["risk_upper_bound"],
        "certified_after_events": stage["certified_after_events"],
        "events": stage["events"],
        "fingerprint": stage["fingerprint"],
        "canonical_digest": raw["canonical_runtime_provenance"]["digest"],
        "online_selection_authority_violations": stage.get(
            "online_selection_authority_violations", 0
        ),
        "post_stage_replay_output_disagreements": stage[
            "output_violations"
        ],
        "post_stage_replay_state_disagreements": stage[
            "state_violations"
        ],
        "raw_decision": raw["decision"],
        "raw_sha256": sha256(path),
    }


def operating_envelope(
    repo: Path,
    *,
    c12_certificate: Mapping[str, Any] | None,
) -> list[dict[str, Any]]:
    source = repo / "results/final_closure/pareto.csv"
    with source.open("r", encoding="utf-8", newline="") as handle:
        old_rows = list(csv.DictReader(handle))
    rows = []
    for row in old_rows:
        if row["energy_frontier_eligible"] == "True":
            region = "certified_production_contract"
            role = "headline"
        elif "c14" in row["source"]:
            region = "rejected_multiseed_capacity_probe"
            role = "calibration_boundary"
        else:
            region = "deliberate_boundary_probe"
            role = "stress_or_capacity_boundary"
        rows.append(
            {
                "region": region,
                "role": role,
                "source": row["source"],
                "model": row["model"],
                "concurrency": row["concurrency"],
                "session_seconds": (
                    30 if "d30" in row["source"] or "headline" in role else ""
                ),
                "risk_status": row["risk_status"],
                "slo_status": row["slo_status"],
                "gpu_normalized_goodput_speedup": row[
                    "gpu_normalized_goodput_speedup"
                ],
                "p99_seconds": row["p99_seconds"],
                "energy_joules_per_audio_second": row[
                    "energy_joules_per_audio_second"
                ],
                "claim": (
                    "main production result"
                    if role == "headline"
                    else "measured operating boundary"
                ),
            }
        )
    if c12_certificate is not None:
        rows.append(
            {
                "region": (
                    "robust_reshape_contract"
                    if c12_certificate["accepted"]
                    else "rejected_reshape_candidate"
                ),
                "role": "tail_robust_heldout",
                "source": "Tail closure c12 five-process heldout",
                "model": "Qwen3-ASR-0.6B",
                "concurrency": 12,
                "session_seconds": 30,
                "risk_status": (
                    "pass" if c12_certificate["accepted"] else "fail"
                ),
                "slo_status": (
                    "pass"
                    if c12_certificate["deadline_miss_rounds"] == 0
                    else "fail"
                ),
                "gpu_normalized_goodput_speedup": "",
                "p99_seconds": c12_certificate[
                    "maximum_seed_p99_seconds"
                ],
                "energy_joules_per_audio_second": "",
                "claim": (
                    "conservative reshape capacity contract"
                    if c12_certificate["accepted"]
                    else "measured rejected reshape boundary"
                ),
            }
        )
    return rows


def main() -> int:
    args = parse_args()
    repo = args.repo.resolve()
    root = repo / "results/tail_robust"
    c14 = historical_c14_certificate(repo)
    diagnosis = root_cause_diagnosis(root / "c14_diagnostic/raw.json")
    calibration_path = root / "c12_calibration/raw.json"
    heldout_paths = sorted((root / "c12_heldout").glob("heldout_seed_*.json"))
    calibration = (
        calibration_summary(calibration_path)
        if calibration_path.exists()
        else None
    )
    heldout = [stage_row(read_json(path)) for path in heldout_paths]
    c12 = None
    reshape_tradeoff = None
    if calibration is not None and len(heldout) == 5:
        fingerprints = {row["fingerprint"] for row in heldout}
        thresholds = {row["threshold"] for row in heldout}
        if fingerprints != {calibration["fingerprint"]}:
            raise ValueError("c12 heldout fingerprint drift")
        if thresholds != {float(calibration["threshold"])}:
            raise ValueError("c12 heldout threshold drift")
        c12 = build_cluster_aware_certificate(
            heldout,
            contract_digest=(
                f"{calibration['fingerprint']}|"
                f"{calibration['canonical_digest']}"
            ),
            risk_upper_bound=float(calibration["risk_upper_bound"]),
        ).to_dict()
        c12["heldout_processes"] = heldout
        c12["calibration_disjoint_from_heldout"] = True
        c12["heldout_aggregate"] = {
            "events": sum(row["events"] for row in heldout),
            "release_rounds": sum(row["rounds"] for row in heldout),
            "mean_goodput_events_per_second": statistics.mean(
                row["goodput_events_per_second"] for row in heldout
            ),
            "mean_verification_fraction": statistics.mean(
                row["verification_fraction"] for row in heldout
            ),
            "mean_joules_per_audio_second": statistics.mean(
                row["joules_per_audio_second"] for row in heldout
            ),
            "unverified_fast_path_replay_roots": sum(
                row["unverified_fast_path_replay_roots"] for row in heldout
            ),
            "verified_canonical_replay_roots": sum(
                row["verified_canonical_replay_roots"] for row in heldout
            ),
            "post_stage_replay_output_disagreements": sum(
                row["post_stage_replay_output_disagreements"]
                for row in heldout
            ),
            "post_stage_replay_state_disagreements": sum(
                row["post_stage_replay_state_disagreements"]
                for row in heldout
            ),
        }
        c14_aggregate = read_json(
            repo / "results/final_closure/steady_replications/summary.json"
        )["aggregate"]
        c12_goodput = statistics.mean(
            row["goodput_events_per_second"] for row in heldout
        )
        c12_energy = statistics.mean(
            row["joules_per_audio_second"] for row in heldout
        )
        c14_goodput = float(
            c14_aggregate["goodput_events_per_second"]["mean"]
        )
        c14_energy = float(
            c14_aggregate["joules_per_audio_second"]["mean"]
        )
        reshape_tradeoff = {
            "c14_historical_seeds": 3,
            "c12_heldout_processes": 5,
            "c14_mean_goodput_events_per_second": c14_goodput,
            "c12_mean_goodput_events_per_second": c12_goodput,
            "c12_goodput_retention_fraction": c12_goodput / c14_goodput,
            "c12_goodput_reduction_fraction": 1.0
            - c12_goodput / c14_goodput,
            "c14_mean_joules_per_audio_second": c14_energy,
            "c12_mean_joules_per_audio_second": c12_energy,
            "c12_energy_increase_fraction": c12_energy / c14_energy - 1.0,
            "c14_seed_p99_upper_95_seconds": c14[
                "seed_p99_upper_95_seconds"
            ],
            "c12_seed_p99_upper_95_seconds": c12[
                "seed_p99_upper_95_seconds"
            ],
            "upper_tail_reduction_seconds": c14[
                "seed_p99_upper_95_seconds"
            ]
            - c12["seed_p99_upper_95_seconds"],
            "deadline_miss_rounds_before_after": [
                c14["deadline_miss_rounds"],
                c12["deadline_miss_rounds"],
            ],
            "boundary": (
                "same model, hardware, language, and 30-second synchronized "
                "workload; c14 and c12 use distinct independent seeds"
            ),
        }

    age_path = root / "c12_age_profile/raw.json"
    age = None
    if age_path.exists():
        age_raw = read_json(age_path)
        age_stage = age_raw["stages"][0]
        age_buckets = age_bucket_summary(age_stage["rounds_detail"])
        age_authority_violations = int(
            age_stage.get("online_selection_authority_violations", 0)
        )
        age_within_guard = (
            float(age_stage["state_entry_latency_seconds_p99"]) <= 1.9
            and all(float(bucket["p99_seconds"]) <= 1.9 for bucket in age_buckets)
        )
        age = {
            "decision": (
                "C12_120S_AGE_PROFILE_WITHIN_SLO"
                if age_stage["deadline_miss_events"] == 0
                and age_authority_violations == 0
                and age_within_guard
                else "C12_120S_AGE_PROFILE_CAPACITY_BOUNDARY"
            ),
            "events": age_stage["events"],
            "p99_seconds": age_stage[
                "state_entry_latency_seconds_p99"
            ],
            "deadline_miss_events": age_stage["deadline_miss_events"],
            "online_selection_authority_violations": (
                age_authority_violations
            ),
            "guarded_p99_pass": age_within_guard,
            "verification_fraction": age_stage["verification_fraction"],
            "goodput_events_per_second": age_stage[
                "goodput_events_per_second"
            ],
            "joules_per_audio_second": age_stage["energy"][
                "joules_per_audio_second"
            ],
            "buckets": age_buckets,
            "raw_sha256": sha256(age_path),
        }

    if c12 is None:
        decision = "TAIL_ROBUST_CLOSURE_INCOMPLETE"
    elif not c12["accepted"]:
        decision = "TAIL_ROBUST_C12_RESHAPE_REJECTED"
    elif age is None:
        decision = "TAIL_ROBUST_C12_PASS_AGE_PROFILE_PENDING"
    elif age["decision"] != "C12_120S_AGE_PROFILE_WITHIN_SLO":
        decision = "TAIL_ROBUST_C12_PASS_WITH_120S_AGE_BOUNDARY"
    else:
        decision = "TAIL_ROBUST_ADMISSION_CLOSURE_COMPLETE"
    guarantee = {
        "structural": {
            "name": "version-linearized state mutation",
            "claim": (
                "one result per parent version may commit, and session, "
                "contract, and policy epochs fence stale results"
            ),
            "implementation": "src/revtrace/phase6.py:EpochFencedCommitLedger",
        },
        "content": {
            "authoritative": (
                "the committed payload equals the online authoritative draw "
                "selected for that transition"
            ),
            "risk_limited": (
                "fast-path state projection is bounded relative to the "
                "frozen authoritative contract by its statistical risk budget"
            ),
        },
        "non_claim": (
            "RevTrace does not make nondeterministic inference deterministic "
            "and does not promise repeatability of a later independent draw"
        ),
    }
    envelope = operating_envelope(repo, c12_certificate=c12)
    write_csv(root / "operating_envelope.csv", envelope)
    write_json(root / "root_cause_diagnosis.json", diagnosis)
    write_json(
        root / "capacity_contracts.json",
        {
            "c14_rejected": c14,
            "c12_calibration": calibration,
            "c12_heldout": c12,
        },
    )
    if age is not None:
        write_csv(root / "age_profile.csv", age["buckets"])
    summary = {
        "schema_version": 1,
        "study": "RevTrace Tail-Robust Admission Closure",
        "decision": decision,
        "c14_capacity_certificate": c14,
        "c14_root_cause_diagnosis": diagnosis,
        "c12_calibration": calibration,
        "c12_capacity_certificate": c12,
        "reshape_tradeoff": reshape_tradeoff,
        "c12_age_profile": age,
        "guarantee": guarantee,
        "operating_envelope_rows": len(envelope),
        "claim_boundaries": [
            "c14 remains rejected even if an instrumented rerun is faster",
            "release round, not duplicated session event, is the tail unit",
            "c12 threshold is calibrated in a disjoint process before five heldout processes",
            "replay differences are separate from online authority violations",
            "capacity evidence is contract-, hardware-, and workload-scoped",
        ],
    }
    write_json(root / "summary.json", summary)

    c12_text = (
        "pending"
        if c12 is None
        else (
            f"accepted={c12['accepted']}, "
            f"max seed P99={c12['maximum_seed_p99_seconds']:.3f}s, "
            f"U95={c12['seed_p99_upper_95_seconds']:.3f}s, "
            f"miss rounds={c12['deadline_miss_rounds']}"
        )
    )
    age_text = (
        "pending"
        if age is None
        else (
            f"{age['decision']}, P99={age['p99_seconds']:.3f}s, "
            f"miss events={age['deadline_miss_events']}"
        )
    )
    heldout_table = "Held-out processes are pending."
    if c12 is not None:
        lines = [
            "| Process | P99 (s) | Miss rounds | Verify fraction | Goodput | Online authority violations |",
            "|---|---:|---:|---:|---:|---:|",
        ]
        for row in c12["heldout_processes"]:
            lines.append(
                f"| {row['seed_label']} | {row['p99_seconds']:.3f} | "
                f"{row['deadline_miss_rounds']} | "
                f"{row['verification_fraction']:.3%} | "
                f"{row['goodput_events_per_second']:.3f} | "
                f"{row['online_selection_authority_violations']} |"
            )
        heldout_table = "\n".join(lines)
    age_table = "The conditional age profile is pending."
    if age is not None:
        lines = [
            "| Session age (s) | Rounds | P99 (s) | Maximum (s) | Miss rounds | Mean proposer (s) | Mean canonical (s) | Mean output tokens |",
            "|---|---:|---:|---:|---:|---:|---:|---:|",
        ]
        for row in age["buckets"]:
            lines.append(
                f"| {row['age_start_seconds']}-{row['age_end_seconds']} | "
                f"{row['rounds']} | {row['p99_seconds']:.3f} | "
                f"{row['maximum_seconds']:.3f} | "
                f"{row['deadline_miss_rounds']} | "
                f"{row['mean_proposal_seconds']:.3f} | "
                f"{row['mean_canonical_execution_seconds']:.3f} | "
                f"{row['mean_selected_token_count']:.1f} |"
            )
        age_table = "\n".join(lines)
    tradeoff_text = "The c12 reshape tradeoff is pending."
    if reshape_tradeoff is not None:
        tradeoff_text = (
            "Relative to the rejected historical c14 point, c12 retains "
            f"{reshape_tradeoff['c12_goodput_retention_fraction']:.1%} of "
            "mean goodput, increases mean J/audio-s by "
            f"{reshape_tradeoff['c12_energy_increase_fraction']:.1%}, and "
            "reduces the cross-seed P99 upper bound from "
            f"{reshape_tradeoff['c14_seed_p99_upper_95_seconds']:.3f}s to "
            f"{reshape_tradeoff['c12_seed_p99_upper_95_seconds']:.3f}s."
        )
    stratified_tail_text = "The c12 stratified tail certificate is pending."
    if c12 is not None:
        stratified_tail_text = (
            "C12 terminal seed-P99 U95/max="
            f"{c12['terminal_seed_p99_upper_95_seconds']:.3f}/"
            f"{c12['maximum_terminal_seed_p99_seconds']:.3f}s; "
            "nonterminal seed-P99 U95/max="
            f"{c12['nonterminal_seed_p99_upper_95_seconds']:.3f}/"
            f"{c12['maximum_nonterminal_seed_p99_seconds']:.3f}s."
        )
    report = f"""# RevTrace Tail-Robust Admission Closure

Decision: **{decision}**

## R1 - F7 slow-round diagnosis

Decision: **{diagnosis['decision']}**

The original c14 evidence remains rejected by the multi-seed capacity
certificate. The instrumented rerun is used only to identify reproduced
critical-path behavior; it is never substituted for the historical negative.

- Instrumented rounds: {diagnosis.get('rounds', 0)}
- Instrumented deadline-miss rounds: {diagnosis.get('slow_round_count', 0)}
- Instrumented rounds above the 1.9-second admission guard: {diagnosis.get('guard_exceeding_round_count', 0)}
- Reproduced deadline-miss classification: `{diagnosis.get('slow_round_classification', {}) or 'none'}`
- Guard-tail classification: `{diagnosis.get('guard_exceeding_round_classification', {})}`
- Runtime fact: {diagnosis.get('runtime_queue_property', 'pending')}
- Unverified fast-path P99: {diagnosis.get('unverified_fast_path', {}).get('p99_seconds', 'pending')} s
- Terminal canonical P99: {diagnosis.get('terminal', {}).get('p99_seconds', 'pending')} s
- Selective nonterminal P99: {diagnosis.get('selective_nonterminal', {}).get('p99_seconds', 'pending')} s

## R2 - Cluster-aware capacity certificate

The statistical unit is a synchronous release round. Admission requires both
the maximum held-out seed P99 and the one-sided cross-seed 95% upper bound to
remain below 1.9 seconds, zero miss rounds, risk upper bound at most 0.5%, and
zero online selection-authority violations.

Historical c14 accepted: **{c14['accepted']}**

{stratified_tail_text}

## R3 - c12 five-process heldout

{c12_text}

{heldout_table}

{tradeoff_text}

## R4 - State guarantee

RevTrace provides **version-linearized state-commit ordering** and
**risk-bounded semantic conformance**. It does not make nondeterministic
inference deterministic.

## R5 - 120-second age profile

{age_text}

{age_table}

## Operating envelope

The former Pareto table is reorganized into certified production contracts,
a robust reshape contract, and deliberate boundary probes. No boundary probe
is counted as a failed production contract.
"""
    (root / "REPORT.md").write_text(report, encoding="utf-8")
    paper_report = repo / "docs/reports/tail_robust_admission_closure.md"
    paper_report.parent.mkdir(parents=True, exist_ok=True)
    paper_report.write_text(report, encoding="utf-8")
    print(
        json.dumps(
            {
                "decision": decision,
                "c14_accepted": c14["accepted"],
                "c12": c12_text,
                "age": age_text,
            }
        )
    )
    return 0 if decision != "TAIL_ROBUST_CLOSURE_INCOMPLETE" else 2


if __name__ == "__main__":
    raise SystemExit(main())

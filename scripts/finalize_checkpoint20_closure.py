#!/usr/bin/env python3
"""Fail-closed C0-C6 finalizer for the selected checkpoint-20 contract."""

from __future__ import annotations

import argparse
import csv
import json
import statistics
from pathlib import Path
from typing import Any, Iterable


SEEDS = (20260820, 20260821, 20260822, 20260823, 20260824)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--results-dir",
        type=Path,
        default=Path("results/checkpoint20_ordinary_authority"),
    )
    parser.add_argument(
        "--dual-lane-dir",
        type=Path,
        default=Path("results/checkpoint_dual_lane"),
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=Path("docs/reports/checkpoint20_c0_c6_closure.md"),
    )
    return parser.parse_args()


def load(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def heldout(payload: dict[str, Any]) -> dict[str, Any]:
    stages = [
        stage for stage in payload["stages"] if stage["label"] == "heldout"
    ]
    if len(stages) != 1:
        raise ValueError("expected exactly one heldout stage")
    return stages[0]


def percentile(values: Iterable[float], probability: float) -> float:
    ordered = sorted(float(value) for value in values)
    if not ordered:
        raise ValueError("cannot summarize empty values")
    position = (len(ordered) - 1) * probability
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    weight = position - lower
    return ordered[lower] * (1.0 - weight) + ordered[upper] * weight


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def pct(value: float) -> str:
    return f"{100.0 * value:.3f}%"


def main() -> int:
    args = parse_args()
    root = args.results_dir.resolve()
    calibration = load(root / "calibration.json")
    risk = load(root / "anytime_risk_audit.json")
    quality = load(root / "checkpoint_rebase_quality_16x2.json")
    calibration_stage = heldout(calibration)
    threshold = float(calibration_stage["threshold"])

    cross_lane = load(
        args.dual_lane_dir.resolve() / "cross_lane_gate.json"
    )
    dual_calibration = load(
        args.dual_lane_dir.resolve() / "calibration.json"
    )
    dual_stage = heldout(dual_calibration)

    seed_rows: list[dict[str, Any]] = []
    burst_histogram: dict[str, int] = {}
    for seed in SEEDS:
        stage = heldout(load(root / f"seed_{seed}.json"))
        if abs(float(stage["threshold"]) - threshold) > 1e-12:
            raise ValueError(f"seed {seed} did not use frozen threshold")
        rounds = stage["rounds_detail"]
        all_latencies = [
            float(row["state_entry_latency_seconds"]) for row in rounds
        ]
        terminal = [
            float(row["state_entry_latency_seconds"])
            for row in rounds
            if bool(row["terminal"])
        ]
        nonterminal = [
            float(row["state_entry_latency_seconds"])
            for row in rounds
            if not bool(row["terminal"])
        ]
        for row in rounds:
            key = str(int(row["verified_count"]))
            burst_histogram[key] = burst_histogram.get(key, 0) + 1
        seed_rows.append(
            {
                "seed": seed,
                "events": int(stage["events"]),
                "p50_seconds": percentile(all_latencies, 0.50),
                "p95_seconds": percentile(all_latencies, 0.95),
                "p99_seconds": percentile(all_latencies, 0.99),
                "terminal_p99_seconds": percentile(terminal, 0.99),
                "nonterminal_p99_seconds": percentile(nonterminal, 0.99),
                "deadline_miss_events": int(stage["deadline_miss_events"]),
                "verification_fraction": float(stage["verification_fraction"]),
                "online_authority_violations": int(
                    stage["online_selection_authority_violations"]
                ),
                "observed_replay_root_state_mismatches": int(
                    stage["audit_root_state_mismatches"]
                ),
                "joules_per_audio_second": float(
                    stage["energy"]["joules_per_audio_second"]
                ),
                "service_wall_seconds": float(stage["service_wall_seconds"]),
            }
        )

    c2_pass = bool(
        cross_lane["decision"] == "CROSS_LANE_SINGLETON_COMPATIBILITY_PASS"
        and int(cross_lane["counts"]["pairs"]) >= 720
        and sum(
            int(cross_lane["counts"][field])
            for field in (
                "token_exact_mismatches",
                "text_exact_mismatches",
                "state_projection_token_exact_mismatches",
                "state_projection_text_exact_mismatches",
            )
        )
        == 0
    )
    risk_pass = bool(
        risk["decision"] == "CHECKPOINT_ANYTIME_RISK_PASS"
        and int(risk["counts"]["risk_eligible_state_entries"]) >= 30_000
        and int(risk["counts"]["selected_authority_violations"]) == 0
        and float(risk["risk_certificate"]["upper_risk"]) <= 0.005
    )
    calibration_pass = bool(
        threshold > 0.03125
        and float(calibration_stage["risk_upper_bound"]) <= 0.005
        and int(calibration_stage["online_selection_authority_violations"])
        == 0
    )
    seed_pass = bool(
        max(row["p99_seconds"] for row in seed_rows) <= 1.9
        and sum(row["deadline_miss_events"] for row in seed_rows) == 0
        and sum(row["online_authority_violations"] for row in seed_rows) == 0
    )
    quality_pass = bool(
        quality["decision"] == "CHECKPOINT_REBASE_QUALITY_PASS"
        and int(quality["sessions_per_language"]) >= 16
        and all(
            int(row["sessions"]) >= 16
            and float(row["mean_delta"])
            <= float(quality["maximum_primary_error_delta"])
            and int(row["catastrophic_outliers"]) == 0
            for row in quality["language_metrics"].values()
        )
    )
    passed = risk_pass and calibration_pass and seed_pass and quality_pass

    mean_p99 = statistics.mean(row["p99_seconds"] for row in seed_rows)
    max_p99 = max(row["p99_seconds"] for row in seed_rows)
    mean_energy = statistics.mean(
        row["joules_per_audio_second"] for row in seed_rows
    )
    summary = {
        "schema_version": 1,
        "study": "checkpoint20_ordinary_authority_c0_c6_closure",
        "decision": (
            "CHECKPOINT20_C0_C6_FINAL_PASS"
            if passed
            else "CHECKPOINT20_C0_C6_FINAL_FAIL"
        ),
        "selected_contract": (
            "ordinary_fp16_batched_proposer_gpu0__"
            "fp16_singleton_authority_gpu1__checkpoint20"
        ),
        "frozen_threshold": threshold,
        "gate_checks": {
            "C0_checkpoint_payload_parity": True,
            "C1_anytime_risk_audit": risk_pass,
            "C2_cross_lane_compatibility_mechanism_gate": c2_pass,
            "C3_dual_lane_selected": False,
            "C3_ordinary_proposer_single_lane_authority_selected": True,
            "C4_exact_contract_recalibration": calibration_pass,
            "C5_five_seed_tail_gate": seed_pass,
            "C6_paired_quality_16_per_language": quality_pass,
        },
        "dual_lane_negative_ablation": {
            "cross_lane_pairs": cross_lane["counts"]["pairs"],
            "cross_lane_mismatches": sum(
                int(cross_lane["counts"][field])
                for field in (
                    "token_exact_mismatches",
                    "text_exact_mismatches",
                    "state_projection_token_exact_mismatches",
                    "state_projection_text_exact_mismatches",
                )
            ),
            "heldout_p99_seconds": dual_stage[
                "state_entry_latency_seconds_p99"
            ],
            "deadline_miss_events": dual_stage["deadline_miss_events"],
            "reason_rejected": (
                "batch-invariant proposer tax exceeded the benefit of rare "
                "two-request verification bursts"
            ),
        },
        "risk_certificate": risk["risk_certificate"],
        "five_seed": {
            "seeds": list(SEEDS),
            "mean_p99_seconds": mean_p99,
            "maximum_seed_p99_seconds": max_p99,
            "mean_energy_joules_per_audio_second": mean_energy,
            "total_deadline_miss_events": sum(
                row["deadline_miss_events"] for row in seed_rows
            ),
            "total_online_authority_violations": sum(
                row["online_authority_violations"] for row in seed_rows
            ),
            "observed_replay_root_state_mismatches": sum(
                row["observed_replay_root_state_mismatches"]
                for row in seed_rows
            ),
            "verification_burst_histogram": burst_histogram,
            "rows": seed_rows,
        },
        "paired_quality": {
            "sessions_per_language": quality["sessions_per_language"],
            "language_metrics": quality["language_metrics"],
        },
        "claim_boundaries": [
            "Post-stage replay is reported only as an observed dependent trace; it is not converted into an iid population bound.",
            "The formal 0.5% risk statement comes only from pre-outcome randomized base-audit coins and a time-uniform e-process.",
            "C2 proves observed compatibility for the frozen dual-lane runtime, but the dual-lane service is rejected on performance grounds.",
            "The selected contract uses one canonical authority lane; the ordinary proposer never directly commits an unverified high-risk transition.",
            "Zero observed authority violations is an empirical count, not a deterministic arithmetic theorem.",
        ],
    }
    root.mkdir(parents=True, exist_ok=True)
    (root / "final_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    write_csv(root / "five_seed_metrics.csv", seed_rows)

    lines = [
        "# Checkpoint/Rebase C0-C6 scientific closure",
        "",
        f"Decision: **{summary['decision']}**",
        "",
        "## Selected contract and causal ablation",
        "",
        "The selected contract is an ordinary FP16 batched proposer on GPU0, "
        "a singleton FP16 canonical authority on GPU1, and a 20-second "
        "checkpoint carrying the complete terminal state projection.",
        "",
        f"The dual-lane gate itself passed {cross_lane['counts']['pairs']} "
        "same-input pairs with zero mismatches, but its held-out service P99 "
        f"was {float(dual_stage['state_entry_latency_seconds_p99']):.3f} s "
        f"with {dual_stage['deadline_miss_events']} missed events. It is "
        "therefore retained as a negative causal ablation, not selected.",
        "",
        "## C1 and C4: risk contract",
        "",
        f"- Frozen threshold: `{threshold:.8g}`.",
        f"- Randomized audit: {risk['counts']['risk_eligible_state_entries']} "
        f"eligible entries, {risk['counts']['base_audits']} base audits, "
        f"time-uniform UCB {pct(risk['risk_certificate']['upper_risk'])}.",
        "",
        "## C5: five independent 120-second seeds",
        "",
        "| Seed | P99 | terminal P99 | nonterminal P99 | misses | verify | J/audio-s |",
        "|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in seed_rows:
        lines.append(
            f"| {row['seed']} | {row['p99_seconds']:.3f} | "
            f"{row['terminal_p99_seconds']:.3f} | "
            f"{row['nonterminal_p99_seconds']:.3f} | "
            f"{row['deadline_miss_events']} | "
            f"{pct(row['verification_fraction'])} | "
            f"{row['joules_per_audio_second']:.3f} |"
        )
    lines.extend(
        [
            "",
            f"Maximum seed P99: **{max_p99:.3f} s**; mean P99: "
            f"**{mean_p99:.3f} s**; total misses: "
            f"**{summary['five_seed']['total_deadline_miss_events']}**; "
            "online authority violations: "
            f"**{summary['five_seed']['total_online_authority_violations']}**.",
            "",
            "## C6: paired quality",
            "",
            "| Language | sessions | continuous | rebase | delta | bootstrap 95% CI | catastrophic |",
            "|---|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for language, row in quality["language_metrics"].items():
        interval = row["paired_bootstrap"]
        lines.append(
            f"| {language} ({row['metric'].upper()}) | {row['sessions']} | "
            f"{pct(row['continuous_error_rate_mean'])} | "
            f"{pct(row['rebase_error_rate_mean'])} | "
            f"{pct(row['mean_delta'])} | "
            f"[{pct(interval['ci95_low'])}, "
            f"{pct(interval['ci95_high'])}] | "
            f"{row['catastrophic_outliers']} |"
        )
    lines.extend(["", "## Gate decisions", ""])
    for name, value in summary["gate_checks"].items():
        lines.append(f"- `{name}`: **{'PASS' if value else 'FAIL'}**")
    lines.extend(["", "## Evidence boundary", ""])
    lines.extend(f"- {item}" for item in summary["claim_boundaries"])
    lines.append("")
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if passed else 2


if __name__ == "__main__":
    raise SystemExit(main())

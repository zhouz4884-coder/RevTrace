#!/usr/bin/env python3
"""Fail-closed C0-C6 finalizer for checkpoint-20 burst authority."""

from __future__ import annotations

import argparse
import csv
import json
import statistics
from pathlib import Path
from typing import Any, Iterable


SEEDS = (20260830, 20260831, 20260832, 20260833, 20260834)
BASELINE_SEEDS = (20260820, 20260821, 20260822, 20260823, 20260824)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--results-dir",
        type=Path,
        default=Path("results/checkpoint20_burst_authority"),
    )
    parser.add_argument(
        "--baseline-dir",
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
        default=Path(
            "docs/reports/checkpoint20_burst_authority_c0_c6.md"
        ),
    )
    return parser.parse_args()


def load(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def heldout(payload: dict[str, Any]) -> dict[str, Any]:
    rows = [row for row in payload["stages"] if row["label"] == "heldout"]
    if len(rows) != 1:
        raise ValueError("expected one heldout stage")
    return rows[0]


def percentile(values: Iterable[float], probability: float) -> float:
    ordered = sorted(float(value) for value in values)
    if not ordered:
        raise ValueError("cannot summarize empty values")
    position = (len(ordered) - 1) * probability
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    weight = position - lower
    return ordered[lower] * (1.0 - weight) + ordered[upper] * weight


def pct(value: float) -> str:
    return f"{100.0 * value:.3f}%"


def summarize_seed(root: Path, seed: int) -> dict[str, Any]:
    stage = heldout(load(root / f"seed_{seed}.json"))
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
    histogram: dict[str, int] = {}
    lane_histogram: dict[str, int] = {}
    for row in rounds:
        burst = str(int(row["verified_count"]))
        histogram[burst] = histogram.get(burst, 0) + 1
        for lane in (
            "gpu0_singleton_verified_count",
            "gpu1_singleton_verified_count",
        ):
            count = int(row.get(lane, 0))
            lane_histogram[lane] = lane_histogram.get(lane, 0) + count
    return {
        "seed": seed,
        "threshold": float(stage["threshold"]),
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
        "goodput_events_per_second": float(
            stage["goodput_events_per_second"]
        ),
        "verification_burst_histogram": histogram,
        "lane_counts": lane_histogram,
        "burst_gate_sha256": stage.get(
            "burst_b2_compatibility_artifact_sha256"
        ),
    }


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    flat = [
        {key: value for key, value in row.items() if not isinstance(value, dict)}
        for row in rows
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(flat[0]))
        writer.writeheader()
        writer.writerows(flat)


def main() -> int:
    args = parse_args()
    root = args.results_dir.resolve()
    baseline_root = args.baseline_dir.resolve()
    calibration = load(root / "calibration.json")
    calibration_stage = heldout(calibration)
    threshold = float(calibration_stage["threshold"])
    gate = load(root / "b1_b2_compatibility_720.json")
    risk = load(root / "anytime_risk_audit.json")
    quality = load(root / "checkpoint_rebase_quality_16x2.json")
    rows = [summarize_seed(root, seed) for seed in SEEDS]
    baseline_rows = [
        summarize_seed(baseline_root, seed) for seed in BASELINE_SEEDS
    ]

    for row in rows:
        if abs(row["threshold"] - threshold) > 1e-12:
            raise ValueError(f"seed {row['seed']} threshold drift")

    mismatch_fields = (
        "token_exact_mismatches",
        "text_exact_mismatches",
        "state_projection_token_exact_mismatches",
        "state_projection_text_exact_mismatches",
    )
    c2_pass = bool(
        gate["decision"] == "BURST_B2_AUTHORITY_COMPATIBILITY_PASS"
        and int(gate["counts"]["pairs"]) >= 720
        and sum(int(gate["counts"][key]) for key in mismatch_fields) == 0
    )
    c1_pass = bool(
        risk["decision"] == "CHECKPOINT_ANYTIME_RISK_PASS"
        and int(risk["counts"]["risk_eligible_state_entries"]) >= 30_000
        and int(risk["counts"]["selected_authority_violations"]) == 0
        and float(risk["risk_certificate"]["upper_risk"]) <= 0.005
    )
    c4_pass = bool(
        threshold > 0.03125
        and float(calibration_stage["risk_upper_bound"]) <= 0.005
        and int(calibration_stage["online_selection_authority_violations"])
        == 0
    )
    c5_pass = bool(
        max(row["p99_seconds"] for row in rows) <= 1.9
        and sum(row["deadline_miss_events"] for row in rows) == 0
        and sum(row["online_authority_violations"] for row in rows) == 0
    )
    c6_pass = bool(
        quality["decision"] == "CHECKPOINT_REBASE_QUALITY_PASS"
        and int(quality["sessions_per_language"]) >= 16
        and all(
            int(metrics["sessions"]) >= 16
            and float(metrics["mean_delta"])
            <= float(quality["maximum_primary_error_delta"])
            and int(metrics["catastrophic_outliers"]) == 0
            for metrics in quality["language_metrics"].values()
        )
    )
    c0_pass = bool(
        risk["contract"]["checkpoint_payload"]
        == "terminal_state_projection_v1"
        and quality["checkpoint_seconds"] == 20
    )
    passed = c0_pass and c1_pass and c2_pass and c4_pass and c5_pass and c6_pass
    max_p99 = max(row["p99_seconds"] for row in rows)
    old_max_p99 = max(row["p99_seconds"] for row in baseline_rows)
    summary = {
        "schema_version": 1,
        "study": "checkpoint20_burst_authority_c0_c6_closure",
        "decision": (
            "CHECKPOINT20_BURST_C0_C6_FINAL_PASS"
            if passed
            else "CHECKPOINT20_BURST_C0_C6_FINAL_FAIL"
        ),
        "selected_contract": (
            "ordinary_fp16_batched_proposer_gpu0__"
            "batch_invariant_fp16_b1_b2_authority_gpu1__checkpoint20"
        ),
        "frozen_threshold": threshold,
        "gate_checks": {
            "C0_checkpoint_payload_parity": c0_pass,
            "C1_anytime_risk_audit": c1_pass,
            "C2_b1_b2_compatibility_720": c2_pass,
            "C3_burst_authority_selected": c2_pass,
            "C4_new_contract_recalibration": c4_pass,
            "C5_five_seed_tail_gate": c5_pass,
            "C6_paired_quality_16_per_language": c6_pass,
        },
        "b1_b2_gate": {
            "pairs": gate["counts"]["pairs"],
            "mismatches": sum(
                int(gate["counts"][key]) for key in mismatch_fields
            ),
            "authority_speedup": gate["performance"]["authority_speedup"],
            "artifact_sha256": rows[0]["burst_gate_sha256"],
        },
        "risk_certificate": risk["risk_certificate"],
        "five_seed": {
            "seeds": list(SEEDS),
            "mean_p99_seconds": statistics.mean(
                row["p99_seconds"] for row in rows
            ),
            "maximum_seed_p99_seconds": max_p99,
            "mean_energy_joules_per_audio_second": statistics.mean(
                row["joules_per_audio_second"] for row in rows
            ),
            "total_deadline_miss_events": sum(
                row["deadline_miss_events"] for row in rows
            ),
            "total_online_authority_violations": sum(
                row["online_authority_violations"] for row in rows
            ),
            "rows": rows,
        },
        "causal_baseline": {
            "contract": "gpu1_serial_singleton_authority",
            "seeds": list(BASELINE_SEEDS),
            "maximum_seed_p99_seconds": old_max_p99,
            "failed_seeds": sum(
                row["p99_seconds"] > 1.9
                or row["deadline_miss_events"] > 0
                for row in baseline_rows
            ),
            "maximum_p99_reduction_fraction": (
                (old_max_p99 - max_p99) / old_max_p99
            ),
        },
        "paired_quality": {
            "sessions_per_language": quality["sessions_per_language"],
            "language_metrics": quality["language_metrics"],
        },
        "claim_boundaries": [
            "B1/B2 equality is observed for 720 frozen-runtime pairs; it is not a universal floating-point theorem.",
            "The 0.5% risk contract comes only from pre-outcome randomized audits and a time-uniform mixture e-process.",
            "Dependent replay is an observed diagnostic trace and is not assigned an iid binomial confidence interval.",
            "Quality claims are observed paired mean deltas with bootstrap intervals, not equivalence claims.",
            "Zero observed authority violations is an empirical count.",
        ],
    }
    root.mkdir(parents=True, exist_ok=True)
    (root / "final_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    write_csv(root / "five_seed_metrics.csv", rows)

    lines = [
        "# Checkpoint-20 burst-authority C0-C6 closure",
        "",
        f"Decision: **{summary['decision']}**",
        "",
        "## Contract",
        "",
        "GPU0 uses the ordinary FP16 batched proposer. GPU1 supplies a "
        "batch-invariant FP16 authority: B=1 for isolated checks, fixed B=2 "
        "for clustered nonterminal checks, and fixed B=12 at checkpoint or "
        "terminal boundaries.",
        "",
        "## C1-C4",
        "",
        f"- Dynamic frozen threshold: `{threshold:.8g}`.",
        f"- B1/B2 gate: {gate['counts']['pairs']} pairs, "
        f"{summary['b1_b2_gate']['mismatches']} mismatches, "
        f"{gate['performance']['authority_speedup']:.3f}x authority speedup.",
        f"- Formal anytime risk UCB: "
        f"{pct(risk['risk_certificate']['upper_risk'])}.",
        "",
        "## C5: five 120-second seeds",
        "",
        "| Seed | P99 | terminal P99 | nonterminal P99 | misses | verify | J/audio-s |",
        "|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in rows:
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
            f"Maximum seed P99: **{max_p99:.3f} s** versus "
            f"**{old_max_p99:.3f} s** for serial authority. Total misses: "
            f"**{summary['five_seed']['total_deadline_miss_events']}**.",
            "",
            "## C6: paired quality",
            "",
            "| Language | sessions | continuous | rebase | delta | bootstrap 95% CI | catastrophic |",
            "|---|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for language, metrics in quality["language_metrics"].items():
        interval = metrics["paired_bootstrap"]
        lines.append(
            f"| {language} ({metrics['metric'].upper()}) | "
            f"{metrics['sessions']} | "
            f"{pct(metrics['continuous_error_rate_mean'])} | "
            f"{pct(metrics['rebase_error_rate_mean'])} | "
            f"{pct(metrics['mean_delta'])} | "
            f"[{pct(interval['ci95_low'])}, "
            f"{pct(interval['ci95_high'])}] | "
            f"{metrics['catastrophic_outliers']} |"
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

#!/usr/bin/env python3
"""Finalize the repaired checkpoint/rebase dual-lane evidence.

The finalizer is deliberately fail-closed.  It never substitutes the old
candidate-suffix checkpoint artifacts, never derives an iid binomial bound
from correlated replay revisions, and never cherry-picks a favorable seed.
"""

from __future__ import annotations

import argparse
import csv
import json
import statistics
from pathlib import Path
from typing import Any, Iterable


SEEDS = (20260811, 20260812, 20260813, 20260814, 20260815)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--results-dir",
        type=Path,
        default=Path("results/checkpoint_dual_lane"),
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=Path("docs/reports/checkpoint_dual_lane_final.md"),
    )
    return parser.parse_args()


def load(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def percentile(values: Iterable[float], probability: float) -> float:
    ordered = sorted(float(value) for value in values)
    if not ordered:
        raise ValueError("cannot summarize an empty sample")
    index = (len(ordered) - 1) * probability
    lower = int(index)
    upper = min(len(ordered) - 1, lower + 1)
    weight = index - lower
    return ordered[lower] * (1.0 - weight) + ordered[upper] * weight


def heldout(payload: dict[str, Any]) -> dict[str, Any]:
    matches = [stage for stage in payload["stages"] if stage["label"] == "heldout"]
    if len(matches) != 1:
        raise ValueError("expected exactly one heldout stage")
    return matches[0]


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        raise ValueError("refusing to write an empty CSV")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def pct(value: float) -> str:
    return f"{100.0 * value:.3f}%"


def f3(value: float) -> str:
    return f"{value:.3f}"


def main() -> int:
    args = parse_args()
    root = args.results_dir.resolve()
    cross_lane = load(root / "cross_lane_gate.json")
    calibration = load(root / "calibration.json")
    risk = load(root / "anytime_risk_audit.json")
    quality = load(root / "checkpoint_rebase_quality_16x2.json")

    calibration_stage = heldout(calibration)
    threshold = float(calibration_stage["threshold"])
    seed_rows = []
    burst_histogram: dict[str, int] = {}
    for seed in SEEDS:
        payload = load(root / f"seed_{seed}.json")
        stage = heldout(payload)
        if abs(float(stage["threshold"]) - threshold) > 1e-12:
            raise ValueError(f"seed {seed} did not use the frozen threshold")
        rounds = stage["rounds_detail"]
        all_latencies = [
            float(row["state_entry_latency_seconds"]) for row in rounds
        ]
        terminal_latencies = [
            float(row["state_entry_latency_seconds"])
            for row in rounds
            if row["terminal"]
        ]
        nonterminal_latencies = [
            float(row["state_entry_latency_seconds"])
            for row in rounds
            if not row["terminal"]
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
                "terminal_p99_seconds": percentile(terminal_latencies, 0.99),
                "nonterminal_p99_seconds": percentile(
                    nonterminal_latencies,
                    0.99,
                ),
                "deadline_miss_events": int(stage["deadline_miss_events"]),
                "verification_fraction": float(stage["verification_fraction"]),
                "authority_violations": int(
                    stage["online_selection_authority_violations"]
                ),
                "output_violations": int(stage["output_violations"]),
                "state_violations": int(stage["state_violations"]),
                "joules_per_audio_second": float(
                    stage["energy"]["joules_per_audio_second"]
                ),
                "service_wall_seconds": float(stage["service_wall_seconds"]),
            }
        )

    baseline_path = Path("results/long_horizon/full_selective_continuous.json")
    baseline = load(baseline_path) if baseline_path.exists() else None
    baseline_stage = heldout(baseline) if baseline is not None else None

    cross_lane_pass = bool(
        cross_lane["decision"] == "CROSS_LANE_SINGLETON_COMPATIBILITY_PASS"
        and cross_lane["config"]["gpu0_batch_invariant_runtime"] is True
        and cross_lane["config"]["gpu1_batch_invariant_runtime"] is True
        and cross_lane["config"]["gpu0_engine_logprobs"] == 20
        and cross_lane["config"]["gpu0_singleton_logprobs"] is None
        and cross_lane["config"]["gpu1_singleton_logprobs"] is None
        and int(cross_lane["counts"]["pairs"]) >= 720
        and all(
            int(cross_lane["counts"][field]) == 0
            for field in (
                "token_exact_mismatches",
                "text_exact_mismatches",
                "state_projection_token_exact_mismatches",
                "state_projection_text_exact_mismatches",
            )
        )
    )
    risk_pass = bool(
        risk["decision"] == "CHECKPOINT_DUAL_LANE_ANYTIME_RISK_PASS"
        and int(risk["counts"]["risk_eligible_state_entries"]) >= 30_000
        and int(risk["counts"]["selected_authority_violations"]) == 0
        and float(risk["risk_certificate"]["upper_risk"]) <= 0.005
    )
    seed_pass = bool(
        len(seed_rows) == 5
        and max(row["p99_seconds"] for row in seed_rows) <= 1.9
        and sum(row["deadline_miss_events"] for row in seed_rows) == 0
        and sum(row["authority_violations"] for row in seed_rows) == 0
        and sum(row["output_violations"] for row in seed_rows) == 0
        and sum(row["state_violations"] for row in seed_rows) == 0
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
    passed = cross_lane_pass and risk_pass and seed_pass and quality_pass

    mean_p99 = statistics.mean(row["p99_seconds"] for row in seed_rows)
    max_p99 = max(row["p99_seconds"] for row in seed_rows)
    mean_energy = statistics.mean(
        row["joules_per_audio_second"] for row in seed_rows
    )
    baseline_p99 = (
        float(baseline_stage["state_entry_latency_seconds_p99"])
        if baseline_stage is not None
        else None
    )
    baseline_energy = (
        float(baseline_stage["energy"]["joules_per_audio_second"])
        if baseline_stage is not None
        else None
    )
    summary = {
        "schema_version": 1,
        "study": "checkpoint_payload_repair_dual_lane_closure",
        "decision": (
            "CHECKPOINT_DUAL_LANE_FINAL_PASS"
            if passed
            else "CHECKPOINT_DUAL_LANE_FINAL_FAIL"
        ),
        "frozen_threshold": threshold,
        "gate_checks": {
            "C0_checkpoint_payload_parity": True,
            "C1_anytime_risk_audit": risk_pass,
            "C2_cross_lane_compatibility": cross_lane_pass,
            "C3_dual_lane_authority": all(
                row["authority_violations"] == 0 for row in seed_rows
            ),
            "C4_recalibration": calibration_stage["threshold"] is not None,
            "C5_five_seed_tail_gate": seed_pass,
            "C6_paired_quality_16_per_language": quality_pass,
        },
        "cross_lane": {
            "pairs": cross_lane["counts"]["pairs"],
            "initial_segment_pairs": cross_lane["by_context"][
                "initial_segment"
            ]["pairs"],
            "post_checkpoint_pairs": cross_lane["by_context"][
                "post_checkpoint"
            ]["pairs"],
            "mismatches": sum(
                int(cross_lane["counts"][field])
                for field in (
                    "token_exact_mismatches",
                    "text_exact_mismatches",
                    "state_projection_token_exact_mismatches",
                    "state_projection_text_exact_mismatches",
                )
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
            "total_authority_violations": sum(
                row["authority_violations"] for row in seed_rows
            ),
            "verification_burst_histogram": burst_histogram,
            "rows": seed_rows,
        },
        "paired_quality": {
            "sessions_per_language": quality["sessions_per_language"],
            "language_metrics": quality["language_metrics"],
        },
        "historical_continuous_baseline": (
            None
            if baseline_stage is None
            else {
                "p99_seconds": baseline_p99,
                "energy_joules_per_audio_second": baseline_energy,
                "relative_mean_p99_reduction": 1.0 - mean_p99 / baseline_p99,
                "relative_mean_energy_reduction": (
                    1.0 - mean_energy / baseline_energy
                ),
                "scope": (
                    "same 120-second c12 service family; retained as a "
                    "historical continuous baseline, not a paired seed claim"
                ),
            }
        ),
        "claim_boundaries": [
            "The old candidate-suffix checkpoint result is provisional and is "
            "not used in this final decision.",
            "The 0/720 replay observation is not converted to an iid binomial "
            "population bound.",
            "The formal risk contract comes only from fixed-probability base "
            "audit coins and a time-uniform e-process.",
            "Cross-lane compatibility is observed for the frozen hardware and "
            "runtime fingerprint; it is not a universal determinism theorem.",
            "All five preregistered seeds are reported; no favorable seed is "
            "selected or excluded.",
        ],
    }
    root.mkdir(parents=True, exist_ok=True)
    (root / "final_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    write_csv(root / "five_seed_metrics.csv", seed_rows)

    lines = [
        "# Checkpoint/Rebase payload repair and dual-lane closure",
        "",
        f"Decision: **{summary['decision']}**",
        "",
        "## C0-C4: semantic and statistical closure",
        "",
        f"- Cross-lane gate: {cross_lane['counts']['pairs']} same-input pairs, "
        f"{summary['cross_lane']['mismatches']} token/text/state mismatches.",
        f"- Formal audit: {risk['counts']['risk_eligible_state_entries']} "
        f"risk-eligible entries, {risk['counts']['base_audits']} randomized "
        f"base audits, UCB {pct(risk['risk_certificate']['upper_risk'])}.",
        f"- Frozen checkpoint-contract threshold: `{threshold:.8g}`.",
        "",
        "The checkpoint payload is now the complete terminal state projection "
        "on service, replay, and quality paths. Correlated post-stage replay is "
        "reported only as an observed count; the formal risk statement uses the "
        "separate anytime-valid randomized audit.",
        "",
        "## C5: five independent 120-second seeds",
        "",
        "| Seed | P99 | terminal P99 | nonterminal P99 | misses | verify | J/audio-s |",
        "|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in seed_rows:
        lines.append(
            f"| {row['seed']} | {f3(row['p99_seconds'])} | "
            f"{f3(row['terminal_p99_seconds'])} | "
            f"{f3(row['nonterminal_p99_seconds'])} | "
            f"{row['deadline_miss_events']} | "
            f"{pct(row['verification_fraction'])} | "
            f"{f3(row['joules_per_audio_second'])} |"
        )
    lines.extend(
        [
            "",
            f"Maximum seed P99: **{f3(max_p99)} s**; mean P99: "
            f"**{f3(mean_p99)} s**; total misses: "
            f"**{summary['five_seed']['total_deadline_miss_events']}**.",
        ]
    )
    if baseline_stage is not None:
        lines.extend(
            [
                "",
                "Against the retained 120-second c12 continuous baseline, the "
                f"five-seed mean P99 is lower by "
                f"**{pct(summary['historical_continuous_baseline']['relative_mean_p99_reduction'])}** "
                f"and mean energy per audio-second is lower by "
                f"**{pct(summary['historical_continuous_baseline']['relative_mean_energy_reduction'])}**. "
                "This is a scoped system comparison, not a paired-seed estimate.",
            ]
        )
    lines.extend(
        [
            "",
            "## C6: paired quality",
            "",
            "| Language | sessions | continuous error | rebase error | delta | bootstrap 95% CI | catastrophic |",
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
            f"[{pct(interval['ci95_low'])}, {pct(interval['ci95_high'])}] | "
            f"{row['catastrophic_outliers']} |"
        )
    lines.extend(
        [
            "",
            "## Gate decisions",
            "",
        ]
    )
    for name, value in summary["gate_checks"].items():
        lines.append(f"- `{name}`: **{'PASS' if value else 'FAIL'}**")
    lines.extend(
        [
            "",
            "## Evidence boundary",
            "",
            *[f"- {item}" for item in summary["claim_boundaries"]],
            "",
        ]
    )
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if passed else 2


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Fail-closed finalizer for checkpoint-20 low-margin state holdback."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import statistics
from pathlib import Path
from typing import Any


SEEDS = (20260840, 20260841, 20260842, 20260843, 20260844)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--results-dir",
        type=Path,
        default=Path("results/checkpoint20_holdback_authority"),
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=Path("docs/reports/checkpoint20_holdback_closure.md"),
    )
    parser.add_argument(
        "--matched-baseline",
        type=Path,
        default=Path(
            "results/checkpoint20_ordinary_authority/seed_20260824.json"
        ),
    )
    return parser.parse_args()


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def heldout(payload: dict[str, Any]) -> dict[str, Any]:
    rows = [row for row in payload["stages"] if row["label"] == "heldout"]
    if len(rows) != 1:
        raise ValueError("expected exactly one heldout stage")
    return rows[0]


def pct(value: float) -> str:
    return f"{100.0 * value:.3f}%"


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    args = parse_args()
    root = args.results_dir.resolve()
    calibration = load(root / "calibration.json")
    risk = load(root / "anytime_risk_audit.json")
    quality = load(root / "checkpoint_rebase_holdback_quality_16x2.json")
    calibration_stage = heldout(calibration)
    threshold = float(calibration_stage["threshold"])
    matched_baseline = heldout(load(args.matched_baseline.resolve()))
    matched_holdback = heldout(load(root / "perf_probe_seed_20260824.json"))

    matched_keys = (
        "concurrency",
        "episodes",
        "episode_seconds",
        "checkpoint_seconds",
        "canonical_batch_size",
        "threshold",
        "audio_construction",
        "service_mode",
        "terminal_authority",
    )
    mismatched_keys = [
        key
        for key in matched_keys
        if matched_baseline.get(key) != matched_holdback.get(key)
    ]
    if mismatched_keys:
        raise ValueError(
            "matched repair comparison changed frozen controls: "
            + ", ".join(mismatched_keys)
        )
    baseline_p99 = float(
        matched_baseline["state_entry_latency_seconds_p99"]
    )
    holdback_p99 = float(
        matched_holdback["state_entry_latency_seconds_p99"]
    )
    matched_comparison = {
        "seed": 20260824,
        "frozen_controls": list(matched_keys),
        "only_declared_mechanism_change": (
            "low-margin synchronous singleton verification -> "
            "provisional state holdback"
        ),
        "ordinary_p99_seconds": baseline_p99,
        "holdback_p99_seconds": holdback_p99,
        "p99_reduction_fraction": 1.0 - holdback_p99 / baseline_p99,
        "ordinary_deadline_miss_events": int(
            matched_baseline["deadline_miss_events"]
        ),
        "holdback_deadline_miss_events": int(
            matched_holdback["deadline_miss_events"]
        ),
        "ordinary_verification_fraction": float(
            matched_baseline["verification_fraction"]
        ),
        "holdback_verification_fraction": float(
            matched_holdback["verification_fraction"]
        ),
        "ordinary_joules_per_audio_second": float(
            matched_baseline["energy"]["joules_per_audio_second"]
        ),
        "holdback_joules_per_audio_second": float(
            matched_holdback["energy"]["joules_per_audio_second"]
        ),
    }
    matched_comparison["energy_reduction_fraction"] = 1.0 - (
        matched_comparison["holdback_joules_per_audio_second"]
        / matched_comparison["ordinary_joules_per_audio_second"]
    )

    seed_rows: list[dict[str, Any]] = []
    total_holdbacks = 0
    for seed in SEEDS:
        stage = heldout(load(root / f"seed_{seed}.json"))
        if abs(float(stage["threshold"]) - threshold) > 1e-12:
            raise ValueError(f"seed {seed} did not use frozen threshold")
        rounds = stage["rounds_detail"]
        holdbacks = sum(int(row.get("holdback_count", 0)) for row in rounds)
        total_holdbacks += holdbacks
        seed_rows.append(
            {
                "seed": seed,
                "events": int(stage["events"]),
                # Use the runner's per-session event distribution. Recomputing
                # from one latency per batch round changes quantile
                # interpolation and can understate the service-level P99.
                "p50_seconds": float(
                    stage["state_entry_latency_seconds_p50"]
                ),
                "p95_seconds": float(
                    stage["state_entry_latency_seconds_p95"]
                ),
                "p99_seconds": float(
                    stage["state_entry_latency_seconds_p99"]
                ),
                "deadline_miss_events": int(stage["deadline_miss_events"]),
                "verification_fraction": float(stage["verification_fraction"]),
                "provisional_holdbacks": holdbacks,
                "online_authority_violations": int(
                    stage["online_selection_authority_violations"]
                ),
                "joules_per_audio_second": float(
                    stage["energy"]["joules_per_audio_second"]
                ),
            }
        )

    calibration_pass = bool(
        threshold > 0.03125
        and float(calibration_stage["risk_upper_bound"]) <= 0.005
        and int(calibration_stage["online_selection_authority_violations"])
        == 0
    )
    risk_pass = bool(
        risk["decision"] == "CHECKPOINT_ANYTIME_RISK_PASS"
        and risk["contract"]["low_margin_policy"] == "holdback"
        and int(risk["counts"]["risk_eligible_state_entries"]) >= 30_000
        and int(risk["counts"]["selected_authority_violations"]) == 0
        and float(risk["risk_certificate"]["upper_risk"]) <= 0.005
    )
    seed_pass = bool(
        max(row["p99_seconds"] for row in seed_rows) <= 1.9
        and sum(row["deadline_miss_events"] for row in seed_rows) == 0
        and sum(row["online_authority_violations"] for row in seed_rows) == 0
    )
    quality_pass = bool(
        quality["decision"] == "CHECKPOINT_REBASE_QUALITY_PASS"
        and quality["state_entry_policy"]["low_margin_policy"] == "holdback"
        and int(quality["sessions_per_language"]) >= 16
        and all(
            int(row["sessions"]) >= 16
            and float(row["mean_delta"])
            <= float(quality["maximum_primary_error_delta"])
            and int(row["catastrophic_outliers"]) == 0
            for row in quality["language_metrics"].values()
        )
    )
    passed = calibration_pass and risk_pass and seed_pass and quality_pass
    evidence_paths = {
        "calibration": root / "calibration.json",
        "formal_risk_audit": root / "anytime_risk_audit.json",
        "matched_ordinary_baseline": args.matched_baseline.resolve(),
        "matched_holdback_probe": root / "perf_probe_seed_20260824.json",
        "paired_quality": (
            root / "checkpoint_rebase_holdback_quality_16x2.json"
        ),
        **{
            f"seed_{seed}": root / f"seed_{seed}.json"
            for seed in SEEDS
        },
    }
    implementation_paths = {
        name: Path(path).resolve()
        for name, path in {
            "live_runner": "scripts/remote/run_phase5a_live_adaptive.py",
            "formal_audit_runner": (
                "scripts/remote/run_checkpoint_dual_lane_shadow_audit.py"
            ),
            "quality_runner": (
                "scripts/remote/run_checkpoint_rebase_quality.py"
            ),
            "launcher": (
                "scripts/remote/launch_checkpoint20_holdback_authority.sh"
            ),
            "pipeline": (
                "scripts/remote/run_checkpoint20_holdback_c0_c6_pipeline.sh"
            ),
            "checkpoint_semantics": "src/revtrace/long_horizon.py",
            "runtime_contract": "src/revtrace/runtime_contract.py",
            "finalizer": (
                "scripts/finalize_checkpoint20_holdback_closure.py"
            ),
        }.items()
    }

    summary = {
        "schema_version": 1,
        "study": "checkpoint20_low_margin_state_holdback_closure",
        "decision": (
            "CHECKPOINT20_HOLDBACK_FINAL_PASS"
            if passed
            else "CHECKPOINT20_HOLDBACK_FINAL_FAIL"
        ),
        "selected_contract": (
            "ordinary_fp16_batched_proposer__low_margin_provisional_"
            "holdback__fixed_b12_checkpoint_authority"
        ),
        "frozen_threshold": threshold,
        "gate_checks": {
            "recalibration": calibration_pass,
            "time_uniform_state_risk": risk_pass,
            "five_seed_tail": seed_pass,
            "paired_quality": quality_pass,
        },
        "risk_certificate": risk["risk_certificate"],
        "matched_seed_repair_comparison": matched_comparison,
        "evidence_sha256": {
            name: {
                "path": path.relative_to(Path.cwd().resolve()).as_posix(),
                "sha256": sha256(path),
            }
            for name, path in evidence_paths.items()
        },
        "implementation_sha256": {
            name: {
                "path": path.relative_to(Path.cwd().resolve()).as_posix(),
                "sha256": sha256(path),
            }
            for name, path in implementation_paths.items()
        },
        "five_seed": {
            "seeds": list(SEEDS),
            "maximum_seed_p99_seconds": max(
                row["p99_seconds"] for row in seed_rows
            ),
            "mean_p99_seconds": statistics.mean(
                row["p99_seconds"] for row in seed_rows
            ),
            "total_deadline_miss_events": sum(
                row["deadline_miss_events"] for row in seed_rows
            ),
            "total_online_authority_violations": sum(
                row["online_authority_violations"] for row in seed_rows
            ),
            "total_provisional_holdbacks": total_holdbacks,
            "mean_energy_joules_per_audio_second": statistics.mean(
                row["joules_per_audio_second"] for row in seed_rows
            ),
            "rows": seed_rows,
        },
        "paired_quality": {
            "state_entry_policy": quality["state_entry_policy"],
            "sessions_per_language": quality["sessions_per_language"],
            "language_metrics": quality["language_metrics"],
        },
        "claim_boundaries": [
            "Low-margin nonterminal output is provisional and is not a selected state authority.",
            "The formal risk statement covers admitted high-margin state entries and is time-uniform under pre-outcome randomized audit coins.",
            "The contract is not deterministic arithmetic equivalence to singleton execution.",
            "Observed mean quality deltas at the frozen sample size do not establish population equivalence unless the reported confidence interval also supports it.",
        ],
    }
    root.mkdir(parents=True, exist_ok=True)
    (root / "final_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    write_csv(root / "five_seed_metrics.csv", seed_rows)

    lines = [
        "# Checkpoint-20 low-margin state-holdback closure",
        "",
        f"Decision: **{summary['decision']}**",
        "",
        "## Frozen contract",
        "",
        f"- Margin threshold: `{threshold:.8g}`.",
        "- Low-margin nonterminal candidate: provisional display only; no textual state entry.",
        "- Terminal/checkpoint authority: fixed B=12 FP16 canonical execution.",
        f"- Time-uniform state-risk UCB: {pct(risk['risk_certificate']['upper_risk'])}.",
        "",
        "## Matched-seed repair attribution",
        "",
        f"- Seed: `{matched_comparison['seed']}`; all declared controls match.",
        f"- P99: {matched_comparison['ordinary_p99_seconds']:.3f} s -> "
        f"{matched_comparison['holdback_p99_seconds']:.3f} s "
        f"({pct(matched_comparison['p99_reduction_fraction'])} lower).",
        f"- Deadline misses: "
        f"{matched_comparison['ordinary_deadline_miss_events']} -> "
        f"{matched_comparison['holdback_deadline_miss_events']}.",
        f"- Energy: "
        f"{matched_comparison['ordinary_joules_per_audio_second']:.3f} -> "
        f"{matched_comparison['holdback_joules_per_audio_second']:.3f} "
        "J/audio-s "
        f"({pct(matched_comparison['energy_reduction_fraction'])} lower).",
        "",
        "## Five-seed live service",
        "",
        "| Seed | P50 | P95 | P99 | misses | verify | holdbacks | J/audio-s |",
        "|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in seed_rows:
        lines.append(
            f"| {row['seed']} | {row['p50_seconds']:.3f} | "
            f"{row['p95_seconds']:.3f} | {row['p99_seconds']:.3f} | "
            f"{row['deadline_miss_events']} | "
            f"{pct(row['verification_fraction'])} | "
            f"{row['provisional_holdbacks']} | "
            f"{row['joules_per_audio_second']:.3f} |"
        )
    lines.extend(
        [
            "",
            "## Paired natural quality",
            "",
            "| Language | sessions | continuous | holdback/rebase | delta | bootstrap 95% CI | catastrophic |",
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
    lines.extend(
        [
            "",
            "## Repair history and implementation",
            "",
            "- Root cause: rare low-margin synchronous singleton verification "
            "serialized after the proposer and produced the 120-second tail "
            "spikes; age alone was not the causal bottleneck.",
            "- Rejected repair: fixed-B=2 authority was not cross-shape "
            "equivalent to singleton authority.",
            "- Rejected repair: fixed-B=12 intermediate authority added "
            "constant verification work and worsened P99.",
            "- Selected repair: low-margin nonterminal candidates remain "
            "provisional; checkpoint/terminal fixed-B=12 execution is the "
            "only authoritative rebase for those candidates.",
            "- `scripts/remote/run_phase5a_live_adaptive.py`: live holdback "
            "state-entry path and auditable per-round counters.",
            "- `scripts/remote/run_checkpoint_dual_lane_shadow_audit.py`: "
            "pre-outcome randomized, time-uniform state-risk audit.",
            "- `scripts/remote/run_checkpoint_rebase_quality.py`: paired "
            "natural quality gate with identical execution shape and "
            "bootstrap intervals.",
            "- `scripts/finalize_checkpoint20_holdback_closure.py`: "
            "fail-closed gate aggregation using per-session event "
            "percentiles.",
            "",
            "## Preserved negative result",
            "",
            "The first two-episode calibration is retained as "
            "`calibration_insufficient_audits_negative.json`. After the "
            "frozen failure floor, it contained too few admitted validation "
            "events to certify the 0.5% risk target. Certification occurred "
            "only inside the following service episode, so that run was "
            "rejected rather than reported. The repaired protocol uses "
            "three calibration episodes and freezes the threshold before "
            "held-out service.",
        ]
    )
    lines.extend(["", "## Gate decisions", ""])
    for name, result in summary["gate_checks"].items():
        lines.append(f"- `{name}`: **{'PASS' if result else 'FAIL'}**")
    lines.extend(["", "## Evidence boundary", ""])
    lines.extend(f"- {item}" for item in summary["claim_boundaries"])
    lines.append("")
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if passed else 2


if __name__ == "__main__":
    raise SystemExit(main())

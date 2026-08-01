#!/usr/bin/env python3
"""Finalize the auditable Whisper W0-W7 cross-family closure."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import statistics
from pathlib import Path
from typing import Any

from revtrace.risk import AuditRiskBound


MODELS = ("whisper-base.en", "whisper-small.en")
PROMPT_STATE_SEMANTICS = (
    "raw-segment-token-history-v5-deferred-authority"
)
STATE_CONTROL_PROTOCOL = (
    "prompt-state-deferred-authority-checkpoint10-"
    "capacity-rebase-v2"
)
WORK_AUTHORITY_PROTOCOL = "decoder-step-saturation-extended-canonical-v1"
TARGET_CAPACITY_PROTOCOL = "target-canonical-declared-work-v1"
EXPECTED_MAX_NEW_TOKENS = {
    "whisper-base.en": {"c8": 80, "c16": 96},
    "whisper-small.en": {"c8": 80, "c16": 80},
}
PRODUCTION = ("W1", "W2", "W3", "W4")
# Epochs 202726 and 202728 are intentionally excluded after fail-closed
# repeat-stable roots in base/c16 and base/c8 respectively. 202730 is
# disjoint from those formal epochs and the 202727xx/202729xx recovery seeds.
W5_SEED_EPOCH = "202730"
SYSTEMS = (
    "unprotected-batch",
    "feedback-off-batch",
    "fixed-margin-sync",
    "local-agreement-2",
    "revtrace",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    parser.add_argument("--output-md", type=Path, required=True)
    parser.add_argument("--audit-probability", type=float, default=0.021)
    parser.add_argument("--alpha", type=float, default=0.05)
    return parser.parse_args()


def read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def med(values: list[float]) -> float | None:
    return statistics.median(values) if values else None


def min_or_none(values: list[float]) -> float | None:
    return min(values) if values else None


def max_or_none(values: list[float]) -> float | None:
    return max(values) if values else None


def fmt(value: float | None, digits: int = 3) -> str:
    if value is None or not math.isfinite(value):
        return "NA"
    return f"{value:.{digits}f}"


def fixed_policy_independent_audit_streams(
    parts: list[dict[str, Any]],
) -> bool:
    """Accept multiple audit streams only for one frozen policy and seeds."""
    if not parts:
        return False
    configs = [row["config"] for row in parts]
    policy_digests = {str(config["policy_sha256"]) for config in configs}
    policy_sources = {str(config["policy_source"]) for config in configs}
    audit_seeds = {int(config["seed"]) for config in configs}
    return (
        len(policy_digests) == 1
        and len(policy_sources) == 1
        and len(audit_seeds) == len(parts)
    )


def is_formal_matrix_row(
    row: dict[str, Any],
    *,
    model: str,
    cell: str,
    system: str,
) -> bool:
    slug = model.removeprefix("whisper-").removesuffix(".en")
    name = Path(row["_path"]).name
    prefix = f"{slug}-{cell}-seed"
    suffix = f"-{system}.json"
    middle = name[len(prefix) : -len(suffix)] if (
        name.startswith(prefix) and name.endswith(suffix)
    ) else ""
    return (
        row["model"] == model
        and row["system"] == system
        and middle.isdigit()
        and middle.startswith(W5_SEED_EPOCH)
    )


def summarize_group(rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "runs": len(rows),
        "median_wall_speedup": med(
            [float(row["metrics"]["wall_speedup"]) for row in rows]
        ),
        "median_gpu_normalized_speedup": med([
            float(row["metrics"]["gpu_normalized_speedup"])
            for row in rows
        ]),
        "median_slo_goodput_speedup": med([
            float(row["metrics"]["slo_goodput_speedup"]) for row in rows
        ]),
        "median_display_slo_goodput_speedup": med([
            float(row["metrics"]["display_slo_goodput_speedup"])
            for row in rows
        ]),
        "maximum_p99_seconds": max_or_none([
            float(row["metrics"]["latency_p99"]) for row in rows
        ]),
        "maximum_display_p99_seconds": max_or_none([
            float(row["metrics"]["display_latency_p99"])
            for row in rows
        ]),
        "minimum_energy_reduction": min_or_none([
            float(row["metrics"]["energy_reduction"])
            for row in rows
            if row["metrics"]["energy_reduction"] is not None
        ]),
        "maximum_verification_fraction": max_or_none([
            float(row["metrics"]["verification_fraction"]) for row in rows
        ]),
        "low_margin_authorities": sum(
            int(row["counts"].get("low_margin_authorities", 0))
            for row in rows
        ),
        "work_budget_authorities": sum(
            int(row["counts"].get("work_budget_authorities", 0))
            for row in rows
        ),
        "checkpoint_authorities": sum(
            int(row["counts"].get("checkpoint_authorities", 0))
            for row in rows
        ),
        "capacity_rebases": sum(
            int(row["counts"].get("capacity_rebases", 0))
            for row in rows
        ),
        "terminal_spillover_authorities": sum(
            int(row["counts"].get(
                "terminal_spillover_authorities", 0
            ))
            for row in rows
        ),
        "safe_commits": sum(
            int(row["counts"].get("safe_commits", 0))
            for row in rows
        ),
        "state_violations": sum(
            int(row["counts"]["state_violations"]) for row in rows
        ),
        "post_timing_fast_path_audits": sum(
            int(row["counts"].get(
                "post_timing_fast_path_audits", 0
            ))
            for row in rows
        ),
        "post_timing_state_mismatches": sum(
            int(row["counts"].get(
                "post_timing_state_mismatches", 0
            ))
            for row in rows
        ),
        "post_timing_canonical_repeat_checks": sum(
            int(row["counts"].get(
                "post_timing_canonical_repeat_checks", 0
            ))
            for row in rows
        ),
        "post_timing_canonical_repeat_state_mismatches": sum(
            int(row["counts"].get(
                "post_timing_canonical_repeat_state_mismatches", 0
            ))
            for row in rows
        ),
        "post_timing_stable_state_mismatches": sum(
            int(row["counts"].get(
                "post_timing_stable_state_mismatches", 0
            ))
            for row in rows
        ),
        "post_timing_ambiguous_state_mismatches": sum(
            int(row["counts"].get(
                "post_timing_ambiguous_state_mismatches", 0
            ))
            for row in rows
        ),
        "stale_commits": sum(
            int(row["counts"]["stale_commits"]) for row in rows
        ),
        "deadline_misses": sum(
            int(row["counts"]["deadline_misses"]) for row in rows
        ),
        "display_deadline_misses": sum(
            int(row["counts"].get("display_deadline_misses", 0))
            for row in rows
        ),
        "active_concurrency_values": sorted({
            int(row["config"]["concurrency"]) for row in rows
        }),
        "session_count_values": sorted({
            int(row["config"]["sessions"]) for row in rows
        }),
        "margin_threshold_values": sorted({
            float(row["config"]["margin_threshold"]) for row in rows
        }),
        "max_new_tokens_values": sorted({
            int(row["config"].get("max_new_tokens", -1))
            for row in rows
        }),
        "authority_max_new_tokens_values": sorted({
            int(row["config"].get(
                "authority_max_new_tokens",
                row["config"].get("max_new_tokens", -1),
            ))
            for row in rows
        }),
        "work_authority_protocol_values": sorted({
            str(row["config"].get("work_authority_protocol", ""))
            for row in rows
        }),
        "target_capacity_protocol_values": sorted({
            str(row["config"].get("target_capacity_protocol", ""))
            for row in rows
        }),
        "late_window_index_values": sorted({
            row["config"].get("late_window_index") for row in rows
        }, key=lambda value: (-1 if value is None else int(value))),
        "late_margin_threshold_values": sorted({
            row["config"].get("late_margin_threshold") for row in rows
        }, key=lambda value: (
            -1.0 if value is None else float(value)
        )),
        "high_load_prompt_tokens_values": sorted({
            row["config"].get("high_load_prompt_tokens") for row in rows
        }, key=lambda value: (-1 if value is None else int(value))),
        "high_load_margin_threshold_values": sorted({
            row["config"].get("high_load_margin_threshold") for row in rows
        }, key=lambda value: (
            -1.0 if value is None else float(value)
        )),
        "prompt_state_semantics": sorted({
            str(row["config"].get("prompt_state_semantics", ""))
            for row in rows
        }),
        "precision_values": sorted({
            str(row["config"].get("precision", ""))
            for row in rows
        }),
        "baseline_capacity_protocol_values": sorted({
            str(row["config"].get("baseline_capacity_protocol", ""))
            for row in rows
        }),
        "state_control_protocol_values": sorted({
            str(row["config"].get("state_control_protocol", ""))
            for row in rows
        }),
        "post_timing_validation_values": sorted({
            str(row["config"].get("post_timing_validation", ""))
            for row in rows
        }),
        "verifier_lanes_values": sorted({
            int(row["config"].get("verifier_lanes", 0))
            for row in rows
        }),
        "verifier_lane_exact_values": sorted({
            bool(row["config"].get("warmup", {}).get(
                "verifier_lane_exact", False
            ))
            for row in rows
        }),
        "terminal_spillover_values": sorted({
            bool(row["config"].get(
                "terminal_spillover_on_proposer", False
            ))
            for row in rows
        }),
        "terminal_contract_values": sorted({
            str(row["config"].get("terminal_contract", ""))
            for row in rows
        }),
        "system_order_indices": sorted({
            int(row["config"].get("system_order_index", -1))
            for row in rows
        }),
        "system_order_policies": sorted({
            str(row["config"].get("system_order_policy", ""))
            for row in rows
        }),
    }


def main() -> int:
    args = parse_args()
    source_root = Path(__file__).resolve().parents[1]
    study_config = read(
        source_root / "configs" / "revtrace_whisper_w0_w7.json"
    )
    gates = study_config["gates"]
    prior_art = read(
        source_root / "configs" / "revtrace_whisper_w0_prior_art.json"
    )
    w0_pass = prior_art["decision"] == "W0_NO_DIRECT_COLLISION"
    files = sorted(args.input_dir.glob("*.json"))
    workloads = []
    for path in files:
        try:
            row = read(path)
        except Exception:
            continue
        if row.get("study") == "Whisper cross-architecture system-performance closure":
            row["_path"] = str(path)
            workloads.append(row)

    matrix: dict[str, Any] = {}
    for model in MODELS:
        matrix[model] = {}
        for cell in (*PRODUCTION, "B1", "B2"):
            matrix[model][cell] = {}
            for system in SYSTEMS:
                rows = [
                    row for row in workloads
                    if is_formal_matrix_row(
                        row, model=model, cell=cell, system=system
                    )
                ]
                matrix[model][cell][system] = summarize_group(rows)
            ours = matrix[model][cell]["revtrace"]
            feedback = matrix[model][cell]["feedback-off-batch"]
            recovery_values = []
            ours_by_seed = {
                int(row["config"]["seed"]): row for row in workloads
                if is_formal_matrix_row(
                    row, model=model, cell=cell, system="revtrace"
                )
            }
            feedback_by_seed = {
                int(row["config"]["seed"]): row for row in workloads
                if is_formal_matrix_row(
                    row,
                    model=model,
                    cell=cell,
                    system="feedback-off-batch",
                )
            }
            for seed in set(ours_by_seed) & set(feedback_by_seed):
                numerator = float(
                    ours_by_seed[seed]["metrics"][
                        "display_slo_goodput"
                    ]
                )
                denominator = float(
                    feedback_by_seed[seed]["metrics"]["slo_goodput"]
                )
                if denominator > 0:
                    recovery_values.append(numerator / denominator)
            ours["minimum_feedback_off_goodput_recovery"] = min_or_none(
                recovery_values
            )
            expected_runs = (
                5 if cell in ("W1", "W3")
                else 3 if cell in ("W2", "W4")
                else 1
            )
            all_system_runs_complete = all(
                matrix[model][cell][system]["runs"] >= expected_runs
                for system in SYSTEMS
            )
            order_gate = (
                ours["system_order_indices"] == list(range(5))
                if expected_runs == 5
                else len(ours["system_order_indices"])
                == expected_runs
            )
            expected_sessions = 32 if cell == "B1" else (
                16 if cell in ("W1", "W2", "B2") else 8
            )
            expected_max_new_tokens = EXPECTED_MAX_NEW_TOKENS[
                model
            ][f"c{ours['active_concurrency_values'][0]}"] if (
                len(ours["active_concurrency_values"]) == 1
            ) else None
            passed = (
                all_system_runs_complete
                and ours["runs"] >= expected_runs
                and ours["median_wall_speedup"] is not None
                and ours["median_wall_speedup"]
                >= gates["median_wall_speedup_min"]
                and ours["median_gpu_normalized_speedup"]
                >= gates["median_gpu_normalized_speedup_min"]
                and ours["median_display_slo_goodput_speedup"]
                >= gates["median_display_slo_goodput_speedup_min"]
                and ours["maximum_p99_seconds"] is not None
                and ours["maximum_p99_seconds"]
                <= gates["maximum_state_entry_p99_seconds"]
                and ours["maximum_display_p99_seconds"] is not None
                and ours["maximum_display_p99_seconds"]
                <= gates["maximum_display_p99_seconds"]
                and ours["minimum_energy_reduction"] is not None
                and ours["minimum_energy_reduction"]
                >= gates["minimum_energy_reduction"]
                and ours["maximum_verification_fraction"] is not None
                and ours["maximum_verification_fraction"]
                <= gates["synchronous_verification_fraction_max"]
                and ours[
                    "minimum_feedback_off_goodput_recovery"
                ] is not None
                and ours["minimum_feedback_off_goodput_recovery"]
                >= gates[
                    "feedback_off_display_goodput_recovery_min"
                ]
                and ours["state_violations"] == 0
                and ours["post_timing_fast_path_audits"]
                == ours["safe_commits"]
                and ours["post_timing_stable_state_mismatches"] == 0
                and ours["stale_commits"] == 0
                and ours["display_deadline_misses"] == 0
                and len(ours["active_concurrency_values"]) == 1
                and ours["session_count_values"] == [expected_sessions]
                and ours["max_new_tokens_values"]
                == [expected_max_new_tokens]
                and len(ours["margin_threshold_values"]) == 1
                and ours["prompt_state_semantics"]
                == [PROMPT_STATE_SEMANTICS]
                and ours["precision_values"] == ["float16"]
                and ours["baseline_capacity_protocol_values"]
                == ["declared-work-capacity-rebase-v2"]
                and ours["state_control_protocol_values"]
                == [STATE_CONTROL_PROTOCOL]
                and ours["post_timing_validation_values"]
                == [
                    "exhaustive-same-state-replay-with-repeat-control-v2"
                ]
                and ours["system_order_policies"]
                == ["cyclic-latin-square-v1"]
                and order_gate
            )
            ours["all_system_runs_complete"] = (
                all_system_runs_complete
            )
            ours["performance_gate_pass"] = passed

    smoke: dict[str, Any] = {}
    smoke_all_pass = True
    for model in MODELS:
        slug = model.removeprefix("whisper-").removesuffix(".en")
        path = args.input_dir / f"w1-smoke-{slug}-final.json"
        row = read(path) if path.exists() else None
        counts = row.get("counts", {}) if row else {}
        passed = (
            row is not None
            and int(counts.get("rows", 0)) == 4
            and int(counts.get("distinct_prompt_token_rows", 0)) == 4
            and int(
                counts.get("raw_history_rows_with_start_marker", 0)
            ) == 4
        )
        smoke[model] = {
            "decision": "W1_SMOKE_PASS" if passed else "W1_SMOKE_FAIL",
            "counts": counts,
        }
        smoke_all_pass = smoke_all_pass and passed

    known_path = args.input_dir / "w2-known-pairs-v4.json"
    known_pairs = read(known_path) if known_path.exists() else None
    w2_pass = (
        known_pairs is not None
        and known_pairs.get("decision")
        == "W2_KNOWN_PAIR_REGRESSION_PASS"
        and known_pairs.get("config", {}).get("state_semantics")
        == PROMPT_STATE_SEMANTICS
        and known_pairs.get("counts", {}).get("state_eligible_pairs")
        == 15
        and known_pairs.get("counts", {}).get(
            "known_pairs_protected"
        ) == 15
        and known_pairs.get("counts", {}).get(
            "stale_parent_commits_rejected"
        ) == 15
        and known_pairs.get("counts", {}).get(
            "terminal_authority_pairs"
        ) == 6
    )

    mechanism: dict[str, Any] = {}
    mechanism_all_pass = True
    for model in MODELS:
        slug = model.removeprefix("whisper-").removesuffix(".en")
        path = args.input_dir / f"w3-mechanism-{slug}.json"
        row = read(path) if path.exists() else None
        counts = row.get("counts", {}) if row else {}
        config = row.get("config", {}) if row else {}
        passed = (
            row is not None
            and int(counts.get("same_input_events", 0)) >= 500
            and int(
                counts.get("singleton_repeat_mismatches", -1)
            ) == 0
            and int(counts.get("distinct_state_pairs", 0)) >= 1
            and int(
                counts.get("feedback_on_propagated_pairs", 0)
            ) >= 1
            and int(
                counts.get("feedback_off_propagated_pairs", -1)
            ) == 0
            and config.get("prompt_state_semantics")
            == PROMPT_STATE_SEMANTICS
            and config.get("capacity_protocol")
            == "declared-work-capacity-rebase-v2"
            and int(config.get("max_new_tokens", -1))
            == EXPECTED_MAX_NEW_TOKENS[model]["c16"]
        )
        mechanism[model] = {
            "decision": (
                "W3_FEEDBACK_MECHANISM_PASS"
                if passed else "W3_FEEDBACK_MECHANISM_BOUNDARY"
            ),
            "counts": counts,
            "max_new_tokens": config.get("max_new_tokens"),
        }
        mechanism_all_pass = mechanism_all_pass and passed

    risk: dict[str, Any] = {}
    risk_all_pass = True
    for model in MODELS:
        risk[model] = {}
        slug = model.removeprefix("whisper-").removesuffix(".en")
        for concurrency in (8, 16):
            def pointer(name: str) -> str:
                return (args.input_dir / name).read_text(
                    encoding="utf-8"
                ).strip()

            final_threshold = float(pointer(
                f"w4-final-threshold-{slug}-c{concurrency}.txt"
            ))
            late_window_raw = pointer(
                f"w4-final-late-window-{slug}-c{concurrency}.txt"
            )
            final_late_window = (
                None if late_window_raw == "none"
                else int(late_window_raw)
            )
            late_threshold_raw = pointer(
                f"w4-final-late-threshold-{slug}-c{concurrency}.txt"
            )
            final_late_threshold = (
                None if late_threshold_raw == "none"
                else float(late_threshold_raw)
            )
            high_load_prompt_raw = pointer(
                f"w4-final-high-load-prompt-{slug}-c{concurrency}.txt"
            )
            final_high_load_prompt = (
                None if high_load_prompt_raw == "none"
                else int(high_load_prompt_raw)
            )
            high_load_threshold_raw = pointer(
                f"w4-final-high-load-threshold-{slug}-c{concurrency}.txt"
            )
            final_high_load_threshold = (
                None if high_load_threshold_raw == "none"
                else float(high_load_threshold_raw)
            )
            parts = []
            rejected_parts = []
            for path in files:
                if (
                    path.name.startswith(
                        f"w4-risk-{slug}-c{concurrency}-"
                    )
                    and path.name.endswith(".json")
                    and ".checkpoint." not in path.name
                ):
                    row = read(path)
                    row["_source_file"] = path.name
                    config = row.get("config", {})
                    contract_matches = (
                        row.get("model") == model
                        and int(config.get("concurrency", -1))
                        == concurrency
                        and config.get("precision") == "float16"
                        and config.get("prompt_state_semantics")
                        == PROMPT_STATE_SEMANTICS
                        and config.get("state_control_protocol")
                        == STATE_CONTROL_PROTOCOL
                        and config.get("audit_interference")
                        == "shadow-canonical-no-state-mutation"
                        and int(config.get("duration_seconds", 0))
                        == 180
                        and bool(config.get("policy_source"))
                        and len(str(config.get("policy_sha256", "")))
                        == 64
                        and config.get("proposer_device")
                        == config.get("verifier_device")
                        and int(config.get("max_new_tokens", -1))
                        == EXPECTED_MAX_NEW_TOKENS[
                            model
                        ][f"c{concurrency}"]
                        and int(config.get(
                            "authority_max_new_tokens",
                            config.get("max_new_tokens", -1),
                        )) == 96
                        and (
                            int(config.get("max_new_tokens", -1)) == 96
                            or config.get("work_authority_protocol")
                            == WORK_AUTHORITY_PROTOCOL
                        )
                        and (
                            int(config.get("max_new_tokens", -1)) == 96
                            or config.get("target_capacity_protocol")
                            == TARGET_CAPACITY_PROTOCOL
                        )
                        and math.isclose(
                            float(config.get("margin_threshold", -1.0)),
                            final_threshold,
                            rel_tol=0.0,
                            abs_tol=1e-12,
                        )
                        and config.get("late_window_index")
                        == final_late_window
                        and config.get("late_margin_threshold")
                        == final_late_threshold
                        and config.get("high_load_prompt_tokens")
                        == final_high_load_prompt
                        and config.get("high_load_margin_threshold")
                        == final_high_load_threshold
                    )
                    if (
                        "risk_certificate" in row
                        and row.get("decision")
                        == "W4_RISK_CERTIFICATE_PASS"
                        and (
                            not row.get(
                                "adaptation_only_stop_on_caught_error", False
                            )
                            or (
                                int(row.get("counts", {}).get(
                                    "risk_eligible_entries", 0
                                )) >= 30_000
                                and int(row.get("counts", {}).get(
                                    "pre_outcome_randomized_audits", 0
                                )) >= 500
                                and int(row.get("counts", {}).get(
                                    "caught_state_errors", -1
                                )) == 0
                            )
                        )
                        and contract_matches
                    ):
                        parts.append(row)
                    elif "risk_certificate" in row:
                        rejected_parts.append(path.name)
            entries = sum(
                int(row["counts"]["risk_eligible_entries"])
                for row in parts
            )
            audits = sum(
                int(
                    row["counts"]["pre_outcome_randomized_audits"]
                )
                for row in parts
            )
            caught = sum(
                int(row["counts"]["caught_state_errors"]) for row in parts
            )
            bound = AuditRiskBound(
                args.audit_probability, args.alpha
            )
            upper = (
                bound.upper_risk(entries, caught) if entries else 1.0
            )
            fixed_policy_independent_streams = (
                fixed_policy_independent_audit_streams(parts)
            )
            passed = (
                fixed_policy_independent_streams
                and entries >= 30_000
                and audits >= 500
                and upper <= 0.005
            )
            risk[model][f"c{concurrency}"] = {
                "parts": len(parts),
                "fixed_policy_independent_streams": (
                    fixed_policy_independent_streams
                ),
                "final_result_files": [
                    row["_source_file"] for row in parts
                ],
                "final_result_file": (
                    parts[0]["_source_file"]
                    if len(parts) == 1 else None
                ),
                "rejected_or_nonfinal_parts": rejected_parts,
                "risk_eligible_entries": entries,
                "random_audits": audits,
                "caught_state_errors": caught,
                "time_uniform_upper_risk": upper,
                "margin_threshold": (
                    float(parts[0]["config"]["margin_threshold"])
                    if parts else None
                ),
                "late_window_index": (
                    parts[0]["config"].get("late_window_index")
                    if parts else None
                ),
                "late_margin_threshold": (
                    parts[0]["config"].get("late_margin_threshold")
                    if parts else None
                ),
                "high_load_prompt_tokens": (
                    parts[0]["config"].get("high_load_prompt_tokens")
                    if parts else None
                ),
                "high_load_margin_threshold": (
                    parts[0]["config"].get(
                        "high_load_margin_threshold"
                    )
                    if parts else None
                ),
                "prompt_state_semantics": (
                    parts[0]["config"]["prompt_state_semantics"]
                    if parts else None
                ),
                "max_new_tokens": (
                    int(parts[0]["config"]["max_new_tokens"])
                    if parts else None
                ),
                "authority_max_new_tokens": (
                    int(parts[0]["config"].get(
                        "authority_max_new_tokens",
                        parts[0]["config"]["max_new_tokens"],
                    ))
                    if parts else None
                ),
                "pass": passed,
            }
            risk_all_pass = risk_all_pass and passed

    production_passes = 0
    required_w1 = True
    required_long = {model: False for model in MODELS}
    for model in MODELS:
        for cell in (*PRODUCTION, "B1", "B2"):
            ours = matrix[model][cell]["revtrace"]
            concurrency_values = ours["active_concurrency_values"]
            risk_row = (
                risk[model].get(f"c{concurrency_values[0]}")
                if len(concurrency_values) == 1 else None
            )
            threshold_values = ours["margin_threshold_values"]
            threshold_match = (
                risk_row is not None
                and risk_row["pass"]
                and len(threshold_values) == 1
                and risk_row["margin_threshold"] is not None
                and math.isclose(
                    threshold_values[0],
                    float(risk_row["margin_threshold"]),
                    rel_tol=0.0,
                    abs_tol=1e-12,
                )
            )
            late_window_values = ours["late_window_index_values"]
            late_margin_values = ours["late_margin_threshold_values"]
            late_contract_match = (
                risk_row is not None
                and len(late_window_values) == 1
                and len(late_margin_values) == 1
                and late_window_values[0] == risk_row["late_window_index"]
                and (
                    late_margin_values[0]
                    == risk_row["late_margin_threshold"]
                    or (
                        late_margin_values[0] is not None
                        and risk_row["late_margin_threshold"] is not None
                        and math.isclose(
                            float(late_margin_values[0]),
                            float(risk_row["late_margin_threshold"]),
                            rel_tol=0.0,
                            abs_tol=1e-12,
                        )
                    )
                )
            )
            high_load_prompt_values = ours[
                "high_load_prompt_tokens_values"
            ]
            high_load_margin_values = ours[
                "high_load_margin_threshold_values"
            ]
            high_load_contract_match = (
                risk_row is not None
                and len(high_load_prompt_values) == 1
                and len(high_load_margin_values) == 1
                and high_load_prompt_values[0]
                == risk_row["high_load_prompt_tokens"]
                and (
                    high_load_margin_values[0]
                    == risk_row["high_load_margin_threshold"]
                    or (
                        high_load_margin_values[0] is not None
                        and risk_row[
                            "high_load_margin_threshold"
                        ] is not None
                        and math.isclose(
                            float(high_load_margin_values[0]),
                            float(
                                risk_row[
                                    "high_load_margin_threshold"
                                ]
                            ),
                            rel_tol=0.0,
                            abs_tol=1e-12,
                        )
                    )
                )
            )
            passed = (
                bool(ours["performance_gate_pass"])
                and threshold_match
                and late_contract_match
                and high_load_contract_match
                and ours["verifier_lanes_values"] == [1]
                and ours["verifier_lane_exact_values"] == [True]
                and ours["terminal_spillover_values"] == [False]
                and ours["terminal_contract_values"] == ["state-only"]
                and ours["authority_max_new_tokens_values"] == [96]
                and ours["work_authority_protocol_values"]
                == [WORK_AUTHORITY_PROTOCOL]
                and ours["target_capacity_protocol_values"]
                == [TARGET_CAPACITY_PROTOCOL]
            )
            ours["risk_contract_match"] = threshold_match
            ours["late_risk_contract_match"] = late_contract_match
            ours["high_load_risk_contract_match"] = (
                high_load_contract_match
            )
            ours["joint_gate_pass"] = passed
            if cell in PRODUCTION:
                production_passes += int(passed)
            if cell == "W1":
                required_w1 = required_w1 and passed
            if cell in ("W3", "W4") and passed:
                required_long[model] = True

    quality: dict[str, Any] = {}
    quality_all_pass = True
    for model in MODELS:
        slug = model.removeprefix("whisper-").removesuffix(".en")
        path = args.input_dir / f"w6-quality-{slug}.json"
        row = read(path) if path.exists() else None
        quality[model] = (
            {
                "decision": row["decision"],
                "counts": row["counts"],
                "metrics": row["metrics"],
            }
            if row else {"decision": "MISSING"}
        )
        quality_all_pass = (
            quality_all_pass
            and row is not None
            and row["decision"] == "W6_QUALITY_UX_PASS"
            and row["config"].get("prompt_state_semantics")
            == PROMPT_STATE_SEMANTICS
            and row["config"].get("state_control_protocol")
            == STATE_CONTROL_PROTOCOL
            and row["config"].get(
                "local_agreement_capacity_protocol"
            ) == "declared-work-capacity-rebase-v2"
            and row["config"].get("precision") == "float16"
            and int(row["config"].get("max_new_tokens", -1))
            == EXPECTED_MAX_NEW_TOKENS[model]["c16"]
            and int(
                row["config"].get("reference_max_new_tokens", -1)
            ) == 96
            and int(
                row["config"].get("authority_max_new_tokens", -1)
            ) == 96
            and row["config"].get("work_authority_protocol")
            == WORK_AUTHORITY_PROTOCOL
            and row["config"].get("target_capacity_protocol")
            == TARGET_CAPACITY_PROTOCOL
            and row["config"].get("deferred_risk_authority") is True
            and row["config"].get("deferred_terminal_authority") is False
            and risk[model]["c16"]["margin_threshold"] is not None
            and math.isclose(
                float(row["config"]["margin_threshold"]),
                float(risk[model]["c16"]["margin_threshold"]),
                rel_tol=0.0,
                abs_tol=1e-12,
            )
            and row["config"].get("late_window_index")
            == risk[model]["c16"]["late_window_index"]
            and row["config"].get("late_margin_threshold")
            == risk[model]["c16"]["late_margin_threshold"]
            and row["config"].get("high_load_prompt_tokens")
            == risk[model]["c16"]["high_load_prompt_tokens"]
            and row["config"].get("high_load_margin_threshold")
            == risk[model]["c16"]["high_load_margin_threshold"]
        )

    completed = (
        w0_pass
        and smoke_all_pass
        and w2_pass
        and mechanism_all_pass
        and production_passes >= gates["production_cells_pass_min"]
        and required_w1
        and all(required_long.values())
        and risk_all_pass
        and quality_all_pass
    )
    decision = (
        "W7_CROSS_FAMILY_STRONG_PASS"
        if completed else "W7_INCOMPLETE_OR_BOUNDARY"
    )
    artifact_files = [
        {
            "path": str(path.relative_to(args.input_dir)),
            "sha256": sha256(path),
            "bytes": path.stat().st_size,
        }
        for path in files
        if not path.name.startswith("excluded-")
        and ".checkpoint." not in path.name
    ]
    source_names = (
        "configs/revtrace_whisper_w0_w7.json",
        "configs/revtrace_whisper_w0_prior_art.json",
        "src/revtrace/whisper_state.py",
        "src/revtrace/control.py",
        "src/revtrace/risk.py",
        "scripts/remote/whisper_batched_executor.py",
        "scripts/remote/run_whisper_w_system.py",
        "scripts/remote/run_whisper_w_mechanism.py",
        "scripts/remote/run_whisper_w_quality.py",
        "scripts/remote/run_whisper_w_matrix.sh",
        "scripts/remote/run_whisper_w3_parallel.sh",
        "scripts/remote/run_whisper_w4_audits.sh",
        "scripts/remote/run_whisper_w4_contract.sh",
        "scripts/remote/run_whisper_w4_dynamic_work_recert.sh",
        "scripts/remote/finish_whisper_w0_w7_v2.sh",
        "scripts/remote/finish_whisper_w4_contracts.sh",
        "scripts/remote/run_whisper_w5_parallel.sh",
        "scripts/remote/run_whisper_w5_authority_scheduler_ablation.sh",
        "scripts/remote/run_whisper_w5_state_contract_crossscale.sh",
        "scripts/remote/run_whisper_w5_state_lane_ablation.sh",
        "scripts/remote/run_whisper_w5_terminal_scheduler_ablation.sh",
        "scripts/remote/run_whisper_w5_transaction_ablation.sh",
        "scripts/remote/run_whisper_w6_parallel.sh",
        "scripts/remote/run_whisper_w6_base_prerun_current.sh",
        "scripts/remote/run_whisper_w6_failure_attribution.sh",
        "scripts/remote/run_whisper_w6_budget_authority_dev.sh",
        "scripts/remote/diagnose_whisper_w6_canonical_trace.py",
        "scripts/remote/run_whisper_w6_state_root_diagnostic.sh",
        "scripts/remote/run_whisper_w6_state_contract_dev.sh",
        "scripts/remote/run_whisper_w7_finalize.sh",
        "scripts/remote/run_whisper_w_smoke.py",
        "scripts/remote/run_whisper_w_concurrent_probe.py",
        "scripts/remote/build_whisper_w_quality_manifest.py",
        "scripts/validate_whisper_w_known_pairs.py",
        "scripts/select_whisper_w_policy.py",
        "scripts/build_whisper_w_state_age_policy.py",
        "scripts/extract_whisper_w5_adaptation_root.py",
        "scripts/build_whisper_w0_w7_artifact.py",
        "scripts/renew_whisper_w_policy.py",
        "scripts/finalize_whisper_w0_w7.py",
        "scripts/finalize_revtrace_paper_evidence.py",
        "scripts/remote/resume_whisper_w5_w6_after_recert.sh",
        "scripts/remote/resume_whisper_w5_w6_state_contract.sh",
        "scripts/remote/release_whisper_w5_after_dynamic_preflight.sh",
        "tests/test_whisper_prompt_state.py",
        "tests/test_whisper_policy_selection.py",
        "tests/test_whisper_w0_w7_finalizer.py",
        "tests/test_whisper_w5_adaptation_root.py",
        "docs/reports/revtrace_paper_identity.md",
        "docs/reports/whisper_w5_protocol_repair.md",
    )
    source_files = []
    for name in source_names:
        path = source_root / name
        if not path.exists():
            raise FileNotFoundError(path)
        source_files.append({
            "path": name,
            "sha256": sha256(path),
            "bytes": path.stat().st_size,
        })
    output = {
        "schema_version": 1,
        "study": "RevTrace W0-W7 final closure",
        "decision": decision,
        "paper_identity": (
            "method-driven state-certified revision serving; Whisper is "
            "cross-family evidence, not the paper identity"
        ),
        "w0_prior_art": prior_art,
        "w1_smoke": smoke,
        "w2_known_pair_regression": (
            known_pairs if known_pairs is not None
            else {"decision": "MISSING"}
        ),
        "w3_feedback_mechanism": mechanism,
        "production_cells_passed": production_passes,
        "production_cells_total": 8,
        "required_w1_pass": required_w1,
        "required_long_cell_pass": required_long,
        "risk": risk,
        "quality": quality,
        "matrix": matrix,
        "artifact_files": artifact_files,
        "source_files": source_files,
        "claim_boundaries": [
            "fixed-dtype same-executor ablations attribute gains to state-authority control",
            "zero observed state violations is not deterministic floating-point exactness",
            "risk evidence is not pooled across models or concurrency fingerprints",
            "boundary cells do not count toward the 6/8 production gate",
            (
                "terminal output has no feedback-state edge; the state-only "
                "terminal contract is bounded by paired W6 quality and is "
                "not claimed singleton-exact"
            ),
            (
                "provisional display latency and authoritative state-entry "
                "latency are separate clocks and cannot substitute for one "
                "another"
            ),
            (
                "a delayed replay mismatch is attributed to the fast path "
                "only when a same-input singleton repeat is stable"
            ),
        ],
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(
        json.dumps(output, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    lines = [
        "# RevTrace Whisper W0-W7 closure",
        "",
        f"Decision: `{decision}`.",
        "",
        "## Paper identity",
        "",
        output["paper_identity"] + ".",
        "",
        "## Joint production gate",
        "",
        f"- Production cells passed: {production_passes}/8.",
        f"- Both W1 cells pass: {required_w1}.",
        f"- Long-cell coverage: `{required_long}`.",
        f"- W0 prior-art boundary pass: {w0_pass}.",
        f"- W1 two-scale smoke pass: {smoke_all_pass}.",
        f"- W2 state-adapter regression pass: {w2_pass}.",
        f"- W3 feedback mechanism pass: {mechanism_all_pass}.",
        "",
        "## Risk contracts",
        "",
        "| Model | Contract | Entries | Audits | Caught | UCB | Pass |",
        "|---|---:|---:|---:|---:|---:|:---:|",
    ]
    for model in MODELS:
        for contract, row in risk[model].items():
            lines.append(
                f"| {model} | {contract} | "
                f"{row['risk_eligible_entries']} | {row['random_audits']} | "
                f"{row['caught_state_errors']} | "
                f"{100 * row['time_uniform_upper_risk']:.4f}% | "
                f"{row['pass']} |"
            )
    lines.extend([
        "",
        "## Production RevTrace cells",
        "",
        "| Model | Cell | Runs | Wall | GPU-norm | Display SLO | Display P99 | State P99 | Energy red. | Verify | Feedback-off recovery | Pass |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|:---:|",
    ])
    for model in MODELS:
        for cell in PRODUCTION:
            row = matrix[model][cell]["revtrace"]
            lines.append(
                f"| {model} | {cell} | {row['runs']} | "
                f"{fmt(row['median_wall_speedup'])}x | "
                f"{fmt(row['median_gpu_normalized_speedup'])}x | "
                f"{fmt(row['median_display_slo_goodput_speedup'])}x | "
                f"{fmt(row['maximum_display_p99_seconds'])}s | "
                f"{fmt(row['maximum_p99_seconds'])}s | "
                f"{fmt(row['minimum_energy_reduction'])} | "
                f"{fmt(row['maximum_verification_fraction'])} | "
                f"{fmt(row['minimum_feedback_off_goodput_recovery'])} | "
                f"{row['joint_gate_pass']} |"
            )
    lines.extend([
        "",
        "## Same-executor causal comparison",
        "",
        "| Model | Cell | System | Runs | Wall | SLO goodput | P99 | Energy red. | State violations |",
        "|---|---:|---|---:|---:|---:|---:|---:|---:|",
    ])
    for model in MODELS:
        for cell in PRODUCTION:
            for system in SYSTEMS:
                row = matrix[model][cell][system]
                lines.append(
                    f"| {model} | {cell} | {system} | "
                    f"{row['runs']} | "
                    f"{fmt(row['median_wall_speedup'])}x | "
                    f"{fmt(row['median_slo_goodput_speedup'])}x | "
                    f"{fmt(row['maximum_p99_seconds'])}s | "
                    f"{fmt(row['minimum_energy_reduction'])} | "
                    f"{row['state_violations']} |"
                )
    lines.extend([
        "",
        "## Paired quality and UX",
        "",
        "| Model | Sessions | Mean WER delta | Bootstrap 95% upper | Catastrophic | Provisional P95 | Pass |",
        "|---|---:|---:|---:|---:|---:|:---:|",
    ])
    for model in MODELS:
        row = quality[model]
        if row["decision"] == "MISSING":
            lines.append(f"| {model} | 0 | NA | NA | NA | NA | False |")
            continue
        lines.append(
            f"| {model} | {row['counts']['sessions']} | "
            f"{fmt(row['metrics']['mean_wer_delta_pp'])} pp | "
            f"{fmt(row['metrics']['paired_bootstrap_95_upper_pp'])} pp | "
            f"{row['counts']['catastrophic_outliers']} | "
            f"{fmt(row['metrics']['provisional_lifetime_p95'])}s | "
            f"{row['decision'] == 'W6_QUALITY_UX_PASS'} |"
        )
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({
        "decision": decision,
        "w0_pass": w0_pass,
        "smoke_all_pass": smoke_all_pass,
        "w2_pass": w2_pass,
        "mechanism_all_pass": mechanism_all_pass,
        "production_cells_passed": production_passes,
        "risk_all_pass": risk_all_pass,
        "quality_all_pass": quality_all_pass,
    }, sort_keys=True))
    return 0 if completed else 2


if __name__ == "__main__":
    raise SystemExit(main())

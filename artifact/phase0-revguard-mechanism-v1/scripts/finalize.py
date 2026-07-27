#!/usr/bin/env python3
"""Finalize RevGuard mechanism gates from live compact records."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


MODELS = ("qwen3-asr-0.6b", "qwen3-asr-1.7b")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input-dir", type=Path, default=Path("results/revguard/probe")
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("results/revguard/revguard_v1/summary.json"),
    )
    return parser.parse_args()


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def margin_row(payload: dict[str, Any], threshold: float) -> dict[str, Any]:
    for row in payload["summary"]["margin_sweep"]:
        if row["minimum_margin_threshold"] == threshold:
            return row
    raise KeyError(f"missing threshold {threshold}")


def main() -> int:
    args = parse_args()
    config = load(Path("configs/revguard_mechanism_gate.json"))
    threshold = float(config["frozen_margin_threshold"])
    models = []
    for model in MODELS:
        calibration = load(
            args.input_dir / f"same-input-d30-c8-{model}.json"
        )
        validation = load(
            args.input_dir / f"same-input-d30-c16-{model}.json"
        )
        selective = load(
            args.input_dir / f"selective-d30-c16-m1.0-{model}.json"
        )
        fp32_calibration = load(
            args.input_dir / f"same-input-float32-d30-c8-{model}.json"
        )
        fp32_validation = load(
            args.input_dir / f"same-input-float32-d30-c16-{model}.json"
        )
        calibration_margin = margin_row(calibration, threshold)
        validation_margin = margin_row(validation, threshold)
        validation_summary = validation["summary"]
        selective_summary = selective["summary"]
        m1_pass = (
            calibration["summary"]["singleton_repeat_token_exact_rate"] == 1.0
            and validation_summary["singleton_repeat_token_exact_rate"] == 1.0
            and (
                calibration["summary"]["cross_shape_mismatch_events"] > 0
                or validation_summary["cross_shape_mismatch_events"] > 0
            )
        )
        m2_pass = (
            validation_margin["false_safe_events"] == 0
            and validation_margin["coverage"]
            >= config["m2_empirical"]["minimum_safe_coverage"]
        )
        m3_pass = (
            selective_summary["policy_violation_events"] == 0
            and selective_summary["single_gpu_policy_speedup"]
            >= config["m3"]["minimum_single_gpu_policy_speedup"]
        )
        m4_pass = (
            selective_summary["verifier_to_proposer_service_ratio"]
            <= config["m4"][
                "verifier_service_time_must_not_exceed_fraction_of_proposer"
            ]
        )
        fp32_shape_stable = all(
            payload["summary"]["singleton_repeat_token_exact_rate"] == 1.0
            and payload["summary"]["batch_repeat_token_exact_rate"] == 1.0
            and payload["summary"][
                "same_input_cross_shape_token_exact_rate"
            ] == 1.0
            for payload in (fp32_calibration, fp32_validation)
        )
        aligned_cross_dtype = [
            (bf16_event, fp32_event)
            for bf16_event, fp32_event in zip(
                calibration["events"], fp32_calibration["events"]
            )
            if bf16_event["input_sha256"] == fp32_event["input_sha256"]
        ]
        replica_probes = [
            event["identical_job_replica_probe"]
            for event in calibration["events"]
            if event.get("identical_job_replica_probe") is not None
        ]
        models.append(
            {
                "model_name": calibration["model_name"],
                "m1_pass": m1_pass,
                "m2_empirical_pass": m2_pass,
                "m3_live_oracle_pass": m3_pass,
                "m4_full_hide_pass": m4_pass,
                "fp32_shape_stable": fp32_shape_stable,
                "calibration": {
                    "event_count": calibration["summary"]["event_count"],
                    "singleton_repeat_exact": calibration["summary"][
                        "singleton_repeat_token_exact_rate"
                    ],
                    "batch_repeat_exact": calibration["summary"][
                        "batch_repeat_token_exact_rate"
                    ],
                    "cross_shape_exact": calibration["summary"][
                        "same_input_cross_shape_token_exact_rate"
                    ],
                    "threshold_1_coverage": calibration_margin["coverage"],
                    "threshold_1_false_safe": calibration_margin[
                        "false_safe_events"
                    ],
                    "replica_probe_count": len(replica_probes),
                    "replica_all_rows_exact_count": sum(
                        probe["all_rows_exact"] for probe in replica_probes
                    ),
                    "replica_all_rows_match_singleton_count": sum(
                        probe["all_rows_match_singleton"]
                        for probe in replica_probes
                    ),
                },
                "held_out_shape": {
                    "event_count": validation_summary["event_count"],
                    "singleton_repeat_exact": validation_summary[
                        "singleton_repeat_token_exact_rate"
                    ],
                    "batch_repeat_exact": validation_summary[
                        "batch_repeat_token_exact_rate"
                    ],
                    "cross_shape_exact": validation_summary[
                        "same_input_cross_shape_token_exact_rate"
                    ],
                    "cross_shape_mismatch_events": validation_summary[
                        "cross_shape_mismatch_events"
                    ],
                    "threshold_1_coverage": validation_margin["coverage"],
                    "threshold_1_false_safe": validation_margin[
                        "false_safe_events"
                    ],
                    "lcp_reference_fraction_median": validation_summary[
                        "lcp_reference_fraction_median"
                    ],
                    "lcp_reference_fraction_minimum": validation_summary[
                        "lcp_reference_fraction_minimum"
                    ],
                },
                "selective_live_oracle": selective_summary,
                "fp32_control": {
                    "c8_cross_shape_exact": fp32_calibration["summary"][
                        "same_input_cross_shape_token_exact_rate"
                    ],
                    "c16_cross_shape_exact": fp32_validation["summary"][
                        "same_input_cross_shape_token_exact_rate"
                    ],
                    "c8_batch_speedup_over_fp32_singleton": fp32_calibration[
                        "summary"
                    ]["batch_a_over_singleton_a_speedup"],
                    "c16_batch_speedup_over_fp32_singleton": fp32_validation[
                        "summary"
                    ]["batch_a_over_singleton_a_speedup"],
                    "bf16_fp32_same_input_pairs": len(aligned_cross_dtype),
                    "bf16_singleton_fp32_singleton_exact_pairs": sum(
                        bf16_event["singleton_a"]["token_ids"]
                        == fp32_event["singleton_a"]["token_ids"]
                        for bf16_event, fp32_event in aligned_cross_dtype
                    ),
                    "whole_trajectory_token_exact_events": sum(
                        bf16_event["singleton_a"]["token_ids"]
                        == fp32_event["singleton_a"]["token_ids"]
                        for bf16_event, fp32_event in zip(
                            calibration["events"], fp32_calibration["events"]
                        )
                    ),
                    "whole_trajectory_events": len(calibration["events"]),
                },
            }
        )

    all_m1 = all(model["m1_pass"] for model in models)
    all_m2 = all(model["m2_empirical_pass"] for model in models)
    all_m3 = all(model["m3_live_oracle_pass"] for model in models)
    all_m4 = all(model["m4_full_hide_pass"] for model in models)
    all_fp32_stable = all(model["fp32_shape_stable"] for model in models)
    summary = {
        "schema_version": 1,
        "study": config["study"],
        "decision": (
            "MECHANISM_ORACLE_VALIDATED_EXACT_CERTIFICATE_UNRESOLVED"
            if all_m1 and all_m2 and all_m3
            else "NO_GO_FOR_CURRENT_REVGUARD_MECHANISM"
        ),
        "gates": {
            "m1_same_input_mechanism": "PASS" if all_m1 else "FAIL",
            "m1_fp32_shape_stability": "PASS" if all_fp32_stable else "FAIL",
            "m2_empirical_margin_partition": "PASS" if all_m2 else "FAIL",
            "m2_deterministic_margin_certificate": "NOT_ESTABLISHED",
            "m3_live_selective_oracle": "PASS" if all_m3 else "FAIL",
            "m4_verifier_fully_hidden": "PASS" if all_m4 else "FAIL",
            "m5_dynamic_rollback": "NOT_RUN_SEQUENTIAL_STOP",
        },
        "mathematical_boundary": {
            "sufficient_condition": "m_batch > 2 * ||log_p_batch - log_p_singleton||_infinity",
            "observed_signal": "top-1/top-2 margin",
            "missing_for_deterministic_claim": "a sound online upper bound on full-distribution cross-shape perturbation",
        },
        "models": models,
        "claim_boundary": [
            "The same-input controls distinguish revision-feedback contamination from execution-shape behavior.",
            "Zero false-safe events on the held-out shape are empirical evidence, not a deterministic or production-frequency guarantee.",
            "The dual-GPU number is a service-time pipeline lower bound, not a deployed cross-GPU runtime.",
            "The public English and Chinese samples test execution semantics only, not ASR quality or dataset generalization."
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(
            json.dumps(summary, indent=2, ensure_ascii=False, sort_keys=True)
            + "\n"
        )
    print(json.dumps(summary["gates"], sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

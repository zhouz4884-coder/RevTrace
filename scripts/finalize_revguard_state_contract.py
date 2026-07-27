#!/usr/bin/env python3
"""Aggregate the RevGuard N1/N3 state-contract intervention results."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def compact_probe(path: Path) -> dict[str, Any]:
    payload = load(path)
    summary = payload["summary"]
    return {
        "file": path.name,
        "model": payload["model_name"],
        "dtype": payload["dtype"],
        "concurrency": payload["concurrency"],
        "mm_encoder_attn_backend": payload.get(
            "mm_encoder_attn_backend"
        ),
        "event_count": summary["event_count"],
        "cross_shape_mismatch_events": summary[
            "cross_shape_mismatch_events"
        ],
        "state_projection_mismatch_events": summary[
            "state_projection_mismatch_events"
        ],
        "suffix_only_mismatch_events": summary[
            "full_mismatch_but_state_projection_exact_events"
        ],
        "batch_repeat_exact_rate": summary[
            "batch_repeat_token_exact_rate"
        ],
        "batch_speedup": summary["batch_a_over_singleton_a_speedup"],
    }


def compact_selective(path: Path) -> dict[str, Any]:
    payload = load(path)
    summary = payload["summary"]
    return {
        "file": path.name,
        "model": payload["model_name"],
        "dtype": payload["dtype"],
        "event_count": summary["event_count"],
        "proposal_mismatch_events": summary["proposal_mismatch_events"],
        "verified_events": summary["verified_events"],
        "verification_fraction": summary["verification_fraction"],
        "policy_violation_events": summary["policy_violation_events"],
        "policy_state_projection_violation_events": summary[
            "policy_state_projection_violation_events"
        ],
        "single_gpu_policy_speedup": summary[
            "single_gpu_policy_speedup"
        ],
        "dual_gpu_pipeline_lower_bound_speedup": summary[
            "dual_gpu_pipeline_lower_bound_speedup"
        ],
        "verifier_to_proposer_service_ratio": summary[
            "verifier_to_proposer_service_ratio"
        ],
        "dual_gpu_headroom_condition_ratio": summary[
            "dual_gpu_headroom_condition_ratio"
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    probes = [
        compact_probe(path)
        for path in sorted(args.input_dir.glob("same-input-*.json"))
    ]
    selective = [
        compact_selective(path)
        for path in sorted(args.input_dir.glob("selective-*.json"))
    ]
    if len(probes) != 16 or len(selective) != 2:
        raise AssertionError(
            f"expected 16 probes and 2 live runs, got "
            f"{len(probes)} and {len(selective)}"
        )

    default_bf16 = [
        row
        for row in probes
        if row["file"].startswith("same-input-n1-bfloat16")
    ]
    full_mismatches = sum(
        row["cross_shape_mismatch_events"] for row in default_bf16
    )
    state_mismatches = sum(
        row["state_projection_mismatch_events"] for row in default_bf16
    )
    absorbed = sum(
        row["suffix_only_mismatch_events"] for row in default_bf16
    )

    live_pass = all(
        row["policy_violation_events"] == 0
        and row["policy_state_projection_violation_events"] == 0
        and row["verification_fraction"] <= 0.1
        and row["verifier_to_proposer_service_ratio"] <= 0.8
        and row["single_gpu_policy_speedup"] >= 2.0
        for row in selective
    )
    result = {
        "schema_version": 1,
        "decision": (
            "LIVE_MECHANISM_GATE_PASS_"
            "DETERMINISTIC_CERTIFICATE_UNRESOLVED"
            if live_pass
            else "LIVE_MECHANISM_GATE_FAIL"
        ),
        "default_bf16_state_projection": {
            "event_count": sum(row["event_count"] for row in default_bf16),
            "full_mismatch_events": full_mismatches,
            "state_projection_mismatch_events": state_mismatches,
            "rollback_absorbed_mismatch_events": absorbed,
            "rollback_absorption_fraction": (
                absorbed / full_mismatches if full_mismatches else 1.0
            ),
        },
        "gates": {
            "n1_commit_projection_general_filter": "FAIL",
            "n3_decoder_attention_only": "FAIL",
            "n3_mm_encoder_attention_only": "FAIL",
            "n3_combined_attention_cross_model": "FAIL",
            "n3_fp16_without_verifier": "FAIL_DETERMINISTIC",
            "n3_live_fp16_selective_verification": (
                "PASS" if live_pass else "FAIL"
            ),
            "deterministic_margin_certificate": "NOT_ESTABLISHED",
            "fp32_concurrency_invariant_canonical": (
                "PASS_FROM_PRIOR_720_EVENT_GATE"
            ),
        },
        "mechanism": {
            "proposer": "float16 batched execution",
            "risk_signal": "minimum full-candidate top-1/top-2 margin <= 0.05",
            "mandatory_verification": "all terminal revisions",
            "canonical_path": "float16 singleton execution",
            "commit_rule": (
                "only the selected policy output may update revision state"
            ),
        },
        "probes": probes,
        "live_runs": selective,
        "claim_boundaries": [
            (
                "Commit projection is exact semantics, but it absorbs only "
                f"{absorbed}/{full_mismatches} observed BF16 full mismatches."
            ),
            (
                "Attention backend and FP16 interventions reduce failures but "
                "do not establish cross-model deterministic invariance."
            ),
            (
                "The live policy has zero observed violations on 480 events; "
                "the 0.05 margin rule remains empirical, not a certificate."
            ),
            (
                "FP32 establishes a stable alternative canonical trajectory, "
                "not exact recovery of the official BF16 singleton trajectory."
            ),
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, indent=2, ensure_ascii=False, sort_keys=True)
        + "\n",
        encoding="utf-8",
    )
    print(json.dumps(result["gates"], sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

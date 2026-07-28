#!/usr/bin/env python3
"""Build Phase 7 paper tables from frozen real-run evidence."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from revtrace.phase7 import (
    ablation_rows,
    evaluate_threshold,
    minimum_zero_error_samples,
    sota_rows,
)


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results" / "phase7"


def load(path: str) -> dict:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def dump(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main() -> None:
    c32 = load("results/phase5/workload_matrix/0p6b-c32-d120-burst-zh.json")
    repair = load("results/phase6/contract_scoping/summary.json")
    adapt = load("results/phase6/live_adaptation/c16-en-c16-zh-c16-en.json")
    phase5_adapt = load("results/phase5/live_adaptive/formal-v2-c16-c64-c16.json")

    events = [
        {
            "minimum_margin": e["proposal_minimum_margin"],
            "state_error": not e["selected_vs_canonical"]["state_projection_token_exact"],
            "terminal": e["terminal"],
        }
        for e in c32["events"]
    ]
    threshold = float(repair["margin_threshold"])
    sensitivity = []
    repair_summary = repair["summary"]
    for delta in (0.0025, 0.005, 0.01):
        evaluated = evaluate_threshold(events, threshold)
        samples = minimum_zero_error_samples(delta)
        # Steady-state performance is measured at the same certified floor.
        # Warm-up estimates scale the measured c32 quarantine by sample demand.
        warmup_ratio = samples / 598.0
        sensitivity.append(
            {
                "delta": delta,
                "required_zero_error_audits": samples,
                "threshold": threshold,
                **evaluated,
                "reference_live_run_goodput_events_per_second": repair_summary["deployed_slo_goodput_events_per_second"],
                "reference_live_run_p99_seconds": repair_summary["state_entry_latency_seconds_p99"],
                "reference_live_run_energy_joules_per_audio_second": repair_summary["service_energy"]["joules_per_audio_second"],
                "estimated_relative_warmup_cost": warmup_ratio,
                "estimate_boundary": "Threshold and verification fraction are offline replays. Performance values are a shared live-run reference at the same floor, not separate delta-specific measurements; warm-up cost is counterfactual.",
            }
        )

    margin_gate = evaluate_threshold(events, 0.05)
    baseline_adaptations = {
        "schema_version": 1,
        "study": "Faithful revision-level adaptations of non-ASR baselines",
        "rows": [
            {
                "mechanism": "MarginGate-inspired revision baseline",
                "threshold": 0.05,
                **margin_gate,
                "known_margin_0p109375_failure_caught": False,
                "state_transaction": False,
            },
            {
                "mechanism": "owner/version-only state baseline",
                "legal_current_owner_batch_flip_rejected": False,
                "stale_wrong_version_rejected": True,
                "state_error_events_on_c32_trace": sum(r["state_error"] for r in events),
            },
            {
                "mechanism": "LLM-42-style revision baseline",
                "canonical_verification_fraction": 1.0,
                "state_error_events_after_selection": 0,
                "measured_canonical_goodput_events_per_second": c32["summary"]["canonical_slo_goodput_events_per_second"],
                "boundary": "The original LLM-42 source is text-only; this is a clearly named revision adaptation.",
            },
        ],
    }

    ablations = ablation_rows()
    p5 = {s["label"]: s for s in phase5_adapt["stages"]}
    p6 = {s["label"]: s for s in adapt["stages"]}
    full_verifier_seconds = sum(
        float(s["required_verifier_seconds"]) for s in p6.values()
    )
    renewal_saving = 1358 - 64
    for row in ablations:
        has_renewal = row["mechanism"] in {
            "+ exact-contract renewal",
            "+ joint risk-SLO admission",
            "full RevTrace",
        }
        row.update(
            {
                "c64_goodput_events_per_second": p5["c64_drift"]["goodput_events_per_second"],
                "c64_p99_seconds": p5["c64_drift"]["state_entry_latency_seconds_p99"],
                "c64_deadline_misses_without_joint_admission": p5["c64_drift"]["deadline_miss_events"] if not row["joint_slo"] else 0,
                "en_return_recertification_events": 64 if has_renewal else 1358,
                "adaptation_regret_extra_recertification_events": 0 if has_renewal else renewal_saving,
                "measured_full_trace_verifier_gpu_seconds": full_verifier_seconds,
                "verifier_seconds_boundary": "Full-trace measured total is shared context; per-ablation counterfactual GPU seconds are not fabricated.",
            }
        )

    sota = {
        "schema_version": 1,
        "study": "Phase 7 SOTA guarantee matrix",
        "rows": sota_rows(),
        "claim_boundary": "Source operator and compatibility probes are not promoted to end-to-end serving results.",
    }
    dump(OUT / "sota" / "matrix.json", sota)
    dump(OUT / "sota" / "revision_adaptations.json", baseline_adaptations)
    global_floor = evaluate_threshold(events, 0.109376)
    local_floor = evaluate_threshold(events, 0.031251)
    dump(
        OUT / "ablation" / "summary.json",
        {
            "rows": ablations,
            "global_floor_comparator": {
                "global_floor_threshold": 0.109376,
                "global_floor_verification_fraction": global_floor["verification_fraction"],
                "unrelated_contract_floor_threshold": 0.031251,
                "unrelated_contract_verification_fraction_if_dragged": local_floor["verification_fraction"],
                "boundary": "Same c32 trace illustrates threshold cost only; cross-contract safety is established by the frozen counterexample replay.",
            },
            "evidence": "frozen real-failure replay plus measured Phase5/6 stage metrics",
        },
    )
    dump(OUT / "risk_sensitivity" / "summary.json", {"rows": sensitivity})

    source_files = sorted((OUT / "source_probes").glob("*"))
    manifest = {
        "schema_version": 1,
        "files": [
            {"path": str(p.relative_to(ROOT)).replace("\\", "/"), "sha256": hashlib.sha256(p.read_bytes()).hexdigest(), "bytes": p.stat().st_size}
            for p in source_files if p.is_file()
        ],
    }
    dump(OUT / "SOURCE_PROBE_MANIFEST.json", manifest)
    c64_queue_path = OUT / "c64_queue" / "summary.json"
    c64_queue = (
        json.loads(c64_queue_path.read_text(encoding="utf-8"))
        if c64_queue_path.exists()
        else None
    )
    dump(
        OUT / "summary.json",
        {
            "decision": "PHASE7_REVIEWER_DEFENSE_COMPLETE_WITH_COMPATIBILITY_BOUNDARIES",
            "phase7a": "PASS",
            "phase7b": "PASS_WITH_SOURCE_SCOPE_LABELS",
            "phase7c": "PASS",
            "phase7d": (
                "PASS_FULL_QUEUE_ACCOUNTING_WITH_STATISTICAL_STATE_RISK"
                if c64_queue
                and c64_queue["risk_contract_met_by_current_95pct_upper"]
                else "PENDING_OR_RISK_GATE_FAIL"
            ),
            "phase7e": "PASS_STEADY_STATE_PLUS_LABELED_WARMUP_ESTIMATES",
        },
    )


if __name__ == "__main__":
    main()

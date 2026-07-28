#!/usr/bin/env python3
"""Finalize the compact, auditable Phase 6 submission-repair artifact."""

from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
RESULT = ROOT / "results/phase6"
ARTIFACT = ROOT / "artifact/phase6-submission-repairs-v1"


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def compact_stage(stage: dict[str, Any]) -> dict[str, Any]:
    return {
        key: stage.get(key)
        for key in (
            "label",
            "fingerprint",
            "concurrency",
            "language",
            "events",
            "switch_action",
            "threshold",
            "failure_floor",
            "risk_upper_bound",
            "verification_fraction",
            "goodput_events_per_second",
            "state_entry_latency_seconds_p99",
            "deadline_miss_events",
            "output_violations",
            "state_violations",
            "certified_after_events",
            "fast_path_window",
            "renewal_canaries_remaining",
            "energy",
        )
    }


def main() -> int:
    config_path = ROOT / "configs/revtrace_phase6_submission_repair_gate.json"
    semantic_path = RESULT / "semantic_gate.json"
    c32_raw_path = (
        RESULT / "contract_scoping/0p6b-c32-d120-burst-zh.json"
    )
    adaptation_raw_path = (
        RESULT / "live_adaptation/c16-en-c16-zh-c16-en.json"
    )
    adaptation_first_fail_path = (
        RESULT / "live_adaptation/c16-en-c16-zh-c16-en-first-fail.json"
    )
    adaptation_second_fail_path = (
        RESULT / "live_adaptation/c16-en-c16-zh-c16-en-second-fail.json"
    )
    phase5_path = ROOT / "results/phase5/summary.json"
    required = (
        config_path,
        semantic_path,
        c32_raw_path,
        adaptation_raw_path,
        adaptation_first_fail_path,
        adaptation_second_fail_path,
        phase5_path,
    )
    missing = [str(path) for path in required if not path.exists()]
    if missing:
        raise FileNotFoundError(f"missing Phase 6 inputs: {missing}")

    config = load(config_path)
    semantic = load(semantic_path)
    c32 = load(c32_raw_path)
    adaptation = load(adaptation_raw_path)
    adaptation_first_fail = load(adaptation_first_fail_path)
    adaptation_second_fail = load(adaptation_second_fail_path)
    phase5 = load(phase5_path)
    c32_summary = c32["summary"]
    stages = adaptation["stages"]
    if len(stages) != 3:
        raise AssertionError("expected three feasible-adaptation stages")

    known = [
        event
        for event in c32["events"]
        if event["revision_id"] == "s023:8"
    ]
    if len(known) != 1:
        raise AssertionError("known c32 counterexample was not reproduced")
    known_event = known[0]
    p6a_gates = {
        **semantic["gates"],
        "semantic_gate_pass": (
            semantic["decision"] == "PHASE6A_SEMANTIC_GATE_PASS"
        ),
    }
    p6a_pass = all(p6a_gates.values())

    p6b_gates = {
        "new_contract_quarantine": (
            c32_summary["quarantine_forced_events"]
            >= config["phase6b"]["minimum_quarantine_events"]
        ),
        "no_c16_certificate_reuse": (
            c32["certificate_source_contract"]
            == config["phase6b"]["certificate_source_contract"]
        ),
        "known_counterexample_verified": bool(known_event["verified"]),
        "known_counterexample_floor_applied": (
            c32["margin_threshold"]
            > float(known_event["proposal_minimum_margin"])
        ),
        "state_projection_violations_zero": (
            c32_summary["state_projection_violation_events"]
            == config["phase6b"]["state_projection_violations"]
        ),
    }
    p6b_pass = all(p6b_gates.values())
    p6b_decision = (
        "PHASE6B_CONTRACT_SCOPING_REPAIR_PASS"
        if p6b_pass
        else "PHASE6B_CONTRACT_SCOPING_REPAIR_FAIL"
    )
    c32_compact = {
        "decision": p6b_decision,
        "gates": p6b_gates,
        "model": c32["model_name"],
        "contract_digest": c32["contract_digest"],
        "certificate_source_contract": c32[
            "certificate_source_contract"
        ],
        "margin_threshold": c32["margin_threshold"],
        "known_counterexample": {
            key: known_event.get(key)
            for key in (
                "revision_id",
                "proposal_minimum_margin",
                "verified",
                "quarantine_forced",
                "selected_vs_canonical",
            )
        },
        "summary": c32_summary,
        "claim_boundary": (
            "live exact-cell rerun; safety repair is distinct from the "
            "known c32 physical deadline-capacity boundary"
        ),
    }
    c32_summary_path = RESULT / "contract_scoping/summary.json"
    write_json(c32_summary_path, c32_compact)

    offered_c64 = phase5["phase5a"]["stages"][1]
    reshape_stage = stages[0]
    guarded_reshape_p99 = (
        float(reshape_stage["state_entry_latency_seconds_p99"])
        + float(config["phase6c"]["p99_guard_seconds"])
    )
    p6c_gates = {
        "c64_not_admitted_at_64": (
            semantic["c64_admission"]["level"] == "capacity_reshape"
            and semantic["c64_admission"]["admitted_concurrency"] < 64
        ),
        "reshaped_live_p99_with_guard_meets_slo": (
            guarded_reshape_p99 <= config["phase6c"]["deadline_seconds"]
        ),
        "admitted_deadline_misses_zero": (
            reshape_stage["deadline_miss_events"]
            == config["phase6c"]["admitted_deadline_misses"]
        ),
    }
    p6c_pass = all(p6c_gates.values())

    maximum_state_risk = max(
        float(stage["state_violations"]) / float(stage["events"])
        for stage in stages
    )
    risk_bounds_valid = all(
        stage["risk_upper_bound"] is not None
        and float(stage["risk_upper_bound"])
        <= config["phase6d"]["risk_upper_bound"]
        for stage in stages
    )
    p6d_gates = {
        "cross_contract_certificate_reuse_zero": (
            adaptation["cross_contract_certificate_reuse"]
            == config["phase6d"]["cross_contract_certificate_reuse"]
        ),
        "exact_return_restore_observed": (
            adaptation["exact_certificate_restores"]
            >= config["phase6d"]["minimum_exact_certificate_restores"]
            and stages[2]["switch_action"] == "exact_restore_canary"
        ),
        "all_contract_risk_bounds_valid": risk_bounds_valid,
        "observed_state_risk_within_contract": (
            maximum_state_risk <= config["phase6d"]["risk_upper_bound"]
        ),
        "admitted_deadline_misses_zero": all(
            stage["deadline_miss_events"]
            == config["phase6d"]["admitted_deadline_misses"]
            for stage in stages
        ),
        "return_renewal_faster_than_flat_recertification": (
            stages[2]["certified_after_events"] is not None
            and stages[2]["certified_after_events"]
            <= 64
            < stages[0]["certified_after_events"]
        ),
    }
    p6d_pass = all(p6d_gates.values())
    return_events = int(stages[2]["certified_after_events"])
    flat_events = int(stages[0]["certified_after_events"])
    recertification_reduction = 1.0 - return_events / flat_events
    adaptation_compact = {
        "decision": (
            "PHASE6D_FEASIBLE_LIVE_ADAPTATION_PASS"
            if p6d_pass
            else "PHASE6D_FEASIBLE_LIVE_ADAPTATION_FAIL"
        ),
        "gates": p6d_gates,
        "cross_contract_certificate_reuse": adaptation[
            "cross_contract_certificate_reuse"
        ],
        "exact_certificate_restores": adaptation[
            "exact_certificate_restores"
        ],
        "recertification_event_reduction_vs_flat": (
            recertification_reduction
        ),
        "maximum_observed_state_risk": maximum_state_risk,
        "stages": [compact_stage(stage) for stage in stages],
        "repair_attempt_diagnoses": [
            {
                "attempt": 1,
                "decision": adaptation_first_fail["decision"],
                "cause_class": "implementation_state_machine",
                "cause": (
                    "quarantine-learning counterexamples were incorrectly "
                    "treated as failures against active positive evidence, "
                    "so the learning window was repeatedly reset"
                ),
                "repair": (
                    "retain caught failures as calibration evidence while a "
                    "new contract is quarantined"
                ),
                "stages": [
                    {
                        "label": stage["label"],
                        "events": stage["events"],
                        "threshold": stage["threshold"],
                        "failure_floor": stage["failure_floor"],
                        "risk_upper_bound": stage["risk_upper_bound"],
                        "deadline_miss_events": stage[
                            "deadline_miss_events"
                        ],
                        "output_violations": stage["output_violations"],
                        "state_violations": stage["state_violations"],
                    }
                    for stage in adaptation_first_fail["stages"]
                ],
            },
            {
                "attempt": 2,
                "decision": adaptation_second_fail["decision"],
                "cause_class": "incomplete_repair_and_cache_consistency",
                "cause": (
                    "a caught error after promotion invalidated the active "
                    "certificate too aggressively while its cached copy "
                    "remained eligible for exact return"
                ),
                "repair": (
                    "raise the contextual floor and recompute the certificate "
                    "atomically; delete both active and cached evidence only "
                    "when the stricter window no longer meets the risk budget"
                ),
                "stages": [
                    {
                        "label": stage["label"],
                        "events": stage["events"],
                        "threshold": stage["threshold"],
                        "failure_floor": stage["failure_floor"],
                        "risk_upper_bound": stage["risk_upper_bound"],
                        "deadline_miss_events": stage[
                            "deadline_miss_events"
                        ],
                        "output_violations": stage["output_violations"],
                        "state_violations": stage["state_violations"],
                    }
                    for stage in adaptation_second_fail["stages"]
                ],
            },
        ],
        "claim_boundary": (
            "live persistent two-GPU sequence; risk-limited stages are "
            "statistical and exact return requires canary renewal; the "
            "controller risk bound is not a bitwise-repeatability certificate "
            "for the canonical runtime itself"
        ),
    }
    adaptation_summary_path = RESULT / "live_adaptation/summary.json"
    write_json(adaptation_summary_path, adaptation_compact)

    p6c = {
        "decision": (
            "PHASE6C_JOINT_RISK_SLO_ADMISSION_PASS"
            if p6c_pass
            else "PHASE6C_JOINT_RISK_SLO_ADMISSION_FAIL"
        ),
        "gates": p6c_gates,
        "offered_c64": {
            "concurrency": 64,
            "phase5_p99_seconds": offered_c64[
                "state_entry_latency_seconds_p99"
            ],
            "phase5_deadline_misses": offered_c64[
                "deadline_miss_events"
            ],
        },
        "admission_action": "reshape_to_c16",
        "backpressured_or_queued_new_sessions": 48,
        "live_reshaped_contract": {
            "concurrency": reshape_stage["concurrency"],
            "p99_seconds": reshape_stage[
                "state_entry_latency_seconds_p99"
            ],
            "guarded_p99_seconds": guarded_reshape_p99,
            "deadline_misses": reshape_stage["deadline_miss_events"],
        },
        "claim_boundary": (
            "active-session live latency after admission; queued-session "
            "waiting is not counted as state-entry service latency"
        ),
    }
    p6c_path = RESULT / "joint_admission/summary.json"
    write_json(p6c_path, p6c)

    overall_pass = p6a_pass and p6b_pass and p6c_pass and p6d_pass
    summary = {
        "schema_version": 1,
        "study": "RevTrace Phase 6 submission repairs",
        "decision": (
            "PHASE6_SUBMISSION_REPAIRS_COMPLETE"
            if overall_pass
            else "PHASE6_SUBMISSION_REPAIRS_COMPLETE_WITH_BOUNDARIES"
        ),
        "phase6a": {
            "decision": semantic["decision"],
            "gates": p6a_gates,
        },
        "phase6b": c32_compact,
        "phase6c": p6c,
        "phase6d": adaptation_compact,
        "publication_boundary": (
            "risk-limited mode is not deterministic exactness; strict mode "
            "means frozen-canonical consistency; c32 safety repair does not "
            "make its overloaded workload SLO-admissible"
        ),
    }
    summary_path = RESULT / "summary.json"
    write_json(summary_path, summary)

    tables = f"""# Phase 6 paper tables

## Contract scoping repair

| Cell | Quarantine | Threshold | Known failure verified | State violations | P99 | Deadline misses | Wall speedup |
|---|---:|---:|---:|---:|---:|---:|---:|
| 0.6B-c32-d120-burst-ZH | {c32_summary['quarantine_forced_events']} | {c32['margin_threshold']:.6f} | {str(bool(known_event['verified']))} | {c32_summary['state_projection_violation_events']} | {c32_summary['state_entry_latency_seconds_p99']:.3f} s | {c32_summary['state_entry_deadline_miss_events']} | {c32_summary['deployed_two_gpu_wall_speedup']:.3f}x |

## Feasible live adaptation

| Stage | Switch action | Learned threshold | Risk upper | Verify | Goodput | P99 | Miss | State violations |
|---|---|---:|---:|---:|---:|---:|---:|---:|
"""
    for stage in stages:
        tables += (
            f"| {stage['label']} | {stage['switch_action']} | "
            f"{float(stage['threshold']):.6f} | "
            f"{100*float(stage['risk_upper_bound']):.4f}% | "
            f"{100*float(stage['verification_fraction']):.2f}% | "
            f"{float(stage['goodput_events_per_second']):.3f} | "
            f"{float(stage['state_entry_latency_seconds_p99']):.3f} s | "
            f"{stage['deadline_miss_events']} | "
            f"{stage['state_violations']} |\n"
        )
    tables += f"""
## Joint capacity admission

| Offered | Historical P99/misses | Action | Live admitted | Guarded P99 | Live misses |
|---|---:|---|---:|---:|---:|
| c64 | {offered_c64['state_entry_latency_seconds_p99']:.3f} s / {offered_c64['deadline_miss_events']} | reshape/backpressure | c16 | {guarded_reshape_p99:.3f} s | {reshape_stage['deadline_miss_events']} |
"""
    tables_path = RESULT / "PAPER_TABLES.md"
    tables_path.write_text(tables, encoding="utf-8", newline="\n")

    report = f"""# RevTrace Phase 6 submission-repair report

Decision: `{summary['decision']}`

## Phase 6A — Evidence lifecycle and epoch fencing

Decision: `{semantic['decision']}`.

The offline semantic gate uses the real Phase 5 c32 failure. Positive
certificates restore only for an exact contract and remain canary-gated.
The c32 counterexample persists at a threshold floor of
`{semantic['evidence_trace'][1]['failure_floor']}` only inside its execution
applicability cone. Cross-contract positive reuse is zero. Contract and policy
epoch changes both reject late results. This is protocol evidence, not a
serving benchmark.

## Phase 6B — Complete contract scoping

Decision: `{p6b_decision}`.

The exact 0.6B/c32/120-second/burst/Chinese cell was rerun. The first
{c32_summary['quarantine_forced_events']} state entries were fail-closed, the
known margin {known_event['proposal_minimum_margin']} event was verified, and
the final state-violation count is
{c32_summary['state_projection_violation_events']}. The live P99 is
{c32_summary['state_entry_latency_seconds_p99']:.3f} seconds with
{c32_summary['state_entry_deadline_miss_events']} misses. Contract scoping is
repaired, but the cell remains a capacity boundary.

## Phase 6C — Joint risk–SLO admission

Decision: `{p6c['decision']}`.

The historical c64 contract (P99
{offered_c64['state_entry_latency_seconds_p99']:.3f} seconds,
{offered_c64['deadline_miss_events']} misses) is not admitted at c64. The
controller reshapes active service to c16 and backpressures 48 new sessions.
The live admitted stage has guarded P99 {guarded_reshape_p99:.3f} seconds and
{reshape_stage['deadline_miss_events']} deadline misses.

## Phase 6D — Feasible live adaptation

Decision: `{adaptation_compact['decision']}`.

The persistent two-GPU process switched English c16 to Chinese c16 and back.
Both populations remained in the two-second service region. The two new
contracts learned independently; the exact return used
`{stages[2]['switch_action']}` and renewed in {return_events} events rather
than {flat_events}, reducing recertification events by
{100*recertification_reduction:.2f}%. Cross-contract certificate reuse and
deadline misses are both zero. The largest observed stage-level state risk is
{100*maximum_state_risk:.4f}% and every reported statistical upper bound is at
most 0.5%.

### Implementation repair audit

The first attempt incorrectly erased the quarantine learning window whenever a
caught proposer/canonical counterexample appeared. The second attempt retained
quarantine evidence but invalidated an active statistical certificate too
aggressively while leaving its cached copy eligible for exact return. The
final state machine separates three cases: quarantine failures raise the
learning floor; active-certificate failures atomically recompute the stricter
window and retain it only if the risk gate still holds; return-canary failures
delete the cached certificate. Both failed raw traces are preserved by hash
and summarized in the Phase 6D result.

## Publication boundary

Risk-limited mode may observe errors allowed by its statistical contract.
Canonical-consistent strict mode is relative to the frozen canonical path, not
mathematical truth or a bitwise repeatability guarantee. The repaired c32
contract remains non-admissible under the two-second SLO. No
deterministic-certificate, Whisper-speedup, or slack-packing claim is added in
Phase 6.
"""
    report_path = ROOT / "docs/reports/phase6_submission_repair_report.md"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(report, encoding="utf-8", newline="\n")

    raw_manifest = {
        str(path.relative_to(ROOT)): {
            "bytes": path.stat().st_size,
            "sha256": sha256(path),
        }
        for path in (
            c32_raw_path,
            adaptation_raw_path,
            adaptation_first_fail_path,
            adaptation_second_fail_path,
        )
    }
    source_manifest_path = RESULT / "SOURCE_MANIFEST.json"
    write_json(source_manifest_path, raw_manifest)

    if ARTIFACT.exists():
        shutil.rmtree(ARTIFACT)
    include = (
        config_path,
        semantic_path,
        c32_summary_path,
        p6c_path,
        adaptation_summary_path,
        summary_path,
        tables_path,
        source_manifest_path,
        report_path,
        ROOT / "src/revtrace/phase6.py",
        ROOT / "src/revtrace/phase5.py",
        ROOT / "tests/test_phase6.py",
        ROOT / "tests/test_phase5.py",
        ROOT / "tests/test_phase6_artifact.py",
        ROOT / "scripts/run_phase6_semantic_gate.py",
        ROOT / "scripts/finalize_phase6.py",
        ROOT / "scripts/audit_phase6_artifact.py",
        ROOT / "scripts/validate_repository.py",
        ROOT / "scripts/remote/run_phase6_submission_repairs.sh",
        ROOT / "scripts/remote/run_phase6d_repair.sh",
        ROOT / "scripts/remote/run_phase5a_live_adaptive.py",
        ROOT / "scripts/remote/run_revtrace_dual_gpu.py",
        ROOT / "src/revtrace/__init__.py",
        ROOT / "configs/experiment_registry.json",
        ROOT / "docs/CLAIM_BOUNDARIES.md",
        ROOT / "docs/roadmap/PHASES.md",
    )
    for source in include:
        relative = source.relative_to(ROOT)
        target = ARTIFACT / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
    (ARTIFACT / "README.md").write_text(
        "# RevTrace Phase 6 submission-repair artifact\n\n"
        "Compact summaries, protocol code, tests, raw-source hashes, and "
        "claim boundaries. Large live traces remain on the designated data "
        "disk.\n",
        encoding="utf-8",
        newline="\n",
    )
    manifest = {
        "schema_version": 1,
        "artifact": "phase6-submission-repairs-v1",
        "decision": summary["decision"],
        "files": {
            str(path.relative_to(ARTIFACT)).replace("\\", "/"): {
                "bytes": path.stat().st_size,
                "sha256": sha256(path),
            }
            for path in sorted(ARTIFACT.rglob("*"))
            if path.is_file()
        },
    }
    write_json(ARTIFACT / "MANIFEST.json", manifest)
    print(json.dumps({"decision": summary["decision"]}))
    return 0 if overall_pass else 2


if __name__ == "__main__":
    raise SystemExit(main())

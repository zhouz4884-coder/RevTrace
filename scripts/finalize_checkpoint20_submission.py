#!/usr/bin/env python3
"""Fail-closed submission finalizer for the checkpoint-20 holdback mechanism."""

from __future__ import annotations

import argparse
import csv
import json
import statistics
import sys
from pathlib import Path
from typing import Any


SEEDS = (20260840, 20260841, 20260842, 20260843, 20260844)
REQUIRED_BINDINGS = {
    "calibration",
    "formal_risk_audit",
    "semantic_integration",
    "deployed_quality",
    "identity_extension",
    "resume_lineage",
    "continuous_provisional_ux",
    "quality_dependency",
    *(f"live_seed_{seed}" for seed in SEEDS),
}


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
        default=Path("docs/reports/checkpoint20_submission_closure.md"),
    )
    return parser.parse_args()


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def heldout(payload: dict[str, Any]) -> dict[str, Any]:
    rows = [row for row in payload["stages"] if row["label"] == "heldout"]
    if len(rows) != 1:
        raise ValueError("expected one heldout stage")
    return rows[0]


def pct(value: float) -> str:
    return f"{100 * value:.3f}%"


def main() -> int:
    args = parse_args()
    root = args.results_dir.resolve()
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
    from revtrace.contract_manifest import sha256_file, validate_binding

    contract_path = root / "contract_manifest.json"
    binding_path = root / "contract_bindings.json"
    contract = load(contract_path)
    bindings = load(binding_path)
    mechanism_digest = contract["mechanism_digest"]
    if bindings["mechanism_digest"] != mechanism_digest:
        raise ValueError("binding set uses a different mechanism digest")
    if set(bindings["bindings"]) != REQUIRED_BINDINGS:
        missing = REQUIRED_BINDINGS - set(bindings["bindings"])
        extra = set(bindings["bindings"]) - REQUIRED_BINDINGS
        raise ValueError(f"binding role mismatch missing={missing} extra={extra}")
    if bindings["contract_manifest"]["sha256"] != sha256_file(contract_path):
        raise ValueError("contract manifest changed after evidence binding")
    for name, binding in bindings["bindings"].items():
        if binding["mechanism_digest"] != mechanism_digest:
            raise ValueError(f"{name} uses a different mechanism")
        validate_binding(
            binding,
            raw_path=(Path.cwd() / binding["path"]).resolve(),
        )

    calibration = heldout(load(root / "calibration.json"))
    risk = load(root / "anytime_risk_audit.json")
    semantics = load(root / "holdback_semantics_gate.json")
    quality = load(root / "deployed_b12_quality_32x2.json")
    identity = load(root / "deployment_identity_v2.json")
    resume = load(root / "resume_quality_attestation.json")
    ux_audit = load(root / "provisional_experience_audit.json")
    dependency = load(root / "quality_dependency_audit.json")
    threshold = float(contract["mechanism"]["risk_policy"]["minimum_margin_threshold"])
    seed_rows: list[dict[str, Any]] = []
    for seed in SEEDS:
        stage = heldout(load(root / f"seed_{seed}.json"))
        checkpoint_rounds = sum(
            bool(row["checkpoint_boundary"])
            for row in stage["rounds_detail"]
        )
        checkpoint_events = checkpoint_rounds * int(stage["concurrency"])
        holdbacks = sum(
            int(row.get("holdback_count", 0))
            for row in stage["rounds_detail"]
        )
        synchronous_low_margin_verifications = sum(
            int(row.get("verified_count", 0))
            for row in stage["rounds_detail"]
            if not row["checkpoint_boundary"]
        )
        revision_opportunities = int(stage["events"])
        seed_rows.append(
            {
                "seed": seed,
                "revision_opportunities": revision_opportunities,
                "committed_state_transitions": (
                    revision_opportunities - holdbacks
                ),
                "p50_seconds": float(stage["state_entry_latency_seconds_p50"]),
                "p95_seconds": float(stage["state_entry_latency_seconds_p95"]),
                "p99_seconds": float(stage["state_entry_latency_seconds_p99"]),
                "deadline_miss_events": int(stage["deadline_miss_events"]),
                "authority_checkpoint_fraction": (
                    checkpoint_events / revision_opportunities
                ),
                "recorded_verification_fraction": float(
                    stage["verification_fraction"]
                ),
                "synchronous_low_margin_verifications": (
                    synchronous_low_margin_verifications
                ),
                "holdbacks": holdbacks,
                "provisional_holdback_fraction": (
                    holdbacks
                    / max(1, revision_opportunities - checkpoint_events)
                ),
                "authority_violations": int(
                    stage["online_selection_authority_violations"]
                ),
                "joules_per_audio_second": float(
                    stage["energy"]["joules_per_audio_second"]
                ),
            }
        )

    checks = {
        "shared_content_addressed_contract": True,
        "calibration": bool(
            abs(float(calibration["threshold"]) - threshold) <= 1e-12
            and float(calibration["risk_upper_bound"]) <= 0.005
            and int(calibration["online_selection_authority_violations"]) == 0
        ),
        "time_uniform_state_risk": bool(
            risk["decision"] == "CHECKPOINT_ANYTIME_RISK_PASS"
            and int(risk["counts"]["risk_eligible_state_entries"]) >= 30_000
            and int(risk["counts"]["selected_authority_violations"]) == 0
            and float(risk["risk_certificate"]["upper_risk"]) <= 0.005
        ),
        "five_seed_tail": bool(
            max(row["p99_seconds"] for row in seed_rows) <= 1.9
            and sum(row["deadline_miss_events"] for row in seed_rows) == 0
            and sum(row["authority_violations"] for row in seed_rows) == 0
        ),
        "five_seed_event_accounting": bool(
            sum(row["revision_opportunities"] for row in seed_rows) == 3_600
            and sum(
                row["committed_state_transitions"] for row in seed_rows
            )
            == 3_539
            and sum(row["holdbacks"] for row in seed_rows) == 61
            and all(
                abs(
                    row["authority_checkpoint_fraction"]
                    - row["recorded_verification_fraction"]
                )
                <= 1e-12
                for row in seed_rows
            )
            and sum(
                row["synchronous_low_margin_verifications"]
                for row in seed_rows
            )
            == 0
        ),
        "holdback_semantics": semantics["decision"] == "HOLDBACK_SEMANTICS_PASS",
        "deployed_b12_quality": bool(
            quality["decision"] == "OBSERVED_QUALITY_TOLERANCE_PASS"
            and int(quality["deployment"]["sessions_per_language"]) >= 16
            and all(
                int(row["catastrophic_outliers"]) == 0
                for row in quality["language_metrics"].values()
            )
        ),
        "provisional_lifetime_bound": bool(
            quality["provisional_experience"]["lifetime_bound_pass"]
        ),
        "resume_lineage": bool(
            resume["decision"] == "RESUME_QUALITY_ATTESTATION_PASS"
            and all(resume["checks"].values())
            and all(resume["reused_transcript_checks"].values())
        ),
        "continuous_provisional_ux": bool(
            ux_audit["decision"] == "CONTINUOUS_PROVISIONAL_UX_AUDIT_PASS"
            and float(
                ux_audit["audit"][
                    "empty_provisional_overwrite_boundary"
                ]
            )
            == 0.0
            and int(ux_audit["audit"]["transition_counts"]["all"])
            == int(ux_audit["audit"]["holdback_events"])
        ),
        "quality_dependence_documented": bool(
            dependency["decision"] == "QUALITY_DEPENDENCE_AUDIT_COMPLETE"
            and dependency["audit"]["cross_session_source_dependence"]
        ),
        "artifact_identity_extension": bool(
            int(identity["schema_version"]) == 2
            and identity["data_manifest_sha256"]
            == contract["mechanism"]["data"]["manifest_sha256"]
            and identity["model_fingerprint"]["content_digest"]
            == contract["mechanism"]["model"]["fingerprint"][
                "content_digest"
            ]
            and identity["authority_runtime_sha256"]
            == contract["mechanism"]["authority"]["runtime_sha256"]
        ),
    }
    passed = all(checks.values())
    quality_rows = []
    for language, row in quality["language_metrics"].items():
        quality_rows.append(
            {
                "language": language,
                "metric": row["metric"],
                "sessions": int(row["sessions"]),
                "continuous": float(row["continuous_error_rate_mean"]),
                "checkpoint_verify": float(
                    row["checkpoint_verify_error_rate_mean"]
                ),
                "checkpoint_holdback": float(
                    row["checkpoint_holdback_error_rate_mean"]
                ),
                "checkpoint_delta": float(
                    row["components"]["checkpoint_delta"]["observed_mean_delta"]
                ),
                "holdback_incremental_delta": float(
                    row["components"]["holdback_incremental_delta"][
                        "observed_mean_delta"
                    ]
                ),
                "holdback_incremental_ci_low": float(
                    row["components"]["holdback_incremental_delta"][
                        "ci95_low"
                    ]
                ),
                "holdback_incremental_ci_high": float(
                    row["components"]["holdback_incremental_delta"][
                        "ci95_high"
                    ]
                ),
                "total_delta": float(
                    row["components"]["total_delta"]["observed_mean_delta"]
                ),
                "total_ci_low": float(
                    row["components"]["total_delta"]["ci95_low"]
                ),
                "total_ci_high": float(
                    row["components"]["total_delta"]["ci95_high"]
                ),
                "catastrophic": int(row["catastrophic_outliers"]),
            }
        )

    evidence_paths = {
        "contract_manifest": contract_path,
        "contract_bindings": binding_path,
        "deployment_identity": root / "deployment_identity.json",
        "deployment_identity_v2": root / "deployment_identity_v2.json",
        "calibration": root / "calibration.json",
        "formal_risk_audit": root / "anytime_risk_audit.json",
        "holdback_semantics": root / "holdback_semantics_gate.json",
        "deployed_quality": root / "deployed_b12_quality_32x2.json",
        "resume_quality_attestation": root
        / "resume_quality_attestation.json",
        "provisional_experience_audit": root
        / "provisional_experience_audit.json",
        "quality_dependency_audit": root / "quality_dependency_audit.json",
        **{f"seed_{seed}": root / f"seed_{seed}.json" for seed in SEEDS},
    }
    implementation_paths = {
        "contract_library": Path("src/revtrace/contract_manifest.py").resolve(),
        "holdback_semantics": Path("src/revtrace/long_horizon.py").resolve(),
        "live_runner": Path(
            "scripts/remote/run_phase5a_live_adaptive.py"
        ).resolve(),
        "risk_runner": Path(
            "scripts/remote/run_checkpoint_dual_lane_shadow_audit.py"
        ).resolve(),
        "semantic_runner": Path(
            "scripts/remote/run_holdback_semantics_gate.py"
        ).resolve(),
        "deployed_quality_runner": Path(
            "scripts/remote/run_deployed_checkpoint20_quality.py"
        ).resolve(),
        "binding_builder": Path(
            "scripts/bind_checkpoint20_evidence.py"
        ).resolve(),
        "offline_evidence_auditor": Path(
            "scripts/audit_checkpoint20_submission_evidence.py"
        ).resolve(),
        "evidence_audit_library": Path(
            "src/revtrace/evidence_audit.py"
        ).resolve(),
        "provenance_library": Path("src/revtrace/provenance.py").resolve(),
        "finalizer": Path(__file__).resolve(),
    }
    ux = quality["provisional_experience"]
    summary = {
        "schema_version": 3,
        "study": "checkpoint20_submission_evidence_closure",
        "decision": (
            "REVTRACE_EXPERIMENTAL_EVIDENCE_COMPLETE_FOR_FGCS_SUBMISSION"
            if passed
            else "REVTRACE_EXPERIMENTAL_EVIDENCE_INCOMPLETE"
        ),
        "mechanism_digest": mechanism_digest,
        "selected_contract": (
            "fp16_ordinary_b12_proposer__low_margin_provisional_holdback__"
            "fp16_batch_invariant_fixed_b12_checkpoint_authority"
        ),
        "gate_checks": checks,
        "quality_decisions": {
            "observed": quality["decision"],
            "population": quality["population_decision"],
        },
        "risk_certificate": risk["risk_certificate"],
        "five_seed": {
            "revision_opportunities": sum(
                row["revision_opportunities"] for row in seed_rows
            ),
            "committed_state_transitions": sum(
                row["committed_state_transitions"] for row in seed_rows
            ),
            "provisional_holdbacks": sum(
                row["holdbacks"] for row in seed_rows
            ),
            "maximum_p99_seconds": max(row["p99_seconds"] for row in seed_rows),
            "mean_p99_seconds": statistics.mean(
                row["p99_seconds"] for row in seed_rows
            ),
            "total_deadline_misses": sum(
                row["deadline_miss_events"] for row in seed_rows
            ),
            "mean_joules_per_audio_second": statistics.mean(
                row["joules_per_audio_second"] for row in seed_rows
            ),
            "rows": seed_rows,
        },
        "deployed_quality": quality_rows,
        "provisional_experience": {
            key: value for key, value in ux.items() if key != "events"
        },
        "continuous_provisional_experience": {
            key: value
            for key, value in ux_audit["audit"].items()
            if key not in {"episodes", "per_session"}
        },
        "quality_dependency": dependency["audit"],
        "resume_lineage": {
            key: value
            for key, value in resume.items()
            if key != "identity_source_checks"
        },
        "artifact_identity_extension": {
            "identity_extension_digest": identity[
                "identity_extension_digest"
            ],
            "audio_file_count": identity["data_content"][
                "audio_file_count"
            ],
            "audio_content_digest": identity["data_content"][
                "content_digest"
            ],
            "gpu_identity": identity["environment"]["gpu_identity"],
            "software": identity["environment"]["software"],
            "claim_boundary": identity["claim_boundary"],
        },
        "runner_provenance": {
            name: binding["execution_profile"]["source_provenance"]
            for name, binding in bindings["bindings"].items()
        },
        "semantic_patterns": semantics["patterns"],
        "excluded_mechanisms": bindings["excluded_evidence"],
        "evidence_sha256": {
            name: {
                "path": path.relative_to(Path.cwd().resolve()).as_posix(),
                "sha256": sha256_file(path),
            }
            for name, path in evidence_paths.items()
        },
        "current_reproduction_implementation_sha256": {
            name: {
                "path": path.relative_to(Path.cwd().resolve()).as_posix(),
                "sha256": sha256_file(path),
            }
            for name, path in implementation_paths.items()
        },
        "claim_boundaries": [
            "The observed quality tolerance gate passed only if the paired sample mean delta stayed within 2 percentage points with no catastrophic outlier.",
            "Population noninferiority is unresolved unless the paired bootstrap upper bound is also at most 2 percentage points.",
            "The time-uniform risk statement concerns admitted state entries; margin is not a deterministic arithmetic certificate.",
            "Provisional experience statistics describe this frozen natural workload, not production prevalence.",
            "The paired bootstrap resamples fixed constructed sessions; cross-session source reuse prevents interpreting it as an independent-source population interval.",
            "The identity extension is a post-run content attestation and does not retroactively alter the frozen mechanism digest.",
            "Live seed runner source is a retrospectively frozen repository snapshot because those raw JSON files did not embed a runner SHA; quality and semantic runners have at-run SHA provenance.",
            "Legacy B=8 quality and the B=2 or dual-lane NO-GO branches are excluded from the selected contract.",
        ],
    }
    output = root / "final_summary_v2.json"
    output.write_text(
        json.dumps(summary, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    csv_path = root / "deployed_quality_summary.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(quality_rows[0]))
        writer.writeheader()
        writer.writerows(quality_rows)

    lines = [
        "# Checkpoint-20 submission evidence closure",
        "",
        f"Decision: **{summary['decision']}**",
        "",
        f"Mechanism digest: `{mechanism_digest}`",
        "",
        "## Contract and semantics",
        "",
        "- All calibration, risk, five-seed service, semantic, and deployed-quality artifacts are content-addressed under one mechanism digest.",
        f"- Holdback semantic patterns: {len(semantics['patterns'])}/5 passed.",
        "- Fixed authority: GPU 1 FP16 batch-invariant B=12; proposer: GPU 0 ordinary FP16 B=12.",
        "",
        "## Five-seed service",
        "",
        f"- Five seeds contain {summary['five_seed']['revision_opportunities']} revision opportunities, {summary['five_seed']['committed_state_transitions']} committed state transitions, and {summary['five_seed']['provisional_holdbacks']} provisional holdbacks.",
        "- The recorded 10% verification field is exactly the fixed checkpoint-authority fraction (6 of 60 rounds); synchronous low-margin verification is zero under holdback.",
        "",
        "| Seed | P50 | P95 | P99 | misses | checkpoint authority | sync low-margin verify | holdbacks | holdback rate | J/audio-s |",
        "|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in seed_rows:
        lines.append(
            f"| {row['seed']} | {row['p50_seconds']:.3f} | "
            f"{row['p95_seconds']:.3f} | {row['p99_seconds']:.3f} | "
            f"{row['deadline_miss_events']} | "
            f"{pct(row['authority_checkpoint_fraction'])} | "
            f"{row['synchronous_low_margin_verifications']} | "
            f"{row['holdbacks']} | "
            f"{pct(row['provisional_holdback_fraction'])} | "
            f"{row['joules_per_audio_second']:.3f} |"
        )
    lines.extend(
        [
            "",
            "## Deployed B=12 paired quality",
            "",
            "| Language | n | continuous | checkpoint+verify | checkpoint+holdback | checkpoint delta | holdback incremental | incremental 95% CI | total delta | total 95% CI | catastrophic |",
            "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for row in quality_rows:
        lines.append(
            f"| {row['language']} ({row['metric'].upper()}) | {row['sessions']} | "
            f"{pct(row['continuous'])} | {pct(row['checkpoint_verify'])} | "
            f"{pct(row['checkpoint_holdback'])} | {pct(row['checkpoint_delta'])} | "
            f"{pct(row['holdback_incremental_delta'])} | "
            f"[{pct(row['holdback_incremental_ci_low'])}, "
            f"{pct(row['holdback_incremental_ci_high'])}] | "
            f"{pct(row['total_delta'])} | "
            f"[{pct(row['total_ci_low'])}, {pct(row['total_ci_high'])}] | "
            f"{row['catastrophic']} |"
        )
    lines.extend(
        [
            "",
            f"- Observed quality: **{quality['decision']}**.",
            f"- Population statement: **{quality['population_decision']}**.",
            "",
            "## Provisional experience",
            "",
            f"- Holdbacks: {ux['holdback_events']} ({pct(ux['holdback_rate'])}).",
            f"- Resolved by next high-margin update: {ux['resolution_counts']['next_high_margin']}; by checkpoint authority: {ux['resolution_counts']['checkpoint_authority']}.",
            f"- Provisional lifetime P50/P95/max: {ux['lifetime_seconds']['p50']:.2f}/{ux['lifetime_seconds']['p95']:.2f}/{ux['lifetime_seconds']['maximum']:.2f} s.",
            f"- Displayed-text overwrite mean/P50/P95/max: "
            f"{pct(ux['provisional_overwrite_fraction']['mean'])}/"
            f"{pct(ux['provisional_overwrite_fraction']['p50'])}/"
            f"{pct(ux['provisional_overwrite_fraction']['p95'])}/"
            f"{pct(ux['provisional_overwrite_fraction']['maximum'])}.",
            f"- Zero-overwrite resolutions: "
            f"{pct(ux['provisional_overwrite_fraction']['zero_overwrite_fraction'])}.",
            f"- Continuous display reconstruction: {ux_audit['audit']['resolution_episodes']} resolution episodes, {ux_audit['audit']['multi_holdback_episodes']} multi-holdback episodes, and maximum burst length {ux_audit['audit']['episode_burst_length']['maximum']:.0f}.",
            f"- Actual P1->P2->...->authority transition overwrite mean/P95/max: "
            f"{pct(ux_audit['audit']['transition_overwrite_fraction']['mean'])}/"
            f"{pct(ux_audit['audit']['transition_overwrite_fraction']['p95'])}/"
            f"{pct(ux_audit['audit']['transition_overwrite_fraction']['maximum'])}.",
            f"- Episode cumulative churn mean/P95/max: "
            f"{ux_audit['audit']['episode_cumulative_churn']['mean']:.3f}/"
            f"{ux_audit['audit']['episode_cumulative_churn']['p95']:.3f}/"
            f"{ux_audit['audit']['episode_cumulative_churn']['maximum']:.3f}.",
            f"- Empty provisional events: {ux_audit['audit']['empty_provisional_events']}; their defined overwrite boundary is exactly zero.",
            "- The legacy forward edit metric is retained in raw JSON only; it counts normal appended text and can exceed 100%, so it is not used as the UX claim.",
            "",
            "## Quality dependence and identity",
            "",
            f"- Cross-session source reuse: {dependency['audit']['cross_session_source_dependence']}; cluster bootstrap status: **{dependency['audit']['cluster_bootstrap_status']}**.",
            "- Both language-specific session-source graphs form one connected component, so the paired bootstrap is reported only for the frozen constructed-session sample.",
            f"- Post-run identity extension covers {identity['data_content']['audio_file_count']} byte-hashed audio files, GPU UUIDs, package versions, Qwen-ASR source, the model fingerprint, and the authority runtime.",
            f"- Resume lineage audit: **{resume['decision']}**; continuous and checkpoint+verify transcripts are byte-for-byte inherited from the declared source artifact.",
            "",
            "## Excluded branches",
            "",
            "- Fixed B=2 burst authority: **NO_GO_EXCLUDED**.",
            "- Dual-lane authority: **NO_GO_EXCLUDED**.",
            "- Legacy B=8 single-engine quality: excluded from deployment claims.",
            "",
            "## Evidence boundary",
            "",
            *[f"- {item}" for item in summary["claim_boundaries"]],
            "",
        ]
    )
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps({"decision": summary["decision"]}, sort_keys=True))
    return 0 if passed else 2


if __name__ == "__main__":
    raise SystemExit(main())

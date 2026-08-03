#!/usr/bin/env python3
"""Fail-closed finalizer for the R9.E online-evidence submission closure."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


POLICY_VERSION = "r9-dgft-v4-semantic-escalation"
EXPECTED_CELLS = {
    **{
        f"base-{arrival}-{seed}.json": (f"whisper-base.en", arrival, seed)
        for arrival in ("sync", "poisson")
        for seed in range(2026103001, 2026103006)
    },
    **{
        f"{model}-sync-{seed}.json": (f"whisper-{model}.en", "sync", seed)
        for model in ("tiny", "small")
        for seed in range(2026104001, 2026104004)
    },
}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical_sha(value: Any) -> str:
    return hashlib.sha256(json.dumps(
        value, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")).hexdigest()


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def stable_output_digest(payload: dict[str, Any]) -> str:
    return canonical_sha([
        {
            "session_id": row["session_id"],
            "utterance_ids": row["utterance_ids"],
            "stable_text": row["stable_text"],
        }
        for row in payload["sessions"]
    ])


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--development", type=Path, required=True)
    parser.add_argument("--final-holdout", type=Path, required=True)
    parser.add_argument("--service", type=Path, required=True)
    parser.add_argument("--prior-service", type=Path, required=True)
    parser.add_argument("--contracts", type=Path, required=True)
    parser.add_argument("--holdout-audit", type=Path, required=True)
    parser.add_argument("--frozen-policy", type=Path, required=True)
    parser.add_argument("--coverage-replay", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    actual = {path.name for path in args.service.glob("*.json")}
    require(actual == set(EXPECTED_CELLS), (
        f"service filename set mismatch missing={sorted(set(EXPECTED_CELLS)-actual)} "
        f"extra={sorted(actual-set(EXPECTED_CELLS))}"
    ))
    contract_by_model: dict[str, dict[str, Any]] = {}
    for model in ("tiny", "base", "small"):
        path = args.contracts / f"whisper-{model}.en-contract.json"
        contract = load(path)
        unsigned = dict(contract)
        claimed = unsigned.pop("contract_digest")
        require(canonical_sha(unsigned) == claimed, f"bad contract digest: {model}")
        require(contract["policy_version"] == POLICY_VERSION, "policy drift")
        contract_by_model[contract["model_name"]] = contract

    cells: list[dict[str, Any]] = []
    total_commits = 0
    total_violations = 0
    strict_passes = 0
    hashes_equal = True
    for filename, expected in sorted(EXPECTED_CELLS.items()):
        path = args.service / filename
        prior_path = args.prior_service / filename
        require(prior_path.is_file(), f"missing prior comparison: {filename}")
        payload = load(path)
        prior = load(prior_path)
        model, arrival, seed = expected
        config = payload["config"]
        metrics = payload["metrics"]
        contract = contract_by_model[model]
        require(
            (config["model_name"], config["arrival"], int(config["seed"]))
            == expected,
            f"cell identity mismatch: {filename}",
        )
        arrivals = config["initial_session_arrivals"]
        require(
            len(arrivals) == 16
            and {int(row["session_id"]) for row in arrivals} == set(range(16)),
            f"initial-arrival identity mismatch: {filename}",
        )
        if arrival == "sync":
            require(
                all(float(row["arrival_time"]) == 0.0 for row in arrivals),
                f"nonzero sync arrival: {filename}",
            )
        else:
            require(
                len({float(row["arrival_time"]) for row in arrivals}) == 16
                and min(float(row["arrival_time"]) for row in arrivals) > 0,
                f"invalid causal Poisson arrivals: {filename}",
            )
        require(config["policy_version"] == POLICY_VERSION, "cell policy drift")
        require(
            config["contract_digest"] == contract["contract_digest"],
            "cell contract mismatch",
        )
        budget = contract["frozen_service_budget"]
        for key in (
            "sessions", "duration_seconds", "window_seconds", "concurrency",
            "proposer_max_steps", "display_slo_seconds", "commit_slo_seconds",
        ):
            require(config[key] == budget[key], f"cell budget drift: {key}")
        require(config["arrival_scale_seconds"] == 0.02, "arrival scale drift")
        require(config["coalesce_seconds"] == 0.5, "coalesce drift")
        require(
            config["coverage_repair_mode"] == "singleton-replay",
            "repair mode drift",
        )
        require(
            config["degeneracy_repetition_threshold"] == 0.25,
            "degeneracy threshold drift",
        )
        frozen = config["frozen_policy"]
        require(frozen["adaptive_min_seconds"] == 15.0, "adaptive min drift")
        require(frozen["adaptive_max_seconds"] == 30.0, "adaptive max drift")
        require(frozen["coverage_threshold"] == 0.20, "coverage drift")
        require(
            frozen["coverage_asymmetry_margin"] == 0.15,
            "asymmetry drift",
        )
        require(
            frozen["structural_coverage_threshold"] == 0.20,
            "structural drift",
        )
        require(
            metrics["certificate_consumption_failures"] == 0
            and metrics["semantic_violations"] == 0,
            f"online transaction violation: {filename}",
        )
        require(
            metrics["online_commit_events"] > 0
            and metrics["commit_certificates"] > 0,
            f"no online evidence: {filename}",
        )
        online = payload["online_transaction_trace"]
        require(
            len(online["states"]) == 16
            and all(
                int(state["audio_frontier_window"]) == 90 * 16_000
                and state["policy_version"] == POLICY_VERSION
                and state["contract_digest"] == contract["contract_digest"]
                for state in online["states"]
            ),
            f"terminal state/frontier mismatch: {filename}",
        )
        speculative_events = [
            row for row in online["events"]
            if row["event"] == "speculative-registered"
        ]
        require(
            len(speculative_events) == 16 * 9,
            f"speculative branch versions not fully exercised: {filename}",
        )
        invalidated = sum(
            len(row.get("invalidated_speculative_versions", ()))
            for row in online["events"]
        )
        require(invalidated == len(speculative_events), (
            f"speculative descendant invalidation mismatch: {filename}"
        ))
        canonical_events = [
            row for row in online["events"]
            if row["event"] == "canonical-segment-committed"
        ]
        commit_events = [
            row for row in online["events"]
            if row["event"] in {
                "canonical-segment-committed",
                "terminal-fallback-committed",
            }
        ]
        require(
            len(canonical_events) == metrics["commit_certificates"],
            f"certificate count mismatch: {filename}",
        )
        require(
            all(
                row["certificate_consumed"]
                and row["certificate"]["contract_digest"]
                == contract["contract_digest"]
                for row in commit_events
            ),
            f"unconsumed or unbound certificate: {filename}",
        )
        equivalent = stable_output_digest(payload) == stable_output_digest(prior)
        hashes_equal = hashes_equal and equivalent
        strict = (
            float(metrics["wall_speedup"]) >= 2.5
            and float(metrics["gpu_normalized_speedup"]) >= 1.25
            and float(metrics["energy_reduction"]) >= 0.20
            and float(metrics["display_latency_p99"]) <= 1.9
            and float(metrics["segment_commit_lag_p99"]) <= 36.0
            and float(metrics["authority_audio_amplification"]) <= 1.2
            and int(metrics["semantic_violations"]) == 0
        )
        strict_passes += int(strict)
        total_commits += int(metrics["commit_certificates"])
        total_violations += int(metrics["semantic_violations"])
        cells.append({
            "filename": filename,
            "model": model,
            "arrival": arrival,
            "seed": seed,
            "strict_gate_pass": strict,
            "stable_output_hash_equivalent_to_prior": equivalent,
            "wall_speedup": metrics["wall_speedup"],
            "gpu_normalized_speedup": metrics["gpu_normalized_speedup"],
            "energy_reduction": metrics["energy_reduction"],
            "display_latency_p99": metrics["display_latency_p99"],
            "online_commit_latency_p99": metrics["segment_commit_lag_p99"],
            "commit_certificates": metrics["commit_certificates"],
            "online_certified_commits": len(commit_events),
            "sha256": sha(path),
        })

    coverage = load(args.coverage_replay)
    require(
        coverage["decision"] == "PASS_R9_COVERAGE_REPLAY_NO_DECISION_CHANGE",
        "coverage fix changed frozen decisions",
    )
    audit = load(args.holdout_audit)
    policy = load(args.frozen_policy)
    require(audit["decision"] == "PASS_R9_HOLDOUT_AUDIT", "holdout audit")
    require(audit["overlap_count"] == 0, "holdout overlap")
    require(policy["policy_version"] == POLICY_VERSION, "policy identity")
    require(policy["frozen_before_final3_execution"], "policy not frozen")
    require(
        policy["holdout_manifest_sha256"] == audit["manifest_sha256"],
        "policy/holdout binding mismatch",
    )

    quality: list[dict[str, Any]] = []
    for model in ("tiny", "base", "small"):
        for cohort, path in (
            (
                "development",
                args.development
                / f"{model}-development-semantic-escalation.json",
            ),
            (
                "third-untouched-confirmation",
                args.final_holdout
                / f"{model}-semantic-final3-confirmation.json",
            ),
        ):
            payload = load(path)
            require(payload["metrics"]["gate_pass"], f"quality fail: {path}")
            require(payload["config"]["coverage_threshold"] == 0.2, "quality drift")
            require(
                payload["config"]["coverage_asymmetry_margin"] == 0.15,
                "quality asymmetry drift",
            )
            sessions = int(payload["metrics"]["sessions"])
            if cohort == "third-untouched-confirmation":
                require(sessions == 40, "final3 must contain 40 long sessions")
            artifact_sha = sha(path)
            binding = canonical_sha({
                "quality_artifact_sha256": artifact_sha,
                "service_contract_digest": contract_by_model[
                    f"whisper-{model}.en"
                ]["contract_digest"],
                "policy_sha256": sha(args.frozen_policy),
                "cohort": cohort,
            })
            quality.append({
                "model": f"whisper-{model}.en",
                "cohort": cohort,
                "sessions": sessions,
                "source_utterances": (
                    sum(audit["counts"].values())
                    if cohort == "third-untouched-confirmation" else None
                ),
                "gate_pass": True,
                "mean_delta_pp": payload["metrics"]["mean_delta_pp"],
                "bootstrap_95_upper_pp": (
                    payload["metrics"]["bootstrap_95_upper_pp"]
                ),
                "quality_artifact_sha256": artifact_sha,
                "quality_service_binding_digest": binding,
            })

    require(hashes_equal, (
        "online service changed stable outputs; a new untouched quality "
        "confirmation is required before submission"
    ))
    require(strict_passes >= 15, "fewer than 15/16 strict service cells")
    require(total_violations == 0, "observed transaction-install violation")
    decision = (
        "PASS_R9E_ONLINE_SUBMISSION_CLOSURE"
        if strict_passes == 16
        else "QUALIFIED_R9E_ONLINE_SUBMISSION_CLOSURE_15_OF_16"
    )
    output = {
        "schema_version": 1,
        "study": "RevTrace R9.E online evidence closure",
        "decision": decision,
        "service_cells": cells,
        "quality": quality,
        "aggregate": {
            "service_cells": 16,
            "strict_service_cells_passed": strict_passes,
            "quality_cells": len(quality),
            "stable_output_hash_equivalence": hashes_equal,
            "commit_certificates": total_commits,
            "observed_transaction_install_violations": total_violations,
            "coverage_replay_segments": coverage["segments"],
            "coverage_replay_changed_decisions": coverage["changed_decisions"],
            "final3_source_utterances": sum(audit["counts"].values()),
            "final3_long_sessions_per_model": 40,
        },
        "claim_boundary": (
            "Zero observed transaction-install violations is an exhaustive "
            "trace result for these 16 service executions, not an iid rate "
            "estimate or mathematical numerical-exactness guarantee. Final3 "
            "uses 214 untouched source utterances assembled deterministically "
            "into 40 long sessions per model. Arrival timing is a causal "
            "virtual-time event stream; GPU wall time and NVML energy are real."
        ),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(output, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps({"decision": decision, **output["aggregate"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

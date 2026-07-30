#!/usr/bin/env python3
"""Bind every frozen checkpoint-20 result to one mechanism digest."""

from __future__ import annotations

import argparse
import json
import sys
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
        "--contract-manifest",
        type=Path,
        default=Path(
            "results/checkpoint20_holdback_authority/contract_manifest.json"
        ),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(
            "results/checkpoint20_holdback_authority/contract_bindings.json"
        ),
    )
    return parser.parse_args()


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def heldout(payload: dict[str, Any]) -> dict[str, Any]:
    rows = [row for row in payload["stages"] if row["label"] == "heldout"]
    if len(rows) != 1:
        raise ValueError("expected exactly one heldout stage")
    return rows[0]


def main() -> int:
    args = parse_args()
    root = args.results_dir.resolve()
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
    from revtrace.contract_manifest import (
        execution_binding,
        sha256_file,
    )
    from revtrace.provenance import resolve_runner_provenance

    contract = load(args.contract_manifest.resolve())
    mechanism = contract["mechanism"]
    digest = contract["mechanism_digest"]
    threshold = float(mechanism["risk_policy"]["minimum_margin_threshold"])
    bsz = int(mechanism["authority"]["fixed_batch_size"])
    runner_paths = {
        "live": Path("scripts/remote/run_phase5a_live_adaptive.py").resolve(),
        "risk": Path(
            "scripts/remote/run_checkpoint_dual_lane_shadow_audit.py"
        ).resolve(),
        "semantics": Path(
            "scripts/remote/run_holdback_semantics_gate.py"
        ).resolve(),
        "quality": Path(
            "scripts/remote/run_deployed_checkpoint20_quality.py"
        ).resolve(),
        "identity": Path(
            "scripts/remote/capture_checkpoint20_identity.py"
        ).resolve(),
        "offline_audit": Path(
            "scripts/audit_checkpoint20_submission_evidence.py"
        ).resolve(),
    }
    for path in runner_paths.values():
        if not path.is_file():
            raise FileNotFoundError(path)

    entries: dict[str, dict[str, Any]] = {}

    def bind(
        name: str,
        raw: Path,
        runner_role: str,
        profile: dict[str, Any],
    ) -> None:
        if not raw.is_file():
            raise FileNotFoundError(raw)
        raw_payload = load(raw)
        provenance = resolve_runner_provenance(
            repo=Path.cwd(),
            runner_path=runner_paths[runner_role],
            raw_payload=raw_payload,
        )
        entries[name] = {
            "path": raw.relative_to(Path.cwd().resolve()).as_posix(),
            **execution_binding(
                mechanism_digest=digest,
                role=name,
                runner_sha256=provenance["runner_sha256"],
                raw_result_sha256=sha256_file(raw),
                execution_profile={
                    **profile,
                    "source_provenance": provenance,
                },
            ),
        }

    calibration_path = root / "calibration.json"
    calibration = heldout(load(calibration_path))
    if (
        abs(float(calibration["threshold"]) - threshold) > 1e-12
        or int(calibration["canonical_batch_size"]) != bsz
        or int(calibration["checkpoint_seconds"]) != 20
        or calibration["low_margin_policy"] != "holdback"
    ):
        raise ValueError("calibration does not implement frozen mechanism")
    bind(
        "calibration",
        calibration_path,
        "live",
        {"role": "threshold_calibration", "heldout": True},
    )

    risk_path = root / "anytime_risk_audit.json"
    risk = load(risk_path)
    if (
        risk["contract"]["low_margin_policy"] != "holdback"
        or int(risk["contract"]["concurrency"]) != bsz
        or int(risk["contract"]["checkpoint_seconds"]) != 20
        or risk["contract"]["batch_invariant_runtime_sha256"]
        != mechanism["authority"]["runtime_sha256"]
    ):
        raise ValueError("risk audit does not implement frozen mechanism")
    bind(
        "formal_risk_audit",
        risk_path,
        "risk",
        {"role": "pre_outcome_anytime_risk_audit"},
    )

    for seed in SEEDS:
        path = root / f"seed_{seed}.json"
        stage = heldout(load(path))
        if (
            abs(float(stage["threshold"]) - threshold) > 1e-12
            or int(stage["concurrency"]) != bsz
            or int(stage["canonical_batch_size"]) != bsz
            or int(stage["checkpoint_seconds"]) != 20
            or stage["low_margin_policy"] != "holdback"
        ):
            raise ValueError(f"seed {seed} does not implement frozen mechanism")
        bind(
            f"live_seed_{seed}",
            path,
            "live",
            {"role": "live_service_tail", "seed": seed},
        )

    semantic_path = root / "holdback_semantics_gate.json"
    semantics = load(semantic_path)
    if (
        semantics["mechanism_digest"] != digest
        or semantics["decision"] != "HOLDBACK_SEMANTICS_PASS"
    ):
        raise ValueError("semantic integration gate is not contract matched")
    bind(
        "semantic_integration",
        semantic_path,
        "semantics",
        {"role": "real_model_state_semantics", "fixed_batch_size": bsz},
    )

    quality_path = root / "deployed_b12_quality_32x2.json"
    quality = load(quality_path)
    if (
        quality["mechanism_digest"] != digest
        or quality["deployment"]["proposer"]
        != "gpu0_fp16_ordinary_fixed_b12"
        or quality["deployment"]["authority"]
        != "gpu1_fp16_batch_invariant_fixed_b12"
        or int(quality["deployment"]["sessions_per_language"]) < 16
    ):
        raise ValueError("quality gate is not the deployed B=12 mechanism")
    bind(
        "deployed_quality",
        quality_path,
        "quality",
        {
            "role": "paired_deployed_quality_and_ux",
            "proposer_batch_size": bsz,
            "authority_batch_size": bsz,
            "distinct_gpu_roles": True,
        },
    )

    identity_path = root / "deployment_identity_v2.json"
    identity = load(identity_path)
    if (
        int(identity["schema_version"]) != 2
        or identity["data_manifest_sha256"]
        != mechanism["data"]["manifest_sha256"]
        or identity["model_fingerprint"]["content_digest"]
        != mechanism["model"]["fingerprint"]["content_digest"]
        or identity["authority_runtime_sha256"]
        != mechanism["authority"]["runtime_sha256"]
        or int(identity["data_content"]["audio_file_count"]) <= 0
    ):
        raise ValueError("identity extension does not match frozen mechanism")
    bind(
        "identity_extension",
        identity_path,
        "identity",
        {
            "role": "post_run_content_identity_extension",
            "at_run_contract_change": False,
            "identity_extension_digest": identity[
                "identity_extension_digest"
            ],
        },
    )

    offline_roles = {
        "resume_lineage": (
            root / "resume_quality_attestation.json",
            "offline_resume_lineage_validation",
        ),
        "continuous_provisional_ux": (
            root / "provisional_experience_audit.json",
            "offline_continuous_display_reconstruction",
        ),
        "quality_dependency": (
            root / "quality_dependency_audit.json",
            "offline_source_reuse_dependence_audit",
        ),
    }
    for name, (path, role) in offline_roles.items():
        payload = load(path)
        if (
            payload["mechanism_digest"] != digest
            or payload["quality_artifact_sha256"]
            != sha256_file(quality_path)
            or payload["identity_extension_sha256"]
            != sha256_file(identity_path)
        ):
            raise ValueError(f"{name} is not linked to frozen evidence")
        bind(
            name,
            path,
            "offline_audit",
            {"role": role, "model_inference_executed": False},
        )

    ux_negative = root / "deployed_b12_quality_32x2_ux_metric_negative.json"
    if not ux_negative.is_file():
        raise FileNotFoundError(ux_negative)
    payload = {
        "schema_version": 1,
        "mechanism_digest": digest,
        "contract_manifest": {
            "path": args.contract_manifest.resolve()
            .relative_to(Path.cwd().resolve())
            .as_posix(),
            "sha256": sha256_file(args.contract_manifest.resolve()),
        },
        "bindings": entries,
        "excluded_evidence": {
            "checkpoint_rebase_holdback_quality_16x2.json": (
                "legacy B=8 single-engine quality; not deployment matched"
            ),
            "burst_b2": "NO_GO_EXCLUDED",
            "dual_lane": "NO_GO_EXCLUDED",
            "provisional_forward_edit_metric": {
                "decision": "METRIC_DEFINITION_REJECTED",
                "path": ux_negative.relative_to(
                    Path.cwd().resolve()
                ).as_posix(),
                "sha256": sha256_file(ux_negative),
                "reason": (
                    "counted normal appended text as an overwrite and used "
                    "provisional length as denominator, so values could exceed 1"
                ),
            },
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"mechanism_digest": digest, "bindings": len(entries)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

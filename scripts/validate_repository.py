from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def check_manifest(root: Path, manifest_path: Path, repo_relative: bool) -> list[str]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    failures: list[str] = []
    base = ROOT if repo_relative else root
    for item in manifest["files"]:
        path = base / item["path"]
        if not path.is_file():
            failures.append(f"missing:{path}")
            continue
        if path.stat().st_size != item["bytes"]:
            failures.append(f"size:{path}")
        if sha256(path) != item["sha256"]:
            failures.append(f"sha256:{path}")
    return failures


def main() -> int:
    required = [
        "README.md",
        "AGENTS.md",
        "configs/experiment_registry.json",
        "docs/CLAIM_BOUNDARIES.md",
        "docs/roadmap/PHASES.md",
        "results/phase0",
        "results/phase1/deployed_v1/summary.json",
        "artifact/phase1-deployed-system-v1/MANIFEST.json",
        "results/phase2/risk_v1/summary.json",
        "results/phase2/terminal_canonical/summary.json",
        "artifact/phase2-risk-tail-v1/MANIFEST.json",
        "results/phase3/idle_audit/summary.json",
        "results/phase3/rir_population/summary.json",
        "results/phase3/second_architecture/summary.json",
        "artifact/phase3b-d-boundaries-v1/MANIFEST.json",
        "results/phase4/summary.json",
        "artifact/phase4-adaptation-generality-v1/MANIFEST.json",
        "src/revtrace/core.py",
        "src/revtrace/risk.py",
        "src/revtrace/control.py",
        "src/revtrace/amplification.py",
    ]
    failures = [
        f"missing-required:{path}"
        for path in required
        if not (ROOT / path).exists()
    ]

    registry = json.loads(
        (ROOT / "configs" / "experiment_registry.json").read_text(
            encoding="utf-8"
        )
    )
    for experiment in registry["experiments"]:
        for key in ("config", "result", "artifact"):
            if (
                key in {"result", "artifact"}
                and experiment["status"].startswith("RUNNING_")
            ):
                continue
            if not (ROOT / experiment[key]).exists():
                failures.append(
                    f"registry:{experiment['id']}:{key}:{experiment[key]}"
                )

    failures.extend(
        check_manifest(
            ROOT / "results" / "phase1" / "deployed_v1",
            ROOT / "results" / "phase1" / "deployed_v1" / "MANIFEST.json",
            repo_relative=False,
        )
    )
    failures.extend(
        check_manifest(
            ROOT / "results" / "phase2",
            ROOT / "results" / "phase2" / "MANIFEST.json",
            repo_relative=True,
        )
    )
    failures.extend(
        check_manifest(
            ROOT / "artifact" / "phase2-risk-tail-v1",
            ROOT
            / "artifact"
            / "phase2-risk-tail-v1"
            / "MANIFEST.json",
            repo_relative=False,
        )
    )
    failures.extend(
        check_manifest(
            ROOT / "artifact" / "phase1-deployed-system-v1",
            ROOT
            / "artifact"
            / "phase1-deployed-system-v1"
            / "MANIFEST.json",
            repo_relative=False,
        )
    )
    phase3_artifact_manifest = (
        ROOT
        / "artifact"
        / "phase3b-d-boundaries-v1"
        / "MANIFEST.json"
    )
    if phase3_artifact_manifest.exists():
        failures.extend(
            check_manifest(
                ROOT / "artifact" / "phase3b-d-boundaries-v1",
                phase3_artifact_manifest,
                repo_relative=False,
            )
        )
    phase4_artifact_manifest = (
        ROOT
        / "artifact"
        / "phase4-adaptation-generality-v1"
        / "MANIFEST.json"
    )
    if phase4_artifact_manifest.exists():
        failures.extend(
            check_manifest(
                ROOT / "artifact" / "phase4-adaptation-generality-v1",
                phase4_artifact_manifest,
                repo_relative=False,
            )
        )
    phase2_summary = json.loads(
        (
            ROOT
            / "results"
            / "phase2"
            / "risk_v1"
            / "summary.json"
        ).read_text(encoding="utf-8")
    )
    if not phase2_summary["decision"].startswith(
        "PHASE2_RISK_AND_TAIL_GATE_PASS"
    ):
        failures.append(
            f"phase2-decision:{phase2_summary['decision']}"
        )
    if len(phase2_summary.get("risk_rows", [])) != 2:
        failures.append("phase2-risk-model-count")
    for row in phase2_summary.get("risk_rows", []):
        if not row["decision"].endswith("_PASS"):
            failures.append(
                f"phase2-risk:{row['model']}:{row['decision']}"
            )
    if len(phase2_summary.get("replicate_stats", [])) != 2:
        failures.append("phase2-system-model-count")
    for row in phase2_summary.get("replicate_stats", []):
        if row["runs"] != 5 or not row["all_runs_pass"]:
            failures.append(
                f"phase2-replicates:{row['model']}:{row['runs']}"
            )
        if any(
            row[key] != 0
            for key in (
                "total_deadline_misses",
                "total_output_violations",
                "total_state_violations",
                "total_stale_or_replayed",
            )
        ):
            failures.append(f"phase2-system-safety:{row['model']}")
    phase2_environment = json.loads(
        (ROOT / "deployment" / "phase2_environment.json").read_text(
            encoding="utf-8"
        )
    )
    runner_paths = {
        "shadow_audit_sha256":
            ROOT / "scripts" / "remote" / "run_shadow_risk_audit.py",
        "dual_gpu_service_sha256":
            ROOT / "scripts" / "remote" / "run_revtrace_dual_gpu.py",
        "terminal_replicates_orchestrator_sha256":
            ROOT / "scripts" / "remote" / "run_terminal_replicates.sh",
        "post_calibration_orchestrator_sha256":
            ROOT
            / "scripts"
            / "remote"
            / "run_phase2_post_calibration.sh",
        "risk_v2_repair_orchestrator_sha256":
            ROOT
            / "scripts"
            / "remote"
            / "run_phase2_risk_v2_repair.sh",
    }
    for key, path in runner_paths.items():
        if sha256(path) != phase2_environment["runners"][key]:
            failures.append(f"phase2-runner-hash:{key}")

    print(
        json.dumps(
            {
                "project": "RevTrace",
                "registered_experiments": len(registry["experiments"]),
                "failures": failures,
                "status": "PASS" if not failures else "FAIL",
            },
            indent=2,
        )
    )
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Build and verify the bounded checkpoint-20 submission artifact."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path


FILES = (
    "README.md",
    "configs/checkpoint20_excluded_mechanisms.json",
    "docs/protocols/checkpoint20_holdback_authority_closure.md",
    "docs/reports/checkpoint20_submission_closure.md",
    "results/checkpoint20_holdback_authority/contract_manifest.json",
    "results/checkpoint20_holdback_authority/contract_bindings.json",
    "results/checkpoint20_holdback_authority/deployment_identity.json",
    "results/checkpoint20_holdback_authority/deployment_identity_v2.json",
    "results/checkpoint20_holdback_authority/holdback_semantics_gate.json",
    "results/checkpoint20_holdback_authority/deployed_b12_quality_32x2.json",
    "results/checkpoint20_holdback_authority/deployed_b12_quality_32x2_ux_metric_negative.json",
    "results/checkpoint20_holdback_authority/deployed_quality_summary.csv",
    "results/checkpoint20_holdback_authority/resume_quality_attestation.json",
    "results/checkpoint20_holdback_authority/provisional_experience_audit.json",
    "results/checkpoint20_holdback_authority/quality_dependency_audit.json",
    "results/checkpoint20_holdback_authority/final_summary_v2.json",
    "scripts/audit_checkpoint20_submission_evidence.py",
    "scripts/bind_checkpoint20_evidence.py",
    "scripts/build_checkpoint20_submission_artifact.py",
    "scripts/finalize_checkpoint20_submission.py",
    "scripts/verify_checkpoint20_submission_artifact.py",
    "scripts/remote/capture_checkpoint20_identity.py",
    "scripts/remote/run_deployed_checkpoint20_quality.py",
    "scripts/remote/run_holdback_semantics_gate.py",
    "src/revtrace/contract_manifest.py",
    "src/revtrace/evidence_audit.py",
    "src/revtrace/long_horizon.py",
    "src/revtrace/provenance.py",
    "tests/test_checkpoint20_submission_finalizer.py",
    "tests/test_provisional_experience.py",
)
TEXT_SUFFIXES = {".csv", ".json", ".md", ".py"}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("artifact/checkpoint20-submission-closure-v2"),
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = Path.cwd().resolve()
    output = args.output.resolve()
    if output == root or root not in output.parents:
        raise ValueError("artifact output must stay inside the repository")
    if output.exists():
        shutil.rmtree(output)
    entries = {}
    for relative in FILES:
        source = (root / relative).resolve()
        if not source.is_file():
            raise FileNotFoundError(source)
        target = output / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        if source.suffix.lower() in TEXT_SUFFIXES:
            target.write_bytes(
                source.read_bytes().replace(b"\r\n", b"\n")
            )
        else:
            shutil.copy2(source, target)
        entries[relative] = {
            "bytes": target.stat().st_size,
            "sha256": sha256(target),
        }
    final = json.loads(
        (output / "results/checkpoint20_holdback_authority/final_summary_v2.json")
        .read_text(encoding="utf-8")
    )
    manifest = {
        "schema_version": 2,
        "artifact": "checkpoint20-submission-closure-v2",
        "decision": final["decision"],
        "mechanism_digest": final["mechanism_digest"],
        "scope": (
            "bounded paper-facing evidence, current reproduction source, and "
            "Git-resolved historical runner provenance; "
            "large calibration/service raw traces remain content-addressed "
            "by final_summary_v2.json"
        ),
        "identity_extension_digest": final["artifact_identity_extension"][
            "identity_extension_digest"
        ],
        "files": entries,
    }
    manifest_path = output / "MANIFEST.json"
    manifest_path.write_bytes(
        (
            json.dumps(
                manifest,
                indent=2,
                ensure_ascii=False,
                sort_keys=True,
            )
            + "\n"
        ).encode("utf-8")
    )
    for relative, record in entries.items():
        if sha256(output / relative) != record["sha256"]:
            raise AssertionError(f"artifact verification failed: {relative}")
    print(
        json.dumps(
            {
                "decision": manifest["decision"],
                "files": len(entries),
                "manifest_sha256": sha256(manifest_path),
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

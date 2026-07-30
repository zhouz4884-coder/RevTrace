#!/usr/bin/env python3
"""Offline, fail-closed audits for the checkpoint-20 submission evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--results-dir",
        type=Path,
        default=Path("results/checkpoint20_holdback_authority"),
    )
    parser.add_argument(
        "--identity-extension",
        type=Path,
        default=Path(
            "results/checkpoint20_holdback_authority/"
            "deployment_identity_v2.json"
        ),
    )
    return parser.parse_args()


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> int:
    args = parse_args()
    root = args.results_dir.resolve()
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
    from revtrace.evidence_audit import (
        audit_provisional_events,
        audit_quality_dependencies,
        validate_resume_quality,
    )

    contract_path = root / "contract_manifest.json"
    quality_path = root / "deployed_b12_quality_32x2.json"
    quality = load(quality_path)
    contract = load(contract_path)
    resume_sha = quality["environment"].get(
        "resumed_from_quality_sha256"
    )
    if not resume_sha:
        raise ValueError("quality artifact does not declare resumed source")
    candidates = [
        path
        for path in root.glob("*.json")
        if path != quality_path and sha256(path) == resume_sha
    ]
    if len(candidates) != 1:
        raise ValueError(
            f"expected one resume source for {resume_sha}, found {candidates}"
        )
    resume_path = candidates[0]
    resumed = load(resume_path)
    expected_deployment = {
        key: quality["deployment"][key]
        for key in (
            "proposer",
            "authority",
            "duration_seconds",
            "checkpoint_seconds",
            "margin_threshold",
            "sessions_per_language",
        )
    }
    expected_sessions = [
        {
            "session_id": row["session_id"],
            "language": row["language"],
            "source_ids": row["source_ids"],
            "reference": row["reference"],
        }
        for row in quality["paired_sessions"]
    ]
    resume_attestation = validate_resume_quality(
        resumed=resumed,
        expected_sessions=expected_sessions,
        mechanism_digest=contract["mechanism_digest"],
        contract_manifest_sha256=sha256(contract_path),
        expected_deployment=expected_deployment,
    )
    by_resume = {
        row["session_id"]: row for row in resumed["paired_sessions"]
    }
    reused_transcript_checks = {
        mode: all(
            row["transcripts"][mode]
            == by_resume[row["session_id"]]["transcripts"][mode]
            for row in quality["paired_sessions"]
        )
        for mode in ("continuous", "checkpoint_verify")
    }
    if not all(reused_transcript_checks.values()):
        raise ValueError("final artifact changed a reused transcript")

    identity_path = args.identity_extension.resolve()
    identity = load(identity_path)
    if (
        identity["data_manifest_sha256"]
        != contract["mechanism"]["data"]["manifest_sha256"]
        or identity["model_fingerprint"]["content_digest"]
        != contract["mechanism"]["model"]["fingerprint"]["content_digest"]
        or identity["authority_runtime_sha256"]
        != contract["mechanism"]["authority"]["runtime_sha256"]
    ):
        raise ValueError("identity extension does not extend frozen contract")
    content_records = {
        str(row["sample_id"]): row
        for row in identity["data_content"]["records"]
    }
    identity_source_checks = []
    for row in expected_sessions:
        references = []
        for source_id in row["source_ids"]:
            if source_id not in content_records:
                raise ValueError(
                    f"session {row['session_id']} has unknown source {source_id}"
                )
            record = content_records[source_id]
            if record["language"] != row["language"]:
                raise ValueError(
                    f"session {row['session_id']} crosses language identity"
                )
            references.append(record["reference"])
        matched = " ".join(references) == row["reference"]
        if not matched:
            raise ValueError(
                f"session {row['session_id']} reference/source mismatch"
            )
        identity_source_checks.append(
            {
                "session_id": row["session_id"],
                "source_count": len(row["source_ids"]),
                "reference_reconstructed": matched,
            }
        )

    common = {
        "schema_version": 1,
        "mechanism_digest": contract["mechanism_digest"],
        "quality_artifact_sha256": sha256(quality_path),
        "identity_extension_sha256": sha256(identity_path),
        "environment": {
            "code_commit": subprocess.check_output(
                ["git", "rev-parse", "HEAD"],
                cwd=Path.cwd(),
                text=True,
            ).strip(),
            "runner_sha256": sha256(Path(__file__).resolve()),
        },
    }
    resume_attestation.update(
        {
            **common,
            "resume_artifact": resume_path.relative_to(
                Path.cwd().resolve()
            ).as_posix(),
            "resume_artifact_sha256": resume_sha,
            "reused_transcript_checks": reused_transcript_checks,
            "identity_source_checks": identity_source_checks,
            "claim_boundary": (
                "This is an offline fail-closed validation of the recorded "
                "resume relation. It does not rerun model inference."
            ),
        }
    )
    ux = {
        **common,
        "decision": "CONTINUOUS_PROVISIONAL_UX_AUDIT_PASS",
        "audit": audit_provisional_events(
            quality["provisional_experience"]["events"]
        ),
        "claim_boundary": (
            "UX transitions are recomputed from frozen raw events; no model "
            "execution or new production-prevalence evidence is introduced."
        ),
    }
    dependencies = {
        **common,
        "decision": "QUALITY_DEPENDENCE_AUDIT_COMPLETE",
        "audit": audit_quality_dependencies(quality["paired_sessions"]),
        "claim_boundary": (
            "The existing bootstrap is retained as a fixed-session paired "
            "sample analysis, not an independent-source population claim."
        ),
    }
    outputs = {
        "resume_quality_attestation.json": resume_attestation,
        "provisional_experience_audit.json": ux,
        "quality_dependency_audit.json": dependencies,
    }
    for name, payload in outputs.items():
        path = root / name
        path.write_text(
            json.dumps(
                payload,
                indent=2,
                ensure_ascii=False,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
    print(
        json.dumps(
            {
                "decision": "CHECKPOINT20_OFFLINE_AUDITS_PASS",
                "outputs": sorted(outputs),
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

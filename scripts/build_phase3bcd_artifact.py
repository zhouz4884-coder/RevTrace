#!/usr/bin/env python3
"""Build a hash-audited Phase 3B--3D evidence artifact."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def copy_file(source: Path, destination: Path) -> None:
    if not source.exists():
        return
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--artifact-root",
        type=Path,
        default=ROOT / "artifact" / "phase3b-d-boundaries-v1",
    )
    args = parser.parse_args()
    if args.artifact_root.exists():
        shutil.rmtree(args.artifact_root)
    sources = [
        ROOT / "configs" / "revtrace_phase3b_idle_audit_gate.json",
        ROOT / "configs" / "revtrace_phase3c_rir_gate.json",
        ROOT
        / "configs"
        / "revtrace_phase3d_second_architecture_gate.json",
        ROOT / "configs" / "experiment_registry.json",
        ROOT / "README.md",
        ROOT / "results" / "phase3" / "README.md",
        ROOT / "results" / "phase3" / "idle_audit" / "replay.json",
        ROOT / "results" / "phase3" / "idle_audit" / "summary.json",
        ROOT / "results" / "phase3" / "idle_audit" / "REPORT.md",
        ROOT / "results" / "phase3" / "rir_population" / "summary.json",
        ROOT / "results" / "phase3" / "rir_population" / "REPORT.md",
        ROOT
        / "results"
        / "phase3"
        / "rir_population"
        / "phase3c-test-clean-64-manifest.json",
        ROOT
        / "results"
        / "phase3"
        / "second_architecture"
        / "voxtral.json",
        ROOT
        / "results"
        / "phase3"
        / "second_architecture"
        / "voxtral-short-source.json",
        ROOT
        / "results"
        / "phase3"
        / "second_architecture"
        / "voxtral-smoke-missing-accelerate.json",
        ROOT
        / "results"
        / "phase3"
        / "second_architecture"
        / "summary.json",
        ROOT
        / "results"
        / "phase3"
        / "second_architecture"
        / "REPORT.md",
        ROOT / "scripts" / "evaluate_idle_audit_replay.py",
        ROOT / "scripts" / "finalize_phase3b.py",
        ROOT / "scripts" / "finalize_phase3c.py",
        ROOT / "scripts" / "finalize_phase3d.py",
        ROOT / "scripts" / "remote" / "run_revision_impulse_population.py",
        ROOT / "scripts" / "remote" / "build_phase3c_audio_manifest.py",
        ROOT / "scripts" / "remote" / "prepare_phase3c_librispeech.sh",
        ROOT / "scripts" / "remote" / "run_phase3c_stress.sh",
        ROOT / "scripts" / "remote" / "run_phase3c_librispeech.sh",
        ROOT / "scripts" / "remote" / "run_voxtral_boundary.py",
        ROOT / "scripts" / "remote" / "run_phase3d_voxtral.sh",
        ROOT / "scripts" / "remote" / "setup_voxtral_env.sh",
        ROOT / "src" / "revtrace" / "amplification.py",
        ROOT / "src" / "revtrace" / "control.py",
        ROOT / "tests" / "test_amplification.py",
        ROOT / "docs" / "roadmap" / "PHASES.md",
        ROOT / "docs" / "CLAIM_BOUNDARIES.md",
    ]
    for source in sources:
        if source.exists():
            copy_file(
                source,
                args.artifact_root / source.relative_to(ROOT),
            )
    raw_root = ROOT / "results" / "phase3" / "rir_population"
    for source in sorted(raw_root.glob("qwen3-asr-*.json")):
        copy_file(
            source,
            args.artifact_root / source.relative_to(ROOT),
        )
    commit = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        check=True,
        text=True,
        capture_output=True,
    ).stdout.strip()
    files = []
    for path in sorted(args.artifact_root.rglob("*")):
        if path.is_file():
            files.append(
                {
                    "path": path.relative_to(
                        args.artifact_root
                    ).as_posix(),
                    "bytes": path.stat().st_size,
                    "sha256": sha256(path),
                }
            )
    manifest = {
        "schema_version": 1,
        "artifact": "RevTrace Phase 3B--3D bounded evidence",
        "source_commit": commit,
        "files": files,
        "claim_boundary": (
            "The artifact preserves PASS, unresolved, and population-gate "
            "boundaries; it is not a deterministic certificate."
        ),
    }
    (args.artifact_root / "MANIFEST.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "artifact": str(args.artifact_root),
                "files": len(files),
                "bytes": sum(item["bytes"] for item in files),
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

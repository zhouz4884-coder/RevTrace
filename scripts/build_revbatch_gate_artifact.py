#!/usr/bin/env python3
"""Build or verify the compact RevBatch gate artifact."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def verify(output: Path) -> int:
    manifest = json.loads((output / "MANIFEST.json").read_text(encoding="utf-8"))
    expected = {item["path"]: item for item in manifest["files"]}
    actual = {
        path.relative_to(output).as_posix(): path
        for path in output.rglob("*")
        if path.is_file() and path.name != "MANIFEST.json"
    }
    if set(expected) != set(actual):
        raise AssertionError("artifact file set differs from manifest")
    for relative, path in actual.items():
        entry = expected[relative]
        if path.stat().st_size != entry["bytes"]:
            raise AssertionError(f"size mismatch: {relative}")
        if sha256(path) != entry["sha256"]:
            raise AssertionError(f"hash mismatch: {relative}")
    print(json.dumps({"files": len(actual), "status": "PASS"}, sort_keys=True))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    root = args.root.resolve()
    output = root / "artifact" / "phase0-revbatch-gate-v1"
    if args.check:
        return verify(output)

    if output.exists():
        shutil.rmtree(output)
    for directory in ["raw", "evidence", "scripts"]:
        (output / directory).mkdir(parents=True)

    sources = {
        root / "configs" / "revbatch_gate.json": output / "config.json",
        root / "docs" / "reports" / "revbatch_gate_protocol.md":
            output / "PROTOCOL.md",
        root / "docs" / "reports" / "revbatch_gate_report.md":
            output / "REPORT.md",
        root / "results" / "phase0" / "revbatch" / "d0" / "source_audit.json":
            output / "evidence" / "source_audit.json",
        root / "results" / "phase0" / "revbatch" / "revbatch_v1" / "summary.json":
            output / "summary.json",
        root / "results" / "phase0" / "revbatch" / "probe" / "formal-qwen3-asr-0.6b.json":
            output / "raw" / "formal-qwen3-asr-0.6b.json",
        root / "results" / "phase0" / "revbatch" / "probe" / "formal-qwen3-asr-1.7b.json":
            output / "raw" / "formal-qwen3-asr-1.7b.json",
        root / "results" / "phase0" / "revbatch" / "probe" / "smoke-qwen3-asr-0.6b.json":
            output / "raw" / "smoke-qwen3-asr-0.6b.json",
        root / "results" / "phase0" / "revbatch" / "probe" / "smoke-qwen3-asr-1.7b.json":
            output / "raw" / "smoke-qwen3-asr-1.7b.json",
        root / "results" / "phase0" / "revbatch" / "environment" / "environment.json":
            output / "evidence" / "environment.json",
        root / "results" / "phase0" / "revbatch" / "environment" / "qwen3_asr_commit.txt":
            output / "evidence" / "qwen3_asr_commit.txt",
        root / "results" / "phase0" / "revbatch" / "environment" / "requirements-lock.txt":
            output / "evidence" / "requirements-lock.txt",
        root / "results" / "phase0" / "revbatch" / "data" / "manifest.json":
            output / "evidence" / "data_manifest.json",
        root / "scripts" / "remote" / "setup_revbatch_gate.sh":
            output / "scripts" / "setup.sh",
        root / "scripts" / "remote" / "prepare_revbatch_data.py":
            output / "scripts" / "prepare_data.py",
        root / "scripts" / "remote" / "run_revbatch_gate.py":
            output / "scripts" / "run_gate.py",
        root / "scripts" / "remote" / "launch_revbatch_gate.sh":
            output / "scripts" / "launch.sh",
        root / "scripts" / "finalize_revbatch_gate.py":
            output / "scripts" / "finalize.py",
        root / "scripts" / "validate_revbatch_gate.py":
            output / "scripts" / "validate.py",
    }
    for source, destination in sources.items():
        if not source.is_file():
            raise FileNotFoundError(source)
        shutil.copyfile(source, destination)

    readme = """# RevBatch Gate artifact

Decision: `NO_GO_FOR_REVBATCH_EXACT_REVISION_GATE_B`.

Gate A passed with maximum live audio-throughput speedups of 11.073x for
Qwen3-ASR-0.6B and 8.752x for Qwen3-ASR-1.7B. Gate B failed after 1,699
revision events per model: neither model preserved the required 100% token,
partial-transcript, and final-transcript exactness. Gate C was therefore not
run.

The artifact includes the frozen contract, D0 source audit, full compact
per-cell records and bounded mismatch examples, formal logs, environment and
data hashes, report, and reproduction scripts. The public bilingual inputs are
performance/semantics stimuli only; no ASR quality claim is made.
"""
    (output / "README.md").write_text(readme, encoding="utf-8", newline="\n")

    entries = []
    for path in sorted(item for item in output.rglob("*") if item.is_file()):
        if path.name == "MANIFEST.json":
            continue
        entries.append(
            {
                "path": path.relative_to(output).as_posix(),
                "bytes": path.stat().st_size,
                "sha256": sha256(path),
            }
        )
    manifest = {
        "schema_version": 1,
        "artifact": "revbatch-gate-v1",
        "decision": "NO_GO_FOR_REVBATCH_EXACT_REVISION_GATE_B",
        "files": entries,
    }
    (output / "MANIFEST.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(json.dumps({"files": len(entries), "output": str(output)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

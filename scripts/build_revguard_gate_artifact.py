#!/usr/bin/env python3
"""Build or verify the compact RevGuard mechanism-gate artifact."""

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


def copy_reproducible_text(source: Path, destination: Path) -> None:
    text = source.read_text(encoding="utf-8")
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    with destination.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)


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
    output = root / "artifact" / "phase0-revguard-mechanism-v1"
    if args.check:
        return verify(output)
    if output.exists():
        shutil.rmtree(output)
    for directory in ("raw", "evidence", "scripts"):
        (output / directory).mkdir(parents=True)

    sources = {
        root / "configs" / "revguard_mechanism_gate.json":
            output / "config.json",
        root / "docs" / "reports" / "revguard_mechanism_gate_report.md":
            output / "REPORT.md",
        root / "results" / "phase0" / "revguard" / "revguard_v1" / "summary.json":
            output / "summary.json",
        root / "results" / "phase0" / "revbatch" / "environment" / "environment.json":
            output / "evidence" / "environment.json",
        root / "results" / "phase0" / "revbatch" / "environment" / "requirements-lock.txt":
            output / "evidence" / "requirements-lock.txt",
        root / "results" / "phase0" / "revbatch" / "data" / "manifest.json":
            output / "evidence" / "data_manifest.json",
        root / "scripts" / "remote" / "run_revguard_same_input.py":
            output / "scripts" / "run_same_input.py",
        root / "scripts" / "remote" / "launch_revguard_same_input.sh":
            output / "scripts" / "launch_same_input.sh",
        root / "scripts" / "remote" / "run_revguard_selective.py":
            output / "scripts" / "run_selective.py",
        root / "scripts" / "remote" / "launch_revguard_selective.sh":
            output / "scripts" / "launch_selective.sh",
        root / "scripts" / "finalize_revguard_gate.py":
            output / "scripts" / "finalize.py",
        root / "scripts" / "validate_revguard_gate.py":
            output / "scripts" / "validate.py",
    }
    probe = root / "results" / "phase0" / "revguard" / "probe"
    for path in sorted(probe.glob("*.json")):
        sources[path] = output / "raw" / path.name
    for source, destination in sources.items():
        if not source.is_file():
            raise FileNotFoundError(source)
        copy_reproducible_text(source, destination)

    (output / "README.md").write_text(
        """# RevGuard mechanism gate artifact

Decision: `MECHANISM_ORACLE_VALIDATED_EXACT_CERTIFICATE_UNRESOLVED`.

Same-input controls isolate BF16 batch-shape/runtime divergence from revision
feedback. A margin-threshold selective canonical verifier had zero observed
violations on the held-out c=16 shape and retained 2.88-2.99x single-GPU
speedup, but margin is not a deterministic certificate and verifier work was
not fully hidden. FP32 made singleton and batch execution internally exact in
the tested cells, while changing the frozen BF16 trajectory.

The artifact contains compact live records, frozen gates, report, environment
and data hashes, reproduction scripts, and a hash manifest. It makes no ASR
quality, production-frequency, or deployed two-GPU serving claim.
""",
        encoding="utf-8",
        newline="\n",
    )
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
        "artifact": "revguard-mechanism-gate-v1",
        "decision": "MECHANISM_ORACLE_VALIDATED_EXACT_CERTIFICATE_UNRESOLVED",
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

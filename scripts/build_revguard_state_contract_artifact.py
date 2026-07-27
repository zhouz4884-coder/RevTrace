#!/usr/bin/env python3
"""Build or verify the compact RevGuard state-contract artifact."""

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


def copy_text(source: Path, destination: Path) -> None:
    text = source.read_text(encoding="utf-8")
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)


def verify(output: Path) -> int:
    manifest = json.loads((output / "MANIFEST.json").read_text("utf-8"))
    expected = {entry["path"]: entry for entry in manifest["files"]}
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
    print(json.dumps({"files": len(actual), "status": "PASS"}))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    root = args.root.resolve()
    output = root / "artifact" / "phase0-state-contract-v1"
    if args.check:
        return verify(output)
    if output.exists():
        raise FileExistsError(
            f"{output} already exists; remove the exact artifact directory "
            "before rebuilding"
        )
    output.mkdir(parents=True)

    sources = {
        root / "configs" / "revguard_state_contract_gate.json":
            output / "config.json",
        root / "docs" / "reports" / "revguard_state_contract_report.md":
            output / "REPORT.md",
        root / "results" / "phase0" / "revguard" / "revguard_n1" / "summary.json":
            output / "summary.json",
        root / "scripts" / "remote" / "run_revguard_same_input.py":
            output / "scripts" / "run_same_input.py",
        root / "scripts" / "remote" / "run_revguard_selective.py":
            output / "scripts" / "run_selective.py",
        root / "scripts" / "finalize_revguard_state_contract.py":
            output / "scripts" / "finalize.py",
        root / "scripts" / "validate_revguard_state_contract.py":
            output / "scripts" / "validate.py",
    }
    raw = root / "results" / "phase0" / "revguard" / "revguard_n1"
    selected_patterns = [
        "same-input-n1-bfloat16-d30-c16-*.json",
        "same-input-n3-fp16-float16-d30-c16-*.json",
        "selective-n3-fp16-float16-d30-c16-m0.05-*.json",
    ]
    selected_raw: list[Path] = []
    for pattern in selected_patterns:
        matches = sorted(raw.glob(pattern))
        if len(matches) != 2:
            raise AssertionError(f"expected two files for {pattern}")
        selected_raw.extend(matches)
    for path in selected_raw:
        sources[path] = output / "raw" / path.name
    for source, destination in sources.items():
        if not source.is_file():
            raise FileNotFoundError(source)
        copy_text(source, destination)

    raw_index = []
    for path in sorted(raw.glob("*.json")):
        if path.name == "summary.json":
            continue
        raw_index.append(
            {
                "repository_path": path.relative_to(root).as_posix(),
                "bytes": path.stat().st_size,
                "sha256": sha256(path),
                "packaged": path in selected_raw,
            }
        )
    (output / "RAW_INDEX.json").write_text(
        json.dumps(raw_index, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    (output / "README.md").write_text(
        """# RevGuard state-contract artifact

Decision:
`LIVE_MECHANISM_GATE_PASS_DETERMINISTIC_CERTIFICATE_UNRESOLVED`.

The packaged raw subset contains the default BF16 c=16 state-projection
controls, the default FP16 c=16 precision controls, and the two FP16 live
selective-verification runs. `RAW_INDEX.json` hashes all 18 repository raw
records, including attention-backend ablations.

The live mechanism had zero observed full-output and state-projection
violations over 480 events, 7.92-9.17% verification, 4.12-4.57x single-GPU
speedup, and verifier/proposer service ratios of 0.581-0.626. The margin rule
is an empirical scheduler signal, not a deterministic certificate.
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
        "artifact": "revguard-state-contract-v1",
        "decision": (
            "LIVE_MECHANISM_GATE_PASS_"
            "DETERMINISTIC_CERTIFICATE_UNRESOLVED"
        ),
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

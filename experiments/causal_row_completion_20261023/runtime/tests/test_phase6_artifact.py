from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_phase6_summary_and_artifact_are_consistent() -> None:
    summary = json.loads(
        (ROOT / "results/phase6/summary.json").read_text(encoding="utf-8")
    )
    manifest = json.loads(
        (
            ROOT / "artifact/phase6-submission-repairs-v1/MANIFEST.json"
        ).read_text(encoding="utf-8")
    )
    assert summary["decision"] == manifest["decision"]
    assert summary["phase6a"]["decision"] == "PHASE6A_SEMANTIC_GATE_PASS"


def test_phase6_manifest_hashes() -> None:
    artifact = ROOT / "artifact/phase6-submission-repairs-v1"
    manifest = json.loads(
        (artifact / "MANIFEST.json").read_text(encoding="utf-8")
    )
    for relative, expected in manifest["files"].items():
        path = artifact / relative
        assert path.stat().st_size == expected["bytes"]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == expected[
            "sha256"
        ]
    actual = {
        str(path.relative_to(artifact)).replace("\\", "/")
        for path in artifact.rglob("*")
        if path.is_file() and path.name != "MANIFEST.json"
    }
    assert actual == set(manifest["files"])

from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_phase5_artifact_manifest_and_boundaries() -> None:
    artifact = ROOT / "artifact" / "phase5-system-hardening-v1"
    manifest = json.loads(
        (artifact / "MANIFEST.json").read_text(encoding="utf-8")
    )
    for record in manifest["files"]:
        path = artifact / record["path"]
        assert path.is_file()
        assert path.stat().st_size == record["bytes"]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == record[
            "sha256"
        ]

    summary = json.loads(
        (ROOT / "results" / "phase5" / "summary.json").read_text(
            encoding="utf-8"
        )
    )
    assert summary["decision"] == (
        "PAPER_CORE_GO_WITH_PHASE5_MEASURED_BOUNDARIES"
    )
    assert summary["all_hard_gates_pass"] is False
    assert summary["phase5c"]["cell_count"] == 8
    assert summary["phase5c"]["safe_cells"] == 7
    assert summary["phase5d"]["decision"] == (
        "PHASE5D_LIVE_SLACK_PACKING_NO_GO"
    )
    assert summary["phase5e"]["distinct_records"] == 72

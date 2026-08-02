from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


SCRIPT = (
    Path(__file__).resolve().parents[1]
    / "scripts"
    / "build_whisper_evidence_manifest.py"
)


def test_manifest_marks_large_remote_only_artifacts_and_is_not_recursive(
    tmp_path: Path,
) -> None:
    root = tmp_path / "evidence"
    root.mkdir()
    (root / "small.json").write_bytes(b"{}\n")
    (root / "large.bin").write_bytes(b"x" * 17)
    manifest = root / "MANIFEST.json"

    subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--root",
            str(root),
            "--output",
            str(manifest),
            "--remote-only-threshold-bytes",
            "16",
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    payload = json.loads(manifest.read_text(encoding="utf-8"))
    rows = {row["path"]: row for row in payload["files"]}
    assert set(rows) == {"large.bin", "small.json"}
    assert rows["small.json"]["remote_only"] is False
    assert rows["large.bin"]["remote_only"] is True
    assert payload["remote_only_file_count"] == 1
    assert payload["remote_only_bytes"] == 17

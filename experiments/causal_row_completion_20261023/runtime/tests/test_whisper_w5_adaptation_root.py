from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def test_extracts_only_fail_closed_state_mismatches(tmp_path: Path) -> None:
    source = tmp_path / "w5.json"
    output = tmp_path / "root.json"
    source.write_text(
        json.dumps({
            "model": "whisper-base.en",
            "config": {"seed": 7},
            "events": [
                {
                    "window_index": 3,
                    "minimum_margin": 0.03125,
                    "prior_prompt_tokens": 47,
                    "terminal": False,
                    "post_timing_stable_state_mismatch": True,
                    "state_error": False,
                },
                {
                    "window_index": 4,
                    "minimum_margin": 1.0,
                    "prior_prompt_tokens": 50,
                    "terminal": False,
                    "post_timing_stable_state_mismatch": False,
                },
            ],
        }),
        encoding="utf-8",
    )
    subprocess.run(
        [
            sys.executable,
            "scripts/extract_whisper_w5_adaptation_root.py",
            "--input", str(source),
            "--output", str(output),
        ],
        check=True,
    )
    row = json.loads(output.read_text(encoding="utf-8"))
    assert row["counts"]["adaptation_roots"] == 1
    assert row["audit_rows"][0]["state_error"] is True
    assert "excluded" in row["claim_boundary"]

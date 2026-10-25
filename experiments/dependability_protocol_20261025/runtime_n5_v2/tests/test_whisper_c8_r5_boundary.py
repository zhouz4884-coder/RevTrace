from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "build_whisper_c8_r5_boundary",
    ROOT / "scripts" / "build_whisper_c8_r5_boundary.py",
)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_sha256_is_stable(tmp_path: Path) -> None:
    path = tmp_path / "evidence.json"
    path.write_text("evidence\n", encoding="utf-8")
    assert MODULE.sha256(path) == (
        "ffb9a8be5f26ace0e4edc54d3112c480a187104286279284363f5896767e6ae3"
    )

from __future__ import annotations

import importlib.util
from pathlib import Path


MODULE_PATH = (
    Path(__file__).resolve().parents[1]
    / "scripts"
    / "remote"
    / "run_checkpoint_rebase_quality.py"
)
SPEC = importlib.util.spec_from_file_location(
    "run_checkpoint_rebase_quality", MODULE_PATH
)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_quality_normalization_matches_language_metric() -> None:
    assert MODULE.normalize_text("Hello, WORLD!", "English") == "hello world"
    assert MODULE.normalize_text("各个，公司。", "Chinese") == "各个公司"
    assert MODULE.error_rate("one two", "one too", "English") == 0.5
    assert MODULE.error_rate("中国", "中果", "Chinese") == 0.5


def test_edit_distance_handles_insert_delete_substitute() -> None:
    assert MODULE.edit_distance(list("abc"), list("abc")) == 0
    assert MODULE.edit_distance(list("abc"), list("axc")) == 1
    assert MODULE.edit_distance(list("abc"), list("abdc")) == 1
    assert MODULE.edit_distance(list("abc"), list("ac")) == 1

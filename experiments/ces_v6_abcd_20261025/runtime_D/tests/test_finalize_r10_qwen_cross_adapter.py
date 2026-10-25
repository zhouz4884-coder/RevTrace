from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "finalize_r10",
    ROOT / "scripts" / "finalize_r10_qwen_cross_adapter.py",
)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_expected_matrix_has_two_models_and_two_modes() -> None:
    assert set(MODULE.EXPECTED) == {
        ("Qwen3-ASR-0.6B", "dgft"),
        ("Qwen3-ASR-0.6B", "hybrid"),
        ("Qwen3-ASR-1.7B", "dgft"),
        ("Qwen3-ASR-1.7B", "hybrid"),
    }


def test_checked_in_matrix_passes_fail_closed_audit() -> None:
    config = MODULE.load_json(ROOT / "configs" / "revtrace_r10_qwen_cross_adapter.json")
    cells = [
        MODULE.audit_cell(
            ROOT / "results" / "r10_qwen_cross_adapter" / filename,
            model,
            mode,
            config["gates"],
        )
        for (model, mode), filename in MODULE.EXPECTED.items()
    ]
    assert all(cell["pass"] for cell in cells)
    assert {cell["code_commit"] for cell in cells} == {
        "f54c1ab0bb397ee648839977274d159823c37a15"
    }
    assert sum(
        cell["metrics"]["transaction_install_violations"] for cell in cells
    ) == 0
    assert sum(
        cell["metrics"]["authority_batch_repeat_mismatches"]
        + cell["metrics"]["authority_batch_vs_singleton_mismatches"]
        for cell in cells
    ) == 0

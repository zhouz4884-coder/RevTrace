from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "finalize_r10_dgft_ablation",
    ROOT / "scripts" / "finalize_r10_dgft_ablation.py",
)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_ablation_declares_three_adapters_on_two_models() -> None:
    assert set(MODULE.MODE_FILES) == {"sg", "coarse-dgft", "hybrid-dgft"}
    assert all(
        set(files) == {"Qwen3-ASR-0.6B", "Qwen3-ASR-1.7B"}
        for files in MODULE.MODE_FILES.values()
    )


def test_checked_in_sg_cells_are_exact_but_retain_tail_boundary() -> None:
    root = ROOT / "results" / "r10_qwen_cross_adapter"
    cells = [
        MODULE.audit_sg(root / filename, model)
        for model, filename in MODULE.MODE_FILES["sg"].items()
    ]
    assert all(cell["contract_match"] for cell in cells)
    assert all(not cell["slo_pass"] for cell in cells)
    assert all(cell["metrics"]["output_violations"] == 0 for cell in cells)
    assert all(cell["metrics"]["state_violations"] == 0 for cell in cells)
    assert all(cell["metrics"]["stale_commits"] == 0 for cell in cells)
    assert all(cell["metrics"]["wall_speedup"] >= 4.0 for cell in cells)


def test_all_six_cells_cover_the_same_audio_workload() -> None:
    root = ROOT / "results" / "r10_qwen_cross_adapter"
    cells = []
    for adapter, files in MODULE.MODE_FILES.items():
        for model, filename in files.items():
            cells.append(
                MODULE.audit_sg(root / filename, model)
                if adapter == "sg"
                else MODULE.audit_dgft(root / filename, model, adapter)
            )
    assert len(cells) == 6
    assert all(cell["contract_match"] for cell in cells)
    assert {cell["metrics"]["audio_seconds"] for cell in cells} == {480.0}
    assert sum(
        cell["metrics"]["output_violations"]
        + cell["metrics"]["state_violations"]
        + cell["metrics"]["stale_commits"]
        for cell in cells
    ) == 0


def test_excluded_unrecorded_run_is_repeat_control_only() -> None:
    root = ROOT / "results" / "r10_qwen_cross_adapter"
    excluded = MODULE.load_json(
        root / "diagnostics" / "qwen17-sg-r10-unrecorded.json"
    )
    accepted = MODULE.load_json(root / "sg" / "qwen17-sg-r10.json")
    assert excluded["environment"]["code_commit"] == "UNRECORDED"
    assert len(accepted["environment"]["code_commit"]) == 40
    excluded_events = {
        (event["session_id"], event["chunk_id"]): event
        for event in excluded["events"]
    }
    accepted_events = {
        (event["session_id"], event["chunk_id"]): event
        for event in accepted["events"]
    }
    assert set(excluded_events) == set(accepted_events)
    assert all(
        excluded_events[key]["selected_token_ids"]
        == accepted_events[key]["selected_token_ids"]
        for key in accepted_events
    )

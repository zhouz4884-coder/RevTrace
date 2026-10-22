from __future__ import annotations

import json
from pathlib import Path

from scripts.finalize_tail_robust_closure import (
    root_cause_diagnosis,
    stage_row,
)


ROOT = Path(__file__).resolve().parents[1]


def test_instrumented_c14_diagnosis_keeps_guard_tail() -> None:
    diagnosis = root_cause_diagnosis(
        ROOT / "results/tail_robust/c14_diagnostic/raw.json"
    )
    assert diagnosis["guard_exceeding_round_count"] == 3
    assert diagnosis["slow_round_count"] == 0
    assert diagnosis["guard_exceeding_round_classification"] == {
        "serial_proposer_then_selective_canonical": 3
    }
    assert (
        diagnosis["thermal_throttling_explanation"]
        == "not_supported_by_measured_temperature_or_clock"
    )


def test_heldout_parser_uses_release_rounds_and_online_authority() -> None:
    path = ROOT / "results/tail_robust/c12_heldout/heldout_seed_1.json"
    row = stage_row(json.loads(path.read_text(encoding="utf-8")))
    assert row["rounds"] == 90
    assert row["events"] == 1080
    assert row["deadline_miss_rounds"] == 0
    assert row["online_selection_authority_violations"] == 0

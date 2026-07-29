from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "finalize_final_closure",
    ROOT / "scripts/finalize_final_closure.py",
)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_normalization_is_language_appropriate() -> None:
    assert MODULE.normalize_text("Hello,  WORLD!", "English") == "hello world"
    assert MODULE.normalize_text("各个，公司。A1", "Chinese") == "各个公司a1"


def test_edit_distance_handles_insert_delete_substitute() -> None:
    assert MODULE.edit_distance(list("abc"), list("abc")) == 0
    assert MODULE.edit_distance(list("abc"), list("axc")) == 1
    assert MODULE.edit_distance(list("abc"), list("abdc")) == 1
    assert MODULE.edit_distance(list("abc"), list("ac")) == 1


def test_churn_is_zero_for_stable_partials() -> None:
    assert MODULE.churn(["same", "same", "same"], "English") == 0.0


def test_error_counts_match_exact_reference() -> None:
    counts = MODULE.error_counts(
        "THE QUICK BROWN FOX", "the quick brown fox.", "English"
    )
    assert counts["word_edits"] == 0
    assert counts["char_edits"] == 0


def test_paired_bootstrap_zero_delta_is_degenerate() -> None:
    rows = [
        {
            "word_edits": 1,
            "reference_words": 10,
            "char_edits": 2,
            "reference_chars": 40,
        }
        for _ in range(4)
    ]
    result = MODULE.paired_bootstrap(
        rows,
        rows,
        metric="wer",
        replicates=100,
        seed=1,
    )
    assert result["delta"] == 0.0
    assert result["ci95_low"] == 0.0
    assert result["ci95_high"] == 0.0


def test_initial_failure_summary_separates_roots_from_cascades() -> None:
    def row(episode: int, session: str, margin: float) -> dict:
        return {
            "episode": episode,
            "session_id": session,
            "proposal_minimum_margin": margin,
            "comparison": {"state_projection_token_exact": False},
        }

    result = MODULE.summarize_initial_steady_failure(
        {
            "decision": "FAIL",
            "stages": [
                {
                    "audit_violation_rows": [
                        row(0, "a", 0.03125),
                        row(0, "a", 0.5),
                        row(4, "b", 0.0625),
                    ]
                }
            ],
        }
    )
    assert result["state_violation_rows"] == 3
    assert result["root_counterexamples"] == 2
    assert result["cascade_descendants"] == 1
    assert result["root_margins"] == [0.03125, 0.0625]

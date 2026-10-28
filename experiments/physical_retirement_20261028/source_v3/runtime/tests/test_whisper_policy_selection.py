from __future__ import annotations

import json
import importlib.util
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "build_whisper_w_state_age_policy",
    ROOT / "scripts" / "build_whisper_w_state_age_policy.py",
)
assert SPEC is not None and SPEC.loader is not None
STATE_POLICY = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(STATE_POLICY)


def write_json(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload), encoding="utf-8")


def calibration(seed: int) -> dict[str, object]:
    rows = [
        {
            "terminal": False,
            "minimum_margin": 1.0,
            "state_error": False,
        }
        for _ in range(1_000)
    ]
    rows.extend(
        {
            "terminal": True,
            "minimum_margin": 100.0,
            "state_error": True,
        }
        for _ in range(100)
    )
    return {
        "model": "whisper-base.en",
        "config": {
            "concurrency": 16,
            "duration_seconds": 90,
            "window_seconds": 10,
            "model_path": "/models/base",
            "precision": "float16",
            "prompt_state_semantics": (
                "raw-segment-token-history-v5-deferred-authority"
            ),
            "calibration_state_protocol": (
                "canonical-state-capacity-rebase-v1"
            ),
            "max_prompt_tokens": 224,
            "max_new_tokens": 96,
            "torch_version": "test",
            "transformers_version": "test",
            "cuda_runtime": "test",
            "gpu_name": "test",
            "seed": seed,
        },
        "rows": rows,
    }


def test_terminal_display_rows_do_not_train_state_policy(
    tmp_path: Path,
) -> None:
    root = Path(__file__).resolve().parents[1]
    inputs: list[Path] = []
    for seed in (1, 2):
        path = tmp_path / f"calibration-{seed}.json"
        path.write_text(
            json.dumps(calibration(seed)),
            encoding="utf-8",
        )
        inputs.append(path)
    output = tmp_path / "policy.json"
    command = [
        sys.executable,
        str(root / "scripts" / "select_whisper_w_policy.py"),
    ]
    for path in inputs:
        command.extend(["--calibration", str(path)])
    command.extend(["--output", str(output)])
    subprocess.run(command, check=True, cwd=root)
    policy = json.loads(output.read_text(encoding="utf-8"))
    assert policy["decision"] == "CALIBRATION_POLICY_SELECTED"
    assert policy["counts"]["events"] == 2_000
    assert policy["counts"]["state_errors"] == 0
    assert (
        policy["selected_policy"]["verification_fraction"] == 0.0
    )


def test_state_age_policy_covers_roots_without_counting_them(
    tmp_path: Path,
) -> None:
    root = Path(__file__).resolve().parents[1]
    contract = calibration(0)["config"]
    initial = tmp_path / "initial.json"
    write_json(initial, {
        "contract": contract,
        "selected_policy": {"threshold": 0.1},
    })
    calibration_paths: list[Path] = []
    for seed in (1, 2):
        path = tmp_path / f"state-age-calibration-{seed}.json"
        write_json(path, {
            "rows": [
                {
                    "terminal": False,
                    "minimum_margin": 1.0,
                    "state_error": False,
                    "window_index": index % 9,
                    "prior_prompt_tokens": index % 140,
                }
                for index in range(1_000)
            ],
        })
        calibration_paths.append(path)
    adaptation = tmp_path / "adaptation.json"
    write_json(adaptation, {
        "audit_rows": [
            {
                "episode": 1,
                "session_id": 1,
                "window_index": 7,
                "minimum_margin": 0.5,
                "prior_prompt_tokens": 100,
                "next_prompt_tokens": 120,
                "state_error": True,
            },
        ],
    })
    output = tmp_path / "state-age-policy.json"
    command = [
        sys.executable,
        str(root / "scripts" / "build_whisper_w_state_age_policy.py"),
        "--policy",
        str(initial),
    ]
    for path in calibration_paths:
        command.extend(["--calibration", str(path)])
    command.extend([
        "--adaptation-audit",
        str(adaptation),
        "--output",
        str(output),
    ])
    subprocess.run(command, check=True, cwd=root)
    selected = json.loads(output.read_text(encoding="utf-8"))
    assert selected["decision"] == "STATE_AGE_POLICY_SELECTED"
    assert selected["counts"]["calibration_events"] == 2_000
    assert selected["counts"]["adaptation_roots"] == 1
    assert selected["selected_policy"]["caught_roots_covered"] == 1
    assert (
        selected["selected_policy"]["verification_fraction"] <= 0.20
    )
    assert selected["adaptation_root_summaries"] == [{
        "minimum_margin": 0.5,
        "next_prompt_tokens": 120,
        "prior_prompt_tokens": 100,
        "terminal": False,
        "window_index": 7,
    }]


def test_recovery_selection_prefers_zero_known_state_errors() -> None:
    common = {
        "calibration_upper_risk": 0.004,
        "late_window_index": None,
        "late_margin_threshold": None,
        "high_load_prompt_tokens": None,
        "high_load_margin_threshold": None,
        "threshold": 0.1,
    }
    fast_but_unsafe = {
        **common,
        "fast_path_state_errors": 1,
        "verification_fraction": 0.05,
    }
    safe_within_budget = {
        **common,
        "fast_path_state_errors": 0,
        "verification_fraction": 0.15,
    }
    assert STATE_POLICY.select_recovery_policy([
        fast_but_unsafe, safe_within_budget
    ]) is safe_within_budget

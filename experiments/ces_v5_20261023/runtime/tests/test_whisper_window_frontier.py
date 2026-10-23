from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "whisper_policy", ROOT / "scripts" / "build_whisper_w_state_age_policy.py"
)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_exact_window_rule_is_local() -> None:
    common = dict(
        threshold=0.01,
        age_window_index=None,
        age_margin_threshold=None,
        late_window_index=None,
        late_margin_threshold=None,
        high_load_prompt_tokens=None,
        high_load_margin_threshold=None,
        window_margin_rules=[{"window_index": 7, "margin_threshold": 0.03}],
    )
    assert MODULE.verify(
        {"window_index": 7, "minimum_margin": 0.02}, **common
    )
    assert not MODULE.verify(
        {"window_index": 6, "minimum_margin": 0.02}, **common
    )

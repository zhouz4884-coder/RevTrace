from __future__ import annotations

import importlib.util
import importlib.machinery
import sys
import types
from pathlib import Path

import numpy as np

soundfile_stub = types.ModuleType("soundfile")
soundfile_stub.__spec__ = importlib.machinery.ModuleSpec(
    "soundfile", loader=None
)
sys.modules.setdefault("soundfile", soundfile_stub)

executor_stub = types.ModuleType("whisper_batched_executor")
executor_stub.DistinctPromptWhisper = object
executor_stub.SAMPLE_RATE = 16_000
sys.modules.setdefault("whisper_batched_executor", executor_stub)


MODULE_PATH = (
    Path(__file__).resolve().parents[1]
    / "scripts"
    / "remote"
    / "run_whisper_w_quality.py"
)
SPEC = importlib.util.spec_from_file_location(
    "run_whisper_w_quality", MODULE_PATH
)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def test_first_fit_packing_does_not_stop_on_one_oversized_remainder(
    monkeypatch,
) -> None:
    # At 16 kHz, 65 s + 26 s cannot fit, but a later 20 s utterance can.
    durations = [65, 26, 20, 60, 29, 60, 29]
    records = [
        {
            "split": "test-clean",
            "path": str(index),
            "samples": seconds * MODULE.SAMPLE_RATE,
            "text": f"text {index}",
            "utterance_id": f"utt-{index}",
            "speaker_id": f"spk-{index}",
        }
        for index, seconds in enumerate(durations)
    ]
    monkeypatch.setattr(
        MODULE.random.Random, "shuffle", lambda self, values: None
    )
    monkeypatch.setattr(
        MODULE,
        "load_audio",
        lambda path: np.zeros(
            records[int(path)]["samples"], dtype=np.float32
        ),
    )
    sessions = MODULE.build_sessions(
        records,
        split="test-clean",
        count=3,
        duration_seconds=90,
        seed=0,
    )
    assert len(sessions) == 3
    utterances = [u for session in sessions for u in session.utterance_ids]
    assert len(utterances) == len(set(utterances))
    assert all(session.audio.size == 90 * MODULE.SAMPLE_RATE for session in sessions)

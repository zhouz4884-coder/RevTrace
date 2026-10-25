from __future__ import annotations

import numpy as np

from revtrace.feedback_metrics import (
    edit_distance,
    pack_disjoint_audio,
    repetition_score,
)


def test_edit_distance() -> None:
    assert edit_distance([1, 2, 3], [1, 4, 3]) == 1
    assert edit_distance([], [1, 2]) == 2


def test_repetition_score_separates_loops() -> None:
    loop = "thank you all thank you all thank you all thank you all"
    natural = "this is a short sentence with no repeated three word span"
    assert repetition_score(loop) > repetition_score(natural)


def test_pack_disjoint_audio_never_reuses_samples() -> None:
    sources = [
        np.full(4, index, dtype=np.float32) for index in (1, 2, 3)
    ]
    sessions = pack_disjoint_audio(
        sources, target_samples=3, max_sessions=4
    )
    assert len(sessions) == 4
    assert np.concatenate(sessions).tolist() == [
        1,
        1,
        1,
        1,
        2,
        2,
        2,
        2,
        3,
        3,
        3,
        3,
    ]

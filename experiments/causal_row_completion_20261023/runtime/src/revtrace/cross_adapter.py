"""Cross-architecture evidence adapters for the RevTrace transaction core.

The common contract is intentionally small: a fast path may display a
provisional revision, but only the selected authority may advance feedback
state.  Qwen's cross-adapter gate compares a fine 2-second batched branch with
a coarser canonical segment and optionally invokes the native fine-grained
singleton authority when the two evidence directions expose an omission or a
numerically fragile fine branch.
"""

from __future__ import annotations

from dataclasses import dataclass

from .dgft import classify_asymmetric_omission_conflict, coverage_units


@dataclass(frozen=True)
class CrossAdapterDecision:
    mode: str
    selected_authority: str
    replay_required: bool
    reasons: tuple[str, ...]
    forward_deficit: float
    reverse_deficit: float
    fine_minimum_margin: float


def decide_qwen_cross_adapter(
    *,
    fine_text: str,
    coarse_text: str,
    fine_minimum_margin: float,
    mode: str,
    forward_threshold: float = 0.20,
    reverse_ceiling: float = 0.20,
    risk_margin: float = 0.05,
    terminal: bool = False,
) -> CrossAdapterDecision:
    """Select the authority for one Qwen macro-revision.

    ``dgft`` always installs the coarse canonical segment.  ``hybrid`` keeps
    the same coarse authority when the evidence agrees, but replays the macro
    segment through the native 2-second singleton path when directional
    omission, low-margin numerical risk, or terminal finalization requires
    the stricter authority.  The evidence signals schedule authority; they do
    not themselves certify transcript correctness.
    """

    if mode not in {"dgft", "hybrid"}:
        raise ValueError("mode must be 'dgft' or 'hybrid'")
    if fine_minimum_margin < 0:
        raise ValueError("fine minimum margin must be non-negative")
    omission = classify_asymmetric_omission_conflict(
        fine_text,
        coarse_text,
        forward_threshold=forward_threshold,
        reverse_ceiling=reverse_ceiling,
    )
    reasons: list[str] = []
    if omission.fallback_required:
        reasons.append("directional-omission")
    if fine_minimum_margin <= risk_margin:
        reasons.append("fine-numerical-risk")
    if terminal:
        reasons.append("terminal-finalization")
    replay = mode == "hybrid" and bool(reasons)
    return CrossAdapterDecision(
        mode=mode,
        selected_authority=("fine-singleton-replay" if replay else "coarse-segment"),
        replay_required=replay,
        reasons=tuple(reasons),
        forward_deficit=omission.forward_deficit,
        reverse_deficit=omission.reverse_deficit,
        fine_minimum_margin=fine_minimum_margin,
    )


def unit_edit_rate(reference: str, hypothesis: str) -> float:
    """Levenshtein error rate over the same mixed-script coverage units."""

    left = coverage_units(reference)
    right = coverage_units(hypothesis)
    if not left:
        return 0.0 if not right else 1.0
    previous = list(range(len(right) + 1))
    for row, source in enumerate(left, start=1):
        current = [row]
        for column, target in enumerate(right, start=1):
            current.append(min(
                current[-1] + 1,
                previous[column] + 1,
                previous[column - 1] + (source != target),
            ))
        previous = current
    return previous[-1] / len(left)


def normalized_boundary_chunk_id(
    previous_chunk_id: int, fine_windows: int
) -> int:
    """Transport a coarse authority result onto the fine revision lattice."""

    if previous_chunk_id < 0:
        raise ValueError("previous chunk id must be non-negative")
    if fine_windows <= 0:
        raise ValueError("fine window count must be positive")
    return previous_chunk_id + fine_windows

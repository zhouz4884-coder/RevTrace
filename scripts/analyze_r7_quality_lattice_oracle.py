#!/usr/bin/env python3
"""Measure whether multiple legal feedback-state views can repair R7 tails.

This is an offline mechanism oracle, not a deployable selector.  It compares
the frozen EFSC full-state proposal and the already-recorded empty-state
proposal, then enumerates their per-window combinations against the session
reference.  Reference-aware choices are reported only as an upper bound.
"""

from __future__ import annotations

import argparse
import itertools
import json
import statistics
from pathlib import Path
from typing import Any, Sequence

from run_whisper_w_quality import build_sessions, word_error


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--quality", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--sessions-per-split", type=int, default=64)
    parser.add_argument("--duration-seconds", type=int, default=90)
    parser.add_argument("--seed", type=int, default=2026080701)
    return parser.parse_args()


def wer(reference: str, hypothesis: str) -> float:
    errors, words = word_error(reference, hypothesis)
    return 100.0 * errors / max(1, words)


def catastrophic(candidate: float, canonical: float) -> bool:
    delta = candidate - canonical
    return delta > 10.0 or (
        candidate > 2.0 * max(canonical, 1.0) and delta > 5.0
    )


def join(rows: Sequence[str]) -> str:
    return " ".join(value for value in rows if value).strip()


def main() -> int:
    args = parse_args()
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    quality = json.loads(args.quality.read_text(encoding="utf-8"))
    sessions = (
        build_sessions(
            manifest["records"], split="test-clean",
            count=args.sessions_per_split,
            duration_seconds=args.duration_seconds, seed=args.seed,
        )
        + build_sessions(
            manifest["records"], split="test-other",
            count=args.sessions_per_split,
            duration_seconds=args.duration_seconds, seed=args.seed + 1,
        )
    )
    strategies: dict[str, list[float]] = {
        name: [] for name in (
            "canonical", "efsc", "empty", "longer", "oracle_two_view"
        )
    }
    rows: list[dict[str, Any]] = []
    for session, recorded in zip(sessions, quality["sessions"]):
        trace = recorded["efsc_trace"]
        full = [str(event["candidate_text"]) for event in trace]
        empty = [str(event["feedback_off_text"]) for event in trace]
        longer = [
            left if len(left) >= len(right) else right
            for left, right in zip(full, empty)
        ]
        canonical_wer = float(recorded["canonical_wer"])
        values = {
            "canonical": canonical_wer,
            "efsc": wer(session.reference, join(full)),
            "empty": wer(session.reference, join(empty)),
            "longer": wer(session.reference, join(longer)),
        }
        # The expensive combinatorial oracle is needed only for sessions that
        # failed the frozen tail contract.  Non-outliers retain the deployed
        # EFSC output, making this a repair-headroom estimate rather than an
        # oracle that silently improves every session in the test set.
        best_wer = values["efsc"]
        best_mask = 0
        if bool(recorded["catastrophic_outlier"]):
            for mask in range(1 << len(full)):
                candidate = join([
                    empty[index] if mask & (1 << index) else full[index]
                    for index in range(len(full))
                ])
                score = wer(session.reference, candidate)
                if score < best_wer:
                    best_wer = score
                    best_mask = mask
        values["oracle_two_view"] = best_wer
        for name, value in values.items():
            strategies[name].append(value)
        rows.append({
            "session_id": int(recorded["session_id"]),
            "split": recorded["split"],
            "canonical_wer": canonical_wer,
            "efsc_wer": values["efsc"],
            "empty_wer": values["empty"],
            "longer_wer": values["longer"],
            "oracle_two_view_wer": best_wer,
            "oracle_empty_windows": [
                index for index in range(len(full))
                if best_mask & (1 << index)
            ],
            "efsc_catastrophic": catastrophic(values["efsc"], canonical_wer),
            "longer_catastrophic": catastrophic(values["longer"], canonical_wer),
            "oracle_catastrophic": catastrophic(best_wer, canonical_wer),
        })
    summary: dict[str, Any] = {}
    canonical = strategies["canonical"]
    for name, values in strategies.items():
        summary[name] = {
            "mean_wer": statistics.fmean(values),
            "mean_delta_vs_canonical_pp": statistics.fmean(
                value - base for value, base in zip(values, canonical)
            ),
            "catastrophic_outliers": sum(
                catastrophic(value, base)
                for value, base in zip(values, canonical)
            ),
        }
    payload = {
        "schema_version": 1,
        "study": "R7 legal two-view feedback-lattice quality oracle",
        "sessions": len(rows),
        "summary": summary,
        "rows": rows,
        "claim_boundary": (
            "oracle_two_view uses ground-truth references and is only a "
            "mechanism upper bound; longer is deployable but not certified"
        ),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(summary))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

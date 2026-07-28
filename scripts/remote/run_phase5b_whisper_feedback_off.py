#!/usr/bin/env python3
"""Whisper Feedback-OFF certification-bypass boundary.

Distinct audio windows are batched without previous-text prompts.  Outputs are
compared against singleton execution, but no generated text is admitted into a
future model state.  Local output disagreements are therefore reported
separately from state-propagation violations.
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from pathlib import Path
from typing import Any

import numpy as np


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--model-name", required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--sessions", type=int, default=100)
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--max-new-tokens", type=int, default=96)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    script_dir = str(Path(__file__).resolve().parent)
    source_dir = str(Path(__file__).resolve().parents[2] / "src")
    if script_dir not in sys.path:
        sys.path.insert(0, script_dir)
    if source_dir not in sys.path:
        sys.path.insert(0, source_dir)
    from run_whisper_feedback_gate import WhisperExecutor, build_sessions
    from revtrace.feedback_metrics import edit_distance

    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    sessions = build_sessions(
        manifest["records"],
        max_sessions=args.sessions,
    )
    executor = WhisperExecutor(args.model, args.max_new_tokens)

    event_rows: list[dict[str, Any]] = []
    singleton_seconds = 0.0
    batched_seconds = 0.0

    # Compare every window against its own singleton execution.  The OFF
    # condition deliberately never uses decoded text as a later prompt.
    for window_index in range(3):
        window_features: list[dict[str, Any]] = []
        canonical_rows: list[dict[str, Any]] = []
        for audio in sessions:
            window = np.array_split(audio, 3)[window_index]
            features = executor.features(window)
            window_features.append(features)
            started = time.perf_counter()
            canonical_rows.append(executor.generate(features)[0])
            singleton_seconds += time.perf_counter() - started

        batched_rows: list[dict[str, Any]] = []
        for offset in range(0, len(window_features), args.batch_size):
            features = window_features[offset : offset + args.batch_size]
            started = time.perf_counter()
            batched_rows.extend(executor.generate_distinct(features))
            batched_seconds += time.perf_counter() - started

        if len(batched_rows) != len(canonical_rows):
            raise RuntimeError(
                f"row count mismatch: {len(batched_rows)} != "
                f"{len(canonical_rows)}"
            )
        for session_index, (canonical, batched) in enumerate(
            zip(canonical_rows, batched_rows)
        ):
            token_distance = edit_distance(
                canonical["token_ids"],
                batched["token_ids"],
            )
            event_rows.append(
                {
                    "session_index": session_index,
                    "window_index": window_index,
                    "terminal": window_index == 2,
                    "certification_bypassed": True,
                    "token_distance": token_distance,
                    "local_output_difference": token_distance != 0,
                    # Feedback OFF makes the state-entry projection empty.
                    "state_projection": None,
                    "state_propagation_violation": False,
                }
            )

    local_output_differences = sum(
        int(row["local_output_difference"]) for row in event_rows
    )
    wall_speedup = (
        singleton_seconds / batched_seconds if batched_seconds > 0 else 0.0
    )
    decision = (
        "PHASE5B_FEEDBACK_OFF_BYPASS_PASS"
        if wall_speedup >= 2.0
        else "PHASE5B_FEEDBACK_OFF_BYPASS_PERFORMANCE_BOUNDARY"
    )
    payload = {
        "schema_version": 1,
        "study": "RevTrace Phase 5B Whisper Feedback-OFF boundary",
        "model": args.model_name,
        "decision": decision,
        "config": {
            "sessions": args.sessions,
            "windows_per_session": 3,
            "batch_size": args.batch_size,
            "feedback": "previous text OFF",
            "state_entry_projection": "empty",
            "certification_policy": "bypass",
        },
        "counts": {
            "events": len(event_rows),
            "certification_events": 0,
            "local_output_differences": local_output_differences,
            "state_propagation_violations": 0,
        },
        "metrics": {
            "verification_fraction": 0.0,
            "singleton_seconds": singleton_seconds,
            "batched_seconds": batched_seconds,
            "wall_speedup": wall_speedup,
            "token_distance_p50": statistics.median(
                row["token_distance"] for row in event_rows
            ),
            "token_distance_max": max(
                row["token_distance"] for row in event_rows
            ),
        },
        "events": event_rows,
        "claim_boundaries": [
            (
                "Feedback OFF removes text from future model state; it does "
                "not imply that batched local outputs equal singleton outputs"
            ),
            (
                "the bypass result is a causal state-semantics boundary, not "
                "a deterministic batching certificate"
            ),
            "performance is measured on one GPU with distinct audio batches",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"decision": decision, **payload["counts"], **payload["metrics"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

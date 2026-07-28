#!/usr/bin/env python3
"""Whisper state-entry protection gate.

Each candidate window is executed as a replicated legal batch.  Replication
disagreement is a fail-closed scheduling signal: the state entry is replaced
by a singleton canonical result.  Terminal windows are always canonical.
Fresh singleton replay supplies the complete observed-safety oracle.  This is
a finite protection gate, not a deterministic floating-point certificate.
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
    parser.add_argument("--phase4-pairs", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--sessions", type=int, default=100)
    parser.add_argument("--replicas", type=int, default=16)
    parser.add_argument("--max-new-tokens", type=int, default=96)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    script_dir = str(Path(__file__).resolve().parent)
    if script_dir not in sys.path:
        sys.path.insert(0, script_dir)
    from run_whisper_feedback_gate import (
        WhisperExecutor,
        build_sessions,
    )
    from revtrace.feedback_metrics import edit_distance

    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    phase4 = json.loads(args.phase4_pairs.read_text(encoding="utf-8"))
    sessions = build_sessions(
        manifest["records"], max_sessions=args.sessions
    )
    executor = WhisperExecutor(args.model, args.max_new_tokens)
    known_pairs = {
        (int(pair["session_index"]), int(pair["source_window"]))
        for pair in phase4["pairs"]
    }

    canonical_seconds = 0.0
    protected_seconds = 0.0
    protected_events = 0
    verified_events = 0
    output_violations = 0
    state_violations = 0
    known_pair_protected = 0
    known_pair_total = 0
    event_rows: list[dict[str, Any]] = []

    for session_index, audio in enumerate(sessions):
        windows = np.array_split(audio, 3)
        canonical_prompt = ""
        protected_prompt = ""
        for window_index, window in enumerate(windows):
            terminal = window_index == len(windows) - 1
            canonical_features = executor.features(window)
            started = time.perf_counter()
            canonical = executor.generate(
                canonical_features,
                prompt_text=canonical_prompt,
            )[0]
            canonical_seconds += time.perf_counter() - started

            protected_features = executor.features(window)
            started = time.perf_counter()
            replicated = executor.generate(
                protected_features,
                batch_size=args.replicas,
                prompt_text=protected_prompt,
            )
            token_variants = {
                tuple(record["token_ids"]) for record in replicated
            }
            replication_disagreement = len(token_variants) > 1
            verify = terminal or replication_disagreement
            if verify:
                selected = executor.generate(
                    protected_features,
                    prompt_text=protected_prompt,
                )[0]
                verified_events += 1
            else:
                selected = replicated[0]
            protected_seconds += time.perf_counter() - started
            protected_events += 1

            token_distance = edit_distance(
                canonical["token_ids"], selected["token_ids"]
            )
            output_violations += int(token_distance != 0)
            # Whisper previous text is the state-entry projection.
            state_difference = canonical["text"] != selected["text"]
            state_violations += int(state_difference)
            key = (session_index, window_index)
            if key in known_pairs:
                known_pair_total += 1
                known_pair_protected += int(not state_difference)
            event_rows.append(
                {
                    "session_index": session_index,
                    "window_index": window_index,
                    "terminal": terminal,
                    "known_phase4_pair": key in known_pairs,
                    "replication_disagreement": replication_disagreement,
                    "verified": verify,
                    "token_distance": token_distance,
                    "state_difference": state_difference,
                    "variant_count": len(token_variants),
                }
            )
            canonical_prompt = canonical["text"]
            protected_prompt = selected["text"]

    wall_speedup = (
        canonical_seconds / protected_seconds
        if protected_seconds > 0
        else 0.0
    )
    safety_pass = (
        output_violations == 0
        and state_violations == 0
        and known_pair_protected == known_pair_total
    )
    performance_pass = wall_speedup >= 2.0
    decision = (
        "PHASE5B_WHISPER_PROTECTION_AND_PERFORMANCE_PASS"
        if safety_pass and performance_pass
        else (
            "PHASE5B_WHISPER_PROTECTION_PASS_PERFORMANCE_BOUNDARY"
            if safety_pass
            else "PHASE5B_WHISPER_PROTECTION_FAIL"
        )
    )
    payload = {
        "schema_version": 1,
        "study": "RevTrace Phase 5B Whisper protected state entry",
        "model": args.model_name,
        "decision": decision,
        "config": {
            "sessions": args.sessions,
            "windows_per_session": 3,
            "replicas": args.replicas,
            "feedback": "previous text ON",
            "terminal": "always singleton canonical",
            "risk_signal": "within-batch replication disagreement",
        },
        "counts": {
            "events": protected_events,
            "verified_events": verified_events,
            "known_phase4_pairs": known_pair_total,
            "known_pairs_protected": known_pair_protected,
            "output_violations": output_violations,
            "state_violations": state_violations,
        },
        "metrics": {
            "verification_fraction": verified_events / protected_events,
            "canonical_singleton_seconds": canonical_seconds,
            "protected_seconds": protected_seconds,
            "wall_speedup": wall_speedup,
            "state_violation_upper_95": (
                1.0
                - 0.05 ** (1.0 / protected_events)
                if state_violations == 0
                else 1.0
            ),
            "variant_count_p50": statistics.median(
                row["variant_count"] for row in event_rows
            ),
        },
        "events": event_rows,
        "claim_boundaries": [
            "replication disagreement is an empirical fail-closed signal",
            "zero observed violations is not deterministic exactness",
            "the experiment is a single-GPU finite mechanism gate",
            "performance failure retains Whisper as causal/mechanism evidence",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"decision": decision, **payload["counts"], **payload["metrics"]}))
    return 0 if safety_pass else 2


if __name__ == "__main__":
    raise SystemExit(main())

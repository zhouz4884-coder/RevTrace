#!/usr/bin/env python3
"""Reference-free R9 development probe for fine/coarse coverage conflicts.

The online features are computed only from two independently scheduled model
views.  WER/outlier labels are copied from the completed quality run after all
generation has finished and are used only to audit/select a frozen rule.
"""

from __future__ import annotations

import argparse
import json
import re
import time
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

import numpy as np

from run_whisper_w_quality import build_sessions
from whisper_batched_executor import DistinctPromptWhisper, SAMPLE_RATE


WORD = re.compile(r"[A-Za-z0-9']+")


def words(text: str) -> list[str]:
    return [match.group(0).lower() for match in WORD.finditer(text)]


def coverage_features(fine: str, coarse: str) -> dict[str, float]:
    left, right = words(fine), words(coarse)
    blocks = SequenceMatcher(None, left, right, autojunk=False).get_matching_blocks()
    matched = sum(block.size for block in blocks)
    return {
        "fine_words": float(len(left)),
        "coarse_words": float(len(right)),
        "matched_words": float(matched),
        "fine_missing_fraction": 1.0 - matched / max(1, len(left)),
        "coarse_extra_fraction": 1.0 - matched / max(1, len(right)),
        "symmetric_disagreement": 1.0 - 2.0 * matched / max(1, len(left) + len(right)),
        "length_ratio": len(right) / max(1, len(left)),
    }


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--model", type=Path, required=True)
    p.add_argument("--model-name", required=True)
    p.add_argument("--manifest", type=Path, required=True)
    p.add_argument("--coarse-result", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--sessions-per-split", type=int, default=64)
    p.add_argument("--duration-seconds", type=int, default=50)
    p.add_argument("--window-seconds", type=int, default=10)
    p.add_argument("--concurrency", type=int, default=16)
    p.add_argument("--seed", type=int, required=True)
    p.add_argument("--device", default="cuda:0")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
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
    executor = DistinctPromptWhisper(args.model, device=args.device, max_new_tokens=96)
    executor.generate([sessions[0].audio[: args.window_seconds * SAMPLE_RATE]], [()])
    prompts: list[tuple[int, ...]] = [() for _ in sessions]
    pieces: list[list[str]] = [[] for _ in sessions]
    elapsed = 0.0
    calls = 0
    windows = args.duration_seconds // args.window_seconds
    started = time.perf_counter()
    for window in range(windows):
        for offset in range(0, len(sessions), args.concurrency):
            ids = list(range(offset, min(len(sessions), offset + args.concurrency)))
            audio = [
                np.asarray(
                    sessions[sid].audio[
                        window * args.window_seconds * SAMPLE_RATE:
                        (window + 1) * args.window_seconds * SAMPLE_RATE
                    ], dtype=np.float32,
                )
                for sid in ids
            ]
            rows = executor.generate(audio, [prompts[sid] for sid in ids])
            calls += 1
            for sid, record in zip(ids, rows):
                pieces[sid].append(record.text)
                prompts[sid] = executor.advance_prompt(prompts[sid], record.token_ids)
                elapsed += record.elapsed_seconds
    wall = time.perf_counter() - started
    coarse = json.loads(args.coarse_result.read_text(encoding="utf-8"))
    mode = next(iter(coarse["modes"].values()))
    rows: list[dict[str, Any]] = []
    for sid, (segments, coarse_row) in enumerate(zip(pieces, mode["sessions"])):
        fine = " ".join(piece for piece in segments if piece)
        row = {
            "session_id": sid,
            "split": coarse_row["split"],
            "fine_text": fine,
            "fine_window_texts": list(segments),
            "coarse_text": coarse_row["text"],
            **coverage_features(fine, coarse_row["text"]),
            "offline_catastrophic_outlier": coarse_row["catastrophic_outlier"],
            "offline_delta_pp": coarse_row["delta_pp"],
        }
        rows.append(row)
    payload = {
        "schema_version": 1,
        "study": "R9 cross-granularity coverage probe",
        "model_name": args.model_name,
        "config": vars(args) | {
            "model": str(args.model), "manifest": str(args.manifest),
            "coarse_result": str(args.coarse_result), "output": str(args.output),
        },
        "fine_proposer_wall_seconds": wall,
        "fine_proposer_summed_record_seconds": elapsed,
        "fine_proposer_calls": calls,
        "rows": rows,
        "claim_boundary": (
            "coverage features are reference-free; WER labels are joined only "
            "after generation and this file is development evidence"
        ),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"sessions": len(rows), "wall_seconds": wall, "calls": calls}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

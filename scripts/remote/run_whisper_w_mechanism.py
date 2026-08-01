#!/usr/bin/env python3
"""W2/W3 cross-scale mechanism and feedback-propagation gate.

The experiment separates a legal same-input execution-shape intervention from
its future consequence.  At each source window, the W-suite singleton and
batched paths receive identical audio and prompt state.  When they disagree,
the two resulting prompt states are replayed over fixed future audio with
feedback ON and with the feedback edge removed.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import time
from pathlib import Path
from typing import Any

import numpy as np
import soundfile as sf
import torch

from revtrace.feedback_metrics import edit_distance, pack_disjoint_audio
from revtrace.whisper_state import capacity_rebase_required
from whisper_batched_executor import DistinctPromptWhisper, SAMPLE_RATE


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--model-name", required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--sessions", type=int, default=100)
    parser.add_argument("--duration-seconds", type=int, default=90)
    parser.add_argument("--window-seconds", type=int, default=10)
    parser.add_argument("--concurrency", type=int, default=16)
    parser.add_argument("--future-windows", type=int, default=2)
    parser.add_argument("--max-new-tokens", type=int, default=96)
    parser.add_argument("--seed", type=int, default=20260730)
    parser.add_argument("--device", default="cuda:0")
    return parser.parse_args()


def load_audio(path: str) -> np.ndarray:
    audio, rate = sf.read(path, dtype="float32", always_2d=False)
    if rate != SAMPLE_RATE:
        raise ValueError(f"expected 16 kHz, got {rate}: {path}")
    if audio.ndim == 2:
        audio = audio.mean(axis=1)
    return np.asarray(audio, dtype=np.float32)


def build_sessions(args: argparse.Namespace) -> list[np.ndarray]:
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    records = list(manifest["records"])
    random.Random(args.seed).shuffle(records)
    sessions = pack_disjoint_audio(
        [load_audio(record["path"]) for record in records],
        target_samples=SAMPLE_RATE * args.duration_seconds,
        max_sessions=args.sessions,
        separator_samples=SAMPLE_RATE // 10,
    )
    if len(sessions) < args.sessions:
        raise RuntimeError(
            f"only {len(sessions)} disjoint sessions; requested {args.sessions}"
        )
    return sessions


def pair_digest(
    prompt: tuple[int, ...],
    canonical: tuple[int, ...],
    proposer: tuple[int, ...],
) -> str:
    return hashlib.sha256(
        json.dumps(
                [prompt, canonical, proposer], separators=(",", ":")
        ).encode("utf-8")
    ).hexdigest()


def capacity_safe_prompt(
    executor: DistinctPromptWhisper,
    prompt: tuple[int, ...],
) -> tuple[int, ...]:
    prompt_length = len(executor.prompt_tokens(prompt))
    if capacity_rebase_required(
        prompt_length,
        declared_next_segment_tokens=executor.max_new_tokens,
        maximum_prompt_tokens=executor.max_prompt_tokens,
    ):
        return ()
    return prompt


def main() -> int:
    args = parse_args()
    sessions = build_sessions(args)
    executor = DistinctPromptWhisper(
        args.model,
        device=args.device,
        dtype=torch.float16,
        max_new_tokens=args.max_new_tokens,
    )
    if args.duration_seconds % args.window_seconds:
        raise ValueError("duration must be divisible by window-seconds")
    windows_per_session = args.duration_seconds // args.window_seconds
    if windows_per_session <= args.future_windows:
        raise ValueError("duration has no source window before future replay")
    windows = [
        list(np.array_split(audio, windows_per_session))
        for audio in sessions
    ]
    pairs: list[dict[str, Any]] = []
    same_input_events = 0
    singleton_repeat_mismatches = 0
    batch_repeat_mismatches = 0
    started = time.perf_counter()

    # Materialize each canonical prompt frontier once.  The previous version
    # rebuilt the same authority prefix independently for every source window,
    # performing a triangular number of identical singleton calls.  This
    # cache changes only experiment cost: the stored value is exactly the
    # prompt presented to the canonical source-window execution.
    authority_prompt_inputs: list[list[tuple[int, ...]]] = [
        [() for _ in range(windows_per_session - args.future_windows)]
        for _ in sessions
    ]
    running_prompts: list[tuple[int, ...]] = [() for _ in sessions]
    for source_window in range(
        windows_per_session - args.future_windows
    ):
        for session_id in range(len(sessions)):
            running_prompts[session_id] = capacity_safe_prompt(
                executor, running_prompts[session_id]
            )
            authority_prompt_inputs[session_id][source_window] = (
                running_prompts[session_id]
            )
        for begin in range(0, len(sessions), args.concurrency):
            ids = list(range(begin, min(
                begin + args.concurrency, len(sessions)
            )))
            authority = [
                executor.canonical(
                    windows[index][source_window],
                    running_prompts[index],
                )
                for index in ids
            ]
            for index, record in zip(ids, authority):
                running_prompts[index] = executor.advance_prompt(
                    running_prompts[index], record.token_ids
                )

    for source_window in range(
        windows_per_session - args.future_windows
    ):
        canonical_prompts = [
            authority_prompt_inputs[index][source_window]
            for index in range(len(sessions))
        ]

        for begin in range(0, len(sessions), args.concurrency):
            ids = list(range(begin, min(
                begin + args.concurrency, len(sessions)
            )))
            audio = [windows[index][source_window] for index in ids]
            prompts = [canonical_prompts[index] for index in ids]
            singleton = [
                executor.canonical(value, prompt)
                for value, prompt in zip(audio, prompts)
            ]
            repeat_singleton = [
                executor.canonical(value, prompt)
                for value, prompt in zip(audio, prompts)
            ]
            batch = executor.generate(audio, prompts)
            repeat_batch = executor.generate(audio, prompts)
            same_input_events += len(ids)
            singleton_repeat_mismatches += sum(
                left.token_ids != right.token_ids
                for left, right in zip(singleton, repeat_singleton)
            )
            batch_repeat_mismatches += sum(
                left.token_ids != right.token_ids
                for left, right in zip(batch, repeat_batch)
            )
            for local, session_id in enumerate(ids):
                authority = singleton[local]
                proposal = batch[local]
                if authority.token_ids == proposal.token_ids:
                    continue
                prompt_on_authority = executor.advance_prompt(
                    prompts[local], authority.token_ids
                )
                prompt_on_proposal = executor.advance_prompt(
                    prompts[local], proposal.token_ids
                )
                feedback_on_distances: list[int] = []
                feedback_off_distances: list[int] = []
                for future_offset in range(1, args.future_windows + 1):
                    prompt_on_authority = capacity_safe_prompt(
                        executor, prompt_on_authority
                    )
                    prompt_on_proposal = capacity_safe_prompt(
                        executor, prompt_on_proposal
                    )
                    future = windows[session_id][
                        source_window + future_offset
                    ]
                    on_authority = executor.canonical(
                        future, prompt_on_authority
                    )
                    on_proposal = executor.canonical(
                        future, prompt_on_proposal
                    )
                    off_left = executor.canonical(future, "")
                    off_right = executor.canonical(future, "")
                    feedback_on_distances.append(edit_distance(
                        on_authority.token_ids, on_proposal.token_ids
                    ))
                    feedback_off_distances.append(edit_distance(
                        off_left.token_ids, off_right.token_ids
                    ))
                    prompt_on_authority = executor.advance_prompt(
                        prompt_on_authority, on_authority.token_ids
                    )
                    prompt_on_proposal = executor.advance_prompt(
                        prompt_on_proposal, on_proposal.token_ids
                    )
                pairs.append({
                    "session_index": session_id,
                    "source_window": source_window,
                    "batch_slot": local,
                    "pair_sha256": pair_digest(
                        prompts[local],
                        authority.token_ids,
                        proposal.token_ids,
                    ),
                    "canonical_text": authority.text,
                    "proposer_text": proposal.text,
                    "canonical_token_ids": list(authority.token_ids),
                    "proposer_token_ids": list(proposal.token_ids),
                    "minimum_margin": proposal.minimum_margin,
                    "source_prompt_tokens": len(
                        executor.prompt_tokens(prompts[local])
                    ),
                    "feedback_on_distances": feedback_on_distances,
                    "feedback_off_distances": feedback_off_distances,
                    "propagated_with_feedback": any(
                        value > 0 for value in feedback_on_distances
                    ),
                    "propagated_without_feedback": any(
                        value > 0 for value in feedback_off_distances
                    ),
                })

    unique = {
        row["pair_sha256"]: row for row in pairs
    }
    unique_pairs = list(unique.values())
    payload = {
        "schema_version": 1,
        "study": "Whisper W2/W3 scale and feedback mechanism gate",
        "model": args.model_name,
        "config": {
            "sessions": args.sessions,
            "duration_seconds": args.duration_seconds,
            "window_seconds": args.window_seconds,
            "concurrency": args.concurrency,
            "future_windows": args.future_windows,
            "seed": args.seed,
            "dtype": "float16",
            "model_path": str(args.model.resolve()),
            "max_prompt_tokens": executor.max_prompt_tokens,
            "max_new_tokens": executor.max_new_tokens,
            "prompt_state_semantics": (
                "raw-segment-token-history-v5-deferred-authority"
            ),
            "canonical": "W-suite batch-size-one distinct-prompt path",
            "capacity_protocol": "declared-work-capacity-rebase-v2",
        },
        "counts": {
            "same_input_events": same_input_events,
            "singleton_repeat_mismatches": singleton_repeat_mismatches,
            "batch_repeat_mismatches": batch_repeat_mismatches,
            "raw_state_pairs": len(pairs),
            "distinct_state_pairs": len(unique_pairs),
            "feedback_on_propagated_pairs": sum(
                row["propagated_with_feedback"] for row in unique_pairs
            ),
            "feedback_off_propagated_pairs": sum(
                row["propagated_without_feedback"] for row in unique_pairs
            ),
        },
        "pairs": unique_pairs,
        "wall_seconds": time.perf_counter() - started,
        "claim_boundaries": [
            "same-input differences arise from a legal execution-shape change",
            "future audio is fixed and replayed on the singleton authority",
            "targeted pairs establish mechanism, not population prevalence",
            "zero pairs makes this checkpoint a performance boundary only",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(payload["counts"], sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

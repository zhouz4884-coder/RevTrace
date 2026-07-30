#!/usr/bin/env python3
"""Paired quality death gate for fixed-window checkpoint-and-rebase."""

from __future__ import annotations

import argparse
import json
import os
import random
import re
import statistics
import sys
import time
import unicodedata
from pathlib import Path
from typing import Any

import numpy as np


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument(
        "--experiment-id",
        default="revtrace-checkpoint-rebase-quality",
    )
    parser.add_argument("--model-name", required=True)
    parser.add_argument("--data-manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--duration-seconds", type=int, default=120)
    parser.add_argument("--checkpoint-seconds", type=int, default=30)
    parser.add_argument("--sessions-per-language", type=int, default=4)
    parser.add_argument(
        "--evaluation-batch-size",
        type=int,
        default=8,
        help="number of paired natural sessions evaluated per model batch",
    )
    parser.add_argument("--silence-ms", type=int, default=250)
    parser.add_argument("--gpu", default="0")
    parser.add_argument("--gpu-memory-utilization", type=float, default=0.82)
    parser.add_argument(
        "--maximum-primary-error-delta",
        type=float,
        default=0.02,
    )
    parser.add_argument(
        "--maximum-catastrophic-outliers",
        type=int,
        default=0,
    )
    parser.add_argument("--bootstrap-replicates", type=int, default=10_000)
    parser.add_argument("--bootstrap-seed", type=int, default=20260806)
    parser.add_argument(
        "--low-margin-policy",
        choices=("verify", "holdback"),
        default="verify",
        help=(
            "Quality-only state-entry policy. In holdback mode, a low-margin "
            "nonterminal proposal remains provisional and does not update the "
            "revision text state; the next checkpoint reconstructs an "
            "authoritative segment."
        ),
    )
    parser.add_argument(
        "--margin-threshold",
        type=float,
        default=0.0,
        help="Frozen state-entry margin threshold used by holdback mode.",
    )
    return parser.parse_args()


def normalize_text(text: str, language: str) -> str:
    value = unicodedata.normalize("NFKC", text).lower()
    if language == "Chinese":
        return "".join(
            character
            for character in value
            if not character.isspace()
            and not unicodedata.category(character).startswith("P")
        )
    value = re.sub(r"[^\w\s']", " ", value)
    return " ".join(value.split())


def edit_distance(left: list[str], right: list[str]) -> int:
    previous = list(range(len(right) + 1))
    for left_index, left_item in enumerate(left, start=1):
        current = [left_index]
        for right_index, right_item in enumerate(right, start=1):
            current.append(
                min(
                    current[-1] + 1,
                    previous[right_index] + 1,
                    previous[right_index - 1]
                    + int(left_item != right_item),
                )
            )
        previous = current
    return previous[-1]


def error_rate(reference: str, hypothesis: str, language: str) -> float:
    reference = normalize_text(reference, language)
    hypothesis = normalize_text(hypothesis, language)
    if language == "Chinese":
        ref_items = list(reference)
        hyp_items = list(hypothesis)
    else:
        ref_items = reference.split()
        hyp_items = hypothesis.split()
    return edit_distance(ref_items, hyp_items) / max(1, len(ref_items))


def paired_bootstrap(
    values: list[float],
    *,
    replicates: int,
    seed: int,
) -> dict[str, float | int]:
    if not values or replicates <= 0:
        raise ValueError("paired bootstrap requires values and replicates")
    rng = random.Random(seed)
    draws = []
    for _ in range(replicates):
        draws.append(
            statistics.mean(
                values[rng.randrange(len(values))]
                for _ in range(len(values))
            )
        )
    draws.sort()
    low_index = max(0, int(0.025 * replicates) - 1)
    high_index = min(replicates - 1, int(0.975 * replicates))
    return {
        "observed_mean_delta": statistics.mean(values),
        "ci95_low": draws[low_index],
        "ci95_high": draws[high_index],
        "replicates": replicates,
        "seed": seed,
    }


def hypothesis_distance(
    left: str,
    right: str,
    language: str,
) -> float:
    normalized_left = normalize_text(left, language)
    normalized_right = normalize_text(right, language)
    if language == "Chinese":
        left_items = list(normalized_left)
        right_items = list(normalized_right)
    else:
        left_items = normalized_left.split()
        right_items = normalized_right.split()
    return edit_distance(left_items, right_items) / max(1, len(left_items))


def main() -> int:
    args = parse_args()
    if (
        args.duration_seconds % args.checkpoint_seconds
        or args.checkpoint_seconds % 2
        or args.evaluation_batch_size <= 0
    ):
        raise ValueError("checkpoint must be an even divisor of duration")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    script_dir = str(Path(__file__).resolve().parent)
    if script_dir not in sys.path:
        sys.path.insert(0, script_dir)

    from run_revbatch_gate import (
        SAMPLE_RATE,
        apply_output,
        prepare_job,
        read_audio,
    )
    from run_revtrace_dual_gpu import build_asr
    from run_revguard_same_input import (
        candidate_record,
        state_projection_record,
    )
    source_dir = str(Path(__file__).resolve().parents[2] / "src")
    if source_dir not in sys.path:
        sys.path.insert(0, source_dir)
    from revtrace.long_horizon import (
        append_checkpoint_history,
        checkpoint_payload,
        checkpoint_due,
    )

    manifest = json.loads(args.data_manifest.read_text(encoding="utf-8"))
    grouped: dict[str, list[dict[str, Any]]] = {
        "English": [],
        "Chinese": [],
    }
    for record in manifest["records"]:
        language = str(record["language"])
        if language in grouped and record.get("reference"):
            grouped[language].append(dict(record))
    needed = args.sessions_per_language
    if any(len(grouped[language]) < needed for language in grouped):
        raise RuntimeError("annotated manifest lacks language coverage")

    target_samples = args.duration_seconds * SAMPLE_RATE
    silence = np.zeros(
        (args.silence_ms * SAMPLE_RATE // 1000,), dtype=np.float32
    )

    def make_stream(language: str, stream_index: int) -> dict[str, Any]:
        candidates = grouped[language]
        pieces = []
        references = []
        source_ids = []
        total = 0
        for offset in range(len(candidates)):
            record = candidates[
                (stream_index * 13 + offset) % len(candidates)
            ]
            if record["sample_id"] in source_ids:
                raise RuntimeError(
                    "annotated source pool is too short without repetition"
                )
            audio = read_audio(Path(record["path"]))
            separator_samples = int(silence.size) if pieces else 0
            if total + separator_samples + int(audio.size) > target_samples:
                continue
            if pieces and silence.size:
                pieces.append(silence)
                total += int(silence.size)
            pieces.append(audio)
            total += int(audio.size)
            references.append(str(record["reference"]))
            source_ids.append(str(record["sample_id"]))
            if target_samples - total < SAMPLE_RATE:
                break
        if not pieces:
            raise RuntimeError("no annotated utterance fits the target")
        if total < target_samples:
            pieces.append(
                np.zeros((target_samples - total,), dtype=np.float32)
            )
        return {
            "session_id": f"{language}-{stream_index:02d}",
            "language": language,
            "audio": np.concatenate(pieces)[:target_samples],
            "reference": " ".join(references),
            "source_ids": source_ids,
        }

    streams = [
        make_stream(language, index)
        for language in ("English", "Chinese")
        for index in range(args.sessions_per_language)
    ]
    os.environ["CUDA_VISIBLE_DEVICES"] = args.gpu
    asr = build_asr(
        str(args.model),
        "float16",
        args.gpu_memory_utilization,
        max_model_len=4096,
        max_num_seqs=min(args.evaluation_batch_size, len(streams)),
    )

    def run(mode: str, active_streams: list[dict[str, Any]]) -> dict[str, Any]:
        states = [
            asr.init_streaming_state(
                language=stream["language"],
                unfixed_chunk_num=2,
                unfixed_token_num=5,
                chunk_size_sec=2.0,
            )
            for stream in active_streams
        ]
        histories = ["" for _ in active_streams]
        partials = [[] for _ in active_streams]
        boundary_snapshots: dict[str, list[str]] = {}
        round_rows = []
        holdback_count = 0
        for chunk_index in range(args.duration_seconds // 2):
            age_end_seconds = (chunk_index + 1) * 2
            session_terminal = chunk_index == args.duration_seconds // 2 - 1
            boundary_due = checkpoint_due(
                age_end_seconds,
                args.checkpoint_seconds,
            )
            checkpoint = bool(
                mode == "rebase"
                and boundary_due
            )
            terminal = session_terminal or checkpoint
            jobs = []
            prefixes = []
            round_started = time.perf_counter()
            for stream, state in zip(active_streams, states):
                begin = chunk_index * 2 * SAMPLE_RATE
                end = begin + 2 * SAMPLE_RATE
                job, prefix = prepare_job(
                    asr,
                    state,
                    stream["audio"][begin:end],
                    tail=terminal,
                )
                jobs.append(job)
                prefixes.append(prefix)
            outputs = asr.model.generate(
                jobs,
                sampling_params=asr.sampling_params,
                use_tqdm=False,
            )
            current_texts = ["" for _ in active_streams]
            round_holdbacks = 0
            for position, (state, output, prefix) in enumerate(
                zip(states, outputs, prefixes)
            ):
                selected = candidate_record(output)
                selected_projection = state_projection_record(
                    asr,
                    state,
                    prefix,
                    selected,
                    terminal=terminal,
                )
                low_margin = (
                    selected["minimum_margin"] is None
                    or float(selected["minimum_margin"])
                    <= args.margin_threshold
                )
                held_back = bool(
                    mode == "rebase"
                    and not terminal
                    and args.low_margin_policy == "holdback"
                    and low_margin
                )
                if held_back:
                    # prepare_job already advanced the audio frontier.  The
                    # candidate may be shown provisionally, but it is barred
                    # from the textual revision state until an authoritative
                    # checkpoint reconstructs the segment.
                    round_holdbacks += 1
                    holdback_count += 1
                    provisional_text = (
                        prefix + str(selected["text"])
                    ).strip()
                    partials[position].append(provisional_text)
                    current_texts[position] = provisional_text
                else:
                    applied = apply_output(state, output, prefix)
                    partials[position].append(str(applied["text"]))
                    current_texts[position] = str(applied["text"]).strip()
                if checkpoint:
                    segment_text = checkpoint_payload(
                        prefix=prefix,
                        selected=selected,
                        selected_projection=selected_projection,
                    )
                    if segment_text != current_texts[position]:
                        raise AssertionError(
                            "quality path and service checkpoint payload differ"
                        )
                    histories[position] = append_checkpoint_history(
                        histories[position],
                        segment_text,
                    )
                    current_texts[position] = histories[position]
                    if not session_terminal:
                        states[position] = asr.init_streaming_state(
                            context=histories[position],
                            language=active_streams[position]["language"],
                            unfixed_chunk_num=2,
                            unfixed_token_num=5,
                            chunk_size_sec=2.0,
                        )
            if boundary_due:
                boundary_snapshots[str(age_end_seconds)] = current_texts
            round_rows.append(
                {
                    "chunk_index": chunk_index,
                    "age_end_seconds": age_end_seconds,
                    "checkpoint": checkpoint,
                    "holdback_count": round_holdbacks,
                    "service_seconds": time.perf_counter() - round_started,
                }
            )
        finals = [
            histories[position]
            if mode == "rebase"
            else states[position].text
            for position in range(len(active_streams))
        ]
        return {
            "finals": finals,
            "partials": partials,
            "rounds": round_rows,
            "boundary_snapshots": boundary_snapshots,
            "holdback_count": holdback_count,
        }

    def run_all(mode: str) -> dict[str, Any]:
        combined: dict[str, Any] = {
            "finals": [],
            "partials": [],
            "rounds": [],
            "boundary_snapshots": {},
            "holdback_count": 0,
        }
        for start in range(0, len(streams), args.evaluation_batch_size):
            batch = streams[start : start + args.evaluation_batch_size]
            result = run(mode, batch)
            combined["finals"].extend(result["finals"])
            combined["partials"].extend(result["partials"])
            combined["holdback_count"] += result["holdback_count"]
            for row in result["rounds"]:
                combined["rounds"].append(
                    {
                        **row,
                        "evaluation_batch_start": start,
                        "evaluation_batch_size": len(batch),
                    }
                )
            for age_key, snapshots in result["boundary_snapshots"].items():
                combined["boundary_snapshots"].setdefault(
                    age_key,
                    [],
                ).extend(snapshots)
        return combined

    continuous = run_all("continuous")
    rebase = run_all("rebase")
    paired = []
    for position, stream in enumerate(streams):
        language = stream["language"]
        continuous_rate = error_rate(
            stream["reference"],
            continuous["finals"][position],
            language,
        )
        rebase_rate = error_rate(
            stream["reference"],
            rebase["finals"][position],
            language,
        )
        checkpoint_boundary_edits = {}
        for age_key in sorted(
            rebase["boundary_snapshots"],
            key=lambda value: int(value),
        ):
            checkpoint_boundary_edits[age_key] = hypothesis_distance(
                continuous["boundary_snapshots"][age_key][position],
                rebase["boundary_snapshots"][age_key][position],
                language,
            )
        paired.append(
            {
                "session_id": stream["session_id"],
                "language": language,
                "source_ids": stream["source_ids"],
                "reference": stream["reference"],
                "continuous_transcript": continuous["finals"][position],
                "rebase_transcript": rebase["finals"][position],
                "continuous_primary_error_rate": continuous_rate,
                "rebase_primary_error_rate": rebase_rate,
                "primary_error_delta": rebase_rate - continuous_rate,
                "checkpoint_boundary_edit_rates": (
                    checkpoint_boundary_edits
                ),
                "catastrophic_outlier": (
                    rebase_rate - continuous_rate >= 0.20
                ),
            }
        )

    language_rows = {}
    for language_index, language in enumerate(("English", "Chinese")):
        subset = [row for row in paired if row["language"] == language]
        boundary_metrics = {}
        for age_key in sorted(
            continuous["boundary_snapshots"],
            key=lambda value: int(value),
        ):
            values = [
                row["checkpoint_boundary_edit_rates"][age_key]
                for row in subset
            ]
            boundary_metrics[age_key] = {
                "mean_continuous_rebase_edit_rate": statistics.mean(values),
                "maximum_continuous_rebase_edit_rate": max(values),
            }
        language_rows[language] = {
            "metric": "wer" if language == "English" else "cer",
            "sessions": len(subset),
            "continuous_error_rate_mean": statistics.mean(
                row["continuous_primary_error_rate"] for row in subset
            ),
            "rebase_error_rate_mean": statistics.mean(
                row["rebase_primary_error_rate"] for row in subset
            ),
            "mean_delta": statistics.mean(
                row["primary_error_delta"] for row in subset
            ),
            "paired_bootstrap": paired_bootstrap(
                [row["primary_error_delta"] for row in subset],
                replicates=args.bootstrap_replicates,
                seed=args.bootstrap_seed + language_index,
            ),
            "checkpoint_boundary_analysis": boundary_metrics,
            "catastrophic_outliers": sum(
                row["catastrophic_outlier"] for row in subset
            ),
        }
    passed = bool(
        all(
            row["mean_delta"] <= args.maximum_primary_error_delta
            for row in language_rows.values()
        )
        and sum(row["catastrophic_outlier"] for row in paired)
        <= args.maximum_catastrophic_outliers
    )
    payload = {
        "schema_version": 1,
        "experiment_id": args.experiment_id,
        "study": "Authoritative checkpoint-and-rebase paired quality gate",
        "decision": (
            "CHECKPOINT_REBASE_QUALITY_PASS"
            if passed
            else "CHECKPOINT_REBASE_QUALITY_FAIL"
        ),
        "model": args.model_name,
        "dtype": "float16",
        "duration_seconds": args.duration_seconds,
        "checkpoint_seconds": args.checkpoint_seconds,
        "sessions_per_language": args.sessions_per_language,
        "evaluation_batch_size": args.evaluation_batch_size,
        "maximum_primary_error_delta": (
            args.maximum_primary_error_delta
        ),
        "maximum_catastrophic_outliers": (
            args.maximum_catastrophic_outliers
        ),
        "bootstrap_replicates": args.bootstrap_replicates,
        "bootstrap_seed": args.bootstrap_seed,
        "state_entry_policy": {
            "low_margin_policy": args.low_margin_policy,
            "margin_threshold": args.margin_threshold,
            "rebase_provisional_holdbacks": rebase["holdback_count"],
        },
        "language_metrics": language_rows,
        "paired_sessions": paired,
        "continuous_rounds": continuous["rounds"],
        "rebase_rounds": rebase["rounds"],
        "claim_boundaries": [
            (
                "quality is a paired natural concatenated-utterance death "
                "gate, not a production prevalence estimate"
            ),
            (
                "the experiment isolates rebase and holdback quality under "
                "the same FP16 batched execution shape; it does not certify "
                "state-entry risk"
            ),
            (
                "checkpoint text is versioned context and accumulated audio "
                "is reset exactly every declared checkpoint interval"
            ),
            (
                "paired bootstrap intervals quantify this fixed natural "
                "session sample; they are not a deterministic equivalence "
                "certificate"
            ),
        ],
    }
    args.output.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"decision": payload["decision"]}))
    return 0 if passed else 2


if __name__ == "__main__":
    raise SystemExit(main())

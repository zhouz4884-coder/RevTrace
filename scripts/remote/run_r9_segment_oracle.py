#!/usr/bin/env python3
"""R9.1 legal quality/compute oracle for canonical segment authority.

No reference transcript, WER, or prior canonical output is consulted while a
trajectory is generated.  References are read only after every fixed policy
has completed, for offline evaluation.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import statistics
import time
from pathlib import Path
from typing import Any, Sequence

import numpy as np

from revtrace.dgft import adaptive_audio_plan, fixed_segment_plan
from revtrace.whisper_state import capacity_rebase_required
from run_whisper_w_quality import bootstrap_upper, build_sessions, word_error
from whisper_batched_executor import DistinctPromptWhisper, SAMPLE_RATE


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--model-name", required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--source-quality", type=Path)
    parser.add_argument("--continuous-result", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--sessions-per-split", type=int, default=64)
    parser.add_argument("--duration-seconds", type=int, default=90)
    parser.add_argument("--window-seconds", type=int, default=10)
    parser.add_argument("--concurrency", type=int, default=16)
    parser.add_argument("--modes", nargs="+", default=["sequential", "fused20", "fused30"])
    parser.add_argument("--reference-max-new-tokens", type=int, default=96)
    parser.add_argument("--fused-max-new-tokens", type=int, default=192)
    parser.add_argument("--adaptive-min-seconds", type=float, default=15.0)
    parser.add_argument("--adaptive-max-seconds", type=float, default=30.0)
    parser.add_argument(
        "--segment-salvage-yield-threshold", type=float, default=0.0,
        help="Reference-free tokens/audio-second floor; zero disables salvage.",
    )
    parser.add_argument("--segment-salvage-max-steps", type=int, default=96)
    parser.add_argument(
        "--session-salvage-on-conflict",
        action=argparse.BooleanOptionalAction,
        default=False,
    )
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--bootstrap-seed", type=int, required=True)
    parser.add_argument("--bootstrap-replicates", type=int, default=10_000)
    parser.add_argument("--device", default="cuda:0")
    parser.add_argument(
        "--quality-only", action=argparse.BooleanOptionalAction, default=False
    )
    return parser.parse_args()


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def outlier(canonical_wer: float, candidate_wer: float) -> bool:
    delta = candidate_wer - canonical_wer
    return delta > 10.0 or (
        candidate_wer > 2.0 * max(canonical_wer, 1.0) and delta > 5.0
    )


def continuous_authority_seconds(payload: dict[str, Any]) -> float:
    metrics = payload["metrics"]
    # R8 accounts raw-lineage canonical work in capsule_seconds and additional
    # cutset/terminal singleton work in authority_seconds.
    return float(metrics.get("capsule_seconds", 0.0)) + float(
        metrics.get("authority_seconds", 0.0)
    )


def evaluate_rows(
    *,
    outputs: Sequence[str],
    sessions: Sequence[Any],
    source_rows: Sequence[dict[str, Any]],
    bootstrap_seed: int,
    bootstrap_replicates: int,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    deltas: list[float] = []
    for sid, (text, session, source) in enumerate(
        zip(outputs, sessions, source_rows)
    ):
        errors, words = word_error(session.reference, text)
        wer = 100.0 * errors / max(1, words)
        canonical_wer = float(source["canonical_wer"])
        delta = wer - canonical_wer
        deltas.append(delta)
        rows.append({
            "session_id": sid,
            "split": session.split,
            "utterance_ids": list(session.utterance_ids),
            "canonical_wer": canonical_wer,
            "wer": wer,
            "delta_pp": delta,
            "catastrophic_outlier": outlier(canonical_wer, wer),
            "text": text,
        })
    split_metrics: dict[str, Any] = {}
    for offset, split in enumerate(("test-clean", "test-other")):
        values = [row["delta_pp"] for row in rows if row["split"] == split]
        split_metrics[split] = {
            "sessions": len(values),
            "mean_delta_pp": statistics.fmean(values),
            "bootstrap_95_upper_pp": bootstrap_upper(
                values,
                seed=bootstrap_seed + offset + 1,
                replicates=bootstrap_replicates,
            ),
            "catastrophic_outliers": sum(
                bool(row["catastrophic_outlier"])
                for row in rows if row["split"] == split
            ),
        }
    mean_delta = statistics.fmean(deltas)
    upper = bootstrap_upper(
        deltas, seed=bootstrap_seed, replicates=bootstrap_replicates
    )
    metrics = {
        "sessions": len(rows),
        "catastrophic_outliers": sum(
            bool(row["catastrophic_outlier"]) for row in rows
        ),
        "mean_delta_pp": mean_delta,
        "bootstrap_95_upper_pp": upper,
        "split_metrics": split_metrics,
    }
    metrics["quality_gate_pass"] = (
        metrics["catastrophic_outliers"] == 0
        and mean_delta <= 1.0
        and upper <= 2.0
        and all(
            value["catastrophic_outliers"] == 0
            and value["mean_delta_pp"] <= 1.0
            and value["bootstrap_95_upper_pp"] <= 2.0
            for value in split_metrics.values()
        )
    )
    return rows, metrics


def run_mode(
    *,
    mode: str,
    executor: DistinctPromptWhisper,
    sessions: Sequence[Any],
    windows_per_session: int,
    window_seconds: int,
    adaptive_min_seconds: float,
    adaptive_max_seconds: float,
) -> tuple[
    list[str], float, int, int, float,
    list[list[dict[str, Any]]], dict[str, Any]
]:
    if mode == "sequential":
        windows_per_segment = 1
    elif mode == "fused20":
        windows_per_segment = 20 // window_seconds
    elif mode == "fused30":
        windows_per_segment = 30 // window_seconds
    elif mode in {"adaptive15_30", "adaptive15_30_reset"}:
        windows_per_segment = 0
    else:
        raise ValueError(f"unsupported R9.1 mode: {mode}")
    outputs: list[str] = []
    traces: list[list[dict[str, Any]]] = []
    invocations = 0
    audio_seconds = 0.0
    started = time.perf_counter()
    for session in sessions:
        windows = list(np.array_split(session.audio, windows_per_session))
        if mode.startswith("adaptive"):
            sample_plan = adaptive_audio_plan(
                session.audio,
                sample_rate=SAMPLE_RATE,
                minimum_seconds=adaptive_min_seconds,
                maximum_seconds=adaptive_max_seconds,
            )
            segment_plan = tuple(
                (start, end, start / (window_seconds * SAMPLE_RATE),
                 end / (window_seconds * SAMPLE_RATE))
                for start, end in sample_plan
            )
        else:
            segment_plan = tuple(
                (
                    start * window_seconds * SAMPLE_RATE,
                    end * window_seconds * SAMPLE_RATE,
                    float(start),
                    float(end),
                )
                for start, end in fixed_segment_plan(
                    windows=windows_per_session,
                    windows_per_segment=windows_per_segment,
                )
            )
        prompt: tuple[int, ...] = ()
        pieces: list[str] = []
        trace: list[dict[str, Any]] = []
        for segment_index, (
            sample_start, sample_end, frontier_start, frontier_end
        ) in enumerate(segment_plan):
            segment_audio = np.asarray(
                session.audio[sample_start:sample_end], dtype=np.float32
            )
            if mode == "sequential" and capacity_rebase_required(
                len(executor.prompt_tokens(prompt)),
                declared_next_segment_tokens=executor.max_new_tokens,
                maximum_prompt_tokens=executor.max_prompt_tokens,
            ):
                prompt = ()
            elif mode == "adaptive15_30_reset" and segment_index:
                # A raw-audio hard boundary starts a fresh prompt epoch.  The
                # stable transcript remains committed, but no prior text is
                # granted write authority over the new acoustic segment.
                prompt = ()
            before = prompt
            record = executor.canonical(segment_audio, prompt)
            prompt = executor.advance_prompt(prompt, record.token_ids)
            invocations += 1
            audio_seconds += segment_audio.size / SAMPLE_RATE
            pieces.append(record.text)
            trace.append({
                "segment_index": segment_index,
                "audio_start_window": frontier_start,
                "audio_end_window": frontier_end,
                "audio_seconds": segment_audio.size / SAMPLE_RATE,
                "prompt_sha256": hashlib.sha256(
                    json.dumps(list(executor.prompt_tokens(before))).encode()
                ).hexdigest(),
                "token_sha256": record.token_sha256,
                "generation_steps": record.generation_steps,
                "terminated_by_eos": record.terminated_by_eos,
                "minimum_margin": record.minimum_margin,
                "first_step_no_speech_probability": (
                    record.first_step_no_speech_probability
                ),
                "average_token_log_probability": (
                    record.average_token_log_probability
                ),
                "compression_ratio": record.compression_ratio,
                "text": record.text,
            })
        outputs.append(" ".join(piece for piece in pieces if piece))
        traces.append(trace)
    elapsed = time.perf_counter() - started
    return (
        outputs, elapsed, invocations, invocations, audio_seconds, traces,
        {"salvaged_segments": 0, "salvage_invocations": 0},
    )


def run_batched_adaptive(
    *,
    mode: str,
    executor: DistinctPromptWhisper,
    sessions: Sequence[Any],
    concurrency: int,
    window_seconds: int,
    adaptive_min_seconds: float,
    adaptive_max_seconds: float,
    salvage_yield_threshold: float,
    salvage_max_steps: int,
    session_salvage_on_conflict: bool,
) -> tuple[
    list[str], float, int, int, float,
    list[list[dict[str, Any]]], dict[str, Any]
]:
    """Run dependency-respecting segment waves across independent sessions."""

    reset_prompt = mode == "adaptive15_30_reset_batch"
    plans = [
        adaptive_audio_plan(
            session.audio,
            sample_rate=SAMPLE_RATE,
            minimum_seconds=adaptive_min_seconds,
            maximum_seconds=adaptive_max_seconds,
        )
        for session in sessions
    ]
    prompts: list[tuple[int, ...]] = [() for _ in sessions]
    pieces: list[list[str]] = [[] for _ in sessions]
    traces: list[list[dict[str, Any]]] = [[] for _ in sessions]
    audio_seconds = 0.0
    batch_calls = 0
    segment_jobs = 0
    salvaged_segments = 0
    salvage_invocations = 0
    conflict_sessions: set[int] = set()
    failed_salvage_sessions: set[int] = set()
    started = time.perf_counter()
    for wave in range(max(len(plan) for plan in plans)):
        ready = [sid for sid, plan in enumerate(plans) if wave < len(plan)]
        for offset in range(0, len(ready), concurrency):
            group = ready[offset:offset + concurrency]
            audio_rows: list[np.ndarray] = []
            prompt_rows: list[tuple[int, ...]] = []
            metadata: list[tuple[int, int, int]] = []
            for sid in group:
                start, end = plans[sid][wave]
                if reset_prompt and wave:
                    prompts[sid] = ()
                audio_rows.append(np.asarray(
                    sessions[sid].audio[start:end], dtype=np.float32
                ))
                prompt_rows.append(prompts[sid])
                metadata.append((sid, start, end))
                audio_seconds += (end - start) / SAMPLE_RATE
            records = executor.generate(audio_rows, prompt_rows)
            batch_calls += 1
            segment_jobs += len(group)
            for (sid, start, end), before, record in zip(
                metadata, prompt_rows, records
            ):
                duration = (end - start) / SAMPLE_RATE
                token_yield = len(record.token_ids) / max(duration, 1e-9)
                structural_conflict = (
                    salvage_yield_threshold > 0
                    and (
                        token_yield < salvage_yield_threshold
                        or not record.terminated_by_eos
                        or float(record.compression_ratio or 0.0) > 2.4
                    )
                )
                selected_text = record.text
                selected_token_ids = record.token_ids
                salvage_trace: list[dict[str, Any]] = []
                salvage_elapsed = 0.0
                salvage_failed = False
                if structural_conflict:
                    salvage_started = time.perf_counter()
                    conflict_sessions.add(sid)
                    salvaged_segments += 1
                    replay_prompt = before
                    replay_pieces: list[str] = []
                    replay_tokens: list[int] = []
                    step = 10 * SAMPLE_RATE
                    for sub_start in range(start, end, step):
                        sub_end = min(end, sub_start + step)
                        replay = executor.generate(
                            [np.asarray(
                                sessions[sid].audio[sub_start:sub_end],
                                dtype=np.float32,
                            )],
                            [replay_prompt],
                            max_steps=salvage_max_steps,
                        )[0]
                        replay_duration = (sub_end - sub_start) / SAMPLE_RATE
                        replay_yield = len(replay.token_ids) / max(
                            replay_duration, 1e-9
                        )
                        replay_failed = (
                            replay_yield < salvage_yield_threshold
                            or not replay.terminated_by_eos
                            or float(replay.compression_ratio or 0.0) > 2.4
                        )
                        salvage_failed = salvage_failed or replay_failed
                        salvage_invocations += 1
                        replay_pieces.append(replay.text)
                        replay_tokens.extend(replay.token_ids)
                        replay_prompt = executor.advance_prompt(
                            replay_prompt, replay.token_ids
                        )
                        salvage_trace.append({
                            "audio_start_sample": sub_start,
                            "audio_end_sample": sub_end,
                            "generation_steps": replay.generation_steps,
                            "terminated_by_eos": replay.terminated_by_eos,
                            "token_sha256": replay.token_sha256,
                            "text": replay.text,
                            "token_yield_per_audio_second": replay_yield,
                            "compression_ratio": replay.compression_ratio,
                            "average_token_log_probability": (
                                replay.average_token_log_probability
                            ),
                            "replay_structural_conflict": replay_failed,
                        })
                    salvage_elapsed = time.perf_counter() - salvage_started
                    prompts[sid] = replay_prompt
                    selected_text = " ".join(
                        value for value in replay_pieces if value
                    )
                    selected_token_ids = tuple(replay_tokens)
                    if salvage_failed:
                        failed_salvage_sessions.add(sid)
                else:
                    prompts[sid] = executor.advance_prompt(
                        prompts[sid], record.token_ids
                    )
                pieces[sid].append(selected_text)
                traces[sid].append({
                    "segment_index": wave,
                    "audio_start_window": start / (window_seconds * SAMPLE_RATE),
                    "audio_end_window": end / (window_seconds * SAMPLE_RATE),
                    "audio_seconds": (end - start) / SAMPLE_RATE,
                    "authority_batch_size": len(group),
                    "authority_batch_slot": group.index(sid),
                    "prompt_sha256": hashlib.sha256(
                        json.dumps(list(executor.prompt_tokens(before))).encode()
                    ).hexdigest(),
                    "prompt_token_ids": list(executor.prompt_tokens(before)),
                    "token_sha256": record.token_sha256,
                    "generation_steps": record.generation_steps,
                    "terminated_by_eos": record.terminated_by_eos,
                    "minimum_margin": record.minimum_margin,
                    "first_step_no_speech_probability": (
                        record.first_step_no_speech_probability
                    ),
                    "average_token_log_probability": (
                        record.average_token_log_probability
                    ),
                    "compression_ratio": record.compression_ratio,
                    "token_yield_per_audio_second": token_yield,
                    "structural_conflict": structural_conflict,
                    "proposed_token_sha256": record.token_sha256,
                    "selected_token_sha256": hashlib.sha256(
                        json.dumps(list(selected_token_ids)).encode()
                    ).hexdigest(),
                    "selected_token_ids": list(selected_token_ids),
                    "next_prompt_token_ids": list(prompts[sid]),
                    "authority_elapsed_seconds": (
                        record.elapsed_seconds + salvage_elapsed
                    ),
                    "salvage_elapsed_seconds": salvage_elapsed,
                    "proposed_text": record.text,
                    "text": selected_text,
                    "salvage_trace": salvage_trace,
                    "salvage_failed": salvage_failed,
                })
    session_fallback_invocations = 0
    if session_salvage_on_conflict:
        for sid in sorted(failed_salvage_sessions):
            fallback_started = time.perf_counter()
            fallback_prompt: tuple[int, ...] = ()
            fallback_pieces: list[str] = []
            fallback_trace: list[dict[str, Any]] = []
            step = 10 * SAMPLE_RATE
            for sub_start in range(0, sessions[sid].audio.size, step):
                sub_end = min(sessions[sid].audio.size, sub_start + step)
                if capacity_rebase_required(
                    len(executor.prompt_tokens(fallback_prompt)),
                    declared_next_segment_tokens=salvage_max_steps,
                    maximum_prompt_tokens=executor.max_prompt_tokens,
                ):
                    fallback_prompt = ()
                replay = executor.generate(
                    [np.asarray(
                        sessions[sid].audio[sub_start:sub_end],
                        dtype=np.float32,
                    )],
                    [fallback_prompt],
                    max_steps=salvage_max_steps,
                )[0]
                session_fallback_invocations += 1
                audio_seconds += (sub_end - sub_start) / SAMPLE_RATE
                fallback_pieces.append(replay.text)
                fallback_prompt = executor.advance_prompt(
                    fallback_prompt, replay.token_ids
                )
                fallback_trace.append({
                    "audio_start_sample": sub_start,
                    "audio_end_sample": sub_end,
                    "token_sha256": replay.token_sha256,
                    "token_ids": list(replay.token_ids),
                    "generation_steps": replay.generation_steps,
                    "terminated_by_eos": replay.terminated_by_eos,
                    "text": replay.text,
                })
            pieces[sid] = fallback_pieces
            traces[sid].append({
                "terminal_session_fallback": True,
                "parent_conflict_segments": sum(
                    bool(row.get("structural_conflict"))
                    for row in traces[sid]
                ),
                "fallback_trace": fallback_trace,
                "next_prompt_token_ids": list(fallback_prompt),
                "fallback_elapsed_seconds": (
                    time.perf_counter() - fallback_started
                ),
            })
    elapsed = time.perf_counter() - started
    return (
        [" ".join(piece for piece in row if piece) for row in pieces],
        elapsed,
        batch_calls + salvage_invocations + session_fallback_invocations,
        segment_jobs,
        audio_seconds,
        traces,
        {
            "authority_batch_calls": batch_calls,
            "salvaged_segments": salvaged_segments,
            "salvage_invocations": salvage_invocations,
            "conflict_sessions": len(conflict_sessions),
            "failed_salvage_sessions": len(failed_salvage_sessions),
            "session_fallbacks": (
                len(failed_salvage_sessions)
                if session_salvage_on_conflict else 0
            ),
            "session_fallback_invocations": session_fallback_invocations,
        },
    )


def main() -> int:
    args = parse_args()
    if args.duration_seconds % args.window_seconds:
        raise ValueError("duration must be divisible by window size")
    legal = {
        "sequential", "fused20", "fused30",
        "adaptive15_30", "adaptive15_30_reset",
        "adaptive15_30_batch", "adaptive15_30_reset_batch",
    }
    if not set(args.modes) <= legal:
        raise ValueError(f"modes must be within {sorted(legal)}")
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    source = (
        json.loads(args.source_quality.read_text(encoding="utf-8"))
        if args.source_quality is not None else None
    )
    continuous = (
        json.loads(args.continuous_result.read_text(encoding="utf-8"))
        if args.continuous_result is not None else None
    )
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
    executors = {
        "sequential": DistinctPromptWhisper(
            args.model, device=args.device,
            max_new_tokens=args.reference_max_new_tokens,
        )
    }
    if any(mode != "sequential" for mode in args.modes):
        executors["fused"] = DistinctPromptWhisper(
            args.model, device=args.device,
            max_new_tokens=args.fused_max_new_tokens,
        )
    windows_per_session = args.duration_seconds // args.window_seconds
    if source is None:
        (
            canonical_outputs, canonical_seconds, _, _, _, canonical_traces, _
        ) = run_mode(
            mode="sequential",
            executor=executors["sequential"],
            sessions=sessions,
            windows_per_session=windows_per_session,
            window_seconds=args.window_seconds,
            adaptive_min_seconds=args.adaptive_min_seconds,
            adaptive_max_seconds=args.adaptive_max_seconds,
        )
        source_rows: list[dict[str, Any]] = []
        for session, text, trace in zip(
            sessions, canonical_outputs, canonical_traces
        ):
            errors, words = word_error(session.reference, text)
            source_rows.append({
                "utterance_ids": list(session.utterance_ids),
                "canonical_text": text,
                "canonical_wer": 100.0 * errors / max(1, words),
                "canonical_trace": trace,
            })
        source = {
            "metrics": {"canonical_seconds": canonical_seconds},
            "sessions": source_rows,
            "generated_in_process": True,
        }
    else:
        if len(sessions) != len(source["sessions"]):
            raise AssertionError("source/session count mismatch")
        for session, row in zip(sessions, source["sessions"]):
            if tuple(session.utterance_ids) != tuple(row["utterance_ids"]):
                raise AssertionError("source/session reconstruction mismatch")
    canonical_seconds = float(source["metrics"]["canonical_seconds"])
    proposal_seconds = (
        float(continuous["metrics"]["proposal_seconds"])
        if continuous is not None else 0.0
    )
    old_authority_seconds = (
        continuous_authority_seconds(continuous)
        if continuous is not None else 0.0
    )
    payload: dict[str, Any] = {
        "schema_version": 1,
        "study": "R9.1 legal canonical segment oracle",
        "model_name": args.model_name,
        "config": {
            "seed": args.seed,
            "bootstrap_seed": args.bootstrap_seed,
            "sessions_per_split": args.sessions_per_split,
            "duration_seconds": args.duration_seconds,
            "window_seconds": args.window_seconds,
            "concurrency": args.concurrency,
            "reference_max_new_tokens": args.reference_max_new_tokens,
            "fused_max_new_tokens": args.fused_max_new_tokens,
            "segment_salvage_yield_threshold": (
                args.segment_salvage_yield_threshold
            ),
            "segment_salvage_max_steps": args.segment_salvage_max_steps,
            "session_salvage_on_conflict": args.session_salvage_on_conflict,
            "model_sha256": sha256_file(args.model / "config.json"),
            "manifest_sha256": sha256_file(args.manifest),
            "source_quality_sha256": (
                sha256_file(args.source_quality)
                if args.source_quality is not None else None
            ),
            "continuous_result_sha256": (
                sha256_file(args.continuous_result)
                if args.continuous_result is not None else None
            ),
            "self_generated_canonical_source": (
                args.source_quality is None
            ),
            "quality_only": args.quality_only,
        },
        "baselines": {
            "canonical_seconds": canonical_seconds,
            "continuous_proposal_seconds": proposal_seconds,
            "continuous_authority_seconds": old_authority_seconds,
        },
        "modes": {},
        "claim_boundary": (
            "fixed policies use no online reference; reference text and WER are "
            "read only after generation; fused segment authority defines a new "
            "coarse-grained canonical trajectory and is not claimed bitwise "
            "equal to per-window singleton"
        ),
    }
    for mode in args.modes:
        executor = executors["sequential" if mode == "sequential" else "fused"]
        if mode.endswith("_batch"):
            (
                outputs, seconds, invocations, segment_jobs, audio_seconds,
                traces, mechanism_metrics,
            ) = (
                run_batched_adaptive(
                    mode=mode,
                    executor=executor,
                    sessions=sessions,
                    concurrency=args.concurrency,
                    window_seconds=args.window_seconds,
                    adaptive_min_seconds=args.adaptive_min_seconds,
                    adaptive_max_seconds=args.adaptive_max_seconds,
                    salvage_yield_threshold=(
                        args.segment_salvage_yield_threshold
                    ),
                    salvage_max_steps=args.segment_salvage_max_steps,
                    session_salvage_on_conflict=(
                        args.session_salvage_on_conflict
                    ),
                )
            )
        else:
            (
                outputs, seconds, invocations, segment_jobs, audio_seconds,
                traces, mechanism_metrics,
            ) = run_mode(
                mode=mode,
                executor=executor,
                sessions=sessions,
                windows_per_session=windows_per_session,
                window_seconds=args.window_seconds,
                adaptive_min_seconds=args.adaptive_min_seconds,
                adaptive_max_seconds=args.adaptive_max_seconds,
            )
        rows, metrics = evaluate_rows(
            outputs=outputs,
            sessions=sessions,
            source_rows=source["sessions"],
            bootstrap_seed=args.bootstrap_seed,
            bootstrap_replicates=args.bootstrap_replicates,
        )
        projected_two_gpu_wall = max(proposal_seconds, seconds)
        metrics.update({
            "authority_seconds": seconds,
            "authority_audio_seconds": audio_seconds,
            "authority_invocations": invocations,
            "authority_segment_jobs": segment_jobs,
            "authority_time_ratio_vs_continuous": (
                seconds / max(old_authority_seconds, 1e-9)
            ),
            "authority_audio_amplification": (
                audio_seconds / (len(sessions) * args.duration_seconds)
            ),
            "authority_invocation_amplification": (
                invocations / len(sessions)
            ),
            "projected_two_gpu_wall_seconds": projected_two_gpu_wall,
            "projected_two_gpu_wall_speedup": (
                canonical_seconds / projected_two_gpu_wall
                if projected_two_gpu_wall > 0 else None
            ),
            **mechanism_metrics,
        })
        if mode == "sequential":
            metrics["source_text_exact_sessions"] = sum(
                output == source_row["canonical_text"]
                for output, source_row in zip(outputs, source["sessions"])
            )
            metrics["source_text_exact"] = (
                metrics["source_text_exact_sessions"] == len(outputs)
            )
            if not metrics["source_text_exact"]:
                metrics["quality_gate_pass"] = False
        metrics["compute_gate_pass"] = (
            True if args.quality_only else (
                metrics["authority_time_ratio_vs_continuous"] <= 0.5
                or metrics["projected_two_gpu_wall_speedup"] >= 2.5
            )
        )
        metrics["r9_1_gate_pass"] = (
            metrics["quality_gate_pass"] and metrics["compute_gate_pass"]
        )
        payload["modes"][mode] = {
            "metrics": metrics,
            "sessions": rows,
            "traces": traces,
        }
        print(json.dumps({"model": args.model_name, "mode": mode, **metrics}))
    passing = [
        name for name, result in payload["modes"].items()
        if result["metrics"]["r9_1_gate_pass"]
    ]
    payload["decision"] = (
        "PASS_R9_1_LEGAL_ORACLE" if passing else "STOP_R9_AFTER_LEGAL_ORACLE"
    )
    payload["passing_modes"] = passing
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

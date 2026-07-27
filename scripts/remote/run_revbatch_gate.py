#!/usr/bin/env python3
"""Live Qwen3-ASR singleton-versus-batched streaming death gate.

The batched path preserves the official growing-audio and rollback semantics.
It changes only the arity of the underlying vLLM ``generate`` call.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import platform
import statistics
import time
from pathlib import Path
from typing import Any

import numpy as np
import soundfile as sf

from qwen_asr import Qwen3ASRModel, parse_asr_output


SAMPLE_RATE = 16000


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--model-name", required=True)
    parser.add_argument("--data-manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--smoke", action="store_true")
    parser.add_argument("--gpu-memory-utilization", type=float, default=0.82)
    return parser.parse_args()


def percentile(values: list[float], q: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = (len(ordered) - 1) * q
    lower = math.floor(index)
    upper = math.ceil(index)
    if lower == upper:
        return ordered[lower]
    weight = index - lower
    return ordered[lower] * (1.0 - weight) + ordered[upper] * weight


def read_audio(path: Path) -> np.ndarray:
    wav, sr = sf.read(path, dtype="float32", always_2d=False)
    wav = np.asarray(wav, dtype=np.float32)
    if wav.ndim > 1:
        wav = wav.mean(axis=1)
    if sr != SAMPLE_RATE:
        duration = wav.shape[0] / float(sr)
        target = max(1, int(round(duration * SAMPLE_RATE)))
        old_x = np.linspace(0.0, duration, num=wav.shape[0], endpoint=False)
        new_x = np.linspace(0.0, duration, num=target, endpoint=False)
        wav = np.interp(new_x, old_x, wav).astype(np.float32)
    return wav


def cycle_audio(source: np.ndarray, seconds: int, offset: int) -> np.ndarray:
    target = int(seconds * SAMPLE_RATE)
    if source.size == 0:
        raise ValueError("empty audio source")
    rolled = np.roll(source, offset % source.size)
    repeats = math.ceil(target / rolled.size)
    return np.tile(rolled, repeats)[:target].astype(np.float32, copy=False)


def load_sources(manifest_path: Path) -> dict[str, list[np.ndarray]]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    grouped: dict[str, list[np.ndarray]] = {"English": [], "Chinese": []}
    for record in manifest["records"]:
        language = record["language"]
        if language in grouped:
            grouped[language].append(read_audio(Path(record["path"])))
    if not grouped["English"] or not grouped["Chinese"]:
        raise RuntimeError("both English and Chinese inputs are required")
    return grouped


def make_streams(
    sources: dict[str, list[np.ndarray]], duration: int, concurrency: int
) -> list[dict[str, Any]]:
    streams = []
    for index in range(concurrency):
        language = "English" if concurrency == 1 or index % 2 == 0 else "Chinese"
        candidates = sources[language]
        source = candidates[index % len(candidates)]
        streams.append(
            {
                "session_id": f"s{index:03d}",
                "language": language,
                "audio": cycle_audio(
                    source,
                    duration,
                    offset=(index * 7919) % max(1, source.size),
                ),
            }
        )
    return streams


def rollback_prefix(asr: Qwen3ASRModel, state: Any, *, tail: bool) -> str:
    if state.chunk_id < state.unfixed_chunk_num:
        return ""
    current_ids = asr.processor.tokenizer.encode(state._raw_decoded)
    if tail:
        end_index = max(1, len(current_ids) - int(state.unfixed_token_num))
        return asr.processor.tokenizer.decode(current_ids[:end_index])
    rollback = int(state.unfixed_token_num)
    while True:
        end_index = max(0, len(current_ids) - rollback)
        prefix = (
            asr.processor.tokenizer.decode(current_ids[:end_index])
            if end_index > 0
            else ""
        )
        if "\ufffd" not in prefix or end_index == 0:
            return prefix
        rollback += 1


def prepare_job(
    asr: Qwen3ASRModel, state: Any, chunk: np.ndarray, *, tail: bool
) -> tuple[dict[str, Any], str]:
    chunk = np.asarray(chunk, dtype=np.float32).reshape(-1)
    if tail:
        if state.buffer.size:
            state.buffer = np.concatenate([state.buffer, chunk])
        else:
            state.buffer = chunk
        audio_piece = state.buffer
        state.buffer = np.zeros((0,), dtype=np.float32)
    else:
        if state.buffer.size:
            state.buffer = np.concatenate([state.buffer, chunk])
        else:
            state.buffer = chunk
        if state.buffer.shape[0] < state.chunk_size_samples:
            raise AssertionError("regular job does not contain a complete chunk")
        audio_piece = state.buffer[: state.chunk_size_samples]
        state.buffer = state.buffer[state.chunk_size_samples :]

    if state.audio_accum.size:
        state.audio_accum = np.concatenate([state.audio_accum, audio_piece])
    else:
        state.audio_accum = audio_piece
    prefix = rollback_prefix(asr, state, tail=tail)
    prompt = state.prompt_raw + prefix
    job = {
        "prompt": prompt,
        "multi_modal_data": {"audio": [state.audio_accum]},
    }
    return job, prefix


def apply_output(
    state: Any, output: Any, prefix: str
) -> dict[str, Any]:
    candidate = output.outputs[0]
    generated = candidate.text
    token_ids = [int(token) for token in candidate.token_ids]
    state._raw_decoded = prefix + generated
    language, text = parse_asr_output(
        state._raw_decoded, user_language=state.force_language
    )
    state.language = language
    state.text = text
    state.chunk_id += 1
    return {
        "token_ids": token_ids,
        "raw_decoded": state._raw_decoded,
        "language": state.language,
        "text": state.text,
    }


def event_digest(events: list[dict[str, Any]]) -> str:
    canonical = json.dumps(
        events, ensure_ascii=False, separators=(",", ":"), sort_keys=True
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def run_path(
    asr: Qwen3ASRModel,
    streams: list[dict[str, Any]],
    *,
    mode: str,
    chunk_seconds: float,
) -> dict[str, Any]:
    chunk_samples = int(round(chunk_seconds * SAMPLE_RATE))
    states = [
        asr.init_streaming_state(
            language=stream["language"],
            unfixed_chunk_num=2,
            unfixed_token_num=5,
            chunk_size_sec=chunk_seconds,
        )
        for stream in streams
    ]
    full_chunks = min(stream["audio"].shape[0] // chunk_samples for stream in streams)
    has_tail = any(stream["audio"].shape[0] % chunk_samples for stream in streams)
    events: list[dict[str, Any]] = []
    event_latencies: list[float] = []
    batch_service_times: list[dict[str, Any]] = []
    path_start = time.perf_counter()

    for chunk_index in range(full_chunks):
        round_start = time.perf_counter()
        jobs: list[dict[str, Any]] = []
        prefixes: list[str] = []
        for stream, state in zip(streams, states):
            begin = chunk_index * chunk_samples
            end = begin + chunk_samples
            job, prefix = prepare_job(
                asr, state, stream["audio"][begin:end], tail=False
            )
            jobs.append(job)
            prefixes.append(prefix)

        if mode == "batched":
            service_start = time.perf_counter()
            outputs = asr.model.generate(
                jobs, sampling_params=asr.sampling_params, use_tqdm=False
            )
            service_seconds = time.perf_counter() - service_start
            batch_service_times.append(
                {
                    "audio_frontier_seconds": (chunk_index + 1) * chunk_seconds,
                    "batch_size": len(jobs),
                    "service_seconds": service_seconds,
                }
            )
            for stream, state, output, prefix in zip(
                streams, states, outputs, prefixes
            ):
                result = apply_output(state, output, prefix)
                latency = time.perf_counter() - round_start
                event_latencies.append(latency)
                events.append(
                    {
                        "session_id": stream["session_id"],
                        "chunk_id": chunk_index,
                        "tail": False,
                        **result,
                    }
                )
        elif mode == "singleton":
            for stream, state, job, prefix in zip(
                streams, states, jobs, prefixes
            ):
                service_start = time.perf_counter()
                output = asr.model.generate(
                    [job], sampling_params=asr.sampling_params, use_tqdm=False
                )[0]
                service_seconds = time.perf_counter() - service_start
                batch_service_times.append(
                    {
                        "audio_frontier_seconds": (chunk_index + 1) * chunk_seconds,
                        "batch_size": 1,
                        "service_seconds": service_seconds,
                    }
                )
                result = apply_output(state, output, prefix)
                latency = time.perf_counter() - round_start
                event_latencies.append(latency)
                events.append(
                    {
                        "session_id": stream["session_id"],
                        "chunk_id": chunk_index,
                        "tail": False,
                        **result,
                    }
                )
        else:
            raise ValueError(mode)

    if has_tail:
        round_start = time.perf_counter()
        jobs = []
        prefixes = []
        active: list[tuple[dict[str, Any], Any]] = []
        for stream, state in zip(streams, states):
            begin = full_chunks * chunk_samples
            tail_audio = stream["audio"][begin:]
            if not tail_audio.size:
                continue
            job, prefix = prepare_job(asr, state, tail_audio, tail=True)
            jobs.append(job)
            prefixes.append(prefix)
            active.append((stream, state))
        if mode == "batched":
            service_start = time.perf_counter()
            outputs = asr.model.generate(
                jobs, sampling_params=asr.sampling_params, use_tqdm=False
            )
            service_seconds = time.perf_counter() - service_start
            batch_service_times.append(
                {
                    "audio_frontier_seconds": streams[0]["audio"].shape[0]
                    / SAMPLE_RATE,
                    "batch_size": len(jobs),
                    "service_seconds": service_seconds,
                }
            )
            iterator = zip(active, outputs, prefixes)
        else:
            singleton_outputs = []
            for job in jobs:
                service_start = time.perf_counter()
                output = asr.model.generate(
                    [job], sampling_params=asr.sampling_params, use_tqdm=False
                )[0]
                service_seconds = time.perf_counter() - service_start
                batch_service_times.append(
                    {
                        "audio_frontier_seconds": streams[0]["audio"].shape[0]
                        / SAMPLE_RATE,
                        "batch_size": 1,
                        "service_seconds": service_seconds,
                    }
                )
                singleton_outputs.append(output)
            iterator = zip(active, singleton_outputs, prefixes)
        for (stream, state), output, prefix in iterator:
            result = apply_output(state, output, prefix)
            event_latencies.append(time.perf_counter() - round_start)
            events.append(
                {
                    "session_id": stream["session_id"],
                    "chunk_id": full_chunks,
                    "tail": True,
                    **result,
                }
            )

    wall_seconds = time.perf_counter() - path_start
    audio_seconds = sum(stream["audio"].shape[0] / SAMPLE_RATE for stream in streams)
    deadline_seconds = chunk_seconds
    on_time_audio = sum(
        min(chunk_seconds, stream["audio"].shape[0] / SAMPLE_RATE)
        for stream in streams
        for _ in range(full_chunks)
    )
    on_time_fraction = (
        sum(latency <= deadline_seconds for latency in event_latencies)
        / len(event_latencies)
        if event_latencies
        else 0.0
    )
    return {
        "mode": mode,
        "wall_seconds": wall_seconds,
        "audio_seconds": audio_seconds,
        "audio_throughput": audio_seconds / wall_seconds,
        "event_count": len(events),
        "p50_event_latency_seconds": percentile(event_latencies, 0.50),
        "p95_event_latency_seconds": percentile(event_latencies, 0.95),
        "p99_event_latency_seconds": percentile(event_latencies, 0.99),
        "deadline_seconds": deadline_seconds,
        "deadline_met_fraction": on_time_fraction,
        "slo_audio_goodput": audio_seconds * on_time_fraction / wall_seconds,
        "event_digest": event_digest(events),
        "events": events,
        "batch_service_times": batch_service_times,
        "final_states": [
            {
                "session_id": stream["session_id"],
                "language": state.language,
                "text": state.text,
                "raw_decoded": state._raw_decoded,
            }
            for stream, state in zip(streams, states)
        ],
    }


def compare_paths(singleton: dict[str, Any], batched: dict[str, Any]) -> dict[str, Any]:
    left = singleton["events"]
    right = batched["events"]
    if len(left) != len(right):
        raise AssertionError("logical event counts differ")
    token_matches = 0
    transcript_matches = 0
    raw_matches = 0
    mismatches = []
    for reference, candidate in zip(left, right):
        identity = ("session_id", "chunk_id", "tail")
        if any(reference[key] != candidate[key] for key in identity):
            raise AssertionError("logical event ordering differs")
        token_equal = reference["token_ids"] == candidate["token_ids"]
        transcript_equal = (
            reference["language"] == candidate["language"]
            and reference["text"] == candidate["text"]
        )
        raw_equal = reference["raw_decoded"] == candidate["raw_decoded"]
        token_matches += int(token_equal)
        transcript_matches += int(transcript_equal)
        raw_matches += int(raw_equal)
        if not (token_equal and transcript_equal and raw_equal) and len(mismatches) < 50:
            mismatches.append(
                {
                    "session_id": reference["session_id"],
                    "chunk_id": reference["chunk_id"],
                    "tail": reference["tail"],
                    "token_equal": token_equal,
                    "transcript_equal": transcript_equal,
                    "raw_equal": raw_equal,
                    "singleton_token_ids": reference["token_ids"],
                    "batched_token_ids": candidate["token_ids"],
                    "singleton_text": reference["text"],
                    "batched_text": candidate["text"],
                }
            )
    final_matches = sum(
        left_state["language"] == right_state["language"]
        and left_state["text"] == right_state["text"]
        and left_state["raw_decoded"] == right_state["raw_decoded"]
        for left_state, right_state in zip(
            singleton["final_states"], batched["final_states"]
        )
    )
    count = len(left)
    final_count = len(singleton["final_states"])
    return {
        "event_count": count,
        "token_exact_matches": token_matches,
        "token_exact_match_rate": token_matches / count if count else 1.0,
        "transcript_exact_matches": transcript_matches,
        "transcript_exact_match_rate": transcript_matches / count if count else 1.0,
        "raw_exact_matches": raw_matches,
        "raw_exact_match_rate": raw_matches / count if count else 1.0,
        "final_count": final_count,
        "final_exact_matches": final_matches,
        "final_exact_match_rate": final_matches / final_count if final_count else 1.0,
        "mismatches": mismatches,
    }


def compact_path(path: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in path.items() if key not in {"events"}}


def official_smoke(
    asr: Qwen3ASRModel, source: np.ndarray
) -> dict[str, Any]:
    audio = cycle_audio(source, seconds=4, offset=0)
    warmup = asr.init_streaming_state(language="English", chunk_size_sec=2.0)
    for index in range(2):
        chunk = audio[index * 32000 : (index + 1) * 32000]
        asr.streaming_transcribe(chunk, warmup)
    official = asr.init_streaming_state(language="English", chunk_size_sec=2.0)
    custom = asr.init_streaming_state(language="English", chunk_size_sec=2.0)
    official_records = []
    custom_records = []
    for index in range(2):
        chunk = audio[index * 32000 : (index + 1) * 32000]
        asr.streaming_transcribe(chunk, official)
        official_records.append((official.language, official.text, official._raw_decoded))
        job, prefix = prepare_job(asr, custom, chunk, tail=False)
        output = asr.model.generate(
            [job], sampling_params=asr.sampling_params, use_tqdm=False
        )[0]
        apply_output(custom, output, prefix)
        custom_records.append((custom.language, custom.text, custom._raw_decoded))
    return {
        "exact": official_records == custom_records,
        "warmup_final": (warmup.language, warmup.text, warmup._raw_decoded),
        "official": official_records,
        "custom": custom_records,
    }


def workload_matrix(smoke: bool) -> list[dict[str, int]]:
    if smoke:
        return [{"duration_seconds": 6, "concurrency": 2}]
    cells = [
        {"duration_seconds": 30, "concurrency": value}
        for value in [1, 4, 8, 16, 32]
    ]
    cells.extend(
        {"duration_seconds": duration, "concurrency": 8}
        for duration in [15, 60, 120]
    )
    return cells


def main() -> int:
    args = parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    sources = load_sources(args.data_manifest)
    started = time.time()
    asr = Qwen3ASRModel.LLM(
        model=str(args.model),
        gpu_memory_utilization=args.gpu_memory_utilization,
        max_inference_batch_size=128,
        max_new_tokens=32,
        enforce_eager=True,
        max_num_seqs=128,
        mm_processor_cache_gb=0,
        async_scheduling=False,
    )
    smoke_result = official_smoke(asr, sources["English"][0])
    if not smoke_result["exact"]:
        args.output.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "model_name": args.model_name,
                    "smoke": args.smoke,
                    "status": "OFFICIAL_SEMANTICS_MISMATCH",
                    "official_semantics_smoke": smoke_result,
                },
                indent=2,
                ensure_ascii=False,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        print(json.dumps(smoke_result, ensure_ascii=False, sort_keys=True), flush=True)
        raise AssertionError("custom singleton path differs from official streaming semantics")

    cells = []
    for specification in workload_matrix(args.smoke):
        streams = make_streams(
            sources,
            duration=specification["duration_seconds"],
            concurrency=specification["concurrency"],
        )
        singleton = run_path(asr, streams, mode="singleton", chunk_seconds=2.0)
        batched = run_path(asr, streams, mode="batched", chunk_seconds=2.0)
        comparison = compare_paths(singleton, batched)
        cells.append(
            {
                **specification,
                "languages": sorted({stream["language"] for stream in streams}),
                "singleton": compact_path(singleton),
                "batched": compact_path(batched),
                "comparison": comparison,
                "audio_throughput_speedup": (
                    batched["audio_throughput"] / singleton["audio_throughput"]
                ),
                "slo_goodput_speedup": (
                    batched["slo_audio_goodput"] / singleton["slo_audio_goodput"]
                    if singleton["slo_audio_goodput"] > 0
                    else None
                ),
                "p99_reduction_fraction": (
                    1.0
                    - batched["p99_event_latency_seconds"]
                    / singleton["p99_event_latency_seconds"]
                    if singleton["p99_event_latency_seconds"] > 0
                    else 0.0
                ),
            }
        )
        print(
            json.dumps(
                {
                    "model": args.model_name,
                    "cell": specification,
                    "speedup": cells[-1]["audio_throughput_speedup"],
                    "token_exact": comparison["token_exact_match_rate"],
                    "transcript_exact": comparison["transcript_exact_match_rate"],
                },
                sort_keys=True,
            ),
            flush=True,
        )

    total_events = sum(cell["comparison"]["event_count"] for cell in cells)
    total_token_matches = sum(
        cell["comparison"]["token_exact_matches"] for cell in cells
    )
    total_transcript_matches = sum(
        cell["comparison"]["transcript_exact_matches"] for cell in cells
    )
    total_finals = sum(cell["comparison"]["final_count"] for cell in cells)
    total_final_matches = sum(
        cell["comparison"]["final_exact_matches"] for cell in cells
    )
    result = {
        "schema_version": 1,
        "model_name": args.model_name,
        "model_path": str(args.model.resolve()),
        "smoke": args.smoke,
        "official_semantics_smoke": smoke_result,
        "environment": {
            "hostname": platform.node(),
            "python": platform.python_version(),
            "cuda_visible_devices": os.environ.get("CUDA_VISIBLE_DEVICES"),
        },
        "started_unix": started,
        "elapsed_seconds": time.time() - started,
        "cells": cells,
        "aggregate": {
            "event_count": total_events,
            "token_exact_matches": total_token_matches,
            "token_exact_match_rate": (
                total_token_matches / total_events if total_events else 1.0
            ),
            "transcript_exact_matches": total_transcript_matches,
            "transcript_exact_match_rate": (
                total_transcript_matches / total_events if total_events else 1.0
            ),
            "final_count": total_finals,
            "final_exact_matches": total_final_matches,
            "final_exact_match_rate": (
                total_final_matches / total_finals if total_finals else 1.0
            ),
            "max_audio_throughput_speedup": max(
                cell["audio_throughput_speedup"] for cell in cells
            ),
            "median_audio_throughput_speedup": statistics.median(
                cell["audio_throughput_speedup"] for cell in cells
            ),
            "max_p99_reduction_fraction": max(
                cell["p99_reduction_fraction"] for cell in cells
            ),
        },
    }
    args.output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(result["aggregate"], sort_keys=True), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

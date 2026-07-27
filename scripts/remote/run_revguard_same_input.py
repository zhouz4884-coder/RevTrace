#!/usr/bin/env python3
"""Same-input RevGuard diagnostic for Qwen3-ASR revision execution.

Every revision job is prepared exactly once from the canonical singleton state,
then evaluated four times without mutating that state:

1. singleton A;
2. singleton B;
3. batched A;
4. batched B.

Only singleton A updates the next revision state.  The design separates
within-shape repeatability from cross-shape numerical drift and prevents an
earlier decoded-text difference from contaminating the same-input comparison.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import platform
import statistics
import time
from pathlib import Path
from typing import Any

import numpy as np
from qwen_asr import Qwen3ASRModel
from vllm import SamplingParams

from run_revbatch_gate import (
    SAMPLE_RATE,
    apply_output,
    load_sources,
    make_streams,
    official_smoke,
    prepare_job,
    rollback_prefix,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--model-name", required=True)
    parser.add_argument("--data-manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--duration-seconds", type=int, default=30)
    parser.add_argument("--concurrency", type=int, default=8)
    parser.add_argument("--chunk-seconds", type=float, default=2.0)
    parser.add_argument("--top-logprobs", type=int, default=20)
    parser.add_argument("--dtype", default="bfloat16")
    parser.add_argument("--max-model-len", type=int, default=65536)
    parser.add_argument("--gpu-memory-utilization", type=float, default=0.82)
    parser.add_argument("--mm-encoder-attn-backend")
    return parser.parse_args()


def job_digest(job: dict[str, Any]) -> str:
    hasher = hashlib.sha256()
    prompt = str(job["prompt"]).encode("utf-8")
    audio = np.asarray(
        job["multi_modal_data"]["audio"][0], dtype=np.float32
    ).reshape(-1)
    hasher.update(len(prompt).to_bytes(8, "little"))
    hasher.update(prompt)
    hasher.update(audio.shape[0].to_bytes(8, "little"))
    hasher.update(audio.tobytes(order="C"))
    return hasher.hexdigest()


def candidate_record(output: Any) -> dict[str, Any]:
    candidate = output.outputs[0]
    token_ids = [int(token) for token in candidate.token_ids]
    margins: list[float | None] = []
    chosen_logprobs: list[float | None] = []
    if candidate.logprobs is None:
        margins = [None] * len(token_ids)
        chosen_logprobs = [None] * len(token_ids)
    else:
        for token_id, table in zip(token_ids, candidate.logprobs):
            values = sorted(
                (float(item.logprob) for item in table.values()), reverse=True
            )
            chosen = table.get(token_id)
            chosen_logprobs.append(
                float(chosen.logprob) if chosen is not None else None
            )
            margins.append(values[0] - values[1] if len(values) >= 2 else None)
    finite_margins = [value for value in margins if value is not None]
    return {
        "token_ids": token_ids,
        "text": candidate.text,
        "chosen_logprobs": chosen_logprobs,
        "margins": margins,
        "minimum_margin": min(finite_margins) if finite_margins else None,
    }


def state_projection_record(
    asr: Qwen3ASRModel,
    state: Any,
    prefix: str,
    candidate: dict[str, Any],
    *,
    terminal: bool,
) -> dict[str, Any]:
    """Project an output onto the state that can affect the next revision.

    Intermediate revisions use the exact rollback loop from ``rollback_prefix``
    after accounting for ``apply_output`` incrementing ``chunk_id``.  A
    terminal revision has no later rollback opportunity, so its entire raw
    decoded output is part of the final-state contract.

    ``committed_minimum_margin`` is an empirical scheduling feature, not an
    exact certificate.  Its token boundary is conservative when concatenating
    ``prefix`` and generated text changes tokenizer segmentation; the exact
    contract is always evaluated from ``projection_token_ids`` and
    ``projection_text``.
    """

    tokenizer = asr.processor.tokenizer
    raw_decoded = prefix + candidate["text"]
    raw_token_ids = [int(token) for token in tokenizer.encode(raw_decoded)]
    next_chunk_id = int(state.chunk_id) + 1
    if terminal:
        end_index = len(raw_token_ids)
    elif next_chunk_id < int(state.unfixed_chunk_num):
        end_index = 0
    else:
        rollback = int(state.unfixed_token_num)
        while True:
            end_index = max(0, len(raw_token_ids) - rollback)
            projection = (
                tokenizer.decode(raw_token_ids[:end_index])
                if end_index > 0
                else ""
            )
            if "\ufffd" not in projection or end_index == 0:
                break
            rollback += 1
    projection_text = (
        tokenizer.decode(raw_token_ids[:end_index]) if end_index > 0 else ""
    )
    projection_token_ids = raw_token_ids[:end_index]
    original_raw_decoded = state._raw_decoded
    original_chunk_id = state.chunk_id
    try:
        state._raw_decoded = raw_decoded
        state.chunk_id = next_chunk_id
        official_projection = (
            raw_decoded
            if terminal
            else rollback_prefix(asr, state, tail=False)
        )
    finally:
        state._raw_decoded = original_raw_decoded
        state.chunk_id = original_chunk_id
    if projection_text != official_projection:
        raise AssertionError(
            "state projection does not match the official rollback path: "
            f"{projection_text!r} != {official_projection!r}"
        )

    prefix_token_count = len(tokenizer.encode(prefix)) if prefix else 0
    boundary_delta = len(raw_token_ids) - (
        prefix_token_count + len(tokenizer.encode(candidate["text"]))
    )
    committed_generated_tokens = max(
        0,
        min(
            len(candidate["token_ids"]),
            end_index - prefix_token_count,
        ),
    )
    committed_margins = [
        value
        for value in candidate["margins"][:committed_generated_tokens]
        if value is not None
    ]
    return {
        "terminal": terminal,
        "next_chunk_id": next_chunk_id,
        "raw_decoded": raw_decoded,
        "projection_text": projection_text,
        "projection_token_ids": projection_token_ids,
        "raw_token_count": len(raw_token_ids),
        "projection_token_count": len(projection_token_ids),
        "rolled_back_token_count": len(raw_token_ids) - end_index,
        "committed_generated_token_count": committed_generated_tokens,
        "committed_minimum_margin": (
            min(committed_margins) if committed_margins else None
        ),
        "tokenization_boundary_delta": boundary_delta,
    }


def longest_common_prefix(left: list[int], right: list[int]) -> int:
    count = 0
    for a, b in zip(left, right):
        if a != b:
            break
        count += 1
    return count


def evaluate_singletons(
    asr: Qwen3ASRModel, jobs: list[dict[str, Any]]
) -> tuple[list[Any], float]:
    started = time.perf_counter()
    outputs = [
        asr.model.generate(
            [job], sampling_params=asr.sampling_params, use_tqdm=False
        )[0]
        for job in jobs
    ]
    return outputs, time.perf_counter() - started


def evaluate_batch(
    asr: Qwen3ASRModel, jobs: list[dict[str, Any]]
) -> tuple[list[Any], float]:
    started = time.perf_counter()
    outputs = asr.model.generate(
        jobs, sampling_params=asr.sampling_params, use_tqdm=False
    )
    return outputs, time.perf_counter() - started


def compare_records(
    left: dict[str, Any], right: dict[str, Any]
) -> dict[str, Any]:
    lcp = longest_common_prefix(left["token_ids"], right["token_ids"])
    comparison = {
        "token_exact": left["token_ids"] == right["token_ids"],
        "text_exact": left["text"] == right["text"],
        "lcp_tokens": lcp,
        "reference_tokens": len(left["token_ids"]),
        "candidate_tokens": len(right["token_ids"]),
        "lcp_reference_fraction": (
            lcp / len(left["token_ids"]) if left["token_ids"] else 1.0
        ),
    }
    if "state_projection" in left and "state_projection" in right:
        left_projection = left["state_projection"]
        right_projection = right["state_projection"]
        comparison.update(
            {
                "state_projection_token_exact": (
                    left_projection["projection_token_ids"]
                    == right_projection["projection_token_ids"]
                ),
                "state_projection_text_exact": (
                    left_projection["projection_text"]
                    == right_projection["projection_text"]
                ),
            }
        )
    return comparison


def rate(records: list[dict[str, Any]], key: str) -> float:
    return (
        sum(bool(record[key]) for record in records) / len(records)
        if records
        else 1.0
    )


def margin_sweep(
    events: list[dict[str, Any]],
    *,
    margin_path: tuple[str, ...] = ("minimum_margin",),
    exact_key: str = "token_exact",
) -> list[dict[str, Any]]:
    def margin(event: dict[str, Any]) -> float | None:
        value: Any = event["batch_a"]
        for key in margin_path:
            value = value[key]
        return value

    eligible = [
        event
        for event in events
        if margin(event) is not None
    ]
    if not eligible:
        return []
    thresholds = sorted(
        {
            0.0,
            0.001,
            0.005,
            0.01,
            0.02,
            0.05,
            0.1,
            0.2,
            0.5,
            1.0,
        }
    )
    result = []
    for threshold in thresholds:
        admitted = [
            event
            for event in eligible
            if margin(event) > threshold
        ]
        false_safe = sum(
            not event["singleton_a_vs_batch_a"][exact_key]
            for event in admitted
        )
        result.append(
            {
                "minimum_margin_threshold": threshold,
                "admitted_events": len(admitted),
                "coverage": len(admitted) / len(eligible),
                "false_safe_events": false_safe,
                "false_safe_rate": (
                    false_safe / len(admitted) if admitted else 0.0
                ),
            }
        )
    return result


def main() -> int:
    args = parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    sources = load_sources(args.data_manifest)
    streams = make_streams(
        sources,
        duration=args.duration_seconds,
        concurrency=args.concurrency,
    )
    started = time.time()
    model_kwargs: dict[str, Any] = {}
    if args.mm_encoder_attn_backend:
        model_kwargs["mm_encoder_attn_backend"] = (
            args.mm_encoder_attn_backend
        )
    asr = Qwen3ASRModel.LLM(
        model=str(args.model),
        gpu_memory_utilization=args.gpu_memory_utilization,
        max_inference_batch_size=128,
        max_new_tokens=32,
        enforce_eager=True,
        max_num_seqs=128,
        mm_processor_cache_gb=0,
        async_scheduling=False,
        enable_prefix_caching=False,
        dtype=args.dtype,
        max_model_len=args.max_model_len,
        **model_kwargs,
    )
    asr.sampling_params = SamplingParams(
        temperature=0.0,
        max_tokens=32,
        logprobs=(
            args.top_logprobs if args.top_logprobs > 0 else None
        ),
    )
    smoke = official_smoke(asr, sources["English"][0])
    if not smoke["exact"]:
        raise AssertionError("warm official and copied singleton paths differ")

    states = [
        asr.init_streaming_state(
            language=stream["language"],
            unfixed_chunk_num=2,
            unfixed_token_num=5,
            chunk_size_sec=args.chunk_seconds,
        )
        for stream in streams
    ]
    chunk_samples = int(round(args.chunk_seconds * SAMPLE_RATE))
    rounds = min(stream["audio"].shape[0] // chunk_samples for stream in streams)
    events: list[dict[str, Any]] = []
    service_seconds = {
        "singleton_a": 0.0,
        "singleton_b": 0.0,
        "batch_a": 0.0,
        "batch_b": 0.0,
    }

    for chunk_index in range(rounds):
        terminal = chunk_index == rounds - 1
        jobs: list[dict[str, Any]] = []
        prefixes: list[str] = []
        hashes: list[str] = []
        for stream, state in zip(streams, states):
            begin = chunk_index * chunk_samples
            end = begin + chunk_samples
            job, prefix = prepare_job(
                asr, state, stream["audio"][begin:end], tail=False
            )
            jobs.append(job)
            prefixes.append(prefix)
            hashes.append(job_digest(job))

        singleton_a_outputs, elapsed = evaluate_singletons(asr, jobs)
        service_seconds["singleton_a"] += elapsed
        singleton_b_outputs, elapsed = evaluate_singletons(asr, jobs)
        service_seconds["singleton_b"] += elapsed
        batch_a_outputs, elapsed = evaluate_batch(asr, jobs)
        service_seconds["batch_a"] += elapsed
        batch_b_outputs, elapsed = evaluate_batch(asr, jobs)
        service_seconds["batch_b"] += elapsed

        for stream, state, job, prefix, digest, output_sa, output_sb, output_ba, output_bb in zip(
            streams,
            states,
            jobs,
            prefixes,
            hashes,
            singleton_a_outputs,
            singleton_b_outputs,
            batch_a_outputs,
            batch_b_outputs,
        ):
            sa = candidate_record(output_sa)
            sb = candidate_record(output_sb)
            ba = candidate_record(output_ba)
            bb = candidate_record(output_bb)
            for record in (sa, sb, ba, bb):
                record["state_projection"] = state_projection_record(
                    asr,
                    state,
                    prefix,
                    record,
                    terminal=terminal,
                )
            cross_a = compare_records(sa, ba)
            replica_probe = None
            if not cross_a["token_exact"]:
                replica_outputs, replica_seconds = evaluate_batch(
                    asr, [job] * args.concurrency
                )
                replica_records = [
                    candidate_record(output) for output in replica_outputs
                ]
                replica_probe = {
                    "batch_size": args.concurrency,
                    "service_seconds": replica_seconds,
                    "all_rows_exact": all(
                        record["token_ids"] == replica_records[0]["token_ids"]
                        for record in replica_records[1:]
                    ),
                    "all_rows_match_singleton": all(
                        record["token_ids"] == sa["token_ids"]
                        for record in replica_records
                    ),
                    "row_token_ids": [
                        record["token_ids"] for record in replica_records
                    ],
                    "row_minimum_margins": [
                        record["minimum_margin"] for record in replica_records
                    ],
                }
            events.append(
                {
                    "session_id": stream["session_id"],
                    "language": stream["language"],
                    "chunk_id": chunk_index,
                    "terminal": terminal,
                    "input_sha256": digest,
                    "prompt_characters": len(job["prompt"]),
                    "audio_samples": int(
                        job["multi_modal_data"]["audio"][0].shape[0]
                    ),
                    "singleton_a": sa,
                    "singleton_b": sb,
                    "batch_a": ba,
                    "batch_b": bb,
                    "singleton_repeat": compare_records(sa, sb),
                    "batch_repeat": compare_records(ba, bb),
                    "singleton_a_vs_batch_a": cross_a,
                    "singleton_b_vs_batch_b": compare_records(sb, bb),
                    "identical_job_replica_probe": replica_probe,
                }
            )
            apply_output(state, output_sa, prefix)
        print(
            json.dumps(
                {
                    "model": args.model_name,
                    "chunk": chunk_index,
                    "events": len(events),
                },
                sort_keys=True,
            ),
            flush=True,
        )

    singleton_repeats = [event["singleton_repeat"] for event in events]
    batch_repeats = [event["batch_repeat"] for event in events]
    cross = [event["singleton_a_vs_batch_a"] for event in events]
    lcp_fractions = [record["lcp_reference_fraction"] for record in cross]
    mismatches = [
        event
        for event in events
        if not event["singleton_a_vs_batch_a"]["token_exact"]
    ]
    projection_mismatches = [
        event
        for event in events
        if not event["singleton_a_vs_batch_a"][
            "state_projection_token_exact"
        ]
    ]
    suffix_only_mismatches = [
        event
        for event in mismatches
        if event["singleton_a_vs_batch_a"][
            "state_projection_token_exact"
        ]
    ]
    summary = {
        "event_count": len(events),
        "singleton_repeat_token_exact_rate": rate(
            singleton_repeats, "token_exact"
        ),
        "batch_repeat_token_exact_rate": rate(batch_repeats, "token_exact"),
        "same_input_cross_shape_token_exact_rate": rate(cross, "token_exact"),
        "same_input_cross_shape_text_exact_rate": rate(cross, "text_exact"),
        "same_input_cross_shape_state_projection_token_exact_rate": rate(
            cross, "state_projection_token_exact"
        ),
        "same_input_cross_shape_state_projection_text_exact_rate": rate(
            cross, "state_projection_text_exact"
        ),
        "cross_shape_mismatch_events": len(mismatches),
        "state_projection_mismatch_events": len(projection_mismatches),
        "full_mismatch_but_state_projection_exact_events": len(
            suffix_only_mismatches
        ),
        "lcp_reference_fraction_mean": statistics.fmean(lcp_fractions),
        "lcp_reference_fraction_median": statistics.median(lcp_fractions),
        "lcp_reference_fraction_minimum": min(lcp_fractions),
        "service_seconds": service_seconds,
        "batch_a_over_singleton_a_speedup": (
            service_seconds["singleton_a"] / service_seconds["batch_a"]
        ),
        "margin_sweep": margin_sweep(events),
        "state_projection_margin_sweep": margin_sweep(
            events,
            margin_path=(
                "state_projection",
                "committed_minimum_margin",
            ),
            exact_key="state_projection_token_exact",
        ),
    }
    payload = {
        "schema_version": 2,
        "study": "RevGuard same-input execution-shape diagnostic",
        "model_name": args.model_name,
        "model_path": str(args.model),
        "duration_seconds": args.duration_seconds,
        "concurrency": args.concurrency,
        "chunk_seconds": args.chunk_seconds,
        "top_logprobs": args.top_logprobs,
        "dtype": args.dtype,
        "max_model_len": args.max_model_len,
        "mm_encoder_attn_backend": args.mm_encoder_attn_backend,
        "canonical_state_update": "singleton_a_only",
        "state_contract": (
            "next rollback projection for intermediate revisions; complete "
            "raw decoded output for terminal revisions"
        ),
        "official_semantics_smoke": smoke,
        "summary": summary,
        "mismatch_examples": mismatches[:30],
        "events": events,
        "environment": {
            "python": platform.python_version(),
            "numpy": np.__version__,
        },
        "started_unix": started,
        "finished_unix": time.time(),
    }
    args.output.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

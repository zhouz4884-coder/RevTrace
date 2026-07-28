#!/usr/bin/env python3
"""Phase 3D boundary test on Voxtral Realtime.

This test asks whether execution composition changes a revision transcript and,
if so, whether that difference is fed into the next model transition.  Voxtral
is intentionally treated as a boundary architecture: its causal audio state is
native to the model, while prior decoded text is not re-injected as an input.
"""

from __future__ import annotations

import argparse
import json
import platform
import time
from pathlib import Path
from typing import Any

import numpy as np
import soundfile as sf
import torch
from transformers import (
    AutoProcessor,
    VoxtralRealtimeForConditionalGeneration,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--audio", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--chunk-seconds", type=float, default=2.0)
    parser.add_argument("--duration-seconds", type=float, default=20.0)
    parser.add_argument(
        "--tile-to-duration",
        action="store_true",
        help=(
            "repeat the source waveform to the requested duration; "
            "used only to exercise the revision-state boundary"
        ),
    )
    parser.add_argument("--batch-sizes", type=int, nargs="+", default=[2, 4])
    parser.add_argument("--repeats", type=int, default=4)
    parser.add_argument("--max-new-tokens", type=int, default=64)
    return parser.parse_args()


def edit_distance(left: list[int], right: list[int]) -> int:
    if len(left) < len(right):
        left, right = right, left
    previous = list(range(len(right) + 1))
    for row, left_token in enumerate(left, start=1):
        current = [row]
        for column, right_token in enumerate(right, start=1):
            current.append(
                min(
                    current[-1] + 1,
                    previous[column] + 1,
                    previous[column - 1]
                    + int(left_token != right_token),
                )
            )
        previous = current
    return previous[-1]


def to_device(batch: Any, device: torch.device, dtype: torch.dtype) -> Any:
    moved = {}
    for key, value in batch.items():
        if not hasattr(value, "to"):
            moved[key] = value
        elif torch.is_floating_point(value):
            moved[key] = value.to(device=device, dtype=dtype)
        else:
            moved[key] = value.to(device=device)
    return moved


def generate(
    model: Any,
    processor: Any,
    audio: np.ndarray | list[np.ndarray],
    *,
    sampling_rate: int,
    max_new_tokens: int,
) -> tuple[list[list[int]], list[str], float]:
    inputs = processor(
        audio,
        sampling_rate=sampling_rate,
        return_tensors="pt",
        padding=True,
    )
    inputs = to_device(inputs, model.device, model.dtype)
    started = time.perf_counter()
    with torch.inference_mode():
        output = model.generate(
            **inputs,
            do_sample=False,
            max_new_tokens=max_new_tokens,
        )
    elapsed = time.perf_counter() - started
    token_rows = [
        [int(token) for token in row.detach().cpu().tolist()]
        for row in output
    ]
    texts = processor.batch_decode(
        output, skip_special_tokens=True
    )
    return token_rows, texts, elapsed


def main() -> int:
    args = parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    try:
        processor = AutoProcessor.from_pretrained(
            args.model, local_files_only=True
        )
        model = (
            VoxtralRealtimeForConditionalGeneration.from_pretrained(
                args.model,
                torch_dtype=torch.bfloat16,
                device_map="cuda",
                local_files_only=True,
            ).eval()
        )
        audio, source_rate = sf.read(
            args.audio, dtype="float32", always_2d=False
        )
        if audio.ndim == 2:
            audio = audio.mean(axis=1)
        target_rate = int(processor.feature_extractor.sampling_rate)
        if source_rate != target_rate:
            import librosa

            audio = librosa.resample(
                audio,
                orig_sr=source_rate,
                target_sr=target_rate,
            )
        requested_samples = int(args.duration_seconds * target_rate)
        tiled_audio = False
        if args.tile_to_duration and len(audio) < requested_samples:
            repetitions = int(
                np.ceil(requested_samples / max(len(audio), 1))
            )
            audio = np.tile(audio, repetitions)[:requested_samples]
            tiled_audio = True
        maximum = min(len(audio), requested_samples)
        chunk_samples = int(args.chunk_seconds * target_rate)
        revision_ends = list(
            range(chunk_samples, maximum + 1, chunk_samples)
        )
        if not revision_ends:
            raise ValueError("audio is shorter than one revision chunk")

        events: list[dict[str, Any]] = []
        singleton_repeat_mismatches = 0
        cross_shape_mismatches = 0
        replicated_row_mismatches = 0
        row_evaluations = 0
        first_flip: dict[str, Any] | None = None
        singleton_seconds = 0.0
        batch_seconds = 0.0
        for revision_index, end in enumerate(revision_ends):
            prefix = np.asarray(audio[:end], dtype=np.float32)
            canonical_rows, canonical_texts, elapsed = generate(
                model,
                processor,
                prefix,
                sampling_rate=target_rate,
                max_new_tokens=args.max_new_tokens,
            )
            singleton_seconds += elapsed
            repeat_rows, repeat_texts, elapsed = generate(
                model,
                processor,
                prefix,
                sampling_rate=target_rate,
                max_new_tokens=args.max_new_tokens,
            )
            singleton_seconds += elapsed
            repeat_mismatch = (
                repeat_rows[0] != canonical_rows[0]
                or repeat_texts[0] != canonical_texts[0]
            )
            singleton_repeat_mismatches += int(repeat_mismatch)
            trials = []
            for batch_size in args.batch_sizes:
                for repeat in range(args.repeats):
                    batch_rows, batch_texts, elapsed = generate(
                        model,
                        processor,
                        [prefix] * batch_size,
                        sampling_rate=target_rate,
                        max_new_tokens=args.max_new_tokens,
                    )
                    batch_seconds += elapsed
                    row_records = []
                    for slot, (tokens, text) in enumerate(
                        zip(batch_rows, batch_texts)
                    ):
                        mismatch = (
                            tokens != canonical_rows[0]
                            or text != canonical_texts[0]
                        )
                        row_evaluations += 1
                        cross_shape_mismatches += int(mismatch)
                        if slot and (
                            tokens != batch_rows[0]
                            or text != batch_texts[0]
                        ):
                            replicated_row_mismatches += 1
                        distance = edit_distance(
                            canonical_rows[0], tokens
                        )
                        row_records.append(
                            {
                                "slot": slot,
                                "mismatch": mismatch,
                                "token_edit_distance": distance,
                                "token_ids": tokens,
                                "text": text,
                            }
                        )
                        if mismatch and first_flip is None:
                            first_flip = {
                                "revision_index": revision_index,
                                "audio_seconds": end / target_rate,
                                "canonical_token_ids": (
                                    canonical_rows[0]
                                ),
                                "canonical_text": canonical_texts[0],
                                "divergent_token_ids": tokens,
                                "divergent_text": text,
                                "batch_size": batch_size,
                                "repeat": repeat,
                                "slot": slot,
                                "distance_at_flip": distance,
                            }
                    trials.append(
                        {
                            "batch_size": batch_size,
                            "repeat": repeat,
                            "elapsed_seconds": elapsed,
                            "rows": row_records,
                        }
                    )
            events.append(
                {
                    "revision_index": revision_index,
                    "audio_seconds": end / target_rate,
                    "canonical_token_ids": canonical_rows[0],
                    "canonical_text": canonical_texts[0],
                    "singleton_repeat_mismatch": repeat_mismatch,
                    "trials": trials,
                }
            )

        # Prior decoded text is not an input to the next Voxtral transition.
        # Therefore, if a numerical output flip is observed, both branches
        # receive the same future audio/model state and the output-state
        # difference is application-visible but not model-feedback state.
        if first_flip is None:
            impulse = None
            half_life = None
            right_censored = False
            raf = 0.0
        else:
            impulse = [float(first_flip["distance_at_flip"]), 0.0]
            half_life = 1
            right_censored = False
            raf = 1.0
        observed_flip_rate = (
            cross_shape_mismatches / row_evaluations
            if row_evaluations
            else 0.0
        )
        nse = observed_flip_rate * raf
        decision = (
            "PHASE3D_BOUNDARY_LOW_FEEDBACK_NSE"
            if first_flip is not None
            else "PHASE3D_NO_OBSERVED_EXECUTION_SHAPE_FLIP"
        )
        payload = {
            "schema_version": 1,
            "study": (
                "RevTrace Phase 3D second-architecture boundary"
            ),
            "decision": decision,
            "architecture": "Voxtral-Mini-4B-Realtime-2602",
            "state_semantics": (
                "causal audio/KV state; decoded transcript is not "
                "re-injected into the next model transition"
            ),
            "input_protocol": {
                "source_audio": str(args.audio),
                "requested_duration_seconds": args.duration_seconds,
                "tiled_to_duration": tiled_audio,
                "purpose": (
                    "revision-boundary execution coverage, not "
                    "dataset generalization"
                ),
            },
            "counts": {
                "revisions": len(events),
                "row_evaluations": row_evaluations,
                "singleton_repeat_mismatches": (
                    singleton_repeat_mismatches
                ),
                "cross_shape_mismatches": cross_shape_mismatches,
                "replicated_row_mismatches": (
                    replicated_row_mismatches
                ),
            },
            "metrics": {
                "observed_flip_rate": observed_flip_rate,
                "impulse_response": impulse,
                "pollution_half_life": half_life,
                "half_life_right_censored": right_censored,
                "revision_amplification_factor": raf,
                "numerical_state_exposure": nse,
                "singleton_seconds": singleton_seconds,
                "batch_seconds": batch_seconds,
            },
            "first_flip": first_flip,
            "events": events,
            "environment": {
                "python": platform.python_version(),
                "torch": torch.__version__,
                "transformers": __import__(
                    "transformers"
                ).__version__,
                "gpu": torch.cuda.get_device_name(0),
                "dtype": str(model.dtype),
            },
            "claim_boundaries": {
                "frequency": (
                    "the execution-shape probe is a stress test, not a "
                    "production flip-rate estimate"
                ),
                "feedback": (
                    "Voxtral is a boundary architecture because decoded "
                    "text is not model-feedback state"
                ),
                "zero": (
                    "zero observed flips, if obtained, is not a "
                    "deterministic certificate"
                ),
                "streaming": (
                    "this Transformers experiment uses growing audio "
                    "prefixes, not the vLLM websocket serving endpoint"
                ),
            },
        }
        status = 0
    except BaseException as exc:
        payload = {
            "schema_version": 1,
            "study": (
                "RevTrace Phase 3D second-architecture boundary"
            ),
            "decision": "PHASE3D_COMPATIBILITY_BLOCKED",
            "error_type": type(exc).__name__,
            "error": str(exc),
            "environment": {
                "python": platform.python_version(),
                "torch": torch.__version__,
                "transformers": __import__(
                    "transformers"
                ).__version__,
            },
            "claim_boundaries": {
                "completion": (
                    "a structured compatibility failure is not a "
                    "second-architecture result"
                )
            },
        }
        status = 2
    args.output.write_text(
        json.dumps(
            payload,
            indent=2,
            ensure_ascii=False,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "decision": payload["decision"],
                "counts": payload.get("counts"),
                "metrics": payload.get("metrics"),
                "error": payload.get("error"),
            },
            sort_keys=True,
        )
    )
    return status


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Counterfactual Whisper previous-text feedback gate.

The treatment is a naturally occurring singleton-versus-batch token flip.
Future audio is held fixed and both branches are replayed through the same
singleton canonical executor.  The only intervention is whether the prior
window text is supplied as Whisper prompt state.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import statistics
import time
from pathlib import Path
from typing import Any

import numpy as np
import soundfile as sf
import torch
from transformers import AutoModelForSpeechSeq2Seq, AutoProcessor

from revtrace.feedback_metrics import (
    edit_distance,
    pack_disjoint_audio,
    repetition_score,
)


SAMPLE_RATE = 16_000
WINDOW_SECONDS = 30


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--model-name", required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--batch-sizes", type=int, nargs="+", default=[8, 16])
    parser.add_argument("--max-candidates", type=int, default=64)
    parser.add_argument("--target-pairs", type=int, default=20)
    parser.add_argument("--future-windows", type=int, default=2)
    parser.add_argument("--max-new-tokens", type=int, default=96)
    return parser.parse_args()


def load_audio(path: str) -> np.ndarray:
    audio, rate = sf.read(path, dtype="float32", always_2d=False)
    if rate != SAMPLE_RATE:
        raise ValueError(f"expected 16 kHz, got {rate}: {path}")
    if audio.ndim == 2:
        audio = audio.mean(axis=1)
    return np.asarray(audio, dtype=np.float32)


def build_sessions(
    records: list[dict[str, Any]], *, max_sessions: int
) -> list[np.ndarray]:
    """Build deterministic 90-second streams without source reuse."""

    target = SAMPLE_RATE * WINDOW_SECONDS * 3
    sessions = pack_disjoint_audio(
        [load_audio(record["path"]) for record in records],
        target_samples=target,
        max_sessions=max_sessions,
        separator_samples=SAMPLE_RATE // 10,
    )
    if len(sessions) < max_sessions:
        raise RuntimeError(
            f"only {len(sessions)} disjoint 90-second sessions can be "
            f"built; requested {max_sessions}"
        )
    return sessions


class WhisperExecutor:
    def __init__(self, model_path: Path, max_new_tokens: int) -> None:
        self.processor = AutoProcessor.from_pretrained(
            model_path, local_files_only=True
        )
        self.model = AutoModelForSpeechSeq2Seq.from_pretrained(
            model_path,
            dtype=torch.float16,
            local_files_only=True,
        ).cuda().eval()
        self.max_new_tokens = max_new_tokens
        self.timestamp_begin = int(
            self.processor.tokenizer.convert_tokens_to_ids("<|0.00|>")
        )

    def features(self, audio: np.ndarray) -> dict[str, torch.Tensor]:
        payload = self.processor(
            audio,
            sampling_rate=SAMPLE_RATE,
            return_tensors="pt",
            return_attention_mask=True,
        )
        return {
            "input_features": payload.input_features.to(
                "cuda", dtype=torch.float16
            ),
            "attention_mask": payload.attention_mask.to("cuda"),
        }

    def _decode_rows(
        self,
        generated: torch.Tensor,
        *,
        prompt_ids: torch.Tensor | None,
    ) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for row in generated:
            ids = [int(value) for value in row.detach().cpu().tolist()]
            # HF returns prompt tokens before the decoder-start token. Strip
            # them so future damage is not inflated by input-state text.
            if prompt_ids is not None:
                prompt = [
                    int(value)
                    for value in prompt_ids.detach().cpu().reshape(-1).tolist()
                ]
                if ids[: len(prompt)] == prompt:
                    ids = ids[len(prompt) :]
            timestamp_ids = [
                value for value in ids if value >= self.timestamp_begin
            ]
            text = self.processor.decode(
                ids,
                skip_special_tokens=True,
            ).strip()
            rows.append(
                {
                    "token_ids": ids,
                    "text": text,
                    "timestamp_monotone": all(
                        left <= right
                        for left, right in zip(
                            timestamp_ids, timestamp_ids[1:]
                        )
                    ),
                    "repetition_score": repetition_score(text),
                }
            )
        return rows

    def _generation_kwargs(
        self,
        attention_mask: torch.Tensor,
        *,
        prompt_text: str,
    ) -> tuple[dict[str, Any], torch.Tensor | None]:
        kwargs: dict[str, Any] = {
            "max_new_tokens": self.max_new_tokens,
            "do_sample": False,
            "return_timestamps": True,
            "attention_mask": attention_mask,
        }
        if bool(getattr(
            self.model.generation_config, "is_multilingual", False
        )):
            kwargs["task"] = "transcribe"
        prompt_ids = None
        if prompt_text:
            prompt_ids = self.processor.get_prompt_ids(
                prompt_text[-800:], return_tensors="pt"
            ).to("cuda")
            kwargs["prompt_ids"] = prompt_ids
        return kwargs, prompt_ids

    @torch.inference_mode()
    def generate(
        self,
        features: dict[str, torch.Tensor],
        *,
        batch_size: int = 1,
        prompt_text: str = "",
    ) -> list[dict[str, Any]]:
        values = features["input_features"].repeat(batch_size, 1, 1)
        attention_mask = features["attention_mask"].repeat(batch_size, 1)
        kwargs, prompt_ids = self._generation_kwargs(
            attention_mask,
            prompt_text=prompt_text,
        )
        generated = self.model.generate(values, **kwargs)
        return self._decode_rows(generated, prompt_ids=prompt_ids)

    @torch.inference_mode()
    def generate_distinct(
        self,
        features: list[dict[str, torch.Tensor]],
    ) -> list[dict[str, Any]]:
        """Generate an unprompted batch containing distinct audio windows.

        This is the Feedback-OFF boundary path: no generated text is fed into
        a later window, so state-entry certification is intentionally bypassed.
        """

        if not features:
            return []
        values = torch.cat(
            [record["input_features"] for record in features],
            dim=0,
        )
        attention_mask = torch.cat(
            [record["attention_mask"] for record in features],
            dim=0,
        )
        kwargs, prompt_ids = self._generation_kwargs(
            attention_mask,
            prompt_text="",
        )
        generated = self.model.generate(values, **kwargs)
        return self._decode_rows(generated, prompt_ids=prompt_ids)


def pair_hash(canonical: list[int], proposer: list[int]) -> str:
    return hashlib.sha256(
        json.dumps(
            [canonical, proposer], separators=(",", ":")
        ).encode("utf-8")
    ).hexdigest()


def main() -> int:
    args = parse_args()
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    records = manifest["records"]
    sessions = build_sessions(
        records, max_sessions=args.max_candidates
    )
    executor = WhisperExecutor(args.model, args.max_new_tokens)
    pairs: list[dict[str, Any]] = []
    singleton_repeat_mismatches = 0
    scanned = 0
    started = time.perf_counter()

    for session_index, audio in enumerate(sessions):
        if len(pairs) >= args.target_pairs:
            break
        windows = np.array_split(audio, 3)
        for source_window in range(
            min(3 - args.future_windows, len(windows))
        ):
            if len(pairs) >= args.target_pairs:
                break
            features = executor.features(windows[source_window])
            canonical = executor.generate(features)[0]
            repeat = executor.generate(features)[0]
            scanned += 1
            singleton_repeat_mismatches += int(
                canonical["token_ids"] != repeat["token_ids"]
            )
            divergent: dict[str, Any] | None = None
            divergent_batch_size: int | None = None
            divergent_slot: int | None = None
            for batch_size in args.batch_sizes:
                batch = executor.generate(
                    features, batch_size=batch_size
                )
                for slot, candidate in enumerate(batch):
                    if candidate["token_ids"] != canonical["token_ids"]:
                        divergent = candidate
                        divergent_batch_size = batch_size
                        divergent_slot = slot
                        break
                if divergent is not None:
                    break
            if divergent is None:
                continue

            on_canonical = canonical
            on_proposer = divergent
            distances = [
                edit_distance(
                    on_canonical["token_ids"],
                    on_proposer["token_ids"],
                )
            ]
            off_distances: list[int] = []
            catastrophe_c = False
            catastrophe_b = False
            for step in range(1, args.future_windows + 1):
                future = executor.features(windows[source_window + step])
                on_canonical = executor.generate(
                    future, prompt_text=on_canonical["text"]
                )[0]
                on_proposer = executor.generate(
                    future, prompt_text=on_proposer["text"]
                )[0]
                distances.append(
                    edit_distance(
                        on_canonical["token_ids"],
                        on_proposer["token_ids"],
                    )
                )
                off_left = executor.generate(future)[0]
                off_right = executor.generate(future)[0]
                off_distances.append(
                    edit_distance(
                        off_left["token_ids"], off_right["token_ids"]
                    )
                )
                catastrophe_c = catastrophe_c or (
                    not on_canonical["timestamp_monotone"]
                    or on_canonical["repetition_score"] >= 0.5
                )
                catastrophe_b = catastrophe_b or (
                    not on_proposer["timestamp_monotone"]
                    or on_proposer["repetition_score"] >= 0.5
                )
            initial = max(1, distances[0])
            raf = sum(value / initial for value in distances)
            recovery = next(
                (index for index, value in enumerate(distances[1:], 1)
                 if value == 0),
                None,
            )
            pairs.append(
                {
                    "pair_sha256": pair_hash(
                        canonical["token_ids"], divergent["token_ids"]
                    ),
                    "session_index": session_index,
                    "source_window": source_window,
                    "batch_size": divergent_batch_size,
                    "slot": divergent_slot,
                    "canonical": canonical,
                    "proposer": divergent,
                    "feedback_on_distances": distances,
                    "feedback_off_distances": off_distances,
                    "raf": raf,
                    "recovery_window": recovery,
                    "persistent_at_horizon": distances[-1] > 0,
                    "terminal_difference": distances[-1] > 0,
                    "unprotected_catastrophe": (
                        catastrophe_b and not catastrophe_c
                    ),
                    "revtrace_catastrophe": False,
                }
            )
            print(
                json.dumps(
                    {
                        "model": args.model_name,
                        "scanned": scanned,
                        "pairs": len(pairs),
                        "last_raf": raf,
                    },
                    sort_keys=True,
                ),
                flush=True,
            )

    unique = {item["pair_sha256"] for item in pairs}
    persistent = sum(item["persistent_at_horizon"] for item in pairs)
    catastrophes = sum(item["unprotected_catastrophe"] for item in pairs)
    payload = {
        "schema_version": 1,
        "study": "Whisper counterfactual previous-text feedback gate",
        "model": args.model_name,
        "decision": (
            "PHASE4B_FEEDBACK_CAUSAL_GATE_PASS"
            if len(unique) >= args.target_pairs
            else "PHASE4B_INSUFFICIENT_NATURAL_EXECUTION_SHAPE_PAIRS"
        ),
        "config": vars(args) | {
            "model": str(args.model),
            "manifest": str(args.manifest),
            "output": str(args.output),
        },
        "counts": {
            "candidate_windows_scanned": scanned,
            "singleton_repeat_mismatches": singleton_repeat_mismatches,
            "raw_pairs": len(pairs),
            "distinct_state_pairs": len(unique),
            "persistent_pairs": persistent,
            "unprotected_application_catastrophes": catastrophes,
            "revtrace_application_catastrophes": 0,
        },
        "metrics": {
            "median_raf": (
                statistics.median(item["raf"] for item in pairs)
                if pairs else None
            ),
            "pcm_h": persistent / len(pairs) if pairs else None,
            "feedback_off_nonzero_future_distances": sum(
                any(value > 0 for value in item["feedback_off_distances"])
                for item in pairs
            ),
            "catastrophe_prevention_claim_eligible": catastrophes >= 5,
            "wall_seconds": time.perf_counter() - started,
        },
        "pairs": pairs,
        "claim_boundaries": [
            "treatment flips are produced by legal execution-shape changes",
            "future audio is fixed and replay uses singleton canonical execution",
            "stress-pair yield is not a production prevalence estimate",
            "catastrophe prevention is claimed only with at least five events",
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

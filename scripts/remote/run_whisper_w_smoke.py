#!/usr/bin/env python3
"""W1 smoke: distinct prompt batching, repeatability and prompt isolation."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import soundfile as sf
import torch

from whisper_batched_executor import DistinctPromptWhisper


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--device", default="cuda:0")
    return parser.parse_args()


def load(path: str) -> np.ndarray:
    audio, rate = sf.read(path, dtype="float32", always_2d=False)
    if rate != 16_000:
        raise ValueError(rate)
    if audio.ndim == 2:
        audio = audio.mean(axis=1)
    return np.asarray(audio, dtype=np.float32)


def main() -> int:
    args = parse_args()
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    audio = [load(row["path"]) for row in manifest["records"][:4]]
    prompts = [
        "",
        "A previous discussion about astronomy.",
        "The speaker was describing a railway station.",
        "This is an intentionally different prompt.",
    ]
    executor = DistinctPromptWhisper(
        args.model,
        device=args.device,
        dtype=torch.float16,
        max_new_tokens=64,
    )
    singleton = [
        executor.canonical(item, prompt)
        for item, prompt in zip(audio, prompts)
    ]
    official = [
        executor.official_canonical(item, prompt)
        for item, prompt in zip(audio, prompts)
    ]
    batch = executor.generate(audio, prompts)
    repeat = executor.generate(audio, prompts)
    raw_prompt_rows = [
        executor.advance_prompt((), record.token_ids)
        for record in singleton
    ]
    raw_singleton = [
        executor.canonical(item, prompt)
        for item, prompt in zip(audio, raw_prompt_rows)
    ]
    raw_batch = executor.generate(audio, raw_prompt_rows)
    payload = {
        "schema_version": 1,
        "study": "W1 distinct-prompt batching smoke",
        "counts": {
            "rows": len(audio),
            "batch_repeat_mismatches": sum(
                left.token_ids != right.token_ids
                for left, right in zip(batch, repeat)
            ),
            "singleton_batch_mismatches": sum(
                left.token_ids != right.token_ids
                for left, right in zip(singleton, batch)
            ),
            "w_canonical_official_mismatches": sum(
                left.token_ids != right.token_ids
                for left, right in zip(singleton, official)
            ),
            "distinct_prompt_token_rows": len(
                {row.prompt_token_ids for row in batch}
            ),
            "raw_history_singleton_batch_mismatches": sum(
                left.token_ids != right.token_ids
                for left, right in zip(raw_singleton, raw_batch)
            ),
            "raw_history_rows_with_start_marker": sum(
                bool(row)
                and row[0] == executor.start_of_previous
                for row in raw_prompt_rows
            ),
        },
        "rows": [
            {
                "prompt": prompt,
                "singleton_text": one.text,
                "batch_text": many.text,
                "repeat_text": again.text,
                "official_text": upstream.text,
                "w_canonical_official_exact": (
                    one.token_ids == upstream.token_ids
                ),
                "w_token_ids": list(one.token_ids),
                "official_token_ids": list(upstream.token_ids),
                "singleton_margin": one.minimum_margin,
                "batch_margin": many.minimum_margin,
                "prompt_token_ids": list(many.prompt_token_ids),
            }
            for prompt, one, many, again, upstream in zip(
                prompts, singleton, batch, repeat, official
            )
        ],
        "claim_boundary": (
            "batch-size-one from this executor is the versioned W-suite "
            "canonical; equality with the legacy HF generate path is not "
            "assumed"
        ),
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

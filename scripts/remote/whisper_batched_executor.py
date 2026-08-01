#!/usr/bin/env python3
"""Distinct-prompt batched greedy Whisper execution.

Transformers' Whisper ``prompt_ids`` argument is rank-1, so it cannot encode a
different previous-text prompt for every row in a serving batch.  This module
uses the public encoder/decoder forward APIs directly.  Left padding is paired
with explicit per-row decoder positions; prompt pads therefore do not acquire
state semantics. Callers accumulate raw tokens from confirmed prior segments
and this executor derives the prompt bound from the checkpoint's target
context. The same implementation with batch size one is the versioned
canonical path used by the W0-W7 closure.
"""

from __future__ import annotations

import hashlib
import json
import math
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence

import numpy as np
import torch
from transformers import AutoModelForSpeechSeq2Seq, AutoProcessor
from transformers.modeling_outputs import BaseModelOutput

from revtrace.whisper_state import append_prompt_tokens


SAMPLE_RATE = 16_000


@dataclass(frozen=True)
class WhisperCandidate:
    token_ids: tuple[int, ...]
    text: str
    minimum_margin: float | None
    elapsed_seconds: float
    prompt_token_ids: tuple[int, ...]
    generation_steps: int = 0
    terminated_by_eos: bool = False

    @property
    def token_sha256(self) -> str:
        return hashlib.sha256(
            json.dumps(
                self.token_ids, separators=(",", ":")
            ).encode("utf-8")
        ).hexdigest()


class DistinctPromptWhisper:
    def __init__(
        self,
        model_path: Path,
        *,
        device: str,
        dtype: torch.dtype = torch.float16,
        max_new_tokens: int = 96,
        max_prompt_tokens: int | None = None,
    ) -> None:
        self.device = torch.device(device)
        self.dtype = dtype
        self.processor = AutoProcessor.from_pretrained(
            model_path,
            local_files_only=True,
        )
        self.model = AutoModelForSpeechSeq2Seq.from_pretrained(
            model_path,
            torch_dtype=dtype,
            local_files_only=True,
        ).to(self.device).eval()
        self.max_new_tokens = int(max_new_tokens)
        self.max_prompt_tokens = int(
            max_prompt_tokens
            if max_prompt_tokens is not None
            else self.model.config.max_target_positions // 2
        )
        config = self.model.generation_config
        self.decoder_start = int(config.decoder_start_token_id)
        self.no_timestamps = int(config.no_timestamps_token_id)
        self.eos = int(config.eos_token_id)
        self.pad = int(config.pad_token_id)
        self.start_of_previous = int(
            self.processor.tokenizer.convert_tokens_to_ids(
                "<|startofprev|>"
            )
        )
        self.suppress = tuple(
            int(value)
            for value in (config.suppress_tokens or ())
            if int(value) >= 0
        )
        self.begin_suppress = tuple(
            int(value)
            for value in (config.begin_suppress_tokens or ())
            if int(value) >= 0
        )

    def prompt_tokens(
        self,
        prompt: str | Sequence[int],
    ) -> tuple[int, ...]:
        if not prompt:
            return ()
        if isinstance(prompt, str):
            values = [
                int(value)
                for value in self.processor.get_prompt_ids(
                    prompt[-800:],
                    return_tensors="pt",
                ).reshape(-1).tolist()
            ]
        else:
            values = [int(value) for value in prompt]
            if values[0] != self.start_of_previous:
                values.insert(0, self.start_of_previous)
        if len(values) > self.max_prompt_tokens:
            # Preserve <|startofprev|> and the most recent prompt context.
            values = [values[0], *values[-(self.max_prompt_tokens - 1) :]]
        return tuple(values)

    def advance_prompt(
        self,
        current: Sequence[int],
        segment: Sequence[int],
    ) -> tuple[int, ...]:
        return append_prompt_tokens(
            current,
            segment,
            start_of_previous_token=self.start_of_previous,
            maximum_tokens=self.max_prompt_tokens,
        )

    def _features(
        self,
        audio: Sequence[np.ndarray],
    ) -> tuple[torch.Tensor, torch.Tensor]:
        payload = self.processor(
            [np.asarray(value, dtype=np.float32) for value in audio],
            sampling_rate=SAMPLE_RATE,
            return_tensors="pt",
            return_attention_mask=True,
        )
        return (
            payload.input_features.to(self.device, dtype=self.dtype),
            payload.attention_mask.to(self.device),
        )

    def _prefix_batch(
        self,
        prompts: Sequence[str | Sequence[int]],
    ) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor, list[tuple[int, ...]]]:
        prompt_rows = [self.prompt_tokens(text) for text in prompts]
        rows = [
            (*prompt, self.decoder_start, self.no_timestamps)
            for prompt in prompt_rows
        ]
        maximum = max(len(row) for row in rows)
        input_ids = torch.full(
            (len(rows), maximum),
            self.pad,
            dtype=torch.long,
            device=self.device,
        )
        mask = torch.zeros_like(input_ids)
        positions = torch.zeros_like(input_ids)
        for index, row in enumerate(rows):
            length = len(row)
            input_ids[index, maximum - length :] = torch.tensor(
                row,
                dtype=torch.long,
                device=self.device,
            )
            mask[index, maximum - length :] = 1
            positions[index, maximum - length :] = torch.arange(
                length,
                dtype=torch.long,
                device=self.device,
            )
        return input_ids, mask, positions, prompt_rows

    def _filter_logits(
        self,
        logits: torch.Tensor,
        *,
        first_step: bool,
        finished: torch.Tensor,
    ) -> torch.Tensor:
        logits = logits.float()
        if self.suppress:
            logits[:, list(self.suppress)] = -math.inf
        if first_step and self.begin_suppress:
            logits[:, list(self.begin_suppress)] = -math.inf
        if bool(finished.any()):
            logits[finished] = -math.inf
            logits[finished, self.eos] = 0.0
        return logits

    @torch.inference_mode()
    def generate(
        self,
        audio: Sequence[np.ndarray],
        prompts: Sequence[str | Sequence[int]],
    ) -> list[WhisperCandidate]:
        if len(audio) != len(prompts) or not audio:
            raise ValueError("audio and prompts must be non-empty and aligned")
        started = time.perf_counter()
        input_features, attention_mask = self._features(audio)
        decoder_ids, decoder_mask, decoder_positions, prompt_rows = (
            self._prefix_batch(prompts)
        )
        encoder = self.model.model.encoder(
            input_features,
            attention_mask=attention_mask,
            return_dict=True,
        )
        encoder_outputs = BaseModelOutput(
            last_hidden_state=encoder.last_hidden_state
        )
        output = self.model(
            encoder_outputs=encoder_outputs,
            attention_mask=attention_mask,
            decoder_input_ids=decoder_ids,
            decoder_attention_mask=decoder_mask,
            decoder_position_ids=decoder_positions,
            use_cache=True,
            return_dict=True,
        )
        past = output.past_key_values
        finished = torch.zeros(
            len(audio), dtype=torch.bool, device=self.device
        )
        generated: list[list[int]] = [[] for _ in audio]
        margins: list[list[float]] = [[] for _ in audio]
        real_lengths = decoder_mask.sum(dim=1)

        for step in range(self.max_new_tokens):
            logits = self._filter_logits(
                output.logits[:, -1, :],
                first_step=step == 0,
                finished=finished,
            )
            top = torch.topk(logits, k=2, dim=-1)
            next_tokens = top.indices[:, 0]
            step_margins = top.values[:, 0] - top.values[:, 1]
            for row in range(len(audio)):
                if bool(finished[row]):
                    continue
                token = int(next_tokens[row].item())
                margins[row].append(float(step_margins[row].item()))
                if token == self.eos:
                    finished[row] = True
                else:
                    # HF Whisper's short-form wrapper removes the terminal
                    # EOS from returned transcription ids.  Keep the EOS
                    # decision in the margin audit, but normalize the exposed
                    # candidate sequence to that upstream contract.
                    generated[row].append(token)
            if bool(finished.all()):
                break
            decoder_mask = torch.cat(
                [
                    decoder_mask,
                    torch.ones(
                        (len(audio), 1),
                        dtype=decoder_mask.dtype,
                        device=self.device,
                    ),
                ],
                dim=1,
            )
            next_positions = (real_lengths + step).reshape(-1, 1)
            output = self.model(
                encoder_outputs=encoder_outputs,
                attention_mask=attention_mask,
                decoder_input_ids=next_tokens.reshape(-1, 1),
                decoder_attention_mask=decoder_mask,
                decoder_position_ids=next_positions,
                past_key_values=past,
                use_cache=True,
                return_dict=True,
            )
            past = output.past_key_values

        torch.cuda.current_stream(self.device).synchronize()
        elapsed = time.perf_counter() - started
        records: list[WhisperCandidate] = []
        for ids, row_margins, prompt in zip(
            generated, margins, prompt_rows
        ):
            records.append(
                WhisperCandidate(
                    token_ids=tuple(ids),
                    text=self.processor.decode(
                        ids,
                        skip_special_tokens=True,
                    ).strip(),
                    minimum_margin=(
                        min(row_margins) if row_margins else None
                    ),
                    elapsed_seconds=elapsed,
                    prompt_token_ids=prompt,
                    # Exposed transcription ids intentionally omit EOS.  An
                    # EOS chosen on the final permitted step therefore looks
                    # like max_new_tokens - 1 ids even though the proposal
                    # exhausted its decoder work budget.  Preserve the actual
                    # number of decoder decisions for the authority protocol.
                    generation_steps=len(row_margins),
                    terminated_by_eos=(len(ids) < len(row_margins)),
                )
            )
        return records

    def canonical(
        self,
        audio: np.ndarray,
        prompt: str | Sequence[int],
    ) -> WhisperCandidate:
        return self.generate([audio], [prompt])[0]

    @torch.inference_mode()
    def official_canonical(
        self,
        audio: np.ndarray,
        prompt: str,
    ) -> WhisperCandidate:
        """Run upstream HF generation for a semantic-parity audit.

        The W-suite authority remains the batch-size-one form of
        :meth:`generate`, since upstream ``prompt_ids`` cannot represent a
        different previous-text prompt for every batch row.  This method is a
        regression oracle, not a second serving authority.
        """

        started = time.perf_counter()
        input_features, attention_mask = self._features([audio])
        kwargs: dict[str, Any] = {
            "attention_mask": attention_mask,
            "do_sample": False,
            "max_new_tokens": self.max_new_tokens,
            "return_timestamps": False,
        }
        prompt_ids: torch.Tensor | None = None
        if prompt:
            prompt_ids = self.processor.get_prompt_ids(
                prompt[-800:],
                return_tensors="pt",
            ).to(self.device)
            if prompt_ids.numel() > self.max_prompt_tokens:
                prompt_ids = torch.cat(
                    (
                        prompt_ids[:1],
                        prompt_ids[-(self.max_prompt_tokens - 1) :],
                    )
                )
            kwargs["prompt_ids"] = prompt_ids
        generated = self.model.generate(input_features, **kwargs)
        ids = [int(value) for value in generated[0].detach().cpu().tolist()]
        prompt_row: tuple[int, ...] = ()
        if prompt_ids is not None:
            prompt_row = tuple(
                int(value)
                for value in prompt_ids.detach().cpu().reshape(-1).tolist()
            )
            if tuple(ids[: len(prompt_row)]) == prompt_row:
                ids = ids[len(prompt_row) :]
        control = (self.decoder_start, self.no_timestamps)
        if tuple(ids[: len(control)]) == control:
            ids = ids[len(control) :]
        torch.cuda.current_stream(self.device).synchronize()
        return WhisperCandidate(
            token_ids=tuple(ids),
            text=self.processor.decode(
                ids,
                skip_special_tokens=True,
            ).strip(),
            minimum_margin=None,
            elapsed_seconds=time.perf_counter() - started,
            prompt_token_ids=prompt_row,
        )

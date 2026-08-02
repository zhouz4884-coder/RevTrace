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
import statistics
import time
import zlib
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
    first_step_no_speech_probability: float | None = None
    average_token_log_probability: float | None = None
    compression_ratio: float | None = None

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
        self.no_speech = int(
            self.processor.tokenizer.convert_tokens_to_ids("<|nospeech|>")
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
        *,
        max_steps: int | None = None,
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
        token_log_probabilities: list[list[float]] = [[] for _ in audio]
        no_speech_probabilities: list[float | None] = [None for _ in audio]
        real_lengths = decoder_mask.sum(dim=1)

        step_budget = int(
            self.max_new_tokens if max_steps is None else max_steps
        )
        if not 0 < step_budget <= self.max_new_tokens:
            raise ValueError("max_steps must lie in [1, max_new_tokens]")
        for step in range(step_budget):
            raw_logits = output.logits[:, -1, :].float()
            if step == 0 and self.no_speech >= 0:
                probabilities = torch.softmax(raw_logits, dim=-1)
                for row in range(len(audio)):
                    no_speech_probabilities[row] = float(
                        probabilities[row, self.no_speech].item()
                    )
            logits = self._filter_logits(
                raw_logits,
                first_step=step == 0,
                finished=finished,
            )
            log_probabilities = torch.log_softmax(logits, dim=-1)
            top = torch.topk(logits, k=2, dim=-1)
            next_tokens = top.indices[:, 0]
            step_margins = top.values[:, 0] - top.values[:, 1]
            for row in range(len(audio)):
                if bool(finished[row]):
                    continue
                token = int(next_tokens[row].item())
                margins[row].append(float(step_margins[row].item()))
                token_log_probabilities[row].append(float(
                    log_probabilities[row, token].item()
                ))
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
        for ids, row_margins, row_log_probs, no_speech, prompt in zip(
            generated,
            margins,
            token_log_probabilities,
            no_speech_probabilities,
            prompt_rows,
        ):
            text = self.processor.decode(
                ids,
                skip_special_tokens=True,
            ).strip()
            encoded_text = text.encode("utf-8")
            records.append(
                WhisperCandidate(
                    token_ids=tuple(ids),
                    text=text,
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
                    first_step_no_speech_probability=no_speech,
                    average_token_log_probability=(
                        statistics.fmean(row_log_probs)
                        if row_log_probs else None
                    ),
                    compression_ratio=(
                        len(encoded_text) / max(1, len(zlib.compress(encoded_text)))
                        if encoded_text else 0.0
                    ),
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
    def acoustic_candidate_scores(
        self,
        audio: np.ndarray,
        candidates: Sequence[Sequence[int]],
    ) -> list[dict[str, float]]:
        """Teacher-force candidate transcripts without previous-text context.

        The score is deliberately conditioned only on the current acoustic
        window.  It therefore cannot reward a recovery candidate merely for
        repeating its capsule prompt.  This is a selection signal, not a
        correctness certificate or a replacement for the EFSC authority
        contract.
        """

        if not candidates:
            raise ValueError("at least one candidate is required")
        input_features, attention_mask = self._features([audio])
        encoder = self.model.model.encoder(
            input_features,
            attention_mask=attention_mask,
            return_dict=True,
        )
        rows = [
            (
                self.decoder_start,
                self.no_timestamps,
                *(int(token) for token in candidate),
                self.eos,
            )
            for candidate in candidates
        ]
        maximum = max(len(row) for row in rows)
        decoder_ids = torch.full(
            (len(rows), maximum - 1),
            self.pad,
            dtype=torch.long,
            device=self.device,
        )
        targets = torch.full_like(decoder_ids, self.pad)
        decoder_mask = torch.zeros_like(decoder_ids)
        score_mask = torch.zeros_like(decoder_ids, dtype=torch.bool)
        decoder_positions = torch.zeros_like(decoder_ids)
        for index, row in enumerate(rows):
            inputs = row[:-1]
            outputs = row[1:]
            offset = maximum - len(row)
            decoder_ids[index, offset:] = torch.tensor(
                inputs, dtype=torch.long, device=self.device
            )
            targets[index, offset:] = torch.tensor(
                outputs, dtype=torch.long, device=self.device
            )
            decoder_mask[index, offset:] = 1
            decoder_positions[index, offset:] = torch.arange(
                len(inputs), dtype=torch.long, device=self.device
            )
            # The first scored target follows the fixed decoder control
            # prefix; include every transcript token and terminal EOS.
            score_mask[index, offset + 1:] = True
        repeated_encoder = BaseModelOutput(
            last_hidden_state=encoder.last_hidden_state.repeat(
                len(rows), 1, 1
            )
        )
        repeated_attention = attention_mask.repeat(len(rows), 1)
        output = self.model(
            encoder_outputs=repeated_encoder,
            attention_mask=repeated_attention,
            decoder_input_ids=decoder_ids,
            decoder_attention_mask=decoder_mask,
            decoder_position_ids=decoder_positions,
            use_cache=False,
            return_dict=True,
        )
        log_probabilities = torch.log_softmax(output.logits.float(), dim=-1)
        selected = log_probabilities.gather(
            -1, targets.clamp_min(0).unsqueeze(-1)
        ).squeeze(-1)
        results: list[dict[str, float]] = []
        for index in range(len(rows)):
            values = selected[index][score_mask[index]]
            results.append({
                "mean_log_probability": float(values.mean().item()),
                "sum_log_probability": float(values.sum().item()),
                "scored_tokens": float(values.numel()),
            })
        return results

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

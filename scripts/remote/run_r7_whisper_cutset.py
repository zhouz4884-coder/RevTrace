#!/usr/bin/env python3
"""Diagnose the minimal Whisper projection-replay cutset.

The experiment holds every audio window and EFSC prompt state fixed, then
factorizes execution into encoder and decoder arithmetic paths:

* SE+SD: singleton encoder and singleton decoder (canonical reference);
* BE+BD: batched encoder and batched decoder (serving proposer);
* BE+SD: batched encoder and singleton decoder;
* SE+BD: singleton encoder and batched decoder.

This is a same-input causal decomposition.  It does not tune the frozen EFSC
policy and therefore cannot conceal a failed quality gate.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import statistics
import time
from pathlib import Path
from typing import Any, Sequence

import numpy as np
import torch
from transformers.modeling_outputs import BaseModelOutput

from revtrace.feedback_coherence import (
    EFSCContract,
    ElasticFeedbackController,
    ElasticFeedbackState,
    FeedbackAction,
    FeedbackCandidate,
    FeedbackIdentity,
    WhisperHistoryAdapter,
)
from run_whisper_w_quality import build_sessions
from whisper_batched_executor import DistinctPromptWhisper, WhisperCandidate


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--policy", type=Path, required=True)
    parser.add_argument("--quality-trace", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--sessions-per-split", type=int, default=64)
    parser.add_argument("--duration-seconds", type=int, default=90)
    parser.add_argument("--window-seconds", type=int, default=10)
    parser.add_argument("--concurrency", type=int, default=16)
    parser.add_argument("--max-new-tokens", type=int, default=96)
    parser.add_argument("--seed", type=int, default=2026080701)
    parser.add_argument("--device", default="cuda:0")
    parser.add_argument(
        "--selection",
        choices=("quality-roots", "all"),
        default="quality-roots",
    )
    return parser.parse_args()


def token_digest(tokens: Sequence[int]) -> str:
    return hashlib.sha256(
        json.dumps(list(tokens), separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def contract_from_payload(
    executor: DistinctPromptWhisper, payload: dict[str, Any]
) -> EFSCContract:
    raw = payload["config"]["contract"]
    return EFSCContract(**raw)


def reconstruct_prompt_rows(
    payload: dict[str, Any], contract: EFSCContract
) -> list[list[tuple[int, ...]]]:
    """Reconstruct the exact frozen EFSC input prompt for every event."""

    adapter = WhisperHistoryAdapter(contract.maximum_prompt_tokens)
    controller = ElasticFeedbackController(contract)
    rows: list[list[tuple[int, ...]]] = []
    for session in payload["sessions"]:
        state = ElasticFeedbackState(
            FeedbackIdentity(f"s{session['session_id']}", 1, 1, 0)
        )
        prompts: list[tuple[int, ...]] = []
        for event in session["efsc_trace"]:
            state, preparation = controller.prepare_for_proposal(state, adapter)
            observed_preparation = (
                preparation.action.value
                if preparation.action is not None else None
            )
            prompt = tuple(atom.token_id for atom in state.atoms)
            if len(prompt) != int(event["prompt_tokens_for_proposal"]):
                raise AssertionError(
                    "prompt reconstruction length mismatch: "
                    f"{session['session_id']}/{event['window_index']} "
                    f"{len(prompt)}!={event['prompt_tokens_for_proposal']} "
                    f"(reconstructed preparation={observed_preparation!r})"
                )
            prompts.append(prompt)
            candidate = FeedbackCandidate(
                session_id=state.identity.session_id,
                contract_epoch=state.identity.contract_epoch,
                policy_version=state.identity.policy_version,
                parent_state_version=state.identity.state_version,
                token_ids=tuple(int(v) for v in event["candidate_token_ids"]),
                minimum_margin=event["minimum_margin"],
                terminal=(
                    int(event["window_index"])
                    == len(session["efsc_trace"]) - 1
                ),
            )
            state, decision = controller.step(state, candidate, adapter)
            if decision.action.value != event["decision_action"]:
                raise AssertionError("prompt reconstruction decision mismatch")
        rows.append(prompts)
    return rows


@torch.inference_mode()
def encode(
    executor: DistinctPromptWhisper,
    audio: Sequence[np.ndarray],
    *,
    singleton: bool,
) -> tuple[torch.Tensor, torch.Tensor]:
    if not singleton:
        features, mask = executor._features(audio)
        output = executor.model.model.encoder(
            features, attention_mask=mask, return_dict=True
        )
        return output.last_hidden_state, mask

    hidden_rows: list[torch.Tensor] = []
    mask_rows: list[torch.Tensor] = []
    for row in audio:
        features, mask = executor._features([row])
        output = executor.model.model.encoder(
            features, attention_mask=mask, return_dict=True
        )
        hidden_rows.append(output.last_hidden_state)
        mask_rows.append(mask)
    return torch.cat(hidden_rows, dim=0), torch.cat(mask_rows, dim=0)


@torch.inference_mode()
def decode(
    executor: DistinctPromptWhisper,
    hidden: torch.Tensor,
    attention_mask: torch.Tensor,
    prompts: Sequence[Sequence[int]],
) -> list[WhisperCandidate]:
    decoder_ids, decoder_mask, decoder_positions, prompt_rows = (
        executor._prefix_batch(prompts)
    )
    encoded = BaseModelOutput(last_hidden_state=hidden)
    output = executor.model(
        encoder_outputs=encoded,
        attention_mask=attention_mask,
        decoder_input_ids=decoder_ids,
        decoder_attention_mask=decoder_mask,
        decoder_position_ids=decoder_positions,
        use_cache=True,
        return_dict=True,
    )
    past = output.past_key_values
    finished = torch.zeros(
        len(prompts), dtype=torch.bool, device=executor.device
    )
    generated: list[list[int]] = [[] for _ in prompts]
    margins: list[list[float]] = [[] for _ in prompts]
    real_lengths = decoder_mask.sum(dim=1)
    for step in range(executor.max_new_tokens):
        logits = executor._filter_logits(
            output.logits[:, -1, :],
            first_step=step == 0,
            finished=finished,
        )
        top = torch.topk(logits, k=2, dim=-1)
        next_tokens = top.indices[:, 0]
        step_margins = top.values[:, 0] - top.values[:, 1]
        for row in range(len(prompts)):
            if bool(finished[row]):
                continue
            token = int(next_tokens[row].item())
            margins[row].append(float(step_margins[row].item()))
            if token == executor.eos:
                finished[row] = True
            else:
                generated[row].append(token)
        if bool(finished.all()):
            break
        decoder_mask = torch.cat(
            (
                decoder_mask,
                torch.ones(
                    (len(prompts), 1),
                    dtype=decoder_mask.dtype,
                    device=executor.device,
                ),
            ),
            dim=1,
        )
        positions = (real_lengths + step).reshape(-1, 1)
        output = executor.model(
            encoder_outputs=encoded,
            attention_mask=attention_mask,
            decoder_input_ids=next_tokens.reshape(-1, 1),
            decoder_attention_mask=decoder_mask,
            decoder_position_ids=positions,
            past_key_values=past,
            use_cache=True,
            return_dict=True,
        )
        past = output.past_key_values
    records: list[WhisperCandidate] = []
    for ids, row_margins, prompt in zip(generated, margins, prompt_rows):
        records.append(
            WhisperCandidate(
                token_ids=tuple(ids),
                text=executor.processor.decode(
                    ids, skip_special_tokens=True
                ).strip(),
                minimum_margin=(
                    min(row_margins) if row_margins else None
                ),
                elapsed_seconds=0.0,
                prompt_token_ids=prompt,
                generation_steps=len(row_margins),
                terminated_by_eos=(len(ids) < len(row_margins)),
            )
        )
    return records


def execute_cutset(
    executor: DistinctPromptWhisper,
    audio: Sequence[np.ndarray],
    prompts: Sequence[Sequence[int]],
    *,
    singleton_encoder: bool,
    singleton_decoder: bool,
) -> tuple[list[WhisperCandidate], float]:
    torch.cuda.synchronize(executor.device)
    started = time.perf_counter()
    hidden, mask = encode(executor, audio, singleton=singleton_encoder)
    if singleton_decoder:
        rows: list[WhisperCandidate] = []
        for index, prompt in enumerate(prompts):
            rows.extend(
                decode(
                    executor,
                    hidden[index : index + 1],
                    mask[index : index + 1],
                    [prompt],
                )
            )
    else:
        rows = decode(executor, hidden, mask, prompts)
    torch.cuda.synchronize(executor.device)
    return rows, time.perf_counter() - started


def selected_workloads(
    payload: dict[str, Any], concurrency: int, selection: str
) -> list[tuple[int, int]]:
    windows = len(payload["sessions"][0]["efsc_trace"])
    if selection == "all":
        return [
            (window, begin)
            for window in range(windows)
            for begin in range(0, len(payload["sessions"]), concurrency)
        ]
    chosen: set[tuple[int, int]] = set()
    for session in payload["sessions"]:
        if not session["catastrophic_outlier"]:
            continue
        sid = int(session["session_id"])
        for event in session["efsc_trace"]:
            canonical = session["canonical_trace"][event["window_index"]]
            candidate = event["candidate_text"]
            # Select the tail failures, not every event in an outlier session.
            length_gap = len(str(canonical["text"])) - len(candidate)
            if length_gap >= 50 or int(event["generation_steps"]) <= 10:
                chosen.add((int(event["window_index"]), sid // concurrency * concurrency))
    return sorted(chosen)


def main() -> int:
    args = parse_args()
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    quality = json.loads(args.quality_trace.read_text(encoding="utf-8"))
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
    executor = DistinctPromptWhisper(
        args.model, device=args.device, max_new_tokens=args.max_new_tokens
    )
    contract = contract_from_payload(executor, quality)
    prompts = reconstruct_prompt_rows(quality, contract)
    windows = [
        list(np.array_split(session.audio, args.duration_seconds // args.window_seconds))
        for session in sessions
    ]
    workloads = selected_workloads(quality, args.concurrency, args.selection)
    modes = {
        "SE_SD": (True, True),
        "BE_BD": (False, False),
        "BE_SD": (False, True),
        "SE_BD": (True, False),
    }
    timings = {name: 0.0 for name in modes}
    rows: list[dict[str, Any]] = []
    for window_index, begin in workloads:
        ids = list(range(begin, min(begin + args.concurrency, len(sessions))))
        audio = [windows[index][window_index] for index in ids]
        prompt_rows = [prompts[index][window_index] for index in ids]
        outcomes: dict[str, list[WhisperCandidate]] = {}
        for name, (single_encoder, single_decoder) in modes.items():
            records, elapsed = execute_cutset(
                executor,
                audio,
                prompt_rows,
                singleton_encoder=single_encoder,
                singleton_decoder=single_decoder,
            )
            outcomes[name] = records
            timings[name] += elapsed
        reference = outcomes["SE_SD"]
        traced = quality["sessions"]
        for position, session_id in enumerate(ids):
            record: dict[str, Any] = {
                "session_id": session_id,
                "window_index": window_index,
                "selected_quality_root": bool(
                    traced[session_id]["catastrophic_outlier"]
                ),
                "prompt_sha256": token_digest(prompt_rows[position]),
            }
            for name in modes:
                item = outcomes[name][position]
                record[name] = {
                    "token_sha256": item.token_sha256,
                    "token_count": len(item.token_ids),
                    "generation_steps": item.generation_steps,
                    "minimum_margin": item.minimum_margin,
                    "text": item.text,
                    "matches_SE_SD": item.token_ids == reference[position].token_ids,
                }
            record["reproduces_traced_BE_BD"] = (
                outcomes["BE_BD"][position].token_sha256
                == token_digest(
                    traced[session_id]["efsc_trace"][window_index][
                        "candidate_token_ids"
                    ]
                )
            )
            rows.append(record)

    summary: dict[str, Any] = {}
    for name in modes:
        mismatches = sum(not bool(row[name]["matches_SE_SD"]) for row in rows)
        summary[name] = {
            "events": len(rows),
            "projection_mismatches_vs_SE_SD": mismatches,
            "projection_exact_rate": 1.0 - mismatches / max(1, len(rows)),
            "seconds": timings[name],
            "time_fraction_of_full_canonical": (
                timings[name] / timings["SE_SD"]
                if timings["SE_SD"] else math.inf
            ),
        }
    root_rows = [row for row in rows if row["selected_quality_root"]]
    payload = {
        "schema_version": 1,
        "study": "RevTrace R7 projection replay cutset diagnostic",
        "selection": args.selection,
        "workloads": len(workloads),
        "events": len(rows),
        "quality_root_events": len(root_rows),
        "batch_reproduction_rate": statistics.fmean(
            bool(row["reproduces_traced_BE_BD"]) for row in rows
        ),
        "summary": summary,
        "rows": rows,
        "claim_boundary": (
            "same-input causal cutset diagnostic; a root-only run is not a "
            "held-out certificate or a serving-performance result"
        ),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "workloads": len(workloads),
        "events": len(rows),
        "reproduction": payload["batch_reproduction_rate"],
        "summary": summary,
    }))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

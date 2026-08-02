#!/usr/bin/env python3
"""Apply a frozen cross-granularity coverage fallback to an R9 trajectory."""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import numpy as np

from revtrace.dgft import (
    boundary_adjusted_coverage_deficit,
    balanced_replay_plan,
    classify_asymmetric_omission_conflict,
    classify_coverage_conflict,
    repeated_ngram_fraction,
)
from revtrace.whisper_state import capacity_rebase_required
from run_r9_segment_oracle import evaluate_rows
from run_whisper_w_quality import build_sessions
from whisper_batched_executor import DistinctPromptWhisper


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--model", type=Path, required=True)
    p.add_argument("--model-name", required=True)
    p.add_argument("--manifest", type=Path, required=True)
    p.add_argument("--source-quality", type=Path, required=True)
    p.add_argument("--coarse-result", type=Path, required=True)
    p.add_argument("--coverage-probe", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--coverage-threshold", type=float, default=0.20)
    p.add_argument("--coverage-asymmetry-margin", type=float, default=0.15)
    p.add_argument("--structural-coverage-threshold", type=float, default=0.20)
    p.add_argument("--post-rebase-forward-threshold", type=float, default=0.20)
    p.add_argument("--post-rebase-reverse-ceiling", type=float, default=0.20)
    p.add_argument("--degeneracy-repetition-threshold", type=float, default=0.25)
    p.add_argument(
        "--coverage-scope", choices=("session", "segment"), default="segment"
    )
    p.add_argument(
        "--repair-mode",
        choices=("suffix-rebase", "display-segment", "witness-select"),
        default="display-segment",
    )
    p.add_argument("--sessions-per-split", type=int, default=64)
    p.add_argument("--duration-seconds", type=int, default=50)
    p.add_argument("--window-seconds", type=int, default=10)
    p.add_argument("--seed", type=int, required=True)
    p.add_argument("--bootstrap-seed", type=int, required=True)
    p.add_argument("--device", default="cuda:0")
    return p.parse_args()


def replay_from_checkpoint(
    executor: DistinctPromptWhisper,
    session: object,
    *,
    start_sample: int,
    end_sample: int | None = None,
    parent_prompt: tuple[int, ...],
    window_seconds: int,
) -> tuple[str, float, int, float, list[dict[str, object]]]:
    prompt = parent_prompt
    pieces: list[str] = []
    trace: list[dict[str, object]] = []
    calls = 0
    audio_seconds = 0.0
    step = window_seconds * 16_000
    started = time.perf_counter()
    replay_end = session.audio.size if end_sample is None else min(
        int(end_sample), session.audio.size
    )
    for sub_start, sub_end in balanced_replay_plan(
        start_sample=start_sample, end_sample=replay_end,
        maximum_samples=step,
    ):
        if sub_start != start_sample and capacity_rebase_required(
            len(executor.prompt_tokens(prompt)),
            declared_next_segment_tokens=96,
            maximum_prompt_tokens=executor.max_prompt_tokens,
        ):
            prompt = ()
        record = executor.generate(
            [np.asarray(session.audio[sub_start:sub_end], dtype=np.float32)],
            [prompt], max_steps=96,
        )[0]
        calls += 1
        audio_seconds += (sub_end - sub_start) / 16_000
        pieces.append(record.text)
        prompt = executor.advance_prompt(prompt, record.token_ids)
        trace.append({
            "audio_start_sample": sub_start,
            "audio_end_sample": sub_end,
            "token_ids": list(record.token_ids),
            "token_sha256": record.token_sha256,
            "text": record.text,
            "next_prompt_token_ids": list(prompt),
            "generation_steps": record.generation_steps,
            "terminated_by_eos": record.terminated_by_eos,
            "compression_ratio": record.compression_ratio,
            "average_token_log_probability": (
                record.average_token_log_probability
            ),
        })
    return (
        " ".join(piece for piece in pieces if piece),
        time.perf_counter() - started,
        calls,
        audio_seconds,
        trace,
    )


def segment_decisions(
    *,
    fine_windows: list[str],
    coarse_trace: list[dict[str, object]],
    window_seconds: int,
    threshold: float,
    asymmetry_margin: float = 0.0,
    structural_threshold: float | None = None,
) -> list[dict[str, object]]:
    active_rows = [
        row for row in coarse_trace
        if not row.get("terminal_session_fallback")
    ]
    witnesses: list[str] = []
    coarse_texts: list[str] = []
    for coarse_row in active_rows:
        start_seconds = float(coarse_row["audio_start_window"]) * window_seconds
        end_seconds = float(coarse_row["audio_end_window"]) * window_seconds
        witnesses.append(" ".join(
            text for index, text in enumerate(fine_windows)
            if start_seconds <= (index + 0.5) * window_seconds < end_seconds
        ))
        coarse_texts.append(str(coarse_row["text"]))
    rows: list[dict[str, object]] = []
    for segment_index, coarse_row in enumerate(active_rows):
        start_seconds = float(coarse_row["audio_start_window"]) * window_seconds
        end_seconds = float(coarse_row["audio_end_window"]) * window_seconds
        witness = witnesses[segment_index]
        adjusted_deficit, raw_missing, residual_missing = (
            boundary_adjusted_coverage_deficit(
                witnesses, coarse_texts, segment_index
            )
        )
        decision = classify_coverage_conflict(
            witness, str(coarse_row["text"]), threshold=threshold
        )
        reverse_deficit = classify_coverage_conflict(
            str(coarse_row["text"]), witness, threshold=0.0
        ).deficit
        omission_margin = adjusted_deficit - reverse_deficit
        effective_threshold = (
            float(structural_threshold)
            if coarse_row.get("structural_conflict")
            and structural_threshold is not None else threshold
        )
        rows.append({
            "segment_index": segment_index,
            "start_seconds": start_seconds,
            "end_seconds": end_seconds,
            "fine_text": witness,
            "coarse_text": str(coarse_row["text"]),
            "deficit": decision.deficit,
            "boundary_adjusted_deficit": adjusted_deficit,
            "raw_missing_tokens": raw_missing,
            "residual_missing_tokens": residual_missing,
            "reverse_deficit": reverse_deficit,
            "omission_margin": omission_margin,
            "effective_threshold": effective_threshold,
            "fallback_required": (
                adjusted_deficit >= effective_threshold
                and omission_margin >= asymmetry_margin
            ),
        })
    return rows


def main() -> int:
    args = parse_args()
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    source = json.loads(args.source_quality.read_text(encoding="utf-8"))
    coarse = json.loads(args.coarse_result.read_text(encoding="utf-8"))
    probe = json.loads(args.coverage_probe.read_text(encoding="utf-8"))
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
    mode = next(iter(coarse["modes"].values()))
    outputs = [row["text"] for row in mode["sessions"]]
    structural = {
        sid for sid, trace in enumerate(mode["traces"])
        if any(row.get("terminal_session_fallback") for row in trace)
    }
    if args.coverage_scope == "session":
        decisions = []
        for row in probe["rows"]:
            decision = classify_asymmetric_omission_conflict(
                str(row["fine_text"]), str(row["coarse_text"]),
                forward_threshold=args.coverage_threshold,
                reverse_ceiling=max(
                    0.0, args.coverage_threshold - args.coverage_asymmetry_margin
                ),
            )
            decisions.append([{
                "segment_index": 0,
                "start_seconds": 0.0,
                "end_seconds": float(args.duration_seconds),
                "deficit": decision.forward_deficit,
                "reverse_deficit": decision.reverse_deficit,
                "omission_margin": (
                    decision.forward_deficit - decision.reverse_deficit
                ),
                "fallback_required": decision.fallback_required,
            }])
    else:
        decisions = [
            segment_decisions(
                fine_windows=list(probe_row["fine_window_texts"]),
                coarse_trace=list(trace),
                window_seconds=args.window_seconds,
                threshold=args.coverage_threshold,
                asymmetry_margin=args.coverage_asymmetry_margin,
                structural_threshold=args.structural_coverage_threshold,
            )
            for probe_row, trace in zip(probe["rows"], mode["traces"])
        ]
    selected = [
        sid for sid, rows in enumerate(decisions)
        if any(bool(row["fallback_required"]) for row in rows)
        and sid not in structural
    ]
    executor = DistinctPromptWhisper(args.model, device=args.device, max_new_tokens=96)
    if selected:
        if args.repair_mode != "witness-select":
            executor.generate(
                [sessions[selected[0]].audio[: args.window_seconds * 16_000]],
                [()],
            )
        replay_seconds = replay_audio = 0.0
        replay_calls = 0
        replay_traces = []
        for sid in selected:
            coarse_rows = [
                row for row in mode["traces"][sid]
                if not row.get("terminal_session_fallback")
            ]
            conflicts = [
                row for row in decisions[sid] if row["fallback_required"]
            ]
            if args.repair_mode == "suffix-rebase":
                conflicts = conflicts[:1]
            replacements: dict[int, str] = {}
            session_trace: list[dict[str, object]] = []
            for conflict in conflicts:
                segment_index = int(conflict["segment_index"])
                start_sample = int(round(
                    float(conflict["start_seconds"]) * 16_000
                ))
                end_sample = (
                    None if args.repair_mode == "suffix-rebase" else int(round(
                        float(conflict["end_seconds"]) * 16_000
                    ))
                )
                if args.repair_mode == "witness-select":
                    text = str(conflict["fine_text"])
                    elapsed, calls, audio, trace = 0.0, 0, 0.0, []
                else:
                    parent_prompt = tuple(
                        int(value)
                        for value in coarse_rows[segment_index]["prompt_token_ids"]
                    )
                    text, elapsed, calls, audio, trace = replay_from_checkpoint(
                        executor, sessions[sid], start_sample=start_sample,
                        end_sample=end_sample, parent_prompt=parent_prompt,
                        window_seconds=args.window_seconds,
                    )
                replacements[segment_index] = text
                replay_seconds += elapsed
                replay_calls += calls
                replay_audio += audio
                session_trace.append({
                    "segment_index": segment_index,
                    "audio_start_sample": start_sample,
                    "audio_end_sample": (
                        sessions[sid].audio.size
                        if end_sample is None else end_sample
                    ),
                    "trace": trace,
                    "source": (
                        "fine_witness" if args.repair_mode == "witness-select"
                        else "singleton_replay"
                    ),
                })
            if args.repair_mode == "suffix-rebase":
                first_index = int(conflicts[0]["segment_index"])
                outputs[sid] = " ".join(
                    value for value in (
                        " ".join(
                            str(row["text"])
                            for row in coarse_rows[:first_index] if row["text"]
                        ),
                        replacements[first_index],
                    ) if value
                )
            else:
                outputs[sid] = " ".join(
                    replacements.get(index, str(row["text"]))
                    for index, row in enumerate(coarse_rows)
                    if replacements.get(index, str(row["text"]))
                )
            replay_traces.append({
                "session_id": sid,
                "repair_mode": args.repair_mode,
                "repairs": session_trace,
            })
    else:
        replay_seconds = replay_audio = 0.0
        replay_calls = 0
        replay_traces = []
    post_rebase_decisions: list[dict[str, object]] = []
    session_escalations: list[int] = []
    escalation_traces: list[dict[str, object]] = []
    for sid in selected:
        fine_text = str(probe["rows"][sid]["fine_text"])
        decision = classify_asymmetric_omission_conflict(
            fine_text, outputs[sid],
            forward_threshold=args.post_rebase_forward_threshold,
            reverse_ceiling=args.post_rebase_reverse_ceiling,
        )
        post_rebase_decisions.append({
            "session_id": sid,
            "forward_deficit": decision.forward_deficit,
            "reverse_deficit": decision.reverse_deficit,
            "fallback_required": decision.fallback_required,
        })
        if not decision.fallback_required:
            continue
        text, elapsed, calls, audio, trace = replay_from_checkpoint(
            executor, sessions[sid], start_sample=0, parent_prompt=(),
            window_seconds=args.window_seconds,
        )
        outputs[sid] = text
        replay_seconds += elapsed
        replay_calls += calls
        replay_audio += audio
        session_escalations.append(sid)
        escalation_traces.append({
            "session_id": sid,
            "reason": "persistent_asymmetric_omission",
            "fallback_trace": trace,
        })
    degeneracy_scores = {
        sid: max(
            (
                repeated_ngram_fraction(str(row.get("text", "")))
                for row in trace if row.get("structural_conflict")
            ),
            default=0.0,
        )
        for sid, trace in enumerate(mode["traces"])
    }
    degeneracy_escalations: list[int] = []
    for sid, score in degeneracy_scores.items():
        if (
            score < args.degeneracy_repetition_threshold
            or sid in session_escalations
        ):
            continue
        text, elapsed, calls, audio, trace = replay_from_checkpoint(
            executor, sessions[sid], start_sample=0, parent_prompt=(),
            window_seconds=args.window_seconds,
        )
        outputs[sid] = text
        replay_seconds += elapsed
        replay_calls += calls
        replay_audio += audio
        session_escalations.append(sid)
        degeneracy_escalations.append(sid)
        escalation_traces.append({
            "session_id": sid,
            "reason": "structural_repetition_after_local_salvage",
            "repeated_4gram_fraction": score,
            "fallback_trace": trace,
        })
    rows, quality = evaluate_rows(
        outputs=outputs, sessions=sessions, source_rows=source["sessions"],
        bootstrap_seed=args.bootstrap_seed, bootstrap_replicates=10_000,
    )
    base_metrics = mode["metrics"]
    authority_seconds = float(base_metrics["authority_seconds"]) + replay_seconds
    authority_audio = float(base_metrics["authority_audio_seconds"]) + replay_audio
    projected_wall = max(float(probe["fine_proposer_wall_seconds"]), authority_seconds)
    baseline_seconds = float(source["metrics"]["canonical_seconds"])
    quality.update({
        "coverage_threshold": args.coverage_threshold,
        "coverage_scope": args.coverage_scope,
        "coverage_conflicts": sum(
            bool(row["fallback_required"])
            for session_rows in decisions for row in session_rows
        ),
        "coverage_fallbacks": len(selected),
        "preexisting_structural_fallbacks": len(structural),
        "fallback_session_ids": selected,
        "post_rebase_forward_threshold": (
            args.post_rebase_forward_threshold
        ),
        "post_rebase_reverse_ceiling": args.post_rebase_reverse_ceiling,
        "full_session_escalations": len(session_escalations),
        "full_session_escalation_ids": session_escalations,
        "degeneracy_repetition_threshold": (
            args.degeneracy_repetition_threshold
        ),
        "degeneracy_escalations": len(degeneracy_escalations),
        "degeneracy_escalation_ids": degeneracy_escalations,
        "maximum_structural_repetition_score": max(
            degeneracy_scores.values(), default=0.0
        ),
        "fallback_invocations": replay_calls,
        "authority_seconds": authority_seconds,
        "fine_proposer_wall_seconds": probe["fine_proposer_wall_seconds"],
        "projected_two_gpu_wall_seconds": projected_wall,
        "projected_two_gpu_wall_speedup": baseline_seconds / projected_wall,
        "authority_audio_amplification": authority_audio / (
            len(sessions) * args.duration_seconds
        ),
        "compute_gate_pass": (
            baseline_seconds / projected_wall >= 2.5
            and authority_audio / (len(sessions) * args.duration_seconds) <= 1.2
        ),
    })
    quality["gate_pass"] = quality["quality_gate_pass"] and quality["compute_gate_pass"]
    payload = {
        "schema_version": 1,
        "study": "R9 cross-granularity coverage fallback",
        "model_name": args.model_name,
        "decision": "PASS_R9_COVERAGE_GATE" if quality["gate_pass"] else "FAIL_R9_COVERAGE_GATE",
        "config": vars(args) | {
            "model": str(args.model), "manifest": str(args.manifest),
            "source_quality": str(args.source_quality),
            "coarse_result": str(args.coarse_result),
            "coverage_probe": str(args.coverage_probe), "output": str(args.output),
        },
        "metrics": quality,
        "sessions": rows,
        "coverage_decisions": [
            {
                "session_id": sid,
                "already_structurally_canonical": sid in structural,
                "segments": rows,
            }
            for sid, rows in enumerate(decisions)
        ],
        "fallback_traces": replay_traces,
        "post_rebase_decisions": post_rebase_decisions,
        "session_escalation_traces": escalation_traces,
        "claim_boundary": (
            "coverage is a reference-free scheduling witness, not a "
            "deterministic exactness certificate; selected sessions are "
            "replayed by the legal sequential singleton authority; display-"
            "segment repair preserves the separately certified feedback axis; "
            "persistent asymmetric "
            "omission escalates to full-session authority"
        ),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"decision": payload["decision"], **quality}))
    return 0 if quality["gate_pass"] else 2


if __name__ == "__main__":
    raise SystemExit(main())

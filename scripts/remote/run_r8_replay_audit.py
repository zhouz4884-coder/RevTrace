#!/usr/bin/env python3
"""Time-uniform random-sentinel audit of the R8 replay fast path."""

from __future__ import annotations

import argparse
import json
import random
from pathlib import Path
from typing import Any

import numpy as np

from revtrace.risk import AuditRiskBound
from revtrace.whisper_state import capacity_rebase_required
from run_whisper_w_quality import build_sessions
from whisper_batched_executor import DistinctPromptWhisper


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--model", type=Path, required=True)
    p.add_argument("--manifest", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--sessions", type=int, default=32)
    p.add_argument("--duration-seconds", type=int, default=90)
    p.add_argument("--window-seconds", type=int, default=10)
    p.add_argument("--concurrency", type=int, default=16)
    p.add_argument("--margin-threshold", type=float, default=0.05)
    p.add_argument("--audit-probability", type=float, default=0.04)
    p.add_argument("--target-fast-commits", type=int, default=30_000)
    p.add_argument("--minimum-sentinels", type=int, default=1_200)
    p.add_argument("--seed", type=int, default=2026082701)
    p.add_argument("--alpha", type=float, default=0.05)
    p.add_argument("--delta", type=float, default=0.005)
    p.add_argument("--max-new-tokens", type=int, default=96)
    p.add_argument("--device", default="cuda:0")
    args = p.parse_args()

    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    clean = args.sessions // 2
    sessions = (
        build_sessions(
            manifest["records"], split="test-clean", count=clean,
            duration_seconds=args.duration_seconds, seed=args.seed,
        )
        + build_sessions(
            manifest["records"], split="test-other",
            count=args.sessions - clean,
            duration_seconds=args.duration_seconds, seed=args.seed + 1,
        )
    )
    windows_per_session = args.duration_seconds // args.window_seconds
    windows = [
        list(np.array_split(session.audio, windows_per_session))
        for session in sessions
    ]
    executor = DistinctPromptWhisper(
        args.model, device=args.device, max_new_tokens=args.max_new_tokens
    )
    executor.generate([windows[0][0]], [()])
    rng = random.Random(args.seed)
    fast_commits = 0
    sentinels = 0
    caught_output_errors = 0
    caught_state_errors = 0
    capsule_lineage_violations = 0
    stale_installs = 0
    episodes = 0
    audited_rows = []
    risk = AuditRiskBound(args.audit_probability, args.alpha)
    canonical_cache: dict[tuple[int, int, tuple[int, ...]], Any] = {}
    canonical_cache_hits = 0
    canonical_cache_misses = 0
    args.output.parent.mkdir(parents=True, exist_ok=True)

    while fast_commits < args.target_fast_commits or sentinels < args.minimum_sentinels:
        prompts: list[tuple[int, ...]] = [() for _ in sessions]
        versions = [0 for _ in sessions]
        order = list(range(len(sessions)))
        rng.shuffle(order)
        for window_index in range(windows_per_session):
            # Slot/composition changes across episodes are intentional stress,
            # while each sentinel compares identical audio and prompt bytes.
            rotated = order[window_index:] + order[:window_index]
            for begin in range(0, len(rotated), args.concurrency):
                ids = rotated[begin:begin + args.concurrency]
                batch_audio = []
                batch_prompts = []
                for sid in ids:
                    prompt = prompts[sid]
                    if capacity_rebase_required(
                        len(executor.prompt_tokens(prompt)),
                        declared_next_segment_tokens=executor.max_new_tokens,
                        maximum_prompt_tokens=executor.max_prompt_tokens,
                    ):
                        prompt = ()
                        prompts[sid] = ()
                    batch_audio.append(windows[sid][window_index])
                    batch_prompts.append(prompt)
                rows = executor.generate(batch_audio, batch_prompts)
                for sid, audio, prompt, row in zip(
                    ids, batch_audio, batch_prompts, rows
                ):
                    if versions[sid] != window_index:
                        stale_installs += 1
                    terminal = window_index == windows_per_session - 1
                    eligible = (
                        not terminal
                        and row.terminated_by_eos
                        and row.generation_steps < args.max_new_tokens
                        and row.minimum_margin > args.margin_threshold
                    )
                    audit_coin = rng.random() if eligible else None
                    audited = bool(
                        eligible and audit_coin is not None
                        and audit_coin < args.audit_probability
                    )
                    canonical = None
                    if audited or not eligible:
                        cache_key = (sid, window_index, tuple(prompt))
                        if cache_key in canonical_cache:
                            canonical = canonical_cache[cache_key]
                            canonical_cache_hits += 1
                        else:
                            canonical = executor.canonical(audio, prompt)
                            canonical_cache[cache_key] = canonical
                            canonical_cache_misses += 1
                    if eligible:
                        fast_commits += 1
                        sentinels += int(audited)
                        if audited:
                            assert canonical is not None
                            output_error = tuple(row.token_ids) != tuple(
                                canonical.token_ids
                            )
                            batch_state = executor.advance_prompt(
                                prompt, row.token_ids
                            )
                            canonical_state = executor.advance_prompt(
                                prompt, canonical.token_ids
                            )
                            state_error = batch_state != canonical_state
                            caught_output_errors += int(output_error)
                            caught_state_errors += int(state_error)
                            if output_error or state_error:
                                audited_rows.append({
                                    "episode": episodes,
                                    "session_id": sid,
                                    "window_index": window_index,
                                    "minimum_margin": row.minimum_margin,
                                    "output_error": output_error,
                                    "state_error": state_error,
                                    "batch_tokens": list(row.token_ids),
                                    "canonical_tokens": list(canonical.token_ids),
                                })
                        selected = row
                    else:
                        assert canonical is not None
                        selected = canonical
                    prompts[sid] = executor.advance_prompt(
                        prompt, selected.token_ids
                    )
                    versions[sid] += 1
                    if versions[sid] != window_index + 1:
                        capsule_lineage_violations += 1
                if (
                    fast_commits >= args.target_fast_commits
                    and sentinels >= args.minimum_sentinels
                ):
                    break
            if (
                fast_commits >= args.target_fast_commits
                and sentinels >= args.minimum_sentinels
            ):
                break
        episodes += 1
        if episodes % 10 == 0:
            progress = {
                "episodes": episodes,
                "fast_commits": fast_commits,
                "random_sentinels": sentinels,
                "caught_output_errors": caught_output_errors,
                "caught_state_errors": caught_state_errors,
                "canonical_cache_hits": canonical_cache_hits,
                "canonical_cache_misses": canonical_cache_misses,
            }
            progress_path = args.output.with_suffix(".progress.json")
            temporary = progress_path.with_suffix(".tmp")
            temporary.write_text(
                json.dumps(progress, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            temporary.replace(progress_path)

    caught = max(caught_output_errors, caught_state_errors)
    final_ucb = risk.upper_risk(fast_commits, caught)
    passed = (
        fast_commits >= args.target_fast_commits
        and sentinels >= args.minimum_sentinels
        and final_ucb <= args.delta
        and capsule_lineage_violations == 0
        and stale_installs == 0
    )
    payload = {
        "schema_version": 1,
        "study": "RevTrace R8 independent replay time-uniform audit",
        "decision": "PASS_R8_6_AUDIT" if passed else "FAIL_R8_6_AUDIT",
        "config": vars(args) | {
            "model": str(args.model),
            "manifest": str(args.manifest),
            "output": str(args.output),
        },
        "metrics": {
            "episodes": episodes,
            "fast_commits": fast_commits,
            "random_sentinels": sentinels,
            "caught_output_errors": caught_output_errors,
            "caught_state_errors": caught_state_errors,
            "time_uniform_ucb": final_ucb,
            "capsule_lineage_violations": capsule_lineage_violations,
            "stale_installs": stale_installs,
            "canonical_cache_hits": canonical_cache_hits,
            "canonical_cache_misses": canonical_cache_misses,
        },
        "caught_rows": audited_rows,
        "claim_boundary": (
            "random audit coins are drawn before canonical outcomes; zero "
            "caught errors is finite statistical evidence summarized by the "
            "time-uniform upper bound, not deterministic exactness"
        ),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps({"decision": payload["decision"], **payload["metrics"]}))
    return 0 if passed else 2


if __name__ == "__main__":
    raise SystemExit(main())

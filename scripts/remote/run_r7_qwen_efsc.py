#!/usr/bin/env python3
"""Live Qwen3-ASR R7.Q0 gate for Elastic Feedback-State Coherence.

The timed path is deliberately authority-free: FP16 batched proposals may be
displayed, but only the architecture-independent EFSC controller can grant a
proposal future prompt authority.  HOLD, DECAY and RESET never invoke a
singleton model.  This runner is therefore both a semantic integration test
and a real one-GPU service measurement; it is not a deterministic numerical
certificate.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import platform
import random
import statistics
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Any

import torch


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--model-name", required=True)
    parser.add_argument("--data-manifest", type=Path, required=True)
    parser.add_argument("--known-roots", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--target-events", type=int, default=10_000)
    parser.add_argument("--duration-seconds", type=int, default=30)
    parser.add_argument("--concurrency", type=int, default=16)
    parser.add_argument("--seed", type=int, default=20260802)
    parser.add_argument("--gpu", default="0")
    parser.add_argument("--gpu-memory-utilization", type=float, default=0.82)
    parser.add_argument("--enter-margin", type=float, required=True)
    parser.add_argument("--exit-margin", type=float, required=True)
    parser.add_argument("--contract-epoch", type=int, default=7)
    parser.add_argument("--policy-version", type=int, default=1)
    parser.add_argument("--maximum-prompt-tokens", type=int, default=224)
    parser.add_argument("--power-sampling-interval-seconds", type=float, default=0.1)
    return parser.parse_args()


def percentile(values: list[float], q: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    position = (len(ordered) - 1) * q
    lower = int(position)
    upper = min(len(ordered) - 1, lower + 1)
    weight = position - lower
    return ordered[lower] * (1.0 - weight) + ordered[upper] * weight


def source_digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_known_roots(path: Path, model_name: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            if row.get("model") != model_name:
                continue
            rows.append(
                {
                    "source": row.get("source"),
                    "ticket": row.get("ticket"),
                    "job_sha256": row.get("job_sha256"),
                    "minimum_margin": float(row["minimum_margin"]),
                    "state_error": row.get("state_error", "").lower() == "true",
                }
            )
    if not rows:
        raise ValueError(f"no known mismatch roots found for {model_name}")
    return rows


def main() -> int:
    args = parse_args()
    if args.target_events < args.concurrency:
        raise ValueError("target-events must be at least one full batch")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    os.environ["CUDA_VISIBLE_DEVICES"] = args.gpu

    script_dir = str(Path(__file__).resolve().parent)
    project_root = str(Path(__file__).resolve().parents[2])
    for entry in (script_dir, str(Path(project_root) / "src")):
        if entry not in sys.path:
            sys.path.insert(0, entry)

    from qwen_asr import parse_asr_output
    from run_revbatch_gate import (
        SAMPLE_RATE,
        load_sources,
        make_streams,
        official_smoke,
        prepare_job,
    )
    from run_revguard_same_input import candidate_record, state_projection_record
    from run_revtrace_dual_gpu import build_asr
    from revtrace.feedback_coherence import (
        EFSCContract,
        ElasticFeedbackController,
        ElasticFeedbackState,
        FeedbackAction,
        FeedbackCandidate,
        FeedbackIdentity,
        QwenRollbackAdapter,
    )
    from revtrace.phase5 import NvidiaPowerSampler, summarize_energy

    contract = EFSCContract(
        enter_margin=args.enter_margin,
        exit_margin=args.exit_margin,
        minimum_hold_windows=1,
        safe_streak_required=2,
        maximum_quarantine_windows=3,
        maximum_feedback_debt=3,
        maximum_influence_windows=3,
        maximum_prompt_tokens=args.maximum_prompt_tokens,
        decay_suffix_tokens=min(32, args.maximum_prompt_tokens - 1),
    )
    controller = ElasticFeedbackController(contract)
    adapter = QwenRollbackAdapter()
    known_roots = load_known_roots(args.known_roots, args.model_name)

    asr = build_asr(
        str(args.model),
        "float16",
        args.gpu_memory_utilization,
        logprobs=20,
    )
    sources = load_sources(args.data_manifest)
    smoke = official_smoke(asr, sources["English"][0])
    if not smoke["exact"]:
        raise AssertionError("proposer official-semantics smoke failed")

    chunk_samples = 2 * SAMPLE_RATE
    action_counts: Counter[str] = Counter()
    preparation_counts: Counter[str] = Counter()
    reason_counts: Counter[str] = Counter()
    mode_counts: Counter[str] = Counter()
    total_events = 0
    episodes = 0
    provisional_ancestor_violations = 0
    ancestry_nonexpansion_violations = 0
    stale_identity_violations = 0
    debt_violations = 0
    influence_violations = 0
    prompt_load_violations = 0
    acoustic_rebase_violations = 0
    acoustic_rebases = 0
    maximum_ancestry_age = 0
    maximum_feedback_debt = 0
    maximum_prompt_load = 0
    batch_seconds: list[float] = []
    event_latencies: list[float] = []
    episode_rows: list[dict[str, Any]] = []
    event_samples: list[dict[str, Any]] = []
    final_text_sha256: list[str] = []

    power = NvidiaPowerSampler(
        [int(args.gpu)], interval_seconds=args.power_sampling_interval_seconds
    )
    power.start()
    service_started = time.perf_counter()

    while total_events < args.target_events:
        episode_seed = args.seed + episodes
        rng = random.Random(episode_seed)
        streams = make_streams(sources, args.duration_seconds, args.concurrency)
        rng.shuffle(streams)
        for position, stream in enumerate(streams):
            stream["session_id"] = f"e{episodes:04d}-s{position:03d}"
        states = [
            asr.init_streaming_state(
                language=stream["language"],
                unfixed_chunk_num=2,
                unfixed_token_num=5,
                chunk_size_sec=2.0,
            )
            for stream in streams
        ]
        feedback_states = [
            ElasticFeedbackState(
                FeedbackIdentity(
                    stream["session_id"],
                    args.contract_epoch,
                    args.policy_version,
                    0,
                )
            )
            for stream in streams
        ]
        full_chunks = min(
            stream["audio"].shape[0] // chunk_samples for stream in streams
        )
        episode_started = time.perf_counter()
        episode_event_start = total_events
        episode_latencies: list[float] = []

        for chunk_index in range(full_chunks):
            terminal = chunk_index == full_chunks - 1
            jobs: list[dict[str, Any]] = []
            prefixes: list[str] = []
            round_started = time.perf_counter()

            for position, (stream, state) in enumerate(zip(streams, states)):
                current = feedback_states[position]
                prepared, preparation = controller.prepare_for_proposal(
                    current, adapter
                )
                if preparation.action is not None:
                    preparation_counts[preparation.action.value] += 1
                    state._raw_decoded = asr.processor.tokenizer.decode(
                        [atom.token_id for atom in prepared.atoms]
                    )
                    # Qwen's effective feedback state couples the rollback
                    # text to cumulative audio.  A text-only reset would make
                    # the next revision retranscribe the entire old waveform
                    # from an empty/stale prefix.  Rebase the replay frontier
                    # at the same lattice transition; the incoming 2 s chunk
                    # is appended by prepare_job immediately below.
                    state.audio_accum = state.audio_accum[:0].copy()
                    acoustic_rebases += 1
                feedback_states[position] = prepared
                begin = chunk_index * chunk_samples
                end = begin + chunk_samples
                job, prefix = prepare_job(
                    asr,
                    state,
                    stream["audio"][begin:end],
                    # All streams contain exact 2 s chunks.  Match the frozen
                    # c16 service path; ``tail=True`` is reserved for a real
                    # sub-chunk remainder and changes rollback semantics.
                    tail=False,
                )
                jobs.append(job)
                prefixes.append(prefix)

            proposal_started = time.perf_counter()
            outputs = asr.model.generate(
                jobs,
                sampling_params=asr.sampling_params,
                use_tqdm=False,
            )
            elapsed = time.perf_counter() - proposal_started
            batch_seconds.append(elapsed)
            round_latency = time.perf_counter() - round_started

            for position, (stream, state, prefix, output) in enumerate(
                zip(streams, states, prefixes, outputs)
            ):
                record = candidate_record(output)
                projection = state_projection_record(
                    asr,
                    state,
                    prefix,
                    record,
                    terminal=terminal,
                )
                current = feedback_states[position]
                old_ancestors = current.ancestors
                candidate = FeedbackCandidate(
                    session_id=stream["session_id"],
                    contract_epoch=args.contract_epoch,
                    policy_version=args.policy_version,
                    parent_state_version=current.identity.state_version,
                    token_ids=tuple(projection["projection_token_ids"]),
                    minimum_margin=record["minimum_margin"],
                    terminal=terminal,
                )
                try:
                    next_feedback, decision = controller.step(
                        current, candidate, adapter
                    )
                except Exception:
                    stale_identity_violations += 1
                    raise

                action_counts[decision.action.value] += 1
                reason_counts[decision.reason] += 1
                mode_counts[next_feedback.mode.value] += 1
                if (
                    decision.action != FeedbackAction.FAST_COMMIT
                    and next_feedback.ancestors - old_ancestors
                ):
                    ancestry_nonexpansion_violations += 1
                if (
                    not decision.candidate_became_ancestor
                    and next_feedback.identity.state_version
                    in next_feedback.ancestors
                ):
                    provisional_ancestor_violations += 1
                if next_feedback.feedback_debt > contract.maximum_feedback_debt:
                    debt_violations += 1
                if next_feedback.oldest_ancestor_age > contract.maximum_influence_windows:
                    influence_violations += 1
                if next_feedback.prompt_load > contract.maximum_prompt_tokens:
                    prompt_load_violations += 1

                maximum_ancestry_age = max(
                    maximum_ancestry_age, next_feedback.oldest_ancestor_age
                )
                maximum_feedback_debt = max(
                    maximum_feedback_debt, next_feedback.feedback_debt
                )
                maximum_prompt_load = max(
                    maximum_prompt_load, next_feedback.prompt_load
                )

                # Display and feedback authority are intentionally decoupled.
                display_raw = prefix + record["text"]
                language, display_text = parse_asr_output(
                    display_raw, user_language=state.force_language
                )
                state.language = language
                state.text = display_text
                state._raw_decoded = asr.processor.tokenizer.decode(
                    [atom.token_id for atom in next_feedback.atoms]
                )
                if (
                    not terminal
                    and decision.action != FeedbackAction.FAST_COMMIT
                ):
                    # HOLD/DECAY/RESET deny this output feedback authority.
                    # Advancing the acoustic replay frontier prevents the
                    # denied segment from being regenerated as if it were
                    # still awaiting a text-state write.
                    state.audio_accum = state.audio_accum[:0].copy()
                    acoustic_rebases += 1
                    if state.audio_accum.size:
                        acoustic_rebase_violations += 1
                state.chunk_id += 1
                feedback_states[position] = next_feedback

                total_events += 1
                event_latencies.append(round_latency)
                episode_latencies.append(round_latency)
                if len(event_samples) < 512 or total_events % 1000 == 0:
                    event_samples.append(
                        {
                            "event_index": total_events,
                            "episode": episodes,
                            "session_id": stream["session_id"],
                            "chunk_index": chunk_index,
                            "terminal": terminal,
                            "minimum_margin": record["minimum_margin"],
                            "action": decision.action.value,
                            "reason": decision.reason,
                            "mode": next_feedback.mode.value,
                            "feedback_debt": next_feedback.feedback_debt,
                            "prompt_load": next_feedback.prompt_load,
                            "oldest_ancestor_age": next_feedback.oldest_ancestor_age,
                            "display_token_count": len(record["token_ids"]),
                            "feedback_token_count": next_feedback.prompt_load,
                            "latency_seconds": round_latency,
                        }
                    )
                if terminal:
                    final_text_sha256.append(
                        hashlib.sha256(display_text.encode("utf-8")).hexdigest()
                    )

        episode_wall = time.perf_counter() - episode_started
        episode_events = total_events - episode_event_start
        episode_rows.append(
            {
                "episode": episodes,
                "seed": episode_seed,
                "events": episode_events,
                "wall_seconds": episode_wall,
                "goodput_events_per_second": episode_events / episode_wall,
                "latency_p50_seconds": percentile(episode_latencies, 0.50),
                "latency_p95_seconds": percentile(episode_latencies, 0.95),
                "latency_p99_seconds": percentile(episode_latencies, 0.99),
            }
        )
        episodes += 1
        print(
            json.dumps(
                {
                    "model": args.model_name,
                    "episodes": episodes,
                    "events": total_events,
                    "actions": dict(action_counts),
                    "last_wall_seconds": episode_wall,
                },
                sort_keys=True,
            ),
            flush=True,
        )

    service_wall = time.perf_counter() - service_started
    power_samples = power.stop()
    completed_audio_seconds = total_events * 2.0
    energy = summarize_energy(
        power_samples,
        completed_audio_seconds=completed_audio_seconds,
    )

    # Known historical numerical roots are replayed through the frozen shared
    # policy as stress decisions.  This is controller coverage, not a new GPU
    # reproduction of the old jobs (the source artifacts retain those hashes).
    root_stress: list[dict[str, Any]] = []
    for index, root in enumerate(known_roots):
        root_state = ElasticFeedbackState(
            FeedbackIdentity(
                f"known-root-{index}",
                args.contract_epoch,
                args.policy_version,
                0,
            )
        )
        root_candidate = FeedbackCandidate(
            session_id=root_state.identity.session_id,
            contract_epoch=args.contract_epoch,
            policy_version=args.policy_version,
            parent_state_version=0,
            token_ids=(1,),
            minimum_margin=root["minimum_margin"],
            terminal=False,
        )
        _, root_decision = controller.step(root_state, root_candidate, adapter)
        root_stress.append({**root, "action": root_decision.action.value})

    required_actions = {
        FeedbackAction.FAST_COMMIT.value,
        FeedbackAction.PROVISIONAL_HOLD.value,
        FeedbackAction.SAFE_RESET.value,
    }
    observed_actions = set(action_counts) | set(preparation_counts)
    violations = {
        "provisional_ancestor": provisional_ancestor_violations,
        "ancestry_nonexpansion": ancestry_nonexpansion_violations,
        "stale_identity": stale_identity_violations,
        "feedback_debt": debt_violations,
        "influence_horizon": influence_violations,
        "prompt_load": prompt_load_violations,
        "acoustic_rebase": acoustic_rebase_violations,
    }
    passed = (
        total_events >= args.target_events
        and required_actions.issubset(observed_actions)
        and all(value == 0 for value in violations.values())
        and maximum_ancestry_age <= contract.maximum_influence_windows
        and all(row["action"] != FeedbackAction.FAST_COMMIT.value for row in root_stress)
    )

    payload = {
        "schema_version": 1,
        "study": "RevTrace R7.Q0 live Qwen EFSC gate",
        "decision": "PASS_R7_Q0_LIVE_MODEL" if passed else "FAIL_R7_Q0_LIVE_MODEL",
        "claim_boundary": {
            "evidence": "real FP16 batched Qwen3-ASR execution with live EFSC prompt-state updates",
            "not_evidence": "deterministic numerical certification or a formal risk certificate",
            "known_root_replay": "controller stress replay bound to prior GPU root hashes; not fresh same-input reproduction",
        },
        "model": args.model_name,
        "config": {
            "model_path": str(args.model),
            "data_manifest": str(args.data_manifest),
            "target_events": args.target_events,
            "duration_seconds": args.duration_seconds,
            "concurrency": args.concurrency,
            "seed": args.seed,
            "dtype": "float16",
            "device": args.gpu,
            "contract_epoch": args.contract_epoch,
            "policy_version": args.policy_version,
            "contract": contract.__dict__,
        },
        "counts": {
            "events": total_events,
            "episodes": episodes,
            "sessions": episodes * args.concurrency,
            "actions": dict(action_counts),
            "pre_proposal_actions": dict(preparation_counts),
            "reasons": dict(reason_counts),
            "modes": dict(mode_counts),
        },
        "semantic_contract": {
            "violations": violations,
            "maximum_ancestry_age": maximum_ancestry_age,
            "maximum_feedback_debt": maximum_feedback_debt,
            "maximum_prompt_load": maximum_prompt_load,
            "acoustic_rebases": acoustic_rebases,
            "required_actions": sorted(required_actions),
            "observed_actions": sorted(observed_actions),
        },
        "known_root_stress": root_stress,
        "performance": {
            "service_wall_seconds": service_wall,
            "events_per_second": total_events / service_wall,
            "latency_p50_seconds": percentile(event_latencies, 0.50),
            "latency_p95_seconds": percentile(event_latencies, 0.95),
            "latency_p99_seconds": percentile(event_latencies, 0.99),
            "batch_seconds_p50": percentile(batch_seconds, 0.50),
            "batch_seconds_p99": percentile(batch_seconds, 0.99),
            "energy": energy,
            "first_five_episodes": episode_rows[:5],
            "episode_median_wall_seconds_first_five": statistics.median(
                row["wall_seconds"] for row in episode_rows[:5]
            ),
            "episode_median_p99_seconds_first_five": statistics.median(
                row["latency_p99_seconds"] for row in episode_rows[:5]
            ),
        },
        "display": {
            "terminal_sessions": len(final_text_sha256),
            "terminal_text_sha256_sample": final_text_sha256[:32],
        },
        "event_samples": event_samples,
        "environment": {
            "python": platform.python_version(),
            "code_commit": os.environ.get("REVTRACE_CODE_COMMIT", "UNRECORDED"),
            "runner_sha256": source_digest(Path(__file__)),
            "controller_sha256": source_digest(
                Path(project_root) / "src" / "revtrace" / "feedback_coherence.py"
            ),
            "platform": platform.platform(),
        },
    }
    args.output.write_text(
        json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8"
    )
    print(json.dumps({"decision": payload["decision"], "output": str(args.output)}))
    if torch.distributed.is_available() and torch.distributed.is_initialized():
        torch.distributed.destroy_process_group()
    return 0 if passed else 2


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""R7.4 epoch-fenced random-sentinel risk audit for Whisper EFSC.

The audit samples only EFSC FAST_COMMIT state entries.  Canonical outcomes are
computed on an independent GPU after the pre-outcome random draw and never
replace or otherwise mutate the live feedback state.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import time
from pathlib import Path
from typing import Any

import numpy as np

from revtrace.feedback_coherence import (
    EFSCContract,
    ElasticFeedbackController,
    ElasticFeedbackState,
    EpochFencedBackgroundProfiler,
    FeedbackAction,
    FeedbackCandidate,
    FeedbackIdentity,
    ProfilerChannel,
    WhisperHistoryAdapter,
)
from revtrace.risk import AuditRiskBound
from run_whisper_w_system import build_sessions
from whisper_batched_executor import DistinctPromptWhisper


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--model-name", required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--policy", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--sessions", type=int, default=32)
    parser.add_argument("--duration-seconds", type=int, default=90)
    parser.add_argument("--window-seconds", type=int, default=10)
    parser.add_argument("--concurrency", type=int, default=16)
    parser.add_argument("--target-eligible", type=int, default=60_000)
    parser.add_argument("--minimum-audits", type=int, default=1_200)
    parser.add_argument("--sentinel-probability", type=float, default=0.021)
    parser.add_argument("--alpha", type=float, default=0.05)
    parser.add_argument("--delta", type=float, default=0.005)
    parser.add_argument("--seed", type=int, default=2026080801)
    parser.add_argument("--max-new-tokens", type=int, default=96)
    parser.add_argument("--proposer-device", default="cuda:0")
    parser.add_argument("--verifier-device", default="cuda:1")
    return parser.parse_args()


def contract_from_policy(
    policy: dict[str, Any], maximum_prompt_tokens: int
) -> EFSCContract:
    return EFSCContract(
        enter_margin=float(policy["enter_margin"]),
        exit_margin=float(policy["exit_margin"]),
        minimum_hold_windows=int(policy["minimum_hold_windows"]),
        safe_streak_required=int(policy["safe_streak_required"]),
        maximum_quarantine_windows=int(policy["maximum_quarantine_windows"]),
        maximum_feedback_debt=int(policy["maximum_feedback_debt"]),
        maximum_influence_windows=int(policy["maximum_influence_windows"]),
        maximum_prompt_tokens=maximum_prompt_tokens,
        decay_suffix_tokens=min(32, maximum_prompt_tokens - 1),
    )


def main() -> int:
    args = parse_args()
    if args.duration_seconds % args.window_seconds:
        raise ValueError("duration must be divisible by window size")
    policy_payload = json.loads(args.policy.read_text(encoding="utf-8"))
    selected = policy_payload["selected_policy"]
    sessions = build_sessions(
        args.manifest,
        duration_seconds=args.duration_seconds,
        count=args.sessions,
        seed=args.seed,
    )
    proposer = DistinctPromptWhisper(
        args.model,
        device=args.proposer_device,
        max_new_tokens=args.max_new_tokens,
    )
    verifier = DistinctPromptWhisper(
        args.model,
        device=args.verifier_device,
        max_new_tokens=args.max_new_tokens,
    )
    maximum_prompt_tokens = proposer.max_prompt_tokens - 1
    contract = contract_from_policy(selected, maximum_prompt_tokens)
    adapter = WhisperHistoryAdapter(maximum_prompt_tokens)
    controller = ElasticFeedbackController(contract)
    profiler = EpochFencedBackgroundProfiler(
        epoch=1,
        sentinel_probability=args.sentinel_probability,
        seed=args.seed + 17,
    )
    windows_per_session = args.duration_seconds // args.window_seconds
    split = [list(np.array_split(row, windows_per_session)) for row in sessions]
    total_events = 0
    episode = 0
    semantic_violations = 0
    maximum_age = 0
    maximum_debt = 0
    audit_rows: list[dict[str, Any]] = []
    action_counts = {action.value: 0 for action in FeedbackAction}
    started = time.perf_counter()

    def complete() -> bool:
        evidence = profiler.evidence
        return (
            evidence.eligible_fast_commits >= args.target_eligible
            and evidence.sentinel_audits >= args.minimum_audits
        )

    while not complete():
        states = [
            ElasticFeedbackState(
                FeedbackIdentity(f"episode-{episode}-session-{i}", 1, 1, 0)
            )
            for i in range(len(sessions))
        ]
        prompts: list[tuple[int, ...]] = [() for _ in sessions]
        for window_index in range(windows_per_session):
            for begin in range(0, len(sessions), args.concurrency):
                ids = list(range(begin, min(begin + args.concurrency, len(sessions))))
                for session_id in ids:
                    state, _ = controller.prepare_for_proposal(
                        states[session_id], adapter
                    )
                    states[session_id] = state
                    prompts[session_id] = tuple(atom.token_id for atom in state.atoms)
                audio = [split[index][window_index] for index in ids]
                prompt_rows = [prompts[index] for index in ids]
                proposed = proposer.generate(audio, prompt_rows)
                for position, session_id in enumerate(ids):
                    current = states[session_id]
                    record = proposed[position]
                    terminal = window_index == windows_per_session - 1
                    candidate = FeedbackCandidate(
                        session_id=current.identity.session_id,
                        contract_epoch=current.identity.contract_epoch,
                        policy_version=current.identity.policy_version,
                        parent_state_version=current.identity.state_version,
                        token_ids=tuple(record.token_ids),
                        minimum_margin=record.minimum_margin,
                        terminal=terminal,
                    )
                    next_state, transition = controller.step(
                        current, candidate, adapter
                    )
                    action_counts[transition.action.value] += 1
                    decision = profiler.decide(
                        transition.action,
                        diagnostics_enabled=False,
                    )
                    state_error = False
                    canonical_sha = None
                    if decision.channel == ProfilerChannel.RANDOM_SENTINEL:
                        canonical = verifier.canonical(
                            audio[position], prompt_rows[position]
                        )
                        canonical_prompt = verifier.advance_prompt(
                            prompt_rows[position], canonical.token_ids
                        )
                        # EFSC atoms contain raw history tokens.  The executor
                        # materializes <|startofprev|> only at the decoder
                        # boundary, so remove that transport marker before
                        # comparing the semantic feedback state.
                        canonical_history = (
                            canonical_prompt[1:]
                            if canonical_prompt
                            and canonical_prompt[0] == verifier.start_of_previous
                            else canonical_prompt
                        )
                        proposed_prompt = tuple(
                            atom.token_id for atom in next_state.atoms
                        )
                        state_error = proposed_prompt != canonical_history
                        canonical_sha = canonical.token_sha256
                        profiler.observe(decision, state_error=state_error)
                        audit_rows.append({
                            "episode": episode,
                            "session_id": session_id,
                            "window_index": window_index,
                            "margin": record.minimum_margin,
                            "state_error": state_error,
                            "proposal_sha256": record.token_sha256,
                            "canonical_sha256": canonical_sha,
                            "prompt_sha256": hashlib.sha256(
                                json.dumps(list(prompt_rows[position]), separators=(",", ":"))
                                .encode("utf-8")
                            ).hexdigest(),
                        })
                    states[session_id] = next_state
                    prompts[session_id] = tuple(
                        atom.token_id for atom in next_state.atoms
                    )
                    if next_state.feedback_debt > contract.maximum_feedback_debt:
                        semantic_violations += 1
                    if next_state.oldest_ancestor_age > contract.maximum_influence_windows:
                        semantic_violations += 1
                    maximum_age = max(maximum_age, next_state.oldest_ancestor_age)
                    maximum_debt = max(maximum_debt, next_state.feedback_debt)
                    total_events += 1
            if complete():
                break
        episode += 1
        checkpoint = args.output.with_suffix(".checkpoint.json")
        checkpoint.parent.mkdir(parents=True, exist_ok=True)
        checkpoint.write_text(json.dumps({
            "episode": episode,
            "total_events": total_events,
            "eligible": profiler.evidence.eligible_fast_commits,
            "audits": profiler.evidence.sentinel_audits,
            "caught": profiler.evidence.caught_state_errors,
            "elapsed_seconds": time.perf_counter() - started,
        }, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(checkpoint.read_text(encoding="utf-8").strip(), flush=True)

    evidence = profiler.evidence
    bound = AuditRiskBound(args.sentinel_probability, args.alpha)
    upper_count = bound.upper_error_count(
        evidence.eligible_fast_commits,
        evidence.caught_state_errors,
    )
    upper_risk = upper_count / evidence.eligible_fast_commits
    passed = (
        evidence.eligible_fast_commits >= args.target_eligible
        and evidence.sentinel_audits >= args.minimum_audits
        and upper_risk <= args.delta
        and semantic_violations == 0
    )
    payload = {
        "schema_version": 1,
        "study": "RevTrace R7.4 epoch-fenced Whisper EFSC sentinel audit",
        "decision": "PASS_R7_4_RISK" if passed else "FAIL_R7_4_RISK",
        "model": args.model_name,
        "config": {
            **vars(args),
            "model": str(args.model.resolve()),
            "manifest": str(args.manifest.resolve()),
            "policy": str(args.policy.resolve()),
            "policy_sha256": hashlib.sha256(args.policy.read_bytes()).hexdigest(),
            "contract": contract.__dict__,
            "audit_epoch": profiler.epoch,
            "audit_interference": "shadow-canonical-no-live-state-mutation",
        },
        "counts": {
            "episodes": episode,
            "total_events": total_events,
            "eligible_fast_commits": evidence.eligible_fast_commits,
            "random_sentinel_audits": evidence.sentinel_audits,
            "caught_state_errors": evidence.caught_state_errors,
            "semantic_violations": semantic_violations,
            "actions": action_counts,
            "maximum_prompt_state_age": maximum_age,
            "maximum_feedback_debt": maximum_debt,
        },
        "risk_certificate": {
            "upper_error_count": upper_count,
            "upper_risk": upper_risk,
            "confidence": 1.0 - args.alpha,
            "target_delta": args.delta,
            "method": "fixed-probability mixture e-process inversion",
        },
        "audit_rows": audit_rows,
        "wall_seconds": time.perf_counter() - started,
        "claim_boundaries": [
            "eligible entries are correlated execution events, not utterances",
            "sentinel coins are drawn before canonical outcomes",
            "shadow audits never mutate the live EFSC state",
            "the certificate is model- and policy-epoch-specific",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "decision": payload["decision"],
        **payload["counts"],
        **payload["risk_certificate"],
    }, sort_keys=True))
    return 0 if passed else 2


if __name__ == "__main__":
    raise SystemExit(main())

"""Deterministic state-machine fuzzing for DGFT commit validation.

This is a protocol test, not a GPU serving benchmark.  It mutates one binding
field at a time around otherwise-valid commits and checks that rejected
transactions leave the committed state unchanged.  Accepted commits must
advance exactly one checkpoint and one contiguous audio frontier.
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from collections import Counter
from dataclasses import asdict, replace
from hashlib import sha256
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from revtrace.dgft import (  # noqa: E402
    CanonicalSegmentJob,
    FeedbackTransactionState,
    build_dual_axis_certificate,
    commit_canonical_segment,
    digest_bytes,
    digest_tokens,
)


MUTATIONS = (
    "valid",
    "cross-session",
    "stale-epoch",
    "stale-policy",
    "contract-digest",
    "runtime-digest",
    "stale-parent",
    "audio-gap",
    "audio-overlap",
    "empty-segment",
    "missing-audio-digest",
    "prompt-digest",
    "duplicate-segment",
    "certificate-session",
    "certificate-contract",
    "certificate-policy",
    "certificate-segment",
    "certificate-parent",
    "certificate-frontier",
    "certificate-prompt",
    "certificate-audio",
    "certificate-display",
    "certificate-feedback-state",
    "certificate-runtime",
    "replay-consumed-transition",
)


def initial_state(session_id: int) -> FeedbackTransactionState:
    return FeedbackTransactionState(
        session_id=session_id,
        contract_epoch=7,
        policy_version="paper-fuzz-v1",
        contract_digest="contract-v1",
        canonical_runtime_digest="runtime-v1",
    )


def make_valid(state: FeedbackTransactionState, serial: int):
    width = 1 + serial % 5
    audio = f"audio:{state.session_id}:{serial}".encode("ascii")
    display = (serial % 997 + 1, (serial * 7) % 991 + 1)
    feedback = (*state.prompt_tokens, *display)
    segment_id = f"{state.session_id}:{state.checkpoint_id}:{serial}"
    job = CanonicalSegmentJob(
        session_id=state.session_id,
        contract_epoch=state.contract_epoch,
        policy_version=state.policy_version,
        parent_checkpoint_id=state.checkpoint_id,
        audio_start_window=state.audio_frontier_window,
        audio_end_window=state.audio_frontier_window + width,
        segment_id=segment_id,
        prompt_digest=digest_tokens(state.prompt_tokens),
        contract_digest=state.contract_digest,
        canonical_runtime_digest=state.canonical_runtime_digest,
        audio_sha256=digest_bytes(audio),
    )
    certificate = build_dual_axis_certificate(
        job=job,
        audio=audio,
        display_tokens=display,
        feedback_state_tokens=feedback,
        canonical_runtime_digest=state.canonical_runtime_digest,
    )
    return job, certificate, display, feedback


def mutate(kind, state, job, certificate, display, feedback, previous):
    if kind == "valid":
        return job, certificate, display, feedback
    if kind == "replay-consumed-transition":
        return previous
    if kind == "cross-session":
        job = replace(job, session_id=state.session_id + 10_000)
    elif kind == "stale-epoch":
        job = replace(job, contract_epoch=state.contract_epoch - 1)
    elif kind == "stale-policy":
        job = replace(job, policy_version="stale-policy")
    elif kind == "contract-digest":
        job = replace(job, contract_digest="wrong-contract")
    elif kind == "runtime-digest":
        job = replace(job, canonical_runtime_digest="wrong-runtime")
    elif kind == "stale-parent":
        job = replace(job, parent_checkpoint_id=max(0, state.checkpoint_id - 1))
        if state.checkpoint_id == 0:
            job = replace(job, parent_checkpoint_id=1)
    elif kind == "audio-gap":
        job = replace(job, audio_start_window=state.audio_frontier_window + 1)
    elif kind == "audio-overlap":
        job = replace(job, audio_start_window=max(0, state.audio_frontier_window - 1))
        if state.audio_frontier_window == 0:
            job = replace(job, audio_start_window=1)
    elif kind == "empty-segment":
        job = replace(job, audio_end_window=job.audio_start_window)
    elif kind == "missing-audio-digest":
        job = replace(job, audio_sha256="")
    elif kind == "prompt-digest":
        job = replace(job, prompt_digest="bad")
    elif kind == "duplicate-segment":
        if state.committed_segment_ids:
            job = replace(job, segment_id=state.committed_segment_ids[-1])
        else:
            job = replace(job, prompt_digest="bad")
    elif kind == "certificate-session":
        certificate = replace(certificate, session_id=state.session_id + 1)
    elif kind == "certificate-contract":
        certificate = replace(certificate, contract_digest="wrong-contract")
    elif kind == "certificate-policy":
        certificate = replace(certificate, policy_version="wrong-policy")
    elif kind == "certificate-segment":
        certificate = replace(certificate, segment_id="wrong-segment")
    elif kind == "certificate-parent":
        certificate = replace(certificate, parent_checkpoint_id=state.checkpoint_id + 1)
    elif kind == "certificate-frontier":
        certificate = replace(certificate, audio_end_window=job.audio_end_window + 1)
    elif kind == "certificate-prompt":
        certificate = replace(certificate, prompt_sha256="0" * 64)
    elif kind == "certificate-audio":
        certificate = replace(certificate, audio_sha256="1" * 64)
    elif kind == "certificate-display":
        certificate = replace(certificate, display_sha256="2" * 64)
    elif kind == "certificate-feedback-state":
        certificate = replace(certificate, feedback_state_sha256="3" * 64)
    elif kind == "certificate-runtime":
        certificate = replace(certificate, canonical_runtime_sha256="wrong-runtime")
    else:
        raise AssertionError(kind)
    return job, certificate, display, feedback


def run(*, attempts: int, sessions: int, seed: int) -> dict:
    rng = random.Random(seed)
    states = {sid: initial_state(sid) for sid in range(sessions)}
    previous = {sid: None for sid in range(sessions)}
    attempts_by_kind = Counter()
    rejection_reasons = Counter()
    accepted = rejected = invariant_violations = invalid_accepts = 0

    # Cycle through every mutation before randomizing to guarantee coverage.
    schedule = list(MUTATIONS)
    rng.shuffle(schedule)
    for serial in range(attempts):
        sid = rng.randrange(sessions)
        state = states[sid]
        job, certificate, display, feedback = make_valid(state, serial)
        kind = schedule[serial % len(schedule)]
        if serial and serial % len(schedule) == 0:
            rng.shuffle(schedule)
        candidate = mutate(
            kind, state, job, certificate, display, feedback, previous[sid]
        )
        # A replay needs one previously accepted transition.  Until then, use
        # a deterministic stale-parent mutation so the attempt remains invalid.
        if candidate is None:
            candidate = mutate(
                "stale-parent", state, job, certificate, display, feedback, None
            )
        c_job, c_cert, c_display, c_feedback = candidate
        result = commit_canonical_segment(
            state,
            c_job,
            certificate=c_cert,
            display_tokens=c_display,
            segment_tokens=c_display,
            next_prompt_tokens=c_feedback,
            descendant_versions=(state.speculative_version + 1,),
        )
        attempts_by_kind[kind] += 1
        should_accept = kind == "valid"
        if result.accepted:
            accepted += 1
            if not should_accept:
                invalid_accepts += 1
            nxt = result.state
            if not (
                nxt.checkpoint_id == state.checkpoint_id + 1
                and nxt.audio_frontier_window == c_job.audio_end_window
                and nxt.audio_frontier_window > state.audio_frontier_window
                and nxt.checkpoint_audio_frontiers[-1] == nxt.audio_frontier_window
                and all(
                    left < right
                    for left, right in zip(
                        nxt.checkpoint_audio_frontiers,
                        nxt.checkpoint_audio_frontiers[1:],
                    )
                )
                and len(nxt.committed_segment_ids)
                == len(set(nxt.committed_segment_ids))
                and nxt.prompt_tokens == tuple(c_feedback)
            ):
                invariant_violations += 1
            states[sid] = nxt
            previous[sid] = (c_job, c_cert, c_display, c_feedback)
        else:
            rejected += 1
            rejection_reasons[result.reason] += 1
            if should_accept or result.state != state:
                invariant_violations += 1

    payload = {
        "schema_version": 1,
        "study": "DGFT deterministic transaction state-machine fuzz",
        "evidence_tier": (
            "CPU protocol-state fuzz; not a GPU serving, numerical, or "
            "population failure-rate result"
        ),
        "seed": seed,
        "sessions": sessions,
        "attempts": attempts,
        "accepted_valid_commits": accepted,
        "rejected_mutated_or_replayed_commits": rejected,
        "invalid_accepts": invalid_accepts,
        "invariant_violations": invariant_violations,
        "attempts_by_kind": dict(sorted(attempts_by_kind.items())),
        "rejection_reasons": dict(sorted(rejection_reasons.items())),
        "final_committed_checkpoints": sum(s.checkpoint_id for s in states.values()),
        "decision": "PASS" if invalid_accepts == invariant_violations == 0 else "FAIL",
        "boundaries": [
            "The fuzzer covers certificate tampering, cross-session/epoch/policy, stale parent, gap/overlap, duplicate/replay, and atomic state invariants.",
            "It does not simulate Byzantine trusted components, wall-clock certificate expiry, GPU worker crashes, or floating-point execution.",
        ],
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    payload["payload_sha256"] = sha256(canonical.encode("utf-8")).hexdigest()
    return payload


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--attempts", type=int, default=250_000)
    parser.add_argument("--sessions", type=int, default=64)
    parser.add_argument("--seed", type=int, default=20260805)
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "results" / "paper_review_closure" / "transaction_fuzz.json",
    )
    args = parser.parse_args()
    payload = run(attempts=args.attempts, sessions=args.sessions, seed=args.seed)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2))
    if payload["decision"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()

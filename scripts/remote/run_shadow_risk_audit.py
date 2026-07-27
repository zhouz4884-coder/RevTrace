#!/usr/bin/env python3
"""Randomized shadow audit for RevTrace state-entry risk.

This is an evidence run, not a latency benchmark.  It executes the deployed
FP16 proposer policy, routes low-margin and terminal transitions through the
canonical singleton path, and independently shadows a fixed-probability coin
sample of otherwise-fast state entries.  Only the fixed base-audit coin enters
the anytime-valid risk calculation.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import multiprocessing as mp
import os
import platform
import queue
import random
import statistics
import sys
import time
from pathlib import Path
from types import SimpleNamespace
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--model-name", required=True)
    parser.add_argument("--data-manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--target-risk-entries", type=int, default=30_000)
    parser.add_argument("--duration-seconds", type=int, default=30)
    parser.add_argument("--concurrency", type=int, default=64)
    parser.add_argument("--margin-threshold", type=float, default=0.05)
    parser.add_argument("--audit-probability", type=float, default=0.021)
    parser.add_argument("--alpha", type=float, default=0.05)
    parser.add_argument("--delta", type=float, default=0.005)
    parser.add_argument("--seed", type=int, default=20260727)
    parser.add_argument("--proposer-gpu", default="0")
    parser.add_argument("--verifier-gpu", default="1")
    parser.add_argument("--gpu-memory-utilization", type=float, default=0.82)
    parser.add_argument("--result-timeout-seconds", type=float, default=900.0)
    return parser.parse_args()


def digest_job(job: dict[str, Any]) -> str:
    import numpy as np

    hasher = hashlib.sha256()
    hasher.update(str(job["prompt"]).encode("utf-8"))
    audio = np.asarray(
        job["multi_modal_data"]["audio"][0], dtype=np.float32
    ).reshape(-1)
    hasher.update(audio.shape[0].to_bytes(8, "little"))
    hasher.update(audio.tobytes(order="C"))
    return hasher.hexdigest()


def snapshot_state(state: Any) -> SimpleNamespace:
    return SimpleNamespace(
        chunk_id=int(state.chunk_id),
        unfixed_chunk_num=int(state.unfixed_chunk_num),
        unfixed_token_num=int(state.unfixed_token_num),
        force_language=state.force_language,
        _raw_decoded=str(state._raw_decoded),
    )


def records_differ(
    proposer: dict[str, Any],
    canonical: dict[str, Any],
) -> bool:
    return (
        proposer["token_ids"] != canonical["token_ids"]
        or proposer["text"] != canonical["text"]
    )


def wait_for_kind(
    result_queue: Any,
    expected: int,
    *,
    timeout: float,
) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    deadline = time.monotonic() + timeout
    while len(records) < expected:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError(
                f"timed out after {len(records)}/{expected} results"
            )
        result = result_queue.get(timeout=remaining)
        if result.get("kind") == "error":
            raise RuntimeError(result["traceback"])
        if result.get("kind") != "verified_item":
            continue
        records.append(result)
    return records


def main() -> int:
    args = parse_args()
    if not 0.0 < args.audit_probability < 1.0:
        raise ValueError("audit probability must lie in (0,1)")

    mp.set_start_method("spawn", force=True)
    script_dir = str(Path(__file__).resolve().parent)
    if script_dir not in sys.path:
        sys.path.insert(0, script_dir)
    from run_revtrace_dual_gpu import build_asr, verifier_worker

    command_queue = mp.Queue()
    result_queue = mp.Queue()
    verifier = mp.Process(
        target=verifier_worker,
        kwargs={
            "command_queue": command_queue,
            "result_queue": result_queue,
            "gpu": args.verifier_gpu,
            "model": str(args.model),
            "dtype": "float16",
            "gpu_memory_utilization": args.gpu_memory_utilization,
            "data_manifest": str(args.data_manifest),
            "duration_seconds": args.duration_seconds,
            "concurrency": args.concurrency,
            "worker_id": 0,
            "max_model_len": 4096,
            "terminal_canonical_batch_size": 1,
            "terminal_canonical_batch_invariant": False,
        },
    )
    verifier.start()
    ready = result_queue.get(timeout=args.result_timeout_seconds)
    if ready.get("kind") == "error":
        raise RuntimeError(ready["traceback"])
    if ready.get("kind") != "ready":
        raise RuntimeError(f"unexpected verifier startup record: {ready}")

    os.environ["CUDA_VISIBLE_DEVICES"] = args.proposer_gpu
    from run_revbatch_gate import (
        SAMPLE_RATE,
        load_sources,
        make_streams,
        official_smoke,
        prepare_job,
    )
    from run_revguard_same_input import (
        candidate_record,
        state_projection_record,
    )
    from run_revtrace_dual_gpu import apply_candidate_record
    from revtrace.risk import AuditRiskBound

    proposer = build_asr(
        str(args.model),
        "float16",
        args.gpu_memory_utilization,
        logprobs=20,
    )
    sources = load_sources(args.data_manifest)
    smoke = official_smoke(proposer, sources["English"][0])
    if not smoke["exact"]:
        raise AssertionError("proposer official-semantics smoke failed")

    rng = random.Random(args.seed)
    chunk_samples = 2 * SAMPLE_RATE
    risk_entries = 0
    total_events = 0
    base_audits = 0
    caught_output_errors = 0
    caught_state_errors = 0
    mandatory_verifications = 0
    terminal_verifications = 0
    selected_output_violations = 0
    selected_state_violations = 0
    audit_records: list[dict[str, Any]] = []
    margin_strata = {
        "(0.05,0.10]": {
            "entries": 0, "audits": 0, "caught_state_errors": 0
        },
        "(0.10,0.20]": {
            "entries": 0, "audits": 0, "caught_state_errors": 0
        },
        "(0.20,0.50]": {
            "entries": 0, "audits": 0, "caught_state_errors": 0
        },
        "(0.50,1.00]": {
            "entries": 0, "audits": 0, "caught_state_errors": 0
        },
        "(1.00,inf)": {
            "entries": 0, "audits": 0, "caught_state_errors": 0
        },
    }
    batch_seconds: list[float] = []
    verifier_seconds: list[float] = []
    episodes = 0
    ticket_counter = 0
    started = time.perf_counter()

    while risk_entries < args.target_risk_entries:
        streams = make_streams(
            sources, args.duration_seconds, args.concurrency
        )
        rng.shuffle(streams)
        states = [
            proposer.init_streaming_state(
                language=stream["language"],
                unfixed_chunk_num=2,
                unfixed_token_num=5,
                chunk_size_sec=2.0,
            )
            for stream in streams
        ]
        full_chunks = min(
            stream["audio"].shape[0] // chunk_samples
            for stream in streams
        )
        for chunk_index in range(full_chunks):
            terminal = chunk_index == full_chunks - 1
            jobs: list[dict[str, Any]] = []
            prefixes: list[str] = []
            snapshots: list[SimpleNamespace] = []
            # Decide the independent audit coin before observing canonical
            # outcomes.  It is consumed only if the transition is fast-path
            # eligible after proposer inference.
            base_coins = [
                rng.random() < args.audit_probability
                for _ in streams
            ]
            for stream, state in zip(streams, states):
                begin = chunk_index * chunk_samples
                end = begin + chunk_samples
                job, prefix = prepare_job(
                    proposer,
                    state,
                    stream["audio"][begin:end],
                    tail=terminal,
                )
                jobs.append(job)
                prefixes.append(prefix)
                snapshots.append(snapshot_state(state))

            proposal_started = time.perf_counter()
            outputs = proposer.model.generate(
                jobs,
                sampling_params=proposer.sampling_params,
                use_tqdm=False,
            )
            batch_seconds.append(time.perf_counter() - proposal_started)
            proposal_records = [
                candidate_record(output) for output in outputs
            ]
            proposal_projections = [
                state_projection_record(
                    proposer,
                    state,
                    prefix,
                    record,
                    terminal=terminal,
                )
                for state, prefix, record in zip(
                    states, prefixes, proposal_records
                )
            ]

            verification_items: list[dict[str, Any]] = []
            metadata_by_ticket: dict[str, dict[str, Any]] = {}
            selected_records = list(proposal_records)
            selected_projections = list(proposal_projections)
            for position, record in enumerate(proposal_records):
                minimum_margin = record["minimum_margin"]
                low_margin = (
                    minimum_margin is None
                    or minimum_margin <= args.margin_threshold
                )
                risk_eligible = not terminal and not low_margin
                audited = risk_eligible and base_coins[position]
                if risk_eligible:
                    if minimum_margin <= 0.10:
                        stratum = "(0.05,0.10]"
                    elif minimum_margin <= 0.20:
                        stratum = "(0.10,0.20]"
                    elif minimum_margin <= 0.50:
                        stratum = "(0.20,0.50]"
                    elif minimum_margin <= 1.00:
                        stratum = "(0.50,1.00]"
                    else:
                        stratum = "(1.00,inf)"
                    margin_strata[stratum]["entries"] += 1
                    margin_strata[stratum]["audits"] += int(audited)
                    risk_entries += 1
                    base_audits += int(audited)
                else:
                    stratum = None
                mandatory = terminal or low_margin
                if mandatory:
                    mandatory_verifications += 1
                    terminal_verifications += int(terminal)
                if not (mandatory or audited):
                    continue
                ticket = f"e{episodes:04d}-c{chunk_index:02d}-p{position:03d}-t{ticket_counter}"
                ticket_counter += 1
                verification_items.append(
                    {
                        "ticket": ticket,
                        "job": jobs[position],
                    }
                )
                metadata_by_ticket[ticket] = {
                    "position": position,
                    "audited": audited,
                    "mandatory": mandatory,
                    "terminal": terminal,
                    "prefix": prefixes[position],
                    "state": snapshots[position],
                    "job_sha256": digest_job(jobs[position]),
                    "proposer": proposal_records[position],
                    "proposer_projection": proposal_projections[position],
                    "minimum_margin": minimum_margin,
                    "stratum": stratum,
                }

            if verification_items:
                command_queue.put(
                    {
                        "kind": "verify",
                        "batch_id": f"e{episodes}-c{chunk_index}",
                        "items": verification_items,
                    }
                )
                verified = wait_for_kind(
                    result_queue,
                    len(verification_items),
                    timeout=args.result_timeout_seconds,
                )
                for result in verified:
                    verifier_seconds.append(
                        float(result["request_seconds"])
                    )
                    metadata = metadata_by_ticket[result["ticket"]]
                    canonical = result["record"]
                    canonical_projection = state_projection_record(
                        proposer,
                        metadata["state"],
                        metadata["prefix"],
                        canonical,
                        terminal=metadata["terminal"],
                    )
                    output_error = records_differ(
                        metadata["proposer"], canonical
                    )
                    state_error = (
                        metadata["proposer_projection"][
                            "projection_token_ids"
                        ]
                        != canonical_projection["projection_token_ids"]
                    )
                    if metadata["audited"]:
                        caught_output_errors += int(output_error)
                        caught_state_errors += int(state_error)
                        margin_strata[metadata["stratum"]][
                            "caught_state_errors"
                        ] += int(state_error)
                        audit_records.append(
                            {
                                "ticket": result["ticket"],
                                "job_sha256": metadata["job_sha256"],
                                "terminal": metadata["terminal"],
                                "minimum_margin": metadata[
                                    "minimum_margin"
                                ],
                                "output_error": output_error,
                                "state_error": state_error,
                                "proposer_token_ids": metadata["proposer"][
                                    "token_ids"
                                ],
                                "canonical_token_ids": canonical[
                                    "token_ids"
                                ],
                                "proposer_projection_sha256": hashlib.sha256(
                                    json.dumps(
                                        metadata["proposer_projection"][
                                            "projection_token_ids"
                                        ],
                                        separators=(",", ":"),
                                    ).encode("utf-8")
                                ).hexdigest(),
                                "canonical_projection_sha256": hashlib.sha256(
                                    json.dumps(
                                        canonical_projection[
                                            "projection_token_ids"
                                        ],
                                        separators=(",", ":"),
                                    ).encode("utf-8")
                                ).hexdigest(),
                            }
                        )
                    if metadata["mandatory"] or metadata["audited"]:
                        position = int(metadata["position"])
                        selected_records[position] = canonical
                        selected_projections[position] = canonical_projection
                        selected_output_violations += int(
                            records_differ(
                                selected_records[position], canonical
                            )
                        )
                        selected_state_violations += int(
                            selected_projections[position][
                                "projection_token_ids"
                            ]
                            != canonical_projection[
                                "projection_token_ids"
                            ]
                        )

            for state, prefix, record in zip(
                states, prefixes, selected_records
            ):
                apply_candidate_record(state, record, prefix)
            total_events += len(streams)
        episodes += 1
        print(
            json.dumps(
                {
                    "episodes": episodes,
                    "total_events": total_events,
                    "risk_entries": risk_entries,
                    "base_audits": base_audits,
                    "caught_state_errors": caught_state_errors,
                    "elapsed_seconds": time.perf_counter() - started,
                },
                sort_keys=True,
            ),
            flush=True,
        )

    command_queue.put({"kind": "stop"})
    try:
        while True:
            stopped = result_queue.get(timeout=30.0)
            if stopped.get("kind") == "stopped":
                break
    except queue.Empty:
        pass
    verifier.join(timeout=30.0)
    if verifier.is_alive():
        verifier.terminate()
        verifier.join()

    bound = AuditRiskBound(args.audit_probability, args.alpha)
    upper_error_count = bound.upper_error_count(
        risk_entries, caught_state_errors
    )
    upper_risk = upper_error_count / risk_entries
    passed = (
        risk_entries >= args.target_risk_entries
        and base_audits >= 500
        and upper_risk <= args.delta
        and selected_output_violations == 0
        and selected_state_violations == 0
    )
    payload = {
        "schema_version": 1,
        "study": "RevTrace S1 randomized natural shadow audit",
        "decision": (
            "S1_NATURAL_SHADOW_AUDIT_PASS"
            if passed
            else "S1_NATURAL_SHADOW_AUDIT_FAIL"
        ),
        "model": args.model_name,
        "config": {
            "target_risk_entries": args.target_risk_entries,
            "duration_seconds": args.duration_seconds,
            "concurrency": args.concurrency,
            "dtype": "float16",
            "margin_threshold": args.margin_threshold,
            "audit_probability": args.audit_probability,
            "alpha": args.alpha,
            "delta": args.delta,
            "seed": args.seed,
        },
        "counts": {
            "episodes": episodes,
            "total_revision_events": total_events,
            "risk_eligible_state_entries": risk_entries,
            "base_audits": base_audits,
            "mandatory_verifications": mandatory_verifications,
            "terminal_verifications": terminal_verifications,
            "caught_output_errors": caught_output_errors,
            "caught_state_errors": caught_state_errors,
            "selected_output_violations": selected_output_violations,
            "selected_state_violations": selected_state_violations,
        },
        "risk_certificate": {
            "upper_error_count": upper_error_count,
            "upper_risk": upper_risk,
            "confidence": 1.0 - args.alpha,
            "target_delta": args.delta,
            "method": "fixed-probability mixture e-process inversion",
        },
        "margin_strata": margin_strata,
        "timing_diagnostics": {
            "wall_seconds": time.perf_counter() - started,
            "proposer_batch_seconds_total": sum(batch_seconds),
            "proposer_batch_seconds_p50": statistics.median(batch_seconds),
            "verifier_request_seconds_total": sum(verifier_seconds),
            "verifier_request_seconds_p50": (
                statistics.median(verifier_seconds)
                if verifier_seconds
                else 0.0
            ),
        },
        "audit_records": audit_records,
        "environment": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "proposer_gpu": args.proposer_gpu,
            "verifier_gpu": args.verifier_gpu,
        },
        "claim_boundaries": {
            "population": (
                "FP16 high-margin nonterminal state entries on repeated "
                "natural audio traces under randomized batch composition"
            ),
            "dependence": (
                "error sequence may be dependent and drift arbitrarily; "
                "only base audit coins are independent"
            ),
            "uniqueness": (
                "30k entries are execution events, not 30k independent "
                "utterances"
            ),
            "latency": (
                "shadow-audit wall time is diagnostic and is not a deployed "
                "serving performance claim"
            ),
            "determinism": (
                "risk certificate is statistical, not a deterministic "
                "arithmetic-path certificate"
            ),
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(payload, sort_keys=True))
    return 0 if passed else 2


if __name__ == "__main__":
    raise SystemExit(main())

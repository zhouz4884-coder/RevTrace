#!/usr/bin/env python3
"""Live selective canonical-verification oracle for RevGuard.

The policy uses a threshold frozen on the c=8 calibration run:

* generate every ready revision in one batch;
* accept a proposal only when every generated token has top-1/top-2 logprob
  margin strictly greater than 1.0;
* recompute all other revisions through the canonical singleton path.

A full singleton pass is also executed as the correctness reference but is
excluded from policy service time.  Only policy outputs update revision state.
"""

from __future__ import annotations

import argparse
import json
import platform
import statistics
import time
from pathlib import Path
from typing import Any

from qwen_asr import Qwen3ASRModel
from vllm import SamplingParams

from run_revbatch_gate import (
    SAMPLE_RATE,
    apply_output,
    load_sources,
    make_streams,
    official_smoke,
    prepare_job,
)
from run_revguard_same_input import (
    candidate_record,
    compare_records,
    state_projection_record,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--model-name", required=True)
    parser.add_argument("--data-manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--duration-seconds", type=int, default=30)
    parser.add_argument("--concurrency", type=int, default=16)
    parser.add_argument("--margin-threshold", type=float, default=1.0)
    parser.add_argument("--dtype", default="bfloat16")
    parser.add_argument("--gpu-memory-utilization", type=float, default=0.82)
    return parser.parse_args()


def singleton_generate(
    asr: Qwen3ASRModel, jobs: list[dict[str, Any]]
) -> tuple[list[Any], float, list[float]]:
    outputs = []
    per_request = []
    started = time.perf_counter()
    for job in jobs:
        item_started = time.perf_counter()
        outputs.append(
            asr.model.generate(
                [job], sampling_params=asr.sampling_params, use_tqdm=False
            )[0]
        )
        per_request.append(time.perf_counter() - item_started)
    return outputs, time.perf_counter() - started, per_request


def batch_generate(
    asr: Qwen3ASRModel, jobs: list[dict[str, Any]]
) -> tuple[list[Any], float]:
    started = time.perf_counter()
    outputs = asr.model.generate(
        jobs, sampling_params=asr.sampling_params, use_tqdm=False
    )
    return outputs, time.perf_counter() - started


def main() -> int:
    args = parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    sources = load_sources(args.data_manifest)
    streams = make_streams(
        sources,
        duration=args.duration_seconds,
        concurrency=args.concurrency,
    )
    asr = Qwen3ASRModel.LLM(
        model=str(args.model),
        gpu_memory_utilization=args.gpu_memory_utilization,
        max_inference_batch_size=128,
        max_new_tokens=32,
        enforce_eager=True,
        max_num_seqs=128,
        mm_processor_cache_gb=0,
        async_scheduling=False,
        enable_prefix_caching=False,
        dtype=args.dtype,
    )
    asr.sampling_params = SamplingParams(
        temperature=0.0,
        max_tokens=32,
        logprobs=20,
    )
    smoke = official_smoke(asr, sources["English"][0])
    if not smoke["exact"]:
        raise AssertionError("warm official and copied singleton paths differ")

    states = [
        asr.init_streaming_state(
            language=stream["language"],
            unfixed_chunk_num=2,
            unfixed_token_num=5,
            chunk_size_sec=2.0,
        )
        for stream in streams
    ]
    chunk_samples = 2 * SAMPLE_RATE
    rounds = min(stream["audio"].shape[0] // chunk_samples for stream in streams)
    events = []
    reference_seconds = 0.0
    proposer_seconds = 0.0
    verifier_seconds = 0.0
    verifier_request_seconds: list[float] = []

    for chunk_index in range(rounds):
        terminal = chunk_index == rounds - 1
        jobs = []
        prefixes = []
        for stream, state in zip(streams, states):
            begin = chunk_index * chunk_samples
            end = begin + chunk_samples
            job, prefix = prepare_job(
                asr, state, stream["audio"][begin:end], tail=False
            )
            jobs.append(job)
            prefixes.append(prefix)

        references, elapsed, _ = singleton_generate(asr, jobs)
        reference_seconds += elapsed
        proposals, elapsed = batch_generate(asr, jobs)
        proposer_seconds += elapsed
        proposal_records = [candidate_record(output) for output in proposals]
        for state, prefix, record in zip(
            states, prefixes, proposal_records
        ):
            record["state_projection"] = state_projection_record(
                asr,
                state,
                prefix,
                record,
                terminal=terminal,
            )
        risky_indices = [
            index
            for index, record in enumerate(proposal_records)
            if record["state_projection"]["terminal"]
            or record["minimum_margin"] is None
            or record["minimum_margin"] <= args.margin_threshold
        ]
        risky_jobs = [jobs[index] for index in risky_indices]
        verified_by_index: dict[int, Any] = {}
        if risky_jobs:
            verified, elapsed, per_request = singleton_generate(asr, risky_jobs)
            verifier_seconds += elapsed
            verifier_request_seconds.extend(per_request)
            verified_by_index = dict(zip(risky_indices, verified))

        policy_outputs = [
            verified_by_index.get(index, proposal)
            for index, proposal in enumerate(proposals)
        ]
        for index, (stream, state, prefix, reference, proposal, policy) in enumerate(
            zip(streams, states, prefixes, references, proposals, policy_outputs)
        ):
            reference_record = candidate_record(reference)
            proposal_record = proposal_records[index]
            policy_record = candidate_record(policy)
            for record in (reference_record, policy_record):
                record["state_projection"] = state_projection_record(
                    asr,
                    state,
                    prefix,
                    record,
                    terminal=terminal,
                )
            events.append(
                {
                    "session_id": stream["session_id"],
                    "language": stream["language"],
                    "chunk_id": chunk_index,
                    "terminal": terminal,
                    "verified": index in verified_by_index,
                    "proposal_minimum_margin": proposal_record["minimum_margin"],
                    "proposal_committed_minimum_margin": (
                        proposal_record["state_projection"][
                            "committed_minimum_margin"
                        ]
                    ),
                    "proposal_vs_reference": compare_records(
                        reference_record, proposal_record
                    ),
                    "policy_vs_reference": compare_records(
                        reference_record, policy_record
                    ),
                    "reference_token_ids": reference_record["token_ids"],
                    "proposal_token_ids": proposal_record["token_ids"],
                    "policy_token_ids": policy_record["token_ids"],
                }
            )
            apply_output(state, policy, prefix)
        print(
            json.dumps(
                {
                    "model": args.model_name,
                    "chunk": chunk_index,
                    "verified": len(risky_indices),
                },
                sort_keys=True,
            ),
            flush=True,
        )

    proposal_mismatches = sum(
        not event["proposal_vs_reference"]["token_exact"] for event in events
    )
    violations = sum(
        not event["policy_vs_reference"]["token_exact"] for event in events
    )
    state_violations = sum(
        not event["policy_vs_reference"][
            "state_projection_token_exact"
        ]
        for event in events
    )
    verified_events = sum(event["verified"] for event in events)
    policy_seconds = proposer_seconds + verifier_seconds
    dual_gpu_pipeline_seconds = max(proposer_seconds, verifier_seconds)
    payload = {
        "schema_version": 1,
        "study": "RevGuard live selective canonical-verification oracle",
        "model_name": args.model_name,
        "duration_seconds": args.duration_seconds,
        "concurrency": args.concurrency,
        "margin_threshold": args.margin_threshold,
        "dtype": args.dtype,
        "summary": {
            "event_count": len(events),
            "proposal_mismatch_events": proposal_mismatches,
            "proposal_exact_rate": 1.0 - proposal_mismatches / len(events),
            "verified_events": verified_events,
            "verification_fraction": verified_events / len(events),
            "policy_violation_events": violations,
            "policy_exact_rate": 1.0 - violations / len(events),
            "policy_state_projection_violation_events": state_violations,
            "policy_state_projection_exact_rate": (
                1.0 - state_violations / len(events)
            ),
            "reference_singleton_seconds": reference_seconds,
            "batch_proposer_seconds": proposer_seconds,
            "canonical_verifier_seconds": verifier_seconds,
            "single_gpu_policy_seconds": policy_seconds,
            "single_gpu_policy_speedup": reference_seconds / policy_seconds,
            "dual_gpu_pipeline_lower_bound_speedup": (
                reference_seconds / dual_gpu_pipeline_seconds
            ),
            "verifier_to_proposer_service_ratio": (
                verifier_seconds / proposer_seconds
            ),
            "dual_gpu_headroom_condition_ratio": (
                verifier_seconds / (0.8 * proposer_seconds)
            ),
            "verifier_request_seconds_p50": (
                statistics.median(verifier_request_seconds)
                if verifier_request_seconds
                else 0.0
            ),
        },
        "events": events,
        "official_semantics_smoke": smoke,
        "environment": {
            "python": platform.python_version(),
        },
    }
    args.output.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(payload["summary"], sort_keys=True), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

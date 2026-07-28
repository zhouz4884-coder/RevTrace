#!/usr/bin/env python3
"""Live release-aware packing gate for non-preemptive audit requests.

The same warmed GPU and mandatory revision trace are executed twice:
mandatory-only and release-aware packing.  An audit is admitted only if its
pre-measured P99 plus a guard fits before the next two-second release.  This is
a real GPU scheduling gate, not an offline trace replay.
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--model-name", required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--gpu", default="1")
    parser.add_argument("--concurrency", type=int, default=8)
    parser.add_argument("--rounds", type=int, default=20)
    parser.add_argument("--audit-calibration-requests", type=int, default=20)
    parser.add_argument("--release-interval-seconds", type=float, default=2.0)
    parser.add_argument("--guard-fraction", type=float, default=0.10)
    return parser.parse_args()


def percentile(values: list[float], q: float) -> float:
    ordered = sorted(values)
    position = (len(ordered) - 1) * q
    lower = int(position)
    upper = min(len(ordered) - 1, lower + 1)
    weight = position - lower
    return ordered[lower] * (1.0 - weight) + ordered[upper] * weight


def main() -> int:
    args = parse_args()
    if args.rounds < 2:
        raise ValueError("--rounds must be at least two")
    script_dir = str(Path(__file__).resolve().parent)
    source_dir = str(Path(__file__).resolve().parents[2] / "src")
    for path in (script_dir, source_dir):
        if path not in sys.path:
            sys.path.insert(0, path)

    import os

    os.environ["CUDA_VISIBLE_DEVICES"] = str(args.gpu)
    from run_revbatch_gate import (
        SAMPLE_RATE,
        apply_output,
        load_sources,
        make_streams,
        prepare_job,
    )
    from run_revguard_same_input import candidate_record
    from run_revtrace_dual_gpu import build_asr
    from revtrace.phase5 import release_aware_audit_admissible

    asr = build_asr(str(args.model), "float16", 0.82)
    sources = load_sources(args.manifest)
    duration = args.rounds * 2

    def new_streams(concurrency: int) -> tuple[list[dict[str, Any]], list[Any]]:
        streams = make_streams(
            sources,
            duration=duration,
            concurrency=concurrency,
        )
        states = [
            asr.init_streaming_state(
                language=stream["language"],
                unfixed_chunk_num=2,
                unfixed_token_num=5,
                chunk_size_sec=2.0,
            )
            for stream in streams
        ]
        return streams, states

    def execute_round(
        streams: list[dict[str, Any]],
        states: list[Any],
        chunk_index: int,
    ) -> tuple[list[dict[str, Any]], float]:
        jobs = []
        prefixes = []
        begin = chunk_index * 2 * SAMPLE_RATE
        end = begin + 2 * SAMPLE_RATE
        for stream, state in zip(streams, states):
            job, prefix = prepare_job(
                asr,
                state,
                stream["audio"][begin:end],
                tail=False,
            )
            jobs.append(job)
            prefixes.append(prefix)
        started = time.perf_counter()
        outputs = asr.model.generate(
            jobs,
            sampling_params=asr.sampling_params,
            use_tqdm=False,
        )
        elapsed = time.perf_counter() - started
        records = [candidate_record(output) for output in outputs]
        for state, output, prefix in zip(states, outputs, prefixes):
            apply_output(state, output, prefix)
        return records, elapsed

    # Warm every measured shape before calibration.
    warm_streams, warm_states = new_streams(args.concurrency)
    execute_round(warm_streams, warm_states, 0)
    warm_audit_streams, warm_audit_states = new_streams(1)
    execute_round(warm_audit_streams, warm_audit_states, 0)

    # Calibration uses real singleton audit requests but is excluded from both
    # service traces.
    audit_calibration_seconds: list[float] = []
    audit_streams, audit_states = new_streams(1)
    for index in range(args.audit_calibration_requests):
        chunk = index % args.rounds
        if chunk == 0 and index > 0:
            audit_streams, audit_states = new_streams(1)
        _, elapsed = execute_round(audit_streams, audit_states, chunk)
        audit_calibration_seconds.append(elapsed)
    audit_p99 = percentile(audit_calibration_seconds, 0.99)
    guard = max(0.02, audit_p99 * args.guard_fraction)

    def run_mode(
        *,
        packing: bool,
    ) -> dict[str, Any]:
        streams, states = new_streams(args.concurrency)
        packed_audit_streams, packed_audit_states = new_streams(1)
        service_started = time.perf_counter()
        mandatory_latencies: list[float] = []
        mandatory_records: list[list[list[int]]] = []
        packed_audits = 0
        skipped_audits = 0
        audit_completion_times: list[float] = []
        release_lateness: list[float] = []
        for chunk_index in range(args.rounds):
            release = (
                service_started
                + chunk_index * args.release_interval_seconds
            )
            delay = release - time.perf_counter()
            if delay > 0:
                time.sleep(delay)
            actual_start = time.perf_counter()
            release_lateness.append(max(0.0, actual_start - release))
            records, _ = execute_round(
                streams,
                states,
                chunk_index,
            )
            mandatory_latencies.append(time.perf_counter() - release)
            mandatory_records.append(
                [record["token_ids"] for record in records]
            )
            if not packing or chunk_index == args.rounds - 1:
                continue
            next_release = (
                service_started
                + (chunk_index + 1) * args.release_interval_seconds
            )
            now = time.perf_counter()
            if release_aware_audit_admissible(
                now=now,
                verifier_backlog_seconds=0.0,
                audit_p99_seconds=audit_p99,
                guard_seconds=guard,
                next_mandatory_release=next_release,
            ):
                execute_round(
                    packed_audit_streams,
                    packed_audit_states,
                    packed_audits % args.rounds,
                )
                packed_audits += 1
                audit_completion_times.append(
                    time.perf_counter() - service_started
                )
                if packed_audits % args.rounds == 0:
                    packed_audit_streams, packed_audit_states = new_streams(1)
            else:
                skipped_audits += 1
        return {
            "packing": packing,
            "mandatory_latencies": mandatory_latencies,
            "mandatory_records": mandatory_records,
            "mandatory_p50_seconds": statistics.median(
                mandatory_latencies
            ),
            "mandatory_p99_seconds": percentile(
                mandatory_latencies,
                0.99,
            ),
            "deadline_misses": sum(
                latency > args.release_interval_seconds
                for latency in mandatory_latencies
            ),
            "release_lateness_p99_seconds": percentile(
                release_lateness,
                0.99,
            ),
            "packed_audits": packed_audits,
            "skipped_audits": skipped_audits,
            "first_audit_completion_seconds": (
                audit_completion_times[0]
                if audit_completion_times
                else None
            ),
            "service_wall_seconds": time.perf_counter() - service_started,
        }

    baseline = run_mode(packing=False)
    packed = run_mode(packing=True)
    mandatory_exact = (
        baseline["mandatory_records"] == packed["mandatory_records"]
    )
    p99_change = (
        packed["mandatory_p99_seconds"]
        / baseline["mandatory_p99_seconds"]
        - 1.0
    )
    baseline_detection = (
        args.rounds * args.release_interval_seconds
    )
    packed_detection = (
        packed["first_audit_completion_seconds"]
        if packed["first_audit_completion_seconds"] is not None
        else baseline_detection
    )
    detection_improvement = 1.0 - packed_detection / baseline_detection
    passed = (
        packed["packed_audits"] > 0
        and packed["deadline_misses"] == 0
        and mandatory_exact
        and p99_change <= 0.02
        and detection_improvement >= 0.20
    )
    payload = {
        "schema_version": 1,
        "study": "RevTrace Phase 5D live release-aware audit packing",
        "model": args.model_name,
        "decision": (
            "PHASE5D_LIVE_SLACK_PACKING_PASS"
            if passed
            else "PHASE5D_LIVE_SLACK_PACKING_NO_GO"
        ),
        "config": {
            "concurrency": args.concurrency,
            "rounds": args.rounds,
            "release_interval_seconds": args.release_interval_seconds,
            "audit_calibration_requests": args.audit_calibration_requests,
            "audit_p99_seconds": audit_p99,
            "guard_seconds": guard,
        },
        "baseline": {
            key: value
            for key, value in baseline.items()
            if key not in {"mandatory_records", "mandatory_latencies"}
        },
        "packed": {
            key: value
            for key, value in packed.items()
            if key not in {"mandatory_records", "mandatory_latencies"}
        },
        "metrics": {
            "mandatory_outputs_exact": mandatory_exact,
            "p99_change_fraction": p99_change,
            "detection_time_improvement": detection_improvement,
        },
        "gates": {
            "deadline_miss_zero": packed["deadline_misses"] == 0,
            "p99_change_at_most_2_percent": p99_change <= 0.02,
            "detection_improvement_at_least_20_percent": (
                detection_improvement >= 0.20
            ),
            "live_gpu_service_executed": True,
        },
        "claim_boundaries": [
            "one warmed Qwen3-ASR GPU executes both mandatory and audit work",
            "audit admission uses a pre-measured request P99 plus guard",
            (
                "this small physical gate tests safe packing opportunity; it "
                "does not establish production drift-detection prevalence"
            ),
        ],
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

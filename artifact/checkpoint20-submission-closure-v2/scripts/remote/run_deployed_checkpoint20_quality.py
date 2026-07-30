#!/usr/bin/env python3
"""Deployed B=12 paired quality and provisional-experience gate.

GPU 0 runs the ordinary FP16 B=12 proposer.  GPU 1 runs the frozen FP16
fixed-B=12 authority.  The three paired paths are:

1. continuous full-history proposer;
2. checkpoint-20 with synchronous low-margin singleton verification;
3. checkpoint-20 with provisional low-margin holdback.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import multiprocessing as mp
import os
import platform
import statistics
import sys
import time
from pathlib import Path
from typing import Any

import numpy as np

SOURCE_DIR = Path(__file__).resolve().parents[2] / "src"
sys.path.insert(0, str(SOURCE_DIR))
from revtrace.evidence_audit import (  # noqa: E402
    provisional_overwrite_fraction,
    validate_resume_quality,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--model-name", required=True)
    parser.add_argument("--data-manifest", type=Path, required=True)
    parser.add_argument("--contract-manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--sessions-per-language", type=int, default=32)
    parser.add_argument("--duration-seconds", type=int, default=120)
    parser.add_argument("--checkpoint-seconds", type=int, default=20)
    parser.add_argument("--batch-size", type=int, default=12)
    parser.add_argument("--margin-threshold", type=float, default=0.031251)
    parser.add_argument("--proposer-gpu", default="0")
    parser.add_argument("--authority-gpu", default="1")
    parser.add_argument("--gpu-memory-utilization", type=float, default=0.80)
    parser.add_argument("--authority-gpu-memory-utilization", type=float, default=0.80)
    parser.add_argument("--result-timeout-seconds", type=float, default=900.0)
    parser.add_argument("--silence-ms", type=int, default=250)
    parser.add_argument("--maximum-primary-error-delta", type=float, default=0.02)
    parser.add_argument("--maximum-catastrophic-outliers", type=int, default=0)
    parser.add_argument("--bootstrap-replicates", type=int, default=10_000)
    parser.add_argument("--bootstrap-seed", type=int, default=20260830)
    parser.add_argument(
        "--resume-quality",
        type=Path,
        help=(
            "Reuse the frozen continuous and checkpoint+verify paths and "
            "rerun only holdback to repair/audit provisional UX metrics."
        ),
    )
    return parser.parse_args()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def percentile(values: list[float], q: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = (len(ordered) - 1) * q
    lower = int(index)
    upper = min(lower + 1, len(ordered) - 1)
    weight = index - lower
    return ordered[lower] * (1.0 - weight) + ordered[upper] * weight


def main() -> int:
    args = parse_args()
    if (
        args.duration_seconds % args.checkpoint_seconds
        or args.checkpoint_seconds % 2
        or args.batch_size != 12
        or args.sessions_per_language < 16
    ):
        raise ValueError("frozen gate requires B=12, >=16 sessions/language")
    if (
        args.resume_quality is not None
        and args.resume_quality.resolve() == args.output.resolve()
    ):
        raise ValueError("resume source and output must be different files")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    script_dir = Path(__file__).resolve().parent
    sys.path.insert(0, str(script_dir))
    sys.path.insert(0, str(script_dir.parents[1] / "src"))

    from run_checkpoint_rebase_quality import (
        error_rate,
        hypothesis_distance,
        paired_bootstrap,
    )
    from run_revbatch_gate import SAMPLE_RATE, apply_output, prepare_job, read_audio
    from run_revguard_same_input import candidate_record, state_projection_record
    from run_revtrace_dual_gpu import (
        apply_candidate_record,
        build_asr,
        receive_or_raise,
        verifier_worker,
    )
    from revtrace.long_horizon import (
        append_checkpoint_history,
        assert_provisional_holdback_transition,
        checkpoint_due,
        checkpoint_payload,
        feedback_state_snapshot,
    )

    contract = json.loads(args.contract_manifest.read_text(encoding="utf-8"))
    mechanism = contract["mechanism"]
    expected = {
        "duration": mechanism["revision_contract"]["duration_seconds"],
        "checkpoint": mechanism["revision_contract"]["checkpoint_seconds"],
        "threshold": mechanism["risk_policy"]["minimum_margin_threshold"],
        "proposer_batch": mechanism["proposer"]["ordinary_batch_size"],
        "authority_batch": mechanism["authority"]["fixed_batch_size"],
    }
    observed = {
        "duration": args.duration_seconds,
        "checkpoint": args.checkpoint_seconds,
        "threshold": args.margin_threshold,
        "proposer_batch": args.batch_size,
        "authority_batch": args.batch_size,
    }
    if expected != observed:
        raise ValueError(f"runner/contract mismatch: {observed} != {expected}")
    if sha256(args.data_manifest) != mechanism["data"]["manifest_sha256"]:
        raise ValueError("data manifest does not match frozen contract")

    manifest = json.loads(args.data_manifest.read_text(encoding="utf-8"))
    grouped: dict[str, list[dict[str, Any]]] = {"English": [], "Chinese": []}
    for record in manifest["records"]:
        language = str(record["language"])
        if language in grouped and record.get("reference"):
            grouped[language].append(dict(record))
    if any(len(records) < args.sessions_per_language for records in grouped.values()):
        raise RuntimeError("annotated manifest lacks language coverage")
    target_samples = args.duration_seconds * SAMPLE_RATE
    silence = np.zeros(args.silence_ms * SAMPLE_RATE // 1000, dtype=np.float32)

    def make_stream(language: str, index: int) -> dict[str, Any]:
        candidates = grouped[language]
        pieces: list[np.ndarray] = []
        references: list[str] = []
        source_ids: list[str] = []
        total = 0
        for offset in range(len(candidates)):
            record = candidates[(index * 13 + offset) % len(candidates)]
            sample_id = str(record["sample_id"])
            if sample_id in source_ids:
                continue
            audio = read_audio(Path(record["path"]))
            separator = int(silence.size) if pieces else 0
            if total + separator + int(audio.size) > target_samples:
                continue
            if pieces and silence.size:
                pieces.append(silence)
                total += int(silence.size)
            pieces.append(audio)
            total += int(audio.size)
            source_ids.append(sample_id)
            references.append(str(record["reference"]))
            if target_samples - total < SAMPLE_RATE:
                break
        if not pieces:
            raise RuntimeError("no annotated utterance fits target duration")
        if total < target_samples:
            pieces.append(np.zeros(target_samples - total, dtype=np.float32))
        return {
            "session_id": f"{language}-{index:02d}",
            "language": language,
            "audio": np.concatenate(pieces)[:target_samples],
            "reference": " ".join(references),
            "source_ids": source_ids,
        }

    streams = [
        make_stream(language, index)
        for language in ("English", "Chinese")
        for index in range(args.sessions_per_language)
    ]
    resumed_from: dict[str, Any] | None = None
    resume_validation: dict[str, Any] | None = None
    if args.resume_quality is not None:
        resumed_from = json.loads(
            args.resume_quality.read_text(encoding="utf-8")
        )
        expected_deployment = {
            "proposer": "gpu0_fp16_ordinary_fixed_b12",
            "authority": "gpu1_fp16_batch_invariant_fixed_b12",
            "duration_seconds": args.duration_seconds,
            "checkpoint_seconds": args.checkpoint_seconds,
            "margin_threshold": args.margin_threshold,
            "sessions_per_language": args.sessions_per_language,
        }
        resume_validation = validate_resume_quality(
            resumed=resumed_from,
            expected_sessions=streams,
            mechanism_digest=contract["mechanism_digest"],
            contract_manifest_sha256=sha256(args.contract_manifest),
            expected_deployment=expected_deployment,
        )

    context = mp.get_context("spawn")
    command_queue = context.Queue()
    result_queue = context.Queue()
    authority = context.Process(
        target=verifier_worker,
        kwargs={
            "command_queue": command_queue,
            "result_queue": result_queue,
            "gpu": args.authority_gpu,
            "model": str(args.model),
            "dtype": "float16",
            "gpu_memory_utilization": args.authority_gpu_memory_utilization,
            "data_manifest": str(args.data_manifest),
            "duration_seconds": args.duration_seconds,
            "concurrency": args.batch_size,
            "worker_id": 0,
            "max_model_len": 4096,
            "terminal_canonical_batch_size": args.batch_size,
            "terminal_canonical_batch_invariant": True,
        },
    )
    authority.start()
    ready = receive_or_raise(result_queue, args.result_timeout_seconds)
    if ready.get("kind") != "ready":
        raise RuntimeError(f"authority did not become ready: {ready}")

    os.environ["CUDA_VISIBLE_DEVICES"] = args.proposer_gpu
    proposer = build_asr(
        str(args.model),
        "float16",
        args.gpu_memory_utilization,
        max_model_len=4096,
        logprobs=20,
        max_num_seqs=args.batch_size,
    )
    request_counter = 0

    def canonical(
        jobs: list[dict[str, Any]],
        *,
        fixed_batch: bool,
    ) -> tuple[list[dict[str, Any]], float]:
        nonlocal request_counter
        request_counter += 1
        kind = "canonical_batch" if fixed_batch else "verify"
        items = [
            {
                "ticket": {
                    "request_id": request_counter,
                    "position": position,
                },
                "job": job,
            }
            for position, job in enumerate(jobs)
        ]
        command_queue.put(
            {
                "kind": kind,
                "batch_id": request_counter,
                "items": items,
                "fixed_shape": args.batch_size,
            }
        )
        records: dict[int, dict[str, Any]] = {}
        elapsed = 0.0
        while len(records) < len(items):
            message = receive_or_raise(result_queue, args.result_timeout_seconds)
            if message.get("kind") != "verified_item":
                raise RuntimeError(f"unexpected authority message: {message}")
            records[int(message["position"])] = message["record"]
            elapsed += float(message["elapsed_seconds"])
        return [records[index] for index in range(len(items))], elapsed

    def proposer_batch(jobs: list[dict[str, Any]]) -> tuple[list[Any], float]:
        padded = list(jobs) + [jobs[0]] * (args.batch_size - len(jobs))
        started = time.perf_counter()
        outputs = proposer.model.generate(
            padded,
            sampling_params=proposer.sampling_params,
            use_tqdm=False,
        )
        return outputs[: len(jobs)], time.perf_counter() - started

    def resolve_pending(
        pending: list[list[dict[str, Any]]],
        *,
        position: int,
        age_seconds: int,
        authoritative_text: str,
        language: str,
        reason: str,
        ux_events: list[dict[str, Any]],
    ) -> None:
        for item in pending[position]:
            ux_events.append(
                {
                    **item,
                    "resolution_age_seconds": age_seconds,
                    "resolution": reason,
                    "lifetime_seconds": age_seconds - item["start_age_seconds"],
                    "provisional_to_authority_edit_rate": hypothesis_distance(
                        item["provisional_text"],
                        authoritative_text,
                        language,
                    ),
                    "provisional_overwrite_fraction": (
                        provisional_overwrite_fraction(
                            item["provisional_text"],
                            authoritative_text,
                            language,
                        )
                    ),
                    "authoritative_text": authoritative_text,
                }
            )
        pending[position].clear()

    def run_one(mode: str, active: list[dict[str, Any]]) -> dict[str, Any]:
        if mode not in {"continuous", "checkpoint_verify", "checkpoint_holdback"}:
            raise ValueError(mode)
        states = [
            proposer.init_streaming_state(
                language=stream["language"],
                unfixed_chunk_num=2,
                unfixed_token_num=5,
                chunk_size_sec=2.0,
            )
            for stream in active
        ]
        histories = ["" for _ in active]
        pending: list[list[dict[str, Any]]] = [[] for _ in active]
        ux_events: list[dict[str, Any]] = []
        boundary_snapshots: dict[str, list[str]] = {}
        round_rows: list[dict[str, Any]] = []
        holdbacks = 0
        semantic_checks = 0
        path_started = time.perf_counter()
        for chunk_index in range(args.duration_seconds // 2):
            age = (chunk_index + 1) * 2
            session_terminal = age == args.duration_seconds
            boundary = checkpoint_due(age, args.checkpoint_seconds)
            checkpoint = mode != "continuous" and boundary
            terminal = session_terminal if mode == "continuous" else checkpoint
            jobs: list[dict[str, Any]] = []
            prefixes: list[str] = []
            before_snapshots: list[dict[str, Any]] = []
            for stream, state in zip(active, states):
                before_snapshots.append(feedback_state_snapshot(state))
                begin = chunk_index * 2 * SAMPLE_RATE
                end = begin + 2 * SAMPLE_RATE
                job, prefix = prepare_job(
                    proposer,
                    state,
                    stream["audio"][begin:end],
                    tail=terminal,
                )
                jobs.append(job)
                prefixes.append(prefix)
            round_started = time.perf_counter()
            proposer_seconds = 0.0
            authority_seconds = 0.0
            if checkpoint:
                selected, authority_seconds = canonical(jobs, fixed_batch=True)
                proposals: list[dict[str, Any] | None] = [None] * len(jobs)
            else:
                outputs, proposer_seconds = proposer_batch(jobs)
                proposals = [candidate_record(output) for output in outputs]
                selected = list(proposals)
                if mode == "checkpoint_verify":
                    risky = [
                        index
                        for index, record in enumerate(proposals)
                        if record is None
                        or record["minimum_margin"] is None
                        or float(record["minimum_margin"]) <= args.margin_threshold
                    ]
                    if risky:
                        verified, authority_seconds = canonical(
                            [jobs[index] for index in risky],
                            fixed_batch=False,
                        )
                        for index, record in zip(risky, verified):
                            selected[index] = record
            round_holdbacks = 0
            for position, (stream, state, prefix, record) in enumerate(
                zip(active, states, prefixes, selected)
            ):
                proposal = proposals[position]
                low_margin = bool(
                    proposal is not None
                    and (
                        proposal["minimum_margin"] is None
                        or float(proposal["minimum_margin"])
                        <= args.margin_threshold
                    )
                )
                held_back = bool(
                    mode == "checkpoint_holdback"
                    and not checkpoint
                    and low_margin
                )
                if held_back:
                    assert proposal is not None
                    assert_provisional_holdback_transition(
                        before_snapshots[position],
                        feedback_state_snapshot(state),
                        expected_audio_samples=2 * SAMPLE_RATE,
                    )
                    semantic_checks += 1
                    provisional = (prefix + str(proposal["text"])).strip()
                    pending[position].append(
                        {
                            "session_id": stream["session_id"],
                            "language": stream["language"],
                            "start_age_seconds": age,
                            "provisional_text": provisional,
                        }
                    )
                    holdbacks += 1
                    round_holdbacks += 1
                    continue

                projection = state_projection_record(
                    proposer,
                    state,
                    prefix,
                    record,
                    terminal=terminal,
                )
                if proposal is not None and record is proposal:
                    applied = apply_output(state, outputs[position], prefix)
                else:
                    applied = apply_candidate_record(state, record, prefix)
                authoritative_text = str(applied["text"]).strip()
                reason = "checkpoint_authority" if checkpoint else "next_high_margin"
                if checkpoint:
                    segment_text = checkpoint_payload(
                        prefix=prefix,
                        selected=record,
                        selected_projection=projection,
                    )
                    authoritative_text = segment_text
                    histories[position] = append_checkpoint_history(
                        histories[position], segment_text
                    )
                if pending[position]:
                    resolve_pending(
                        pending,
                        position=position,
                        age_seconds=age,
                        authoritative_text=authoritative_text,
                        language=stream["language"],
                        reason=reason,
                        ux_events=ux_events,
                    )
                if checkpoint and not session_terminal:
                    states[position] = proposer.init_streaming_state(
                        context=histories[position],
                        language=stream["language"],
                        unfixed_chunk_num=2,
                        unfixed_token_num=5,
                        chunk_size_sec=2.0,
                    )
            if boundary:
                boundary_snapshots[str(age)] = [
                    histories[index] if checkpoint else str(states[index].text)
                    for index in range(len(active))
                ]
            round_rows.append(
                {
                    "chunk_index": chunk_index,
                    "age_end_seconds": age,
                    "checkpoint": checkpoint,
                    "holdback_count": round_holdbacks,
                    "proposer_seconds": proposer_seconds,
                    "authority_seconds": authority_seconds,
                    "round_wall_seconds": time.perf_counter() - round_started,
                }
            )
        if any(pending):
            raise AssertionError("terminal authority left unresolved provisional output")
        finals = [
            histories[index] if mode != "continuous" else str(states[index].text)
            for index in range(len(active))
        ]
        return {
            "finals": finals,
            "boundary_snapshots": boundary_snapshots,
            "rounds": round_rows,
            "holdbacks": holdbacks,
            "ux_events": ux_events,
            "semantic_checks": semantic_checks,
            "wall_seconds": time.perf_counter() - path_started,
        }

    def run_all(mode: str) -> dict[str, Any]:
        combined = {
            "finals": [],
            "boundary_snapshots": {},
            "rounds": [],
            "holdbacks": 0,
            "ux_events": [],
            "semantic_checks": 0,
            "wall_seconds": 0.0,
        }
        for start in range(0, len(streams), args.batch_size):
            batch = streams[start : start + args.batch_size]
            result = run_one(mode, batch)
            combined["finals"].extend(result["finals"])
            combined["rounds"].extend(
                {**row, "evaluation_batch_start": start, "real_batch_size": len(batch)}
                for row in result["rounds"]
            )
            combined["holdbacks"] += result["holdbacks"]
            combined["ux_events"].extend(result["ux_events"])
            combined["semantic_checks"] += result["semantic_checks"]
            combined["wall_seconds"] += result["wall_seconds"]
            for age, values in result["boundary_snapshots"].items():
                combined["boundary_snapshots"].setdefault(age, []).extend(values)
        return combined

    if args.resume_quality is None:
        continuous = run_all("continuous")
        checkpoint_verify = run_all("checkpoint_verify")
    else:
        assert resumed_from is not None
        by_session = {
            row["session_id"]: row for row in resumed_from["paired_sessions"]
        }
        continuous = {
            "finals": [
                by_session[stream["session_id"]]["transcripts"]["continuous"]
                for stream in streams
            ],
            "rounds": resumed_from["rounds"]["continuous"],
            "wall_seconds": resumed_from["mode_wall_seconds"]["continuous"],
        }
        checkpoint_verify = {
            "finals": [
                by_session[stream["session_id"]]["transcripts"][
                    "checkpoint_verify"
                ]
                for stream in streams
            ],
            "rounds": resumed_from["rounds"]["checkpoint_verify"],
            "wall_seconds": resumed_from["mode_wall_seconds"][
                "checkpoint_verify"
            ],
        }
    checkpoint_holdback = run_all("checkpoint_holdback")

    paired: list[dict[str, Any]] = []
    for position, stream in enumerate(streams):
        language = stream["language"]
        rates = {
            "continuous": error_rate(
                stream["reference"], continuous["finals"][position], language
            ),
            "checkpoint_verify": error_rate(
                stream["reference"], checkpoint_verify["finals"][position], language
            ),
            "checkpoint_holdback": error_rate(
                stream["reference"], checkpoint_holdback["finals"][position], language
            ),
        }
        paired.append(
            {
                "session_id": stream["session_id"],
                "language": language,
                "source_ids": stream["source_ids"],
                "reference": stream["reference"],
                "transcripts": {
                    "continuous": continuous["finals"][position],
                    "checkpoint_verify": checkpoint_verify["finals"][position],
                    "checkpoint_holdback": checkpoint_holdback["finals"][position],
                },
                "primary_error_rates": rates,
                "checkpoint_delta": rates["checkpoint_verify"] - rates["continuous"],
                "holdback_incremental_delta": (
                    rates["checkpoint_holdback"] - rates["checkpoint_verify"]
                ),
                "total_delta": rates["checkpoint_holdback"] - rates["continuous"],
                "catastrophic_outlier": (
                    rates["checkpoint_holdback"] - rates["continuous"] >= 0.20
                ),
            }
        )

    language_metrics: dict[str, Any] = {}
    observed_pass = True
    population_pass = True
    for language_index, language in enumerate(("English", "Chinese")):
        subset = [row for row in paired if row["language"] == language]
        component_rows: dict[str, Any] = {}
        for component_index, component in enumerate(
            ("checkpoint_delta", "holdback_incremental_delta", "total_delta")
        ):
            values = [float(row[component]) for row in subset]
            component_rows[component] = paired_bootstrap(
                values,
                replicates=args.bootstrap_replicates,
                seed=args.bootstrap_seed + language_index * 10 + component_index,
            )
        total_mean = statistics.mean(row["total_delta"] for row in subset)
        catastrophic = sum(row["catastrophic_outlier"] for row in subset)
        observed_pass &= (
            total_mean <= args.maximum_primary_error_delta and catastrophic == 0
        )
        population_pass &= (
            component_rows["total_delta"]["ci95_high"]
            <= args.maximum_primary_error_delta
        )
        language_metrics[language] = {
            "metric": "wer" if language == "English" else "cer",
            "sessions": len(subset),
            "continuous_error_rate_mean": statistics.mean(
                row["primary_error_rates"]["continuous"] for row in subset
            ),
            "checkpoint_verify_error_rate_mean": statistics.mean(
                row["primary_error_rates"]["checkpoint_verify"] for row in subset
            ),
            "checkpoint_holdback_error_rate_mean": statistics.mean(
                row["primary_error_rates"]["checkpoint_holdback"] for row in subset
            ),
            "components": component_rows,
            "catastrophic_outliers": catastrophic,
        }

    ux = checkpoint_holdback["ux_events"]
    lifetimes = [float(row["lifetime_seconds"]) for row in ux]
    edit_rates = [float(row["provisional_to_authority_edit_rate"]) for row in ux]
    overwrite_fractions = [
        float(row["provisional_overwrite_fraction"]) for row in ux
    ]
    resolution_counts = {
        reason: sum(row["resolution"] == reason for row in ux)
        for reason in ("next_high_margin", "checkpoint_authority")
    }
    provisional_experience = {
        "holdback_events": len(ux),
        "holdback_rate": len(ux)
        / max(1, len(streams) * (args.duration_seconds // 2 - args.duration_seconds // args.checkpoint_seconds)),
        "resolution_counts": resolution_counts,
        "resolution_fractions": {
            key: value / max(1, len(ux)) for key, value in resolution_counts.items()
        },
        "lifetime_seconds": {
            "p50": percentile(lifetimes, 0.50),
            "p95": percentile(lifetimes, 0.95),
            "maximum": max(lifetimes, default=0.0),
        },
        "provisional_to_authority_edit_rate": {
            "definition": (
                "legacy forward edit distance divided by provisional length; "
                "can exceed one because normal appended text is counted"
            ),
            "mean": statistics.mean(edit_rates) if edit_rates else 0.0,
            "p95": percentile(edit_rates, 0.95),
            "maximum": max(edit_rates, default=0.0),
        },
        "provisional_overwrite_fraction": {
            "definition": (
                "fraction of already displayed normalized units no longer "
                "preserved as an exact prefix; appended text is free"
            ),
            "mean": (
                statistics.mean(overwrite_fractions)
                if overwrite_fractions
                else 0.0
            ),
            "p50": percentile(overwrite_fractions, 0.50),
            "p95": percentile(overwrite_fractions, 0.95),
            "maximum": max(overwrite_fractions, default=0.0),
            "zero_overwrite_fraction": (
                sum(value == 0.0 for value in overwrite_fractions)
                / max(1, len(overwrite_fractions))
            ),
        },
        "maximum_allowed_lifetime_seconds": args.checkpoint_seconds,
        "lifetime_bound_pass": max(lifetimes, default=0.0) <= args.checkpoint_seconds,
        "events": ux,
    }
    decision = (
        "OBSERVED_QUALITY_TOLERANCE_PASS"
        if observed_pass
        else "OBSERVED_QUALITY_TOLERANCE_FAIL"
    )
    population_decision = (
        "POPULATION_NONINFERIORITY_PASS"
        if population_pass
        else "POPULATION_NONINFERIORITY_UNRESOLVED"
    )
    payload = {
        "schema_version": 2,
        "experiment_id": "checkpoint20-deployed-b12-quality",
        "decision": decision,
        "population_decision": population_decision,
        "mechanism_digest": contract["mechanism_digest"],
        "contract_manifest_sha256": sha256(args.contract_manifest),
        "deployment": {
            "proposer": "gpu0_fp16_ordinary_fixed_b12",
            "authority": "gpu1_fp16_batch_invariant_fixed_b12",
            "duration_seconds": args.duration_seconds,
            "checkpoint_seconds": args.checkpoint_seconds,
            "margin_threshold": args.margin_threshold,
            "sessions_per_language": args.sessions_per_language,
        },
        "mode_wall_seconds": {
            "continuous": continuous["wall_seconds"],
            "checkpoint_verify": checkpoint_verify["wall_seconds"],
            "checkpoint_holdback": checkpoint_holdback["wall_seconds"],
        },
        "semantic_integration_checks": checkpoint_holdback["semantic_checks"],
        "language_metrics": language_metrics,
        "provisional_experience": provisional_experience,
        "paired_sessions": paired,
        "rounds": {
            "continuous": continuous["rounds"],
            "checkpoint_verify": checkpoint_verify["rounds"],
            "checkpoint_holdback": checkpoint_holdback["rounds"],
        },
        "environment": {
            "python": platform.python_version(),
            "code_commit": os.environ.get("REVTRACE_CODE_COMMIT", "UNRECORDED"),
            "runner_sha256": sha256(Path(__file__)),
            "authority_ready": ready,
            "resumed_from_quality_sha256": (
                sha256(args.resume_quality)
                if args.resume_quality is not None
                else None
            ),
            "resume_validation": resume_validation,
        },
        "claim_boundaries": [
            "Observed paired mean quality tolerance is distinct from population noninferiority.",
            "Margin is an empirical scheduling signal, not a deterministic certificate.",
            "The proposer and authority are deployed on distinct GPUs at frozen B=12.",
            "Provisional UX metrics measure the frozen natural session sample, not production prevalence.",
        ],
    }
    args.output.write_bytes(
        (
            json.dumps(
                payload,
                indent=2,
                ensure_ascii=False,
                sort_keys=True,
            )
            + "\n"
        ).encode("utf-8")
    )
    command_queue.put({"kind": "stop"})
    stopped = receive_or_raise(result_queue, args.result_timeout_seconds)
    if stopped.get("kind") != "stopped":
        raise RuntimeError(f"authority failed to stop: {stopped}")
    authority.join(timeout=30)
    if authority.is_alive():
        authority.terminate()
        authority.join(timeout=10)
        raise RuntimeError("authority worker did not stop")
    print(
        json.dumps(
            {
                "decision": decision,
                "population_decision": population_decision,
                "holdbacks": len(ux),
            },
            sort_keys=True,
        )
    )
    return 0 if observed_pass else 2


if __name__ == "__main__":
    raise SystemExit(main())

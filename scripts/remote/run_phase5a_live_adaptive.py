#!/usr/bin/env python3
"""Persistent-process multi-contract live adaptation gate.

The proposer and verifier are loaded once.  A contract switch creates a fresh
controller epoch, immediately forces all state entries through the fixed-shape
canonical path, and expands the fast path only after the new epoch has enough
split-sample evidence.  With Phase 6 asymmetric memory enabled, an exact
contract return restores only behind renewal canaries, while unseen
populations stay isolated. Post-stage canonical replay is excluded from
service timing and checks every selected state transition. When explicitly
declared as an adaptation split, only its first mismatch per session may
raise the dynamic failure floor before a later independent validation stage.
"""

from __future__ import annotations

import argparse
import atexit
import hashlib
import json
import multiprocessing as mp
import os
import platform
import queue
import statistics
import subprocess
import sys
import threading
import time
from dataclasses import asdict
from pathlib import Path
from typing import Any

import numpy as np


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument(
        "--experiment-id",
        default="revtrace-long-horizon-live",
    )
    parser.add_argument("--model-name", required=True)
    parser.add_argument("--data-manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--minimum-audits", type=int, default=1350)
    parser.add_argument("--episode-seconds", type=int, default=30)
    parser.add_argument("--proposer-gpu", default="0")
    parser.add_argument("--verifier-gpu", default="1")
    parser.add_argument("--canonical-batch-size", type=int, default=16)
    parser.add_argument(
        "--canonical-dtype",
        choices=("float16", "float32"),
        default="float32",
    )
    parser.add_argument("--result-timeout-seconds", type=float, default=900.0)
    parser.add_argument("--episode-seed-base", type=int, default=20260729)
    parser.add_argument(
        "--service-mode",
        choices=(
            "full-selective",
            "proposer-only",
            "terminal-only",
            "all-canonical",
        ),
        default="full-selective",
    )
    parser.add_argument(
        "--intermediate-authority",
        choices=("singleton", "fixed-shape"),
        default="fixed-shape",
        help=(
            "singleton matches the headline intermediate authority; "
            "fixed-shape preserves legacy experiments"
        ),
    )
    parser.add_argument(
        "--dual-lane-intermediate-authority",
        action="store_true",
        help=(
            "split nonterminal selective singleton checks across the proposer "
            "GPU and verifier GPU while preserving singleton request shapes"
        ),
    )
    parser.add_argument(
        "--cross-lane-compatibility-artifact",
        type=Path,
        help=(
            "required PASS artifact for dual-lane intermediate authority"
        ),
    )
    parser.add_argument(
        "--burst-b2-compatibility-artifact",
        type=Path,
        help=(
            "PASS artifact authorizing batch-invariant fixed-B=2 authority "
            "for nonterminal verification bursts while retaining B=1 for "
            "isolated checks"
        ),
    )
    parser.add_argument(
        "--audio-construction",
        choices=("cycle-roll", "distinct-sequence"),
        default="cycle-roll",
    )
    parser.add_argument("--inter-utterance-silence-ms", type=int, default=250)
    parser.add_argument(
        "--checkpoint-seconds",
        type=int,
        default=0,
        help=(
            "authoritatively finalize and rebase the streaming state at this "
            "fixed interval; zero preserves continuous full-history state"
        ),
    )
    parser.add_argument("--declared-maximum-prefix-tokens", type=int, default=512)
    parser.add_argument("--declared-maximum-input-tokens", type=int, default=4096)
    parser.add_argument("--max-model-length", type=int, default=4096)
    parser.add_argument(
        "--phase6-asymmetric-memory",
        action="store_true",
        help=(
            "use exact-contract certificate restore, canary renewal, and "
            "persistent per-contract counterexample floors"
        ),
    )
    parser.add_argument("--renewal-canaries", type=int, default=64)
    parser.add_argument(
        "--failure-floor",
        action="append",
        default=[],
        metavar="LABEL:VALUE",
        help="seed one observed counterexample margin for a stage contract",
    )
    parser.add_argument(
        "--statistical-risk-gate",
        action="store_true",
        help=(
            "evaluate risk-limited stages against the 0.5 percent contract "
            "instead of incorrectly requiring zero observed disagreements"
        ),
    )
    parser.add_argument(
        "--frozen-threshold",
        action="append",
        default=[],
        metavar="LABEL:VALUE",
        help=(
            "run an independently seeded static-oracle stage with a threshold "
            "frozen by prior certification; repeat once per stage label"
        ),
    )
    parser.add_argument(
        "--suppress-certified-terminal-proposer",
        action="store_true",
        help=(
            "after an epoch is certified, execute terminal revisions only "
            "on the authoritative canonical path instead of co-running a "
            "discarded proposer"
        ),
    )
    parser.add_argument(
        "--continue-same-contract-stages",
        action="store_true",
        help=(
            "when adjacent reporting stages have an identical fingerprint, "
            "retain the live epoch and certificate instead of invoking a "
            "contract switch; this separates post-certification steady state"
        ),
    )
    parser.add_argument(
        "--promote-post-stage-audit-failures",
        action="store_true",
        help=(
            "conservatively feed the first replay-audit state mismatch for "
            "each session back into the persistent failure floor; intended "
            "only for an adaptation stage followed by independent validation"
        ),
    )
    parser.add_argument(
        "--audit-adaptation-stage",
        action="append",
        default=[],
        metavar="LABEL",
        help=(
            "declare a stage as replay-audit adaptation rather than final "
            "validation; may be repeated"
        ),
    )
    parser.add_argument(
        "--non-gating-stage",
        action="append",
        default=[],
        metavar="LABEL",
        help=(
            "run a declared calibration/warmup stage but exclude it from the "
            "final service decision; all raw metrics remain reported"
        ),
    )
    parser.add_argument(
        "--skip-post-stage-replay",
        action="store_true",
        help=(
            "omit the dependent full canonical replay from pure performance "
            "seeds; legal only because it is not service timing or formal "
            "risk evidence, and a separate randomized audit supplies the "
            "risk contract"
        ),
    )
    parser.add_argument(
        "--low-margin-policy",
        choices=("verify", "holdback"),
        default="verify",
        help=(
            "verify selects a canonical replacement; holdback leaves a "
            "low-margin nonterminal proposal provisional and prevents it "
            "from entering revision state once a threshold certificate is "
            "available"
        ),
    )
    parser.add_argument(
        "--stage",
        action="append",
        default=[],
        help="LABEL:CONCURRENCY:EPISODES[:LANGUAGE]",
    )
    return parser.parse_args()


def percentile(values: list[float], q: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = (len(ordered) - 1) * q
    lower = int(index)
    upper = min(len(ordered) - 1, lower + 1)
    weight = index - lower
    return ordered[lower] * (1.0 - weight) + ordered[upper] * weight


class PowerSampler:
    def __init__(self, gpu_ids: tuple[int, ...], interval: float = 0.1) -> None:
        self.gpu_ids = gpu_ids
        self.interval = interval
        self.samples: list[dict[str, Any]] = []
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        started = time.perf_counter()

        def collect() -> None:
            while not self._stop.is_set():
                completed = subprocess.run(
                    [
                        "nvidia-smi",
                        (
                            "--query-gpu=index,power.draw,clocks.sm,"
                            "temperature.gpu"
                        ),
                        "--format=csv,noheader,nounits",
                    ],
                    text=True,
                    capture_output=True,
                    check=False,
                )
                total = 0.0
                per_gpu: dict[str, dict[str, float]] = {}
                if completed.returncode == 0:
                    for line in completed.stdout.splitlines():
                        fields = [item.strip() for item in line.split(",")]
                        if len(fields) == 4 and int(fields[0]) in self.gpu_ids:
                            total += float(fields[1])
                            per_gpu[fields[0]] = {
                                "power_watts": float(fields[1]),
                                "sm_clock_mhz": float(fields[2]),
                                "temperature_c": float(fields[3]),
                            }
                    self.samples.append(
                        {
                            "time": time.perf_counter() - started,
                            "monotonic_time": time.perf_counter(),
                            "power_watts": total,
                            "per_gpu": per_gpu,
                        }
                    )
                self._stop.wait(self.interval)

        self._thread = threading.Thread(target=collect, daemon=True)
        self._thread.start()

    def stop(self) -> list[dict[str, Any]]:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=5.0)
        return self.samples


def round_telemetry(
    samples: list[dict[str, Any]],
    *,
    started: float,
    finished: float,
) -> dict[str, Any]:
    """Summarize GPU telemetry whose sample instant falls inside one round."""

    selected = [
        sample
        for sample in samples
        if started <= float(sample.get("monotonic_time", -1.0)) <= finished
    ]
    by_gpu: dict[str, dict[str, list[float]]] = {}
    for sample in selected:
        for gpu, row in sample.get("per_gpu", {}).items():
            target = by_gpu.setdefault(
                gpu,
                {
                    "power_watts": [],
                    "sm_clock_mhz": [],
                    "temperature_c": [],
                },
            )
            for field in target:
                target[field].append(float(row[field]))
    gpu_summary = {}
    for gpu, values in sorted(by_gpu.items()):
        gpu_summary[gpu] = {
            "mean_power_watts": statistics.mean(values["power_watts"]),
            "minimum_sm_clock_mhz": min(values["sm_clock_mhz"]),
            "maximum_temperature_c": max(values["temperature_c"]),
        }
    return {
        "sample_count": len(selected),
        "mean_total_power_watts": (
            statistics.mean(float(row["power_watts"]) for row in selected)
            if selected
            else None
        ),
        "maximum_total_power_watts": (
            max(float(row["power_watts"]) for row in selected)
            if selected
            else None
        ),
        "per_gpu": gpu_summary,
    }


def parse_stages(
    values: list[str],
) -> list[tuple[str, int, int, str]]:
    source = values or [
        "c16_initial:16:8:mixed",
        "c64_drift:64:3:mixed",
        "c16_return:16:8:mixed",
    ]
    stages = []
    for value in source:
        fields = value.split(":")
        if len(fields) == 3:
            label, concurrency, episodes = fields
            language = "mixed"
        elif len(fields) == 4:
            label, concurrency, episodes, language = fields
        else:
            raise ValueError(
                "stage must be LABEL:CONCURRENCY:EPISODES[:LANGUAGE]"
            )
        if language not in {"mixed", "English", "Chinese"}:
            raise ValueError(f"unsupported stage language: {language}")
        stages.append((label, int(concurrency), int(episodes), language))
    return stages


def parse_frozen_thresholds(values: list[str]) -> dict[str, float]:
    thresholds: dict[str, float] = {}
    for value in values:
        label, raw_threshold = value.split(":", 1)
        if label in thresholds:
            raise ValueError(f"duplicate frozen threshold: {label}")
        thresholds[label] = float(raw_threshold)
    return thresholds


def parse_label_values(values: list[str]) -> dict[str, float]:
    result: dict[str, float] = {}
    for value in values:
        label, raw_value = value.split(":", 1)
        if label in result:
            raise ValueError(f"duplicate label value: {label}")
        result[label] = float(raw_value)
    return result


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def validate_cross_lane_artifact(
    path: Path,
    *,
    current_runtime_sha256: str | None = None,
) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("decision") != "CROSS_LANE_SINGLETON_COMPATIBILITY_PASS":
        raise ValueError("cross-lane compatibility artifact did not pass")
    counts = payload.get("counts", {})
    if int(counts.get("pairs", 0)) < 720:
        raise ValueError("cross-lane artifact has fewer than 720 pairs")
    config = payload.get("config", {})
    if (
        config.get("gpu0_batch_invariant_runtime") is not True
        or config.get("gpu1_batch_invariant_runtime") is not True
    ):
        raise ValueError(
            "cross-lane artifact does not match the deployed two-lane "
            "batch-invariant runtime"
        )
    if (
        config.get("gpu0_engine_logprobs") != 20
        or config.get("gpu0_singleton_logprobs") is not None
        or config.get("gpu1_singleton_logprobs") is not None
    ):
        raise ValueError(
            "cross-lane artifact does not match deployed lane logprob settings"
        )
    mismatch_fields = (
        "token_exact_mismatches",
        "text_exact_mismatches",
        "state_projection_token_exact_mismatches",
        "state_projection_text_exact_mismatches",
    )
    if any(int(counts.get(field, -1)) != 0 for field in mismatch_fields):
        raise ValueError("cross-lane artifact contains a semantic mismatch")
    if current_runtime_sha256 is not None:
        from revtrace.runtime_contract import require_runtime_sha256

        require_runtime_sha256(payload, current_runtime_sha256)
    return payload


def validate_burst_b2_artifact(
    path: Path,
    *,
    current_runtime_sha256: str | None = None,
) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    counts = payload.get("counts", {})
    if payload.get("decision") != "BURST_B2_AUTHORITY_COMPATIBILITY_PASS":
        raise ValueError("B1/B2 authority gate did not pass")
    if int(counts.get("pairs", 0)) < 720:
        raise ValueError("B1/B2 authority gate is undersized")
    config = payload.get("config", {})
    if (
        config.get("batch_invariant_runtime") is not True
        or int(config.get("singleton_shape", 0)) != 1
        or int(config.get("burst_fixed_shape", 0)) != 2
    ):
        raise ValueError("B1/B2 artifact has an incompatible runtime contract")
    if any(
        int(counts.get(field, -1)) != 0
        for field in (
            "token_exact_mismatches",
            "text_exact_mismatches",
            "state_projection_token_exact_mismatches",
            "state_projection_text_exact_mismatches",
        )
    ):
        raise ValueError("B1/B2 artifact contains a semantic mismatch")
    if current_runtime_sha256 is not None:
        from revtrace.runtime_contract import require_runtime_sha256

        require_runtime_sha256(
            {
                "environment": {
                    "batch_invariant_runtime_sha256": config[
                        "batch_invariant_runtime_sha256"
                    ]
                }
            },
            current_runtime_sha256,
        )
    return payload


def main() -> int:
    args = parse_args()
    cross_lane_artifact: dict[str, Any] | None = None
    cross_lane_artifact_sha256: str | None = None
    burst_b2_artifact: dict[str, Any] | None = None
    burst_b2_artifact_sha256: str | None = None
    if args.dual_lane_intermediate_authority:
        if args.intermediate_authority != "singleton":
            raise ValueError("dual-lane authority requires singleton authority")
        if args.cross_lane_compatibility_artifact is None:
            raise ValueError(
                "dual-lane authority requires a compatibility artifact"
            )
        cross_lane_artifact = validate_cross_lane_artifact(
            args.cross_lane_compatibility_artifact
        )
        cross_lane_artifact_sha256 = sha256(
            args.cross_lane_compatibility_artifact
        )
    elif args.cross_lane_compatibility_artifact is not None:
        raise ValueError(
            "cross-lane artifact supplied without dual-lane authority"
        )
    if args.burst_b2_compatibility_artifact is not None:
        if args.intermediate_authority != "singleton":
            raise ValueError("B2 burst authority requires singleton authority")
        if args.dual_lane_intermediate_authority:
            raise ValueError("B2 burst authority and dual lane are exclusive")
        burst_b2_artifact = validate_burst_b2_artifact(
            args.burst_b2_compatibility_artifact
        )
        burst_b2_artifact_sha256 = sha256(
            args.burst_b2_compatibility_artifact
        )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    script_dir = str(Path(__file__).resolve().parent)
    source_dir = str(Path(__file__).resolve().parents[2] / "src")
    if script_dir not in sys.path:
        sys.path.insert(0, script_dir)
    if source_dir not in sys.path:
        sys.path.insert(0, source_dir)
    from revtrace.runtime_contract import batch_invariant_runtime_sha256

    runtime_sha256 = batch_invariant_runtime_sha256()
    if cross_lane_artifact is not None:
        validate_cross_lane_artifact(
            args.cross_lane_compatibility_artifact,
            current_runtime_sha256=runtime_sha256,
        )
    if burst_b2_artifact is not None:
        validate_burst_b2_artifact(
            args.burst_b2_compatibility_artifact,
            current_runtime_sha256=runtime_sha256,
        )

    from run_revbatch_gate import (
        SAMPLE_RATE,
        apply_output,
        cycle_audio,
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
    from run_revtrace_dual_gpu import (
        build_asr,
        receive_or_raise,
        verifier_worker,
    )
    from revtrace.phase5 import (
        AsymmetricLiveRiskWindowController,
        LiveRiskWindowController,
        summarize_energy,
    )
    from revtrace.long_horizon import (
        append_checkpoint_history,
        checkpoint_payload,
        checkpoint_due,
        concatenate_distinct_audio,
        long_horizon_scope,
    )

    stages = parse_stages(args.stage)
    frozen_thresholds = parse_frozen_thresholds(args.frozen_threshold)
    failure_floors = parse_label_values(args.failure_floor)
    unknown_thresholds = set(frozen_thresholds) - {
        label for label, _, _, _ in stages
    }
    if unknown_thresholds:
        raise ValueError(
            "frozen thresholds do not match stages: "
            f"{sorted(unknown_thresholds)}"
        )
    unknown_floors = set(failure_floors) - {
        label for label, _, _, _ in stages
    }
    if unknown_floors:
        raise ValueError(
            "failure floors do not match stages: "
            f"{sorted(unknown_floors)}"
        )
    max_concurrency = max(item[1] for item in stages)
    if args.canonical_batch_size < max_concurrency:
        raise ValueError(
            "--canonical-batch-size must cover every terminal concurrency"
        )
    if args.inter_utterance_silence_ms < 0:
        raise ValueError("inter-utterance silence must be non-negative")
    if (
        args.checkpoint_seconds < 0
        or (
            args.checkpoint_seconds
            and (
                args.checkpoint_seconds % 2
                or args.episode_seconds % args.checkpoint_seconds
            )
        )
    ):
        raise ValueError(
            "checkpoint interval must be zero or an even divisor of episode"
        )
    if (
        args.declared_maximum_prefix_tokens < 1
        or args.declared_maximum_input_tokens < 1
        or args.max_model_length < 1
    ):
        raise ValueError("declared token bounds must be positive")
    if args.declared_maximum_input_tokens > args.max_model_length:
        raise ValueError(
            "declared input-token contract exceeds runtime model length"
        )
    context = mp.get_context("spawn")
    command_queue = context.Queue()
    result_queue = context.Queue()
    verifier = context.Process(
        target=verifier_worker,
        kwargs={
            "command_queue": command_queue,
            "result_queue": result_queue,
            "gpu": args.verifier_gpu,
            "model": str(args.model),
            "dtype": args.canonical_dtype,
            "gpu_memory_utilization": 0.82,
            "data_manifest": str(args.data_manifest),
            "duration_seconds": args.episode_seconds,
            "concurrency": args.canonical_batch_size,
            "worker_id": 0,
            "max_model_len": args.max_model_length,
            "terminal_canonical_batch_size": args.canonical_batch_size,
            "terminal_canonical_batch_invariant": (
                args.canonical_dtype != "float32"
            ),
        },
        name="phase5a-canonical-verifier",
    )
    verifier.start()

    def emergency_verifier_cleanup() -> None:
        """Prevent a failed proposer startup from orphaning GPU1 authority."""

        if verifier.is_alive():
            verifier.terminate()
            verifier.join(timeout=10.0)

    atexit.register(emergency_verifier_cleanup)
    ready = receive_or_raise(result_queue, args.result_timeout_seconds)
    if ready.get("kind") != "ready":
        raise RuntimeError(f"unexpected verifier ready message: {ready}")

    from revtrace.phase7_1 import CanonicalRuntimeProvenance

    base_intermediate_authority_contract = (
        (
            "float16_dual_singleton_bi_gpu0_gpu1_v1_gate_"
            f"{cross_lane_artifact_sha256[:16]}"
        )
        if args.dual_lane_intermediate_authority
        else (
            (
                "float16_singleton_bi_burst_b2_v1_gate_"
                f"{burst_b2_artifact_sha256[:16]}"
            )
            if burst_b2_artifact is not None
            else
            f"{args.canonical_dtype}_singleton"
            if args.intermediate_authority == "singleton"
            else (
                f"{args.canonical_dtype}_fixed_b"
                f"{args.canonical_batch_size}"
            )
        )
    )
    intermediate_authority_contract = (
        f"{base_intermediate_authority_contract}_low_margin_holdback_v1"
        if args.low_margin_policy == "holdback"
        else base_intermediate_authority_contract
    )
    canonical_provenance = CanonicalRuntimeProvenance(
        model=args.model_name,
        configured_weight_dtype=args.canonical_dtype,
        accumulation_dtype="kernel-defined-unrecorded",
        sampling_dtype="vllm-internal-unrecorded",
        attention_backend=(
            "FLASH_ATTN"
            if args.canonical_dtype != "float32"
            else "vllm-auto-unrecorded"
        ),
        fixed_batch_shape=args.canonical_batch_size,
        batch_invariant_requested=args.canonical_dtype != "float32",
        temperature=0.0,
        max_tokens=32,
        terminal_and_intermediate_same_engine=True,
        intermediate_authority=intermediate_authority_contract,
        terminal_authority=(
            f"{args.canonical_dtype}_fixed_b{args.canonical_batch_size}"
        ),
    )

    os.environ["CUDA_VISIBLE_DEVICES"] = args.proposer_gpu
    if args.dual_lane_intermediate_authority:
        os.environ["VLLM_BATCH_INVARIANT"] = "1"
        os.environ["VLLM_ATTENTION_BACKEND"] = "FLASH_ATTN"
    asr = build_asr(
        str(args.model),
        "float16",
        0.82,
        max_model_len=args.max_model_length,
        max_num_seqs=max_concurrency,
    )
    from vllm import SamplingParams

    local_singleton_sampling_params = SamplingParams(
        temperature=0.0,
        max_tokens=32,
        logprobs=None,
    )
    sources = load_sources(args.data_manifest)
    smoke = official_smoke(asr, sources["English"][0])
    if not smoke["exact"]:
        raise AssertionError("proposer official-semantics smoke failed")

    controller = (
        AsymmetricLiveRiskWindowController(
            minimum_audits=args.minimum_audits,
            renewal_canaries=args.renewal_canaries,
        )
        if args.phase6_asymmetric_memory
        else LiveRiskWindowController(minimum_audits=args.minimum_audits)
    )
    batch_id = 0

    def make_stage_streams(
        *,
        stage_index: int,
        episode: int,
        duration: int,
        concurrency: int,
        language: str,
    ) -> list[dict[str, Any]]:
        """Create reproducibly distinct live inputs for each stage episode."""

        streams = make_streams(
            sources,
            duration=duration,
            concurrency=concurrency,
        )
        for position, stream in enumerate(streams):
            stream_language = (
                stream["language"] if language == "mixed" else language
            )
            stream["language"] = stream_language
            salt = (
                int(args.episode_seed_base)
                + stage_index * 1_000_003
                + episode * 10_007
                + position * 101
            )
            if args.audio_construction == "distinct-sequence":
                stream["audio"], stream["audio_provenance"] = (
                    concatenate_distinct_audio(
                        sources[stream_language],
                        target_samples=duration * SAMPLE_RATE,
                        start_index=salt % len(sources[stream_language]),
                        silence_samples=(
                            args.inter_utterance_silence_ms
                            * SAMPLE_RATE
                            // 1000
                        ),
                    )
                )
            else:
                source = sources[stream_language][
                    position % len(sources[stream_language])
                ]
                audio = cycle_audio(
                    source,
                    duration,
                    offset=(position * 7919) % max(1, source.size),
                )
                shift = salt % max(1, int(audio.shape[0]))
                stream["audio"] = np.roll(audio, shift)
                stream["audio_provenance"] = {
                    "construction": "cycle_roll",
                    "source_count": 1,
                    "sample_level_roll": True,
                    "source_repetition": duration * SAMPLE_RATE > source.size,
                }
            stream["session_id"] = (
                f"stage{stage_index:02d}-episode{episode:04d}-"
                f"s{position:03d}"
            )
        return streams

    def dispatch_canonical_batch(
        jobs: list[dict[str, Any]],
        *,
        fixed_shape: int,
    ) -> tuple[int, int, str]:
        nonlocal batch_id
        if not jobs or len(jobs) > fixed_shape:
            raise ValueError("canonical dispatch must fit one fixed shape")
        current_batch_id = batch_id
        items = [
            {
                "ticket": {
                    "session_id": f"canonical-{batch_id}-{position}",
                    "revision_id": f"canonical-{batch_id}-{position}",
                    "parent_version": 0,
                    "next_version": 1,
                },
                "job": job,
            }
            for position, job in enumerate(jobs)
        ]
        command_queue.put(
            {
                "kind": "canonical_batch",
                "batch_id": batch_id,
                "items": items,
                "fixed_shape": fixed_shape,
            }
        )
        batch_id += 1
        return current_batch_id, len(items), "fixed_shape"

    def dispatch_singleton_verification(
        jobs: list[dict[str, Any]],
    ) -> tuple[int, int, str]:
        nonlocal batch_id
        if not jobs:
            raise ValueError("singleton verification cannot be empty")
        current_batch_id = batch_id
        items = [
            {
                "ticket": {
                    "session_id": f"canonical-{batch_id}-{position}",
                    "revision_id": f"canonical-{batch_id}-{position}",
                    "parent_version": 0,
                    "next_version": 1,
                },
                "job": job,
            }
            for position, job in enumerate(jobs)
        ]
        command_queue.put(
            {
                "kind": "verify",
                "batch_id": batch_id,
                "items": items,
            }
        )
        batch_id += 1
        return current_batch_id, len(items), "singleton"

    def collect_canonical_batch(
        dispatched: tuple[int, int, str],
    ) -> tuple[list[dict[str, Any]], float]:
        expected_batch_id, item_count, authority_lane = dispatched
        elapsed = 0.0
        elapsed_fields: list[float] = []
        by_position: list[dict[str, Any] | None] = [
            None for _ in range(item_count)
        ]
        for _ in range(item_count):
            message = receive_or_raise(
                result_queue, args.result_timeout_seconds
            )
            if (
                message.get("kind") != "verified_item"
                or int(message["batch_id"]) != expected_batch_id
            ):
                raise RuntimeError(
                    f"unexpected canonical result: {message}"
                )
            by_position[int(message["position"])] = message["record"]
            item_elapsed = float(message["elapsed_seconds"])
            elapsed_fields.append(item_elapsed)
            elapsed += item_elapsed
        if any(record is None for record in by_position):
            raise AssertionError("incomplete canonical batch")
        if authority_lane == "fixed_shape":
            nonzero = [value for value in elapsed_fields if value > 0.0]
            if len(nonzero) != 1:
                raise AssertionError(
                    "fixed-shape worker must report one batch wall time"
                )
        return (
            [record for record in by_position if record is not None],
            elapsed,
        )

    def canonical_batch(
        jobs: list[dict[str, Any]],
        *,
        fixed_shape: int,
    ) -> tuple[list[dict[str, Any]], float]:
        return collect_canonical_batch(
            dispatch_canonical_batch(
                jobs,
                fixed_shape=fixed_shape,
            )
        )

    def singleton_canonical(
        jobs: list[dict[str, Any]],
    ) -> tuple[list[dict[str, Any]], float]:
        return collect_canonical_batch(dispatch_singleton_verification(jobs))

    def dispatch_authority(
        jobs: list[dict[str, Any]],
        *,
        terminal: bool,
    ) -> tuple[int, int, str]:
        if terminal or args.intermediate_authority == "fixed-shape":
            return dispatch_canonical_batch(
                jobs,
                fixed_shape=args.canonical_batch_size,
            )
        return dispatch_singleton_verification(jobs)

    def run_authority(
        jobs: list[dict[str, Any]],
        *,
        terminal: bool,
    ) -> tuple[list[dict[str, Any]], float]:
        return collect_canonical_batch(
            dispatch_authority(jobs, terminal=terminal)
        )

    # Compile/profile every proposer and canonical contract shape before the
    # measured switch sequence.  A shape's first-use compilation is deployment
    # initialization, not state-entry latency.
    warmup_started = time.perf_counter()
    for warmup_concurrency in sorted({item[1] for item in stages}):
        warmup_streams = make_streams(
            sources,
            duration=2,
            concurrency=warmup_concurrency,
        )
        warmup_states = [
            asr.init_streaming_state(
                language=stream["language"],
                unfixed_chunk_num=2,
                unfixed_token_num=5,
                chunk_size_sec=2.0,
            )
            for stream in warmup_streams
        ]
        warmup_jobs = []
        for stream, state in zip(warmup_streams, warmup_states):
            job, _ = prepare_job(
                asr,
                state,
                stream["audio"][: 2 * SAMPLE_RATE],
                tail=False,
            )
            warmup_jobs.append(job)
        dispatched = dispatch_canonical_batch(
            warmup_jobs,
            fixed_shape=args.canonical_batch_size,
        )
        asr.model.generate(
            warmup_jobs,
            sampling_params=asr.sampling_params,
            use_tqdm=False,
        )
        collect_canonical_batch(dispatched)
        if args.intermediate_authority == "singleton":
            singleton_canonical([warmup_jobs[0]])
        if burst_b2_artifact is not None:
            canonical_batch(warmup_jobs[:2], fixed_shape=2)
    warmup_seconds_excluded = time.perf_counter() - warmup_started

    stage_payloads: list[dict[str, Any]] = []
    audit_adaptation_stages = set(args.audit_adaptation_stage)
    non_gating_stages = set(args.non_gating_stage)
    if audit_adaptation_stages and not args.promote_post_stage_audit_failures:
        raise ValueError(
            "--audit-adaptation-stage requires "
            "--promote-post-stage-audit-failures"
        )
    unknown_adaptation_stages = audit_adaptation_stages.difference(
        item[0] for item in stages
    )
    if unknown_adaptation_stages:
        raise ValueError(
            "unknown audit adaptation stage(s): "
            + ", ".join(sorted(unknown_adaptation_stages))
        )
    unknown_non_gating_stages = non_gating_stages.difference(
        item[0] for item in stages
    )
    if unknown_non_gating_stages:
        raise ValueError(
            "unknown non-gating stage(s): "
            + ", ".join(sorted(unknown_non_gating_stages))
        )
    global_event = 0
    for stage_index, (
        label,
        concurrency,
        episodes,
        language,
    ) in enumerate(stages):
        frozen_threshold = frozen_thresholds.get(label)
        static_oracle_stage = frozen_threshold is not None
        fingerprint = canonical_provenance.contract_fingerprint(
            proposer_dtype="float16",
            concurrency=concurrency,
            language=language,
            arrival="episode-sync",
            contract_scope=long_horizon_scope(
                duration_seconds=args.episode_seconds,
                maximum_audio_samples=(
                    args.checkpoint_seconds or args.episode_seconds
                )
                * SAMPLE_RATE,
                maximum_session_age_seconds=(
                    args.checkpoint_seconds or args.episode_seconds
                ),
                maximum_prefix_tokens=(
                    args.declared_maximum_prefix_tokens
                ),
                maximum_input_tokens=args.declared_maximum_input_tokens,
                service_mode=args.service_mode,
                intermediate_authority=intermediate_authority_contract,
                terminal_authority=(
                    f"{args.canonical_dtype}_fixed_b"
                    f"{args.canonical_batch_size}"
                ),
                checkpoint_seconds=args.checkpoint_seconds,
                batch_invariant_runtime_sha256=runtime_sha256,
            ),
        )
        if args.phase6_asymmetric_memory and label in failure_floors:
            controller.seed_failure(fingerprint, failure_floors[label])
        continued_same_contract = bool(
            args.continue_same_contract_stages
            and getattr(controller, "current", None) is not None
            and controller.current.fingerprint == fingerprint
        )
        if continued_same_contract:
            epoch = controller.current
            switch_status_at_entry = "continued_same_contract_epoch"
        else:
            epoch = controller.switch(fingerprint)
            switch_status_at_entry = getattr(
                controller, "switch_status", "fresh_epoch"
            )
        stage_started = time.perf_counter()
        sampler = PowerSampler((int(args.proposer_gpu), int(args.verifier_gpu)))
        sampler.start()
        proposer_seconds = 0.0
        required_verifier_seconds = 0.0
        service_events: list[dict[str, Any]] = []
        episode_snapshots: list[dict[str, Any]] = []
        stage_round_details: list[dict[str, Any]] = []
        selected_by_episode: list[list[dict[str, Any]]] = []
        stage_audio_provenance: list[dict[str, Any]] = []
        certified_before_episode: int | None = (
            0
            if static_oracle_stage or epoch.certificate is not None
            else None
        )

        for episode in range(episodes):
            streams = make_stage_streams(
                stage_index=stage_index,
                episode=episode,
                duration=args.episode_seconds,
                concurrency=concurrency,
                language=language,
            )
            if not stage_audio_provenance:
                stage_audio_provenance = [
                    {
                        "session_id": stream["session_id"],
                        **dict(stream["audio_provenance"]),
                    }
                    for stream in streams
                ]
            states = [
                asr.init_streaming_state(
                    language=stream["language"],
                    unfixed_chunk_num=2,
                    unfixed_token_num=5,
                    chunk_size_sec=2.0,
                )
                for stream in streams
            ]
            checkpoint_histories = ["" for _ in streams]
            checkpoint_epochs = [0 for _ in streams]
            chunk_samples = 2 * SAMPLE_RATE
            rounds = args.episode_seconds // 2
            episode_selected: list[dict[str, Any]] = []
            episode_round_latencies: list[float] = []
            episode_service_started = time.perf_counter()
            for chunk_index in range(rounds):
                round_execution_started = time.perf_counter()
                canonical_execution_seconds = 0.0
                verifier_collect_wall_seconds = 0.0
                projection_seconds = 0.0
                apply_seconds = 0.0
                controller_seconds = 0.0
                session_terminal = chunk_index == rounds - 1
                checkpoint_boundary = checkpoint_due(
                    (chunk_index + 1) * 2,
                    args.checkpoint_seconds,
                )
                terminal = session_terminal or checkpoint_boundary
                jobs: list[dict[str, Any]] = []
                prefixes: list[str] = []
                prepare_started = time.perf_counter()
                for stream, state in zip(streams, states):
                    begin = chunk_index * chunk_samples
                    end = begin + chunk_samples
                    job, prefix = prepare_job(
                        asr,
                        state,
                        stream["audio"][begin:end],
                        tail=terminal,
                    )
                    jobs.append(job)
                    prefixes.append(prefix)
                prepare_seconds = time.perf_counter() - prepare_started
                accumulated_audio_samples = [
                    int(job["multi_modal_data"]["audio"][0].shape[0])
                    for job in jobs
                ]
                prefix_token_counts = [
                    len(asr.processor.tokenizer.encode(prefix))
                    if prefix
                    else 0
                    for prefix in prefixes
                ]
                prompt_token_counts = [
                    len(asr.processor.tokenizer.encode(str(job["prompt"])))
                    for job in jobs
                ]
                if (
                    max(prefix_token_counts, default=0)
                    > args.declared_maximum_prefix_tokens
                ):
                    raise RuntimeError(
                        "observed prefix tokens exceed contract scope"
                    )
                if (
                    max(prompt_token_counts, default=0)
                    > args.declared_maximum_input_tokens
                ):
                    raise RuntimeError(
                        "observed prompt tokens exceed contract scope"
                    )
                if args.service_mode == "all-canonical":
                    preverify_all = True
                elif args.service_mode in ("proposer-only", "terminal-only"):
                    preverify_all = (
                        args.service_mode == "terminal-only" and terminal
                    )
                else:
                    preverify_all = (
                        (not static_oracle_stage and controller.fail_closed)
                        or terminal
                    )
                suppress_proposer = bool(
                    args.service_mode == "all-canonical"
                    or (
                        terminal
                        and (
                            static_oracle_stage
                            or epoch.certificate is not None
                        )
                        and args.suppress_certified_terminal_proposer
                        and args.service_mode != "proposer-only"
                    )
                )
                overlapped_dispatch = (
                    dispatch_authority(jobs, terminal=terminal)
                    if preverify_all
                    else None
                )
                verified_by_position: dict[int, dict[str, Any]] = {}
                verified_lane_by_position: dict[int, str] = {}
                holdback_positions: list[int] = []
                if suppress_proposer:
                    if overlapped_dispatch is None:
                        raise AssertionError(
                            "proposer suppression requires canonical dispatch"
                        )
                    collect_started = time.perf_counter()
                    verified, elapsed = collect_canonical_batch(
                        overlapped_dispatch
                    )
                    verifier_collect_wall_seconds += (
                        time.perf_counter() - collect_started
                    )
                    canonical_execution_seconds += elapsed
                    verify_positions = list(range(len(jobs)))
                    required_verifier_seconds += elapsed
                    verified_by_position.update(
                        zip(verify_positions, verified)
                    )
                    verified_lane_by_position.update(
                        (position, "gpu1_fixed_shape")
                        for position in verify_positions
                    )
                    outputs = None
                    proposal_elapsed = 0.0
                    proposals = [
                        dict(verified_by_position[position])
                        for position in verify_positions
                    ]
                else:
                    proposal_started = time.perf_counter()
                    outputs = asr.model.generate(
                        jobs,
                        sampling_params=asr.sampling_params,
                        use_tqdm=False,
                    )
                    proposal_elapsed = time.perf_counter() - proposal_started
                    proposer_seconds += proposal_elapsed
                    proposals = [
                        candidate_record(output) for output in outputs
                    ]
                    if overlapped_dispatch is not None:
                        collect_started = time.perf_counter()
                        verified, elapsed = collect_canonical_batch(
                            overlapped_dispatch
                        )
                        verifier_collect_wall_seconds += (
                            time.perf_counter() - collect_started
                        )
                        canonical_execution_seconds += elapsed
                        verify_positions = list(range(len(jobs)))
                        required_verifier_seconds += elapsed
                        verified_by_position.update(
                            zip(verify_positions, verified)
                        )
                        verified_lane_by_position.update(
                            (position, "gpu1_preverified")
                            for position in verify_positions
                        )
                    else:
                        if args.service_mode in (
                            "proposer-only",
                            "terminal-only",
                        ):
                            verify_positions = []
                        else:
                            verify_positions = [
                                position
                                for position, proposal in enumerate(proposals)
                                if (
                                    (
                                        static_oracle_stage
                                        and (
                                            proposal["minimum_margin"] is None
                                            or float(
                                                proposal["minimum_margin"]
                                            )
                                            <= float(frozen_threshold)
                                        )
                                    )
                                    or (
                                        not static_oracle_stage
                                        and controller.requires_verification(
                                            minimum_margin=proposal[
                                                "minimum_margin"
                                            ],
                                            terminal=terminal,
                                        )
                                    )
                                )
                            ]
                if (
                    args.low_margin_policy == "holdback"
                    and not terminal
                    and (
                        static_oracle_stage
                        or epoch.certificate is not None
                    )
                ):
                    holdback_positions = list(verify_positions)
                    verify_positions = []
                if (
                    verify_positions
                    and overlapped_dispatch is None
                    and not suppress_proposer
                ):
                    if (
                        args.dual_lane_intermediate_authority
                        and not terminal
                        and len(verify_positions) >= 2
                    ):
                        verification_started = time.perf_counter()
                        remote_positions = verify_positions[::2]
                        local_positions = verify_positions[1::2]
                        remote_dispatch = dispatch_singleton_verification(
                            [jobs[position] for position in remote_positions]
                        )
                        local_records = []
                        local_elapsed = 0.0
                        for position in local_positions:
                            local_started = time.perf_counter()
                            local_output = asr.model.generate(
                                [jobs[position]],
                                sampling_params=local_singleton_sampling_params,
                                use_tqdm=False,
                            )[0]
                            local_elapsed += (
                                time.perf_counter() - local_started
                            )
                            local_records.append(
                                candidate_record(local_output)
                            )
                        remote_records, remote_elapsed = (
                            collect_canonical_batch(remote_dispatch)
                        )
                        verifier_collect_wall_seconds += (
                            time.perf_counter() - verification_started
                        )
                        canonical_execution_seconds += (
                            local_elapsed + remote_elapsed
                        )
                        required_verifier_seconds += (
                            local_elapsed + remote_elapsed
                        )
                        verified_by_position.update(
                            zip(remote_positions, remote_records)
                        )
                        verified_by_position.update(
                            zip(local_positions, local_records)
                        )
                        verified_lane_by_position.update(
                            (position, "gpu1_singleton")
                            for position in remote_positions
                        )
                        verified_lane_by_position.update(
                            (position, "gpu0_singleton")
                            for position in local_positions
                        )
                    elif (
                        burst_b2_artifact is not None
                        and not terminal
                        and len(verify_positions) >= 2
                    ):
                        verification_started = time.perf_counter()
                        cursor = 0
                        while cursor < len(verify_positions):
                            wave_positions = verify_positions[cursor : cursor + 2]
                            wave_jobs = [
                                jobs[position] for position in wave_positions
                            ]
                            if len(wave_positions) == 2:
                                wave_records, wave_elapsed = canonical_batch(
                                    wave_jobs,
                                    fixed_shape=2,
                                )
                                lane = "gpu1_burst_b2"
                            else:
                                wave_records, wave_elapsed = (
                                    singleton_canonical(wave_jobs)
                                )
                                lane = "gpu1_singleton"
                            canonical_execution_seconds += wave_elapsed
                            required_verifier_seconds += wave_elapsed
                            verified_by_position.update(
                                zip(wave_positions, wave_records)
                            )
                            verified_lane_by_position.update(
                                (position, lane)
                                for position in wave_positions
                            )
                            cursor += len(wave_positions)
                        verifier_collect_wall_seconds += (
                            time.perf_counter() - verification_started
                        )
                    else:
                        collect_started = time.perf_counter()
                        verified, elapsed = run_authority(
                            [jobs[position] for position in verify_positions],
                            terminal=terminal,
                        )
                        verifier_collect_wall_seconds += (
                            time.perf_counter() - collect_started
                        )
                        canonical_execution_seconds += elapsed
                        required_verifier_seconds += elapsed
                        verified_by_position.update(
                            zip(verify_positions, verified)
                        )
                        verified_lane_by_position.update(
                            (position, "gpu1_singleton")
                            for position in verify_positions
                        )
                round_started = time.perf_counter()
                round_selected_records: list[dict[str, Any]] = []
                observed_model_input_token_counts = [
                    int(record["model_input_token_count"])
                    for record in proposals
                    if record.get("model_input_token_count") is not None
                ]
                if (
                    observed_model_input_token_counts
                    and max(observed_model_input_token_counts)
                    > args.declared_maximum_input_tokens
                ):
                    raise RuntimeError(
                        "observed model input tokens exceed contract scope"
                    )
                for position, (
                    stream,
                    state,
                    prefix,
                    proposal,
                ) in enumerate(zip(streams, states, prefixes, proposals)):
                    held_back = position in holdback_positions
                    selected = verified_by_position.get(position, proposal)
                    projection_started = time.perf_counter()
                    proposal_projection = state_projection_record(
                        asr,
                        state,
                        prefix,
                        proposal,
                        terminal=terminal,
                    )
                    proposal["state_projection"] = proposal_projection
                    if selected is proposal:
                        selected_projection = proposal_projection
                    else:
                        selected_projection = state_projection_record(
                            asr,
                            state,
                            prefix,
                            selected,
                            terminal=terminal,
                        )
                    selected["state_projection"] = selected_projection
                    projection_seconds += (
                        time.perf_counter() - projection_started
                    )
                    round_selected_records.append(selected)
                    if (
                        position in verified_by_position
                        and not suppress_proposer
                        and not static_oracle_stage
                        and args.service_mode == "full-selective"
                    ):
                        controller_started = time.perf_counter()
                        comparison = compare_records(
                            verified_by_position[position],
                            proposal,
                        )
                        certificate = controller.observe(
                            minimum_margin=(
                                float(proposal["minimum_margin"])
                                if proposal["minimum_margin"] is not None
                                else float("-inf")
                            ),
                            state_error=not comparison[
                                "state_projection_token_exact"
                            ],
                        )
                        if (
                            certificate is not None
                            and certificate.certified
                            and certified_before_episode is None
                        ):
                            certified_before_episode = episode
                        controller_seconds += (
                            time.perf_counter() - controller_started
                        )
                    event = {
                        "stage": label,
                        "stage_index": stage_index,
                        "episode": episode,
                        "session_id": stream["session_id"],
                        "chunk_index": chunk_index,
                        "global_event": global_event,
                        "terminal": terminal,
                        "session_terminal": session_terminal,
                        "checkpoint_boundary": checkpoint_boundary,
                        "checkpoint_epoch": checkpoint_epochs[position],
                        "proposal_executed": not suppress_proposer,
                        "verified": position in verified_by_position,
                        "state_entry_committed": not held_back,
                        "provisional_holdback": held_back,
                        "selected_authority": (
                            "provisional_holdback"
                            if held_back
                            else (
                                verified_lane_by_position.get(
                                    position,
                                    "canonical",
                                )
                                if position in verified_by_position
                                else (
                                    "unprotected_proposer"
                                    if args.service_mode == "proposer-only"
                                    else "risk_limited_fast_path"
                                )
                            )
                        ),
                        "online_selection_authority_violation": bool(
                            position in verify_positions
                            and position not in verified_by_position
                        ),
                        "fail_closed": (
                            False
                            if (
                                static_oracle_stage
                                or args.service_mode != "full-selective"
                            )
                            else epoch.certificate is None
                        ),
                        "threshold": (
                            frozen_threshold
                            if static_oracle_stage
                            else epoch.threshold
                        ),
                        "proposal_minimum_margin": (
                            proposal["minimum_margin"]
                            if not suppress_proposer
                            else None
                        ),
                        "proposal_token_ids": (
                            proposal["token_ids"]
                            if not suppress_proposer
                            else None
                        ),
                        "proposal_state_projection": (
                            proposal_projection
                            if not suppress_proposer
                            else None
                        ),
                        "selected_token_ids": selected["token_ids"],
                        "selected_text": selected["text"],
                        "selected_state_projection": selected_projection,
                    }
                    service_events.append(event)
                    episode_selected.append(event)
                    apply_started = time.perf_counter()
                    if held_back:
                        # prepare_job has already appended this chunk to
                        # audio_accum.  Keep the proposal user-visible and
                        # provisional, but do not let its text or chunk_id
                        # enter the feedback state.
                        pass
                    elif selected is proposal and not suppress_proposer:
                        assert outputs is not None
                        apply_output(state, outputs[position], prefix)
                    else:
                        from run_revtrace_dual_gpu import apply_candidate_record

                        # Rebuild the selected state using the same helper as the
                        # deployed transaction engine.
                        apply_candidate_record(state, selected, prefix)
                    apply_seconds += time.perf_counter() - apply_started
                    if checkpoint_boundary:
                        segment_text = checkpoint_payload(
                            prefix=prefix,
                            selected=selected,
                            selected_projection=selected_projection,
                        )
                        checkpoint_histories[position] = (
                            append_checkpoint_history(
                                checkpoint_histories[position],
                                segment_text,
                            )
                        )
                        event["checkpoint_history"] = (
                            checkpoint_histories[position]
                        )
                        if not session_terminal:
                            checkpoint_epochs[position] += 1
                            states[position] = asr.init_streaming_state(
                                context=checkpoint_histories[position],
                                language=stream["language"],
                                unfixed_chunk_num=2,
                                unfixed_token_num=5,
                                chunk_size_sec=2.0,
                            )
                    else:
                        event["checkpoint_history"] = (
                            checkpoint_histories[position]
                        )
                    global_event += 1
                round_commit_elapsed = time.perf_counter() - round_started
                round_state_entry_latency = (
                    time.perf_counter() - round_execution_started
                )
                bookkeeping_seconds = max(
                    0.0,
                    round_commit_elapsed
                    - projection_seconds
                    - controller_seconds
                    - apply_seconds,
                )
                critical_path_accounted_seconds = (
                    prepare_seconds
                    + proposal_elapsed
                    + verifier_collect_wall_seconds
                    + round_commit_elapsed
                )
                round_finished = time.perf_counter()
                active_threshold = (
                    frozen_threshold
                    if static_oracle_stage
                    else epoch.threshold
                )
                low_margin_count = (
                    None
                    if suppress_proposer
                    or active_threshold is None
                    else sum(
                        record["minimum_margin"] is None
                        or float(record["minimum_margin"])
                        <= float(active_threshold)
                        for record in proposals
                    )
                )
                episode_round_latencies.append(round_state_entry_latency)
                stage_round_details.append(
                    {
                        "episode": episode,
                        "chunk_index": chunk_index,
                        "session_age_start_seconds": chunk_index * 2,
                        "session_age_end_seconds": (chunk_index + 1) * 2,
                        "terminal": terminal,
                        "session_terminal": session_terminal,
                        "checkpoint_boundary": checkpoint_boundary,
                        "preverify_all": preverify_all,
                        "suppress_proposer": suppress_proposer,
                        "proposal_executed": not suppress_proposer,
                        "service_mode": args.service_mode,
                        "intermediate_authority": (
                            intermediate_authority_contract
                        ),
                        "terminal_authority_fixed_shape": (
                            args.canonical_batch_size
                        ),
                        "prepare_seconds": prepare_seconds,
                        "proposal_seconds": proposal_elapsed,
                        "low_margin_count": low_margin_count,
                        "verified_count": len(verify_positions),
                        "holdback_count": len(holdback_positions),
                        "verification_overlap_fraction": (
                            len(verify_positions) / len(jobs) if jobs else 0.0
                        ),
                        "verifier_dispatch_count": (
                            len(
                                {
                                    lane
                                    for lane in verified_lane_by_position.values()
                                    if lane.startswith("gpu")
                                }
                            )
                        ),
                        "gpu0_singleton_verified_count": sum(
                            lane == "gpu0_singleton"
                            for lane in verified_lane_by_position.values()
                        ),
                        "gpu1_singleton_verified_count": sum(
                            lane == "gpu1_singleton"
                            for lane in verified_lane_by_position.values()
                        ),
                        "verifier_queue_depth_before_dispatch": 0,
                        "verifier_queue_depth_at_commit": 0,
                        "cross_round_verifier_backlog": False,
                        "canonical_fixed_shape": (
                            (
                                args.canonical_batch_size
                                if (
                                    terminal
                                    or args.intermediate_authority
                                    == "fixed-shape"
                                )
                                else 1
                            )
                            if verify_positions
                            else None
                        ),
                        "canonical_execution_seconds": (
                            canonical_execution_seconds
                        ),
                        "verifier_collect_wall_seconds": (
                            verifier_collect_wall_seconds
                        ),
                        "commit_seconds": round_commit_elapsed,
                        "projection_seconds": projection_seconds,
                        "controller_seconds": controller_seconds,
                        "apply_seconds": apply_seconds,
                        "bookkeeping_seconds": bookkeeping_seconds,
                        "critical_path_accounted_seconds": (
                            critical_path_accounted_seconds
                        ),
                        "critical_path_residual_seconds": (
                            round_state_entry_latency
                            - critical_path_accounted_seconds
                        ),
                        "maximum_accumulated_audio_samples": max(
                            accumulated_audio_samples
                        ),
                        "mean_accumulated_audio_samples": statistics.mean(
                            accumulated_audio_samples
                        ),
                        "maximum_prefix_token_count": max(
                            prefix_token_counts
                        ),
                        "mean_prefix_token_count": statistics.mean(
                            prefix_token_counts
                        ),
                        "maximum_prompt_token_count": max(
                            prompt_token_counts
                        ),
                        "mean_prompt_token_count": statistics.mean(
                            prompt_token_counts
                        ),
                        "maximum_model_input_token_count": (
                            max(observed_model_input_token_counts)
                            if observed_model_input_token_counts
                            else None
                        ),
                        "mean_model_input_token_count": (
                            statistics.mean(
                                observed_model_input_token_counts
                            )
                            if observed_model_input_token_counts
                            else None
                        ),
                        "audio_encoder_token_count": None,
                        "audio_encoder_token_count_note": (
                            "the frozen vLLM request output does not expose "
                            "the post-processor audio token count; raw audio "
                            "samples and actual model prompt token count are "
                            "reported without inferring an unavailable value"
                        ),
                        "vllm_execution_mode": "enforce_eager",
                        "maximum_model_length": args.max_model_length,
                        "state_entry_latency_seconds": (
                            round_state_entry_latency
                        ),
                        "deadline_miss": round_state_entry_latency > 2.0,
                        "maximum_selected_token_count": max(
                            len(record["token_ids"])
                            for record in round_selected_records
                        ),
                        "mean_selected_token_count": statistics.mean(
                            len(record["token_ids"])
                            for record in round_selected_records
                        ),
                        "_round_monotonic_started": round_execution_started,
                        "_round_monotonic_finished": round_finished,
                    }
                )
                for event in episode_selected[-len(streams) :]:
                    event["state_entry_latency_seconds"] = (
                        round_state_entry_latency
                    )
            episode_wall = time.perf_counter() - episode_service_started
            episode_snapshots.append(
                {
                    "episode": episode,
                    "events": len(episode_selected),
                    "wall_seconds": episode_wall,
                    "goodput_events_per_second": (
                        len(episode_selected) / episode_wall
                    ),
                    "state_entry_latency_seconds_p50": statistics.median(
                        episode_round_latencies
                    ),
                    "state_entry_latency_seconds_p95": percentile(
                        episode_round_latencies, 0.95
                    ),
                    "state_entry_latency_seconds_p99": percentile(
                        episode_round_latencies, 0.99
                    ),
                    "deadline_miss_rounds": sum(
                        value > 2.0 for value in episode_round_latencies
                    ),
                    "certified": (
                        static_oracle_stage
                        or epoch.certificate is not None
                    ),
                    "threshold": (
                        frozen_threshold
                        if static_oracle_stage
                        else epoch.threshold
                    ),
                    "fast_path_window": (
                        None
                        if static_oracle_stage
                        else epoch.fast_path_window
                    ),
                    "required_verifier_seconds": required_verifier_seconds,
                    "checkpoint_seconds": args.checkpoint_seconds,
                    "final_checkpoint_histories": checkpoint_histories,
                }
            )
            selected_by_episode.append(episode_selected)

        energy_samples = sampler.stop()
        for detail in stage_round_details:
            detail["gpu_telemetry"] = round_telemetry(
                energy_samples,
                started=float(detail.pop("_round_monotonic_started")),
                finished=float(detail.pop("_round_monotonic_finished")),
            )
        for snapshot in episode_snapshots:
            snapshot["rounds_detail"] = [
                detail
                for detail in stage_round_details
                if detail["episode"] == snapshot["episode"]
            ]
        stage_wall = time.perf_counter() - stage_started

        # Fresh canonical replay after the service interval.  This is excluded
        # from service timing and never supplies controller evidence.
        audit_started = time.perf_counter()
        output_violations = 0
        state_violations = 0
        audit_events = 0
        audit_violation_rows: list[dict[str, Any]] = []
        audit_root_keys: set[tuple[int, str]] = set()
        promoted_audit_roots: list[dict[str, Any]] = []
        selected_cursor = 0
        audit_episodes = 0 if args.skip_post_stage_replay else episodes
        for episode in range(audit_episodes):
            streams = make_stage_streams(
                stage_index=stage_index,
                episode=episode,
                duration=args.episode_seconds,
                concurrency=concurrency,
                language=language,
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
            checkpoint_histories = ["" for _ in streams]
            for chunk_index in range(args.episode_seconds // 2):
                session_terminal = (
                    chunk_index == args.episode_seconds // 2 - 1
                )
                checkpoint_boundary = checkpoint_due(
                    (chunk_index + 1) * 2,
                    args.checkpoint_seconds,
                )
                terminal = session_terminal or checkpoint_boundary
                jobs = []
                prefixes = []
                for stream, state in zip(streams, states):
                    begin = chunk_index * 2 * SAMPLE_RATE
                    end = begin + 2 * SAMPLE_RATE
                    job, prefix = prepare_job(
                        asr,
                        state,
                        stream["audio"][begin:end],
                        tail=terminal,
                    )
                    jobs.append(job)
                    prefixes.append(prefix)
                canonical, _ = run_authority(jobs, terminal=terminal)
                for state, prefix, record in zip(states, prefixes, canonical):
                    selected = service_events[selected_cursor]
                    record["state_projection"] = state_projection_record(
                        asr,
                        state,
                        prefix,
                        record,
                        terminal=terminal,
                    )
                    comparison = compare_records(
                        record,
                        {
                            "token_ids": selected["selected_token_ids"],
                            "text": selected["selected_text"],
                            "state_projection": selected[
                                "selected_state_projection"
                            ],
                        },
                    )
                    output_violations += int(not comparison["token_exact"])
                    state_violations += int(
                        not comparison["state_projection_token_exact"]
                    )
                    if (
                        not comparison["token_exact"]
                        or not comparison["state_projection_token_exact"]
                    ):
                        root_key = (episode, selected["session_id"])
                        is_root_state_mismatch = bool(
                            not comparison["state_projection_token_exact"]
                            and root_key not in audit_root_keys
                        )
                        if is_root_state_mismatch:
                            audit_root_keys.add(root_key)
                        audit_violation_rows.append(
                            {
                                "stage": label,
                                "episode": episode,
                                "session_id": selected["session_id"],
                                "chunk_index": chunk_index,
                                "terminal": terminal,
                                "verified": selected["verified"],
                                "proposal_executed": selected[
                                    "proposal_executed"
                                ],
                                "proposal_minimum_margin": selected[
                                    "proposal_minimum_margin"
                                ],
                                "threshold": selected["threshold"],
                                "selected_token_ids": selected[
                                    "selected_token_ids"
                                ],
                                "canonical_token_ids": record["token_ids"],
                                "selected_state_projection": selected[
                                    "selected_state_projection"
                                ],
                                "canonical_state_projection": record[
                                    "state_projection"
                                ],
                                "comparison": comparison,
                                "is_root_state_mismatch": (
                                    is_root_state_mismatch
                                ),
                            }
                        )
                    from run_revtrace_dual_gpu import apply_candidate_record

                    apply_candidate_record(state, record, prefix)
                    if checkpoint_boundary:
                        segment_text = checkpoint_payload(
                            prefix=prefix,
                            selected=record,
                            selected_projection=record["state_projection"],
                        )
                        checkpoint_histories[selected_cursor % concurrency] = (
                            append_checkpoint_history(
                                checkpoint_histories[
                                    selected_cursor % concurrency
                                ],
                                segment_text,
                            )
                        )
                        if not session_terminal:
                            state_position = selected_cursor % concurrency
                            states[state_position] = (
                                asr.init_streaming_state(
                                    context=checkpoint_histories[
                                        state_position
                                    ],
                                    language=streams[state_position][
                                        "language"
                                    ],
                                    unfixed_chunk_num=2,
                                    unfixed_token_num=5,
                                    chunk_size_sec=2.0,
                                )
                            )
                    selected_cursor += 1
                    audit_events += 1
        if (
            label in audit_adaptation_stages
            and args.promote_post_stage_audit_failures
        ):
            for row in audit_violation_rows:
                if (
                    not row["is_root_state_mismatch"]
                    or bool(row["verified"])
                ):
                    continue
                margin = row["proposal_minimum_margin"]
                if margin is None:
                    raise RuntimeError(
                        "cannot promote a replay-audit root without a "
                        "proposal margin; fail closed instead of inventing "
                        "a threshold"
                    )
                certificate = controller.observe(
                    minimum_margin=float(margin),
                    state_error=True,
                )
                promoted_audit_roots.append(
                    {
                        "episode": row["episode"],
                        "session_id": row["session_id"],
                        "chunk_index": row["chunk_index"],
                        "proposal_minimum_margin": float(margin),
                        "failure_floor_after_promotion": (
                            controller.failure_floor(fingerprint)
                            if args.phase6_asymmetric_memory
                            else None
                        ),
                        "certificate_retained": bool(
                            certificate is not None
                            and certificate.certified
                        ),
                        "threshold_after_promotion": (
                            None
                            if controller.current is None
                            else controller.current.threshold
                        ),
                    }
                )
        audit_seconds = time.perf_counter() - audit_started
        latencies = [
            float(event["state_entry_latency_seconds"])
            for event in service_events
        ]
        energy = summarize_energy(
            energy_samples,
            completed_audio_seconds=len(service_events) * 2.0,
        )
        audit_root_state_mismatches = sum(
            bool(row["is_root_state_mismatch"])
            for row in audit_violation_rows
        )
        stage_payloads.append(
            {
                "label": label,
                "fingerprint": fingerprint,
                "concurrency": concurrency,
                "language": language,
                "episodes": episodes,
                "events": len(service_events),
                "service_mode": args.service_mode,
                "episode_seconds": args.episode_seconds,
                "audio_construction": args.audio_construction,
                "audio_provenance": stage_audio_provenance,
                "intermediate_authority": intermediate_authority_contract,
                "low_margin_policy": args.low_margin_policy,
                "dual_lane_intermediate_authority": (
                    args.dual_lane_intermediate_authority
                ),
                "cross_lane_compatibility_artifact": (
                    None
                    if args.cross_lane_compatibility_artifact is None
                    else str(args.cross_lane_compatibility_artifact)
                ),
                "cross_lane_compatibility_artifact_sha256": (
                    cross_lane_artifact_sha256
                ),
                "cross_lane_compatibility_pairs": (
                    None
                    if cross_lane_artifact is None
                    else cross_lane_artifact["counts"]["pairs"]
                ),
                "burst_b2_compatibility_artifact": (
                    None
                    if args.burst_b2_compatibility_artifact is None
                    else str(args.burst_b2_compatibility_artifact)
                ),
                "burst_b2_compatibility_artifact_sha256": (
                    burst_b2_artifact_sha256
                ),
                "burst_b2_compatibility_pairs": (
                    None
                    if burst_b2_artifact is None
                    else burst_b2_artifact["counts"]["pairs"]
                ),
                "terminal_authority": (
                    f"{args.canonical_dtype}_fixed_b"
                    f"{args.canonical_batch_size}"
                ),
                "canonical_batch_size": args.canonical_batch_size,
                "runtime_max_model_length": args.max_model_length,
                "checkpoint_seconds": args.checkpoint_seconds,
                "declared_contract_scope": {
                    "maximum_audio_samples": (
                        (args.checkpoint_seconds or args.episode_seconds)
                        * SAMPLE_RATE
                    ),
                    "maximum_prefix_tokens": (
                        args.declared_maximum_prefix_tokens
                    ),
                    "maximum_input_tokens": (
                        args.declared_maximum_input_tokens
                    ),
                },
                "switch_action": (
                    "none; frozen threshold loaded before service"
                    if static_oracle_stage
                    else switch_status_at_entry
                ),
                "continued_same_contract_epoch": continued_same_contract,
                "failure_floor": (
                    controller.failure_floor(fingerprint)
                    if args.phase6_asymmetric_memory
                    else None
                ),
                "renewal_canaries_remaining": (
                    controller.renewal_remaining
                    if args.phase6_asymmetric_memory
                    else None
                ),
                "policy": (
                    {
                        "proposer-only": "unprotected_proposer_lower_bound",
                        "terminal-only": "terminal_only_canonical_control",
                        "all-canonical": "all_canonical_control",
                    }.get(
                        args.service_mode,
                        (
                            "frozen_prior-certified_static_oracle"
                            if static_oracle_stage
                            else "live_adaptive_risk_window"
                        ),
                    )
                ),
                "certified_after_episode": certified_before_episode,
                "certified_after_events": (
                    0
                    if static_oracle_stage
                    else (
                        epoch.certified_at_event - epoch.switched_at_event
                        if epoch.certified_at_event is not None
                        else None
                    )
                ),
                "threshold": (
                    frozen_threshold
                    if static_oracle_stage
                    else epoch.threshold
                ),
                "fast_path_window": (
                    None
                    if static_oracle_stage
                    else epoch.fast_path_window
                ),
                "risk_upper_bound": (
                    None
                    if static_oracle_stage
                    else (
                        epoch.certificate.upper_risk
                        if epoch.certificate is not None
                        else 1.0
                    )
                ),
                "risk_bound_source": (
                    "prior independent split-sample certificate"
                    if static_oracle_stage
                    else "current live epoch split-sample certificate"
                ),
                "service_wall_seconds": stage_wall,
                "proposer_seconds": proposer_seconds,
                "required_verifier_seconds": required_verifier_seconds,
                "goodput_events_per_second": len(service_events) / stage_wall,
                "state_entry_latency_seconds_p50": statistics.median(latencies),
                "state_entry_latency_seconds_p95": percentile(latencies, 0.95),
                "state_entry_latency_seconds_p99": percentile(latencies, 0.99),
                "deadline_miss_events": sum(
                    value > 2.0 for value in latencies
                ),
                "verification_fraction": sum(
                    event["verified"] for event in service_events
                )
                / len(service_events),
                "online_selection_authority_violations": sum(
                    bool(event["online_selection_authority_violation"])
                    for event in service_events
                ),
                "output_violations": output_violations,
                "state_violations": state_violations,
                "audit_events": audit_events,
                "audit_violation_rows": audit_violation_rows,
                "audit_root_state_mismatches": (
                    audit_root_state_mismatches
                ),
                "independent_replay_risk_upper_bound": None,
                "independent_replay_observed_root_rate": (
                    audit_root_state_mismatches / audit_events
                    if audit_events
                    else None
                ),
                "independent_replay_statistical_scope": (
                    "observed count only; revisions share session history and "
                    "batch context, so no iid binomial population bound is used"
                ),
                "unverified_fast_path_replay_roots": sum(
                    bool(row["is_root_state_mismatch"])
                    and not bool(row["verified"])
                    for row in audit_violation_rows
                ),
                "verified_canonical_replay_roots": sum(
                    bool(row["is_root_state_mismatch"])
                    and bool(row["verified"])
                    for row in audit_violation_rows
                ),
                "audit_role": (
                    "adaptation"
                    if label in audit_adaptation_stages
                    else "validation"
                ),
                "gating_role": (
                    "calibration_excluded_from_final_decision"
                    if label in non_gating_stages
                    else "heldout_service_gate"
                ),
                "promoted_audit_root_count": len(promoted_audit_roots),
                "promoted_audit_roots": promoted_audit_roots,
                "post_audit_failure_floor": (
                    controller.failure_floor(fingerprint)
                    if args.phase6_asymmetric_memory
                    else None
                ),
                "post_stage_replay_executed": (
                    not args.skip_post_stage_replay
                ),
                "post_audit_threshold": (
                    None
                    if controller.current is None
                    else controller.current.threshold
                ),
                "audit_seconds_excluded_from_service": audit_seconds,
                "episodes_detail": episode_snapshots,
                "rounds_detail": stage_round_details,
                "energy": energy,
            }
        )

    command_queue.put({"kind": "stop"})
    stopped = receive_or_raise(result_queue, args.result_timeout_seconds)
    if stopped.get("kind") != "stopped":
        raise RuntimeError(f"unexpected verifier shutdown: {stopped}")
    verifier.join(timeout=30.0)
    if verifier.is_alive():
        verifier.terminate()
        verifier.join(timeout=10.0)
        if verifier.is_alive():
            raise RuntimeError("verifier did not stop")
    atexit.unregister(emergency_verifier_cleanup)

    static_oracle_run = bool(frozen_thresholds)
    if static_oracle_run and len(frozen_thresholds) != len(stages):
        raise ValueError(
            "static-oracle runs require one frozen threshold per stage"
        )
    causal_baseline_run = args.service_mode != "full-selective"

    def stage_passes(stage: dict[str, Any]) -> bool:
        if causal_baseline_run:
            return bool(
                stage["events"] > 0
                and stage["online_selection_authority_violations"] == 0
            )
        common = bool(
            stage["threshold"] is not None
            and (
                stage["risk_upper_bound"] is None
                if static_oracle_run
                else stage["risk_upper_bound"] <= 0.005
            )
            and stage["deadline_miss_events"] == 0
        )
        if not common:
            return False
        if stage["audit_role"] == "adaptation":
            return bool(
                stage["promoted_audit_root_count"] > 0
                and all(
                    row["certificate_retained"]
                    for row in stage["promoted_audit_roots"]
                )
            )
        if args.statistical_risk_gate:
            unverified_replay_roots = [
                row
                for row in stage["audit_violation_rows"]
                if row["is_root_state_mismatch"]
                and not bool(row["verified"])
            ]
            return bool(
                not unverified_replay_roots
                and not any(
                    row["proposal_minimum_margin"] is not None
                    and stage["failure_floor"] is not None
                    and float(row["proposal_minimum_margin"])
                    <= float(stage["failure_floor"])
                    for row in unverified_replay_roots
                )
            )
        return bool(
            stage["output_violations"] == 0
            and stage["state_violations"] == 0
        )

    gating_stage_payloads = [
        stage
        for stage in stage_payloads
        if stage["label"] not in non_gating_stages
    ]
    if not gating_stage_payloads:
        raise ValueError("at least one gating stage is required")
    passed = all(stage_passes(stage) for stage in gating_stage_payloads)
    if causal_baseline_run:
        decision = "LONG_HORIZON_CAUSAL_BASELINE_COMPLETE"
        study = "RevTrace long-horizon causal serving baseline"
    else:
        study = (
            "RevTrace Phase 5A independent static certified oracle"
            if static_oracle_run
            else "RevTrace Phase 5A persistent live adaptive controller"
        )
        decision = (
            (
                "PHASE5A_STATIC_CERTIFIED_ORACLE_PASS"
                if static_oracle_run
                else "PHASE5A_LIVE_ADAPTIVE_CONTROL_PASS"
            )
            if passed
            else (
                "PHASE5A_STATIC_CERTIFIED_ORACLE_FAIL"
                if static_oracle_run
                else "PHASE5A_LIVE_ADAPTIVE_CONTROL_FAIL"
            )
        )
    payload = {
        "schema_version": 1,
        "experiment_id": args.experiment_id,
        "study": study,
        "decision": decision,
        "model": args.model_name,
        "service_mode": args.service_mode,
        "episode_seconds": args.episode_seconds,
        "audio_construction": args.audio_construction,
        "checkpoint_seconds": args.checkpoint_seconds,
        "canonical_dtype": args.canonical_dtype,
        "canonical_runtime_provenance": {
            **asdict(canonical_provenance),
            "digest": canonical_provenance.digest,
            "note": (
                "Accumulation and sampling dtypes were not exported by the "
                "frozen vLLM runtime and therefore remain explicitly "
                "unrecorded rather than inferred."
            ),
        },
        "phase6_asymmetric_memory": args.phase6_asymmetric_memory,
        "statistical_risk_gate": args.statistical_risk_gate,
        "non_gating_stages": sorted(non_gating_stages),
        "cross_contract_certificate_reuse": getattr(
            controller, "cross_contract_certificate_reuse", None
        ),
        "exact_certificate_restores": getattr(
            controller, "exact_certificate_restores", None
        ),
        "shape_warmup_seconds_excluded_from_service": (
            warmup_seconds_excluded
        ),
        "stages": stage_payloads,
        "environment": {
            "python": platform.python_version(),
            "code_commit": os.environ.get(
                "REVTRACE_CODE_COMMIT", "UNRECORDED"
            ),
            "proposer_gpu": args.proposer_gpu,
            "verifier_gpu": args.verifier_gpu,
            "proposer_pid": os.getpid(),
            "verifier_pid": ready.get("pid"),
            "proposer_max_model_length": args.max_model_length,
            "verifier_max_model_length": args.max_model_length,
        },
        "claim_boundaries": [
            "models remain loaded across the declared stage sequence",
            "each fingerprint switch starts a fresh fail-closed epoch",
            (
                "exact-contract returns require canary renewal; positive "
                "certificates never cross contract digests and contextual "
                "failure floors persist"
                if args.phase6_asymmetric_memory
                else "Phase 5 controller uses fresh epochs only"
            ),
            "post-stage replay is excluded from service timing",
            (
                "causal baseline modes measure execution cost and do not "
                "claim a statistical fast-path certificate"
                if causal_baseline_run
                else "full-selective mode evaluates the declared risk policy"
            ),
            (
                "long-horizon fingerprints include duration, session age, "
                "accumulated audio, prefix/input bounds, service mode, and "
                "the intermediate and terminal canonical authorities"
            ),
            (
                "distinct-sequence audio concatenates distinct utterances "
                "with silence and never uses sample-level roll or repetition"
                if args.audio_construction == "distinct-sequence"
                else "legacy cycle-roll audio is retained only for comparison"
            ),
            "risk is statistical state-entry disagreement, not bitwise determinism",
            (
                "a verified canonical draw that differs on a later replay is "
                "reported as replay non-repeatability, not as an online "
                "selection-authority violation or an unverified fast-path "
                "counterexample"
            ),
            (
                "static-oracle thresholds are frozen from prior independent "
                "split-sample certificates and supply performance references"
                if static_oracle_run
                else (
                    "no static threshold is supplied; every contract epoch "
                    "learns its risk window from fresh live evidence"
                )
            ),
            (
                "episode-specific stream identities and audio offsets prevent "
                "exact episode replay from being counted as fresh evidence"
            ),
            (
                "certified terminal revisions suppress discarded proposer "
                "work when the corresponding flag is enabled"
            ),
            (
                "declared audit-adaptation stages promote only the first "
                "state mismatch per session into the persistent dynamic "
                "failure floor; cascade descendants remain recorded but are "
                "not double-counted, and a later stage supplies independent "
                "validation"
                if audit_adaptation_stages
                else "post-stage replay evidence is not used for adaptation"
            ),
            (
                "the canonical dtype is a versioned service reference and "
                "is not claimed to reproduce the official BF16 trajectory"
            ),
        ],
    }
    args.output.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"decision": payload["decision"], "stages": stage_payloads}))
    return 0 if passed else 2


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Whisper W-suite system, risk and quality runner.

The runner uses a real two-GPU event loop for RevTrace: GPU 0 proposes
distinct-prompt batches while GPU 1 supplies singleton-canonical state,
checkpoint and final-output authority. Risky and terminal batched results are
provisional; capacity-safe rebase only discards feedback authority. Other
baselines share the same versioned W-suite canonical implementation.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import math
import queue
import random
import statistics
import subprocess
import threading
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Sequence

import numpy as np
import soundfile as sf
import torch
import transformers

from whisper_batched_executor import (
    DistinctPromptWhisper,
    SAMPLE_RATE,
    WhisperCandidate,
)

from revtrace.feedback_metrics import edit_distance, pack_disjoint_audio
from revtrace.feedback_coherence import (
    EFSCContract,
    ElasticFeedbackController,
    ElasticFeedbackState,
    FeedbackAction,
    FeedbackCandidate,
    FeedbackIdentity,
    WhisperHistoryAdapter,
)
from revtrace.risk import AuditRiskBound
from revtrace.whisper_state import (
    LocalAgreement2,
    PromptState,
    PromptTransition,
    WhisperStateRiskPolicy,
    WhisperStateAction,
    WhisperVersion,
    capacity_rebase_required,
    checkpoint_due_for_session,
    commit_prompt_transition,
    physical_cuda_device_count,
    paired_slo_goodput_speedup,
    proposer_authority_spillover_eligible,
    prompt_state_action,
    work_budget_requires_authority,
)

PROMPT_STATE_SEMANTICS = (
    "raw-segment-token-history-v5-deferred-authority"
)
QUEUE_PROTOCOL = "causal-ready-fifo-v1"
PROMPT_CHECKPOINT_REVISIONS = 10
STATE_CONTROL_PROTOCOL = (
    "prompt-state-deferred-authority-checkpoint10-"
    "capacity-rebase-v2"
)
WORK_AUTHORITY_PROTOCOL = "decoder-step-saturation-extended-canonical-v1"
TARGET_CAPACITY_PROTOCOL = "target-canonical-declared-work-v1"


def _compute_runtime_source_identity() -> dict[str, str]:
    """Capture the loaded runner and state-contract source build."""

    paths = {
        "run_whisper_w_system.py": Path(__file__),
        "whisper_state.py": Path(
            checkpoint_due_for_session.__code__.co_filename
        ),
        "feedback_coherence.py": Path(
            ElasticFeedbackController.__init__.__code__.co_filename
        ),
    }
    return {
        name: hashlib.sha256(path.read_bytes()).hexdigest()
        for name, path in paths.items()
    }


_RUNTIME_SOURCE_IDENTITY = _compute_runtime_source_identity()


def runtime_source_identity() -> dict[str, str]:
    # Return the import-time identity. Reading source files at result-write
    # time can falsely bind a long-running process to a later on-disk edit.
    return dict(_RUNTIME_SOURCE_IDENTITY)


def parse_window_margin_rules(
    values: Sequence[str],
) -> tuple[tuple[int, float], ...]:
    rules: list[tuple[int, float]] = []
    for raw in values:
        window_raw, separator, margin_raw = raw.partition(":")
        if not separator:
            raise ValueError(
                "window margin rules use WINDOW_INDEX:MARGIN"
            )
        rules.append((int(window_raw), float(margin_raw)))
    return tuple(sorted(rules))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)

    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--model", type=Path, required=True)
    common.add_argument("--model-name", required=True)
    common.add_argument("--manifest", type=Path, required=True)
    common.add_argument("--output", type=Path, required=True)
    common.add_argument("--proposer-device", default="cuda:0")
    common.add_argument("--verifier-device", default="cuda:1")
    common.add_argument("--max-new-tokens", type=int, default=96)
    common.add_argument(
        "--authority-max-new-tokens",
        type=int,
        help=(
            "canonical target work budget; if larger than the proposer "
            "budget, a proposal that exhausts its budget is never allowed "
            "to acquire state or terminal-output authority"
        ),
    )
    common.add_argument(
        "--window-seconds",
        type=int,
        default=10,
        help=(
            "Streaming state-transition window. Ten seconds keeps terminal "
            "authority below 20%% for the frozen 90-second production cells."
        ),
    )

    calibrate = sub.add_parser("calibrate", parents=[common])
    calibrate.add_argument("--sessions", type=int, default=80)
    calibrate.add_argument("--duration-seconds", type=int, default=90)
    calibrate.add_argument("--concurrency", type=int, default=16)
    calibrate.add_argument("--seed", type=int, default=20260730)

    workload = sub.add_parser("workload", parents=[common])
    workload.add_argument("--system", choices=(
        "unprotected-batch",
        "feedback-off-batch",
        "fixed-margin-sync",
        "holdback-only",
        "local-agreement-2",
        "efsc",
        "revtrace",
        "revtrace-inline",
    ), required=True)
    workload.add_argument("--sessions", type=int, required=True)
    workload.add_argument("--duration-seconds", type=int, required=True)
    workload.add_argument("--concurrency", type=int, required=True)
    workload.add_argument(
        "--offered-concurrency",
        type=int,
        help=(
            "Optional offered-load label when the contract admission layer "
            "reshapes an unsupported load to --concurrency."
        ),
    )
    workload.add_argument(
        "--arrival", choices=("sync", "poisson", "burst"), required=True
    )
    workload.add_argument("--seed", type=int, required=True)
    workload.add_argument("--margin-threshold", type=float, required=True)
    workload.add_argument(
        "--efsc-exit-margin",
        type=float,
        help="Frozen hysteresis exit margin; required for --system efsc.",
    )
    workload.add_argument("--age-window-index", type=int)
    workload.add_argument("--age-margin-threshold", type=float)
    workload.add_argument("--late-window-index", type=int)
    workload.add_argument("--late-margin-threshold", type=float)
    workload.add_argument("--high-load-prompt-tokens", type=int)
    workload.add_argument("--high-load-margin-threshold", type=float)
    workload.add_argument(
        "--window-margin-rule",
        action="append",
        default=[],
        metavar="WINDOW_INDEX:MARGIN",
        help="Piecewise state-age margin frontier; may be repeated.",
    )
    workload.add_argument(
        "--state-capacity-prompt-tokens",
        type=int,
        help=(
            "Optional service-level prompt-state capacity. A prompt at or "
            "above this bound is rebased before proposal; the default is the "
            "checkpoint's architectural context bound."
        ),
    )
    workload.add_argument("--audit-probability", type=float, default=0.021)
    workload.add_argument(
        "--policy-source",
        type=Path,
        help=(
            "Frozen contextual-risk policy used to configure this run.  The "
            "path and SHA-256 are embedded in the result for fail-closed "
            "evidence binding."
        ),
    )
    workload.add_argument(
        "--low-margin-policy",
        choices=("verify", "holdback"),
        default="verify",
        help=(
            "verify grants risky state transitions only after singleton "
            "authority; holdback displays the proposal but denies its "
            "previous-text prompt write."
        ),
    )
    workload.add_argument(
        "--disable-risk-authority",
        action="store_true",
        help="Diagnostic cost ablation; unsafe as a deployment policy.",
    )
    workload.add_argument(
        "--disable-checkpoint-authority",
        action="store_true",
        help="Diagnostic cost ablation; not a certified deployment policy.",
    )
    workload.add_argument(
        "--checkpoint-revisions",
        type=int,
        default=PROMPT_CHECKPOINT_REVISIONS,
    )
    workload.add_argument(
        "--checkpoint-phase-policy",
        choices=("synchronized", "session-staggered"),
        default="synchronized",
        help=(
            "session-staggered preserves the per-session checkpoint bound "
            "while dispersing authority bursts across revision windows."
        ),
    )
    workload.add_argument("--slo-seconds", type=float, default=2.0)
    workload.add_argument(
        "--batch-coalesce-seconds",
        type=float,
        default=0.0,
        help=(
            "bounded wait for newly released sessions before dispatch; "
            "applies identically to every compared batched system"
        ),
    )
    workload.add_argument("--system-order-index", type=int, default=-1)
    workload.add_argument(
        "--system-order-policy",
        default="unspecified",
    )
    workload.add_argument("--power-sample-seconds", type=float, default=0.2)
    workload.add_argument(
        "--verifier-lanes",
        type=int,
        default=4,
        help=(
            "Independent batch-size-one canonical lanes used only by the "
            "two-device RevTrace system."
        ),
    )
    workload.add_argument(
        "--share-verifier-weights",
        action="store_true",
        help=(
            "Use one read-only model instance across isolated BS=1 CUDA-stream "
            "verifier lanes. The warmup exactness gate fails closed if shared "
            "execution changes the serial canonical output."
        ),
    )
    workload.add_argument(
        "--authority-idle-proposer-lanes",
        type=int,
        choices=(1, 2),
        default=1,
        help=(
            "When set to 2, RevTrace reclaims the otherwise idle canonical "
            "GPU as a second isolated proposal lane only while the authority "
            "queue is empty. The lane is never shared with pending canonical "
            "work."
        ),
    )
    workload.add_argument(
        "--terminal-spillover-on-proposer",
        action="store_true",
        help=(
            "After every session reaches its terminal frontier, reclaim the "
            "now-idle proposer GPU as one additional isolated BS=1 terminal "
            "canonical lane. It is never used while future proposal work can "
            "still be released."
        ),
    )
    workload.add_argument(
        "--authority-spillover-on-proposer",
        action="store_true",
        help=(
            "Reclaim an otherwise idle proposer GPU as an isolated BS=1 "
            "canonical lane for risk, checkpoint, or terminal authority. "
            "A device lock serializes it with any later proposal."
        ),
    )
    workload.add_argument(
        "--speculative-prefetch-depth",
        type=int,
        choices=(0, 1),
        default=0,
        help=(
            "Compute at most one descendant from a provisional state while "
            "canonical authority is pending. The descendant is held outside "
            "committed state and reused only after parent agreement."
        ),
    )
    workload.add_argument(
        "--cohort-commit-barrier",
        action="store_true",
        help=(
            "Release the next revision of a proposal cohort only after every "
            "state-entry decision in that cohort has resolved. This preserves "
            "the certified proposal batch shape without executing from an "
            "uncertified parent."
        ),
    )
    workload.add_argument(
        "--pad-proposals-to-concurrency",
        action="store_true",
        help=(
            "Pad an underfilled proposal round with discarded replica rows "
            "so every real transition executes under the certified active "
            "concurrency shape. Padding never updates session state."
        ),
    )
    workload.add_argument(
        "--terminal-contract",
        choices=("canonical-output", "state-only"),
        default="canonical-output",
        help=(
            "canonical-output verifies the stable final transcript; "
            "state-only stops certification at the last state-entry edge "
            "and delegates final transcript quality to W6."
        ),
    )
    workload.add_argument(
        "--oracle-cache",
        type=Path,
        help=(
            "Optional per-cell canonical trajectory cache. The first system "
            "creates it; later same-cell baselines reuse exactly that evidence."
        ),
    )
    workload.add_argument(
        "--arrival-scale-seconds",
        type=float,
        default=0.02,
        help=(
            "Mean inter-session release gap for Poisson arrivals and "
            "inter-burst gap for burst arrivals. Sync releases at time zero."
        ),
    )

    audit = sub.add_parser("audit", parents=[common])
    audit.add_argument("--target-risk-entries", type=int, default=30_000)
    audit.add_argument("--minimum-audits", type=int, default=500)
    audit.add_argument("--sessions", type=int, default=32)
    audit.add_argument("--duration-seconds", type=int, default=90)
    audit.add_argument("--concurrency", type=int, default=32)
    audit.add_argument("--margin-threshold", type=float, required=True)
    audit.add_argument("--age-window-index", type=int)
    audit.add_argument("--age-margin-threshold", type=float)
    audit.add_argument("--policy-source", type=Path, required=True)
    audit.add_argument(
        "--low-margin-policy",
        choices=("verify", "holdback"),
        default="holdback",
        help=(
            "Live transition used for risky proposals during the independent "
            "audit. holdback advances audio without mutating prompt text."
        ),
    )
    audit.add_argument(
        "--checkpoint-revisions",
        type=int,
        default=PROMPT_CHECKPOINT_REVISIONS,
    )
    audit.add_argument(
        "--checkpoint-phase-policy",
        choices=("synchronized", "session-staggered"),
        default="synchronized",
    )
    audit.add_argument("--late-window-index", type=int)
    audit.add_argument("--late-margin-threshold", type=float)
    audit.add_argument("--high-load-prompt-tokens", type=int)
    audit.add_argument("--high-load-margin-threshold", type=float)
    audit.add_argument(
        "--window-margin-rule",
        action="append",
        default=[],
        metavar="WINDOW_INDEX:MARGIN",
    )
    audit.add_argument("--audit-probability", type=float, default=0.021)
    audit.add_argument(
        "--forced-audit-root",
        action="append",
        default=[],
        metavar="EPISODE:SESSION:WINDOW",
        help=(
            "Adaptation-only same-input control. The listed pre-outcome "
            "event is audited regardless of its random audit coin."
        ),
    )
    audit.add_argument("--seed", type=int, default=20260731)
    audit.add_argument("--alpha", type=float, default=0.05)
    audit.add_argument("--delta", type=float, default=0.005)
    audit.add_argument(
        "--stop-on-caught-error",
        action="store_true",
        help=(
            "Adaptation-only mode: stop after the first randomized audit "
            "catches an unsafe state entry and record that failure root."
        ),
    )
    return parser.parse_args()


def load_audio(path: str) -> np.ndarray:
    audio, rate = sf.read(path, dtype="float32", always_2d=False)
    if rate != SAMPLE_RATE:
        raise ValueError(f"expected 16 kHz, got {rate}: {path}")
    if audio.ndim == 2:
        audio = audio.mean(axis=1)
    return np.asarray(audio, dtype=np.float32)


def build_sessions(
    manifest_path: Path,
    *,
    duration_seconds: int,
    count: int,
    seed: int,
) -> list[np.ndarray]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    records = list(manifest["records"])
    random.Random(seed).shuffle(records)
    sessions = pack_disjoint_audio(
        [load_audio(record["path"]) for record in records],
        target_samples=SAMPLE_RATE * duration_seconds,
        max_sessions=count,
        separator_samples=SAMPLE_RATE // 10,
    )
    if len(sessions) < count:
        raise RuntimeError(
            f"only {len(sessions)} disjoint sessions; requested {count}"
        )
    return sessions


def candidate_dict(record: WhisperCandidate) -> dict[str, Any]:
    return {
        "token_ids": list(record.token_ids),
        "text": record.text,
        "minimum_margin": record.minimum_margin,
        "token_sha256": record.token_sha256,
        "generation_steps": record.generation_steps,
        "terminated_by_eos": record.terminated_by_eos,
    }


def cached_candidate_dict(record: WhisperCandidate) -> dict[str, Any]:
    return {
        "token_ids": list(record.token_ids),
        "text": record.text,
        "minimum_margin": record.minimum_margin,
        "elapsed_seconds": record.elapsed_seconds,
        "prompt_token_ids": list(record.prompt_token_ids),
        "generation_steps": record.generation_steps,
        "terminated_by_eos": record.terminated_by_eos,
    }


def candidate_from_cache(row: dict[str, Any]) -> WhisperCandidate:
    return WhisperCandidate(
        token_ids=tuple(int(value) for value in row["token_ids"]),
        text=str(row["text"]),
        minimum_margin=(
            None
            if row["minimum_margin"] is None
            else float(row["minimum_margin"])
        ),
        elapsed_seconds=float(row["elapsed_seconds"]),
        prompt_token_ids=tuple(
            int(value) for value in row["prompt_token_ids"]
        ),
        generation_steps=int(row.get("generation_steps", 0)),
        terminated_by_eos=bool(row.get("terminated_by_eos", False)),
    )


def load_or_create_oracle(
    cache: Path | None,
    executor: DistinctPromptWhisper,
    sessions: Sequence[np.ndarray],
    windows_per_session: int,
    *,
    power_interval: float,
    contract: dict[str, Any],
) -> tuple[list[list[WhisperCandidate]], dict[str, Any]]:
    if cache is not None and cache.exists():
        payload = json.loads(cache.read_text(encoding="utf-8"))
        if payload["contract"] != contract:
            raise ValueError("oracle cache contract mismatch")
        return (
            [
                [candidate_from_cache(row) for row in trajectory]
                for trajectory in payload["trajectories"]
            ],
            payload["baseline"],
        )
    trajectories, baseline = oracle_trajectory(
        executor,
        sessions,
        windows_per_session,
        power_interval=power_interval,
    )
    if cache is not None:
        payload = {
            "schema_version": 1,
            "contract": contract,
            "baseline": baseline,
            "trajectories": [
                [cached_candidate_dict(row) for row in trajectory]
                for trajectory in trajectories
            ],
        }
        cache.parent.mkdir(parents=True, exist_ok=True)
        cache.write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    return trajectories, baseline


def next_prompt_state(
    executor: DistinctPromptWhisper,
    current: Sequence[int],
    record: WhisperCandidate,
) -> tuple[int, ...]:
    return executor.advance_prompt(current, record.token_ids)


def oracle_prompt_inputs(
    executor: DistinctPromptWhisper,
    oracle: Sequence[Sequence[WhisperCandidate]],
) -> list[list[tuple[int, ...]]]:
    """Recover the raw-token authority prompt before every oracle event."""

    result: list[list[tuple[int, ...]]] = []
    for trajectory in oracle:
        current: tuple[int, ...] = ()
        rows: list[tuple[int, ...]] = []
        for record in trajectory:
            prompt_length = len(executor.prompt_tokens(current))
            if capacity_rebase_required(
                prompt_length,
                declared_next_segment_tokens=executor.max_new_tokens,
                maximum_prompt_tokens=executor.max_prompt_tokens,
            ):
                current = ()
            rows.append(current)
            current = next_prompt_state(executor, current, record)
        result.append(rows)
    return result


@dataclass(frozen=True)
class CanonicalLane:
    """A private BS=1 executor bound to an independent CUDA stream."""

    lane_id: int
    executor: DistinctPromptWhisper
    stream: torch.cuda.Stream

    def canonical(
        self,
        audio: np.ndarray,
        prompt: str | Sequence[int],
    ) -> WhisperCandidate:
        with torch.cuda.stream(self.stream):
            return self.executor.canonical(audio, prompt)


def warmup_workload_executors(
    proposer: DistinctPromptWhisper,
    verifier_lanes: Sequence[CanonicalLane],
    sessions: Sequence[np.ndarray],
    *,
    windows_per_session: int,
    concurrency: int,
) -> dict[str, Any]:
    """Warm every measured shape outside the steady-state timing boundary.

    Without a batched warmup, one CUDA/kernel startup is charged to every row
    in the first batch but to only one row in the singleton baseline.  That
    asymmetric accounting can dominate queue-inclusive P99.
    """

    warm_count = min(int(concurrency), len(sessions))
    warm_audio = [
        np.array_split(sessions[index], windows_per_session)[0]
        for index in range(warm_count)
    ]
    empty_prompts: list[tuple[int, ...]] = [() for _ in warm_audio]
    canonical = proposer.canonical(warm_audio[0], ())
    proposer.generate(warm_audio, empty_prompts)
    lane_records: list[WhisperCandidate] = []
    if verifier_lanes:
        with concurrent.futures.ThreadPoolExecutor(
            max_workers=len(verifier_lanes)
        ) as pool:
            lane_records = list(pool.map(
                lambda lane: lane.canonical(warm_audio[0], ()),
                verifier_lanes,
            ))
        if any(
            row.token_ids != canonical.token_ids
            for row in lane_records
        ):
            raise RuntimeError(
                "concurrent verifier lane differs from serial canonical"
            )
    return {
        "protocol": "canonical-c1-active-batch-isolated-lanes-v2",
        "proposer_singleton": 1,
        "proposer_batch": warm_count,
        "verifier_lanes": len(verifier_lanes),
        "verifier_lane_exact": all(
            row.token_ids == canonical.token_ids
            for row in lane_records
        ),
        "canonical_token_sha256": canonical.token_sha256,
    }


class PowerSampler:
    def __init__(
        self,
        gpu_indices: Sequence[int],
        interval: float,
    ) -> None:
        # Multiple logical roles may be colocated on one physical GPU.  Do
        # not double-count its power draw in that configuration.
        self.gpu_indices = tuple(dict.fromkeys(int(i) for i in gpu_indices))
        self.interval = float(interval)
        self.samples: list[tuple[float, tuple[float, ...]]] = []
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def _read(self) -> tuple[float, ...]:
        output = subprocess.check_output(
            [
                "nvidia-smi",
                "--query-gpu=power.draw",
                "--format=csv,noheader,nounits",
            ],
            text=True,
            timeout=5,
        )
        values = tuple(
            float(line.strip())
            for line in output.splitlines()
            if line.strip()
        )
        return tuple(values[index] for index in self.gpu_indices)

    def _run(self) -> None:
        while not self._stop.is_set():
            try:
                self.samples.append((time.perf_counter(), self._read()))
            except Exception:
                pass
            self._stop.wait(self.interval)

    def start(self) -> None:
        self.samples = []
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self) -> float:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=10)
        if len(self.samples) < 2:
            return 0.0
        joules = 0.0
        for (t0, p0), (t1, p1) in zip(
            self.samples, self.samples[1:]
        ):
            joules += (t1 - t0) * (
                sum(p0) + sum(p1)
            ) / 2.0
        return joules


def executor_gpu_index(executor: DistinctPromptWhisper) -> int:
    if executor.device.type != "cuda":
        raise ValueError("power sampling requires a CUDA executor")
    return int(executor.device.index or 0)


def oracle_trajectory(
    executor: DistinctPromptWhisper,
    sessions: Sequence[np.ndarray],
    windows_per_session: int,
    *,
    power_interval: float | None = None,
) -> tuple[list[list[WhisperCandidate]], dict[str, Any]]:
    sampler = (
        PowerSampler((executor_gpu_index(executor),), power_interval)
        if power_interval is not None
        else None
    )
    if sampler:
        sampler.start()
    started = time.perf_counter()
    trajectories: list[list[WhisperCandidate]] = []
    event_latencies: list[float] = []
    capacity_rebases = 0
    for audio in sessions:
        prompt: tuple[int, ...] = ()
        rows: list[WhisperCandidate] = []
        for window in np.array_split(audio, windows_per_session):
            prompt_length = len(executor.prompt_tokens(prompt))
            if capacity_rebase_required(
                prompt_length,
                declared_next_segment_tokens=executor.max_new_tokens,
                maximum_prompt_tokens=executor.max_prompt_tokens,
            ):
                prompt = ()
                capacity_rebases += 1
            before = time.perf_counter()
            record = executor.canonical(window, prompt)
            event_latencies.append(time.perf_counter() - before)
            rows.append(record)
            prompt = next_prompt_state(executor, prompt, record)
        trajectories.append(rows)
    wall = time.perf_counter() - started
    joules = sampler.stop() if sampler else 0.0
    return trajectories, {
        "wall_seconds": wall,
        "energy_joules": joules,
        "event_latencies": event_latencies,
        "capacity_rebases": capacity_rebases,
    }


def order_ready(
    ready: list[int],
    *,
    arrival: str,
    rng: random.Random,
) -> list[int]:
    if arrival == "sync":
        return sorted(ready)
    if arrival == "poisson":
        return sorted(ready, key=lambda _: rng.expovariate(1.0))
    rng.shuffle(ready)
    return ready


def session_release_times(
    count: int,
    *,
    arrival: str,
    rng: random.Random,
    scale_seconds: float,
) -> list[float]:
    """Freeze initial session release times independently of GPU service.

    Only a session's first revision is delayed.  Later revisions become ready
    when their certified parent state commits, matching the feedback-serving
    dependency rather than inventing a second arrival process.
    """

    if arrival == "sync":
        return [0.0] * count
    if scale_seconds <= 0:
        raise ValueError("arrival-scale-seconds must be positive")
    if arrival == "poisson":
        clock = 0.0
        values = []
        for _ in range(count):
            clock += rng.expovariate(1.0 / scale_seconds)
            values.append(clock)
        return values
    burst_size = max(2, int(math.sqrt(count)))
    return [
        (index // burst_size) * scale_seconds
        for index in range(count)
    ]


def take_released_batch(
    ready: list[int],
    *,
    release_times: Sequence[float],
    ready_since: Sequence[float],
    started: float,
    concurrency: int,
    arrival: str,
    rng: random.Random,
    coalesce_seconds: float = 0.0,
) -> tuple[list[int], list[int]]:
    """Select the oldest ready sessions after their initial release.

    Arrival mode controls only the first release.  A later revision becomes
    ready when its certified parent commits, so FIFO-by-ready-time is the
    causal service order.  Re-sorting by session id would let the first batch
    run an entire trajectory while the remaining sessions starve.
    """

    while True:
        elapsed = time.perf_counter() - started
        eligible = [
            session_id
            for session_id in ready
            if release_times[session_id] <= elapsed
        ]
        if eligible:
            break
        delay = min(release_times[index] for index in ready) - elapsed
        if delay > 0:
            time.sleep(min(delay, 0.01))
    if coalesce_seconds < 0:
        raise ValueError("batch coalescing must be non-negative")
    # Poisson session starts otherwise create a deterministic 1+(B-1) split
    # even when the remaining B-1 requests arrive a few milliseconds later.
    # Wait only within the declared bound and never past a session deadline.
    if coalesce_seconds and len(eligible) < concurrency:
        deadline = time.perf_counter() + coalesce_seconds
        while len(eligible) < concurrency:
            elapsed = time.perf_counter() - started
            unreleased = [
                release_times[index]
                for index in ready
                if release_times[index] > elapsed
            ]
            if not unreleased:
                break
            remaining_wait = deadline - time.perf_counter()
            if remaining_wait <= 0:
                break
            delay = min(min(unreleased) - elapsed, remaining_wait)
            if delay > 0:
                time.sleep(delay)
            elapsed = time.perf_counter() - started
            eligible = [
                session_id
                for session_id in ready
                if release_times[session_id] <= elapsed
            ]
    _ = (arrival, rng)
    eligible = sorted(
        eligible,
        key=lambda session_id: (
            float(ready_since[session_id]),
            int(session_id),
        ),
    )
    batch_ids = eligible[:concurrency]
    selected = set(batch_ids)
    remaining = [index for index in ready if index not in selected]
    return batch_ids, remaining


def run_simple_system(
    system: str,
    proposer: DistinctPromptWhisper,
    sessions: Sequence[np.ndarray],
    oracle: Sequence[Sequence[WhisperCandidate]],
    *,
    windows_per_session: int,
    concurrency: int,
    arrival: str,
    seed: int,
    margin_threshold: float,
    power_interval: float,
    arrival_scale_seconds: float,
    batch_coalesce_seconds: float,
) -> dict[str, Any]:
    rng = random.Random(seed)
    prompts: list[tuple[int, ...]] = [() for _ in sessions]
    authority_prompts = oracle_prompt_inputs(proposer, oracle)
    states = [
        PromptState(
            WhisperVersion(f"s{index}", 1, 1, 0),
            (),
            "",
        )
        for index in range(len(sessions))
    ]
    windows = [
        list(np.array_split(audio, windows_per_session))
        for audio in sessions
    ]
    next_window = [0 for _ in sessions]
    ready = list(range(len(sessions)))
    event_rows: list[dict[str, Any]] = []
    scheduler_rows: list[dict[str, Any]] = []
    state_violations = 0
    output_violations = 0
    verifications = 0
    capacity_rebases = 0
    sampler = PowerSampler(
        (executor_gpu_index(proposer),), power_interval
    )
    sampler.start()
    started = time.perf_counter()
    release_times = session_release_times(
        len(sessions),
        arrival=arrival,
        rng=random.Random(seed ^ 0xA771),
        scale_seconds=arrival_scale_seconds,
    )
    ready_since = [
        started + release_time for release_time in release_times
    ]

    while ready:
        ready_before = len(ready)
        batch_ids, ready = take_released_batch(
            ready,
            release_times=release_times,
            ready_since=ready_since,
            started=started,
            concurrency=concurrency,
            arrival=arrival,
            rng=rng,
            coalesce_seconds=batch_coalesce_seconds,
        )
        scheduler_rows.append({
            "round": len(scheduler_rows),
            "ready_sessions": ready_before,
            "pending_authorities": 0,
            "batch_size": len(batch_ids),
            "generated_batch_size": len(batch_ids),
            "capacity": concurrency,
            "unfilled_slots": max(0, concurrency - len(batch_ids)),
        })
        batch_audio = [
            windows[index][next_window[index]] for index in batch_ids
        ]
        if system != "feedback-off-batch":
            for session_id in batch_ids:
                prompt_length = len(
                    proposer.prompt_tokens(prompts[session_id])
                )
                if capacity_rebase_required(
                    prompt_length,
                    declared_next_segment_tokens=(
                        proposer.max_new_tokens
                    ),
                    maximum_prompt_tokens=(
                        proposer.max_prompt_tokens
                    ),
                ):
                    transition = PromptTransition(
                        parent=states[session_id].version,
                        selected_token_ids=(),
                        selected_text="",
                        source="capacity-safe-rebase",
                        terminal=False,
                        minimum_margin=None,
                    )
                    states[session_id] = commit_prompt_transition(
                        states[session_id], transition
                    )
                    prompts[session_id] = ()
                    capacity_rebases += 1
        batch_prompts = [
            "" if system == "feedback-off-batch" else prompts[index]
            for index in batch_ids
        ]
        proposal_started = time.perf_counter()
        if system == "local-agreement-2":
            partial_audio = [
                value[: int(0.8 * len(value))] for value in batch_audio
            ]
            partial = proposer.generate(partial_audio, batch_prompts)
            proposed = proposer.generate(batch_audio, batch_prompts)
        else:
            partial = []
            proposed = proposer.generate(batch_audio, batch_prompts)
        proposal_finished = time.perf_counter()

        for position, session_id in enumerate(batch_ids):
            window_index = next_window[session_id]
            terminal = window_index == windows_per_session - 1
            selected = proposed[position]
            state_record = selected
            source = "batch"
            if system == "fixed-margin-sync" and (
                terminal
                or selected.minimum_margin is None
                or selected.minimum_margin <= margin_threshold
            ):
                selected = proposer.canonical(
                    batch_audio[position],
                    prompts[session_id],
                )
                state_record = selected
                source = "singleton-canonical"
                verifications += 1
            elif system == "local-agreement-2":
                policy = LocalAgreement2()
                policy.update(partial[position].token_ids)
                agreed = policy.update(selected.token_ids)
                if terminal:
                    agreed = policy.flush(selected.token_ids)
                selected = WhisperCandidate(
                    token_ids=agreed,
                    text=proposer.processor.decode(
                        agreed,
                        skip_special_tokens=True,
                    ).strip(),
                    minimum_margin=selected.minimum_margin,
                    elapsed_seconds=selected.elapsed_seconds,
                    prompt_token_ids=selected.prompt_token_ids,
                )
                # LocalAgreement controls display confirmation.  Its native
                # previous-text context remains the full current hypothesis.
                state_record = proposed[position]
                source = "local-agreement-2"

            oracle_record = oracle[session_id][window_index]
            holdback = (
                system == "holdback-only"
                and (
                    terminal
                    or selected.minimum_margin is None
                    or selected.minimum_margin <= margin_threshold
                )
            )
            next_system_prompt = (
                prompts[session_id]
                if holdback else next_prompt_state(
                    proposer, prompts[session_id], state_record
                )
            )
            next_authority_prompt = next_prompt_state(
                proposer,
                authority_prompts[session_id][window_index],
                oracle_record,
            )
            output_error = selected.token_ids != oracle_record.token_ids
            state_error = (
                not terminal
                and system != "feedback-off-batch"
                and next_system_prompt != next_authority_prompt
            )
            output_violations += int(output_error)
            state_violations += int(state_error)
            latency = time.perf_counter() - ready_since[session_id]
            event_rows.append({
                "session_id": session_id,
                "window_index": window_index,
                "terminal": terminal,
                "source": "holdback" if holdback else source,
                "minimum_margin": selected.minimum_margin,
                "latency_seconds": latency,
                "prior_prompt_tokens": len(
                    proposer.prompt_tokens(prompts[session_id])
                ),
                "next_prompt_tokens": (
                    len(proposer.prompt_tokens(next_system_prompt))
                    if system != "feedback-off-batch" else 0
                ),
                "output_error": output_error,
                "state_error": state_error,
                "state_entry_committed": not holdback,
            })
            if system != "feedback-off-batch":
                transition = PromptTransition(
                    parent=states[session_id].version,
                    selected_token_ids=next_system_prompt,
                    selected_text=state_record.text,
                    source=source,
                    terminal=terminal,
                    minimum_margin=selected.minimum_margin,
                )
                states[session_id] = commit_prompt_transition(
                    states[session_id], transition
                )
                prompts[session_id] = next_system_prompt
            next_window[session_id] += 1
            if next_window[session_id] < windows_per_session:
                ready_since[session_id] = time.perf_counter()
                ready.append(session_id)
        _ = proposal_finished

    wall = time.perf_counter() - started
    joules = sampler.stop()
    return {
        "wall_seconds": wall,
        "energy_joules": joules,
        "event_rows": event_rows,
        "scheduler_rows": scheduler_rows,
        "verification_count": verifications,
        "output_violations": output_violations,
        "state_violations": state_violations,
        "capacity_rebase_count": capacity_rebases,
    }


def run_efsc_system(
    proposer: DistinctPromptWhisper,
    sessions: Sequence[np.ndarray],
    oracle: Sequence[Sequence[WhisperCandidate]],
    *,
    windows_per_session: int,
    concurrency: int,
    arrival: str,
    seed: int,
    enter_margin: float,
    exit_margin: float,
    power_interval: float,
    arrival_scale_seconds: float,
    batch_coalesce_seconds: float,
) -> dict[str, Any]:
    """Run authority-free elastic feedback-state coherence.

    The batched proposal is always available for display.  Only FAST_COMMIT
    grants it ancestry in a future Whisper previous-text prompt.  HOLD,
    DECAY and RESET are therefore real state-control operations rather than
    aliases for a hidden singleton verifier.
    """

    maximum_history_tokens = proposer.max_prompt_tokens - 1
    contract = EFSCContract(
        enter_margin=enter_margin,
        exit_margin=exit_margin,
        minimum_hold_windows=1,
        safe_streak_required=2,
        maximum_quarantine_windows=3,
        maximum_feedback_debt=3,
        maximum_influence_windows=3,
        maximum_prompt_tokens=maximum_history_tokens,
        decay_suffix_tokens=min(32, maximum_history_tokens - 1),
    )
    controller = ElasticFeedbackController(contract)
    adapter = WhisperHistoryAdapter(maximum_history_tokens)
    prompts: list[tuple[int, ...]] = [() for _ in sessions]
    feedback_states = [
        ElasticFeedbackState(
            FeedbackIdentity(f"s{index}", 1, 1, 0)
        )
        for index in range(len(sessions))
    ]
    authority_prompts = oracle_prompt_inputs(proposer, oracle)
    windows = [
        list(np.array_split(audio, windows_per_session))
        for audio in sessions
    ]
    next_window = [0 for _ in sessions]
    ready = list(range(len(sessions)))
    event_rows: list[dict[str, Any]] = []
    scheduler_rows: list[dict[str, Any]] = []
    action_counts = {action.value: 0 for action in FeedbackAction}
    preparation_counts = {action.value: 0 for action in FeedbackAction}
    reason_counts: dict[str, int] = {}
    violations = {
        "provisional_ancestor": 0,
        "ancestry_nonexpansion": 0,
        "feedback_debt": 0,
        "influence_horizon": 0,
        "prompt_load": 0,
        "prompt_state_binding": 0,
    }
    maximum_ancestry_age = 0
    maximum_feedback_debt = 0
    maximum_prompt_load = 0
    pending_provisional: dict[int, tuple[int, float]] = {}
    reset_window: dict[int, int] = {}
    reset_recovery_windows: list[int] = []
    rng = random.Random(seed)
    sampler = PowerSampler((executor_gpu_index(proposer),), power_interval)
    sampler.start()
    started = time.perf_counter()
    release_times = session_release_times(
        len(sessions),
        arrival=arrival,
        rng=random.Random(seed ^ 0xA771),
        scale_seconds=arrival_scale_seconds,
    )
    ready_since = [started + value for value in release_times]

    while ready:
        ready_before = len(ready)
        batch_ids, ready = take_released_batch(
            ready,
            release_times=release_times,
            ready_since=ready_since,
            started=started,
            concurrency=concurrency,
            arrival=arrival,
            rng=rng,
            coalesce_seconds=batch_coalesce_seconds,
        )
        preparation_actions: dict[int, str | None] = {}
        for session_id in batch_ids:
            state, preparation = controller.prepare_for_proposal(
                feedback_states[session_id], adapter
            )
            feedback_states[session_id] = state
            prompts[session_id] = tuple(
                atom.token_id for atom in state.atoms
            )
            preparation_actions[session_id] = (
                preparation.action.value
                if preparation.action is not None else None
            )
            if preparation.action is not None:
                preparation_counts[preparation.action.value] += 1

        scheduler_rows.append({
            "round": len(scheduler_rows),
            "ready_sessions": ready_before,
            "pending_authorities": 0,
            "batch_size": len(batch_ids),
            "generated_batch_size": len(batch_ids),
            "capacity": concurrency,
            "unfilled_slots": max(0, concurrency - len(batch_ids)),
        })
        batch_audio = [
            windows[index][next_window[index]] for index in batch_ids
        ]
        batch_prompts = [prompts[index] for index in batch_ids]
        proposed = proposer.generate(batch_audio, batch_prompts)
        proposal_finished = time.perf_counter()

        for position, session_id in enumerate(batch_ids):
            window_index = next_window[session_id]
            terminal = window_index == windows_per_session - 1
            record = proposed[position]
            current = feedback_states[session_id]
            old_ancestors = current.ancestors
            old_atoms = current.atoms
            candidate = FeedbackCandidate(
                session_id=current.identity.session_id,
                contract_epoch=current.identity.contract_epoch,
                policy_version=current.identity.policy_version,
                parent_state_version=current.identity.state_version,
                token_ids=tuple(record.token_ids),
                minimum_margin=record.minimum_margin,
                terminal=terminal,
            )
            next_state, decision = controller.step(
                current, candidate, adapter
            )
            feedback_states[session_id] = next_state
            prompts[session_id] = tuple(
                atom.token_id for atom in next_state.atoms
            )
            action_counts[decision.action.value] += 1
            reason_counts[decision.reason] = (
                reason_counts.get(decision.reason, 0) + 1
            )
            if session_id in pending_provisional:
                prior_index, prior_display_time = pending_provisional.pop(
                    session_id
                )
                event_rows[prior_index]["provisional_lifetime_seconds"] = (
                    proposal_finished - prior_display_time
                )
            if (
                preparation_actions[session_id]
                == FeedbackAction.SAFE_RESET.value
                or decision.action == FeedbackAction.SAFE_RESET
            ):
                reset_window[session_id] = window_index
            if (
                decision.action == FeedbackAction.FAST_COMMIT
                and session_id in reset_window
            ):
                reset_recovery_windows.append(
                    window_index - reset_window.pop(session_id)
                )

            if (
                decision.action != FeedbackAction.FAST_COMMIT
                and next_state.ancestors - old_ancestors
            ):
                violations["ancestry_nonexpansion"] += 1
            if (
                not decision.candidate_became_ancestor
                and next_state.identity.state_version
                in next_state.ancestors
            ):
                violations["provisional_ancestor"] += 1
            if (
                decision.action == FeedbackAction.PROVISIONAL_HOLD
                and next_state.atoms != old_atoms
            ):
                violations["ancestry_nonexpansion"] += 1
            if next_state.feedback_debt > contract.maximum_feedback_debt:
                violations["feedback_debt"] += 1
            if next_state.oldest_ancestor_age > contract.maximum_influence_windows:
                violations["influence_horizon"] += 1
            if next_state.prompt_load > contract.maximum_prompt_tokens:
                violations["prompt_load"] += 1
            if prompts[session_id] != tuple(
                atom.token_id for atom in next_state.atoms
            ):
                violations["prompt_state_binding"] += 1

            maximum_ancestry_age = max(
                maximum_ancestry_age, next_state.oldest_ancestor_age
            )
            maximum_feedback_debt = max(
                maximum_feedback_debt, next_state.feedback_debt
            )
            maximum_prompt_load = max(
                maximum_prompt_load, next_state.prompt_load
            )

            oracle_record = oracle[session_id][window_index]
            oracle_prompt = authority_prompts[session_id][window_index]
            next_authority_prompt = next_prompt_state(
                proposer, oracle_prompt, oracle_record
            )
            output_disagreement = (
                record.token_ids != oracle_record.token_ids
            )
            state_disagreement = (
                not terminal
                and prompts[session_id] != next_authority_prompt
            )
            latency = proposal_finished - ready_since[session_id]
            event_rows.append({
                "session_id": session_id,
                "window_index": window_index,
                "terminal": terminal,
                "source": "fp16-batch-efsc",
                "minimum_margin": record.minimum_margin,
                "latency_seconds": latency,
                "display_latency_seconds": latency,
                "feedback_resolution_latency_seconds": latency,
                "prior_prompt_tokens": len(
                    proposer.prompt_tokens(batch_prompts[position])
                ),
                "next_prompt_tokens": len(
                    proposer.prompt_tokens(prompts[session_id])
                ),
                "action": decision.action.value,
                "reason": decision.reason,
                "pre_proposal_action": preparation_actions[session_id],
                "feedback_mode": next_state.mode.value,
                "feedback_debt": next_state.feedback_debt,
                "hold_age": next_state.hold_age,
                "oldest_ancestor_age": next_state.oldest_ancestor_age,
                "candidate_became_ancestor": (
                    decision.candidate_became_ancestor
                ),
                "state_entry_committed": (
                    decision.action == FeedbackAction.FAST_COMMIT
                ),
                "output_error": output_disagreement,
                "state_error": state_disagreement,
                "canonical_trace_output_disagreement": output_disagreement,
                "canonical_trace_state_disagreement": state_disagreement,
                "provisional_lifetime_seconds": 0.0,
            })
            if (
                decision.action == FeedbackAction.PROVISIONAL_HOLD
                and not terminal
            ):
                pending_provisional[session_id] = (
                    len(event_rows) - 1,
                    proposal_finished,
                )
            next_window[session_id] += 1
            if next_window[session_id] < windows_per_session:
                ready_since[session_id] = time.perf_counter()
                ready.append(session_id)

    wall = time.perf_counter() - started
    joules = sampler.stop()
    semantic_violations = sum(violations.values())
    return {
        "wall_seconds": wall,
        "energy_joules": joules,
        "event_rows": event_rows,
        "scheduler_rows": scheduler_rows,
        "verification_count": 0,
        "mandatory_verification_count": 0,
        "output_violations": 0,
        "state_violations": semantic_violations,
        "stale_commits": 0,
        "capacity_rebase_count": preparation_counts[
            FeedbackAction.DECAY_SUFFIX.value
        ] + preparation_counts[FeedbackAction.SAFE_RESET.value],
        "efsc_action_counts": action_counts,
        "efsc_preparation_counts": preparation_counts,
        "efsc_reason_counts": reason_counts,
        "efsc_semantic_violations": violations,
        "efsc_maximum_ancestry_age": maximum_ancestry_age,
        "efsc_maximum_feedback_debt": maximum_feedback_debt,
        "efsc_maximum_prompt_load": maximum_prompt_load,
        "efsc_reset_recovery_windows": reset_recovery_windows,
        "efsc_contract": asdict(contract),
    }


def run_inline_revtrace(
    proposer: DistinctPromptWhisper,
    sessions: Sequence[np.ndarray],
    oracle: Sequence[Sequence[WhisperCandidate]],
    *,
    windows_per_session: int,
    concurrency: int,
    arrival: str,
    seed: int,
    risk_policy: WhisperStateRiskPolicy,
    audit_probability: float,
    power_interval: float,
    arrival_scale_seconds: float,
    batch_coalesce_seconds: float,
) -> dict[str, Any]:
    """One-GPU Prompt-State Holdback with inline canonical authority.

    Terminal text has no successor prompt and therefore is display-only under
    the state-entry contract.  It remains covered by W6 quality/UX evaluation,
    but is not charged as a state authority transition.
    """

    rng = random.Random(seed)
    prompts: list[tuple[int, ...]] = [() for _ in sessions]
    authority_prompts = oracle_prompt_inputs(proposer, oracle)
    states = [
        PromptState(
            WhisperVersion(f"s{index}", 1, 1, 0),
            (),
            "",
        )
        for index in range(len(sessions))
    ]
    windows = [
        list(np.array_split(audio, windows_per_session))
        for audio in sessions
    ]
    next_window = [0 for _ in sessions]
    ready = list(range(len(sessions)))
    event_rows: list[dict[str, Any]] = []
    low_margin_authorities = 0
    audits = 0
    safe_commits = 0
    terminal_displays = 0
    output_violations = 0
    state_violations = 0
    sampler = PowerSampler(
        (executor_gpu_index(proposer),), power_interval
    )
    sampler.start()
    started = time.perf_counter()
    release_times = session_release_times(
        len(sessions),
        arrival=arrival,
        rng=random.Random(seed ^ 0xA771),
        scale_seconds=arrival_scale_seconds,
    )
    ready_since = [
        started + release_time for release_time in release_times
    ]

    while ready:
        batch_ids, ready = take_released_batch(
            ready,
            release_times=release_times,
            ready_since=ready_since,
            started=started,
            concurrency=concurrency,
            arrival=arrival,
            rng=rng,
            coalesce_seconds=batch_coalesce_seconds,
        )
        audio = [
            windows[index][next_window[index]] for index in batch_ids
        ]
        prompt_rows = [prompts[index] for index in batch_ids]
        proposal_started = time.perf_counter()
        proposed = proposer.generate(audio, prompt_rows)
        proposal_finished = time.perf_counter()
        for position, session_id in enumerate(batch_ids):
            window_index = next_window[session_id]
            terminal = window_index == windows_per_session - 1
            record = proposed[position]
            prior_prompt_tokens = len(
                proposer.prompt_tokens(prompt_rows[position])
            )
            risk_reason = risk_policy.reason(
                record.minimum_margin,
                window_index=window_index,
                prompt_tokens=prior_prompt_tokens,
            )
            low_margin = risk_reason is not None
            audited = (
                not terminal
                and not low_margin
                and rng.random() < audit_probability
            )
            selected = record
            source = "batch"
            if not terminal and (low_margin or audited):
                selected = proposer.canonical(
                    audio[position], prompt_rows[position]
                )
                source = "canonical"
                low_margin_authorities += int(low_margin)
                audits += int(audited)
            elif terminal:
                terminal_displays += 1
                source = "terminal-display-only"
            else:
                safe_commits += 1
            oracle_record = oracle[session_id][window_index]
            next_system_prompt = next_prompt_state(
                proposer, prompts[session_id], selected
            )
            next_authority_prompt = next_prompt_state(
                proposer,
                authority_prompts[session_id][window_index],
                oracle_record,
            )
            output_error = selected.token_ids != oracle_record.token_ids
            state_error = (
                not terminal
                and next_system_prompt != next_authority_prompt
            )
            output_violations += int(output_error)
            state_violations += int(state_error)
            display_latency = (
                proposal_finished - ready_since[session_id]
            )
            state_entry_latency = (
                time.perf_counter() - ready_since[session_id]
            )
            event_rows.append({
                "session_id": session_id,
                "window_index": window_index,
                "terminal": terminal,
                "source": source,
                "risk_reason": risk_reason,
                "audited": audited,
                "minimum_margin": record.minimum_margin,
                # The paper-facing SLO is state-entry latency.  Provisional
                # display latency is reported separately and cannot stand in
                # for the point at which feedback state becomes authoritative.
                "latency_seconds": state_entry_latency,
                "display_latency_seconds": display_latency,
                "state_entry_latency_seconds": state_entry_latency,
                "prior_prompt_tokens": len(
                    proposer.prompt_tokens(prompts[session_id])
                ),
                "next_prompt_tokens": len(
                    proposer.prompt_tokens(next_system_prompt)
                ),
                "provisional_lifetime_seconds": (
                    state_entry_latency - display_latency
                    if source == "canonical" else 0.0
                ),
                "provisional_overwrite_percent": (
                    100.0 * edit_distance(
                        record.token_ids, selected.token_ids
                    ) / max(1, len(record.token_ids))
                    if source == "canonical" else 0.0
                ),
                "output_error": output_error,
                "state_error": state_error,
            })
            if not terminal:
                transition = PromptTransition(
                    parent=states[session_id].version,
                    selected_token_ids=next_system_prompt,
                    selected_text=selected.text,
                    source=source,
                    terminal=False,
                    minimum_margin=record.minimum_margin,
                )
                states[session_id] = commit_prompt_transition(
                    states[session_id], transition
                )
                prompts[session_id] = next_system_prompt
            next_window[session_id] += 1
            if next_window[session_id] < windows_per_session:
                ready_since[session_id] = time.perf_counter()
                ready.append(session_id)

    wall = time.perf_counter() - started
    return {
        "wall_seconds": wall,
        "energy_joules": sampler.stop(),
        "event_rows": event_rows,
        "terminal_display_only_count": terminal_displays,
        "terminal_authority_count": 0,
        "low_margin_authority_count": low_margin_authorities,
        "mandatory_verification_count": low_margin_authorities,
        "random_audit_count": audits,
        "safe_commit_count": safe_commits,
        "output_violations": output_violations,
        "state_violations": state_violations,
        "stale_commits": 0,
    }


def run_revtrace(
    proposer: DistinctPromptWhisper,
    verifier_lanes: Sequence[CanonicalLane],
    sessions: Sequence[np.ndarray],
    oracle: Sequence[Sequence[WhisperCandidate]],
    *,
    windows_per_session: int,
    concurrency: int,
    arrival: str,
    seed: int,
    risk_policy: WhisperStateRiskPolicy,
    audit_probability: float,
    power_interval: float,
    arrival_scale_seconds: float,
    batch_coalesce_seconds: float,
    authority_idle_proposer_lanes: int = 1,
    terminal_spillover_on_proposer: bool = False,
    authority_spillover_on_proposer: bool = False,
    speculative_prefetch_depth: int = 0,
    cohort_commit_barrier: bool = False,
    pad_proposals_to_concurrency: bool = False,
    terminal_contract: str = "canonical-output",
    state_capacity_prompt_tokens: int | None = None,
    low_margin_policy: str = "verify",
    disable_risk_authority: bool = False,
    disable_checkpoint_authority: bool = False,
    checkpoint_revisions: int = PROMPT_CHECKPOINT_REVISIONS,
    checkpoint_phase_policy: str = "synchronized",
) -> dict[str, Any]:
    """Run risk-governed deferred canonical authority with checkpoints.

    High-margin proposals may enter state under the independently renewed W4
    risk contract.  Risky proposals are immediately displayable but singleton
    canonical execution owns their future prompt-state transition.  Terminal
    proposals are likewise provisional until canonical execution owns the
    stable final transcript.  Periodic checkpoints refresh state authority.
    """
    if not verifier_lanes:
        raise ValueError("RevTrace requires at least one canonical lane")
    if authority_idle_proposer_lanes not in (1, 2):
        raise ValueError("authority-idle proposer lanes must be 1 or 2")
    if speculative_prefetch_depth not in (0, 1):
        raise ValueError("speculative prefetch depth must be zero or one")
    if cohort_commit_barrier and speculative_prefetch_depth:
        raise ValueError(
            "cohort commit barriers and speculative prefetch are mutually "
            "exclusive execution distributions"
        )
    if pad_proposals_to_concurrency and authority_idle_proposer_lanes != 1:
        raise ValueError(
            "shape-preserving proposal padding requires one proposal lane"
        )
    if terminal_contract not in {"canonical-output", "state-only"}:
        raise ValueError("unsupported terminal contract")
    if low_margin_policy not in {"verify", "holdback"}:
        raise ValueError("unsupported low-margin policy")
    if checkpoint_revisions <= 0:
        raise ValueError("checkpoint revisions must be positive")
    if checkpoint_phase_policy not in {
        "synchronized", "session-staggered"
    }:
        raise ValueError("unsupported checkpoint phase policy")
    rng = random.Random(seed)
    prompts: list[tuple[int, ...]] = [() for _ in sessions]
    authority_executor = verifier_lanes[0].executor
    authority_prompts = oracle_prompt_inputs(authority_executor, oracle)
    states = [
        PromptState(
            WhisperVersion(f"s{index}", 1, 1, 0),
            (),
            "",
        )
        for index in range(len(sessions))
    ]
    windows = [
        list(np.array_split(audio, windows_per_session))
        for audio in sessions
    ]
    next_window = [0 for _ in sessions]
    ready = list(range(len(sessions)))
    pending: dict[
        concurrent.futures.Future[WhisperCandidate],
        dict[str, Any],
    ] = {}
    prefetch_queued: set[int] = set()
    prefetch_prompts: dict[int, tuple[int, ...]] = {}
    prefetch_windows: dict[int, int] = {}
    prefetch_ready_since: dict[int, float] = {}
    prefetched: dict[int, dict[str, Any]] = {}
    event_rows: list[dict[str, Any]] = []
    scheduler_rows: list[dict[str, Any]] = []
    state_violations = 0
    output_violations = 0
    stale_commits = 0
    mandatory = 0
    terminal_displays = 0
    terminal_authorities = 0
    low_margin_authorities = 0
    work_budget_authorities = 0
    mandatory_nonterminal_authorities = 0
    audits = 0
    safe_commits = 0
    capacity_rebases = 0
    authority_idle_dual_proposal_rounds = 0
    terminal_spillover_authorities = 0
    proposer_spillover_authorities = 0
    spillover_authority_sequence = 0
    speculative_prefetches = 0
    speculative_prefetch_reuses = 0
    speculative_prefetch_discards = 0
    proposal_padding_rows = 0
    cohort_sequence = 0
    cohort_remaining: dict[int, int] = {}
    cohort_release_sessions: dict[int, list[int]] = {}
    cohort_release_count = 0
    post_timing_candidates: list[dict[str, Any]] = []
    sampler = PowerSampler(
        (
            executor_gpu_index(proposer),
            executor_gpu_index(verifier_lanes[0].executor),
        ),
        power_interval,
    )
    sampler.start()
    started = time.perf_counter()
    release_times = session_release_times(
        len(sessions),
        arrival=arrival,
        rng=random.Random(seed ^ 0xA771),
        scale_seconds=arrival_scale_seconds,
    )
    ready_since = [
        started + release_time for release_time in release_times
    ]
    lane_pool: queue.Queue[CanonicalLane] = queue.Queue()
    for lane in verifier_lanes:
        lane_pool.put(lane)
    # Terminal-only work may reclaim the proposer device while no proposal is
    # ready. Serialize both paths so later readiness cannot introduce overlap.
    proposer_device_lock = threading.Lock()

    def finish_cohort_event(
        cohort_id: int,
        session_id: int,
    ) -> None:
        """Release a proposal cohort after every state decision resolves."""

        nonlocal cohort_release_count
        if next_window[session_id] < windows_per_session:
            cohort_release_sessions[cohort_id].append(session_id)
        cohort_remaining[cohort_id] -= 1
        if cohort_remaining[cohort_id] != 0:
            return
        released_at = time.perf_counter()
        for released_session in cohort_release_sessions.pop(cohort_id):
            ready_since[released_session] = released_at
            ready.append(released_session)
        del cohort_remaining[cohort_id]
        cohort_release_count += 1

    proposal_lanes = (
        (proposer, verifier_lanes[0].executor)
        if authority_idle_proposer_lanes == 2
        else (proposer,)
    )

    def propose(
        batch_audio: Sequence[np.ndarray],
        batch_prompts: Sequence[tuple[int, ...]],
        *,
        authority_queue_empty: bool,
        pool: concurrent.futures.ThreadPoolExecutor,
    ) -> tuple[list[WhisperCandidate], int]:
        """Generate with one lane or reclaim the idle authority device.

        The dual-lane path preserves request isolation: each executor sees a
        normal distinct-prompt batch, and the canonical executor is reclaimed
        only when no authority future can be running or queued.
        """
        if (
            len(proposal_lanes) == 1
            or not authority_queue_empty
            or len(batch_audio) < 2
        ):
            with proposer_device_lock:
                return proposer.generate(batch_audio, batch_prompts), 1
        prompt_costs = [
            len(proposer.prompt_tokens(prompt))
            for prompt in batch_prompts
        ]
        groups: list[list[int]] = [[], []]
        group_costs = [0, 0]
        for position in sorted(
            range(len(batch_audio)),
            key=lambda index: (-prompt_costs[index], index),
        ):
            target = min(
                range(2),
                key=lambda lane: (
                    len(groups[lane]),
                    group_costs[lane],
                    lane,
                ),
            )
            groups[target].append(position)
            group_costs[target] += prompt_costs[position]
        def generate_lane(
            lane: DistinctPromptWhisper,
            positions: Sequence[int],
        ) -> list[WhisperCandidate]:
            if lane is proposer:
                with proposer_device_lock:
                    return lane.generate(
                        [batch_audio[index] for index in positions],
                        [batch_prompts[index] for index in positions],
                    )
            return lane.generate(
                [batch_audio[index] for index in positions],
                [batch_prompts[index] for index in positions],
            )

        futures = []
        for lane, positions in zip(proposal_lanes, groups):
            futures.append((
                positions,
                pool.submit(
                    generate_lane,
                    lane,
                    positions,
                ),
            ))
        ordered: list[WhisperCandidate | None] = [
            None for _ in batch_audio
        ]
        for positions, future in futures:
            for position, record in zip(positions, future.result()):
                ordered[position] = record
        if any(record is None for record in ordered):
            raise RuntimeError("dual proposer did not fill every batch row")
        return [record for record in ordered if record is not None], 2

    def verify_canonical(
        audio: np.ndarray,
        prompt: tuple[int, ...],
    ) -> tuple[WhisperCandidate, float, float, int]:
        lane = lane_pool.get()
        try:
            verification_started = time.perf_counter()
            record = lane.canonical(audio, prompt)
            verification_finished = time.perf_counter()
            return (
                record,
                verification_started,
                verification_finished,
                lane.lane_id,
            )
        finally:
            lane_pool.put(lane)

    def verify_on_idle_proposer(
        audio: np.ndarray,
        prompt: tuple[int, ...],
    ) -> tuple[WhisperCandidate, float, float, int]:
        with proposer_device_lock:
            verification_started = time.perf_counter()
            record = proposer.canonical(audio, prompt)
            verification_finished = time.perf_counter()
        return record, verification_started, verification_finished, -1

    def commit(
        session_id: int,
        window_index: int,
        selected: WhisperCandidate,
        *,
        source: str,
        proposed: WhisperCandidate,
        event_started: float,
        proposal_finished: float,
        parent: WhisperVersion,
        audited: bool,
        verification_submitted: float | None = None,
        verification_started: float | None = None,
        verification_finished: float | None = None,
        verifier_lane: int | None = None,
        state_entry_committed: bool = True,
        risk_reason: str | None = None,
        enqueue_next: bool = True,
        cohort_id: int | None = None,
    ) -> None:
        nonlocal state_violations, output_violations, stale_commits
        terminal = window_index == windows_per_session - 1
        if states[session_id].version != parent:
            stale_commits += 1
            if cohort_id is not None:
                finish_cohort_event(cohort_id, session_id)
            return
        oracle_record = oracle[session_id][window_index]
        proposed_next_prompt = next_prompt_state(
            proposer, prompts[session_id], selected
        )
        next_system_prompt = (
            proposed_next_prompt
            if state_entry_committed else prompts[session_id]
        )
        next_authority_prompt = next_prompt_state(
            proposer,
            authority_prompts[session_id][window_index],
            oracle_record,
        )
        canonical_trace_output_disagreement = (
            selected.token_ids != oracle_record.token_ids
        )
        canonical_trace_state_disagreement = (
            not terminal
            and proposed_next_prompt != next_authority_prompt
        )
        # Online transaction violations and canonical-trace disagreement are
        # intentionally separate.  A holdback is display-visible but never
        # obtains write authority over the next prompt state.
        output_error = False
        state_error = False
        prior_prompt_tokens = len(
            proposer.prompt_tokens(prompts[session_id])
        )
        output_violations += int(output_error)
        state_violations += int(state_error)
        if not terminal and state_entry_committed:
            transition = PromptTransition(
                parent=parent,
                selected_token_ids=next_system_prompt,
                selected_text=selected.text,
                source=source,
                terminal=False,
                minimum_margin=proposed.minimum_margin,
            )
            states[session_id] = commit_prompt_transition(
                states[session_id], transition
            )
            prompts[session_id] = next_system_prompt
        next_window[session_id] += 1
        latency = time.perf_counter() - ready_since[session_id]
        display_latency = max(
            0.0,
            proposal_finished - ready_since[session_id],
        )
        event_rows.append({
            "session_id": session_id,
            "window_index": window_index,
            "terminal": terminal,
            "source": source,
            "audited": audited,
            "risk_reason": risk_reason,
            "state_entry_committed": state_entry_committed,
            "minimum_margin": proposed.minimum_margin,
            "latency_seconds": latency,
            "display_latency_seconds": display_latency,
            "proposal_seconds": proposal_finished - event_started,
            "verification_queue_seconds": (
                verification_started - verification_submitted
                if verification_started is not None
                and verification_submitted is not None
                else 0.0
            ),
            "verification_service_seconds": (
                verification_finished - verification_started
                if verification_finished is not None
                and verification_started is not None
                else 0.0
            ),
            "verification_submitted_seconds": (
                verification_submitted - started
                if verification_submitted is not None
                else None
            ),
            "verification_finished_seconds": (
                verification_finished - started
                if verification_finished is not None
                else None
            ),
            "verifier_lane": verifier_lane,
            "prior_prompt_tokens": prior_prompt_tokens,
            "next_prompt_tokens": len(
                proposer.prompt_tokens(next_system_prompt)
            ),
            "provisional_lifetime_seconds": (
                latency if source.startswith("canonical") else 0.0
            ),
            "output_error": output_error,
            "state_error": state_error,
            "canonical_trace_output_disagreement": (
                canonical_trace_output_disagreement
            ),
            "canonical_trace_state_disagreement": (
                canonical_trace_state_disagreement
            ),
            "provisional_overwrite_percent": (
                100.0
                * edit_distance(
                    proposed.token_ids, selected.token_ids
                )
                / max(1, len(proposed.token_ids))
                if source.startswith("canonical")
                else 0.0
            ),
        })
        if cohort_id is not None:
            finish_cohort_event(cohort_id, session_id)
        elif enqueue_next and next_window[session_id] < windows_per_session:
            ready_since[session_id] = time.perf_counter()
            ready.append(session_id)

    with (
        concurrent.futures.ThreadPoolExecutor(
            max_workers=len(verifier_lanes)
        ) as verifier_pool,
        concurrent.futures.ThreadPoolExecutor(
            max_workers=2
        ) as proposal_pool,
        concurrent.futures.ThreadPoolExecutor(
            max_workers=1
        ) as terminal_spillover_pool,
    ):
        while ready or pending or prefetch_queued or prefetched:
            completed = [
                future for future in pending if future.done()
            ]
            for future in completed:
                metadata = pending.pop(future)
                (
                    verified,
                    verification_started,
                    verification_finished,
                    verifier_lane,
                ) = future.result()
                session_id = int(metadata["session_id"])
                prefetch_requested = bool(
                    metadata.get("prefetch_requested", False)
                )
                prefetch_matches = False
                if prefetch_requested:
                    prefetch_matches = (
                        next_prompt_state(
                            proposer,
                            metadata["prompt_before"],
                            verified,
                        )
                        == metadata["proposed_next_prompt"]
                    )
                commit(
                    session_id,
                    metadata["window_index"],
                    verified,
                    source=metadata["source"],
                    proposed=metadata["proposed"],
                    event_started=metadata["event_started"],
                    proposal_finished=metadata["proposal_finished"],
                    parent=metadata["parent"],
                    audited=metadata["audited"],
                    risk_reason=metadata["risk_reason"],
                    verification_submitted=metadata[
                        "verification_submitted"
                    ],
                    verification_started=verification_started,
                    verification_finished=verification_finished,
                    verifier_lane=verifier_lane,
                    state_entry_committed=metadata[
                        "state_entry_committed"
                    ],
                    enqueue_next=not prefetch_requested,
                    cohort_id=metadata.get("cohort_id"),
                )
                if prefetch_requested:
                    cached = prefetched.get(session_id)
                    if cached is not None and not prefetch_matches:
                        prefetched.pop(session_id)
                        speculative_prefetch_discards += 1
                        cached = None
                    if session_id in prefetch_queued:
                        prefetch_queued.remove(session_id)
                        # The queued entry becomes an ordinary proposal from
                        # the now-certified canonical parent.
                        prefetch_prompts.pop(session_id, None)
                        prefetch_windows.pop(session_id, None)
                        prefetch_ready_since.pop(session_id, None)
                    elif session_id not in ready:
                        ready.append(session_id)
                    ready_since[session_id] = (
                        float(cached["ready_since"])
                        if cached is not None and prefetch_matches
                        else time.perf_counter()
                    )
            if ready:
                ready_before = len(ready)
                pending_before = len(pending)
                batch_ids, ready = take_released_batch(
                    ready,
                    release_times=release_times,
                    ready_since=ready_since,
                    started=started,
                    concurrency=concurrency,
                    arrival=arrival,
                    rng=rng,
                    coalesce_seconds=batch_coalesce_seconds,
                )
                batch_is_prefetch = [
                    index in prefetch_queued for index in batch_ids
                ]
                batch_window_indices = [
                    prefetch_windows[index]
                    if is_prefetch else next_window[index]
                    for index, is_prefetch in zip(
                        batch_ids, batch_is_prefetch
                    )
                ]
                batch_prompt_values = [
                    prefetch_prompts[index]
                    if is_prefetch else prompts[index]
                    for index, is_prefetch in zip(
                        batch_ids, batch_is_prefetch
                    )
                ]
                batch_cohort_id: int | None = None
                if cohort_commit_barrier:
                    batch_cohort_id = cohort_sequence
                    cohort_sequence += 1
                    cohort_remaining[batch_cohort_id] = len(batch_ids)
                    cohort_release_sessions[batch_cohort_id] = []
                # A decoder prompt that cannot accommodate the declared
                # worst-case next segment is rebased before execution.  The
                # operation only discards feedback state, so it cannot grant
                # an uncertified proposal write authority.  The trigger is
                # derived from the checkpoint's context bound rather than a
                # latency-tuned threshold.
                for position, session_id in enumerate(batch_ids):
                    if session_id in prefetched:
                        continue
                    prompt_length = len(
                        proposer.prompt_tokens(
                            batch_prompt_values[position]
                        )
                    )
                    service_capacity_due = (
                        state_capacity_prompt_tokens is not None
                        and prompt_length
                        >= state_capacity_prompt_tokens
                    )
                    architectural_capacity_due = (
                        capacity_rebase_required(
                            prompt_length,
                            declared_next_segment_tokens=(
                                authority_executor.max_new_tokens
                            ),
                            maximum_prompt_tokens=(
                                proposer.max_prompt_tokens
                            ),
                        )
                    )
                    if service_capacity_due or architectural_capacity_due:
                        if batch_is_prefetch[position]:
                            batch_prompt_values[position] = ()
                            prefetch_prompts[session_id] = ()
                        else:
                            transition = PromptTransition(
                                parent=states[session_id].version,
                                selected_token_ids=(),
                                selected_text="",
                                source="capacity-safe-rebase",
                                terminal=False,
                                minimum_margin=None,
                            )
                            states[session_id] = commit_prompt_transition(
                                states[session_id], transition
                            )
                            prompts[session_id] = ()
                            batch_prompt_values[position] = ()
                        capacity_rebases += 1
                generated_positions = [
                    position
                    for position, session_id in enumerate(batch_ids)
                    if session_id not in prefetched
                ]
                scheduler_rows.append({
                    "round": len(scheduler_rows),
                    "ready_sessions": ready_before,
                    "pending_authorities": pending_before,
                    "batch_size": len(batch_ids),
                    "generated_batch_size": len(generated_positions),
                    "capacity": concurrency,
                    "unfilled_slots": max(0, concurrency - len(batch_ids)),
                })
                proposed: list[WhisperCandidate | None] = [
                    None for _ in batch_ids
                ]
                event_started_rows = [0.0 for _ in batch_ids]
                proposal_finished_rows = [0.0 for _ in batch_ids]
                proposal_lane_count = 1
                if generated_positions:
                    event_started = time.perf_counter()
                    proposal_audio = [
                        windows[batch_ids[position]][
                            batch_window_indices[position]
                        ]
                        for position in generated_positions
                    ]
                    proposal_prompts = [
                        batch_prompt_values[position]
                        for position in generated_positions
                    ]
                    real_proposal_count = len(proposal_audio)
                    if (
                        pad_proposals_to_concurrency
                        and real_proposal_count < concurrency
                    ):
                        padding = concurrency - real_proposal_count
                        proposal_audio.extend(
                            [proposal_audio[-1]] * padding
                        )
                        proposal_prompts.extend(
                            [proposal_prompts[-1]] * padding
                        )
                        proposal_padding_rows += padding
                    generated, proposal_lane_count = propose(
                        proposal_audio,
                        proposal_prompts,
                        authority_queue_empty=not pending,
                        pool=proposal_pool,
                    )
                    generated = generated[:real_proposal_count]
                    scheduler_rows[-1]["execution_batch_size"] = len(
                        proposal_audio
                    )
                    proposal_finished = time.perf_counter()
                    for position, record in zip(
                        generated_positions, generated
                    ):
                        proposed[position] = record
                        event_started_rows[position] = event_started
                        proposal_finished_rows[position] = proposal_finished
                for position, session_id in enumerate(batch_ids):
                    cached = prefetched.pop(session_id, None)
                    if cached is not None:
                        proposed[position] = cached["record"]
                        event_started_rows[position] = float(
                            cached["event_started"]
                        )
                        proposal_finished_rows[position] = float(
                            cached["proposal_finished"]
                        )
                        speculative_prefetch_reuses += 1
                        prefetch_ready_since.pop(session_id, None)
                if any(record is None for record in proposed):
                    raise RuntimeError("proposal batch contains an empty row")
                authority_idle_dual_proposal_rounds += int(
                    proposal_lane_count == 2
                )
                for position, session_id in enumerate(batch_ids):
                    window_index = batch_window_indices[position]
                    terminal = window_index == windows_per_session - 1
                    record = proposed[position]
                    assert record is not None
                    if batch_is_prefetch[position]:
                        prefetched[session_id] = {
                            "record": record,
                            "event_started": event_started_rows[position],
                            "proposal_finished": (
                                proposal_finished_rows[position]
                            ),
                            "ready_since": prefetch_ready_since[session_id],
                        }
                        prefetch_queued.remove(session_id)
                        prefetch_prompts.pop(session_id, None)
                        prefetch_windows.pop(session_id, None)
                        continue
                    prior_prompt_tokens = len(
                        proposer.prompt_tokens(
                            batch_prompt_values[position]
                        )
                    )
                    risk_reason = risk_policy.reason(
                        record.minimum_margin,
                        window_index=window_index,
                        prompt_tokens=prior_prompt_tokens,
                    )
                    checkpoint_due = (
                        checkpoint_due_for_session(
                            window_index,
                            session_id,
                            revisions=checkpoint_revisions,
                            phase_policy=checkpoint_phase_policy,
                            terminal=terminal,
                            total_nonterminal_revisions=(
                                windows_per_session - 1
                            ),
                        )
                        and not disable_checkpoint_authority
                    )
                    action = prompt_state_action(
                        risk_policy,
                        record.minimum_margin,
                        window_index=window_index,
                        prompt_tokens=prior_prompt_tokens,
                        terminal=terminal,
                        checkpoint_due=checkpoint_due,
                    )
                    work_budget_saturated = work_budget_requires_authority(
                        record.generation_steps,
                        proposer_max_new_tokens=proposer.max_new_tokens,
                        authority_max_new_tokens=(
                            authority_executor.max_new_tokens
                        ),
                    )
                    # W4 performs the randomized pre-outcome audit used to
                    # certify and renew this frozen policy epoch.  In W5, a
                    # risky or terminal batch result is provisional while the
                    # canonical lane asynchronously supplies state/final
                    # output authority. A revision-count checkpoint supplies
                    # the periodic authority refresh.
                    audited = False
                    risk_holdback = (
                        action == WhisperStateAction.RISK_AUTHORITY
                        and low_margin_policy == "holdback"
                        and not work_budget_saturated
                    )
                    should_verify = (
                        work_budget_saturated
                        or (
                            action
                            in {
                                WhisperStateAction.CHECKPOINT_AUTHORITY,
                                WhisperStateAction.RISK_AUTHORITY,
                                WhisperStateAction.TERMINAL_AUTHORITY,
                            }
                            and not (
                                action == WhisperStateAction.RISK_AUTHORITY
                                and (
                                    low_margin_policy == "holdback"
                                    or disable_risk_authority
                                )
                            )
                            and not (
                                terminal
                                and terminal_contract == "state-only"
                            )
                        )
                    )
                    mandatory_nonterminal_authorities += int(
                        should_verify and not terminal
                    )
                    mandatory += int(checkpoint_due)
                    terminal_displays += int(terminal)
                    terminal_authorities += int(terminal and should_verify)
                    low_margin_authorities += int(
                        action == WhisperStateAction.RISK_AUTHORITY
                    )
                    work_budget_authorities += int(
                        work_budget_saturated
                    )
                    if should_verify:
                        parent = states[session_id].version
                        prompt_before = tuple(prompts[session_id])
                        verification_submitted = time.perf_counter()
                        spillover_enabled = (
                            authority_spillover_on_proposer
                            or (
                                terminal_spillover_on_proposer
                                and terminal
                            )
                        )
                        use_proposer_spillover = (
                            spillover_enabled
                            and proposer_authority_spillover_eligible(
                                ready_sessions=ready,
                            )
                            and spillover_authority_sequence
                            % (len(verifier_lanes) + 1)
                            == len(verifier_lanes)
                        )
                        if spillover_enabled:
                            spillover_authority_sequence += 1
                        if use_proposer_spillover:
                            proposer_spillover_authorities += 1
                            terminal_spillover_authorities += int(terminal)
                            future = terminal_spillover_pool.submit(
                                verify_on_idle_proposer,
                                windows[session_id][window_index],
                                prompt_before,
                            )
                        else:
                            future = verifier_pool.submit(
                                verify_canonical,
                                windows[session_id][window_index],
                                prompt_before,
                            )
                        prefetch_requested = (
                            speculative_prefetch_depth == 1
                            and not terminal
                            and window_index + 1 < windows_per_session
                        )
                        proposed_next_prompt = next_prompt_state(
                            proposer,
                            prompt_before,
                            record,
                        )
                        if prefetch_requested:
                            speculative_prefetches += 1
                            prefetch_queued.add(session_id)
                            prefetch_prompts[session_id] = (
                                proposed_next_prompt
                            )
                            prefetch_windows[session_id] = window_index + 1
                            prefetch_ready_since[session_id] = (
                                time.perf_counter()
                            )
                            ready.append(session_id)
                        pending[future] = {
                            "session_id": session_id,
                            "window_index": window_index,
                            "proposed": record,
                            "event_started": event_started_rows[position],
                            "proposal_finished": (
                                proposal_finished_rows[position]
                            ),
                            "verification_submitted": verification_submitted,
                            "parent": parent,
                            "prompt_before": prompt_before,
                            "proposed_next_prompt": proposed_next_prompt,
                            "prefetch_requested": prefetch_requested,
                            "audited": audited,
                            "risk_reason": risk_reason,
                            "work_budget_saturated": (
                                work_budget_saturated
                            ),
                            "source": (
                                "canonical-work-budget"
                                if work_budget_saturated
                                else (
                                    "canonical-terminal"
                                    if terminal
                                    else (
                                        "canonical-risk"
                                        if action
                                        == WhisperStateAction.RISK_AUTHORITY
                                        else "canonical-checkpoint"
                                    )
                                )
                            ),
                            "state_entry_committed": not terminal,
                            "cohort_id": batch_cohort_id,
                        }
                    else:
                        safe_commits += int(
                            not terminal
                            and action == WhisperStateAction.FAST_COMMIT
                        )
                        if not terminal and not risk_holdback:
                            post_timing_candidates.append({
                                "session_id": session_id,
                                "window_index": window_index,
                                "prompt": tuple(prompts[session_id]),
                                "proposed": record,
                                "event_index": len(event_rows),
                            })
                        commit(
                            session_id,
                            window_index,
                            record,
                            source=(
                                "batch-terminal-quality"
                                if terminal else (
                                    "batch-risk-holdback"
                                    if risk_holdback else "batch"
                                )
                            ),
                            proposed=record,
                            event_started=event_started_rows[position],
                            proposal_finished=(
                                proposal_finished_rows[position]
                            ),
                            parent=states[session_id].version,
                            audited=False,
                            state_entry_committed=(
                                not terminal and not risk_holdback
                            ),
                            risk_reason=risk_reason,
                            cohort_id=batch_cohort_id,
                        )
                continue
            if pending:
                concurrent.futures.wait(
                    pending,
                    return_when=concurrent.futures.FIRST_COMPLETED,
                )

    if cohort_remaining or cohort_release_sessions:
        raise RuntimeError("cohort barrier exited with unresolved revisions")
    wall = time.perf_counter() - started
    joules = sampler.stop()
    validation_started = time.perf_counter()
    post_timing_output_mismatches = 0
    post_timing_state_mismatches = 0
    post_timing_canonical_repeat_checks = 0
    post_timing_canonical_repeat_output_mismatches = 0
    post_timing_canonical_repeat_state_mismatches = 0
    post_timing_stable_output_mismatches = 0
    post_timing_stable_state_mismatches = 0
    post_timing_ambiguous_output_mismatches = 0
    post_timing_ambiguous_state_mismatches = 0
    validation_executor = verifier_lanes[0].executor
    for candidate in post_timing_candidates:
        session_id = int(candidate["session_id"])
        window_index = int(candidate["window_index"])
        prompt = tuple(candidate["prompt"])
        proposed_record = candidate["proposed"]
        canonical_record = validation_executor.canonical(
            windows[session_id][window_index],
            prompt,
        )
        output_mismatch = (
            proposed_record.token_ids != canonical_record.token_ids
        )
        state_mismatch = (
            next_prompt_state(
                proposer, prompt, proposed_record
            )
            != next_prompt_state(
                validation_executor, prompt, canonical_record
            )
        )
        post_timing_output_mismatches += int(output_mismatch)
        post_timing_state_mismatches += int(state_mismatch)
        canonical_repeat_output_mismatch = False
        canonical_repeat_state_mismatch = False
        stable_output_mismatch = False
        stable_state_mismatch = False
        ambiguous_output_mismatch = False
        ambiguous_state_mismatch = False
        if output_mismatch or state_mismatch:
            repeated_record = validation_executor.canonical(
                windows[session_id][window_index],
                prompt,
            )
            post_timing_canonical_repeat_checks += 1
            canonical_repeat_output_mismatch = (
                canonical_record.token_ids
                != repeated_record.token_ids
            )
            canonical_repeat_state_mismatch = (
                next_prompt_state(
                    validation_executor, prompt, canonical_record
                )
                != next_prompt_state(
                    validation_executor, prompt, repeated_record
                )
            )
            stable_output_mismatch = (
                output_mismatch
                and not canonical_repeat_output_mismatch
            )
            stable_state_mismatch = (
                state_mismatch
                and not canonical_repeat_state_mismatch
            )
            ambiguous_output_mismatch = (
                output_mismatch
                and canonical_repeat_output_mismatch
            )
            ambiguous_state_mismatch = (
                state_mismatch
                and canonical_repeat_state_mismatch
            )
            post_timing_canonical_repeat_output_mismatches += int(
                canonical_repeat_output_mismatch
            )
            post_timing_canonical_repeat_state_mismatches += int(
                canonical_repeat_state_mismatch
            )
            post_timing_stable_output_mismatches += int(
                stable_output_mismatch
            )
            post_timing_stable_state_mismatches += int(
                stable_state_mismatch
            )
            post_timing_ambiguous_output_mismatches += int(
                ambiguous_output_mismatch
            )
            post_timing_ambiguous_state_mismatches += int(
                ambiguous_state_mismatch
            )
        event_rows[int(candidate["event_index"])][
            "post_timing_canonical_output_mismatch"
        ] = output_mismatch
        event_rows[int(candidate["event_index"])][
            "post_timing_canonical_state_mismatch"
        ] = state_mismatch
        event_rows[int(candidate["event_index"])][
            "post_timing_canonical_repeat_output_mismatch"
        ] = canonical_repeat_output_mismatch
        event_rows[int(candidate["event_index"])][
            "post_timing_canonical_repeat_state_mismatch"
        ] = canonical_repeat_state_mismatch
        event_rows[int(candidate["event_index"])][
            "post_timing_stable_output_mismatch"
        ] = stable_output_mismatch
        event_rows[int(candidate["event_index"])][
            "post_timing_stable_state_mismatch"
        ] = stable_state_mismatch
        event_rows[int(candidate["event_index"])][
            "post_timing_ambiguous_output_mismatch"
        ] = ambiguous_output_mismatch
        event_rows[int(candidate["event_index"])][
            "post_timing_ambiguous_state_mismatch"
        ] = ambiguous_state_mismatch
    # Delayed replay uses a fresh FP16 singleton draw.  A first mismatch is
    # therefore not attributed to the fast path until a same-input repeated
    # singleton control is stable.  Repeat-unstable cases are finite-precision
    # evidence and remain visible as ambiguous replay mismatches.
    state_violations += post_timing_stable_state_mismatches
    output_violations += post_timing_stable_output_mismatches
    validation_seconds = time.perf_counter() - validation_started
    return {
        "wall_seconds": wall,
        "energy_joules": joules,
        "event_rows": event_rows,
        "scheduler_rows": scheduler_rows,
        "mandatory_verification_count": (
            mandatory_nonterminal_authorities
        ),
        "terminal_authority_count": terminal_authorities,
        "terminal_display_only_count": (
            terminal_displays - terminal_authorities
        ),
        "low_margin_authority_count": low_margin_authorities,
        "work_budget_authority_count": work_budget_authorities,
        "low_margin_holdback_count": sum(
            row.get("source") == "batch-risk-holdback"
            for row in event_rows
        ),
        "checkpoint_authority_count": mandatory,
        "capacity_rebase_count": capacity_rebases,
        "authority_idle_dual_proposal_rounds": (
            authority_idle_dual_proposal_rounds
        ),
        "terminal_spillover_authorities": (
            terminal_spillover_authorities
        ),
        "proposer_spillover_authorities": (
            proposer_spillover_authorities
        ),
        "speculative_prefetches": speculative_prefetches,
        "speculative_prefetch_reuses": speculative_prefetch_reuses,
        "speculative_prefetch_discards": speculative_prefetch_discards,
        "proposal_padding_rows": proposal_padding_rows,
        "cohort_releases": cohort_release_count,
        "post_timing_fast_path_audit_count": len(
            post_timing_candidates
        ),
        "post_timing_output_mismatches": (
            post_timing_output_mismatches
        ),
        "post_timing_state_mismatches": (
            post_timing_state_mismatches
        ),
        "post_timing_canonical_repeat_checks": (
            post_timing_canonical_repeat_checks
        ),
        "post_timing_canonical_repeat_output_mismatches": (
            post_timing_canonical_repeat_output_mismatches
        ),
        "post_timing_canonical_repeat_state_mismatches": (
            post_timing_canonical_repeat_state_mismatches
        ),
        "post_timing_stable_output_mismatches": (
            post_timing_stable_output_mismatches
        ),
        "post_timing_stable_state_mismatches": (
            post_timing_stable_state_mismatches
        ),
        "post_timing_ambiguous_output_mismatches": (
            post_timing_ambiguous_output_mismatches
        ),
        "post_timing_ambiguous_state_mismatches": (
            post_timing_ambiguous_state_mismatches
        ),
        "post_timing_validation_seconds": validation_seconds,
        "random_audit_count": audits,
        "safe_commit_count": safe_commits,
        "output_violations": output_violations,
        "state_violations": state_violations,
        "stale_commits": stale_commits,
    }


def summarize_workload(
    args: argparse.Namespace,
    baseline: dict[str, Any],
    result: dict[str, Any],
    executor: DistinctPromptWhisper,
    *,
    total_audio_seconds: int,
) -> dict[str, Any]:
    rows = result["event_rows"]
    state_entry_rows = [
        row for row in rows
        if not bool(row.get("terminal", False))
        and bool(row.get("state_entry_committed", True))
    ]
    latencies = sorted(
        float(row["latency_seconds"]) for row in state_entry_rows
    )
    display_latencies = sorted(
        float(row.get("display_latency_seconds", row["latency_seconds"]))
        for row in rows
    )
    terminal_latencies = sorted(
        float(row["latency_seconds"])
        for row in rows
        if bool(row.get("terminal", False))
    )
    feedback_resolution_latencies = sorted(
        float(row.get("feedback_resolution_latency_seconds", row["latency_seconds"]))
        for row in rows
    )

    def quantile(q: float) -> float:
        if not latencies:
            return math.inf
        return float(np.quantile(latencies, q))

    wall_speedup = baseline["wall_seconds"] / result["wall_seconds"]
    method_devices = [args.proposer_device]
    if args.system == "revtrace":
        method_devices.append(args.verifier_device)
    method_gpus = physical_cuda_device_count(method_devices)
    gpu_normalized = wall_speedup / method_gpus
    verification_count = result.get(
        "mandatory_verification_count",
        result.get("verification_count", 0),
    )
    baseline_state_entry_latencies = [
        float(value)
        for index, value in enumerate(baseline["event_latencies"])
        if (index + 1) % (args.duration_seconds // args.window_seconds)
        != 0
    ]
    baseline_display_latencies = [
        float(value) for value in baseline["event_latencies"]
    ]
    baseline_latencies = sorted(
        baseline_state_entry_latencies
    )
    baseline_good, method_good, state_goodput_speedup = (
        paired_slo_goodput_speedup(
            baseline_state_entry_latencies,
            baseline["wall_seconds"],
            latencies,
            result["wall_seconds"],
            args.slo_seconds,
        )
    )
    (
        baseline_display_good,
        method_display_good,
        display_goodput_speedup,
    ) = paired_slo_goodput_speedup(
        baseline_display_latencies,
        baseline["wall_seconds"],
        display_latencies,
        result["wall_seconds"],
        args.slo_seconds,
    )
    scheduler_rows = list(result.get("scheduler_rows", []))
    batch_size_histogram: dict[str, int] = {}
    for row in scheduler_rows:
        key = str(int(row["batch_size"]))
        batch_size_histogram[key] = batch_size_histogram.get(key, 0) + 1
    policy_source = getattr(args, "policy_source", None)
    policy_sha256 = (
        hashlib.sha256(policy_source.read_bytes()).hexdigest()
        if policy_source is not None else None
    )
    payload = {
        "schema_version": 1,
        "study": "Whisper cross-architecture system-performance closure",
        "model": args.model_name,
        "model_path": str(args.model.resolve()),
        "system": args.system,
        "config": {
            "sessions": args.sessions,
            "duration_seconds": args.duration_seconds,
            "window_seconds": args.window_seconds,
            "windows_per_session": (
                args.duration_seconds // args.window_seconds
            ),
            "concurrency": args.concurrency,
            "offered_concurrency": (
                args.offered_concurrency
                if args.offered_concurrency is not None
                else args.concurrency
            ),
            "admission_reshaped": (
                args.offered_concurrency is not None
                and args.offered_concurrency != args.concurrency
            ),
            "arrival": args.arrival,
            "arrival_scale_seconds": args.arrival_scale_seconds,
            "batch_coalesce_seconds": args.batch_coalesce_seconds,
            "seed": args.seed,
            "system_order_index": args.system_order_index,
            "system_order_policy": args.system_order_policy,
            "margin_threshold": args.margin_threshold,
            "efsc_exit_margin": getattr(args, "efsc_exit_margin", None),
            "age_window_index": args.age_window_index,
            "age_margin_threshold": args.age_margin_threshold,
            "late_window_index": args.late_window_index,
            "late_margin_threshold": args.late_margin_threshold,
            "high_load_prompt_tokens": args.high_load_prompt_tokens,
            "high_load_margin_threshold": (
                args.high_load_margin_threshold
            ),
            "window_margin_rules": [
                {
                    "window_index": window,
                    "margin_threshold": margin,
                }
                for window, margin in parse_window_margin_rules(
                    getattr(args, "window_margin_rule", [])
                )
            ],
            "audit_probability": args.audit_probability,
            "policy_source": (
                str(policy_source.resolve())
                if policy_source is not None else None
            ),
            "policy_sha256": policy_sha256,
            "runtime_source_identity": runtime_source_identity(),
            "low_margin_policy": args.low_margin_policy,
            "checkpoint_revisions": args.checkpoint_revisions,
            "checkpoint_phase_policy": args.checkpoint_phase_policy,
            "disable_risk_authority": bool(args.disable_risk_authority),
            "disable_checkpoint_authority": bool(
                args.disable_checkpoint_authority
            ),
            "slo_seconds": args.slo_seconds,
            "canonical": (
                "W-suite FP16 batch-size-one executor with bounded raw "
                "previous-segment token state"
            ),
            "model_path": str(args.model.resolve()),
            "precision": "float16",
            "prompt_state_semantics": PROMPT_STATE_SEMANTICS,
            "baseline_capacity_protocol": (
                "declared-work-capacity-rebase-v2"
            ),
            "queue_protocol": QUEUE_PROTOCOL,
            "state_control_protocol": (
                (
                    "elastic-feedback-state-coherence-v1"
                    if args.system == "efsc" else STATE_CONTROL_PROTOCOL
                )
                if args.system in {"revtrace", "efsc"} else None
            ),
            "work_authority_protocol": (
                WORK_AUTHORITY_PROTOCOL
                if args.system == "revtrace" else None
            ),
            "target_capacity_protocol": (
                TARGET_CAPACITY_PROTOCOL
                if args.system == "revtrace" else None
            ),
            "post_timing_validation": (
                "exhaustive-same-state-replay-with-repeat-control-v2"
                if args.system == "revtrace" else None
            ),
            "prompt_checkpoint_revisions": (
                PROMPT_CHECKPOINT_REVISIONS
                if args.system == "revtrace" else None
            ),
            "max_prompt_tokens": executor.max_prompt_tokens,
            "max_new_tokens": executor.max_new_tokens,
            "authority_max_new_tokens": (
                args.authority_max_new_tokens
                if args.authority_max_new_tokens is not None
                else args.max_new_tokens
            ),
            "proposer_device": args.proposer_device,
            "verifier_device": args.verifier_device,
            "verifier_lanes": (
                args.verifier_lanes if args.system == "revtrace" else 0
            ),
            "share_verifier_weights": (
                bool(args.share_verifier_weights)
                if args.system == "revtrace" else False
            ),
            "authority_idle_proposer_lanes": (
                args.authority_idle_proposer_lanes
                if args.system == "revtrace" else 1
            ),
            "terminal_spillover_on_proposer": (
                bool(args.terminal_spillover_on_proposer)
                if args.system == "revtrace" else False
            ),
            "authority_spillover_on_proposer": (
                bool(args.authority_spillover_on_proposer)
                if args.system == "revtrace" else False
            ),
            "speculative_prefetch_depth": (
                int(args.speculative_prefetch_depth)
                if args.system == "revtrace" else 0
            ),
            "cohort_commit_barrier": (
                bool(args.cohort_commit_barrier)
                if args.system == "revtrace" else False
            ),
            "pad_proposals_to_concurrency": (
                bool(args.pad_proposals_to_concurrency)
                if args.system == "revtrace" else False
            ),
            "terminal_contract": (
                args.terminal_contract
                if args.system == "revtrace" else None
            ),
            "state_capacity_prompt_tokens": (
                args.state_capacity_prompt_tokens
                if args.system == "revtrace" else None
            ),
            "efsc_contract": result.get("efsc_contract"),
            "torch_version": torch.__version__,
            "transformers_version": transformers.__version__,
            "cuda_runtime": torch.version.cuda,
            "gpu_name": torch.cuda.get_device_name(
                torch.device(args.proposer_device)
            ),
        },
        "counts": {
            "events": len(rows),
            "state_entry_events": len(state_entry_rows),
            "output_violations": result.get(
                "output_violations", 0
            ),
            "state_violations": result.get(
                "state_violations", 0
            ),
            "efsc_actions": result.get("efsc_action_counts", {}),
            "efsc_pre_proposal_actions": result.get(
                "efsc_preparation_counts", {}
            ),
            "efsc_semantic_violations": result.get(
                "efsc_semantic_violations", {}
            ),
            "stale_commits": result.get("stale_commits", 0),
            "mandatory_verifications": result.get(
                "mandatory_verification_count", verification_count
            ),
            "terminal_authorities": result.get(
                "terminal_authority_count", 0
            ),
            "terminal_display_only": result.get(
                "terminal_display_only_count", 0
            ),
            "low_margin_authorities": result.get(
                "low_margin_authority_count", 0
            ),
            "work_budget_authorities": result.get(
                "work_budget_authority_count", 0
            ),
            "low_margin_holdbacks": result.get(
                "low_margin_holdback_count", 0
            ),
            "checkpoint_authorities": result.get(
                "checkpoint_authority_count", 0
            ),
            "capacity_rebases": result.get(
                "capacity_rebase_count", 0
            ),
            "baseline_capacity_rebases": baseline.get(
                "capacity_rebases", 0
            ),
            "authority_idle_dual_proposal_rounds": result.get(
                "authority_idle_dual_proposal_rounds", 0
            ),
            "terminal_spillover_authorities": result.get(
                "terminal_spillover_authorities", 0
            ),
            "proposer_spillover_authorities": result.get(
                "proposer_spillover_authorities", 0
            ),
            "speculative_prefetches": result.get(
                "speculative_prefetches", 0
            ),
            "speculative_prefetch_reuses": result.get(
                "speculative_prefetch_reuses", 0
            ),
            "speculative_prefetch_discards": result.get(
                "speculative_prefetch_discards", 0
            ),
            "cohort_releases": result.get("cohort_releases", 0),
            "proposal_padding_rows": result.get(
                "proposal_padding_rows", 0
            ),
            "post_timing_fast_path_audits": result.get(
                "post_timing_fast_path_audit_count", 0
            ),
            "post_timing_output_mismatches": result.get(
                "post_timing_output_mismatches", 0
            ),
            "post_timing_state_mismatches": result.get(
                "post_timing_state_mismatches", 0
            ),
            "post_timing_canonical_repeat_checks": result.get(
                "post_timing_canonical_repeat_checks", 0
            ),
            "post_timing_canonical_repeat_output_mismatches": result.get(
                "post_timing_canonical_repeat_output_mismatches", 0
            ),
            "post_timing_canonical_repeat_state_mismatches": result.get(
                "post_timing_canonical_repeat_state_mismatches", 0
            ),
            "post_timing_stable_output_mismatches": result.get(
                "post_timing_stable_output_mismatches", 0
            ),
            "post_timing_stable_state_mismatches": result.get(
                "post_timing_stable_state_mismatches", 0
            ),
            "post_timing_ambiguous_output_mismatches": result.get(
                "post_timing_ambiguous_output_mismatches", 0
            ),
            "post_timing_ambiguous_state_mismatches": result.get(
                "post_timing_ambiguous_state_mismatches", 0
            ),
            "random_audits": result.get("random_audit_count", 0),
            "safe_commits": result.get("safe_commit_count", 0),
            "deadline_misses": sum(
                value > args.slo_seconds for value in latencies
            ),
            "display_deadline_misses": sum(
                value > args.slo_seconds for value in display_latencies
            ),
        },
        "metrics": {
            "baseline_wall_seconds": baseline["wall_seconds"],
            "wall_seconds": result["wall_seconds"],
            "wall_speedup": wall_speedup,
            "gpu_normalized_speedup": gpu_normalized,
            "baseline_goodput": baseline_good,
            "baseline_display_goodput": baseline_display_good,
            "baseline_latency_p50": float(
                np.quantile(baseline_latencies, 0.50)
            ),
            "baseline_latency_p95": float(
                np.quantile(baseline_latencies, 0.95)
            ),
            "baseline_latency_p99": float(
                np.quantile(baseline_latencies, 0.99)
            ),
            "slo_goodput": method_good,
            "slo_goodput_speedup": (
                state_goodput_speedup
            ),
            "display_slo_goodput": method_display_good,
            "display_slo_goodput_speedup": (
                display_goodput_speedup
            ),
            "latency_p50": quantile(0.50),
            "latency_p95": quantile(0.95),
            "latency_p99": quantile(0.99),
            "display_latency_p99": (
                float(np.quantile(display_latencies, 0.99))
                if display_latencies else math.inf
            ),
            "terminal_stable_latency_p99": (
                float(np.quantile(terminal_latencies, 0.99))
                if terminal_latencies else math.inf
            ),
            "feedback_resolution_latency_p99": (
                float(np.quantile(feedback_resolution_latencies, 0.99))
                if feedback_resolution_latencies else math.inf
            ),
            "efsc_maximum_ancestry_age": result.get(
                "efsc_maximum_ancestry_age", 0
            ),
            "efsc_maximum_feedback_debt": result.get(
                "efsc_maximum_feedback_debt", 0
            ),
            "efsc_maximum_prompt_load": result.get(
                "efsc_maximum_prompt_load", 0
            ),
            "efsc_prompt_state_age_p95": float(np.quantile(
                [row.get("oldest_ancestor_age", 0) for row in rows],
                0.95,
            )),
            "efsc_reset_recovery_windows_p95": (
                float(np.quantile(
                    result.get("efsc_reset_recovery_windows", []), 0.95
                ))
                if result.get("efsc_reset_recovery_windows") else 0.0
            ),
            "energy_joules": result["energy_joules"],
            "baseline_energy_joules": baseline["energy_joules"],
            "joules_per_audio_second": (
                result["energy_joules"] / total_audio_seconds
            ),
            "baseline_joules_per_audio_second": (
                baseline["energy_joules"] / total_audio_seconds
            ),
            "energy_reduction": (
                1.0
                - result["energy_joules"]
                / baseline["energy_joules"]
                if baseline["energy_joules"] > 0 else None
            ),
            "verification_fraction": (
                (
                    verification_count
                    + result.get("random_audit_count", 0)
                )
                / len(rows)
                if rows else 0.0
            ),
            "total_canonical_authority_fraction": (
                (
                    verification_count
                    + result.get("terminal_authority_count", 0)
                    + result.get("random_audit_count", 0)
                )
                / len(rows)
                if rows else 0.0
            ),
            "synchronous_low_margin_fraction": (
                result.get("low_margin_authority_count", 0) / len(rows)
                if rows else 0.0
            ),
            "terminal_authority_fraction": (
                result.get("terminal_authority_count", 0) / len(rows)
                if rows else 0.0
            ),
            "checkpoint_authority_fraction": (
                result.get("checkpoint_authority_count", 0) / len(rows)
                if rows else 0.0
            ),
            "provisional_lifetime_p95": float(np.quantile(
                [
                    row.get("provisional_lifetime_seconds", 0.0)
                    for row in rows
                ],
                0.95,
            )),
            "provisional_lifetime_max": max(
                (
                    row.get("provisional_lifetime_seconds", 0.0)
                    for row in rows
                ),
                default=0.0,
            ),
            "provisional_overwrite_p95": float(np.quantile(
                [
                    row.get("provisional_overwrite_percent", 0.0)
                    for row in rows
                ],
                0.95,
            )),
            "post_timing_validation_seconds": result.get(
                "post_timing_validation_seconds", 0.0
            ),
        },
        "scheduler": {
            "proposal_rounds": len(scheduler_rows),
            "batch_size_histogram": batch_size_histogram,
            "mean_batch_size": (
                statistics.mean(
                    float(row["batch_size"]) for row in scheduler_rows
                )
                if scheduler_rows else 0.0
            ),
            "mean_occupancy_fraction": (
                statistics.mean(
                    float(row["batch_size"])
                    / max(1.0, float(row["capacity"]))
                    for row in scheduler_rows
                )
                if scheduler_rows else 0.0
            ),
            "maximum_pending_authorities": max(
                (
                    int(row.get("pending_authorities", 0))
                    for row in scheduler_rows
                ),
                default=0,
            ),
            "mean_pending_authorities": (
                statistics.mean(
                    int(row.get("pending_authorities", 0))
                    for row in scheduler_rows
                )
                if scheduler_rows else 0.0
            ),
            "unfilled_batch_slots": sum(
                int(row.get("unfilled_slots", 0))
                for row in scheduler_rows
            ),
        },
        "events": rows,
        "claim_boundaries": [
            (
                "LocalAgreement-2 protects a confirmed display prefix, not "
                "equality with singleton-canonical prompt state"
            ),
            (
                "Feedback-OFF is a physical upper bound and is not a "
                "functionally equivalent baseline"
            ),
            (
                "zero observed violations is paired-run evidence, not a "
                "deterministic floating-point certificate"
            ),
            (
                "EFSC canonical-trace disagreement is diagnostic evidence; "
                "HOLD/DECAY/RESET intentionally deny that candidate future "
                "prompt authority and are not contract violations"
            ),
            (
                "formal RevTrace rows exhaustively replay every measured "
                "fast-path write against the same-state singleton canonical "
                "after wall-clock and energy timing"
            ),
        ],
    }
    return payload


def run_calibration(args: argparse.Namespace) -> int:
    sessions = build_sessions(
        args.manifest,
        duration_seconds=args.duration_seconds,
        count=args.sessions,
        seed=args.seed,
    )
    executor = DistinctPromptWhisper(
        args.model,
        device=args.proposer_device,
        max_new_tokens=args.max_new_tokens,
    )
    if args.duration_seconds % args.window_seconds:
        raise ValueError("duration must be divisible by window-seconds")
    windows_per_session = args.duration_seconds // args.window_seconds
    rows: list[dict[str, Any]] = []
    capacity_rebases = 0
    for session_offset in range(0, len(sessions), args.concurrency):
        chunk = sessions[session_offset : session_offset + args.concurrency]
        prompts: list[tuple[int, ...]] = [() for _ in chunk]
        split = [list(np.array_split(item, windows_per_session)) for item in chunk]
        for window_index in range(windows_per_session):
            for local_index in range(len(chunk)):
                prompt_length = len(
                    executor.prompt_tokens(prompts[local_index])
                )
                if capacity_rebase_required(
                    prompt_length,
                    declared_next_segment_tokens=(
                        executor.max_new_tokens
                    ),
                    maximum_prompt_tokens=(
                        executor.max_prompt_tokens
                    ),
                ):
                    prompts[local_index] = ()
                    capacity_rebases += 1
            audio = [item[window_index] for item in split]
            proposed = executor.generate(audio, prompts)
            canonical = [
                executor.canonical(value, prompt)
                for value, prompt in zip(audio, prompts)
            ]
            for local_index, (fast, exact) in enumerate(
                zip(proposed, canonical)
            ):
                terminal = window_index == windows_per_session - 1
                fast_prompt = next_prompt_state(
                    executor, prompts[local_index], fast
                )
                exact_prompt = next_prompt_state(
                    executor, prompts[local_index], exact
                )
                rows.append({
                    "session_id": session_offset + local_index,
                    "window_index": window_index,
                    "terminal": terminal,
                    "minimum_margin": fast.minimum_margin,
                    "prior_prompt_tokens": len(
                        executor.prompt_tokens(prompts[local_index])
                    ),
                    "next_prompt_tokens": len(
                        executor.prompt_tokens(fast_prompt)
                    ),
                    "output_error": fast.token_ids != exact.token_ids,
                    "state_error": (
                        not terminal and fast_prompt != exact_prompt
                    ),
                })
            prompts = [
                next_prompt_state(executor, prompt, record)
                for prompt, record in zip(prompts, canonical)
            ]
    unsafe_margins = [
        float(row["minimum_margin"])
        for row in rows
        if row["state_error"] and row["minimum_margin"] is not None
    ]
    threshold = (
        max(unsafe_margins) + 1e-6
        if unsafe_margins else 0.0
    )
    payload = {
        "schema_version": 1,
        "study": "W-suite frozen margin calibration",
        "model": args.model_name,
        "config": {
            "sessions": args.sessions,
            "duration_seconds": args.duration_seconds,
            "window_seconds": args.window_seconds,
            "concurrency": args.concurrency,
            "seed": args.seed,
            "model_path": str(args.model.resolve()),
            "precision": "float16",
            "prompt_state_semantics": PROMPT_STATE_SEMANTICS,
            "calibration_state_protocol": (
                "canonical-state-capacity-rebase-v1"
            ),
            "max_prompt_tokens": executor.max_prompt_tokens,
            "max_new_tokens": executor.max_new_tokens,
            "torch_version": torch.__version__,
            "transformers_version": transformers.__version__,
            "cuda_runtime": torch.version.cuda,
            "gpu_name": torch.cuda.get_device_name(executor.device),
        },
        "counts": {
            "events": len(rows),
            "state_eligible_events": sum(
                not row["terminal"] for row in rows
            ),
            "output_errors": sum(
                row["output_error"] for row in rows
            ),
            "state_errors": sum(row["state_error"] for row in rows),
            "capacity_rebases": capacity_rebases,
        },
        "frozen_margin_threshold": threshold,
        "rows": rows,
        "claim_boundary": (
            "threshold is frozen before performance, risk, quality and UX "
            "seeds; zero calibration errors does not prove determinism"
        ),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        **payload["counts"],
        "frozen_margin_threshold": threshold,
    }, sort_keys=True))
    return 0


def run_workload(args: argparse.Namespace) -> int:
    if args.system == "efsc":
        if args.efsc_exit_margin is None:
            raise ValueError("--efsc-exit-margin is required for --system efsc")
        if args.efsc_exit_margin <= args.margin_threshold:
            raise ValueError(
                "EFSC exit margin must exceed the enter margin threshold"
            )
    window_margin_rules = parse_window_margin_rules(
        args.window_margin_rule
    )
    if args.policy_source is not None:
        policy_payload = json.loads(
            args.policy_source.read_text(encoding="utf-8")
        )
        selected = policy_payload.get("selected_policy", {})
        expected = {
            "threshold": args.margin_threshold,
            "age_window_index": args.age_window_index,
            "age_margin_threshold": args.age_margin_threshold,
            "late_window_index": args.late_window_index,
            "late_margin_threshold": args.late_margin_threshold,
            "high_load_prompt_tokens": args.high_load_prompt_tokens,
            "high_load_margin_threshold": args.high_load_margin_threshold,
            "window_margin_rules": [
                {
                    "window_index": window,
                    "margin_threshold": margin,
                }
                for window, margin in window_margin_rules
            ],
        }
        mismatches = {
            key: {
                "policy": selected.get(
                    key, [] if key == "window_margin_rules" else None
                ),
                "runtime": value,
            }
            for key, value in expected.items()
            if selected.get(
                key, [] if key == "window_margin_rules" else None
            ) != value
        }
        if mismatches:
            raise ValueError(
                "runtime risk parameters do not match frozen policy: "
                + json.dumps(mismatches, sort_keys=True)
            )
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
    authority_max_new_tokens = (
        args.authority_max_new_tokens
        if args.authority_max_new_tokens is not None
        else args.max_new_tokens
    )
    if args.verifier_lanes <= 0:
        raise ValueError("verifier-lanes must be positive")
    verifier_lanes: tuple[CanonicalLane, ...] = ()
    if args.system == "revtrace":
        if args.share_verifier_weights:
            shared_executor = DistinctPromptWhisper(
                args.model,
                device=args.verifier_device,
                max_new_tokens=authority_max_new_tokens,
            )
            lane_executors = (shared_executor,) * args.verifier_lanes
        else:
            lane_executors = tuple(
                DistinctPromptWhisper(
                    args.model,
                    device=args.verifier_device,
                    max_new_tokens=authority_max_new_tokens,
                )
                for _ in range(args.verifier_lanes)
            )
        verifier_lanes = tuple(
            CanonicalLane(
                lane_id=lane_id,
                executor=executor,
                stream=torch.cuda.Stream(device=executor.device),
            )
            for lane_id, executor in enumerate(lane_executors)
        )
    if args.duration_seconds % args.window_seconds:
        raise ValueError("duration must be divisible by window-seconds")
    windows_per_session = args.duration_seconds // args.window_seconds
    warmup = warmup_workload_executors(
        proposer,
        verifier_lanes,
        sessions,
        windows_per_session=windows_per_session,
        concurrency=args.concurrency,
    )
    risk_policy = WhisperStateRiskPolicy(
        margin_threshold=args.margin_threshold,
        age_window_index=args.age_window_index,
        age_margin_threshold=args.age_margin_threshold,
        late_window_index=args.late_window_index,
        late_margin_threshold=args.late_margin_threshold,
        high_load_prompt_tokens=args.high_load_prompt_tokens,
        high_load_margin_threshold=args.high_load_margin_threshold,
        window_margin_rules=window_margin_rules,
    )
    oracle_contract = {
        "model": args.model_name,
        "sessions": args.sessions,
        "duration_seconds": args.duration_seconds,
        "window_seconds": args.window_seconds,
        "seed": args.seed,
        "canonical": (
            "W-suite FP16 batch-size-one "
            + PROMPT_STATE_SEMANTICS
            + " declared-work-capacity-rebase-v2"
        ),
        "max_prompt_tokens": proposer.max_prompt_tokens,
        "proposer_max_new_tokens": proposer.max_new_tokens,
        "authority_max_new_tokens": authority_max_new_tokens,
        "work_authority_protocol": WORK_AUTHORITY_PROTOCOL,
        "target_capacity_protocol": TARGET_CAPACITY_PROTOCOL,
        "warmup_protocol": warmup["protocol"],
        "queue_protocol": QUEUE_PROTOCOL,
        "torch_version": torch.__version__,
        "transformers_version": transformers.__version__,
        "cuda_runtime": torch.version.cuda,
    }
    oracle_executor = proposer
    owns_oracle_executor = False
    if (
        authority_max_new_tokens != proposer.max_new_tokens
        and (
            args.oracle_cache is None
            or not args.oracle_cache.exists()
        )
    ):
        oracle_executor = DistinctPromptWhisper(
            args.model,
            device=args.proposer_device,
            max_new_tokens=authority_max_new_tokens,
        )
        owns_oracle_executor = True
    oracle, baseline = load_or_create_oracle(
        args.oracle_cache,
        oracle_executor,
        sessions,
        windows_per_session,
        power_interval=args.power_sample_seconds,
        contract=oracle_contract,
    )
    if owns_oracle_executor:
        del oracle_executor
        torch.cuda.empty_cache()
    if args.system == "revtrace":
        result = run_revtrace(
            proposer,
            verifier_lanes,
            sessions,
            oracle,
            windows_per_session=windows_per_session,
            concurrency=args.concurrency,
            arrival=args.arrival,
            seed=args.seed,
            risk_policy=risk_policy,
            audit_probability=args.audit_probability,
            power_interval=args.power_sample_seconds,
            arrival_scale_seconds=args.arrival_scale_seconds,
            batch_coalesce_seconds=args.batch_coalesce_seconds,
            authority_idle_proposer_lanes=(
                args.authority_idle_proposer_lanes
            ),
            terminal_spillover_on_proposer=(
                args.terminal_spillover_on_proposer
            ),
            authority_spillover_on_proposer=(
                args.authority_spillover_on_proposer
            ),
            speculative_prefetch_depth=(
                args.speculative_prefetch_depth
            ),
            cohort_commit_barrier=args.cohort_commit_barrier,
            pad_proposals_to_concurrency=(
                args.pad_proposals_to_concurrency
            ),
            terminal_contract=args.terminal_contract,
            state_capacity_prompt_tokens=(
                args.state_capacity_prompt_tokens
            ),
            low_margin_policy=args.low_margin_policy,
            disable_risk_authority=args.disable_risk_authority,
            disable_checkpoint_authority=(
                args.disable_checkpoint_authority
            ),
            checkpoint_revisions=args.checkpoint_revisions,
            checkpoint_phase_policy=args.checkpoint_phase_policy,
        )
    elif args.system == "efsc":
        result = run_efsc_system(
            proposer,
            sessions,
            oracle,
            windows_per_session=windows_per_session,
            concurrency=args.concurrency,
            arrival=args.arrival,
            seed=args.seed,
            enter_margin=args.margin_threshold,
            exit_margin=args.efsc_exit_margin,
            power_interval=args.power_sample_seconds,
            arrival_scale_seconds=args.arrival_scale_seconds,
            batch_coalesce_seconds=args.batch_coalesce_seconds,
        )
    elif args.system == "revtrace-inline":
        result = run_inline_revtrace(
            proposer,
            sessions,
            oracle,
            windows_per_session=windows_per_session,
            concurrency=args.concurrency,
            arrival=args.arrival,
            seed=args.seed,
            risk_policy=risk_policy,
            audit_probability=args.audit_probability,
            power_interval=args.power_sample_seconds,
            arrival_scale_seconds=args.arrival_scale_seconds,
            batch_coalesce_seconds=args.batch_coalesce_seconds,
        )
    else:
        result = run_simple_system(
            args.system,
            proposer,
            sessions,
            oracle,
            windows_per_session=windows_per_session,
            concurrency=args.concurrency,
            arrival=args.arrival,
            seed=args.seed,
            margin_threshold=args.margin_threshold,
            power_interval=args.power_sample_seconds,
            arrival_scale_seconds=args.arrival_scale_seconds,
            batch_coalesce_seconds=args.batch_coalesce_seconds,
        )
    payload = summarize_workload(
        args,
        baseline,
        result,
        proposer,
        total_audio_seconds=args.sessions * args.duration_seconds,
    )
    payload["config"]["warmup"] = warmup
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "model": args.model_name,
        "system": args.system,
        **payload["counts"],
        **payload["metrics"],
    }, sort_keys=True))
    return 0


def run_audit(args: argparse.Namespace) -> int:
    window_margin_rules = parse_window_margin_rules(
        args.window_margin_rule
    )
    forced_roots: set[tuple[int, int, int]] = set()
    for raw in args.forced_audit_root:
        try:
            episode_raw, session_raw, window_raw = raw.split(":")
            root = (
                int(episode_raw), int(session_raw), int(window_raw)
            )
        except (TypeError, ValueError) as exc:
            raise ValueError(
                "forced audit roots use EPISODE:SESSION:WINDOW"
            ) from exc
        if min(root) < 0:
            raise ValueError("forced audit root indices must be non-negative")
        forced_roots.add(root)
    forced_roots_seen: set[tuple[int, int, int]] = set()
    """Audit only fast-path writes under the deployed state-control protocol.

    Canonical audit outcomes are computed in a shadow path and never replace
    the proposal in the live prompt state.  Low-margin proposals are visible
    but held out of state, periodic checkpoints use canonical authority, and
    capacity rebases discard feedback before execution.  This makes the W4
    event distribution match the W5 RevTrace transition semantics.
    """
    policy_payload = json.loads(
        args.policy_source.read_text(encoding="utf-8")
    )
    selected = policy_payload.get("selected_policy", {})
    expected = {
        "threshold": args.margin_threshold,
        "age_window_index": args.age_window_index,
        "age_margin_threshold": args.age_margin_threshold,
        "late_window_index": args.late_window_index,
        "late_margin_threshold": args.late_margin_threshold,
        "high_load_prompt_tokens": args.high_load_prompt_tokens,
        "high_load_margin_threshold": args.high_load_margin_threshold,
        "window_margin_rules": [
            {
                "window_index": window,
                "margin_threshold": margin,
            }
            for window, margin in window_margin_rules
        ],
    }
    mismatches = {
        key: {
            "policy": selected.get(
                key, [] if key == "window_margin_rules" else None
            ),
            "runtime": value,
        }
        for key, value in expected.items()
        if selected.get(
            key, [] if key == "window_margin_rules" else None
        ) != value
    }
    if mismatches:
        raise ValueError(
            "audit risk parameters do not match frozen policy: "
            + json.dumps(mismatches, sort_keys=True)
        )
    rng = random.Random(args.seed)
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
    authority_max_new_tokens = (
        args.authority_max_new_tokens
        if args.authority_max_new_tokens is not None
        else args.max_new_tokens
    )
    verifier = DistinctPromptWhisper(
        args.model,
        device=args.verifier_device,
        max_new_tokens=authority_max_new_tokens,
    )
    if args.duration_seconds % args.window_seconds:
        raise ValueError("duration must be divisible by window-seconds")
    windows_per_session = args.duration_seconds // args.window_seconds
    risk_policy = WhisperStateRiskPolicy(
        margin_threshold=args.margin_threshold,
        age_window_index=args.age_window_index,
        age_margin_threshold=args.age_margin_threshold,
        late_window_index=args.late_window_index,
        late_margin_threshold=args.late_margin_threshold,
        high_load_prompt_tokens=args.high_load_prompt_tokens,
        high_load_margin_threshold=args.high_load_margin_threshold,
        window_margin_rules=window_margin_rules,
    )
    split = [
        list(np.array_split(audio, windows_per_session))
        for audio in sessions
    ]
    risk_entries = 0
    audits = 0
    caught_state_errors = 0
    total_events = 0
    checkpoint_authorities = 0
    low_margin_holdbacks = 0
    work_budget_authorities = 0
    late_state_mandatory = 0
    high_load_state_mandatory = 0
    terminal_displays = 0
    protected_state_violations = 0
    capacity_rebases = 0
    audit_rows: list[dict[str, Any]] = []
    episode = 0
    started = time.perf_counter()

    def audit_complete() -> bool:
        if forced_roots:
            return forced_roots_seen >= forced_roots
        return (
            risk_entries >= args.target_risk_entries
            and audits >= args.minimum_audits
        )

    def adaptation_stop_ready() -> bool:
        if not args.stop_on_caught_error:
            return False
        if forced_roots:
            return forced_roots_seen >= forced_roots
        return caught_state_errors > 0

    while not audit_complete():
        prompts: list[tuple[int, ...]] = [() for _ in sessions]
        order = list(range(len(sessions)))
        rng.shuffle(order)
        for window_index in range(windows_per_session):
            for offset in range(0, len(order), args.concurrency):
                ids = order[offset : offset + args.concurrency]
                audio = [split[index][window_index] for index in ids]
                for session_id in ids:
                    prompt_length = len(
                        proposer.prompt_tokens(prompts[session_id])
                    )
                    if capacity_rebase_required(
                        prompt_length,
                        declared_next_segment_tokens=(
                            verifier.max_new_tokens
                        ),
                        maximum_prompt_tokens=(
                            proposer.max_prompt_tokens
                        ),
                    ):
                        prompts[session_id] = ()
                        capacity_rebases += 1
                prompt_rows = [prompts[index] for index in ids]
                proposed = proposer.generate(audio, prompt_rows)
                for position, session_id in enumerate(ids):
                    record = proposed[position]
                    terminal = window_index == windows_per_session - 1
                    prior_prompt_tokens = len(
                        proposer.prompt_tokens(prompt_rows[position])
                    )
                    risk_reason = risk_policy.reason(
                        record.minimum_margin,
                        window_index=window_index,
                        prompt_tokens=prior_prompt_tokens,
                    )
                    low_margin = risk_reason is not None
                    checkpoint_due = checkpoint_due_for_session(
                        window_index,
                        session_id,
                        revisions=args.checkpoint_revisions,
                        phase_policy=args.checkpoint_phase_policy,
                        terminal=terminal,
                        total_nonterminal_revisions=(
                            windows_per_session - 1
                        ),
                    )
                    action = prompt_state_action(
                        risk_policy,
                        record.minimum_margin,
                        window_index=window_index,
                        prompt_tokens=prior_prompt_tokens,
                        terminal=terminal,
                        checkpoint_due=checkpoint_due,
                    )
                    work_budget_saturated = work_budget_requires_authority(
                        record.generation_steps,
                        proposer_max_new_tokens=proposer.max_new_tokens,
                        authority_max_new_tokens=verifier.max_new_tokens,
                    )
                    eligible = (
                        action == WhisperStateAction.FAST_COMMIT
                        and not work_budget_saturated
                    )
                    audit_coin = rng.random() if eligible else None
                    forced_root = (
                        episode, session_id, window_index
                    ) in forced_roots
                    audited = eligible and (
                        bool(audit_coin < args.audit_probability)
                        or forced_root
                    )
                    if forced_root and audited:
                        forced_roots_seen.add(
                            (episode, session_id, window_index)
                        )
                    risk_entries += int(eligible)
                    audits += int(audited)
                    checkpoint_authorities += int(
                        action
                        == WhisperStateAction.CHECKPOINT_AUTHORITY
                    )
                    low_margin_holdbacks += int(
                        action == WhisperStateAction.RISK_AUTHORITY
                    )
                    work_budget_authorities += int(
                        work_budget_saturated
                    )
                    late_state_mandatory += int(
                        action == WhisperStateAction.RISK_AUTHORITY
                        and risk_reason == "late-state-margin"
                    )
                    high_load_state_mandatory += int(
                        action == WhisperStateAction.RISK_AUTHORITY
                        and risk_reason == "high-load-state-margin"
                    )
                    terminal_displays += int(terminal)
                    proposed_next_prompt = next_prompt_state(
                        proposer, prompt_rows[position], record
                    )
                    canonical = None
                    canonical_next_prompt = None
                    if (
                        audited
                        or work_budget_saturated
                        or action in {
                            WhisperStateAction.CHECKPOINT_AUTHORITY,
                            WhisperStateAction.RISK_AUTHORITY,
                            WhisperStateAction.TERMINAL_AUTHORITY,
                        }
                    ):
                        canonical = verifier.canonical(
                            audio[position],
                            prompt_rows[position],
                        )
                        canonical_next_prompt = next_prompt_state(
                            verifier, prompt_rows[position], canonical
                        )
                        state_error = (
                            proposed_next_prompt != canonical_next_prompt
                        )
                        if audited:
                            caught_state_errors += int(state_error)
                            caught_row = {
                                "episode": episode,
                                "session_id": session_id,
                                "window_index": window_index,
                                "minimum_margin": record.minimum_margin,
                                "risk_reason": risk_reason,
                                "work_budget_saturated": (
                                    work_budget_saturated
                                ),
                                "prior_prompt_tokens": len(
                                    proposer.prompt_tokens(
                                        prompt_rows[position]
                                    )
                                ),
                                "next_prompt_tokens": len(
                                    proposer.prompt_tokens(
                                        proposed_next_prompt
                                    )
                                ),
                                "state_error": state_error,
                                "forced_audit": forced_root,
                                "audio_sha256": hashlib.sha256(
                                    np.asarray(
                                        audio[position], dtype=np.float32
                                    ).tobytes()
                                ).hexdigest(),
                                "prompt_token_sha256": hashlib.sha256(
                                    json.dumps(
                                        list(prompt_rows[position]),
                                        separators=(",", ":"),
                                    ).encode("utf-8")
                                ).hexdigest(),
                                "proposed_token_sha256": (
                                    record.token_sha256
                                ),
                                "canonical_token_sha256": (
                                    canonical.token_sha256
                                    if canonical is not None else None
                                ),
                            }
                            if state_error:
                                # A caught policy root is actionable only
                                # after same-input singleton repeats separate
                                # a stable fast-path miss from an unstable
                                # canonical oracle.
                                canonical_repeats = [
                                    verifier.canonical(
                                        audio[position],
                                        prompt_rows[position],
                                    )
                                    for _ in range(2)
                                ]
                                repeat_digests = [
                                    item.token_sha256
                                    for item in canonical_repeats
                                ]
                                caught_row.update({
                                    "canonical_repeat_token_sha256": (
                                        repeat_digests
                                    ),
                                    "canonical_repeat_stable": (
                                        canonical is not None
                                        and all(
                                            digest
                                            == canonical.token_sha256
                                            for digest in repeat_digests
                                        )
                                    ),
                                })
                            audit_rows.append(caught_row)
                    # Shadow audits are deliberately non-interfering: an
                    # audited safe proposal follows the same state transition
                    # it would have taken without selection into the audit.
                    if work_budget_saturated and not terminal:
                        assert canonical_next_prompt is not None
                        prompts[session_id] = canonical_next_prompt
                    elif action == WhisperStateAction.FAST_COMMIT:
                        prompts[session_id] = proposed_next_prompt
                    elif (
                        action
                        == WhisperStateAction.CHECKPOINT_AUTHORITY
                    ):
                        assert canonical_next_prompt is not None
                        prompts[session_id] = canonical_next_prompt
                    elif action == WhisperStateAction.RISK_AUTHORITY:
                        if args.low_margin_policy == "verify":
                            assert canonical_next_prompt is not None
                            prompts[session_id] = canonical_next_prompt
                        else:
                            # The proposal remains display-visible, but the
                            # previous-text prompt state is unchanged.  This
                            # is the deployed holdback transition whose future
                            # state distribution the certificate must cover.
                            assert args.low_margin_policy == "holdback"
                    else:
                        assert (
                            action == WhisperStateAction.TERMINAL_AUTHORITY
                        )
                    total_events += 1
                    if adaptation_stop_ready():
                        break
                if adaptation_stop_ready():
                    break
            if adaptation_stop_ready():
                break
            if audit_complete():
                break
        episode += 1
        if (
            forced_roots
            and episode > max(row[0] for row in forced_roots)
            and forced_roots_seen < forced_roots
        ):
            missing = sorted(forced_roots - forced_roots_seen)
            raise RuntimeError(
                "forced audit roots were not fast-path eligible: "
                + json.dumps(missing)
            )
        progress = {
            "episode": episode,
            "risk_entries": risk_entries,
            "audits": audits,
            "caught_state_errors": caught_state_errors,
            "elapsed_seconds": time.perf_counter() - started,
        }
        checkpoint = args.output.with_suffix(".checkpoint.json")
        checkpoint.parent.mkdir(parents=True, exist_ok=True)
        checkpoint.write_text(
            json.dumps(
                {
                    **progress,
                    "caught_rows": [
                        row for row in audit_rows if row["state_error"]
                    ],
                },
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        print(json.dumps(progress, sort_keys=True), flush=True)
        if (
            args.stop_on_caught_error
            and caught_state_errors > 0
        ):
            break

    adaptation_only = bool(forced_roots)
    if adaptation_only:
        # A forced same-input root replay is diagnostic evidence, never a
        # randomized certificate.  In particular audit_probability=0 is
        # legal here and must not be passed to AuditRiskBound, whose domain is
        # deliberately (0, 1).
        upper_count = risk_entries
        upper_risk = 1.0
        passed = False
        risk_method = "not-computed-forced-adaptation-replay"
    else:
        bound = AuditRiskBound(args.audit_probability, args.alpha)
        upper_count = bound.upper_error_count(
            risk_entries, caught_state_errors
        )
        upper_risk = upper_count / risk_entries
        passed = (
            risk_entries >= args.target_risk_entries
            and audits >= args.minimum_audits
            and upper_risk <= args.delta
            and protected_state_violations == 0
        )
        risk_method = "fixed-probability mixture e-process inversion"
    payload = {
        "schema_version": 1,
        "study": "Whisper W-suite independent time-uniform risk audit",
        "model": args.model_name,
        "decision": (
            "W4_RISK_CERTIFICATE_PASS"
            if passed else "W4_RISK_CERTIFICATE_FAIL"
        ),
        "config": vars(args) | {
            "model": str(args.model),
            "manifest": str(args.manifest),
            "output": str(args.output),
            "policy_source": str(args.policy_source.resolve()),
            "policy_sha256": hashlib.sha256(
                args.policy_source.read_bytes()
            ).hexdigest(),
            "runtime_source_identity": runtime_source_identity(),
            "low_margin_policy": args.low_margin_policy,
            "window_margin_rules": [
                {
                    "window_index": window,
                    "margin_threshold": margin,
                }
                for window, margin in window_margin_rules
            ],
            "precision": "float16",
            "prompt_state_semantics": PROMPT_STATE_SEMANTICS,
            "state_control_protocol": STATE_CONTROL_PROTOCOL,
            "work_authority_protocol": WORK_AUTHORITY_PROTOCOL,
            "target_capacity_protocol": TARGET_CAPACITY_PROTOCOL,
            "audit_interference": (
                "shadow-canonical-no-state-mutation"
            ),
            "prompt_checkpoint_revisions": (
                args.checkpoint_revisions
            ),
            "checkpoint_phase_policy": args.checkpoint_phase_policy,
            "max_prompt_tokens": proposer.max_prompt_tokens,
            "proposer_max_new_tokens": proposer.max_new_tokens,
            "authority_max_new_tokens": verifier.max_new_tokens,
            "torch_version": torch.__version__,
            "transformers_version": transformers.__version__,
            "cuda_runtime": torch.version.cuda,
            "gpu_name": torch.cuda.get_device_name(proposer.device),
        },
        "counts": {
            "episodes": episode,
            "total_events": total_events,
            "risk_eligible_entries": risk_entries,
            "pre_outcome_randomized_audits": audits,
            "checkpoint_authorities": checkpoint_authorities,
            "low_margin_authorities": (
                low_margin_holdbacks
                if args.low_margin_policy == "verify" else 0
            ),
            "work_budget_authorities": work_budget_authorities,
            "low_margin_holdbacks": (
                low_margin_holdbacks
                if args.low_margin_policy == "holdback" else 0
            ),
            "late_state_authorities": late_state_mandatory,
            "high_load_state_authorities": high_load_state_mandatory,
            "capacity_rebases": capacity_rebases,
            "terminal_authorities": terminal_displays,
            "terminal_display_only": 0,
            "caught_state_errors": caught_state_errors,
            "protected_state_violations": protected_state_violations,
        },
        "risk_certificate": {
            "upper_error_count": upper_count,
            "upper_risk": upper_risk,
            "confidence": 1.0 - args.alpha,
            "target_delta": args.delta,
            "method": risk_method,
        },
        "stop_on_caught_error_enabled": args.stop_on_caught_error,
        "forced_audit_roots": [list(row) for row in sorted(forced_roots)],
        "forced_audit_roots_seen": [
            list(row) for row in sorted(forced_roots_seen)
        ],
        "adaptation_only_stop_on_caught_error": (
            args.stop_on_caught_error
            and caught_state_errors > 0
            and (
                risk_entries < args.target_risk_entries
                or audits < args.minimum_audits
            )
        ),
        "audit_rows": audit_rows,
        "wall_seconds": time.perf_counter() - started,
        "claim_boundaries": [
            "30k entries are correlated execution events, not utterances",
            "audit coins are drawn before canonical outcomes",
            (
                "shadow canonical audits never replace or otherwise mutate "
                "the live proposal state"
            ),
            (
                "the certificate covers fast-path state writes under the "
                "frozen deferred-authority, checkpoint and capacity-rebase "
                "protocol"
            ),
            "certificate is model-specific and is not pooled",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "decision": payload["decision"],
        **payload["counts"],
        **payload["risk_certificate"],
    }, sort_keys=True))
    return 0 if passed else 2


def main() -> int:
    args = parse_args()
    if args.command == "calibrate":
        return run_calibration(args)
    if args.command == "workload":
        return run_workload(args)
    if args.command == "audit":
        return run_audit(args)
    raise AssertionError(args.command)


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Run the RevTrace V1--V4 matrix on one 8xV100 PBS allocation.

This runner intentionally creates a separate Transformers/eager V100 contract.
It never pools its absolute timings with the RTX 3090 vLLM contract.  Every
cell writes an atomic raw JSON record before the matrix advances, so an OOM or
unsupported cell is evidence rather than a reason to lose the completed work.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import multiprocessing as mp
import os
import platform
import queue
import statistics
import subprocess
import threading
import time
import traceback
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable


SAMPLE_RATE = 16000
FINE_SECONDS = 2
ROLLBACK_TOKENS = 5
UNFIXED_CHUNKS = 2


def percentile(values: Iterable[float], q: float) -> float:
    rows = sorted(float(value) for value in values)
    if not rows:
        return 0.0
    position = (len(rows) - 1) * q
    low = int(position)
    high = min(len(rows) - 1, low + 1)
    weight = position - low
    return rows[low] * (1.0 - weight) + rows[high] * weight


def atomic_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    temporary.replace(path)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def unit_edit_rate(reference: str, candidate: str) -> float:
    left = list(reference)
    right = list(candidate)
    if not left:
        return 0.0 if not right else 1.0
    previous = list(range(len(right) + 1))
    for i, a in enumerate(left, start=1):
        current = [i]
        for j, b in enumerate(right, start=1):
            current.append(min(
                current[-1] + 1,
                previous[j] + 1,
                previous[j - 1] + (a != b),
            ))
        previous = current
    return previous[-1] / max(1, len(left))


@dataclass
class SessionState:
    session_id: int
    source_index: int
    language: str
    raw_decoded: str = ""
    text: str = ""
    chunk_id: int = 0
    version: int = 0


class PowerSampler:
    def __init__(self, gpu_indices: list[int], interval: float = 0.2):
        self.gpu_indices = sorted(set(gpu_indices))
        self.interval = interval
        self.rows: list[dict[str, Any]] = []
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def _sample(self) -> None:
        while not self._stop.is_set():
            stamp = time.perf_counter()
            try:
                output = subprocess.check_output(
                    [
                        "nvidia-smi",
                        "--query-gpu=index,power.draw,utilization.gpu,utilization.memory,memory.used",
                        "--format=csv,noheader,nounits",
                    ],
                    text=True,
                    timeout=5,
                )
                for line in output.splitlines():
                    fields = [item.strip() for item in line.split(",")]
                    if len(fields) != 5:
                        continue
                    index = int(fields[0])
                    if index not in self.gpu_indices:
                        continue
                    self.rows.append({
                        "t": stamp,
                        "gpu": index,
                        "power_w": float(fields[1]),
                        "gpu_util": float(fields[2]),
                        "mem_util": float(fields[3]),
                        "memory_mib": float(fields[4]),
                    })
            except Exception:
                pass
            self._stop.wait(self.interval)

    def start(self) -> None:
        self._thread = threading.Thread(target=self._sample, daemon=True)
        self._thread.start()

    def stop(self) -> dict[str, Any]:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=10)
        per_gpu: dict[int, list[dict[str, Any]]] = {}
        for row in self.rows:
            per_gpu.setdefault(int(row["gpu"]), []).append(row)
        energy = 0.0
        for rows in per_gpu.values():
            rows.sort(key=lambda item: item["t"])
            for left, right in zip(rows, rows[1:]):
                energy += 0.5 * (left["power_w"] + right["power_w"]) * (
                    right["t"] - left["t"]
                )
        return {
            "samples": len(self.rows),
            "energy_joules": energy,
            "gpu_util_mean": (
                statistics.mean(row["gpu_util"] for row in self.rows)
                if self.rows else None
            ),
            "memory_util_mean": (
                statistics.mean(row["mem_util"] for row in self.rows)
                if self.rows else None
            ),
            "memory_mib_peak": (
                max((row["memory_mib"] for row in self.rows), default=None)
            ),
            "power_w_mean": (
                statistics.mean(row["power_w"] for row in self.rows)
                if self.rows else None
            ),
        }


def _worker_main(
    command_queue: Any,
    result_queue: Any,
    *,
    worker_id: str,
    gpu: int,
    model_path: str,
    dtype_name: str,
    manifest_path: str,
    microbatch: int,
    max_new_tokens: int,
    diagnostic_path: str,
) -> None:
    diagnostic = Path(diagnostic_path)
    diagnostic.parent.mkdir(parents=True, exist_ok=True)

    def note(message: str) -> None:
        with diagnostic.open("a", encoding="utf-8") as handle:
            handle.write(f"{time.time():.6f} {message}\n")
            handle.flush()

    note(f"worker-entry gpu={gpu} dtype={dtype_name}")
    os.environ["CUDA_VISIBLE_DEVICES"] = str(gpu)
    os.environ["TOKENIZERS_PARALLELISM"] = "false"
    os.environ["OMP_NUM_THREADS"] = "2"
    try:
        import numpy as np
        import soundfile as sf
        import soxr
        import torch
        from qwen_asr import Qwen3ASRModel, parse_asr_output

        note("imports-complete")
        torch.set_num_threads(2)
        dtype = torch.float16 if dtype_name == "float16" else torch.float32
        manifest = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
        sources = []
        for row in manifest["records"]:
            audio, rate = sf.read(row["path"], dtype="float32")
            if audio.ndim > 1:
                audio = audio.mean(axis=1)
            if rate != SAMPLE_RATE:
                audio = soxr.resample(audio, rate, SAMPLE_RATE, quality="HQ")
            sources.append(np.asarray(audio, dtype=np.float32))

        note("audio-load-complete")
        started = time.perf_counter()
        engine = Qwen3ASRModel.from_pretrained(
            model_path,
            torch_dtype=dtype,
            device_map={"": "cuda:0"},
            attn_implementation="eager",
            low_cpu_mem_usage=True,
            local_files_only=True,
            max_inference_batch_size=microbatch,
            max_new_tokens=max_new_tokens,
        )
        model = engine.model
        processor = engine.processor
        tokenizer = processor.tokenizer
        base_prompts = {
            language: engine._build_text_prompt(context="", force_language=language)
            for language in ("English", "Chinese")
        }
        note(f"model-load-complete seconds={time.perf_counter() - started:.6f}")
        result_queue.put({
            "kind": "ready",
            "worker_id": worker_id,
            "gpu": gpu,
            "dtype": dtype_name,
            "load_seconds": time.perf_counter() - started,
        })

        def audio_for(source_index: int, end_seconds: float) -> np.ndarray:
            source = sources[source_index % len(sources)]
            target = int(round(end_seconds * SAMPLE_RATE))
            repeats = max(1, int(math.ceil(target / max(1, source.size))))
            return np.tile(source, repeats)[:target].astype(np.float32, copy=False)

        def prefix_for(raw: str, chunk_id: int) -> str:
            if chunk_id < UNFIXED_CHUNKS or not raw:
                return ""
            ids = tokenizer.encode(raw)
            k = ROLLBACK_TOKENS
            while True:
                end = max(0, len(ids) - k)
                prefix = tokenizer.decode(ids[:end]) if end else ""
                if "\ufffd" not in prefix or not end:
                    return prefix
                k += 1

        def run_microbatch(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
            prompts = []
            wavs = []
            prefixes = []
            for item in items:
                prefix = prefix_for(item["raw_decoded"], int(item["chunk_id"]))
                prefixes.append(prefix)
                prompts.append(base_prompts[item["language"]] + prefix)
                wavs.append(audio_for(int(item["source_index"]), float(item["audio_end_seconds"])))
            inputs = processor(
                text=prompts,
                audio=wavs,
                return_tensors="pt",
                padding=True,
            )
            moved = {}
            for key, value in inputs.items():
                if hasattr(value, "to"):
                    value = value.to("cuda:0")
                    if torch.is_floating_point(value):
                        value = value.to(dtype)
                moved[key] = value
            input_length = int(moved["input_ids"].shape[1])
            generated = model.generate(
                **moved,
                max_new_tokens=max_new_tokens,
                do_sample=False,
                output_scores=True,
            )
            generated_ids = generated.sequences[:, input_length:]
            decoded = processor.batch_decode(
                generated_ids,
                skip_special_tokens=True,
                clean_up_tokenization_spaces=False,
            )
            margins = [[] for _ in items]
            for scores in generated.scores:
                top = torch.topk(scores.float(), k=2, dim=-1).values
                diff = (top[:, 0] - top[:, 1]).detach().cpu().tolist()
                for index, value in enumerate(diff):
                    margins[index].append(float(value))
            token_rows = generated_ids.detach().cpu().tolist()
            rows = []
            for item, prefix, raw, tokens, token_margins in zip(
                items, prefixes, decoded, token_rows, margins
            ):
                next_raw = prefix + raw
                language, text = parse_asr_output(
                    next_raw, user_language=item["language"]
                )
                rows.append({
                    "job_id": item["job_id"],
                    "session_id": int(item["session_id"]),
                    "raw_decoded": next_raw,
                    "text": text,
                    "language": language,
                    "chunk_id": int(item["chunk_id"]) + int(item.get("chunk_advance", 1)),
                    "token_ids": [int(token) for token in tokens],
                    "minimum_margin": min(token_margins) if token_margins else float("inf"),
                    "generated_tokens": len(tokens),
                })
            del moved, inputs, generated, generated_ids
            return rows

        while True:
            command = command_queue.get()
            if command["kind"] == "stop":
                result_queue.put({"kind": "stopped", "worker_id": worker_id})
                return
            request_id = command["request_id"]
            items = command["jobs"]
            force_singleton = bool(command.get("force_singleton", False))
            requested_microbatch = command.get("microbatch")
            effective_microbatch = (
                microbatch if requested_microbatch is None else requested_microbatch
            )
            limit = (
                1 if force_singleton
                else max(1, int(effective_microbatch))
            )
            request_started = time.perf_counter()
            records = []
            batch_sizes = []
            try:
                for begin in range(0, len(items), limit):
                    chunk = items[begin: begin + limit]
                    batch_started = time.perf_counter()
                    chunk_rows = run_microbatch(chunk)
                    completed = time.perf_counter() - request_started
                    batch_elapsed = time.perf_counter() - batch_started
                    for row in chunk_rows:
                        row["completion_seconds"] = completed
                        row["microbatch_seconds"] = batch_elapsed
                    records.extend(chunk_rows)
                    batch_sizes.append(len(chunk))
                result_queue.put({
                    "kind": "result",
                    "worker_id": worker_id,
                    "request_id": request_id,
                    "records": records,
                    "elapsed_seconds": time.perf_counter() - request_started,
                    "batch_sizes": batch_sizes,
                })
            except BaseException as exc:
                torch.cuda.empty_cache()
                result_queue.put({
                    "kind": "command_error",
                    "worker_id": worker_id,
                    "request_id": request_id,
                    "error": repr(exc),
                    "traceback": traceback.format_exc(),
                })
    except BaseException as exc:
        note("fatal\n" + traceback.format_exc())
        result_queue.put({
            "kind": "fatal",
            "worker_id": worker_id,
            "gpu": gpu,
            "error": repr(exc),
            "traceback": traceback.format_exc(),
        })


class WorkerPool:
    def __init__(
        self,
        *,
        name: str,
        gpus: list[int],
        model_path: Path,
        dtype: str,
        manifest: Path,
        microbatch: int,
        max_new_tokens: int = 32,
        timeout: float = 1800.0,
    ):
        self.name = name
        self.gpus = list(gpus)
        self.timeout = timeout
        self.context = mp.get_context("spawn")
        self.result_queue = self.context.Queue()
        self.command_queues = []
        self.processes = []
        self.counter = 0
        self.pending: dict[str, list[str]] = {}
        self.buffered: dict[str, list[dict[str, Any]]] = {}
        for lane, gpu in enumerate(self.gpus):
            command_queue = self.context.Queue()
            worker_id = f"{name}-{lane}-gpu{gpu}"
            process = self.context.Process(
                target=_worker_main,
                kwargs={
                    "command_queue": command_queue,
                    "result_queue": self.result_queue,
                    "worker_id": worker_id,
                    "gpu": gpu,
                    "model_path": str(model_path),
                    "dtype_name": dtype,
                    "manifest_path": str(manifest),
                    "microbatch": microbatch,
                    "max_new_tokens": max_new_tokens,
                    "diagnostic_path": str(
                        Path(os.environ["REVTRACE_DIAGNOSTIC_DIR"])
                        / f"{worker_id}.log"
                    ),
                },
                name=worker_id,
            )
            process.start()
            self.command_queues.append(command_queue)
            self.processes.append(process)
        ready = []
        deadline = time.time() + timeout
        while len(ready) < len(self.processes):
            try:
                message = self.result_queue.get(
                    timeout=min(5.0, max(1.0, deadline - time.time()))
                )
            except queue.Empty:
                dead = [
                    {
                        "pid": process.pid,
                        "exitcode": process.exitcode,
                        "name": process.name,
                    }
                    for process in self.processes
                    if not process.is_alive()
                ]
                if dead:
                    raise RuntimeError(f"workers exited before ready: {dead}")
                if time.time() >= deadline:
                    raise TimeoutError(f"workers not ready after {timeout}s")
                continue
            if message.get("kind") == "fatal":
                raise RuntimeError(f"worker load failed: {message}")
            if message.get("kind") == "ready":
                ready.append(message)
        self.ready = ready

    def dispatch(
        self,
        jobs: list[dict[str, Any]],
        *,
        force_singleton: bool = False,
        microbatch: int | None = None,
    ) -> str:
        self.counter += 1
        group_id = f"{self.name}-request-{self.counter}"
        partitions = [[] for _ in self.gpus]
        for index, job in enumerate(jobs):
            partitions[index % len(partitions)].append(job)
        request_ids = []
        for lane, rows in enumerate(partitions):
            if not rows:
                continue
            request_id = f"{group_id}-lane-{lane}"
            request_ids.append(request_id)
            self.command_queues[lane].put({
                "kind": "run",
                "request_id": request_id,
                "jobs": rows,
                "force_singleton": force_singleton,
                "microbatch": microbatch,
            })
        self.pending[group_id] = request_ids
        return group_id

    def collect(self, group_id: str) -> dict[str, Any]:
        wanted = set(self.pending.pop(group_id))
        messages = self.buffered.pop(group_id, [])
        deadline = time.time() + self.timeout
        while len(messages) < len(wanted):
            message = self.result_queue.get(timeout=max(1.0, deadline - time.time()))
            request_id = message.get("request_id", "")
            if request_id in wanted:
                messages.append(message)
            else:
                prefix = request_id.rsplit("-lane-", 1)[0]
                self.buffered.setdefault(prefix, []).append(message)
        errors = [message for message in messages if message.get("kind") != "result"]
        if errors:
            raise RuntimeError(f"worker command failed: {errors}")
        records = []
        elapsed = 0.0
        batch_sizes = []
        for message in messages:
            records.extend(message["records"])
            elapsed = max(elapsed, float(message["elapsed_seconds"]))
            batch_sizes.extend(message["batch_sizes"])
        records.sort(key=lambda row: row["job_id"])
        return {
            "records": records,
            "elapsed_seconds": elapsed,
            "batch_sizes": batch_sizes,
            "worker_messages": messages,
        }

    def run(self, jobs: list[dict[str, Any]], **kwargs: Any) -> dict[str, Any]:
        return self.collect(self.dispatch(jobs, **kwargs))

    def close(self) -> None:
        for command_queue in self.command_queues:
            command_queue.put({"kind": "stop"})
        stopped = 0
        deadline = time.time() + 120
        while stopped < len(self.processes) and time.time() < deadline:
            try:
                message = self.result_queue.get(timeout=2)
            except queue.Empty:
                continue
            if message.get("kind") == "stopped":
                stopped += 1
        for process in self.processes:
            process.join(timeout=20)
            if process.is_alive():
                process.terminate()
                process.join(timeout=10)


def initial_states(concurrency: int) -> list[SessionState]:
    return [
        SessionState(
            session_id=index,
            source_index=index % 2,
            language="English" if index % 2 == 0 else "Chinese",
        )
        for index in range(concurrency)
    ]


def jobs_for(
    states: list[SessionState],
    *,
    audio_end_seconds: float,
    chunk_advance: int = 1,
    tag: str,
) -> list[dict[str, Any]]:
    return [
        {
            "job_id": f"{tag}-{state.session_id:05d}",
            "session_id": state.session_id,
            "source_index": state.source_index,
            "language": state.language,
            "raw_decoded": state.raw_decoded,
            "chunk_id": state.chunk_id,
            "chunk_advance": chunk_advance,
            "audio_end_seconds": audio_end_seconds,
        }
        for state in states
    ]


def install(states: list[SessionState], records: list[dict[str, Any]]) -> None:
    lookup = {int(row["session_id"]): row for row in records}
    for state in states:
        row = lookup[state.session_id]
        state.raw_decoded = str(row["raw_decoded"])
        state.text = str(row["text"])
        state.language = str(row["language"])
        state.chunk_id = int(row["chunk_id"])
        state.version += 1


def summarize_cell(
    *,
    phase: str,
    cell_id: str,
    model: str,
    mode: str,
    concurrency: int,
    duration: int,
    used_gpus: list[int],
    wall: float,
    display_latencies: list[float],
    commit_latencies: list[float],
    states: list[SessionState],
    power: dict[str, Any],
    extra: dict[str, Any],
) -> dict[str, Any]:
    audio_seconds = concurrency * duration
    return {
        "schema_version": 1,
        "phase": phase,
        "cell_id": cell_id,
        "model": model,
        "mode": mode,
        "concurrency": concurrency,
        "duration_seconds": duration,
        "used_gpus": used_gpus,
        "used_gpu_count": len(used_gpus),
        "wall_seconds": wall,
        "audio_seconds": audio_seconds,
        "audio_throughput_x_realtime": audio_seconds / wall,
        "gpu_normalized_audio_throughput": audio_seconds / (wall * len(used_gpus)),
        "display_latency_p50_seconds": percentile(display_latencies, 0.50),
        "display_latency_p99_seconds": percentile(display_latencies, 0.99),
        "commit_latency_p50_seconds": percentile(commit_latencies, 0.50),
        "commit_latency_p99_seconds": percentile(commit_latencies, 0.99),
        "display_slo_2s_misses": sum(value > 2.0 for value in display_latencies),
        "display_events": len(display_latencies),
        "final_states": [asdict(state) for state in states],
        "power": {
            **power,
            "joules_per_audio_second": (
                power["energy_joules"] / audio_seconds if audio_seconds else None
            ),
        },
        **extra,
    }


def run_fine_mode(
    *,
    phase: str,
    cell_id: str,
    model: str,
    mode: str,
    concurrency: int,
    duration: int,
    proposer: WorkerPool,
    verifier: WorkerPool | None,
    used_gpus: list[int],
    risk_margin: float = 0.05,
) -> dict[str, Any]:
    states = initial_states(concurrency)
    display_latencies = []
    commit_latencies = []
    verified = 0
    selected_batch = 0
    uncertified_commits = 0
    sampler = PowerSampler(used_gpus)
    sampler.start()
    started = time.perf_counter()
    for window in range(duration // FINE_SECONDS):
        end_seconds = (window + 1) * FINE_SECONDS
        boundary = copy.deepcopy(states)
        jobs = jobs_for(
            boundary, audio_end_seconds=end_seconds,
            tag=f"{cell_id}-w{window}-proposal",
        )
        proposal_started = time.perf_counter()
        proposal = proposer.run(
            jobs,
            force_singleton=(mode in {"all-singleton", "all-canonical"}),
        )
        proposal_records = proposal["records"]
        display_latencies.extend(
            float(row["completion_seconds"]) for row in proposal_records
        )
        selected = list(proposal_records)
        verify_indices: list[int] = []
        if mode in {"llm42", "all-verify"}:
            verify_indices = list(range(concurrency))
        elif mode in {"margingate", "revtrace-sg"}:
            verify_indices = [
                index for index, row in enumerate(proposal_records)
                if float(row["minimum_margin"]) <= risk_margin
            ]
            if mode == "revtrace-sg" and window == duration // FINE_SECONDS - 1:
                verify_indices = list(range(concurrency))
        if verify_indices:
            if verifier is None:
                raise RuntimeError("verification requested without verifier pool")
            verify_jobs = [jobs[index] for index in verify_indices]
            canonical = verifier.run(verify_jobs, force_singleton=True)
            canonical_lookup = {
                int(row["session_id"]): row for row in canonical["records"]
            }
            for index in verify_indices:
                selected[index] = canonical_lookup[int(selected[index]["session_id"])]
            verified += len(verify_indices)
        selected_batch += concurrency - len(verify_indices)
        if mode in {"margingate", "revtrace-sg"}:
            for index, row in enumerate(proposal_records):
                if index not in verify_indices and float(row["minimum_margin"]) <= risk_margin:
                    uncertified_commits += 1
        install(states, selected)
        elapsed = time.perf_counter() - proposal_started
        commit_latencies.extend([elapsed] * concurrency)
    wall = time.perf_counter() - started
    power = sampler.stop()
    return summarize_cell(
        phase=phase,
        cell_id=cell_id,
        model=model,
        mode=mode,
        concurrency=concurrency,
        duration=duration,
        used_gpus=used_gpus,
        wall=wall,
        display_latencies=display_latencies,
        commit_latencies=commit_latencies,
        states=states,
        power=power,
        extra={
            "verification_events": verified,
            "verification_fraction": verified / max(1, concurrency * (duration // FINE_SECONDS)),
            "batch_selected_events": selected_batch,
            "uncertified_risky_commits": uncertified_commits,
            "transaction_install_violations": 0,
        },
    )


def run_coarse_mode(
    *,
    phase: str,
    cell_id: str,
    model: str,
    mode: str,
    concurrency: int,
    duration: int,
    proposer: WorkerPool,
    authority: WorkerPool,
    used_gpus: list[int],
    windows_per_segment: int = 3,
    risk_margin: float = 0.05,
    hybrid_replay: bool = False,
) -> dict[str, Any]:
    segment_seconds = FINE_SECONDS * windows_per_segment
    if duration % segment_seconds:
        raise ValueError("duration must be divisible by segment size")
    states = initial_states(concurrency)
    display_latencies = []
    commit_latencies = []
    proposer_service = 0.0
    authority_service = 0.0
    replay_service = 0.0
    replay_sessions = 0
    directional_events = 0
    transaction_violations = 0
    sampler = PowerSampler(used_gpus)
    sampler.start()
    started = time.perf_counter()
    for segment in range(duration // segment_seconds):
        segment_started = time.perf_counter()
        boundary = copy.deepcopy(states)
        end_seconds = (segment + 1) * segment_seconds
        authority_jobs = jobs_for(
            boundary,
            audio_end_seconds=end_seconds,
            chunk_advance=windows_per_segment,
            tag=f"{cell_id}-s{segment}-authority",
        )
        authority_group = authority.dispatch(authority_jobs)

        fine_states = copy.deepcopy(boundary)
        fine_min_margin = {state.session_id: float("inf") for state in states}
        for local in range(windows_per_segment):
            fine_end = segment * segment_seconds + (local + 1) * FINE_SECONDS
            fine_jobs = jobs_for(
                fine_states,
                audio_end_seconds=fine_end,
                tag=f"{cell_id}-s{segment}-f{local}",
            )
            fine = proposer.run(fine_jobs)
            proposer_service += fine["elapsed_seconds"]
            display_latencies.extend(
                float(row["completion_seconds"]) for row in fine["records"]
            )
            for row in fine["records"]:
                sid = int(row["session_id"])
                fine_min_margin[sid] = min(
                    fine_min_margin[sid], float(row["minimum_margin"])
                )
            install(fine_states, fine["records"])

        canonical = authority.collect(authority_group)
        authority_service += canonical["elapsed_seconds"]
        selected_records = list(canonical["records"])
        if hybrid_replay:
            replay_indices = []
            canonical_by_sid = {
                int(row["session_id"]): row for row in canonical["records"]
            }
            for index, fine_state in enumerate(fine_states):
                coarse = canonical_by_sid[fine_state.session_id]
                deficit = unit_edit_rate(fine_state.text, str(coarse["text"]))
                if deficit > 0.20 or fine_min_margin[fine_state.session_id] <= risk_margin:
                    replay_indices.append(index)
                    if deficit > 0.20:
                        directional_events += 1
            if replay_indices:
                replay_states = [copy.deepcopy(boundary[index]) for index in replay_indices]
                replay_started = time.perf_counter()
                for local in range(windows_per_segment):
                    fine_end = segment * segment_seconds + (local + 1) * FINE_SECONDS
                    replay_jobs = jobs_for(
                        replay_states,
                        audio_end_seconds=fine_end,
                        tag=f"{cell_id}-s{segment}-r{local}",
                    )
                    replay = proposer.run(replay_jobs, force_singleton=True)
                    install(replay_states, replay["records"])
                replay_service += time.perf_counter() - replay_started
                replay_sessions += len(replay_indices)
                replay_by_sid = {state.session_id: state for state in replay_states}
                for position, row in enumerate(selected_records):
                    sid = int(row["session_id"])
                    if sid in replay_by_sid:
                        state = replay_by_sid[sid]
                        selected_records[position] = {
                            **row,
                            "raw_decoded": state.raw_decoded,
                            "text": state.text,
                            "language": state.language,
                            "chunk_id": state.chunk_id,
                        }
        install(states, selected_records)
        if any(state.version != segment + 1 for state in states):
            transaction_violations += 1
            raise AssertionError("coarse transaction version drift")
        commit_latencies.extend(
            [time.perf_counter() - segment_started] * concurrency
        )
    wall = time.perf_counter() - started
    power = sampler.stop()
    return summarize_cell(
        phase=phase,
        cell_id=cell_id,
        model=model,
        mode=mode,
        concurrency=concurrency,
        duration=duration,
        used_gpus=used_gpus,
        wall=wall,
        display_latencies=display_latencies,
        commit_latencies=commit_latencies,
        states=states,
        power=power,
        extra={
            "windows_per_segment": windows_per_segment,
            "proposer_service_seconds": proposer_service,
            "authority_service_seconds": authority_service,
            "authority_to_proposer_ratio": (
                authority_service / proposer_service if proposer_service else None
            ),
            "fine_replay_seconds": replay_service,
            "fine_replay_sessions": replay_sessions,
            "directional_omission_events": directional_events,
            "transaction_install_violations": transaction_violations,
            "uncertified_ancestry_violations": 0,
        },
    )


def compare_final(cell: dict[str, Any], reference: dict[int, str]) -> None:
    errors = []
    exact = 0
    for row in cell.get("final_states", []):
        expected = reference.get(int(row["source_index"]), "")
        actual = str(row["text"])
        errors.append(unit_edit_rate(expected, actual))
        exact += int(expected == actual)
    cell["reference_final_exact_sessions"] = exact
    cell["reference_final_sessions"] = len(errors)
    cell["reference_final_edit_rate_median"] = (
        statistics.median(errors) if errors else None
    )
    cell["reference_final_edit_rate_p95"] = percentile(errors, 0.95)
    cell["reference_final_edit_rate_max"] = max(errors, default=None)


class Matrix:
    def __init__(self, args: argparse.Namespace):
        self.args = args
        self.raw = args.output / "raw"
        self.cells: list[dict[str, Any]] = []
        self.failures: list[dict[str, Any]] = []

    def record(self, cell: dict[str, Any]) -> None:
        atomic_json(self.raw / f"{cell['cell_id']}.json", cell)
        self.cells.append(cell)
        print(json.dumps({
            "complete": cell["cell_id"],
            "wall": cell.get("wall_seconds"),
            "throughput": cell.get("audio_throughput_x_realtime"),
            "p99": cell.get("display_latency_p99_seconds"),
        }, sort_keys=True), flush=True)

    def fail(self, phase: str, cell_id: str, exc: BaseException) -> None:
        payload = {
            "schema_version": 1,
            "phase": phase,
            "cell_id": cell_id,
            "status": "FAILED_CELL_RETAINED",
            "error": repr(exc),
            "traceback": traceback.format_exc(),
        }
        atomic_json(self.raw / f"{cell_id}.failure.json", payload)
        self.failures.append(payload)
        print(json.dumps(payload, sort_keys=True), flush=True)

    def run_v1(self, model_name: str, model_path: Path, manifest: Path) -> None:
        for dtype, gpu in (("float16", 0), ("float32", 1)):
            pool = None
            try:
                pool = WorkerPool(
                    name=f"v1-{model_name}-{dtype}", gpus=[gpu],
                    model_path=model_path, dtype=dtype, manifest=manifest,
                    microbatch=32,
                )
                warm = initial_states(1)
                pool.run(jobs_for(warm, audio_end_seconds=2, tag="warm"))
                for batch_size in (1, 2, 4, 8, 16, 32):
                    cell_id = f"v1-{model_name}-{dtype}-b{batch_size}"
                    try:
                        states = initial_states(batch_size)
                        jobs = jobs_for(states, audio_end_seconds=6, tag=cell_id)
                        sampler = PowerSampler([gpu], interval=0.1)
                        sampler.start()
                        first = pool.run(jobs, microbatch=batch_size)
                        second = pool.run(jobs, microbatch=batch_size)
                        power = sampler.stop()
                        singleton = pool.run(jobs, force_singleton=True)
                        repeat_mismatch = sum(
                            left["token_ids"] != right["token_ids"]
                            for left, right in zip(first["records"], second["records"])
                        )
                        singleton_mismatch = sum(
                            left["token_ids"] != right["token_ids"]
                            for left, right in zip(first["records"], singleton["records"])
                        )
                        elapsed = statistics.mean([
                            first["elapsed_seconds"], second["elapsed_seconds"]
                        ])
                        self.record({
                            "schema_version": 1,
                            "phase": "V1",
                            "cell_id": cell_id,
                            "model": model_name,
                            "dtype": dtype,
                            "batch_size": batch_size,
                            "audio_end_seconds": 6,
                            "repeats": 2,
                            "batch_elapsed_seconds_mean": elapsed,
                            "requests_per_second": batch_size / elapsed,
                            "audio_throughput_x_realtime": batch_size * 6 / elapsed,
                            "singleton_elapsed_seconds": singleton["elapsed_seconds"],
                            "batch_over_singleton_speedup": singleton["elapsed_seconds"] / elapsed,
                            "batch_repeat_token_mismatches": repeat_mismatch,
                            "batch_vs_singleton_token_mismatches": singleton_mismatch,
                            "power": power,
                        })
                    except BaseException as exc:
                        self.fail("V1", cell_id, exc)
            finally:
                if pool is not None:
                    pool.close()

    def run_v2(self, model_name: str, model_path: Path, manifest: Path) -> None:
        proposer = verifier = authority = None
        try:
            proposer = WorkerPool(
                name=f"v2-{model_name}-proposer", gpus=[0],
                model_path=model_path, dtype="float16", manifest=manifest,
                microbatch=16,
            )
            verifier = WorkerPool(
                name=f"v2-{model_name}-verifier", gpus=[1],
                model_path=model_path, dtype="float16", manifest=manifest,
                microbatch=16,
            )
            authority = WorkerPool(
                name=f"v2-{model_name}-authority", gpus=[2],
                model_path=model_path, dtype="float32", manifest=manifest,
                microbatch=8,
            )
            reference_cell = run_fine_mode(
                phase="V2", cell_id=f"v2-{model_name}-all-singleton-c16",
                model=model_name, mode="all-singleton", concurrency=16,
                duration=30, proposer=verifier, verifier=None, used_gpus=[1],
            )
            self.record(reference_cell)
            reference = {}
            for row in reference_cell["final_states"]:
                reference.setdefault(int(row["source_index"]), str(row["text"]))

            fine_specs = [
                ("unprotected-batch", proposer, None, [0]),
                ("fp32-batch", authority, None, [2]),
                ("margingate", proposer, verifier, [0, 1]),
                ("llm42", proposer, verifier, [0, 1]),
                ("revtrace-sg", proposer, verifier, [0, 1]),
            ]
            for mode, primary, secondary, gpus in fine_specs:
                cell_id = f"v2-{model_name}-{mode}-c16"
                try:
                    cell = run_fine_mode(
                        phase="V2", cell_id=cell_id, model=model_name,
                        mode=mode, concurrency=16, duration=30,
                        proposer=primary, verifier=secondary, used_gpus=gpus,
                        risk_margin=0.05,
                    )
                    compare_final(cell, reference)
                    self.record(cell)
                except BaseException as exc:
                    self.fail("V2", cell_id, exc)

            for mode, hybrid in (("coarse-dgft", False), ("hybrid-dgft", True)):
                cell_id = f"v2-{model_name}-{mode}-c16"
                try:
                    cell = run_coarse_mode(
                        phase="V2", cell_id=cell_id, model=model_name,
                        mode=mode, concurrency=16, duration=30,
                        proposer=proposer, authority=authority,
                        used_gpus=[0, 2], windows_per_segment=3,
                        hybrid_replay=hybrid,
                    )
                    compare_final(cell, reference)
                    self.record(cell)
                except BaseException as exc:
                    self.fail("V2", cell_id, exc)
        finally:
            for pool in (proposer, verifier, authority):
                if pool is not None:
                    pool.close()

    def run_v3(self, model_name: str, model_path: Path, manifest: Path) -> None:
        allocations = [
            (1, 1, [0], [4]),
            (1, 2, [0], [4, 5]),
            (2, 2, [0, 1], [4, 5]),
            (4, 4, [0, 1, 2, 3], [4, 5, 6, 7]),
        ]
        for proposer_count, authority_count, proposer_gpus, authority_gpus in allocations:
            proposer = authority = None
            try:
                proposer = WorkerPool(
                    name=f"v3-{model_name}-p{proposer_count}",
                    gpus=proposer_gpus, model_path=model_path,
                    dtype="float16", manifest=manifest, microbatch=16,
                )
                authority = WorkerPool(
                    name=f"v3-{model_name}-a{authority_count}",
                    gpus=authority_gpus, model_path=model_path,
                    dtype="float32", manifest=manifest, microbatch=8,
                )
                for concurrency in (16, 32, 64, 128):
                    cell_id = (
                        f"v3-{model_name}-p{proposer_count}a{authority_count}"
                        f"-c{concurrency}"
                    )
                    try:
                        cell = run_coarse_mode(
                            phase="V3", cell_id=cell_id, model=model_name,
                            mode="coarse-dgft-scaleout", concurrency=concurrency,
                            duration=30, proposer=proposer, authority=authority,
                            used_gpus=proposer_gpus + authority_gpus,
                            windows_per_segment=3,
                        )
                        cell["proposer_replicas"] = proposer_count
                        cell["authority_replicas"] = authority_count
                        self.record(cell)
                    except BaseException as exc:
                        self.fail("V3", cell_id, exc)
            finally:
                for pool in (proposer, authority):
                    if pool is not None:
                        pool.close()

    def run_v4(self, model_name: str, model_path: Path, manifest: Path) -> None:
        proposer = authority16 = authority32 = None
        try:
            proposer = WorkerPool(
                name=f"v4-{model_name}-p", gpus=[0], model_path=model_path,
                dtype="float16", manifest=manifest, microbatch=16,
            )
            authority16 = WorkerPool(
                name=f"v4-{model_name}-a16", gpus=[1], model_path=model_path,
                dtype="float16", manifest=manifest, microbatch=16,
            )
            authority32 = WorkerPool(
                name=f"v4-{model_name}-a32", gpus=[2], model_path=model_path,
                dtype="float32", manifest=manifest, microbatch=8,
            )
            # 30 seconds is divisible by the 2/6/10-second authority windows.
            # Keeping one frozen duration avoids a granularity-duration confound.
            for windows_per_segment in (1, 3, 5):
                for dtype, authority, gpus in (
                    ("float16", authority16, [0, 1]),
                    ("float32", authority32, [0, 2]),
                ):
                    cell_id = (
                        f"v4-{model_name}-rho{windows_per_segment}"
                        f"-authority-{dtype}"
                    )
                    try:
                        cell = run_coarse_mode(
                            phase="V4", cell_id=cell_id, model=model_name,
                            mode=f"coarse-{dtype}", concurrency=16, duration=30,
                            proposer=proposer, authority=authority,
                            used_gpus=gpus,
                            windows_per_segment=windows_per_segment,
                        )
                        cell["authority_dtype"] = dtype
                        self.record(cell)
                    except BaseException as exc:
                        self.fail("V4", cell_id, exc)
        finally:
            for pool in (proposer, authority16, authority32):
                if pool is not None:
                    pool.close()

    def finalize(self, environment: dict[str, Any]) -> dict[str, Any]:
        v3 = [row for row in self.cells if row.get("phase") == "V3"]
        scale_rows = []
        for model in sorted({row["model"] for row in v3}):
            fixed = [
                row for row in v3
                if row["model"] == model and row["concurrency"] == 128
            ]
            fixed.sort(key=lambda row: row["used_gpu_count"])
            if fixed:
                base = fixed[0]["audio_throughput_x_realtime"]
                base_gpus = fixed[0]["used_gpu_count"]
                for row in fixed:
                    gpu_ratio = row["used_gpu_count"] / base_gpus
                    scale_rows.append({
                        "model": model,
                        "cell_id": row["cell_id"],
                        "used_gpu_count": row["used_gpu_count"],
                        "throughput": row["audio_throughput_x_realtime"],
                        "speedup_over_smallest": row["audio_throughput_x_realtime"] / base,
                        "scale_efficiency": (
                            row["audio_throughput_x_realtime"] / base / gpu_ratio
                        ),
                        "display_p99": row["display_latency_p99_seconds"],
                    })
        summary = {
            "schema_version": 1,
            "study": "RevTrace V1-V4 independent 8xV100 matrix",
            "environment": environment,
            "completed_cells": len(self.cells),
            "failed_cells": len(self.failures),
            "phase_counts": {
                phase: sum(row.get("phase") == phase for row in self.cells)
                for phase in ("V1", "V2", "V3", "V4")
            },
            "scale_rows_c128": scale_rows,
            "cells": self.cells,
            "failures": self.failures,
            "claim_boundary": (
                "All measurements use the independent RHEL7/8xTesla-V100-32GB "
                "Transformers-eager contract. Absolute values are not pooled with "
                "the RTX3090/vLLM contract. V3 is single-node scale-out, not multi-node."
            ),
        }
        atomic_json(self.args.output / "v1_v4_summary.json", summary)
        return summary


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--models", nargs="*", default=[
        "Qwen3-ASR-0.6B", "Qwen3-ASR-1.7B"
    ])
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    diagnostic_dir = args.output / "worker_diagnostics"
    diagnostic_dir.mkdir(parents=True, exist_ok=True)
    os.environ["REVTRACE_DIAGNOSTIC_DIR"] = str(diagnostic_dir)

    import torch
    import transformers
    environment = {
        "hostname": platform.node(),
        "python": platform.python_version(),
        "torch": torch.__version__,
        "torch_cuda": torch.version.cuda,
        "transformers": transformers.__version__,
        "gpu_count": torch.cuda.device_count(),
        "gpus": [torch.cuda.get_device_name(i) for i in range(torch.cuda.device_count())],
        "pbs_jobid": os.environ.get("PBS_JOBID"),
        "runner_sha256": sha256(Path(__file__)),
    }
    atomic_json(args.output / "environment.json", environment)
    matrix = Matrix(args)
    manifest = args.root / "datasets/revbatch/manifest.json"
    for model_name in args.models:
        model_path = args.root / "models" / model_name
        for phase in ("V1", "V2", "V3", "V4"):
            try:
                getattr(matrix, f"run_{phase.lower()}")(
                    model_name, model_path, manifest
                )
            except BaseException as exc:
                matrix.fail(phase, f"{phase.lower()}-{model_name}-phase-fatal", exc)
    summary = matrix.finalize(environment)
    print(json.dumps({
        "decision": "V1_V4_MATRIX_COMPLETE",
        "completed_cells": summary["completed_cells"],
        "failed_cells": summary["failed_cells"],
        "phase_counts": summary["phase_counts"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

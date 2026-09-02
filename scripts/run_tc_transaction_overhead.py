"""Measure RevTrace's host-side transaction-protocol cost.

This is deliberately a LOCAL CPU microbenchmark.  It does not execute a
model, launch a GPU kernel, or measure end-to-end service latency.  The four
timed paths separate raw immutable-state materialization from the production
job checks, cumulative certificate checks, and ``commit_canonical_segment``.

The benchmark records repeat-level nanoseconds per operation.  Each repeat
contains many operations timed by ``time.perf_counter_ns``; variant order is
randomized, garbage collection is disabled in the timed region, and all
variants consume the same frozen valid fixture.
"""

from __future__ import annotations

import argparse
import csv
import gc
import json
import math
import os
import platform
import random
import statistics
import subprocess
import sys
import time
from dataclasses import replace
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from typing import Any, Callable


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from revtrace.dgft import (  # noqa: E402
    CanonicalSegmentJob,
    CommitResult,
    DualAxisCommitCertificate,
    FeedbackTransactionState,
    build_dual_axis_certificate,
    commit_canonical_segment,
    digest_bytes,
    digest_tokens,
    validate_dual_axis_certificate,
    validate_segment_job,
)


SCHEMA_VERSION = 1
VARIANTS = (
    "raw_state_materialization_no_validation",
    "owner_version_frontier_job_validation",
    "full_certificate_validation",
    "commit_canonical_segment",
)


def percentile(values: list[float], probability: float) -> float:
    if not values:
        raise ValueError("percentile requires at least one value")
    ordered = sorted(float(value) for value in values)
    position = (len(ordered) - 1) * probability
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    fraction = position - lower
    return ordered[lower] + fraction * (ordered[upper] - ordered[lower])


def sha256_file(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def git_value(*args: str) -> str | None:
    completed = subprocess.run(
        ["git", *args],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode:
        return None
    return completed.stdout.strip()


def build_fixture(
    *, prompt_tokens: int, display_tokens: int, descendants: int
) -> dict[str, Any]:
    prompt = tuple(range(1000, 1000 + prompt_tokens))
    display = tuple(range(10_000, 10_000 + display_tokens))
    next_prompt = (*prompt, *display)
    descendant_versions = tuple(range(11, 11 + descendants))
    contract_digest = sha256(b"tc-overhead-contract-v1").hexdigest()
    runtime_digest = sha256(b"tc-overhead-runtime-v1").hexdigest()
    audio = bytes((index * 17 + 3) % 256 for index in range(64 * 1024))
    state = FeedbackTransactionState(
        session_id=7,
        contract_epoch=3,
        policy_version="tc-overhead-v1",
        contract_digest=contract_digest,
        canonical_runtime_digest=runtime_digest,
        prompt_tokens=prompt,
        speculative_version=10,
    )
    job = CanonicalSegmentJob(
        session_id=state.session_id,
        contract_epoch=state.contract_epoch,
        policy_version=state.policy_version,
        parent_checkpoint_id=state.checkpoint_id,
        audio_start_window=state.audio_frontier_window,
        audio_end_window=3,
        segment_id="7:0:3",
        prompt_digest=digest_tokens(state.prompt_tokens),
        contract_digest=state.contract_digest,
        canonical_runtime_digest=state.canonical_runtime_digest,
        audio_sha256=digest_bytes(audio),
    )
    certificate = build_dual_axis_certificate(
        job=job,
        audio=audio,
        display_tokens=display,
        feedback_state_tokens=next_prompt,
        canonical_runtime_digest=state.canonical_runtime_digest,
    )
    return {
        "state": state,
        "job": job,
        "certificate": certificate,
        "audio": audio,
        "display_tokens": display,
        "segment_tokens": display,
        "next_prompt_tokens": next_prompt,
        "descendant_versions": descendant_versions,
    }


def raw_state_materialization(fixture: dict[str, Any]) -> CommitResult:
    """Mirror the production install's dataclass/tuple work, without checks."""

    state: FeedbackTransactionState = fixture["state"]
    job: CanonicalSegmentJob = fixture["job"]
    segment_tokens = fixture["segment_tokens"]
    next_prompt_tokens = fixture["next_prompt_tokens"]
    invalidated = tuple(
        sorted(
            int(value)
            for value in fixture["descendant_versions"]
            if int(value) > state.speculative_version
        )
    )
    installed = replace(
        state,
        checkpoint_id=state.checkpoint_id + 1,
        audio_frontier_window=job.audio_end_window,
        prompt_tokens=tuple(int(value) for value in next_prompt_tokens),
        stable_token_segments=(
            *state.stable_token_segments,
            tuple(int(value) for value in segment_tokens),
        ),
        committed_segment_ids=(
            *state.committed_segment_ids,
            job.segment_id,
        ),
        checkpoint_audio_frontiers=(
            *state.checkpoint_audio_frontiers,
            job.audio_end_window,
        ),
        speculative_version=max((state.speculative_version, *invalidated)),
    )
    return CommitResult(True, "materialized-without-validation", installed, invalidated)


def job_validation(fixture: dict[str, Any]) -> None:
    reason = validate_segment_job(fixture["state"], fixture["job"])
    if reason is not None:
        raise RuntimeError(f"valid fixture rejected by job validation: {reason}")


def full_certificate_validation(fixture: dict[str, Any]) -> None:
    job_validation(fixture)
    reason = validate_dual_axis_certificate(
        fixture["state"],
        fixture["job"],
        fixture["certificate"],
        display_tokens=fixture["display_tokens"],
        feedback_state_tokens=fixture["next_prompt_tokens"],
    )
    if reason is not None:
        raise RuntimeError(
            f"valid fixture rejected by certificate validation: {reason}"
        )


def full_commit(fixture: dict[str, Any]) -> CommitResult:
    result = commit_canonical_segment(
        fixture["state"],
        fixture["job"],
        certificate=fixture["certificate"],
        display_tokens=fixture["display_tokens"],
        segment_tokens=fixture["segment_tokens"],
        next_prompt_tokens=fixture["next_prompt_tokens"],
        descendant_versions=fixture["descendant_versions"],
    )
    if not result.accepted:
        raise RuntimeError(f"valid fixture rejected by commit: {result.reason}")
    return result


def operations(fixture: dict[str, Any]) -> dict[str, Callable[[], Any]]:
    return {
        VARIANTS[0]: lambda: raw_state_materialization(fixture),
        VARIANTS[1]: lambda: job_validation(fixture),
        VARIANTS[2]: lambda: full_certificate_validation(fixture),
        VARIANTS[3]: lambda: full_commit(fixture),
    }


def assert_fixture_equivalence(fixture: dict[str, Any]) -> None:
    raw = raw_state_materialization(fixture)
    committed = full_commit(fixture)
    if raw.state != committed.state:
        raise AssertionError("raw materialization does not match production commit state")
    if raw.invalidated_speculative_versions != committed.invalidated_speculative_versions:
        raise AssertionError("raw and production invalidation sets differ")
    job_validation(fixture)
    full_certificate_validation(fixture)


def measure(
    fixture: dict[str, Any], *, repeats: int, iterations: int,
    warmup_iterations: int, seed: int,
) -> list[dict[str, Any]]:
    funcs = operations(fixture)
    for function in funcs.values():
        for _ in range(warmup_iterations):
            function()

    samples: list[dict[str, Any]] = []
    rng = random.Random(seed)
    for repeat in range(repeats):
        order = list(VARIANTS)
        rng.shuffle(order)
        for order_index, variant in enumerate(order):
            function = funcs[variant]
            gc.collect()
            gc_was_enabled = gc.isenabled()
            gc.disable()
            try:
                started = time.perf_counter_ns()
                last: Any = None
                for _ in range(iterations):
                    last = function()
                elapsed = time.perf_counter_ns() - started
            finally:
                if gc_was_enabled:
                    gc.enable()
            if variant == VARIANTS[3] and not last.accepted:
                raise AssertionError("timed production commit did not accept")
            samples.append({
                "repeat": repeat,
                "order_index": order_index,
                "variant": variant,
                "iterations": iterations,
                "elapsed_ns": elapsed,
                "ns_per_operation": elapsed / iterations,
            })
    return samples


def summarize(samples: list[dict[str, Any]]) -> dict[str, dict[str, float]]:
    grouped = {
        variant: [
            float(row["ns_per_operation"])
            for row in samples
            if row["variant"] == variant
        ]
        for variant in VARIANTS
    }
    baseline = grouped[VARIANTS[0]]
    baseline_median = statistics.median(baseline)
    by_repeat = {
        (int(row["repeat"]), str(row["variant"])):
        float(row["ns_per_operation"])
        for row in samples
    }
    summary: dict[str, dict[str, float]] = {}
    for variant, values in grouped.items():
        paired_deltas = [
            by_repeat[(repeat, variant)] - by_repeat[(repeat, VARIANTS[0])]
            for repeat in range(len(values))
        ]
        paired_ratios = [
            by_repeat[(repeat, variant)] / by_repeat[(repeat, VARIANTS[0])]
            for repeat in range(len(values))
        ]
        median = statistics.median(values)
        summary[variant] = {
            "repeat_count": float(len(values)),
            "median_ns_per_operation": median,
            "p95_ns_per_operation": percentile(values, 0.95),
            "p99_ns_per_operation": percentile(values, 0.99),
            "min_ns_per_operation": min(values),
            "max_ns_per_operation": max(values),
            "mean_ns_per_operation": statistics.fmean(values),
            "stdev_ns_per_operation": (
                statistics.stdev(values) if len(values) > 1 else 0.0
            ),
            "median_delta_ns_vs_raw": statistics.median(paired_deltas),
            "p95_delta_ns_vs_raw": percentile(paired_deltas, 0.95),
            "median_ratio_vs_raw": statistics.median(paired_ratios),
            "ratio_of_medians_vs_raw": median / baseline_median,
        }
    return summary


def deployed_instrumentation_audit() -> dict[str, Any]:
    """Summarize the existing mixed coordinator interval, without relabeling it."""

    directory = ROOT / "results" / "r9_dgft" / "service" / "online_closure_matrix"
    files = sorted(directory.glob("*.json")) if directory.exists() else []
    values_us: list[float] = []
    for path in files:
        payload = json.loads(path.read_text(encoding="utf-8"))
        trace = payload.get("online_transaction_trace", {})
        for event in trace.get("events", []):
            if event.get("event") != "canonical-segment-committed":
                continue
            start = event.get("certified_perf")
            end = event.get("committed_perf")
            if isinstance(start, (int, float)) and isinstance(end, (int, float)):
                values_us.append((float(end) - float(start)) * 1e6)
    audit: dict[str, Any] = {
        "source_glob": str(directory / "*.json"),
        "file_count": len(files),
        "event_count": len(values_us),
        "interval": "committed_perf - certified_perf",
        "interpretation": (
            "observed online coordinator critical section; includes lock waiting, "
            "input conversion, job/certificate construction, hashing, validation, "
            "state materialization, and pending-version update"
        ),
        "is_pure_protocol_measure": False,
        "eligible_as_isolated_attribution": False,
    }
    if values_us:
        audit["summary_us"] = {
            "median": statistics.median(values_us),
            "p95": percentile(values_us, 0.95),
            "p99": percentile(values_us, 0.99),
            "min": min(values_us),
            "max": max(values_us),
            "mean": statistics.fmean(values_us),
        }
    return audit


def validate_result_schema(payload: dict[str, Any]) -> None:
    required = {
        "schema_version", "claim_boundary", "environment", "parameters",
        "variant_definitions", "raw_samples", "summary",
        "existing_instrumentation_audit", "conclusion",
    }
    missing = required.difference(payload)
    if missing:
        raise ValueError(f"result missing keys: {sorted(missing)}")
    if payload["schema_version"] != SCHEMA_VERSION:
        raise ValueError("unexpected schema version")
    if tuple(payload["summary"]) != VARIANTS:
        raise ValueError("summary variants are incomplete or out of order")
    expected = payload["parameters"]["repeats"] * len(VARIANTS)
    if len(payload["raw_samples"]) != expected:
        raise ValueError("raw sample count does not match repeats x variants")
    for row in payload["raw_samples"]:
        if row["variant"] not in VARIANTS:
            raise ValueError("unknown benchmark variant")
        if not math.isfinite(float(row["ns_per_operation"])):
            raise ValueError("non-finite timing")
        if float(row["ns_per_operation"]) <= 0:
            raise ValueError("non-positive timing")


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def write_report(path: Path, payload: dict[str, Any]) -> None:
    summary = payload["summary"]
    observed = payload["existing_instrumentation_audit"]
    lines = [
        "# TC transaction-overhead attribution audit",
        "",
        "## Decision",
        "",
        payload["conclusion"]["decision"],
        "",
        "This is a **local host-side CPU microbenchmark**, not a GPU or "
        "end-to-end serving result. It uses the production functions in "
        "`src/revtrace/dgft.py` on one frozen valid transaction fixture.",
        "",
        "## Why the prior logs were insufficient alone",
        "",
        f"The existing online trace contains {observed['event_count']:,} commits "
        f"across {observed['file_count']} files. Its `committed_perf - "
        "certified_perf` interval includes lock waiting, conversion, certificate "
        "construction and hashing, validation, state materialization, and the "
        "pending-version update. It is therefore an operational upper envelope, "
        "not an isolated protocol attribution.",
    ]
    if "summary_us" in observed:
        values = observed["summary_us"]
        lines.extend([
            "",
            "Observed mixed coordinator interval: "
            f"median {values['median']:.3f} us, P95 {values['p95']:.3f} us, "
            f"P99 {values['p99']:.3f} us.",
        ])
    lines.extend([
        "",
        "## Isolated microbenchmark",
        "",
        f"Warmup: {payload['parameters']['warmup_iterations']:,} calls/variant. "
        f"Measurement: {payload['parameters']['repeats']} randomized repeats x "
        f"{payload['parameters']['iterations']:,} calls/variant. Values below "
        "are repeat-level nanoseconds per operation; P95/P99 describe variation "
        "across repeat aggregates, not per-request service tails.",
        "",
        "| Path | Median (us/op) | P95 | P99 | Median delta vs raw (us) | "
        "Median ratio vs raw |",
        "|---|---:|---:|---:|---:|---:|",
    ])
    labels = {
        VARIANTS[0]: "Raw immutable-state materialization; no validation",
        VARIANTS[1]: "Production job validation",
        VARIANTS[2]: "Cumulative job + certificate validation",
        VARIANTS[3]: "Production `commit_canonical_segment`",
    }
    for variant in VARIANTS:
        row = summary[variant]
        lines.append(
            f"| {labels[variant]} | {row['median_ns_per_operation'] / 1000:.3f} "
            f"| {row['p95_ns_per_operation'] / 1000:.3f} "
            f"| {row['p99_ns_per_operation'] / 1000:.3f} "
            f"| {row['median_delta_ns_vs_raw'] / 1000:.3f} "
            f"| {row['median_ratio_vs_raw']:.2f}x |"
        )
    commit = summary[VARIANTS[3]]
    lines.extend([
        "",
        "The paired difference between the production commit and the no-check "
        f"materialization baseline is {commit['median_delta_ns_vs_raw'] / 1000:.3f} "
        "us/op at the median. This difference is the cleanest local estimate of "
        "the validation work added to the same immutable-state installation.",
        "",
        "## Attribution boundary",
        "",
        "The result closes the narrow question of whether certificate, version, "
        "frontier, and ledger-state checks have a measurable host-side cost. It "
        "does not establish GPU scalability, service goodput, or an end-to-end "
        "speedup. Existing GPU experiments remain the evidence for those claims.",
        "",
        "No new GPU run is required to close this *host-side protocol-cost* "
        "attribution: the microbenchmark isolates the production functions, while "
        "the pre-existing online trace provides a conservative deployed-path "
        "cross-check. A GPU run would only be necessary for a new claim about "
        "device utilization or end-to-end service performance.",
        "",
        "## Reproduction",
        "",
        "```powershell",
        "E:\\Anaconda\\python.exe scripts\\run_tc_transaction_overhead.py",
        "```",
        "",
        "Raw repeat samples and the complete environment are stored alongside "
        "the JSON result in `results/tc_transaction_overhead/`.",
        "",
    ])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repeats", type=int, default=31)
    parser.add_argument("--iterations", type=int, default=20_000)
    parser.add_argument("--warmup-iterations", type=int, default=2_000)
    parser.add_argument("--seed", type=int, default=20260903)
    parser.add_argument("--prompt-tokens", type=int, default=256)
    parser.add_argument("--display-tokens", type=int, default=32)
    parser.add_argument("--descendants", type=int, default=8)
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "results" / "tc_transaction_overhead" / "result.json",
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=ROOT / "Paper_TC" / "reports" / "TRANSACTION_OVERHEAD.md",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if min(args.repeats, args.iterations, args.warmup_iterations) <= 0:
        raise SystemExit("repeats, iterations and warmup iterations must be positive")
    if min(args.prompt_tokens, args.display_tokens, args.descendants) <= 0:
        raise SystemExit("fixture sizes must be positive")
    fixture = build_fixture(
        prompt_tokens=args.prompt_tokens,
        display_tokens=args.display_tokens,
        descendants=args.descendants,
    )
    assert_fixture_equivalence(fixture)
    samples = measure(
        fixture,
        repeats=args.repeats,
        iterations=args.iterations,
        warmup_iterations=args.warmup_iterations,
        seed=args.seed,
    )
    summary = summarize(samples)
    script_path = Path(__file__).resolve()
    source_path = ROOT / "src" / "revtrace" / "dgft.py"
    status = git_value("status", "--porcelain")
    clock = time.get_clock_info("perf_counter")
    payload = {
        "schema_version": SCHEMA_VERSION,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "claim_boundary": (
            "LOCAL host-side CPU protocol microbenchmark using production "
            "RevTrace transaction functions; not GPU, model inference, service "
            "goodput, tail latency, or end-to-end speedup evidence"
        ),
        "environment": {
            "platform": platform.platform(),
            "system": platform.system(),
            "release": platform.release(),
            "machine": platform.machine(),
            "processor": platform.processor(),
            "processor_identifier": os.environ.get("PROCESSOR_IDENTIFIER", ""),
            "logical_cpu_count": os.cpu_count(),
            "python_version": platform.python_version(),
            "python_implementation": platform.python_implementation(),
            "python_executable": sys.executable,
            "timer": {
                "implementation": clock.implementation,
                "monotonic": clock.monotonic,
                "adjustable": clock.adjustable,
                "resolution_seconds": clock.resolution,
            },
            "git_commit": git_value("rev-parse", "HEAD"),
            "git_dirty": bool(status),
            "script_sha256": sha256_file(script_path),
            "production_source": "src/revtrace/dgft.py",
            "production_source_sha256": sha256_file(source_path),
        },
        "parameters": {
            "repeats": args.repeats,
            "iterations": args.iterations,
            "warmup_iterations": args.warmup_iterations,
            "seed": args.seed,
            "prompt_tokens": args.prompt_tokens,
            "display_tokens": args.display_tokens,
            "next_prompt_tokens": args.prompt_tokens + args.display_tokens,
            "descendant_versions": args.descendants,
            "fixed_audio_bytes": len(fixture["audio"]),
            "garbage_collection_disabled_during_timing": True,
            "variant_order_randomized_per_repeat": True,
        },
        "variant_definitions": {
            VARIANTS[0]: (
                "same dataclass replace, tuple conversion, ledger append and "
                "descendant invalidation as the production install, with no checks"
            ),
            VARIANTS[1]: (
                "production validate_segment_job: session/owner, epoch, policy, "
                "contract/runtime bindings, checkpoint/frontier, audio/prompt "
                "digests, and duplicate-segment checks"
            ),
            VARIANTS[2]: (
                "cumulative production validate_segment_job followed by "
                "validate_dual_axis_certificate"
            ),
            VARIANTS[3]: (
                "production commit_canonical_segment, including job and dual-axis "
                "certificate validation plus immutable-state installation"
            ),
        },
        "raw_samples": samples,
        "summary": summary,
        "existing_instrumentation_audit": deployed_instrumentation_audit(),
        "conclusion": {
            "decision": (
                "CLOSES_HOST_PROTOCOL_ATTRIBUTION_WITHOUT_NEW_GPU_RUN"
            ),
            "reason": (
                "the production-function CPU microbenchmark isolates validation "
                "from the same raw state materialization, while existing online "
                "timestamps remain only a mixed deployed-path upper envelope"
            ),
            "gpu_run_required_for_this_narrow_question": False,
        },
    }
    validate_result_schema(payload)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    write_csv(args.output.with_name("raw_samples.csv"), samples)
    summary_rows = [
        {"variant": variant, **summary[variant]} for variant in VARIANTS
    ]
    write_csv(args.output.with_name("summary.csv"), summary_rows)
    write_report(args.report, payload)
    print(json.dumps({
        "result": str(args.output),
        "report": str(args.report),
        "decision": payload["conclusion"]["decision"],
        "summary": summary,
    }, indent=2))


if __name__ == "__main__":
    main()

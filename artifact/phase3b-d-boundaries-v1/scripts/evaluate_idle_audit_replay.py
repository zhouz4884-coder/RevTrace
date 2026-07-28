#!/usr/bin/env python3
"""Retrospective Phase 3B dual-channel audit gate.

The input pool was labelled by an independent 5% base-audit coin.  Each replay
subsamples 40% of that pool to emulate a 2% formal base channel, then compares
three diagnostic idle policies on the remaining labels.  Idle labels never
enter the formal confidence sequence.
"""

from __future__ import annotations

import argparse
import collections
import json
import math
import random
import statistics
from pathlib import Path
from typing import Callable


POLICIES = (
    "base_only",
    "uniform_idle",
    "margin_idle",
    "voi_idle",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--trials", type=int, default=2000)
    parser.add_argument("--window", type=int, default=64)
    parser.add_argument("--idle-budget", type=int, default=4)
    parser.add_argument(
        "--base-retain-probability", type=float, default=0.4
    )
    parser.add_argument("--seed", type=int, default=20260729)
    return parser.parse_args()


def margin_bin(margin: float) -> str:
    for upper in (0.10, 0.20, 0.50, 1.0):
        if margin <= upper:
            return f"le_{upper:.2f}"
    return "gt_1.00"


def make_voi_ranker(records: list[dict]) -> Callable[[dict], tuple]:
    max_chunk = max(int(item["chunk_index"]) for item in records)
    job_frequency = collections.Counter(
        item["job_sha256"] for item in records
    )
    bin_frequency = collections.Counter(
        margin_bin(float(item["minimum_margin"])) for item in records
    )

    def rank(record: dict) -> tuple:
        margin = max(float(record["minimum_margin"]), 1e-6)
        chunk = int(record["chunk_index"])
        bin_name = margin_bin(margin)
        # Diagnostic estimates only: uncertainty favors sparsely audited
        # strata, amplification favors revisions with more future transitions,
        # and cost grows with accumulated audio/context.
        uncertainty_width = 1.0 / math.sqrt(bin_frequency[bin_name])
        amplification = 1.0 + (max_chunk - chunk) / max(max_chunk, 1)
        traffic_weight = job_frequency[record["job_sha256"]]
        verifier_cost = 1.0 + chunk / max(max_chunk, 1)
        fragility = 1.0 / margin
        value = (
            uncertainty_width
            * amplification
            * traffic_weight
            * fragility
            / verifier_cost
        )
        return (-value, record["job_sha256"])

    return rank


def select_idle(
    remaining: list[dict],
    *,
    policy: str,
    idle_budget: int,
    voi_ranker: Callable[[dict], tuple],
) -> list[dict]:
    if policy == "base_only":
        return []
    if policy == "uniform_idle":
        return remaining[:idle_budget]
    if policy == "margin_idle":
        return sorted(
            remaining,
            key=lambda item: (
                float(item["minimum_margin"]),
                item["job_sha256"],
            ),
        )[:idle_budget]
    if policy == "voi_idle":
        return sorted(remaining, key=voi_ranker)[:idle_budget]
    raise ValueError(policy)


def replay_trial(
    records: list[dict],
    *,
    policy: str,
    window: int,
    idle_budget: int,
    base_retain_probability: float,
    rng: random.Random,
    verifier_seconds: float,
    voi_ranker: Callable[[dict], tuple],
) -> dict:
    verifier_requests = 0
    formal_base_requests = 0
    idle_requests = 0
    candidates_seen = 0
    for start in range(0, len(records), window):
        batch = records[start : start + window]
        base = []
        remaining = []
        for item in batch:
            if rng.random() < base_retain_probability:
                base.append(item)
            else:
                remaining.append(item)
        idle = select_idle(
            remaining,
            policy=policy,
            idle_budget=idle_budget,
            voi_ranker=voi_ranker,
        )
        selected = base + idle
        candidates_seen += len(batch)
        verifier_requests += len(selected)
        formal_base_requests += len(base)
        idle_requests += len(idle)
        if any(bool(item["state_error"]) for item in selected):
            return {
                "detected": True,
                "candidate_records_to_detection": candidates_seen,
                "verifier_requests_to_detection": verifier_requests,
                "formal_base_requests_to_detection": (
                    formal_base_requests
                ),
                "idle_requests_to_detection": idle_requests,
                "verifier_gpu_seconds_to_detection": (
                    verifier_requests * verifier_seconds
                ),
            }
    return {
        "detected": False,
        "candidate_records_to_detection": len(records),
        "verifier_requests_to_detection": verifier_requests,
        "formal_base_requests_to_detection": formal_base_requests,
        "idle_requests_to_detection": idle_requests,
        "verifier_gpu_seconds_to_detection": (
            verifier_requests * verifier_seconds
        ),
    }


def summarize(rows: list[dict]) -> dict:
    detected = [item for item in rows if item["detected"]]

    def metric(name: str, q: float = 0.5) -> float | None:
        if not detected:
            return None
        values = sorted(float(item[name]) for item in detected)
        index = min(len(values) - 1, int(q * len(values)))
        return values[index]

    return {
        "detection_probability": len(detected) / len(rows),
        "candidate_records_to_detection_median": metric(
            "candidate_records_to_detection"
        ),
        "verifier_requests_to_detection_median": metric(
            "verifier_requests_to_detection"
        ),
        "verifier_requests_to_detection_p95": metric(
            "verifier_requests_to_detection", 0.95
        ),
        "verifier_gpu_seconds_to_detection_median": metric(
            "verifier_gpu_seconds_to_detection"
        ),
        "formal_base_requests_to_detection_median": metric(
            "formal_base_requests_to_detection"
        ),
        "idle_requests_to_detection_median": metric(
            "idle_requests_to_detection"
        ),
    }


def main() -> int:
    args = parse_args()
    if not 0.0 < args.base_retain_probability <= 1.0:
        raise ValueError("base retain probability must lie in (0,1]")
    payload = json.loads(args.input.read_text(encoding="utf-8"))
    labelled = list(payload["audit_records"])
    errors = sum(bool(item["state_error"]) for item in labelled)
    unique_errors = {
        item["job_sha256"]
        for item in labelled
        if bool(item["state_error"])
    }
    if errors == 0:
        raise ValueError("idle-audit replay needs a labelled failure pool")
    verifier_p50 = float(
        payload["timing_diagnostics"][
            "verifier_request_seconds_p50"
        ]
    )
    voi_ranker = make_voi_ranker(labelled)
    rng = random.Random(args.seed)
    rows_by_policy = {policy: [] for policy in POLICIES}
    for _ in range(args.trials):
        trial = list(labelled)
        rng.shuffle(trial)
        # Use independent, reproducible selection streams per policy.  The
        # candidate order is common, but each strategy owns its base coin.
        seeds = {
            policy: rng.randrange(2**63) for policy in POLICIES
        }
        for policy in POLICIES:
            rows_by_policy[policy].append(
                replay_trial(
                    trial,
                    policy=policy,
                    window=args.window,
                    idle_budget=args.idle_budget,
                    base_retain_probability=(
                        args.base_retain_probability
                    ),
                    rng=random.Random(seeds[policy]),
                    verifier_seconds=verifier_p50,
                    voi_ranker=voi_ranker,
                )
            )
    summaries = {
        policy: summarize(rows)
        for policy, rows in rows_by_policy.items()
    }
    base = summaries["base_only"]
    uniform = summaries["uniform_idle"]
    margin = summaries["margin_idle"]
    voi = summaries["voi_idle"]
    dual_channel_pass = (
        max(
            uniform["detection_probability"],
            margin["detection_probability"],
            voi["detection_probability"],
        )
        >= base["detection_probability"] + 0.10
    )
    voi_independent_gain = (
        voi["detection_probability"]
        >= margin["detection_probability"] + 0.05
        or (
            voi["verifier_requests_to_detection_median"] is not None
            and margin["verifier_requests_to_detection_median"]
            is not None
            and voi["verifier_requests_to_detection_median"]
            <= 0.90
            * margin["verifier_requests_to_detection_median"]
        )
    )
    decision = (
        "P3B_DUAL_CHANNEL_AND_VOI_PASS"
        if dual_channel_pass and voi_independent_gain
        else (
            "P3B_DUAL_CHANNEL_PASS_VOI_NOT_DISTINGUISHED"
            if dual_channel_pass
            else "P3B_DUAL_CHANNEL_NO_GO"
        )
    )
    result = {
        "schema_version": 1,
        "study": "Phase 3B retrospective dual-channel audit gate",
        "decision": decision,
        "source": str(args.input),
        "labelled_base_audits": len(labelled),
        "labelled_state_errors": errors,
        "unique_error_jobs": len(unique_errors),
        "config": {
            "trials": args.trials,
            "window": args.window,
            "idle_budget": args.idle_budget,
            "base_retain_probability": (
                args.base_retain_probability
            ),
            "effective_base_probability": (
                float(payload["config"]["audit_probability"])
                * args.base_retain_probability
            ),
            "seed": args.seed,
            "verifier_request_seconds_p50": verifier_p50,
        },
        "policies": summaries,
        "gates": {
            "dual_channel_drift_detection_gain": dual_channel_pass,
            "voi_independent_gain_over_margin": (
                voi_independent_gain
            ),
            "formal_certificate_uses_idle_labels": False,
        },
        "claim_boundaries": [
            "All labels come from independent randomized base audits.",
            "The replay is retrospective diagnostic evidence, not a live SLO result.",
            "Idle selections do not enter the formal confidence sequence.",
            "Formal time-uniform certification speed is unchanged by idle labels.",
            "Verifier GPU-seconds use the measured request-time median.",
            "Only one unique failing job is present, limiting VOI-versus-margin conclusions.",
            "No production error frequency is estimated from this stress pool.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(result, sort_keys=True))
    return 0 if dual_channel_pass else 2


if __name__ == "__main__":
    raise SystemExit(main())

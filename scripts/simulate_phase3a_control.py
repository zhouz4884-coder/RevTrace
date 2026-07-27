#!/usr/bin/env python3
"""Semantic gate for Phase 3A adaptive state certification.

This executable uses controlled event streams to test controller invariants.
It is not a serving-performance experiment and its output is labelled
accordingly.
"""

from __future__ import annotations

import argparse
import json
import random
from dataclasses import asdict
from pathlib import Path

from revtrace.control import (
    AdaptiveCertificationController,
    ContractFingerprint,
    ControllerConfig,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("results/phase3/adaptive_control/semantic_gate.json"),
    )
    parser.add_argument("--events-per-stage", type=int, default=32_000)
    parser.add_argument("--seed", type=int, default=20260728)
    return parser.parse_args()


def fingerprint(model: str, concurrency: int) -> ContractFingerprint:
    return ContractFingerprint(
        model_sha256=f"frozen:{model}",
        tokenizer_sha256=f"frozen-tokenizer:{model}",
        runtime="vllm-0.10.2-frozen",
        precision="float16",
        kernel_backend="frozen-phase2-portfolio",
        concurrency_class=f"c{concurrency}",
        chunk_policy="2s-unfixed2-k5",
        canonical_path="fp16-singleton-intermediate-fixedshape-terminal",
    )


def run_stage(
    controller: AdaptiveCertificationController,
    *,
    name: str,
    model: str,
    concurrency: int,
    events: int,
    error_margin: float | None,
    seed: int,
) -> dict:
    controller.start_epoch(
        fingerprint(model, concurrency),
        reason=f"stage transition: {name}",
    )
    rng = random.Random(seed)
    error_index = events // 2 if error_margin is not None else None
    selected_state_violations = 0
    first_active = None
    first_repaired_threshold = None
    mode_changes: list[dict] = []
    previous_mode = controller.mode.value
    for index in range(events):
        margin = (
            error_margin
            if index == error_index
            else (
                1.25
                if index % 10 < 8
                else 0.15
                if index % 10 == 8
                else 0.06
            )
        )
        draw = 0.0 if index == error_index else rng.random()
        decision = controller.decide(
            minimum_margin=margin,
            terminal=False,
            state_amplification=1.0 + 0.5 * (index % 7 == 0),
            verifier_cost=1.0,
            queue_depth=0,
            base_audit_draw=draw,
        )
        is_error = index == error_index
        if is_error and not decision.verify:
            selected_state_violations += 1
        controller.observe(
            decision,
            state_error=is_error if decision.verify else None,
        )
        if decision.mode.value != previous_mode:
            mode_changes.append(
                {
                    "event": index,
                    "from": previous_mode,
                    "to": decision.mode.value,
                    "threshold": decision.threshold,
                }
            )
            previous_mode = decision.mode.value
        if first_active is None and decision.mode.value == "active_certified":
            first_active = index
        if (
            error_index is not None
            and index > error_index
            and decision.threshold is not None
            and decision.threshold > error_margin
            and first_repaired_threshold is None
        ):
            first_repaired_threshold = {
                "event": index,
                "threshold": decision.threshold,
            }

    snapshot = asdict(controller.snapshot())
    certified = [
        item for item in snapshot["certificates"] if item["certified"]
    ]
    return {
        "name": name,
        "model": model,
        "concurrency": concurrency,
        "events": events,
        "injected_numerical_state_errors": int(error_margin is not None),
        "error_margin": error_margin,
        "selected_state_violations": selected_state_violations,
        "first_active_event": first_active,
        "first_repaired_threshold": first_repaired_threshold,
        "mode_changes": mode_changes,
        "snapshot": snapshot,
        "certified_thresholds": [
            item["threshold"] for item in certified
        ],
    }


def main() -> int:
    args = parse_args()
    config = ControllerConfig(
        delta=0.005,
        alpha=0.05,
        audit_probability=0.05,
        minimum_base_audits=500,
        policy_thresholds=(
            0.0,
            0.025,
            0.05,
            0.075,
            0.10,
            0.15,
            0.20,
            0.30,
            0.50,
            0.75,
            1.0,
        ),
        drift_quarantine_events=64,
        control_interval_events=128,
    )
    controller = AdaptiveCertificationController(config, seed=args.seed)
    stages = [
        run_stage(
            controller,
            name="0.6B-c16-safe",
            model="Qwen3-ASR-0.6B",
            concurrency=16,
            events=args.events_per_stage,
            error_margin=None,
            seed=args.seed,
        ),
        run_stage(
            controller,
            name="0.6B-c64-unsafe",
            model="Qwen3-ASR-0.6B",
            concurrency=64,
            events=args.events_per_stage,
            error_margin=0.078125,
            seed=args.seed + 1,
        ),
        run_stage(
            controller,
            name="1.7B-c16-unsafe-low-policy",
            model="Qwen3-ASR-1.7B",
            concurrency=16,
            events=args.events_per_stage,
            error_margin=0.0625,
            seed=args.seed + 2,
        ),
        run_stage(
            controller,
            name="0.6B-c16-fresh-return",
            model="Qwen3-ASR-0.6B",
            concurrency=16,
            events=args.events_per_stage,
            error_margin=None,
            seed=args.seed + 3,
        ),
    ]
    passed = (
        all(item["selected_state_violations"] == 0 for item in stages)
        and stages[0]["snapshot"]["selected_threshold"] == 0.0
        and stages[1]["snapshot"]["selected_threshold"] >= 0.10
        and stages[2]["snapshot"]["selected_threshold"] >= 0.075
        and stages[3]["snapshot"]["selected_threshold"] == 0.0
        and all(item["certified_thresholds"] for item in stages)
    )
    payload = {
        "schema_version": 1,
        "study": "RevControl Phase 3A controlled semantic switch gate",
        "decision": (
            "PHASE3A_SEMANTIC_CONTROL_PASS"
            if passed
            else "PHASE3A_SEMANTIC_CONTROL_FAIL"
        ),
        "config": asdict(config),
        "stages": stages,
        "claim_boundaries": {
            "evidence_tier": "controlled semantic simulation",
            "performance": "not a GPU or serving performance result",
            "error_injection": (
                "state errors are injected at margins copied from frozen "
                "real executions; no artificial logit noise is used"
            ),
            "certificate": (
                "the controller logic uses a simultaneous policy envelope; "
                "real model evidence is evaluated in a separate GPU gate"
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

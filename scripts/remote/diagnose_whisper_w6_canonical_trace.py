#!/usr/bin/env python3
"""Recover per-window canonical roots for an existing W6 development run."""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--quality-runner", type=Path, required=True)
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--result", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--device", default="cuda:1")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    spec = importlib.util.spec_from_file_location(
        "revtrace_w6_quality_runner", args.quality_runner
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load quality runner")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)

    prior = json.loads(args.result.read_text(encoding="utf-8"))
    config = prior["config"]
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    count = int(config["sessions_per_split"])
    seed = int(config["seed"])
    seconds = int(config["duration_seconds"])
    sessions = (
        module.build_sessions(
            manifest["records"],
            split="test-clean",
            count=count,
            duration_seconds=seconds,
            seed=seed,
        )
        + module.build_sessions(
            manifest["records"],
            split="test-other",
            count=count,
            duration_seconds=seconds,
            seed=seed + 1,
        )
    )
    executor = module.DistinctPromptWhisper(
        args.model,
        device=args.device,
        max_new_tokens=int(config["reference_max_new_tokens"]),
    )
    _, elapsed, rebases, traces = module.canonical_system(
        executor,
        sessions,
        seconds // int(config["window_seconds"]),
    )
    events = prior["event_diagnostics"]
    first_divergence = {}
    for row in events:
        sid = int(row["session_id"])
        window = int(row["window_index"])
        canonical = traces[sid][window]
        if (
            sid not in first_divergence
            and row["selected_token_sha256"] != canonical["token_sha256"]
        ):
            first_divergence[sid] = {
                "window_index": window,
                "selected_source": row["selected_source"],
                "minimum_margin": row["minimum_margin"],
                "work_budget_saturated": row["work_budget_saturated"],
                "selected_text": row["selected_text"],
                "canonical_text": canonical["text"],
                "selected_token_sha256": row["selected_token_sha256"],
                "canonical_token_sha256": canonical["token_sha256"],
            }
    payload = {
        "schema_version": 1,
        "study": "W6 first canonical state-root divergence diagnostic",
        "source_result": str(args.result.resolve()),
        "canonical_seconds": elapsed,
        "canonical_capacity_rebases": rebases,
        "canonical_event_diagnostics": traces,
        "first_divergence_by_session": first_divergence,
        "catastrophic_session_roots": {
            str(row["session_id"]): first_divergence.get(row["session_id"])
            for row in prior["sessions"]
            if row["catastrophic_outlier"]
        },
        "claim_boundaries": [
            "diagnostic is post-timing and cannot repair the measured run",
            "the canonical trace uses the frozen max-96 singleton authority",
            "a first divergence is a state-root candidate, not prevalence",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "sessions_with_divergence": len(first_divergence),
        "catastrophic_session_roots": payload[
            "catastrophic_session_roots"
        ],
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

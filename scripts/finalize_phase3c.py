#!/usr/bin/env python3
"""Aggregate Phase 3C RIR population runs without duplicate inflation."""

from __future__ import annotations

import argparse
import json
import re
import statistics
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def base_model(name: str) -> str:
    return re.sub(
        r"-(?:c64|stress|librispeech)$", "", name
    )


def pair_signature(pair: dict, evidence_mode: str) -> tuple:
    first = pair["trajectory"][0]
    return (
        evidence_mode,
        pair["session_id"],
        int(pair["chunk_index"]),
        first["canonical_state_sha256"],
        first["divergent_state_sha256"],
    )


def summarize_pairs(pairs: list[dict], flip_rate: float) -> dict:
    if not pairs:
        return {
            "pairs": 0,
            "horizon": 0,
            "survival_curve": [],
            "pollution_half_life": None,
            "half_life_right_censored": False,
            "mean_raf": None,
            "median_raf": None,
            "terminal_difference_rate": None,
            "reconverged_fraction": None,
            "numerical_state_exposure": None,
        }
    trajectories = [
        [float(item["distance"]) for item in pair["trajectory"]]
        for pair in pairs
    ]
    horizon = max(len(distances) for distances in trajectories) - 1
    recovery_times = [
        next(
            (
                offset
                for offset, value in enumerate(
                    distances[1:], start=1
                )
                if value == 0
            ),
            None,
        )
        for distances in trajectories
    ]
    censor_times = [
        len(distances) - 1 for distances in trajectories
    ]
    survival = [1.0]
    probability = 1.0
    for offset in range(1, horizon + 1):
        at_risk = sum(
            (
                (recovery is None and censor >= offset)
                or (
                    recovery is not None
                    and recovery >= offset
                )
            )
            for recovery, censor in zip(
                recovery_times, censor_times
            )
        )
        events = sum(
            recovery == offset for recovery in recovery_times
        )
        if at_risk:
            probability *= 1.0 - events / at_risk
        survival.append(probability)
    half_life = next(
        (
            offset
            for offset, probability in enumerate(survival)
            if probability <= 0.5
        ),
        None,
    )
    rafs = [
        sum(value / distances[0] for value in distances)
        for distances in trajectories
    ]
    recoveries = [
        recovery is not None for recovery in recovery_times
    ]
    mean_raf = statistics.mean(rafs)
    return {
        "pairs": len(pairs),
        "horizon": horizon,
        "survival_curve": survival,
        "pollution_half_life": half_life,
        "half_life_right_censored": half_life is None,
        "mean_raf": mean_raf,
        "median_raf": statistics.median(rafs),
        "terminal_difference_rate": (
            sum(distances[-1] > 0 for distances in trajectories)
            / len(trajectories)
        ),
        "reconverged_fraction": sum(recoveries) / len(recoveries),
        "numerical_state_exposure": flip_rate * mean_raf,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--result-root",
        type=Path,
        default=ROOT / "results" / "phase3" / "rir_population",
    )
    parser.add_argument("--minimum-pairs", type=int, default=50)
    args = parser.parse_args()
    candidates = sorted(
        path
        for path in args.result_root.glob("*.json")
        if path.name != "summary.json"
    )
    result_runs = []
    for path in candidates:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if all(key in payload for key in ("model", "pairs", "search")):
            result_runs.append((path, payload))
    if not result_runs:
        raise FileNotFoundError("no Phase 3C population results")
    grouped: dict[str, dict[tuple, dict]] = defaultdict(dict)
    source_modes: dict[str, dict[tuple, str]] = defaultdict(dict)
    flip_rates: dict[str, float] = {}
    run_rows = []
    for path, run in result_runs:
        model = base_model(run["model"])
        config = run.get("config", {})
        if bool(config.get("audio_stress", False)):
            mode = "waveform_stress"
        elif config.get("language_mode", "bilingual") != "bilingual":
            mode = "independent_speech_stress"
        else:
            mode = "natural"
        flip_rates.setdefault(
            model,
            float(run.get("config", {}).get("natural_flip_rate", 0.0)),
        )
        for pair in run["pairs"]:
            signature = pair_signature(pair, mode)
            grouped[model].setdefault(signature, pair)
            source_modes[model].setdefault(signature, mode)
        run_rows.append(
            {
                "file": path.name,
                "model": run["model"],
                "evidence_mode": mode,
                "decision": run["decision"],
                "distinct_state_pairs": run["search"][
                    "distinct_state_pairs"
                ],
                "output_flips": run["search"]["output_flips"],
                "absorbed_output_flips": run["search"][
                    "absorbed_output_flips"
                ],
                "duplicate_state_pairs": run["search"][
                    "duplicate_state_pairs"
                ],
                "mean_raf": (
                    run["summary"]["mean_raf"]
                    if run["summary"]
                    else None
                ),
                "half_life": (
                    run["summary"]["pollution_half_life"]
                    if run["summary"]
                    else None
                ),
                "right_censored": (
                    run["summary"]["half_life_right_censored"]
                    if run["summary"]
                    else None
                ),
                "nse": (
                    run["summary"]["numerical_state_exposure"]
                    if run["summary"]
                    else None
                ),
            }
        )
    models = {}
    for model, pairs_by_signature in grouped.items():
        pairs = list(pairs_by_signature.values())
        natural_pairs = [
            pair
            for signature, pair in pairs_by_signature.items()
            if source_modes[model][signature] == "natural"
        ]
        stress_pairs = [
            pair
            for signature, pair in pairs_by_signature.items()
            if source_modes[model][signature] != "natural"
        ]
        aggregate = summarize_pairs(pairs, flip_rates[model])
        natural = summarize_pairs(natural_pairs, flip_rates[model])
        stress = summarize_pairs(stress_pairs, flip_rates[model])
        models[model] = {
            "distinct_state_pairs": len(pairs),
            "gate_pass": len(pairs) >= args.minimum_pairs,
            "natural_pairs": len(natural_pairs),
            "stress_pairs": len(stress_pairs),
            "aggregate": aggregate,
            "natural": natural,
            "stress": stress,
        }
    passed = bool(models) and all(
        item["gate_pass"] for item in models.values()
    )
    decision = (
        "PHASE3C_RIR_POPULATION_PASS"
        if passed
        else "PHASE3C_MECHANISM_CONFIRMED_POPULATION_GATE_NOT_MET"
    )
    summary = {
        "schema_version": 1,
        "study": "RevTrace Phase 3C aggregate RIR population",
        "decision": decision,
        "minimum_distinct_state_pairs_per_model": args.minimum_pairs,
        "runs": run_rows,
        "models": models,
        "claim_boundaries": [
            "distinct state pairs are deduplicated across runs",
            "replicated slots producing one state pair do not inflate N",
            "stress results establish mechanism behavior, not production prevalence",
            "a right-censored trajectory is not an infinite half-life",
        ],
    }
    args.result_root.mkdir(parents=True, exist_ok=True)
    (args.result_root / "summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    rows = "\n".join(
        "| {model} | {distinct_state_pairs} | {natural_pairs} | "
        "{stress_pairs} | {mean_raf:.3f} | {terminal_difference_rate:.3f} | "
        "{right_censored_fraction:.3f} | {gate} |".format(
            model=model,
            distinct_state_pairs=metrics["distinct_state_pairs"],
            natural_pairs=metrics["natural_pairs"],
            stress_pairs=metrics["stress_pairs"],
            mean_raf=metrics["aggregate"]["mean_raf"],
            terminal_difference_rate=metrics["aggregate"][
                "terminal_difference_rate"
            ],
            right_censored_fraction=(
                1.0 - metrics["aggregate"]["reconverged_fraction"]
                if metrics["aggregate"]["reconverged_fraction"] is not None
                else None
            ),
            gate="PASS" if metrics["gate_pass"] else "NOT MET",
        )
        for model, metrics in models.items()
    )
    report = f"""# RevTrace Phase 3C RIR population report

Decision: **{decision}**

| Model | Distinct pairs | Natural | Stress | Mean RAF | Terminal difference | Unrecovered at horizon | 50-pair gate |
|---|---:|---:|---:|---:|---:|---:|---:|
{rows}

The execution-shape stress produced many output flips, but most were either
absorbed by the official state projection or repeated the same state pair.
This confirms that output-flip counts cannot substitute for a state-pair
population.

Natural, waveform-stress, and independent-speech stress evidence remain
separately labeled in `summary.json`. Stress pairs are eligible for the legal
distinct-pair population gate, but their trigger rate is never used as a
production prevalence estimate. Numerical
State Exposure uses the preregistered natural flip-rate multiplier and is
therefore reported as a bounded exposure index, not a production error rate.

The mechanism-level RIR results are retained, while the preregistered
50-distinct-pair generalization claim remains outside the paper unless the gate
is met by additional independent inputs.
"""
    (args.result_root / "REPORT.md").write_text(
        report, encoding="utf-8"
    )
    print(json.dumps({"decision": decision, "models": models}))
    return 0 if passed else 2


if __name__ == "__main__":
    raise SystemExit(main())

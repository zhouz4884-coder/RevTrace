#!/usr/bin/env python3
"""Freeze Phase 4 adaptation, feedback, audit, and diversity evidence."""

from __future__ import annotations

import json
import statistics
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
PHASE4 = ROOT / "results" / "phase4"


def read(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(path)
    return json.loads(path.read_text(encoding="utf-8"))


def whisper_summary(paths: list[Path]) -> dict[str, Any]:
    runs = [read(path) for path in paths]
    pair_hashes: set[str] = set()
    pair_records: list[dict[str, Any]] = []
    for run in runs:
        for pair in run["pairs"]:
            digest = pair["pair_sha256"]
            if digest not in pair_hashes:
                pair_hashes.add(digest)
                pair_records.append(
                    {
                        "model": run["model"],
                        **pair,
                    }
                )
    on_future_nonzero = sum(
        any(value > 0 for value in pair["feedback_on_distances"][1:])
        for pair in pair_records
    )
    off_future_nonzero = sum(
        any(value > 0 for value in pair["feedback_off_distances"])
        for pair in pair_records
    )
    catastrophes = sum(
        bool(pair["unprotected_catastrophe"]) for pair in pair_records
    )
    per_model = {
        run["model"]: {
            "candidate_windows_scanned": run["counts"][
                "candidate_windows_scanned"
            ],
            "distinct_state_pairs": run["counts"][
                "distinct_state_pairs"
            ],
            "persistent_pairs": run["counts"]["persistent_pairs"],
            "median_raf": run["metrics"]["median_raf"],
            "mean_raf": (
                statistics.mean(float(pair["raf"]) for pair in run["pairs"])
                if run["pairs"]
                else None
            ),
            "maximum_raf": (
                max(float(pair["raf"]) for pair in run["pairs"])
                if run["pairs"]
                else None
            ),
            "pcm_h": run["metrics"]["pcm_h"],
            "singleton_repeat_mismatches": run["counts"][
                "singleton_repeat_mismatches"
            ],
            "wall_seconds": run["metrics"]["wall_seconds"],
        }
        for run in runs
    }
    gate_pass = (
        len(pair_records) >= 20
        and all(item["distinct_state_pairs"] > 0 for item in per_model.values())
        and off_future_nonzero == 0
        and on_future_nonzero > 0
    )
    return {
        "decision": (
            "PHASE4B_FEEDBACK_CAUSAL_GATE_PASS"
            if gate_pass
            else "PHASE4B_FEEDBACK_CAUSAL_GATE_NOT_MET"
        ),
        "per_model": per_model,
        "distinct_pairs": len(pair_records),
        "feedback_on_propagating_pairs": on_future_nonzero,
        "feedback_off_propagating_pairs": off_future_nonzero,
        "unprotected_catastrophes": catastrophes,
        "catastrophe_prevention_claim_eligible": catastrophes >= 5,
        "median_raf": (
            statistics.median(float(pair["raf"]) for pair in pair_records)
            if pair_records
            else None
        ),
        "claim_boundary": (
            "legal execution-shape intervention with fixed future audio; "
            "pair yield is not production prevalence"
        ),
    }


def active_mining_summary(paths: list[Path]) -> dict[str, Any]:
    runs = [read(path) for path in paths]
    per_model = {
        run["model"]: {
            "decision": run["decision"],
            "screened": run["search"]["independent_candidates_screened"],
            "probed": run["search"]["candidates_probed"],
            "distinct_pairs": run["search"]["distinct_state_pairs"],
            "replicated_rows": run["search"]["replicated_rows"],
            "duplicate_early_stops": run["search"][
                "duplicate_pair_early_stops"
            ],
            "pair_yield_per_1000_rows": (
                1000
                * run["search"]["distinct_state_pairs"]
                / run["search"]["replicated_rows"]
                if run["search"]["replicated_rows"]
                else 0.0
            ),
            "tail": run["contamination_tail"],
            "wall_seconds": run["elapsed_seconds"],
        }
        for run in runs
    }
    gate_pass = all(
        item["distinct_pairs"] >= 50 for item in per_model.values()
    )
    budget_complete = all(
        item["decision"]
        in {
            "PHASE4D_ACTIVE_MINING_TARGET_PASS",
            "PHASE4D_ACTIVE_MINING_BUDGET_EXHAUSTED",
        }
        for item in per_model.values()
    )
    return {
        "decision": (
            "PHASE4D_ACTIVE_MINING_TARGET_PASS"
            if gate_pass
            else "PHASE4D_ACTIVE_MINING_BUDGET_COMPLETE_TARGET_NOT_MET"
            if budget_complete
            else "PHASE4D_ACTIVE_MINING_INCOMPLETE"
        ),
        "per_model": per_model,
        "gate_pass": gate_pass,
        "budget_complete": budget_complete,
        "claim_boundary": (
            "targeted mechanism population; not natural or production "
            "mismatch prevalence"
        ),
    }


def main() -> int:
    risk = read(PHASE4 / "risk_window" / "summary.json")
    slack = read(PHASE4 / "slackguard" / "summary.json")
    damage = read(PHASE4 / "damage_population" / "summary.json")
    whisper_paths = sorted(
        (PHASE4 / "whisper_feedback_expanded").glob("whisper-*-en.json")
    )
    mining_paths = sorted(
        (PHASE4 / "active_mining").glob("qwen3-asr-*.json")
    )
    if len(whisper_paths) != 2:
        raise RuntimeError("expected two expanded Whisper result files")
    if len(mining_paths) != 2:
        raise RuntimeError("expected two active-mining result files")
    whisper = whisper_summary(whisper_paths)
    mining = active_mining_summary(mining_paths)
    baseline_yield = {
        row["model"].replace("-librispeech", ""): row[
            "pair_yield_per_1000_replicated_rows"
        ]
        for row in damage["runs"]
        if row["file"].endswith("-librispeech.json")
    }
    old_state_pairs: set[tuple[str, str]] = set()
    for path in (
        ROOT / "results" / "phase3" / "rir_population"
    ).glob("*.json"):
        if path.name == "summary.json":
            continue
        payload = read(path)
        for pair in payload.get("pairs", []):
            first = pair["trajectory"][0]
            old_state_pairs.add(
                (
                    first["canonical_state_sha256"],
                    first["divergent_state_sha256"],
                )
            )
    for path in mining_paths:
        run = read(path)
        model_row = mining["per_model"][run["model"]]
        baseline = baseline_yield[run["model"]]
        model_row["previous_natural_pairs_per_1000_rows"] = baseline
        model_row["yield_improvement"] = (
            model_row["pair_yield_per_1000_rows"] / baseline
        )
        model_row["new_pairs_vs_phase3"] = sum(
            (
                pair["trajectory"][0]["canonical_state_sha256"],
                pair["trajectory"][0]["divergent_state_sha256"],
            )
            not in old_state_pairs
            for pair in run["pairs"]
        )
    stages = {
        "phase4a_certified_risk_window": {
            "decision": risk["decision"],
            "live_switch_executed": risk["gates"][
                "live_switch_deployment"
            ],
            "contract_switch_fail_closed": risk["gates"][
                "contract_switch_fail_closed"
            ],
            "stages": risk["stages"],
        },
        "phase4b_whisper_feedback": whisper,
        "phase4c_slackguard": {
            "decision": slack["decision"],
            "live_gate_executed": slack["gates"]["live_gate_executed"],
            "quantum_to_budget_ratio": slack["measurements"][
                "quantum_to_intrusion_budget_ratio"
            ],
            "offline_detection_improvement": slack["measurements"][
                "offline_median_detection_time_improvement"
            ],
            "legal_repair": slack["legal_repair"],
        },
        "phase4d_active_mining": mining,
    }
    all_tasks_accounted = (
        mining["budget_complete"]
        and len(whisper_paths) == 2
        and risk["gates"]["split_sample_certificates"]
    )
    positive_gates = (
        whisper["decision"] == "PHASE4B_FEEDBACK_CAUSAL_GATE_PASS"
        and mining["gate_pass"]
    )
    decision = (
        "PHASE4_ADAPTATION_AND_GENERALITY_PASS_LIVE_AUDIT_NO_GO"
        if positive_gates
        else "PHASE4_TASKS_COMPLETE_WITH_BOUNDED_NEGATIVE_GATES"
        if all_tasks_accounted
        else "PHASE4_INCOMPLETE"
    )
    summary = {
        "schema_version": 1,
        "study": "RevTrace Phase 4 adaptation and positive generality",
        "decision": decision,
        "stages": stages,
        "claim_boundaries": [
            "Phase 4A is split-sample controller replay, not a live c16-c64 switch",
            "Phase 4B isolates the previous-text feedback edge under fixed future audio",
            "Phase 4C full-request audit failed a physical preemption-quantum gate; no live SLO claim is made",
            "Phase 4D is targeted active mining and cannot estimate production prevalence",
            "zero observed violations are empirical, not deterministic arithmetic proof",
        ],
    }
    PHASE4.mkdir(parents=True, exist_ok=True)
    (PHASE4 / "summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    whisper_rows = "\n".join(
        "| {model} | {candidate_windows_scanned} | "
        "{distinct_state_pairs} | {persistent_pairs} | {median_raf:.3f} | "
        "{maximum_raf:.3f} | {pcm_h:.3f} |".format(
            model=model,
            **values,
        )
        for model, values in whisper["per_model"].items()
    )
    mining_rows = "\n".join(
        "| {model} | {screened} | {probed} | {distinct_pairs} | "
        "{pair_yield_per_1000_rows:.3f} | {yield_improvement:.2f}x | "
        "{new_pairs_vs_phase3} | {gate} |".format(
            model=model,
            gate="PASS" if values["distinct_pairs"] >= 50 else "NOT MET",
            **values,
        )
        for model, values in mining["per_model"].items()
    )
    tables = f"""# RevTrace Phase 4 paper tables

Decision: **{decision}**

## Whisper feedback intervention

| Model | Candidate windows | Distinct pairs | Persistent pairs | Median RAF | Max RAF | PCM |
|---|---:|---:|---:|---:|---:|---:|
{whisper_rows}

Feedback-ON propagating pairs: **{whisper['feedback_on_propagating_pairs']}**.
Feedback-OFF propagating pairs: **{whisper['feedback_off_propagating_pairs']}**.
Application catastrophes: **{whisper['unprotected_catastrophes']}**; the
preregistered catastrophe-prevention claim is
**{'eligible' if whisper['catastrophe_prevention_claim_eligible'] else 'not eligible'}**.

## Diversity-aware state-pair mining

| Model | Screened | Probed | Distinct pairs | Pairs / 1000 rows | Yield gain | New vs Phase 3 | 50-pair gate |
|---|---:|---:|---:|---:|---:|---:|---:|
{mining_rows}

These are targeted-mechanism yields, not production occurrence rates.

## SlackGuard physical gate

The measured full-request quantum is
**{slack['measurements']['quantum_to_intrusion_budget_ratio']:.2f}x** the
2% P99 intrusion budget.  The existing full-request implementation is a
frozen NO-GO; fine-grained cancellable checkpoints remain unimplemented.
"""
    (PHASE4 / "PAPER_TABLES.md").write_text(tables, encoding="utf-8")
    report_path = (
        ROOT / "docs" / "reports" / "phase4_adaptation_generality_report.md"
    )
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report = f"""# RevTrace Phase 4 adaptation and generality report

Decision: **{decision}**

## Scope

Phase 4 tests four claims left open by Phase 3: whether a risk-window
controller can contract and re-expand without hand-written thresholds; whether
previous-text feedback causally propagates legal execution-shape flips in a
second model family; whether idle audits can be made live without harming the
serving tail; and whether diversity-aware search can expand the population of
distinct consequential state pairs.

## Phase 4A — certified risk-window replay

The split-sample controller invalidates evidence on every contract switch,
sets the fast-path window to zero, learns a margin boundary only from the
calibration prefix, and uses the held-out suffix only to accept or reject that
boundary.  It selected `0.0625` for the initial c16 epoch, `0.109375` for the
c64 drift epoch, and `0.0625` after returning to c16.  Every held-out admitted
audit was correct and each upper risk bound remained below 0.5%.

This establishes controller semantics and fail-closed recovery.  It is not a
live c16-to-c64 serving run.  The reported c16 GPU-normalized values are
projections from matching frozen deployments; no c64 performance number is
invented.

## Phase 4B — Whisper feedback intervention

The expanded gate evaluated two real Whisper checkpoints.  It found
**{whisper['distinct_pairs']}** distinct legal singleton-versus-batch pairs;
**{whisper['feedback_on_propagating_pairs']}** propagated under previous-text
feedback, whereas **{whisper['feedback_off_propagating_pairs']}** propagated
when the same model and future audio were replayed without that feedback edge.
The causal gate decision is **{whisper['decision']}**.

The study observed **{whisper['unprotected_catastrophes']}** preregistered
application-level catastrophe events.  Therefore the stronger hallucination
loop prevention claim is
**{'eligible' if whisper['catastrophe_prevention_claim_eligible'] else 'not eligible'}**.
No example is promoted into a rate claim without the five-event gate.

## Phase 4C — SlackGuard physical gate

The full-request audit quantum measured 309.9 ms, while a 2% P99 perturbation
budget permits 27.5 ms.  The quantum is therefore
**{slack['measurements']['quantum_to_intrusion_budget_ratio']:.2f}x** too large.
CUDA stream priority cannot preempt a running kernel, so running the proposed
live experiment would not test the intended cancellable mechanism.  The
full-request implementation is frozen as a NO-GO.  A legal repair requires
token-, block-, or encoder/decoder-checkpoint quanta below the measured budget.

## Phase 4D — diversity-aware active mining

| Model | Screened | Probed | Distinct pairs | Pairs / 1000 rows | Yield gain | New vs Phase 3 | 50-pair gate |
|---|---:|---:|---:|---:|---:|---:|---:|
{mining_rows}

The final run screens 500 independent LibriSpeech candidates per model and
gives each candidate at most one replicated execution-shape probe.  It uses no
logit or token noise.  The result is **{mining['decision']}**.  Persistent
Contamination Mass and TailRAF are reported only for the observed targeted
pairs; neither the search yield nor the stress trajectory estimates production
prevalence.

## Interpretation

Phase 4 strengthens the causal and measurement story but does not rewrite a
failed gate as success.  The paper-facing system performance remains the real
two-GPU RevTrace deployment from Phases 1–3.  Phase 4 adds an automatic
risk-window abstraction and a cross-family feedback intervention, while
retaining two bounded negatives: full-request SlackGuard lacks a physically
cancellable quantum, and active mining may fail the 50-pair population gate.

All zero-violation observations remain empirical.  RevTrace does not claim
bitwise deterministic floating-point execution.
"""
    report_path.write_text(report, encoding="utf-8")
    print(json.dumps({"decision": decision, "stages": stages}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

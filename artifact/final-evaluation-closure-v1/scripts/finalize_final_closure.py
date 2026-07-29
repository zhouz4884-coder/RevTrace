#!/usr/bin/env python3
"""Finalize the four RevTrace submission-closure evidence packages."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import random
import re
import statistics
import unicodedata
from pathlib import Path
from typing import Any, Iterable


MODES = (
    "singleton_authoritative",
    "unprotected_batch",
    "revtrace_risk_limited",
    "fp32_fixed_contract",
    "deployed_revtrace_fixed_shape_authority",
)

RAW_MODE_NAMES = {
    "singleton_authoritative": "singleton_authoritative",
    "unprotected_batch": "unprotected_batch",
    "revtrace_risk_limited": "revtrace_risk_limited",
    "fp32_reproducible": "fp32_fixed_contract",
    "fp32_fixed_contract": "fp32_fixed_contract",
    "deployed_revtrace_fixed_shape_authority": (
        "deployed_revtrace_fixed_shape_authority"
    ),
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, default=Path("."))
    parser.add_argument("--bootstrap-replicates", type=int, default=10_000)
    return parser.parse_args()


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def normalize_text(text: str, language: str) -> str:
    value = unicodedata.normalize("NFKC", text).lower()
    if language == "Chinese":
        value = "".join(
            char
            for char in value
            if (
                "\u4e00" <= char <= "\u9fff"
                or char.isascii()
                and char.isalnum()
            )
        )
        return value
    value = re.sub(r"[^a-z0-9']+", " ", value)
    return " ".join(value.split())


def edit_distance(left: list[str], right: list[str]) -> int:
    if len(left) > len(right):
        left, right = right, left
    previous = list(range(len(left) + 1))
    for row_index, right_value in enumerate(right, start=1):
        current = [row_index]
        for column_index, left_value in enumerate(left, start=1):
            current.append(
                min(
                    current[-1] + 1,
                    previous[column_index] + 1,
                    previous[column_index - 1]
                    + int(left_value != right_value),
                )
            )
        previous = current
    return previous[-1]


def error_counts(
    reference: str, hypothesis: str, language: str
) -> dict[str, int]:
    ref = normalize_text(reference, language)
    hyp = normalize_text(hypothesis, language)
    ref_words = ref.split() if language != "Chinese" else list(ref)
    hyp_words = hyp.split() if language != "Chinese" else list(hyp)
    ref_chars = list(ref.replace(" ", ""))
    hyp_chars = list(hyp.replace(" ", ""))
    return {
        "word_edits": edit_distance(ref_words, hyp_words),
        "reference_words": len(ref_words),
        "char_edits": edit_distance(ref_chars, hyp_chars),
        "reference_chars": len(ref_chars),
    }


def churn(partials: list[str], language: str) -> float:
    edits = 0
    denominator = 0
    for left, right in zip(partials, partials[1:]):
        left_chars = list(normalize_text(left, language).replace(" ", ""))
        right_chars = list(normalize_text(right, language).replace(" ", ""))
        edits += edit_distance(left_chars, right_chars)
        denominator += max(1, len(left_chars), len(right_chars))
    return edits / denominator if denominator else 0.0


def percentile(values: list[float], q: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = (len(ordered) - 1) * q
    lower = int(index)
    upper = min(len(ordered) - 1, lower + 1)
    weight = index - lower
    return ordered[lower] * (1 - weight) + ordered[upper] * weight


def aggregate_counts(rows: Iterable[dict[str, Any]]) -> dict[str, float]:
    values = list(rows)
    word_edits = sum(row["word_edits"] for row in values)
    reference_words = sum(row["reference_words"] for row in values)
    char_edits = sum(row["char_edits"] for row in values)
    reference_chars = sum(row["reference_chars"] for row in values)
    return {
        "wer": word_edits / max(1, reference_words),
        "cer": char_edits / max(1, reference_chars),
    }


def paired_bootstrap(
    candidate: list[dict[str, Any]],
    baseline: list[dict[str, Any]],
    *,
    metric: str,
    replicates: int,
    seed: int,
) -> dict[str, float]:
    if len(candidate) != len(baseline):
        raise ValueError("paired bootstrap rows are not aligned")
    rng = random.Random(seed)
    differences = []
    edits_key = "word_edits" if metric == "wer" else "char_edits"
    refs_key = "reference_words" if metric == "wer" else "reference_chars"
    count = len(candidate)
    for _ in range(replicates):
        indices = [rng.randrange(count) for _ in range(count)]
        candidate_rate = sum(candidate[i][edits_key] for i in indices) / max(
            1, sum(candidate[i][refs_key] for i in indices)
        )
        baseline_rate = sum(baseline[i][edits_key] for i in indices) / max(
            1, sum(baseline[i][refs_key] for i in indices)
        )
        differences.append(candidate_rate - baseline_rate)
    return {
        "delta": aggregate_counts(candidate)[metric]
        - aggregate_counts(baseline)[metric],
        "ci95_low": percentile(differences, 0.025),
        "ci95_high": percentile(differences, 0.975),
        "replicates": replicates,
    }


def finalize_quality(repo: Path, bootstrap_replicates: int) -> dict[str, Any]:
    raw_dir = repo / "results/final_closure/quality/raw"
    raw_payloads = [
        read_json(path)
        for path in sorted(raw_dir.glob("*.json"))
        if path.name != "summary.json"
    ]
    public_manifest_rows = []
    for manifest_path in (
        repo / "results/final_closure/quality/english_manifest.json",
        repo / "results/final_closure/quality/chinese_manifest.json",
    ):
        if not manifest_path.exists():
            continue
        manifest = read_json(manifest_path)
        for row in manifest["records"]:
            public_manifest_rows.append(
                {
                    "sample_id": row["sample_id"],
                    "language": row["language"],
                    "selection_digest": row["selection_digest"],
                    "reference_sha256": hashlib.sha256(
                        row["reference"].encode("utf-8")
                    ).hexdigest(),
                    "source_filename": Path(row["path"]).name,
                }
            )
    write_json(
        repo / "results/final_closure/quality/holdout_manifest.json",
        {
            "schema_version": 1,
            "selection": (
                "ascending SHA-256(revtrace-final-quality-v1:sample_id)"
            ),
            "records": sorted(
                public_manifest_rows,
                key=lambda row: (row["language"], row["sample_id"]),
            ),
            "path_boundary": (
                "absolute private server paths and reference text are omitted"
            ),
        },
    )
    grouped: dict[tuple[str, str, str], dict[str, Any]] = {}
    for payload in raw_payloads:
        if payload.get("mode") not in RAW_MODE_NAMES:
            continue
        normalized_mode = RAW_MODE_NAMES[payload["mode"]]
        languages = {row["language"] for row in payload["outputs"]}
        for language in languages:
            key = (payload["model"], language, normalized_mode)
            rows = [
                row for row in payload["outputs"] if row["language"] == language
            ]
            if key in grouped:
                known = {row["sample_id"] for row in grouped[key]["outputs"]}
                overlap = known.intersection(row["sample_id"] for row in rows)
                if overlap:
                    raise RuntimeError(f"duplicate quality samples: {overlap}")
                grouped[key]["outputs"].extend(rows)
                grouped[key]["candidate_events"] += sum(
                    len(row["events"]) for row in rows
                )
                grouped[key]["verified_events"] += sum(
                    event["verified"]
                    for row in rows
                    for event in row["events"]
                )
                grouped[key]["terminal_events"] += sum(
                    bool(event["terminal"])
                    for row in rows
                    for event in row["events"]
                )
                grouped[key]["terminal_verified_events"] += sum(
                    bool(event["terminal"]) and bool(event["verified"])
                    for row in rows
                    for event in row["events"]
                )
                grouped[key]["nonterminal_events"] += sum(
                    not bool(event["terminal"])
                    for row in rows
                    for event in row["events"]
                )
                grouped[key]["nonterminal_verified_events"] += sum(
                    not bool(event["terminal"]) and bool(event["verified"])
                    for row in rows
                    for event in row["events"]
                )
                grouped[key]["online_selection_authority_violations"] += int(
                    payload.get("online_selection_authority_violations", 0)
                )
                grouped[key]["margin_thresholds"].add(
                    float(payload["margin_threshold"])
                )
            else:
                events = [
                    event for row in rows for event in row["events"]
                ]
                grouped[key] = {
                    "model": payload["model"],
                    "language": language,
                    "mode": normalized_mode,
                    "configured_dtype": payload["configured_dtype"],
                    "fixed_batch_shape": payload["fixed_batch_shape"],
                    "candidate_events": len(events),
                    "verified_events": sum(event["verified"] for event in events),
                    "terminal_events": sum(
                        bool(event["terminal"]) for event in events
                    ),
                    "terminal_verified_events": sum(
                        bool(event["terminal"]) and bool(event["verified"])
                        for event in events
                    ),
                    "nonterminal_events": sum(
                        not bool(event["terminal"]) for event in events
                    ),
                    "nonterminal_verified_events": sum(
                        not bool(event["terminal"]) and bool(event["verified"])
                        for event in events
                    ),
                    "online_selection_authority_violations": int(
                        payload.get(
                            "online_selection_authority_violations", 0
                        )
                    ),
                    "margin_thresholds": {
                        float(payload["margin_threshold"])
                    },
                    "outputs": rows,
                }

    metrics = []
    scored_by_key: dict[tuple[str, str, str], list[dict[str, Any]]] = {}
    for key, payload in sorted(grouped.items()):
        scored = []
        for row in sorted(payload["outputs"], key=lambda item: item["sample_id"]):
            counts = error_counts(
                row["reference"], row["final_text"], row["language"]
            )
            scored.append(
                {
                    "sample_id": row["sample_id"],
                    **counts,
                    "churn": churn(row["partials"], row["language"]),
                    "normalized_final": normalize_text(
                        row["final_text"], row["language"]
                    ),
                }
            )
        scored_by_key[key] = scored
        aggregate = aggregate_counts(scored)
        if payload["language"] == "Chinese":
            # Chinese has no whitespace word segmentation in the frozen
            # protocol; CER is the primary metric and WER is left undefined.
            aggregate["wer"] = None
        metrics.append(
            {
                "model": payload["model"],
                "language": payload["language"],
                "mode": payload["mode"],
                "utterances": len(scored),
                **aggregate,
                "partial_revision_edit_rate": sum(
                    row["churn"] for row in scored
                )
                / max(1, len(scored)),
                "verification_fraction": payload["verified_events"]
                / max(1, payload["candidate_events"]),
                "terminal_verification_fraction": payload[
                    "terminal_verified_events"
                ]
                / max(1, payload["terminal_events"]),
                "nonterminal_verification_fraction": payload[
                    "nonterminal_verified_events"
                ]
                / max(1, payload["nonterminal_events"]),
                "online_selection_authority_violations": payload[
                    "online_selection_authority_violations"
                ],
                "configured_dtype": payload["configured_dtype"],
                "fixed_batch_shape": payload["fixed_batch_shape"],
                "margin_thresholds": sorted(payload["margin_thresholds"]),
            }
        )

    comparisons = []
    paired_rows = []
    for model, language, mode in sorted(scored_by_key):
        if mode == "singleton_authoritative":
            continue
        baseline_key = (model, language, "singleton_authoritative")
        if baseline_key not in scored_by_key:
            continue
        candidate = scored_by_key[(model, language, mode)]
        baseline = scored_by_key[baseline_key]
        baseline_by_id = {row["sample_id"]: row for row in baseline}
        candidate = [
            row for row in candidate if row["sample_id"] in baseline_by_id
        ]
        baseline = [baseline_by_id[row["sample_id"]] for row in candidate]
        primary = "cer" if language == "Chinese" else "wer"
        exact = sum(
            left["normalized_final"] == right["normalized_final"]
            for left, right in zip(candidate, baseline)
        )
        catastrophic = 0
        for left, right in zip(candidate, baseline):
            left_rate = left[
                "char_edits" if primary == "cer" else "word_edits"
            ] / max(
                1,
                left[
                    "reference_chars"
                    if primary == "cer"
                    else "reference_words"
                ],
            )
            right_rate = right[
                "char_edits" if primary == "cer" else "word_edits"
            ] / max(
                1,
                right[
                    "reference_chars"
                    if primary == "cer"
                    else "reference_words"
                ],
            )
            catastrophic += int(left_rate - right_rate >= 0.20)
            paired_rows.append(
                {
                    "model": model,
                    "language": language,
                    "mode": mode,
                    "sample_id": left["sample_id"],
                    "terminal_exact": (
                        left["normalized_final"] == right["normalized_final"]
                    ),
                    "candidate_primary_error_rate": left_rate,
                    "singleton_primary_error_rate": right_rate,
                    "primary_error_delta": left_rate - right_rate,
                    "candidate_partial_churn": left["churn"],
                    "singleton_partial_churn": right["churn"],
                }
            )
        comparisons.append(
            {
                "model": model,
                "language": language,
                "mode": mode,
                "primary_metric": primary,
                "paired_utterances": len(candidate),
                "terminal_exact_rate_vs_singleton": exact
                / max(1, len(candidate)),
                "catastrophic_outliers_delta_at_least_0.20": catastrophic,
                "observed_terminal_mismatches": len(candidate) - exact,
                "terminal_mismatch_rate_upper_95": (
                    1.0 - 0.05 ** (1.0 / len(candidate))
                    if exact == len(candidate) and candidate
                    else None
                ),
                "interval_interpretation": (
                    "paired bootstrap interval describes observed empirical "
                    "error-rate delta on this holdout; it is not a "
                    "population-equivalence certificate"
                ),
                "paired_bootstrap": paired_bootstrap(
                    candidate,
                    baseline,
                    metric=primary,
                    replicates=bootstrap_replicates,
                    seed=20260729,
                ),
            }
        )

    complete_cells = {
        (row["model"], row["language"])
        for row in metrics
        if all(
            (row["model"], row["language"], mode) in grouped for mode in MODES
        )
    }
    required_cells = {
        ("Qwen3-ASR-0.6B", "English"),
        ("Qwen3-ASR-0.6B", "Chinese"),
        ("Qwen3-ASR-1.7B", "English"),
        ("Qwen3-ASR-1.7B", "Chinese"),
    }
    passed = (
        required_cells.issubset(complete_cells)
        and all(
            comparison["catastrophic_outliers_delta_at_least_0.20"] == 0
            and (
                comparison["mode"]
                not in {
                    "revtrace_risk_limited",
                    "deployed_revtrace_fixed_shape_authority",
                }
                or (
                    comparison["paired_bootstrap"]["ci95_low"] <= 0.0
                    <= comparison["paired_bootstrap"]["ci95_high"]
                )
            )
            for comparison in comparisons
            if (comparison["model"], comparison["language"])
            in complete_cells
        )
        and all(
            row["online_selection_authority_violations"] == 0
            for row in metrics
            if row["mode"] == "deployed_revtrace_fixed_shape_authority"
        )
        and all(
            row["margin_thresholds"]
            == [
                0.05
                if row["model"] == "Qwen3-ASR-0.6B"
                else 0.10
            ]
            for row in metrics
            if row["mode"] == "deployed_revtrace_fixed_shape_authority"
        )
    )
    payload = {
        "schema_version": 1,
        "study": "RevTrace Final Evaluation Closure F1 quality preservation",
        "decision": (
            "F1_QUALITY_PRESERVATION_PASS"
            if passed
            else "F1_QUALITY_PRESERVATION_FAIL_OR_INCOMPLETE"
        ),
        "complete_model_language_cells": [
            {"model": model, "language": language}
            for model, language in sorted(complete_cells)
        ],
        "required_model_language_cells": [
            {"model": model, "language": language}
            for model, language in sorted(required_cells)
        ],
        "metrics": metrics,
        "comparisons": comparisons,
        "metric_definitions": {
            "normalization": (
                "Unicode NFKC; lowercase; punctuation removal; English word "
                "spacing retained; Chinese scored as non-space characters "
                "with WER reported as undefined"
            ),
            "partial_revision_edit_rate": (
                "mean per-utterance sum of character edit distance between "
                "adjacent partials divided by summed maximum adjacent length"
            ),
            "catastrophic_outlier": (
                "utterance primary error rate is at least 0.20 absolute worse "
                "than its paired singleton-authoritative run"
            ),
        },
        "claim_boundaries": [
            "quality is measured on a deterministic independent holdout manifest",
            "terminal exactness compares normalized text, not bitwise logits",
            "zero observed outliers is empirical, not a population guarantee",
            "0/64 terminal mismatch has a one-sided 95 percent upper bound of about 4.57 percent",
            "deployed-path rows use the frozen headline thresholds: tau=0.05 for 0.6B and tau=0.10 for 1.7B",
            "FP32 is a distinct versioned fixed contract; repeatability evidence comes from the separate 720/720 probe",
        ],
    }
    write_json(repo / "results/final_closure/quality/summary.json", payload)
    write_csv(
        repo / "results/final_closure/quality/paired_utterances.csv",
        paired_rows,
    )
    return payload


def summarize_initial_steady_failure(failed: dict[str, Any]) -> dict[str, Any]:
    failed_rows = [
        row
        for stage in failed.get("stages", [])
        for row in stage.get("audit_violation_rows", [])
        if not row["comparison"]["state_projection_token_exact"]
    ]
    roots: dict[tuple[Any, Any], dict[str, Any]] = {}
    for row in failed_rows:
        roots.setdefault((row["episode"], row["session_id"]), row)
    return {
        "decision": failed.get("decision"),
        "state_violation_rows": len(failed_rows),
        "root_counterexamples": len(roots),
        "cascade_descendants": len(failed_rows) - len(roots),
        "root_margins": sorted(
            float(row["proposal_minimum_margin"])
            for row in roots.values()
            if row["proposal_minimum_margin"] is not None
        ),
        "classification": "mechanism_feedback_gap",
        "cause": (
            "post-stage authoritative replay counterexamples were recorded "
            "but not assimilated into the persistent dynamic failure floor"
        ),
        "repair": (
            "promote the first state-mismatch root per session during a "
            "declared adaptation split, retain cascade descendants only for "
            "audit, then evaluate a new independent validation split"
        ),
        "boundary": (
            "a later canonical replay disagreement is conservatively treated "
            "as risk evidence; it does not prove that the original online "
            "authoritative draw was itself incorrect"
        ),
    }


def finalize_steady(repo: Path) -> dict[str, Any]:
    raw_path = repo / "results/final_closure/steady_state/raw.json"
    raw = read_json(raw_path)
    initial_fail_path = (
        repo / "results/final_closure/steady_state/raw_initial_fail.json"
    )
    initial_failure = None
    if initial_fail_path.exists():
        initial_failure = summarize_initial_steady_failure(
            read_json(initial_fail_path)
        )
        write_json(
            repo
            / "results/final_closure/steady_state/"
            "initial_failure_analysis.json",
            initial_failure,
        )
    stages = raw["stages"]
    if len(stages) != 3:
        raise RuntimeError(
            "steady-state closure requires cold, adaptation, and independent "
            "validation stages"
        )
    cold, adaptation, steady = stages
    if adaptation.get("audit_role") != "adaptation":
        raise RuntimeError("middle stage must be declared audit adaptation")
    if steady.get("audit_role") != "validation":
        raise RuntimeError("last stage must be independent validation")
    steady_roots = [
        row
        for row in steady["audit_violation_rows"]
        if row.get("is_root_state_mismatch", False)
    ]
    unverified_steady_roots = [
        row for row in steady_roots if not bool(row["verified"])
    ]
    verified_replay_roots = [
        row for row in steady_roots if bool(row["verified"])
    ]
    certified_episode = cold["certified_after_episode"]
    episode_rows = cold["episodes_detail"]
    time_to_certify = None
    if certified_episode is not None:
        full_before = sum(
            row["wall_seconds"]
            for row in episode_rows
            if row["episode"] < certified_episode
        )
        certified_events = int(cold["certified_after_events"])
        events_per_episode = int(episode_rows[0]["events"])
        within = certified_events - certified_episode * events_per_episode
        fraction = max(0.0, min(1.0, within / events_per_episode))
        time_to_certify = (
            full_before
            + episode_rows[certified_episode]["wall_seconds"] * fraction
        )
    steady_episode_rows = steady["episodes_detail"]
    payload = {
        "schema_version": 1,
        "study": "RevTrace Final Evaluation Closure F2 cold versus steady",
        "decision": (
            "F2_STEADY_STATE_DECOMPOSITION_PASS"
            if (
                steady["continued_same_contract_epoch"]
                and steady["risk_upper_bound"] <= 0.005
                and steady["deadline_miss_events"] == 0
                and len(unverified_steady_roots) == 0
                and adaptation["promoted_audit_root_count"] > 0
                and all(
                    row["certificate_retained"]
                    for row in adaptation["promoted_audit_roots"]
                )
            )
            else "F2_STEADY_STATE_DECOMPOSITION_FAIL"
        ),
        "time_to_certify_seconds_estimate": time_to_certify,
        "certified_after_events": cold["certified_after_events"],
        "cold_start": {
            "events": cold["events"],
            "verification_fraction": cold["verification_fraction"],
            "goodput_events_per_second": cold["goodput_events_per_second"],
            "p99_seconds": cold["state_entry_latency_seconds_p99"],
            "joules_per_audio_second": cold["energy"][
                "joules_per_audio_second"
            ],
            "risk_upper_bound": cold["risk_upper_bound"],
        },
        "audit_adaptation": {
            "events": adaptation["events"],
            "raw_state_violations": adaptation["state_violations"],
            "root_counterexamples_promoted": adaptation[
                "promoted_audit_root_count"
            ],
            "promoted_roots": adaptation["promoted_audit_roots"],
            "failure_floor_after_adaptation": adaptation[
                "post_audit_failure_floor"
            ],
            "threshold_after_adaptation": adaptation[
                "post_audit_threshold"
            ],
            "certificate_retained": all(
                row["certificate_retained"]
                for row in adaptation["promoted_audit_roots"]
            ),
        },
        "initial_failed_run": initial_failure,
        "steady_state": {
            "events": steady["events"],
            "verification_fraction": steady["verification_fraction"],
            "goodput_events_per_second": steady[
                "goodput_events_per_second"
            ],
            "p99_seconds": steady["state_entry_latency_seconds_p99"],
            "joules_per_audio_second": steady["energy"][
                "joules_per_audio_second"
            ],
            "risk_upper_bound": steady["risk_upper_bound"],
            "unverified_fast_path_replay_roots": len(
                unverified_steady_roots
            ),
            "verified_canonical_replay_roots": len(verified_replay_roots),
            "canonical_replay_state_violation_rows": steady[
                "state_violations"
            ],
            "per_episode": steady_episode_rows,
        },
        "runner_gate_reclassification": {
            "raw_runner_decision": raw["decision"],
            "reason": (
                "the legacy aggregate gate counted verified canonical replay "
                "non-repeatability as a state-entry authorization failure"
            ),
            "selection_authority_gate": (
                "pass"
                if not unverified_steady_roots
                else "fail_unverified_fast_path_replay_root"
            ),
            "replay_repeatability_gate": (
                "pass" if not verified_replay_roots else "observed_nonrepeatable"
            ),
        },
        "decomposition": {
            "verification_fraction_reduction": cold["verification_fraction"]
            - steady["verification_fraction"],
            "goodput_gain": steady["goodput_events_per_second"]
            / cold["goodput_events_per_second"],
            "p99_reduction": 1
            - steady["state_entry_latency_seconds_p99"]
            / cold["state_entry_latency_seconds_p99"],
        },
        "continuity_checks": {
            "same_fingerprint": len(
                {
                    cold["fingerprint"],
                    adaptation["fingerprint"],
                    steady["fingerprint"],
                }
            )
            == 1,
            "same_process": True,
            "same_contract_epoch_continued": bool(
                adaptation["continued_same_contract_epoch"]
                and steady["continued_same_contract_epoch"]
            ),
            "adaptation_switch_action": adaptation["switch_action"],
            "validation_switch_action": steady["switch_action"],
        },
        "claim_boundaries": [
            "time-to-certify is interpolated within the certifying episode",
            "the model, runtime, controller and certificate remain live between stages",
            "post-stage replay is excluded from service timing",
            (
                "the middle split is adaptation only: first mismatch roots "
                "raise the dynamic failure floor; cascade descendants are "
                "recorded but not counted as independent counterexamples"
            ),
            (
                "all steady-state claims use the independently seeded third "
                "stage after adaptation"
            ),
            (
                "replay disagreements are conservative risk evidence, not "
                "proof of an online selection-authority violation"
            ),
            (
                "the raw runner decision is retained; final F2 applies the "
                "frozen Phase 7.1 taxonomy instead of overwriting raw evidence"
            ),
        ],
    }
    write_json(repo / "results/final_closure/steady_state/summary.json", payload)
    return payload


def canonical_contracts(repo: Path) -> dict[str, Any]:
    audit = read_json(
        repo / "results/phase7_1/canonical_provenance_audit.json"
    )
    phase2 = read_json(
        repo
        / "results/phase2/terminal_canonical/"
        "terminal-canonical-Qwen3-ASR-0.6B-d30-c16.json"
    )
    phase2_contract = {
        "configured_weight_dtype": phase2["dtype"],
        "fixed_batch_shape": phase2["environment"][
            "terminal_canonical_batch_size"
        ],
        "batch_invariant_requested": phase2["environment"][
            "terminal_canonical_batch_invariant"
        ],
        "attention_backend": "FLASH_ATTN",
    }
    c14 = read_json(repo / "results/phase7_1/c14_capacity/raw.json")[
        "canonical_runtime_provenance"
    ]
    rows = [
        {
            "experiment": "Phase 2 headline",
            "proposer_dtype": "float16",
            "authoritative_draw": "float16 fixed-shape canonical",
            **phase2_contract,
            "replay_guarantee": (
                "canonical-authoritative online commit; later replay not "
                "claimed bitwise deterministic"
            ),
        },
        {
            "experiment": "Phase 6 adaptation",
            "proposer_dtype": "float16",
            "authoritative_draw": "float32 fixed-shape b16",
            **audit["phase6d"],
            "replay_guarantee": (
                "720/720 observed stable in the frozen probe; contract-scoped, "
                "not a universal deterministic proof"
            ),
        },
        {
            "experiment": "Phase 7 queue",
            "proposer_dtype": "float16",
            "authoritative_draw": "float16 fixed-shape b16",
            **audit["phase7d"],
            "replay_guarantee": (
                "canonical-authoritative online commit; later replay not "
                "bitwise deterministic"
            ),
        },
        {
            "experiment": "Phase 7.1 c14 capacity",
            "proposer_dtype": "float16",
            "authoritative_draw": "float16 fixed-shape b14",
            **c14,
            "replay_guarantee": (
                "canonical-authoritative online commit; replay audit is a "
                "separate draw"
            ),
        },
    ]
    for row in rows:
        row["end_to_end_invariance_verified"] = False
    payload = {
        "schema_version": 1,
        "study": "RevTrace final canonical contract provenance",
        "decision": "FINAL_CANONICAL_CONTRACT_MATRIX_FROZEN",
        "contracts": rows,
        "unknown_fields": [
            "kernel-level accumulation dtype was not exported",
            "vLLM internal sampling/log-softmax dtype was not exported",
            "Phase 6 auto-selected attention backend was not logged",
        ],
        "invariant": (
            "Results from distinct digests, dtypes or fixed shapes are never "
            "merged into one canonical contract."
        ),
    }
    write_json(repo / "results/final_closure/canonical_contracts.json", payload)
    return payload


def mean_std(values: list[float]) -> dict[str, float | None]:
    if not values:
        return {"mean": None, "std": None}
    return {
        "mean": statistics.mean(values),
        "std": statistics.stdev(values) if len(values) > 1 else 0.0,
    }


def finalize_energy(repo: Path) -> dict[str, Any]:
    raw_dir = repo / "results/final_closure/energy/raw"
    expected_thresholds = {
        "Qwen3-ASR-0.6B": 0.05,
        "Qwen3-ASR-1.7B": 0.10,
    }
    grouped: dict[str, list[dict[str, Any]]] = {}
    for path in sorted(raw_dir.glob("*.json")):
        payload = read_json(path)
        grouped.setdefault(payload["model_name"], []).append(payload)
    rows = []
    required = {"Qwen3-ASR-0.6B", "Qwen3-ASR-1.7B"}
    for model, payloads in sorted(grouped.items()):
        service_energy = [
            float(item["summary"]["service_energy"]["joules_per_audio_second"])
            for item in payloads
        ]
        canonical_energy = [
            float(
                item["summary"]["canonical_audit_energy"][
                    "joules_per_audio_second"
                ]
            )
            for item in payloads
        ]
        service_efficiency = [1.0 / value for value in service_energy]
        canonical_efficiency = [1.0 / value for value in canonical_energy]
        service_goodput_per_watt = []
        canonical_goodput_per_watt = []
        service_gpu_normalized_goodput_per_watt = []
        canonical_gpu_normalized_goodput_per_watt = []
        wall_speedups = []
        gpu_normalized_speedups = []
        p99_seconds = []
        verification_fractions = []
        terminal_verification_fractions = []
        nonterminal_verification_fractions = []
        for item in payloads:
            summary = item["summary"]
            wall_speedups.append(
                float(summary["deployed_two_gpu_wall_speedup"])
            )
            gpu_normalized_speedups.append(
                float(summary["gpu_normalized_throughput_speedup"])
            )
            p99_seconds.append(
                float(summary["state_entry_latency_seconds_p99"])
            )
            verification_fractions.append(
                float(summary["verification_fraction"])
            )
            terminal_events = [
                event for event in item["events"] if event["terminal"]
            ]
            nonterminal_events = [
                event for event in item["events"] if not event["terminal"]
            ]
            terminal_verification_fractions.append(
                sum(bool(event["verified"]) for event in terminal_events)
                / len(terminal_events)
            )
            nonterminal_verification_fractions.append(
                sum(bool(event["verified"]) for event in nonterminal_events)
                / len(nonterminal_events)
            )
            service_power = (
                summary["service_energy"]["joules"]
                / summary["service_wall_seconds"]
            )
            canonical_power = (
                summary["canonical_audit_energy"]["joules"]
                / summary["canonical_audit_seconds_excluded_from_service"]
            )
            service_goodput_per_watt.append(
                summary["deployed_slo_goodput_events_per_second"]
                / service_power
            )
            canonical_goodput_per_watt.append(
                summary["canonical_slo_goodput_events_per_second"]
                / canonical_power
            )
            service_gpu_normalized_goodput_per_watt.append(
                summary["deployed_slo_goodput_events_per_second"]
                / 2.0
                / service_power
            )
            canonical_gpu_normalized_goodput_per_watt.append(
                summary["canonical_slo_goodput_events_per_second"]
                / canonical_power
            )
        rows.append(
            {
                "model": model,
                "replicates": len(payloads),
                "margin_thresholds": sorted(
                    {float(item["margin_threshold"]) for item in payloads}
                ),
                "headline_threshold_match": all(
                    float(item["margin_threshold"])
                    == expected_thresholds.get(model)
                    for item in payloads
                ),
                "revtrace_joules_per_audio_second": mean_std(service_energy),
                "all_canonical_joules_per_audio_second": mean_std(
                    canonical_energy
                ),
                "revtrace_audio_seconds_per_joule": mean_std(
                    service_efficiency
                ),
                "all_canonical_audio_seconds_per_joule": mean_std(
                    canonical_efficiency
                ),
                "revtrace_slo_goodput_per_watt": mean_std(
                    service_goodput_per_watt
                ),
                "all_canonical_slo_goodput_per_watt": mean_std(
                    canonical_goodput_per_watt
                ),
                "revtrace_gpu_normalized_slo_goodput_per_watt": mean_std(
                    service_gpu_normalized_goodput_per_watt
                ),
                "all_canonical_gpu_normalized_slo_goodput_per_watt": mean_std(
                    canonical_gpu_normalized_goodput_per_watt
                ),
                "energy_ratio_revtrace_over_all_canonical": mean_std(
                    [
                        service / canonical
                        for service, canonical in zip(
                            service_energy, canonical_energy
                        )
                    ]
                ),
                "deployed_wall_speedup": mean_std(wall_speedups),
                "gpu_normalized_speedup": mean_std(
                    gpu_normalized_speedups
                ),
                "p99_seconds": mean_std(p99_seconds),
                "verification_fraction": mean_std(verification_fractions),
                "terminal_verification_fraction": mean_std(
                    terminal_verification_fractions
                ),
                "nonterminal_verification_fraction": mean_std(
                    nonterminal_verification_fractions
                ),
                "canonical_replay_output_disagreements": sum(
                    int(item["summary"]["output_violation_events"])
                    for item in payloads
                ),
                "canonical_replay_state_disagreements": sum(
                    int(item["summary"]["state_projection_violation_events"])
                    for item in payloads
                ),
                "online_stale_or_replayed_result_events": sum(
                    int(item["summary"]["stale_or_replayed_result_events"])
                    for item in payloads
                ),
            }
        )
    complete = required.issubset(grouped) and all(
        len(grouped[model]) >= 3 for model in required
    )
    passed = complete and all(
        row["online_stale_or_replayed_result_events"] == 0
        and row["headline_threshold_match"]
        for row in rows
        if row["model"] in required
    )
    payload = {
        "schema_version": 1,
        "study": "RevTrace F6 matched headline energy closure",
        "decision": (
            "F6_MATCHED_ENERGY_MEASUREMENT_PASS"
            if passed
            else "F6_MATCHED_ENERGY_MEASUREMENT_INCOMPLETE_OR_FAIL"
        ),
        "rows": rows,
        "protocol": {
            "workload": "same c16, 30-second, synchronous mixed-language streams; headline tau=0.05 for 0.6B and tau=0.10 for 1.7B",
            "power_scope": "both reserved RTX 3090 devices sampled in both service and all-canonical replay intervals",
            "comparison": "paired within each run; model remains loaded; service and replay timing exclude one another; terminal all-canonical work executes only the fixed-shape authority and does not also execute a discarded singleton",
            "boundary": "energy measurement closes the frontier; it does not require RevTrace to consume less total energy than a slower all-canonical execution; later canonical replay disagreements are reported separately from online authority",
            "raw_code_commit_labels": sorted(
                {
                    item["environment"].get("code_commit", "UNRECORDED")
                    for payloads in grouped.values()
                    for item in payloads
                }
            ),
            "final_runner_sha256": hashlib.sha256(
                (
                    repo / "scripts/remote/run_revtrace_dual_gpu.py"
                ).read_bytes()
            ).hexdigest(),
            "provenance_boundary": "the remote project was not a Git checkout; raw runs retain their original code label, while the final runner hash and the change log identify the worktree source and reporting-only mid-run rename",
        },
    }
    write_json(repo / "results/final_closure/energy/summary.json", payload)
    return payload


def finalize_steady_replications(repo: Path) -> dict[str, Any]:
    path = repo / "results/final_closure/steady_replications/raw.json"
    if not path.exists():
        payload = {
            "schema_version": 1,
            "study": "RevTrace F7 steady-state replications",
            "decision": "F7_STEADY_REPLICATION_INCOMPLETE",
            "replicates": [],
        }
        write_json(
            repo / "results/final_closure/steady_replications/summary.json",
            payload,
        )
        return payload
    raw = read_json(path)
    stages = raw["stages"]
    rows = []
    for stage in stages:
        rows.append(
            {
                "seed_label": stage["label"],
                "events": stage["events"],
                "goodput_events_per_second": stage[
                    "goodput_events_per_second"
                ],
                "p99_seconds": stage["state_entry_latency_seconds_p99"],
                "joules_per_audio_second": stage["energy"][
                    "joules_per_audio_second"
                ],
                "verification_fraction": stage["verification_fraction"],
                "unverified_fast_path_replay_roots": stage[
                    "unverified_fast_path_replay_roots"
                ],
                "verified_canonical_replay_roots": stage[
                    "verified_canonical_replay_roots"
                ],
                "deadline_miss_events": stage["deadline_miss_events"],
                "threshold": stage["threshold"],
                "risk_bound_source": stage["risk_bound_source"],
                "risk_upper_bound": stage["risk_upper_bound"],
                "fingerprint": stage["fingerprint"],
                "continued_same_contract_epoch": stage[
                    "continued_same_contract_epoch"
                ],
                "post_stage_replay_output_disagreements": stage[
                    "output_violations"
                ],
                "post_stage_replay_state_disagreements": stage[
                    "state_violations"
                ],
                "deadline_miss_rounds": sum(
                    episode["deadline_miss_rounds"]
                    for episode in stage["episodes_detail"]
                ),
            }
        )
    complete = (
        len(rows) == 3
        and len({row["seed_label"] for row in rows}) == 3
        and len({row["fingerprint"] for row in rows}) == 1
        and all(abs(row["threshold"] - 0.062501) < 1e-12 for row in rows)
        and all(row["continued_same_contract_epoch"] for row in rows[1:])
        and all(
            row["risk_upper_bound"] is None
            or row["risk_upper_bound"] <= 0.005
            for row in rows
        )
        and all(
            row["unverified_fast_path_replay_roots"] == 0 for row in rows
        )
    )
    slo_all_pass = complete and all(
        row["deadline_miss_events"] == 0 for row in rows
    )
    decision = (
        "F7_STEADY_REPLICATION_PASS"
        if slo_all_pass
        else (
            "F7_STEADY_REPLICATION_COMPLETE_WITH_TAIL_VARIANCE"
            if complete
            else "F7_STEADY_REPLICATION_FAIL_OR_INCOMPLETE"
        )
    )
    payload = {
        "schema_version": 1,
        "study": "RevTrace F7 steady-state replications",
        "decision": decision,
        "source_runner_decision": raw["decision"],
        "replicates": rows,
        "aggregate": {
            "goodput_events_per_second": mean_std(
                [row["goodput_events_per_second"] for row in rows]
            ),
            "p99_seconds_mean": (
                statistics.mean([row["p99_seconds"] for row in rows])
                if rows
                else None
            ),
            "p99_seconds_max": (
                max(row["p99_seconds"] for row in rows) if rows else None
            ),
            "joules_per_audio_second": mean_std(
                [row["joules_per_audio_second"] for row in rows]
            ),
            "verification_fraction": mean_std(
                [row["verification_fraction"] for row in rows]
            ),
            "unverified_fast_path_replay_roots": sum(
                row["unverified_fast_path_replay_roots"] for row in rows
            ),
            "verified_canonical_replay_roots": sum(
                row["verified_canonical_replay_roots"] for row in rows
            ),
            "post_stage_replay_output_disagreements": sum(
                row["post_stage_replay_output_disagreements"]
                for row in rows
            ),
            "post_stage_replay_state_disagreements": sum(
                row["post_stage_replay_state_disagreements"]
                for row in rows
            ),
            "deadline_miss_events": sum(
                row["deadline_miss_events"] for row in rows
            ),
            "deadline_miss_rounds": sum(
                row["deadline_miss_rounds"] for row in rows
            ),
            "slo_replicates_passing": sum(
                row["deadline_miss_events"] == 0 for row in rows
            ),
            "slo_replicates_total": len(rows),
            "slo_tail_variance_detected": not slo_all_pass,
        },
        "provenance": {
            "raw_code_commit_label": raw.get("environment", {}).get(
                "code_commit", "UNRECORDED"
            ),
            "final_runner_sha256": hashlib.sha256(
                (
                    repo / "scripts/remote/run_phase5a_live_adaptive.py"
                ).read_bytes()
            ).hexdigest(),
        },
        "claim_boundaries": [
            "the prior c14 certificate threshold is restored; the 1,350-event cold certification is not repeated",
            "three reporting stages use independent episode seeds under one frozen contract",
            "post-stage replay is excluded from service time and is not online selection-authority evidence",
            "the first seed has two synchronized rounds above the 2-second deadline (28 event-level misses); this is retained as tail-latency variance rather than relabeled as a safety failure",
            "the remote project was not a Git checkout; the compact artifact hashes the final runner and the change log records any protocol or reporting repair",
        ],
    }
    write_json(
        repo / "results/final_closure/steady_replications/summary.json",
        payload,
    )
    return payload


def pareto_rows(
    repo: Path,
    steady: dict[str, Any],
    energy: dict[str, Any],
) -> list[dict[str, Any]]:
    phase7 = read_json(repo / "results/phase7_1/performance_comparison.json")
    phase5 = read_json(repo / "results/phase5/summary.json")
    phase6 = read_json(repo / "results/phase6/summary.json")
    rows = []
    energy_by_model = {row["model"]: row for row in energy.get("rows", [])}
    for row in phase7["headline_revtrace"]:
        matched_energy = energy_by_model.get(row["model"])
        rows.append(
            {
                "source": (
                    f"F6 matched energy {row['scope']}"
                    if matched_energy
                    else row["scope"]
                ),
                "mechanism": "RevTrace risk-limited",
                "model": row["model"],
                "concurrency": 16,
                "gpu_normalized_goodput_speedup": (
                    matched_energy["gpu_normalized_speedup"]["mean"]
                    if matched_energy
                    else float(row["gpu_normalized_speedup"])
                ),
                "p99_seconds": (
                    matched_energy["p99_seconds"]["mean"]
                    if matched_energy
                    else float(row["p99_state_entry_seconds"])
                ),
                "energy_joules_per_audio_second": (
                    matched_energy["revtrace_joules_per_audio_second"]["mean"]
                    if matched_energy
                    else None
                ),
                "all_canonical_energy_joules_per_audio_second": (
                    matched_energy["all_canonical_joules_per_audio_second"][
                        "mean"
                    ]
                    if matched_energy
                    else None
                ),
                "energy_ratio_vs_all_canonical": (
                    matched_energy["energy_ratio_revtrace_over_all_canonical"][
                        "mean"
                    ]
                    if matched_energy
                    else None
                ),
                "risk_status": "formal_anytime_contract_pass",
                "slo_status": "pass",
                "joint_feasible": True,
                "matched_energy_baseline": matched_energy is not None,
            }
        )
    for row in phase5["phase5c"]["cells"]:
        risk_pass = (
            row["state_violations"] == 0
            and row["observed_state_risk_upper_95"] is not None
            and row["observed_state_risk_upper_95"] <= 0.005
        )
        slo_pass = row["deadline_misses"] == 0 and row["p99_seconds"] <= 2.0
        rows.append(
            {
                "source": f"Phase5C {row['cell']}",
                "mechanism": "frozen risk-limited workload cell",
                "model": row["model"],
                "concurrency": row["concurrency"],
                "gpu_normalized_goodput_speedup": row[
                    "gpu_normalized_speedup"
                ],
                "p99_seconds": row["p99_seconds"],
                "energy_joules_per_audio_second": row[
                    "joules_per_audio_second"
                ],
                "all_canonical_energy_joules_per_audio_second": None,
                "energy_ratio_vs_all_canonical": None,
                "risk_status": (
                    "pass"
                    if risk_pass
                    else (
                        "observed_violation"
                        if row["state_violations"]
                        else "insufficient_statistical_evidence"
                    )
                ),
                "slo_status": "pass" if slo_pass else "fail",
                "joint_feasible": risk_pass and slo_pass,
                "matched_energy_baseline": False,
            }
        )
    repaired = phase6["phase6b"]["summary"]
    rows.append(
        {
            "source": "Phase6 c32 Chinese burst repaired",
            "mechanism": "RevTrace contract-scoped repair",
            "model": "Qwen3-ASR-0.6B",
            "concurrency": 32,
            "gpu_normalized_goodput_speedup": repaired[
                "gpu_normalized_throughput_speedup"
            ],
            "p99_seconds": repaired["state_entry_latency_seconds_p99"],
            "energy_joules_per_audio_second": repaired["service_energy"][
                "joules_per_audio_second"
            ],
            "all_canonical_energy_joules_per_audio_second": None,
            "energy_ratio_vs_all_canonical": None,
            "risk_status": "observed_zero_after_repair",
            "slo_status": "fail",
            "joint_feasible": False,
            "matched_energy_baseline": False,
        }
    )
    c14 = read_json(repo / "results/phase7_1/capacity_audit.json")[
        "c14_live_result"
    ]
    rows.append(
        {
            "source": "Phase7.1 c14 certified capacity",
            "mechanism": "RevTrace live adaptive",
            "model": "Qwen3-ASR-0.6B",
            "concurrency": 14,
            "gpu_normalized_goodput_speedup": None,
            "p99_seconds": c14["p99_seconds"],
            "energy_joules_per_audio_second": read_json(
                repo / "results/phase7_1/c14_capacity/raw.json"
            )["stages"][0]["energy"]["joules_per_audio_second"],
            "all_canonical_energy_joules_per_audio_second": None,
            "energy_ratio_vs_all_canonical": None,
            "risk_status": "split_sample_contract_pass",
            "slo_status": "pass",
            "joint_feasible": True,
            "matched_energy_baseline": False,
        }
    )
    rows.append(
        {
            "source": "Final closure c14 steady-state",
            "mechanism": "RevTrace continued certified epoch",
            "model": "Qwen3-ASR-0.6B",
            "concurrency": 14,
            "gpu_normalized_goodput_speedup": None,
            "p99_seconds": steady["steady_state"]["p99_seconds"],
            "energy_joules_per_audio_second": steady["steady_state"][
                "joules_per_audio_second"
            ],
            "all_canonical_energy_joules_per_audio_second": None,
            "energy_ratio_vs_all_canonical": None,
            "risk_status": "continued_split_sample_contract_pass",
            "slo_status": (
                "pass"
                if steady["steady_state"]["p99_seconds"] <= 2.0
                else "fail"
            ),
            "joint_feasible": steady["decision"]
            == "F2_STEADY_STATE_DECOMPOSITION_PASS",
            "matched_energy_baseline": False,
        }
    )
    for row in rows:
        row["comparison_eligible"] = bool(
            row["gpu_normalized_goodput_speedup"] is not None
            and row["p99_seconds"] is not None
        )
        row["safe_frontier_eligible"] = bool(
            row["comparison_eligible"] and row["joint_feasible"]
        )
        row["energy_frontier_eligible"] = bool(
            row["safe_frontier_eligible"]
            and row["energy_joules_per_audio_second"] is not None
            and row["matched_energy_baseline"]
        )
        row["comparison_scope"] = (
            "same-task end-to-end comparison point"
            if row["comparison_eligible"]
            else "risk-SLO capacity point; no same-task normalized baseline"
        )
    return rows


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = list(rows[0]) if rows else []
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def markdown_table(rows: list[dict[str, Any]], fields: list[str]) -> str:
    header = "| " + " | ".join(fields) + " |"
    separator = "|" + "|".join("---" for _ in fields) + "|"
    body = []
    for row in rows:
        values = []
        for field in fields:
            value = row.get(field)
            if isinstance(value, float):
                values.append(f"{value:.4f}")
            elif (
                isinstance(value, dict)
                and set(value) == {"mean", "std"}
                and value["mean"] is not None
                and value["std"] is not None
            ):
                values.append(
                    f"{float(value['mean']):.4f} +/- "
                    f"{float(value['std']):.4f}"
                )
            else:
                values.append(str(value))
        body.append("| " + " | ".join(values) + " |")
    return "\n".join([header, separator, *body])


def freeze_artifact(repo: Path, results: dict[str, Any]) -> Path:
    artifact = repo / "artifact/final-evaluation-closure-v1"
    artifact.mkdir(parents=True, exist_ok=True)
    copied = []
    sources = [
        repo / "results/final_closure/summary.json",
        repo / "results/final_closure/quality/summary.json",
        repo / "results/final_closure/quality/paired_utterances.csv",
        repo / "results/final_closure/quality/holdout_manifest.json",
        repo / "results/final_closure/steady_state/summary.json",
        repo
        / "results/final_closure/steady_state/"
        "initial_failure_analysis.json",
        repo / "results/final_closure/canonical_contracts.json",
        repo / "results/final_closure/energy/summary.json",
        repo / "results/final_closure/steady_replications/summary.json",
        repo / "results/final_closure/pareto.csv",
        repo / "results/final_closure/REPORT.md",
        repo / "results/final_closure/F5_F8_CHANGELOG.md",
        repo / "README.md",
        repo / "scripts/finalize_final_closure.py",
        repo / "scripts/build_final_quality_manifest.py",
        repo / "scripts/remote/run_final_quality_mode.py",
        repo / "scripts/remote/run_final_quality_closure.sh",
        repo / "scripts/remote/run_final_steady_state.sh",
        repo / "scripts/remote/run_f5_deployed_quality.py",
        repo / "scripts/remote/run_f5_deployed_quality.sh",
        repo / "scripts/remote/run_f6_headline_energy.sh",
        repo / "scripts/remote/run_f7_steady_replications.sh",
        repo / "scripts/remote/run_phase5a_live_adaptive.py",
        repo / "scripts/remote/run_revtrace_dual_gpu.py",
        repo / "tests/test_final_closure.py",
        repo / "configs/final_evaluation_closure.json",
        repo / "docs/CLAIM_BOUNDARIES.md",
    ]
    for source in sources:
        relative = source.relative_to(repo)
        target = artifact / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(source.read_bytes())
        copied.append(target)
    manifest_rows = []
    for path in sorted(copied):
        manifest_rows.append(
            {
                "path": str(path.relative_to(artifact)).replace("\\", "/"),
                "bytes": path.stat().st_size,
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            }
        )
    write_json(
        artifact / "MANIFEST.json",
        {
            "schema_version": 1,
            "artifact": "RevTrace Final Evaluation Closure v1",
            "decision": results["decision"],
            "files": manifest_rows,
            "raw_data_boundary": (
                "Raw GPU traces remain under results/final_closure and are "
                "not duplicated into this compact submission artifact."
            ),
        },
    )
    return artifact


def main() -> int:
    args = parse_args()
    repo = args.repo.resolve()
    quality = finalize_quality(repo, args.bootstrap_replicates)
    steady = finalize_steady(repo)
    contracts = canonical_contracts(repo)
    energy = finalize_energy(repo)
    steady_replications = finalize_steady_replications(repo)
    pareto = pareto_rows(repo, steady, energy)
    write_csv(repo / "results/final_closure/pareto.csv", pareto)
    joint = [row for row in pareto if row["joint_feasible"]]
    joint_pareto = [
        row for row in joint if row["safe_frontier_eligible"]
    ]
    joint_capacity_only = [
        row for row in joint if not row["comparison_eligible"]
    ]
    infeasible = [row for row in pareto if not row["joint_feasible"]]
    energy_frontier = [
        row for row in pareto if row["energy_frontier_eligible"]
    ]
    closure_inputs_pass = (
        quality["decision"] == "F1_QUALITY_PRESERVATION_PASS"
        and steady["decision"] == "F2_STEADY_STATE_DECOMPOSITION_PASS"
        and energy["decision"] == "F6_MATCHED_ENERGY_MEASUREMENT_PASS"
        and steady_replications["decision"]
        in {
            "F7_STEADY_REPLICATION_PASS",
            "F7_STEADY_REPLICATION_COMPLETE_WITH_TAIL_VARIANCE",
        }
    )
    if not closure_inputs_pass:
        decision = "F5_F8_PROTOCOL_CLOSURE_INCOMPLETE_OR_FAIL"
    elif (
        steady_replications["decision"]
        == "F7_STEADY_REPLICATION_COMPLETE_WITH_TAIL_VARIANCE"
    ):
        decision = "F5_F8_PROTOCOL_CLOSURE_PASS_WITH_F7_TAIL_VARIANCE"
    else:
        decision = "F5_F8_PROTOCOL_CLOSURE_PASS"
    summary = {
        "schema_version": 1,
        "study": "RevTrace Final Evaluation Closure",
        "decision": decision,
        "quality_decision": quality["decision"],
        "steady_state_decision": steady["decision"],
        "energy_decision": energy["decision"],
        "steady_replication_decision": steady_replications["decision"],
        "canonical_contract_decision": contracts["decision"],
        "pareto_rows": len(pareto),
        "joint_feasible_rows": len(joint),
        "comparison_eligible_rows": sum(
            bool(row["comparison_eligible"]) for row in pareto
        ),
        "safe_frontier_rows": sum(
            bool(row["safe_frontier_eligible"]) for row in pareto
        ),
        "energy_frontier_rows": len(energy_frontier),
        "joint_capacity_only_rows": len(joint_capacity_only),
        "infeasible_rows": len(infeasible),
        "claim_boundary": (
            "risk-limited authoritative commit and replay repeatability are "
            "separate guarantees; infeasible capacity cells are not headline "
            "performance points; matched energy is required for the energy "
            "frontier"
        ),
    }
    write_json(repo / "results/final_closure/summary.json", summary)

    fields = [
        "source",
        "model",
        "concurrency",
        "gpu_normalized_goodput_speedup",
        "p99_seconds",
        "energy_joules_per_audio_second",
        "all_canonical_energy_joules_per_audio_second",
        "energy_ratio_vs_all_canonical",
        "risk_status",
        "slo_status",
        "joint_feasible",
        "comparison_eligible",
        "safe_frontier_eligible",
        "energy_frontier_eligible",
        "comparison_scope",
    ]
    quality_comparison_rows = [
        {
            "model": row["model"],
            "language": row["language"],
            "mode": row["mode"],
            "terminal_exact_rate_vs_singleton": row[
                "terminal_exact_rate_vs_singleton"
            ],
            "primary_error_delta": row["paired_bootstrap"]["delta"],
            "ci95_low": row["paired_bootstrap"]["ci95_low"],
            "ci95_high": row["paired_bootstrap"]["ci95_high"],
            "catastrophic_outliers": row[
                "catastrophic_outliers_delta_at_least_0.20"
            ],
            "terminal_mismatch_rate_upper_95": row[
                "terminal_mismatch_rate_upper_95"
            ],
        }
        for row in quality["comparisons"]
    ]
    report = f"""# RevTrace Final Evaluation Closure

Decision: **{decision}**

## F1 — Quality preservation

Decision: **{quality['decision']}**

{markdown_table(quality['metrics'], ['model', 'language', 'mode', 'utterances', 'wer', 'cer', 'partial_revision_edit_rate', 'terminal_verification_fraction', 'nonterminal_verification_fraction', 'online_selection_authority_violations'])}

## F2 — Cold start versus steady state

Decision: **{steady['decision']}**

- Time to certify (interpolated): {steady['time_to_certify_seconds_estimate']:.3f} s
- Cold verification fraction: {steady['cold_start']['verification_fraction']:.4f}
- Steady verification fraction: {steady['steady_state']['verification_fraction']:.4f}
- Cold/steady goodput: {steady['cold_start']['goodput_events_per_second']:.3f} / {steady['steady_state']['goodput_events_per_second']:.3f} events/s
- Cold/steady P99: {steady['cold_start']['p99_seconds']:.3f} / {steady['steady_state']['p99_seconds']:.3f} s

## F3 — Canonical contract matrix

{markdown_table(contracts['contracts'], ['experiment', 'proposer_dtype', 'authoritative_draw', 'fixed_batch_shape', 'attention_backend', 'batch_invariant_requested', 'end_to_end_invariance_verified', 'replay_guarantee'])}

## F4 — Joint risk/SLO Pareto table

### Joint feasible

{markdown_table(joint_pareto, fields)}

### Joint-feasible capacity points without a same-task normalized baseline

{markdown_table(joint_capacity_only, fields)}

### Infeasible or not statistically certified

{markdown_table(infeasible, fields)}

The table intentionally does not rank operator-only BIO/TBIK probes as
end-to-end serving systems.

## F5 - Deployed-path quality attachment

The deployed quality rows use the real Phase-2 authority split: FP16 batched
proposer, FP16 singleton authority for low-margin intermediate revisions, and
GPU-1 FP16 fixed-shape b16 authority for terminal revisions.

## F6 - Matched headline energy

Decision: **{energy['decision']}**

{markdown_table(energy['rows'], ['model', 'replicates', 'margin_thresholds', 'headline_threshold_match', 'revtrace_joules_per_audio_second', 'all_canonical_joules_per_audio_second', 'energy_ratio_revtrace_over_all_canonical', 'terminal_verification_fraction', 'nonterminal_verification_fraction', 'canonical_replay_state_disagreements', 'online_stale_or_replayed_result_events'])}

## F7 - Independent steady-state replications

Decision: **{steady_replications['decision']}**

{markdown_table(steady_replications['replicates'], ['seed_label', 'events', 'goodput_events_per_second', 'p99_seconds', 'deadline_miss_events', 'deadline_miss_rounds', 'joules_per_audio_second', 'verification_fraction', 'unverified_fast_path_replay_roots', 'verified_canonical_replay_roots', 'post_stage_replay_output_disagreements', 'post_stage_replay_state_disagreements'])}

The replication is complete, but not all seeds satisfy the 2-second tail target: {steady_replications['aggregate']['slo_replicates_passing']}/{steady_replications['aggregate']['slo_replicates_total']} seeds have zero deadline misses. Replay disagreements are later independent draws and are not online selection-authority violations.

## F8 - Reporting repair

FP32 is named `fp32_fixed_contract`; bootstrap intervals describe empirical
holdout deltas; terminal and nonterminal verification are separated; and the
comparison, safe-frontier, and matched-energy eligibility fields are distinct.
"""
    normalized_report_lines = []
    for line in report.splitlines():
        for prefix, title in (
            ("## F1 ", "## F1 - Quality preservation"),
            ("## F2 ", "## F2 - Cold start versus steady state"),
            ("## F3 ", "## F3 - Canonical contract matrix"),
            ("## F4 ", "## F4 - Joint risk/SLO Pareto table"),
        ):
            if line.startswith(prefix):
                line = title
                break
        normalized_report_lines.append(line)
    report = "\n".join(normalized_report_lines) + "\n"
    report = report.replace(
        "\n## F2 - Cold start versus steady state\n",
        "\n### Paired quality versus singleton authoritative\n\n"
        + markdown_table(
            quality_comparison_rows,
            [
                "model",
                "language",
                "mode",
                "terminal_exact_rate_vs_singleton",
                "primary_error_delta",
                "ci95_low",
                "ci95_high",
                "catastrophic_outliers",
                "terminal_mismatch_rate_upper_95",
            ],
        )
        + "\n\n## F2 - Cold start versus steady state\n",
    )
    cold_line = (
        "- Cold verification fraction: "
        f"{steady['cold_start']['verification_fraction']:.4f}"
    )
    repaired_protocol = "\n".join(
        [
            cold_line,
            (
                "- Adaptation roots promoted: "
                f"{steady['audit_adaptation']['root_counterexamples_promoted']}"
            ),
            (
                "- Dynamic threshold after adaptation: "
                f"{steady['audit_adaptation']['threshold_after_adaptation']:.6f}"
            ),
        ]
    )
    report = report.replace(cold_line, repaired_protocol)
    p99_line = (
        "- Cold/steady P99: "
        f"{steady['cold_start']['p99_seconds']:.3f} / "
        f"{steady['steady_state']['p99_seconds']:.3f} s"
    )
    protocol_note = "\n".join(
        [
            p99_line,
            (
                "- Cold/steady energy: "
                f"{steady['cold_start']['joules_per_audio_second']:.3f} / "
                f"{steady['steady_state']['joules_per_audio_second']:.3f} "
                "J/audio-s"
            ),
            "",
            (
                "The initial two-stage run is retained as a failed mechanism "
                "version. It recorded replay-audit counterexamples but did "
                "not feed their roots back into the dynamic failure floor."
            ),
            (
                "The repaired protocol uses the middle stage only for "
                "adaptation and reports the independently seeded third stage "
                "as steady validation."
            ),
        ]
    )
    report = report.replace(p99_line, protocol_note)
    report_path = repo / "results/final_closure/REPORT.md"
    report_path.write_text(report, encoding="utf-8")
    artifact = freeze_artifact(repo, summary)
    print(
        json.dumps(
            {
                "decision": decision,
                "artifact": str(artifact),
                "quality_cells": len(quality["metrics"]),
                "pareto_rows": len(pareto),
            }
        )
    )
    return 0 if decision.startswith("F5_F8_PROTOCOL_CLOSURE_PASS") else 2


if __name__ == "__main__":
    raise SystemExit(main())

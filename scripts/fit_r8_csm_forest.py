#!/usr/bin/env python3
"""Fit and export the frozen R8 Cross-Modal Sufficiency Monitor.

The source rows are produced by ``analyze_r8_csm.py`` using only online
features; canonical/reference information supplies development labels only.
The exported forest is plain JSON so the serving path does not depend on
scikit-learn or pickle deserialization.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any, Sequence

import numpy as np
import sklearn
from sklearn.ensemble import RandomForestClassifier


FEATURES = (
    "generation_steps",
    "token_count",
    "token_yield",
    "relative_yield_drop",
    "speech_active_ratio",
    "speech_token_mismatch",
    "terminated_by_eos",
    "minimum_margin",
    "feedback_debt",
    "state_age",
    "first_step_no_speech_probability",
    "average_token_log_probability",
    "compression_ratio",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rows", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--trees", type=int, default=200)
    parser.add_argument("--max-depth", type=int, default=3)
    parser.add_argument("--min-samples-leaf", type=int, default=8)
    parser.add_argument("--negative-quantile", type=float, default=0.91)
    parser.add_argument("--seed", type=int, default=1)
    return parser.parse_args()


def higher_quantile(values: Sequence[float], quantile: float) -> float:
    ordered = sorted(float(value) for value in values)
    index = min(
        len(ordered) - 1,
        max(0, math.ceil(quantile * len(ordered)) - 1),
    )
    return ordered[index]


def strict_decision_threshold(
    values: Sequence[float], quantile: float
) -> float:
    """Place the threshold between adjacent scores, never on a sample."""

    ordered = sorted(float(value) for value in values)
    cutoff = higher_quantile(ordered, quantile)
    greater = next((value for value in ordered if value > cutoff), None)
    return cutoff if greater is None else (cutoff + greater) / 2.0


def make_model(args: argparse.Namespace) -> RandomForestClassifier:
    return RandomForestClassifier(
        n_estimators=args.trees,
        max_depth=args.max_depth,
        min_samples_leaf=args.min_samples_leaf,
        class_weight="balanced",
        random_state=args.seed,
        n_jobs=1,
    )


def export_tree(estimator: Any) -> dict[str, Any]:
    tree = estimator.tree_
    leaf_probability: list[float] = []
    for values in tree.value[:, 0, :]:
        total = float(np.sum(values))
        leaf_probability.append(float(values[1] / total) if total else 0.0)
    return {
        "children_left": tree.children_left.astype(int).tolist(),
        "children_right": tree.children_right.astype(int).tolist(),
        "feature": tree.feature.astype(int).tolist(),
        "threshold": tree.threshold.astype(float).tolist(),
        "positive_probability": leaf_probability,
    }


def main() -> int:
    args = parse_args()
    source = json.loads(args.rows.read_text(encoding="utf-8"))
    rows = source["rows"]
    x = np.asarray([
        [float(row.get(name) or 0.0) for name in FEATURES] for row in rows
    ])
    y = np.asarray([bool(row["root"]) for row in rows])
    folds = np.asarray([int(row["fold"]) for row in rows])
    sessions = np.asarray([int(row["session_id"]) for row in rows])
    predictions = np.zeros(len(rows), dtype=bool)
    scores = np.zeros(len(rows), dtype=float)
    thresholds: list[float] = []
    for fold in sorted(set(folds.tolist())):
        training = folds != fold
        holdout = ~training
        model = make_model(args).fit(x[training], y[training])
        values = model.predict_proba(x)[:, 1]
        threshold = strict_decision_threshold(
            values[training & ~y], args.negative_quantile
        )
        scores[holdout] = values[holdout]
        predictions[holdout] = values[holdout] > threshold
        thresholds.append(threshold)

    root_sessions = set(sessions[y].tolist())
    caught_sessions = set(sessions[y & predictions].tolist())
    session_recall = len(caught_sessions) / max(1, len(root_sessions))
    event_recall = float(np.mean(predictions[y]))
    false_trigger = float(np.mean(predictions[~y]))

    final_model = make_model(args).fit(x, y)
    final_scores = final_model.predict_proba(x)[:, 1]
    final_threshold = strict_decision_threshold(
        final_scores[~y], args.negative_quantile
    )
    passed = session_recall >= 0.90 and false_trigger <= 0.10
    payload = {
        "schema_version": 1,
        "study": "RevTrace R8.2 frozen CSM forest",
        "decision": "PASS_R8_2_CSM" if passed else "FAIL_R8_2_CSM",
        "cross_validation": {
            "folds": len(set(folds.tolist())),
            "root_sessions": len(root_sessions),
            "session_root_recall": session_recall,
            "root_event_recall": event_recall,
            "event_false_trigger_rate": false_trigger,
            "fold_thresholds": thresholds,
        },
        "frozen_policy": {
            "features": list(FEATURES),
            "trees": [export_tree(tree) for tree in final_model.estimators_],
            "score_threshold": final_threshold,
            "structural_reanchor_horizon_windows": 3,
            "structural_sufficiency_rules": {
                "absolute_token_floor": 2,
                "conditional_token_floor": 10,
                "conditional_forest_score": 0.30,
            },
        },
        "config": {
            "trees": args.trees,
            "max_depth": args.max_depth,
            "min_samples_leaf": args.min_samples_leaf,
            "negative_quantile": args.negative_quantile,
            "seed": args.seed,
            "sklearn_version": sklearn.__version__,
        },
        "rows": [
            {
                "session_id": int(row["session_id"]),
                "window_index": int(row["window_index"]),
                "root": bool(row["root"]),
                "fold": int(row["fold"]),
                "score": float(score),
                "trigger": bool(trigger),
            }
            for row, score, trigger in zip(rows, scores, predictions)
        ],
        "authority_boundary": (
            "the CSM schedules causal recovery work; the maximum reanchor "
            "horizon is the structural backstop and only a validated capsule "
            "may acquire feedback authority"
        ),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"decision": payload["decision"], **payload["cross_validation"]}))
    return 0 if passed else 2


if __name__ == "__main__":
    raise SystemExit(main())

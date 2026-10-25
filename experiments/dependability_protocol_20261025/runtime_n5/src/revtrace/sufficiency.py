"""Portable inference for the JSON Cross-Modal Sufficiency Monitor."""

from __future__ import annotations

from typing import Any, Mapping, Sequence


def _tree_probability(tree: Mapping[str, Sequence[Any]], values: Sequence[float]) -> float:
    node = 0
    while int(tree["children_left"][node]) >= 0:
        feature = int(tree["feature"][node])
        if float(values[feature]) <= float(tree["threshold"][node]):
            node = int(tree["children_left"][node])
        else:
            node = int(tree["children_right"][node])
    return float(tree["positive_probability"][node])


def csm_forest_score(
    policy: Mapping[str, Any], features: Mapping[str, float]
) -> float:
    names = tuple(str(name) for name in policy["features"])
    values = tuple(float(features.get(name, 0.0) or 0.0) for name in names)
    trees = policy["trees"]
    if not trees:
        raise ValueError("CSM policy contains no trees")
    return sum(_tree_probability(tree, values) for tree in trees) / len(trees)


def csm_requires_reanchor(
    policy: Mapping[str, Any], features: Mapping[str, float]
) -> bool:
    return csm_forest_score(policy, features) > float(policy["score_threshold"])

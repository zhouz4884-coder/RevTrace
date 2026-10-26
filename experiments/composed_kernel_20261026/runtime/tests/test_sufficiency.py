from revtrace.sufficiency import csm_forest_score, csm_requires_reanchor


def test_portable_forest_inference() -> None:
    policy = {
        "features": ["x"],
        "score_threshold": 0.5,
        "trees": [
            {
                "children_left": [1, -1, -1],
                "children_right": [2, -1, -1],
                "feature": [0, -2, -2],
                "threshold": [3.0, -2.0, -2.0],
                "positive_probability": [0.5, 0.1, 0.9],
            }
        ],
    }
    assert csm_forest_score(policy, {"x": 2.0}) == 0.1
    assert csm_forest_score(policy, {"x": 4.0}) == 0.9
    assert csm_requires_reanchor(policy, {"x": 4.0})

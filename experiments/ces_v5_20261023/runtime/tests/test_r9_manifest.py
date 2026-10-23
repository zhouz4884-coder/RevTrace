from scripts.build_r9_untouched_manifest import collect_utterance_ids


def test_collect_utterance_ids_walks_nested_r9_modes():
    payload = {
        "modes": {
            "adaptive": {
                "sessions": [
                    {"utterance_ids": ["a", "b"]},
                    {"utterance_ids": ["c"]},
                ]
            }
        }
    }
    used: set[str] = set()
    collect_utterance_ids(payload, used)
    assert used == {"a", "b", "c"}

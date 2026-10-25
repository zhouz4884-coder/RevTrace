from scripts.run_dgft_transaction_fuzzer import run


def test_transaction_fuzzer_rejects_all_mutated_commits() -> None:
    result = run(attempts=2_500, sessions=8, seed=17)
    assert result["decision"] == "PASS"
    assert result["invalid_accepts"] == 0
    assert result["invariant_violations"] == 0
    assert result["accepted_valid_commits"] == 100
    assert result["rejected_mutated_or_replayed_commits"] == 2_400

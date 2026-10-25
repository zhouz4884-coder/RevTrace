from __future__ import annotations

import importlib.util
from pathlib import Path


_script = Path(__file__).with_name("run_dsn_structural_matrix.py")
if not _script.exists():
    _script = Path(__file__).resolve().parents[1] / "scripts/run_dsn_structural_matrix.py"
spec = importlib.util.spec_from_file_location("structural_matrix", _script)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def prepared():
    state = m.fuzz.initial_state(0)
    previous = m.fuzz.make_valid(state, 10)
    state = m.apply("dgft", state, previous).state
    return state, m.fuzz.make_valid(state, 20), previous


def test_full_composition_matches_production_on_all_classes():
    state, base, previous = prepared()
    for kind in (*m.fuzz.MUTATIONS, *m.EXTRA_CASES):
        candidate = (m.extra_mutation(kind, state, base) if kind in m.EXTRA_CASES
                     else m.fuzz.mutate(kind, state, *base, previous))
        a, b = (m.apply(method, state, candidate) for method in ("dgft", "composed_full"))
        assert a.accepted == b.accepted
        assert a.state == b.state
        assert a.accepted == (kind == "valid")


def test_coherent_frontier_counterfactual_is_not_certificate_mismatch():
    state, base, _ = prepared()
    for kind in ("coherent_gap", "coherent_overlap", "coherent_empty"):
        candidate = m.extra_mutation(kind, state, base)
        assert all(ok for ok, _ in m.predicates(state, candidate)["content"])
        assert not m.apply("composed_full", state, candidate).accepted
        assert m.apply("composed_no_frontier", state, candidate).accepted


def test_reconstruction_repairs_field_not_consistent_candidate():
    state, base, _ = prepared()
    field = m.extra_mutation("consumed_projection_mutation", state, base)
    repaired = m.apply("trusted_reconstruction", state, field)
    assert repaired.accepted and repaired.state.prompt_tokens == base[3]
    content = m.extra_mutation("consistent_candidate_mutation", state, base)
    copied = m.apply("trusted_reconstruction", state, content)
    assert copied.accepted and copied.state.prompt_tokens != base[3]
    assert not m.apply("dgft", state, content).accepted


def test_disable_identity_exposes_reissued_duplicate_only():
    state, base, _ = prepared()
    candidate = m.extra_mutation("coherent_duplicate", state, base)
    assert not m.apply("composed_full", state, candidate).accepted
    assert m.apply("composed_no_identity", state, candidate).accepted


def test_real_journal_reopen_preserves_admission_for_both(tmp_path):
    for method in ("dgft", "composed_full"):
        row = m.restart_fixture(tmp_path / "wal" / method, method, 10)
        assert row["pass"]
        assert row["epoch_after"] == row["epoch_before"] + 1


def test_production_retry_returns_old_ack(tmp_path):
    volatile = m.coordinator_reopen(tmp_path / "volatile", False)
    durable = m.coordinator_reopen(tmp_path / "durable", True)
    assert volatile["new_admission_on_retry"]
    assert volatile["after_reopen"]["checkpoint_id"] == 0
    assert durable["identical_retry_old_ack"]
    assert durable["after_reopen"]["checkpoint_id"] == 1
    assert durable["after_retry"]["checkpoint_id"] == 1

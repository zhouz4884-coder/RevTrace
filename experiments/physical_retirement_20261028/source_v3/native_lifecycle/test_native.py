from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import sys
import subprocess
import os
import pytest

from independent_checker import audit
from native_store import Store
from native_workflow import CpuFixtureProvider, run_cell
from tasks import development_tasks, validation_tasks, score, trajectory_metrics, fixture_value
from compare_trajectories import compare
from actual_provider import frozen_substitution


def prepared(store, op, cycle):
    f = store.freeze(op, cycle)
    p = CpuFixtureProvider()
    return store.register_selection(f, p.generate(p.prepare(f)))


@pytest.mark.parametrize("index", [0, 1])
def test_two_families_three_persistent_read_write_cycles(tmp_path, index):
    t = development_tasks()[index]
    s = Store(tmp_path)
    s.initialize(t, CpuFixtureProvider.identity, CpuFixtureProvider.tier)
    for i in range(3):
        p = prepared(s, "op" + str(i), i)
        r = s.install(p)
        assert r["status"] == "committed"
        s.deliver(); s.deliver()
    r = audit(tmp_path)
    assert r["status"] == "PASS_SCOPED_CPU_FIXTURE"
    assert r["committed_cycles"] == 3 and len(r["actual_downstream_input_operations"]) == 2
    assert all(x["score"]["current_step_success"] for x in r["task_scores"])


@pytest.mark.parametrize("mutation", ["source-change", "owner-change"])
def test_stale_new_write_rejected_but_historical_receipt_survives(tmp_path, mutation):
    s = Store(tmp_path); s.initialize(development_tasks()[0], CpuFixtureProvider.identity, CpuFixtureProvider.tier)
    first = prepared(s, "first", 0); original = s.install(first)
    pending = prepared(s, "pending", 1)
    s.mutate(mutation)
    assert s.install(first) == original
    assert s.install(pending)["status"] == "rejected"
    s.deliver()
    r = audit(tmp_path)
    assert not r["violations"]


def test_false_content_is_not_repaired_by_task_oracle(tmp_path):
    s = Store(tmp_path); s.initialize(development_tasks()[0], CpuFixtureProvider.identity, CpuFixtureProvider.tier)
    f = s.freeze("wrong", 0); provider = CpuFixtureProvider(); ev = provider.generate(provider.prepare(f))
    ev["value"] = {"completed": ["restart"], "last_action": "restart"}
    ev["rendered_text"] = json.dumps(ev["value"], sort_keys=True, separators=(",", ":"))
    ev["tokens"] = list(ev["rendered_text"].encode()) + [256]
    p = s.register_selection(f, ev)
    assert s.install(p)["status"] == "committed"
    s.deliver(); r = audit(tmp_path)
    assert r["status"] == "PASS_SCOPED_CPU_FIXTURE"
    assert not r["task_scores"][0]["score"]["current_step_success"]


def test_tampered_frozen_identity_cannot_be_replayed(tmp_path):
    s = Store(tmp_path); s.initialize(development_tasks()[0], CpuFixtureProvider.identity, CpuFixtureProvider.tier)
    p = prepared(s, "op", 0); s.install(p)
    p = deepcopy(p); p["frozen"]["parent"] = 8
    assert s.install(p)["status"] == "identity-conflict"


def test_same_operation_must_not_silently_return_a_different_cycle(tmp_path):
    s = Store(tmp_path); s.initialize(development_tasks()[0], CpuFixtureProvider.identity, CpuFixtureProvider.tier)
    original = s.freeze("id", 0)
    assert s.freeze("id", 0) == original
    with pytest.raises(ValueError, match="different cycle"):
        s.freeze("id", 1)


@pytest.mark.parametrize("family_index", [0, 1])
def test_valid_current_output_can_repair_invalid_recorded_prior(family_index):
    task = development_tasks()[family_index]
    wrong = {"completed": ["restart"], "last_action": "restart"} if family_index == 0 else {"reserved": ["unknown"], "remaining": 999}
    repaired = fixture_value(task["family"], task["source"], wrong, task["requests"][0])
    r = score(task["family"], task["source"], wrong, task["requests"][0], repaired)
    assert not r["source_grounded_prior_history"]
    assert r["current_output_valid"] and r["repair_observed"] and r["current_step_success"]
    assert "correct" not in r


def test_local_greedy_success_is_not_called_global_multicycle_optimality():
    t = next(x for x in validation_tasks() if x["id"] == "resource-val-residual")
    prior = t["initial_memory"]
    for i, req in enumerate(t["requests"]):
        out = fixture_value(t["family"], t["source"], prior, req)
        assert score(t["family"], t["source"], prior, req, out)["current_step_success"]
        prior = out
    r = trajectory_metrics(t, 2, t["source"], prior)
    assert r["observed_objective"] == 23 and r["global_bound"] == 24 and r["objective_gap"] == 1


def test_pairing_retains_base_errors_and_refuses_different_actual_source():
    key = {"task_id": "same", "cycle": 0, "source_sha256": "s", "request_sha256": "r"}
    a = {"cycle": 0, "pair_key": key, "current_step_success": False, "current_output_valid": False, "repair_observed": False}
    b = {**a, "current_step_success": True, "current_output_valid": True, "repair_observed": True}
    r = compare({"status": "PASS", "cycle_outcomes": [a]}, {"status": "PASS", "cycle_outcomes": [b]})
    assert r["rows"][0]["clean_failure_changed_success"] and r["all_offered_cycles"] == 1
    b["pair_key"] = {**key, "source_sha256": "different"}
    assert compare({"status": "PASS", "cycle_outcomes": [a]}, {"status": "PASS", "cycle_outcomes": [b]})["comparable_cycles"] == 0


def test_one_injected_cycle_does_not_reinject_downstream_propagation_requests():
    cfg = {"candidate_substitution": {"kind": "fixed-json-return", "on_cycles": [0], "by_family": {
        "runbook": {"completed": ["unsafe"], "last_action": "unsafe"},
        "resource_plan": {"reserved": ["unknown"], "remaining": -1}}}}
    for family in ("runbook", "resource_plan"):
        assert frozen_substitution(cfg, {"family": family, "cycle": 0})["value"] == cfg["candidate_substitution"]["by_family"][family]
        assert frozen_substitution(cfg, {"family": family, "cycle": 1}) is None
        assert frozen_substitution(cfg, {"family": family, "cycle": 2}) is None


def test_no_revtrace_label_without_kernel_adapter(tmp_path):
    s = Store(tmp_path); s.initialize(development_tasks()[0], CpuFixtureProvider.identity, CpuFixtureProvider.tier)
    with pytest.raises(RuntimeError, match="actual reviewed kernel adapter"):
        s.install(prepared(s, "op", 0), "revtrace")


def test_metadata_only_negative_control_is_observably_rejected_by_checker(tmp_path):
    s = Store(tmp_path); s.initialize(development_tasks()[0], CpuFixtureProvider.identity, CpuFixtureProvider.tier)
    p = prepared(s, "op", 0); s.mutate("source-change")
    assert s.install(p, "minimal")["status"] == "committed"
    s.deliver(); r = audit(tmp_path)
    assert r["status"] == "FAIL" and any("stale-source-admission" in x for x in r["violations"])


def test_missing_actual_model_input_is_unknown(tmp_path):
    s = Store(tmp_path); s.initialize(development_tasks()[0], CpuFixtureProvider.identity, CpuFixtureProvider.tier)
    prepared(s, "op", 0)
    with s.db(True) as db:
        row = db.execute("SELECT id,evidence FROM selections").fetchone()
        e = json.loads(row["evidence"]); del e["actual_input_ids"]
        db.execute("UPDATE selections SET evidence=? WHERE id=?", (json.dumps(e), row["id"]))
    r = audit(tmp_path)
    assert any("missing-actual-evidence" in x for x in r["unknown"])


def runtime_source():
    root = Path(os.environ.get("REVTRACE_RUNTIME_SOURCE", Path(__file__).resolve().parents[1] / "runtime" / "src"))
    if not (root / "revtrace" / "composed_kernel.py").is_file():
        pytest.fail("required actual production kernel missing; set REVTRACE_RUNTIME_SOURCE to byte-matched runtime/src")
    return root.resolve()


def kernel_module():
    root = runtime_source()
    sys.path.insert(0, str(root))
    import revtrace_adapter
    return revtrace_adapter


def kernel_prepared(s, op, cycle, km):
    f = s.freeze(op, cycle); p = CpuFixtureProvider(); req = p.prepare(f)
    a = km.create_execution_adapter(s, f, req); a.dispatch_before_execution()
    ev = p.generate(req); a.complete_after_execution(ev)
    return s.register_selection(f, ev)


@pytest.mark.parametrize("family_index", [0, 1])
def test_actual_kernel_restores_full_history_and_replays_old_receipt(tmp_path, family_index):
    km = kernel_module()
    s = Store(tmp_path); s.initialize(development_tasks()[family_index], CpuFixtureProvider.identity, CpuFixtureProvider.tier)
    first = None
    for i in range(3):
        p = kernel_prepared(s, "k" + str(i), i, km)
        adapter = km.create_adapter(s, p)
        r = s.install(p, "revtrace", adapter=adapter)
        if i == 0: first = (p, r)
        assert r["receipt"]["kernel"]["recovery"]["history_entries"] == i
        assert r["receipt"]["kernel"]["recovery"]["used_genesis"] == (i == 0)
        s.deliver()
    old = s.install(first[0], "revtrace", adapter=km.create_adapter(s, first[0]))
    assert old == first[1]
    rows = s.dump()
    recovery = [json.loads(r["payload"]) for r in rows["events"] if r["kind"] == "kernel-receipt-recovery"][-1]
    assert recovery["installed_version"] == recovery["consumer_version"] == 3
    assert not recovery["recovery"]["used_genesis"]
    assert audit(tmp_path)["status"] == "PASS_SCOPED_CPU_FIXTURE"


def test_kernel_install_refuses_missing_actual_predispatch_receipt(tmp_path):
    km = kernel_module()
    s = Store(tmp_path); s.initialize(development_tasks()[0], CpuFixtureProvider.identity, CpuFixtureProvider.tier)
    p = prepared(s, "k0", 0)
    with pytest.raises(AssertionError, match="actual pre-execution"):
        s.install(p, "revtrace", adapter=km.create_adapter(s, p))


def test_untrusted_candidate_is_not_misclassified_as_false_rejection(tmp_path):
    s = Store(tmp_path); s.initialize(development_tasks()[0], CpuFixtureProvider.identity, CpuFixtureProvider.tier)
    f = s.freeze("untrusted", 0); p = CpuFixtureProvider(); e = p.generate(p.prepare(f))
    e["selection_authorized"] = False
    proposal = s.register_selection(f, e)
    assert s.install(proposal)["status"] == "rejected"
    result = audit(tmp_path)
    assert result["false_rejections"] == 0 and not result["violations"]


def test_actual_process_exit_after_sql_commit_restores_kernel_without_duplicate(tmp_path):
    km = kernel_module()
    s = Store(tmp_path); s.initialize(development_tasks()[0], CpuFixtureProvider.identity, CpuFixtureProvider.tier)
    proposal = kernel_prepared(s, "crash0", 0, km)
    (tmp_path / "proposal.json").write_text(json.dumps(proposal))
    code = (
        "import sys,json; from pathlib import Path; "
        "sys.path.insert(0,sys.argv[2]); "
        "from native_store import Store; from revtrace_adapter import create_adapter; "
        "p=Path(sys.argv[1]); s=Store(p); q=json.loads((p/'proposal.json').read_text()); "
        "s.install(q,'revtrace',crash=True,adapter=create_adapter(s,q))"
    )
    proc = subprocess.run([sys.executable, "-B", "-c", code, str(tmp_path), str(runtime_source())], capture_output=True, text=True, timeout=30)
    assert proc.returncode == 91, proc.stderr
    restarted = Store(tmp_path)
    restarted.mutate("owner-change")
    result = restarted.install(proposal, "revtrace", adapter=km.create_adapter(restarted, proposal))
    assert result["receipt"]["seq"] == 1
    assert len(restarted.dump()["admissions"]) == 2
    recovery = [json.loads(x["payload"]) for x in restarted.dump()["events"] if x["kind"] == "kernel-receipt-recovery"][-1]
    assert recovery["installed_version"] == recovery["consumer_version"] == 1
    assert recovery["recovery"]["epoch"] == 2
    assert recovery["recovery"]["history_entries"] == 1 and not recovery["recovery"]["used_genesis"]
    restarted.deliver()
    assert audit(tmp_path)["status"] == "PASS_SCOPED_CPU_FIXTURE"


@pytest.mark.skipif(importlib.util.find_spec("langgraph") is None, reason="fixed native dependency not installed")
@pytest.mark.parametrize("family_index", [0, 1])
@pytest.mark.parametrize("schedule", ["unchanged", "source-change", "owner-change", "crash-after-commit"])
@pytest.mark.parametrize("mode", ["standard", "revtrace"])
def test_native_checkpoint_resume_and_again_write(tmp_path, family_index, schedule, mode):
    t = development_tasks()[family_index]
    root = tmp_path / "cell"
    cfg = {"provider": {"kind": "cpu_fixture"}, "mode": mode, "worker_timeout_seconds": 90}
    if mode == "revtrace":
        kernel_module()
        cfg.update(adapter_module="revtrace_adapter", runtime_source_path=str(runtime_source()))
    run_cell(root, t, cfg, schedule)
    r = audit(root)
    assert r["status"] == "PASS_SCOPED_CPU_FIXTURE"
    assert r["committed_cycles"] == 3 and len(r["actual_downstream_input_operations"]) >= 2
    assert r["task_execution_counts"]["cycle-0:compute"] == 1
    assert r["task_execution_counts"]["cycle-0:install"] == (2 if schedule == "crash-after-commit" else 1)
    assert r["native_checkpoint_returns"] >= 3

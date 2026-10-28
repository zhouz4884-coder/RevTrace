"""CPU-only policy/config/control tests, not native model measurements."""
from pathlib import Path
from actual_provider import physical_gpu_call_count,rejection_counts


def test_cpu_structural_rejection_is_not_counted_as_gpu_verification():
    calls=[{'operation':'generate'},{'operation':'verify-structural-rejection','accepted':False,'actual_gpu_seconds':0.},
           {'operation':'generate'},{'operation':'verify','accepted':False}]
    assert physical_gpu_call_count(calls)==3
    assert rejection_counts(calls)=={'content':1,'structural':1}
import json
import pytest

import actual_provider
from native_power import integrate
from pilot_plan import ARMS, cell_config, evaluate_cell, plan, self_check_gate
from tasks import development_tasks


@pytest.mark.parametrize("mode,roles", [("direct", ["authority"]), ("candidate_only", ["proposal"]),
                                       ("strict_fallback", ["authority", "proposal"])])
def test_mode_loads_only_required_models(tmp_path, monkeypatch, mode, roles):
    loaded = []
    class Fake:
        def __init__(self, config, role, device, dtype):
            loaded.append(role); self.contract = {"role": role, "device": device, "dtype": dtype}
        def input_ids(self, messages): return [1, 2]
    monkeypatch.setattr(actual_provider, "ActualModel", Fake)
    monkeypatch.setattr(actual_provider, "load_asset_manifest", lambda *args: "verified-fixture-assets")
    config = {"identity": "fixture", "selection_mode": mode, "experiment_root": str(tmp_path),
              "model_path": str(tmp_path / "model"), "model_manifest": str(tmp_path / "manifest"),
              "authority_device": 1, "authority_dtype": "float32", "proposer_device": 0, "proposer_dtype": "float16"}
    p = actual_provider.ActualProvider(config)
    assert loaded == roles
    t = development_tasks()[0]
    prepared = p.prepare({"family": t["family"], "source": t["source"], "prior_memory": t["initial_memory"],
                          "request": t["requests"][0], "request_hash": "fixture", "cycle": 0})
    assert prepared["input_ids"] == [1, 2]
    assert (p.authority is None) == (mode == "candidate_only")
    assert (p.proposer is None) == (mode == "direct")


def test_strict_self_replay_failure_does_not_delete_direct_native_work():
    rows = [{"actual_same_input": True, "calls_completed": True, "full_stop": True,
             "repeat_tokens_equal": True, "self_verification_accepted": False}]
    gate = self_check_gate(rows)
    assert gate["direct_provider_go"] and not gate["strict_provider_go"]
    cells = plan(development_tasks(), "smoke", gate["strict_provider_go"])
    assert len(cells) == 10 and sum(c["eligible"] for c in cells) == 6
    assert all(c["eligible"] for c in cells if c["arm"] in {"standard_direct", "revtrace_direct"})
    assert all(c["skip_reason"] == "STRICT_PROVIDER_SELF_CHECK_NO_GO" for c in cells if not c["eligible"])


def test_development_is_a_distinct_plan_with_shared_smoke_cell_identity():
    smoke = plan(development_tasks(), "smoke", True)
    dev = plan(development_tasks(), "development", True)
    assert len(smoke) == 10 and len(dev) == 44
    assert {c["id"] for c in smoke} <= {c["id"] for c in dev}
    assert len({c["id"] for c in dev}) == len(dev)
    assert sum(c["schedule"] == "crash-after-commit" for c in dev) == 4


def test_direct_corrupt_label_is_not_a_rejection_claim():
    config = json.loads((Path(__file__).parent / "PILOT_CONFIG.json").read_text())
    cell = next(c for c in plan(development_tasks(), "development", True)
                if c["arm"] == "standard_direct" and c["condition"] == "cycle0_coherent")
    actual = cell_config(config, cell, "/frozen/runtime/src")
    assert actual["candidate_fault_interpretation"].startswith("not_exposed")
    assert actual["provider"]["selection_mode"] == "direct"


def test_negative_admission_never_becomes_total_safety_pass():
    cell = {"arm": "candidate_only"}
    checked = {"violations": ["unauthorized-state-admission:cycle-0"], "unknown": [],
               "evidence_tier": "ACTUAL_GPU_MODEL", "native_multi_cycle_evidence_complete": True,
               "cycle_outcomes": [{"current_step_success": False, "current_output_valid": False}],
               "verification_rejections_observed": 0}
    runtime = {"offered_cycles": 1, "committed_cycles": 1, "unfulfilled_cycles": 0}
    out = evaluate_cell(cell, checked, runtime)
    assert out["gate"] == "OBSERVED_UNPROTECTED_COUNTEREXAMPLE" and not out["protected"]
    checked["violations"].append("wrong-consumed-memory:x")
    assert not evaluate_cell(cell, checked, runtime)["audit_usable"]


def test_physical_power_includes_idle_second_gpu():
    rows = [{"perf": t, "gpu": {"0": {"watts": 30}, "1": {"watts": 120}}} for t in (0., 2., 4.)]
    out = integrate(rows, .5, 3.5)
    assert out == {"GPU0_joules": 90., "GPU1_joules": 360., "both_GPU_joules": 450.}

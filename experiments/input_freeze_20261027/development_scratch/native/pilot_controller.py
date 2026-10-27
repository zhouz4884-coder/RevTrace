"""Bounded real-GPU native pilot. Explicit stage calls; no automatic big matrix.

Run only after this complete source and CPU tests are frozen. A Strict self-check
NO-GO does not prevent Direct Standard/RevTrace lifecycle evidence.
"""
from pathlib import Path
import argparse
import hashlib
import importlib.metadata
import json
import os
import platform
import subprocess
import sys
import time
import traceback
import xml.etree.ElementTree as ET

from independent_checker import audit
from native_store import Store
from native_workflow import run_cell
from native_power import PowerSampler
from pilot_plan import ARMS, cell_config, evaluate_cell, hash_value, plan, self_check_gate, smoke_gate
from tasks import development_tasks, validation_tasks, validate_schema

B = Path("/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9")
PINS = {"langgraph": "1.0.3", "langgraph-checkpoint-sqlite": "3.0.0", "langgraph-checkpoint": "3.0.1", "langchain-core": "1.7.0"}


def put(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


def file_sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require_idle():
    out = subprocess.check_output(["nvidia-smi", "--query-compute-apps=pid", "--format=csv,noheader,nounits"], text=True)
    if out.strip():
        raise RuntimeError("GPU process is active; do not overlap or kill another workload")


def check_cpu_gate(path, source_commit):
    gate = json.loads(path.read_text())
    assert gate["source_commit"] == source_commit and gate["status"] == "PASS"
    report = Path(gate["raw_test_report"])
    assert file_sha(report) == gate["raw_test_sha256"]
    tree = ET.parse(report)
    cases = tree.findall(".//testcase")
    assert cases and not tree.findall(".//failure") and not tree.findall(".//error") and not tree.findall(".//skipped")
    assert any("native_checkpoint_resume_and_again_write" in t.attrib.get("name", "") for t in cases), "native API lifecycle tests were not executed"
    return {"gate_sha256": file_sha(path), "report_sha256": file_sha(report), "passed_cases": len(cases)}


def freeze(args, config):
    root, output = args.source_root.resolve(), args.output.resolve()
    assert output.is_relative_to(B / "results/revtrace/freeze_boundary_20261027")
    assert Path(args.model_manifest).resolve().is_relative_to(B)
    source = json.loads(args.source_manifest.read_text())
    assert len(source["code_commit"]) == 40
    for row in source["files"]:
        p = (root / row["path"]).resolve()
        assert p.is_relative_to(root) and file_sha(p) == row["sha256"]
    assert any((root / r["path"]).resolve() == Path(__file__).resolve() for r in source["files"])
    cpu = check_cpu_gate(args.cpu_gate, source["code_commit"])
    packages = {n: importlib.metadata.version(n) for n in [*PINS, "torch", "transformers"]}
    assert all(packages[n] == v for n, v in PINS.items())
    hardware = subprocess.check_output(["nvidia-smi", "--query-gpu=index,name,uuid,driver_version,memory.total", "--format=csv,noheader"], text=True)
    assert hardware.count("RTX 3090") == 2
    config = {**config, "provider": {**config["provider"], "model_manifest": str(args.model_manifest.resolve())}}
    signature = {"source_commit": source["code_commit"], "source_manifest_sha256": file_sha(args.source_manifest),
        "config": config, "config_sha256": hash_value(config), "model_manifest_sha256": file_sha(args.model_manifest),
        "cpu_gate": cpu, "packages": packages,
        "development_tasks": development_tasks(), "validation_tasks_frozen_not_run": validation_tasks()}
    if (output / "FREEZE.json").exists():
        old = json.loads((output / "FREEZE.json").read_text())
        assert old["identity"] == signature, "resumption source/config/env changed; create a new frozen run"
    else:
        assert not output.exists(), "unregistered result directory must not be reused"
        output.mkdir(parents=True)
        env = {"python": sys.version, "platform": platform.platform(), "packages": packages, "hardware": hardware}
        put(output / "ENVIRONMENT.json", env)
        put(output / "FREEZE.json", {"experiment_id": config["experiment_id"], "identity": signature,
            "environment_sha256": file_sha(output / "ENVIRONMENT.json"), "raw_result_location": str(output),
            "aggregate_summary_location": str(output / "SUMMARY.json"), "gate_decision_location": str(output / "GATE.json"),
            "scope": "actual-model native application lifecycle; not online ASR capacity"})
    return config


def selfcheck_worker(request):
    from actual_provider import ActualProvider
    root = Path(request["output"]); root.mkdir(parents=True, exist_ok=False)
    config = {**request["provider"], "selection_mode": "direct"}
    config.pop("candidate_substitution", None)
    rows = []
    try:
        provider = ActualProvider(config)
        for task in request["tasks"]:
            store = Store(root / task["id"])
            store.initialize(task, provider.identity, provider.tier)
            frozen = store.freeze("operator-self-check", 0)
            prepared = provider.prepare(frozen)
            one = provider.authority.generate(prepared["input_ids"], "same-input-autoregressive-first")
            put(root / task["id"] / "first.json", one)
            two = provider.authority.generate(prepared["input_ids"], "same-input-autoregressive-repeat")
            put(root / task["id"] / "repeat.json", two)
            verified = provider.authority.verify(prepared["input_ids"], one["tokens"], "complete-self-verification")
            put(root / task["id"] / "verification.json", verified)
            row = {"task_id": task["id"], "family": task["family"], "calls_completed": True,
                "actual_same_input": one["actual_input_ids"] == two["actual_input_ids"] == prepared["input_ids"],
                "repeat_tokens_equal": one["tokens"] == two["tokens"],
                "full_stop": one["complete"] and two["complete"],
                "schema_valid_first": validate_schema(task["family"], one["value"]),
                "self_verification_accepted": verified["accepted"], "request": prepared,
                "first": one, "repeat": two, "verification": verified}
            if verified["operation"] == "verify":
                assert verified["actual_input_ids"] == prepared["input_ids"] + one["tokens"]
            rows.append(row); put(root / (task["id"] + ".json"), row)
        put(root / "GATE.json", self_check_gate(rows))
        put(root / "RESULT.json", {"rows": rows, "gate": self_check_gate(rows),
            "scope": "paid GPU operator self-replay; not native application results"})
    except BaseException:
        put(root / "STOP.json", {"error": traceback.format_exc(), "completed_tasks": len(rows), "rows": rows})
        raise


def subprocess_selfcheck(output, config, source_root):
    target = output / "operator_self_check"
    if (target / "RESULT.json").exists():
        return json.loads((target / "RESULT.json").read_text())["gate"]
    assert not target.exists(), "partial self-check needs explicit diagnosis, not silent restart"
    require_idle()
    req = {"output": str(target), "provider": config["provider"], "tasks": development_tasks()}
    put(output / "SELF_CHECK_REQUEST.json", req)
    sampler = PowerSampler(output / "self_check_power.jsonl")
    start = time.perf_counter()
    failure = None
    try:
        with (output / "self_check_stdout.txt").open("x") as out, (output / "self_check_stderr.txt").open("x") as err:
            p = subprocess.run([sys.executable, "-B", str(Path(__file__).resolve()), "--selfcheck-worker",
                                str(output / "SELF_CHECK_REQUEST.json")], stdout=out, stderr=err, timeout=600)
        assert p.returncode == 0, "operator self-check process failed; preserve diagnostics"
    except BaseException:
        failure = traceback.format_exc()
        put(output / "SELF_CHECK_PROCESS_FAILURE.json", {"error": failure, "actual_work_retained": True})
    finally:
        end = time.perf_counter(); put(output / "SELF_CHECK_ENERGY.json", sampler.finish_interval(start, end))
        sampler.close()
    if failure:
        raise RuntimeError("operator self-check failed; inspect retained process/call/power evidence")
    return json.loads((target / "RESULT.json").read_text())["gate"]


def execute_cell(output, cell, config, runtime_source):
    from independent_codec import Codec
    root = output / "cells" / cell["id"]
    if not cell["eligible"]:
        return {"id": cell["id"], "arm": cell["arm"], "family": cell["task"]["family"],
                "execution_status": "SKIPPED_PROVIDER_NO_GO", "reason": cell["skip_reason"]}
    actual_cfg = cell_config(config, cell, runtime_source)
    identity = {"cell": cell, "config": actual_cfg}
    if (root / "CELL_OUTCOME.json").exists():
        assert json.loads((root / "CELL_IDENTITY.json").read_text()) == identity
        return json.loads((root / "CELL_OUTCOME.json").read_text())
    assert not root.exists(), "partial cell retained; diagnose before any rerun"
    root.parent.mkdir(exist_ok=True)
    require_idle()
    sampler = PowerSampler(output / (cell["id"] + "__power.jsonl"))
    start = time.perf_counter()
    status, runtime = "COMPLETE", None
    error = None
    try:
        runtime = run_cell(root, cell["task"], actual_cfg, cell["schedule"])
    except BaseException:
        status, error = "FAILED", traceback.format_exc()
        root.mkdir(exist_ok=True)
        put(root / "FAILED.json", {"error": error, "all_offered_cycles": len(cell["task"]["requests"]),
                                  "scope": "failed cells remain in plan; no automatic rerun"})
    finally:
        end = time.perf_counter()
        energy = sampler.finish_interval(start, end); sampler.close()
    put(root / "CELL_IDENTITY.json", identity)
    put(root / "ENERGY.json", energy)
    row = {"id": cell["id"], "arm": cell["arm"], "family": cell["task"]["family"],
           "condition": cell["condition"], "repeat": cell["repeat"], "schedule": cell["schedule"],
           "execution_status": status, "energy": energy, "error": error}
    if runtime is not None:
        row["runtime"] = {k: v for k, v in runtime.items() if k != "cycles"}
        try:
            codec = Codec(config["provider"]["model_path"], config["provider"]["model_manifest"])
            checked = audit(root, codec.encode, codec.decode)
            put(root / "INDEPENDENT_AUDIT.json", checked)
            row["evaluation"] = evaluate_cell(cell, checked, runtime)
        except BaseException:
            row["execution_status"] = "FAILED_AUDIT"
            row["audit_error"] = traceback.format_exc()
            row["evaluation"] = {"audit_usable": False, "gate": "AUDIT_FAILURE_RETAINED_ACTUAL_RUN"}
            put(root / "AUDIT_FAILURE.json", {"error": row["audit_error"], "actual_GPU_run_must_not_be_repeated_automatically": True})
        row["cost_evidence_complete"] = (energy["status"] == "MEASURED_BOTH_PHYSICAL_GPUS" and
                                         not runtime["GPU_compute_cost_has_unknown_failure"])
        if not row["cost_evidence_complete"]:
            row["evaluation"]["audit_usable"] = False
            row["evaluation"]["cost_gate"] = "UNKNOWN_COST_REQUIRES_DIAGNOSIS"
    put(root / "CELL_OUTCOME.json", row)
    return row


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--selfcheck-worker", type=Path)
    p.add_argument("--source-root", type=Path); p.add_argument("--source-manifest", type=Path)
    p.add_argument("--cpu-gate", type=Path); p.add_argument("--model-manifest", type=Path)
    p.add_argument("--config", type=Path); p.add_argument("--output", type=Path)
    p.add_argument("--stage", choices=["smoke", "development"], default="smoke")
    a = p.parse_args()
    os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
    if a.selfcheck_worker:
        selfcheck_worker(json.loads(a.selfcheck_worker.read_text())); return
    assert all([a.source_root, a.source_manifest, a.cpu_gate, a.model_manifest, a.config, a.output])
    require_idle()
    config = freeze(a, json.loads(a.config.read_text()))
    if a.stage == "development":
        old = json.loads((a.output / "SMOKE_GATE.json").read_text())
        assert old["status"] == "GO_FOR_SEPARATELY_REQUESTED_DEVELOPMENT", "smoke gate failed or incomplete"
    gate = subprocess_selfcheck(a.output, config, a.source_root)
    assert gate["direct_provider_go"], "Direct provider failed actual input/execution controls"
    cells = plan(development_tasks(), a.stage, gate["strict_provider_go"])
    put(a.output / (a.stage.upper() + "_PLAN.json"), {"cells": cells, "operator_gate": gate})
    rows = []
    for cell in cells:
        row = execute_cell(a.output, cell, config, a.source_root / "runtime" / "src")
        rows.append(row)
        progress = {"stage": a.stage, "completed_plan_entries": len(rows), "expected": len(cells), "rows": rows}
        put(a.output / (a.stage.upper() + "_PROGRESS.json"), progress)
        put(a.output / "PROGRESS.json", progress)
        if row["execution_status"] == "FAILED" or row.get("evaluation", {}).get("audit_usable") is False:
            break
    complete = len(rows) == len(cells)
    result = {"stage": a.stage, "plan_entries": len(cells), "completed_plan_entries": len(rows),
        "execution_complete": complete, "actual_run_cells": sum(r["execution_status"] != "SKIPPED_PROVIDER_NO_GO" for r in rows),
        "skipped_strict_no_go_cells": sum(r["execution_status"] == "SKIPPED_PROVIDER_NO_GO" for r in rows),
        "rows": rows, "operator_gate": gate,
        "scope": "actual native lifecycle and quality/cost observations; no capacity or universal contamination claim"}
    stage_summary = a.output / (a.stage.upper() + "_SUMMARY.json")
    put(stage_summary, result)
    stage_index = {}
    for stage_name in ("SMOKE", "DEVELOPMENT"):
        path = a.output / (stage_name + "_SUMMARY.json")
        if path.exists():
            stage_index[stage_name.lower()] = {"path": str(path), "sha256": file_sha(path)}
    put(a.output / "SUMMARY.json", {"latest_stage": a.stage, "stage_summaries": stage_index,
                                   "scope": "index only; complete per-stage outcomes retained separately"})
    decision = smoke_gate(rows) if a.stage == "smoke" and complete else {
        "status": "DEVELOPMENT_EXECUTED_REQUIRES_INDEPENDENT_REVIEW" if complete else "INCOMPLETE_REPAIR_REQUIRED"}
    put(a.output / (a.stage.upper() + "_GATE.json"), decision)
    put(a.output / "GATE.json", decision)
    print(json.dumps({"stage": a.stage, "complete": complete, "gate": decision, "rows": len(rows)}))


if __name__ == "__main__":
    main()

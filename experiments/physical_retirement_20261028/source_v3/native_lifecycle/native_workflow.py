"""Native LangGraph multi-cycle runner; CPU fixture and real providers are explicit.

A real provider factory must implement prepare(frozen), generate(request), and
return the complete evidence required by Store.register_selection. It must log
actual model-consumed IDs, actual complete Tokens/Stop and trusted rendering.
The fixture uses byte tokens and is never evidence of neural model behavior.
"""
from __future__ import annotations

import argparse
import importlib
import importlib.metadata
import json
import os
from pathlib import Path
import subprocess
import sys
import time

from native_store import Store, digest
from tasks import canonical, development_tasks, fixture_value, messages
from actual_provider import physical_gpu_call_count


class CpuFixtureProvider:
    identity = "deterministic-cpu-fixture-v1"
    tier = "CPU_FIXTURE_NO_MODEL"

    def prepare(self, frozen):
        m = messages(frozen)
        return {"input_ids": list(canonical(m).encode()), "messages": m,
                "frozen": frozen, "frozen_request_hash": frozen["request_hash"],
                "contract": {"kind": self.tier, "encoding": "utf8-byte-fixture", "eos_id": 256}}

    def generate(self, request):
        start = time.time_ns()
        f = request["frozen"]
        value = fixture_value(f["family"], f["source"], f["prior_memory"], f["request"])
        text = canonical(value)
        return {"provider_identity": self.identity, "evidence_tier": self.tier,
                "request": request, "actual_input_ids": list(request["input_ids"]),
                "tokens": list(text.encode()) + [256], "rendered_text": text, "value": value,
                "terminated_by_eos": True, "complete": True,
                "selection_authorized": True, "physical_worker_drained": True,
                "contract": request["contract"],
                "started_ns": start, "completed_ns": time.time_ns(), "actual_gpu_seconds": 0}


def provider(config):
    if config["kind"] == "cpu_fixture":
        return CpuFixtureProvider()
    if config["kind"] == "actual_model":
        obj = importlib.import_module(config["module"]).create_provider(config)
        assert obj.tier == "ACTUAL_GPU_MODEL", "real provider must declare actual execution tier"
        return obj
    raise ValueError(config["kind"])


def native_worker(request):
    from langgraph.checkpoint.sqlite import SqliteSaver
    from langgraph.func import entrypoint, task
    from langgraph.types import Command, interrupt

    store = Store(request["directory"])
    config = request["provider"]

    @task
    def compute(data):
        store.record("native-task-execute", {"task": "compute", "op": data["op"], "cycle": data["cycle"]})
        frozen = store.freeze(data["op"], data["cycle"])
        actual = provider(config)
        prepared = actual.prepare(frozen)
        execution_adapter = None
        if data["mode"] == "revtrace":
            module = importlib.import_module(request["adapter_module"])
            execution_adapter = module.create_execution_adapter(store, frozen, prepared)
            execution_adapter.dispatch_before_execution()
        selected = actual.generate(prepared)
        if selected.get("status") == "unfulfilled":
            if execution_adapter is not None:
                execution_adapter.retain_execution_failure(selected)
            store.record("model-unfulfilled", {"op": data["op"], "frozen": frozen, "evidence": selected})
            return {"unfulfilled": True, "frozen": frozen, "evidence": selected}
        if execution_adapter is not None:
            execution_adapter.complete_after_execution(selected)
        return store.register_selection(frozen, selected)

    @task
    def install(data, proposal):
        store.record("native-task-execute", {"task": "install", "op": data["op"], "cycle": data["cycle"]})
        if proposal.get("unfulfilled"):
            return {"status": "unfulfilled", "reason": "model-selection-or-structure-gate",
                    "op": data["op"], "evidence_retained": True}
        adapter = None
        if data["mode"] == "revtrace":
            module = importlib.import_module(request["adapter_module"])
            adapter = module.create_adapter(store, proposal)
        return store.install(proposal, data["mode"], crash=data.get("crash_after_commit", False), adapter=adapter)

    with SqliteSaver.from_conn_string(str(store.directory / "checkpoint.sqlite")) as saver:
        @entrypoint(checkpointer=saver)
        def workflow(data):
            proposed = compute(data).result()
            if data.get("interrupt_after_compute"):
                interrupt({"phase": "computed-before-install", "selection_id": proposed.get("selection_id"),
                           "unfulfilled": proposed.get("unfulfilled", False)})
            result = install(data, proposed).result()
            return {"proposal": proposed, "decision": result}

        graph_config = {"configurable": {"thread_id": request["thread_id"]}}
        action = request["action"]
        arg = request["data"] if action == "start" else Command(resume=True) if action == "resume_interrupt" else None
        assert action in {"start", "resume_interrupt", "resume_crash"}
        store.record("native-invoke", {"action": action, "thread_id": request["thread_id"]})
        output = workflow.invoke(arg, config=graph_config, durability="sync")
        saved = saver.get_tuple(graph_config)
        native = {"checkpoint_id": saved.checkpoint["id"] if saved else None,
                  "pending_writes": len(saved.pending_writes or []) if saved else None}
        store.record("native-return", {"action": action, "thread_id": request["thread_id"], "native": native})
        result = {"output": output, "native": native, "pid": os.getpid()}
        Path(request["result_path"]).write_text(json.dumps(result, indent=2, default=str) + "\n")


def invoke_process(directory, label, config, data, action, expected_exit=0):
    req = {"directory": str(directory), "provider": config["provider"],
           "adapter_module": config.get("adapter_module"), "data": data,
           "thread_id": data["op"], "action": action,
           "result_path": str(directory / (label + "_result.json"))}
    request_path = directory / (label + "_request.json")
    request_path.write_text(json.dumps(req, indent=2) + "\n")
    child_env = dict(os.environ)
    if config.get("runtime_source_path"):
        runtime = Path(config["runtime_source_path"]).resolve()
        assert (runtime / "revtrace" / "composed_kernel.py").is_file()
        child_env["PYTHONPATH"] = str(runtime) + os.pathsep + child_env.get("PYTHONPATH", "")
    process_started_ns = time.time_ns()
    process_started_perf = time.perf_counter()
    proc = subprocess.run([sys.executable, "-B", str(Path(__file__).resolve()), "--worker", str(request_path)],
                          text=True, capture_output=True, env=child_env,
                          timeout=config.get("worker_timeout_seconds", 240))
    (directory / (label + "_stdout.txt")).write_text(proc.stdout)
    (directory / (label + "_stderr.txt")).write_text(proc.stderr)
    Store(directory).record("driver-process-exit", {"label": label, "actual_exit": proc.returncode,
        "expected_exit": expected_exit, "process_started_ns": process_started_ns,
        "process_completed_ns": time.time_ns(), "whole_process_wall_seconds": time.perf_counter() - process_started_perf})
    if expected_exit == 91 and proc.returncode == 0 and Path(req["result_path"]).exists():
        failed_result = json.loads(Path(req["result_path"]).read_text())
        if failed_result["output"]["decision"]["status"] == "unfulfilled":
            Store(directory).record("faultpoint-not-reached", {"label": label, "reason": "model-unfulfilled"})
            return failed_result
    if proc.returncode != expected_exit:
        raise RuntimeError(f"{label}: expected {expected_exit}, got {proc.returncode}: {proc.stderr[-2000:]}")
    return None if expected_exit else json.loads(Path(req["result_path"]).read_text())


def run_cell(directory, task_spec, config, schedule):
    directory.mkdir(parents=True, exist_ok=False)
    if config["provider"]["kind"] == "cpu_fixture":
        identity, tier = CpuFixtureProvider.identity, CpuFixtureProvider.tier
    else:
        # Declared identity is validated against provider output at registration.
        identity, tier = config["provider"]["identity"], "ACTUAL_GPU_MODEL"
    store = Store(directory)
    store.initialize(task_spec, identity, tier)
    versions = {n: importlib.metadata.version(n) for n in
                ("langgraph", "langgraph-checkpoint-sqlite", "langgraph-checkpoint", "langchain-core")}
    (directory / "RUN_CONFIG.json").write_text(json.dumps({"task": task_spec, "config": config,
        "schedule": schedule, "versions": versions, "evidence_tier": tier}, indent=2) + "\n")
    results = []
    for cycle in range(len(task_spec["requests"])):
        data = {"op": f"cycle-{cycle}", "cycle": cycle, "mode": config["mode"],
                "interrupt_after_compute": cycle == 0 and schedule != "crash-after-commit",
                "crash_after_commit": cycle == 0 and schedule == "crash-after-commit"}
        first = invoke_process(directory, f"c{cycle}-start", config, data, "start",
                               91 if data["crash_after_commit"] else 0)
        if cycle == 0:
            if schedule in {"source-change", "owner-change"}:
                store.mutate(schedule)
            if data["crash_after_commit"]:
                if first is None:
                    # The dead process loses its write grant. Its already durable
                    # receipt remains queryable under the new owner epoch.
                    store.mutate("owner-change")
                    first = invoke_process(directory, f"c{cycle}-resume", config, data, "resume_crash")
            else:
                assert "__interrupt__" in first["output"]
                first = invoke_process(directory, f"c{cycle}-resume", config, data, "resume_interrupt")
        decision = first["output"]["decision"]
        initial_decision = decision
        if decision["status"] == "rejected":
            # Fresh operation re-freezes actual state. Cached old proposal is retained.
            retry = {"op": f"cycle-{cycle}-fresh", "cycle": cycle, "mode": config["mode"],
                     "interrupt_after_compute": False, "crash_after_commit": False}
            repaired = invoke_process(directory, f"c{cycle}-fresh", config, retry, "start")
            decision = repaired["output"]["decision"]
        results.append({"cycle": cycle, "initial_decision": initial_decision, "decision": decision,
                        "clean_pair_key": {"task_id": task_spec["id"], "cycle": cycle,
                                           "repeat": config.get("repeat", 0)}})
        store.deliver()
        store.deliver()
    dump = store.dump()
    events = [{"kind": r["kind"], "payload": json.loads(r["payload"])} for r in dump["events"]]
    evidence = [json.loads(r["evidence"]) for r in dump["selections"]]
    evidence += [e["payload"]["evidence"] for e in events if e["kind"] == "model-unfulfilled"]
    def duration(ev, a, b):
        return (ev[b] - ev[a]) / 1e9 if a in ev and b in ev else 0.
    output = {"status": "EXECUTION_FINISHED_OUTCOMES_REQUIRE_AUDIT", "evidence_tier": tier,
              "cycles": results, "model_task_quality_not_asserted": True,
              "offered_cycles": len(task_spec["requests"]),
              "committed_cycles": sum(r["decision"]["status"] == "committed" for r in results),
              "unfulfilled_cycles": sum(r["decision"]["status"] != "committed" for r in results),
              "rejected_install_attempts": sum(e["kind"] == "new-write-rejected" for e in events),
              "selection_attempts_including_fresh_retry": len(evidence),
              "actual_gpu_call_count": sum(physical_gpu_call_count(ev.get("actual_calls", [])) for ev in evidence),
              "all_execution_or_validation_operations": sum(len(ev.get("actual_calls", [])) for ev in evidence),
              "completed_GPU_compute_seconds": sum(ev.get("actual_gpu_seconds", sum(c["actual_gpu_seconds"] for c in ev.get("actual_calls", []))) for ev in evidence),
              "GPU_compute_cost_has_unknown_failure": any(ev.get("reason") == "provider-execution-failure" for ev in evidence),
              "asset_validation_seconds": sum(duration(ev, "asset_validation_started_ns", "asset_validation_completed_ns") for ev in evidence),
              "model_loading_seconds": sum(duration(ev, "load_started_ns", "load_ready_ns") for ev in evidence),
              "all_child_process_wall_seconds": sum(e["payload"]["whole_process_wall_seconds"] for e in events if e["kind"] == "driver-process-exit"),
              "GPU_energy_joules": None,
              "cost_scope": "all attempts retained; GPU compute differs from model loading and whole process wall; energy needs external recorded sampler"}
    (directory / "RESULT.json").write_text(json.dumps(output, indent=2) + "\n")
    (directory / "DATABASE_DUMP.json").write_text(json.dumps(dump, indent=2) + "\n")
    return output


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--worker", type=Path)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--config", type=Path)
    args = parser.parse_args()
    if args.worker:
        native_worker(json.loads(args.worker.read_text()))
        return
    assert args.out and args.config, "freeze config before running"
    config = json.loads(args.config.read_text())
    assert config["mode"] in {"minimal", "standard", "revtrace"}
    tasks = config.get("tasks") or development_tasks()
    args.out.mkdir(parents=True, exist_ok=False)
    rows = []
    for task in tasks:
        for schedule in config["schedules"]:
            rows.append(run_cell(args.out / (task["id"] + "__" + schedule), task, config, schedule))
    (args.out / "SUMMARY.json").write_text(json.dumps({"cells": len(rows), "results": rows}, indent=2) + "\n")


if __name__ == "__main__":
    main()

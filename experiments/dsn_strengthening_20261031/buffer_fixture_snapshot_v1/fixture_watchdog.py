"""External hard wall clock, independent of Owner/Observer/CUDA query progress.

Ownership/cleanup primitives come from the separately frozen resident harness.
No global CUDA PID is ever signalled. Query failure is unverified cleanup.
"""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import traceback

from fixture_paths import validate_live_output, frozen_path


class WatchdogError(RuntimeError):
    pass


def wait_hard(child, maximum_seconds, stop_owned, *, clock=time.monotonic, sleep=time.sleep,
              monitor=None):
    """The child may be blocked forever; this loop never calls into it."""
    begun = clock()
    deadline = begun + maximum_seconds
    while True:
        if monitor is not None: monitor()
        code = child.poll()
        now = clock()
        # A zero exit observed after the frozen bound is not on-time success.
        if now >= deadline:
            try:
                cleanup = stop_owned()
            except BaseException:
                cleanup = dict(status="FAIL_OWNED_CLEANUP_UNVERIFIED", failure=traceback.format_exc())
            return dict(timed_out=True, returncode=child.poll(), elapsed_seconds=clock() - begun,
                        cleanup=cleanup)
        if code is not None:
            return dict(timed_out=False, returncode=code, elapsed_seconds=now - begun)
        sleep(min(.05, max(0., deadline - now)))


def cleanup_owned(child, out, child_ticks, *, maximum_seconds, query_timeout, child_proof=None):
    # Use exactly the v2 campaign's cleanup: stop the owned Supervisor first,
    # re-read its metadata prefix, retire proved descendant/Owner sessions, and
    # use bounded CUDA queries. There is no second divergent cleanup policy.
    from run_paired_campaign import stop_owned_processes
    return stop_owned_processes(child, out, child_start_ticks=child_ticks,
                                known_members=(child_proof or {}).get("known_members", ()),
                                timeout=maximum_seconds, query_timeout=query_timeout)


def validate_registered_child(record, config, current, parent, *, config_sha256):
    if (record.get("child_pid") != os.getpid() or current is None or
            record.get("child_start_ticks") != current["start_ticks"] or
            parent is None or record.get("watchdog_pid") != parent["pid"] or
            record.get("watchdog_start_ticks") != parent["start_ticks"] or
            record.get("cell_id") != config["cell_id"] or
            record.get("config_sha256") != config_sha256 or
            record.get("nonce") != config["timing_fixture"]["nonce"]):
        raise WatchdogError("child lacks its live independent watchdog PID-generation binding")
    return record


def validate_watchdog_context(config, out, watchdog_dir, *, config_sha256):
    from process_cleanup import process_identity
    validate_live_output(config, out)
    expected = frozen_path(config["watchdog_result_location"], parent=config["frozen_raw_root"])
    if expected.as_posix() != str(watchdog_dir) or expected != (
            frozen_path(config["frozen_raw_root"]) / "watchdog" / config["cell_id"]):
        raise WatchdogError("unbound watchdog artifact location")
    record = json.loads((Path(watchdog_dir) / "CHILD_LAUNCH.json").read_bytes())
    return validate_registered_child(record, config, process_identity(os.getpid()),
                                     process_identity(os.getppid()), config_sha256=config_sha256)


def launch(config_path, out):
    from run_buffer_fixture import verify_dependency
    config_path, out = Path(config_path).resolve(), Path(out)
    config_raw = config_path.read_bytes()
    config = json.loads(config_raw)
    validate_live_output(config, out)
    if os.name != "posix": raise WatchdogError("formal fixture watchdog requires the declared Linux host")
    # The independent timer is frozen separately from original D2/C8 and
    # maximum_service_seconds; it does not authorize a state transition.
    limits = (config.get("maximum_process_seconds"), config.get("watchdog_cleanup_seconds"),
              config.get("watchdog_cli_timeout_seconds"))
    if limits != (900, 40, 5): raise WatchdogError("unfrozen process/cleanup/CLI wall-clock limits")
    base, harness = config["base_nn_source"], config["harness_source"]
    fixture = next(dep for dep in config["execution_dependencies"]
                   if Path(dep["source_root"]).resolve() == Path(__file__).resolve().parent)
    verified = [verify_dependency(dep) for dep in (base, harness, fixture)]
    for dep in (base, harness, fixture): sys.path.insert(0, dep["source_root"])
    from buffer_fixture import write_new
    from process_cleanup import process_identity, cuda_owners
    watchdog = Path(config["watchdog_result_location"])
    expected = frozen_path(config["frozen_raw_root"]) / "watchdog" / config["cell_id"]
    if str(watchdog) != str(expected): raise WatchdogError("watchdog directory differs from exact frozen cell")
    # Verify this second output's actual ancestors as well as its POSIX text.
    from fixture_paths import _reject_existing_links
    _reject_existing_links(watchdog)
    if not watchdog.resolve().is_relative_to(Path(config["frozen_raw_root"]).resolve()):
        raise WatchdogError("watchdog symlink escapes frozen run root")
    if out.exists(): raise WatchdogError("refuse to reuse an existing frozen cell output")
    out.parent.mkdir(parents=True, exist_ok=True)
    validate_live_output(config, out)
    watchdog.parent.mkdir(parents=True, exist_ok=True)
    watchdog.mkdir(exist_ok=False)
    me = process_identity(os.getpid())
    write_new(watchdog / "RUN_RECORD.json", dict(experiment_id=config["cell_id"],
              config_path=str(config_path), config_sha256=hashlib.sha256(config_raw).hexdigest(),
              code_commit=fixture["source_commit"], execution_dependencies=verified,
              raw_result_location=str(out), watchdog_raw=str(watchdog), maximum_process_seconds=limits[0],
              gate_decision_location=str(watchdog / "WATCHDOG_GATE.json")))
    command = [sys.executable, str(Path(__file__).with_name("run_buffer_fixture.py")),
               "--execute-child", "--config", str(config_path), "--out", str(out),
               "--watchdog-dir", str(watchdog)]
    child = None
    ticks = None
    child_proof = [None]
    try:
        with (watchdog / "trial.log").open("xb") as stream:
            child = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=stream,
                                     stderr=subprocess.STDOUT, start_new_session=True)
            identity = process_identity(child.pid)
            if identity is None: raise WatchdogError("child exited before PID-generation registration")
            ticks = identity["start_ticks"]
            from process_cleanup import group_proof, refresh_proof
            child_proof[0] = group_proof(child.pid, ticks)
            write_new(watchdog / "CHILD_LAUNCH.json", dict(cell_id=config["cell_id"],
                      nonce=config["timing_fixture"]["nonce"], child_pid=child.pid, child_start_ticks=ticks,
                      config_sha256=hashlib.sha256(config_raw).hexdigest(),
                      watchdog_pid=me["pid"], watchdog_start_ticks=me["start_ticks"],
                      observed=time.perf_counter(), command=command))
            def monitor():
                child_proof[0] = refresh_proof(child_proof[0])
            state = wait_hard(child, limits[0], lambda: cleanup_owned(
                child, out, ticks, maximum_seconds=limits[1], query_timeout=limits[2],
                child_proof=child_proof[0]), monitor=monitor)
        if state["timed_out"]:
            write_new(watchdog / "WATCHDOG_GATE.json", dict(status="FAIL_HARD_PROCESS_WALL_CLOCK_PRESERVED", **state))
            raise WatchdogError("fixture child exceeded independent frozen process wall clock")
        if state["returncode"] != 0:
            cleanup = cleanup_owned(child, out, ticks, maximum_seconds=limits[1], query_timeout=limits[2],
                                    child_proof=child_proof[0])
            write_new(watchdog / "WATCHDOG_GATE.json", dict(status="FAIL_CHILD_PRESERVED", cleanup=cleanup, **state))
            raise WatchdogError("fixture child failed; raw and original gate preserved")
        remaining = cuda_owners(timeout=limits[2])
        if remaining: raise WatchdogError("CUDA owners remain after successful child exit")
        result = json.loads((out / "BUFFER_WITNESS_GATE.json").read_bytes())
        if not result["status"].startswith("PASS_CONTROLLED_REAL_NN_BUFFER_"):
            raise WatchdogError("child exit zero lacks the complete independent buffer witness gate")
        write_new(watchdog / "WATCHDOG_GATE.json", dict(status="PASS_EXTERNAL_HARD_CLOCK_CHILD_AND_PHYSICAL_DRAIN",
                  cuda_owners=[], buffer_gate_sha256=hashlib.sha256((out / "BUFFER_WITNESS_GATE.json").read_bytes()).hexdigest(), **state))
        return result
    except BaseException:
        if child is not None and ticks is not None and not (watchdog / "WATCHDOG_GATE.json").exists():
            try:
                cleanup = cleanup_owned(child, out, ticks, maximum_seconds=limits[1], query_timeout=limits[2],
                                        child_proof=child_proof[0])
            except BaseException: cleanup = dict(status="FAIL_OWNED_CLEANUP_UNVERIFIED", failure=traceback.format_exc())
            write_new(watchdog / "WATCHDOG_GATE.json", dict(status="FAIL_WATCHDOG_PRESERVED", cleanup=cleanup,
                      failure=traceback.format_exc()))
        raise

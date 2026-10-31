"""Invoke the shared resident Supervisor, then the independent buffer audit."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import traceback
import time
from fixture_paths import validate_live_output


def verify_dependency(dep):
    root, manifest = Path(dep["source_root"]).resolve(), Path(dep["source_manifest"])
    raw = manifest.read_bytes()
    if hashlib.sha256(raw).hexdigest() != dep["source_manifest_sha256"]:
        raise ValueError("execution dependency manifest SHA changed")
    value = json.loads(raw)
    def git(*args):
        return subprocess.check_output(["git", "-C", str(root), *args], text=True).strip()
    if Path(git("rev-parse", "--show-toplevel")).resolve() != root:
        raise ValueError("execution dependency is not an independent checkout")
    if git("rev-parse", "HEAD") != value["source_commit"] or value["source_commit"] != dep["source_commit"]:
        raise ValueError("execution dependency actual full commit differs")
    if git("status", "--porcelain", "--untracked-files=all"):
        raise ValueError("execution dependency checkout is dirty")
    if set(git("ls-files", "-z").split("\0")) - {""} != {row["path"] for row in value["files"]}:
        raise ValueError("execution dependency complete manifest differs")
    for row in value["files"]:
        path = (root / row["path"]).resolve()
        if not path.is_relative_to(root):
            raise ValueError("dependency manifest escapes its source root")
        data = path.read_bytes()
        if len(data) != row["bytes"] or hashlib.sha256(data).hexdigest() != row["sha256"]:
            raise ValueError("execution dependency source bytes changed")
    return dict(source_root=str(root), source_commit=value["source_commit"],
                source_manifest_sha256=dep["source_manifest_sha256"], files_verified=len(value["files"]))


def execute_child(config_path, out, watchdog_dir):
    config_path, out = Path(config_path), Path(out)
    config_raw = config_path.read_bytes()
    config = json.loads(config_raw)
    validate_live_output(config, out)
    base = config["base_nn_source"]
    harness = config["harness_source"]
    fixture = next(dep for dep in config["execution_dependencies"]
                   if Path(dep["source_root"]).resolve() == Path(__file__).resolve().parent)
    dependencies = [verify_dependency(dep) for dep in (base, harness, fixture)]
    # sys.path is inherited by Python spawn. Every module remains in its own
    # manifest-checked source checkout; nothing is copied over NN4f.
    for dep in (base, harness, fixture):
        sys.path.insert(0, dep["source_root"])
    # The child never launches models without its independent live watchdog.
    marker = Path(watchdog_dir) / "CHILD_LAUNCH.json"
    deadline = time.monotonic() + 5.
    while not marker.exists() and time.monotonic() < deadline:
        time.sleep(.01)
    from fixture_watchdog import validate_watchdog_context
    validate_watchdog_context(config, out, watchdog_dir, config_sha256=hashlib.sha256(config_raw).hexdigest())
    from buffer_fixture import timing_owner_entry, make_controller, NN_COMMIT, write_new
    from audit_buffer_witness import audit
    from resident_supervisor import run_resident
    if base["source_commit"] != NN_COMMIT or config["settings"]["source_commit"] != NN_COMMIT:
        raise ValueError("fixture cannot replace the original neural C/U source tag")
    controller = make_controller(config, out)
    try:
        summary = run_resident(config_path, base["source_manifest"], out,
                               owner_target=timing_owner_entry, observer=controller)
        result = audit(out)
        result["verified_execution_dependencies"] = dependencies
        write_new(out / "BUFFER_WITNESS_GATE.json", result)
        return result
    except BaseException:
        if out.exists() and not (out / "BUFFER_WITNESS_GATE.json").exists():
            write_new(out / "BUFFER_WITNESS_GATE.json", dict(
                status="FAIL_CONTROLLED_BUFFER_FIXTURE_PRESERVED", experiment_id=config["cell_id"],
                failure=traceback.format_exc(), verified_execution_dependencies=dependencies))
        raise
    finally:
        controller.close()


def run(config_path, out):
    """The public programmatic entry has the same external watchdog as CLI."""
    from fixture_watchdog import launch
    return launch(config_path, out)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--execute-child", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--watchdog-dir", type=Path, help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.execute_child:
        if args.watchdog_dir is None: parser.error("a registered watchdog is required for child execution")
        result = execute_child(args.config, args.out, args.watchdog_dir)
    else:
        result = run(args.config, args.out)
    print(json.dumps(dict(status=result["status"], experiment_id=result["experiment_id"])))


if __name__ == "__main__":
    main()

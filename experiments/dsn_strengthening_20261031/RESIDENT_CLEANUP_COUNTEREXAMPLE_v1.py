"""CPU-only characterization of the registered-dead-Owner finally branch.

No actual Process, model, Torch, CUDA, or group-kill operation is launched.
Expected for reviewed harness commit 78b92f: cleanup_calls == 0 (the defect).
"""
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import types
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
E = Path(__file__).resolve().parent / "paired_resident_source_dev"
F = ROOT / "experiments/dsn_native_resilience_20261030/source_v2"
sys.path[:0] = [str(E), str(F)]
import resident_supervisor as rs
import common


class Conn:
    def close(self):
        pass


class Owner:
    pid = 24680
    exitcode = -9

    def start(self):
        pass

    def is_alive(self):
        return False

    def join(self, *args):
        pass

    def kill(self):
        raise AssertionError("unexpected direct leader kill")


class Ctx:
    def Value(self, kind, value):
        return types.SimpleNamespace(value=value)

    def Process(self, **kwargs):
        return Owner()

    def Pipe(self, **kwargs):
        return Conn(), Conn()


class Reader:
    def __init__(self, connection, slot, incarnation, inbox, *args):
        inbox.put(dict(type="control", incarnation=0, payload=dict(
            kind="owner_group_started", owner_epoch=0, pid=24680, pgid=24680)))


class Power:
    def __init__(self, *args):
        self.recent = [dict(time=0)]
        self.error = None
        self.t = types.SimpleNamespace(is_alive=lambda: False)

    def close(self):
        pass


def main():
    scratch = E.parent / "resident_independent_review_cpu_scratch"
    scratch.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(dir=scratch) as folder:
        root = Path(folder)
        audio = root / "audio"
        audio.write_bytes(b"a")
        manifest = root / "manifest"
        manifest.write_bytes(b"{}")
        config = dict(
            cell_id="CPU_CLEANUP_BRANCH_ONLY",
            settings=dict(source_commit="test", sources=[dict(
                source_id="s", frames=8000, path=str(audio),
                audio_sha256=hashlib.sha256(b"a").hexdigest())]),
            harness_source=dict(
                source_root=str(E), source_manifest=str(manifest),
                source_manifest_sha256=common.sha(manifest), source_commit="test"),
            execution_dependencies=[],
            request_contract="closed_loop_single_outstanding_independent_EOS_v1",
            request_order=["s"], maximum_service_seconds=10)
        cfg = root / "config"
        cfg.write_text(json.dumps(config))
        out = root / "out"
        with (patch.object(rs, "verify_source", return_value={"source_commit": "test"}),
              patch.object(common, "verify_checkout", return_value={"source_commit": "test"}),
              patch.object(rs.mp, "get_context", return_value=Ctx()),
              patch.object(rs, "FramedReader", Reader),
              patch.object(rs, "BoundedPower", Power),
              patch.object(rs, "start_ticks", return_value=123),
              patch.object(rs.os, "getpgid", return_value=24680, create=True),
              patch.object(rs, "kill_owner_group") as cleanup):
            try:
                rs.run_resident(cfg, manifest, out)
            except RuntimeError as error:
                failure = str(error)
            else:
                raise AssertionError("expected initial Owner-exit failure")
            result = dict(
                scope="CPU branch reproduction only; no actual child/GPU/model",
                failure=failure,
                registered_dead_owner_group_cleanup_calls=cleanup.call_count,
                gate=json.loads((out / "GATE.json").read_bytes())["status"])
            print(json.dumps(result))
            assert cleanup.call_count == 0
            assert failure == "Owner failed before initial neural readiness"


if __name__ == "__main__":
    main()

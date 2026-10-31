"""Controlled timing only: original NN4f worker payloads and Owner stay intact.

The fixture must be frozen separately from NN4f. Nothing in this module grants
input eligibility, fabricates a neural result, or installs a Canonical state.
"""
from __future__ import annotations

import copy
import hashlib
import json
import os
from pathlib import Path
import time

from resilience_transport import FramedSender, CommandReceiver, HintReceiver, start_ticks
from resilience_inbound import semantic_fingerprint

NN_COMMIT = "4f4c3caba2b1068951d7a566e7d9e5aa6fc25f47"
NN_MANIFEST_SHA256 = "60ae549fcc98165a74e5a3dc420bf93418296099fa12b410572b15d281b2c457"
SPEC_ENV = "REVTRACE_BUFFER_FIXTURE_CONTEXT_V1"
SCHEMA = "revtrace-buffer-fixture-v1"


class FixtureError(RuntimeError):
    pass


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False).encode("utf8")


def sha_value(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def write_new(path, value):
    """Publish a complete immutable marker, never an old or partial release."""
    path = Path(path)
    temporary = path.with_name(path.name + f".tmp-{os.getpid()}")
    with temporary.open("xb") as stream:
        stream.write(canonical(value) + b"\n")
        stream.flush()
        os.fsync(stream.fileno())
    # POSIX link is an atomic create-if-absent. Windows rename also refuses
    # an existing destination and does not require hardlink privileges.
    try:
        if os.name == "nt":
            os.rename(temporary, path)
        else:
            os.link(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def validate_spec(spec):
    required = {"schema", "experiment_id", "nonce", "source_id", "expect_match",
                "parent_start", "parent_end", "child_end", "barrier_timeout_seconds",
                "startup_timeout_seconds", "base_nn_commit", "base_manifest_sha256",
                "historical_parent_prediction_sha", "historical_parent_actual_sha"}
    if not required.issubset(spec):
        raise FixtureError("incomplete frozen timing specification")
    if spec["schema"] != SCHEMA or spec["base_nn_commit"] != NN_COMMIT:
        raise FixtureError("wrong timing schema or imported neural source")
    if spec["base_manifest_sha256"] != NN_MANIFEST_SHA256:
        raise FixtureError("wrong imported neural manifest")
    if type(spec["expect_match"]) is not bool:
        raise FixtureError("match expectation must be boolean")
    expected = (16000, 24000, 32000) if spec["expect_match"] else (24000, 32000, 40000)
    if tuple(spec[k] for k in ("parent_start", "parent_end", "child_end")) != expected:
        raise FixtureError("changed preselected original input boundaries")
    for key in ("experiment_id", "nonce", "source_id"):
        if not isinstance(spec[key], str) or not spec[key] or any(c in spec[key] for c in "/\\\0"):
            raise FixtureError("invalid bound fixture namespace")
    if len(spec["nonce"]) < 16:
        raise FixtureError("fixture nonce too short")
    for key in ("barrier_timeout_seconds", "startup_timeout_seconds"):
        value = spec[key]
        if type(value) not in (int, float) or not 0 < value <= 1200:
            raise FixtureError("invalid frozen barrier bound")
    positive = "264652c8230cb0f5fe873170975b170f3a82de7f003dc3baac853a9f86ba3169"
    predicted = positive if spec["expect_match"] else "d25f4c1b78a3dbf8603e3184a5073ac5ef464f17e536d47ce8445ba33ad53e17"
    actual = positive if spec["expect_match"] else "951d27d89c334b8d15689a4ecb0f033a589feaee6a7a2352054cd6ef8b778827"
    if (spec["historical_parent_prediction_sha"], spec["historical_parent_actual_sha"]) != (predicted, actual):
        raise FixtureError("historical exact-state target binding changed")
    return copy.deepcopy(spec)


def event_phase(event, spec):
    if event.get("source_id") != spec["source_id"] or event.get("dispatch_epoch") != 0:
        return None
    if (event.get("kind") == "asr_early" and
            event.get("start_state", {}).get("frontier") == spec["parent_start"] and
            event.get("end_frontier") == spec["parent_end"]):
        return "parent"
    if (event.get("kind") == "completed" and
            event.get("start", {}).get("frontier") == spec["parent_end"] and
            event.get("end", {}).get("frontier") == spec["child_end"]):
        return "child"
    return None


def bound_marker(event, *, spec, phase, slot, incarnation, owner_epoch, pid=None, ticks=None):
    pid = os.getpid() if pid is None else pid
    ticks = start_ticks(pid) if ticks is None else ticks
    wire_event = dict(event, worker_incarnation=incarnation)
    return dict(schema=SCHEMA, experiment_id=spec["experiment_id"], nonce=spec["nonce"],
                phase=phase, owner_epoch=owner_epoch, slot=slot, incarnation=incarnation,
                pid=pid, start_ticks=ticks, job_id=event["job_id"],
                source_id=event["source_id"], event_kind=event["kind"],
                event_semantic_sha256=semantic_fingerprint(wire_event),
                sent_complete_before_marker=True, observed=time.perf_counter())


def validate_marker(marker, event, job, started, spec, phase):
    """A marker alone never authorizes a kill or a parent release."""
    need = lambda condition, message: condition or _bad(message)
    need(marker.get("schema") == SCHEMA and marker.get("experiment_id") == spec["experiment_id"]
         and marker.get("nonce") == spec["nonce"], "foreign or stale fixture marker")
    need(marker.get("phase") == phase and event_phase(event, spec) == phase,
         "marker did not identify its frozen original event")
    need(marker.get("sent_complete_before_marker") is True, "marker predates full send")
    for field in ("job_id", "source_id"):
        need(marker.get(field) == event.get(field) == job.get(field), "marker job/source changed")
    need(marker.get("slot") == event.get("worker") == job.get("worker") == started.get("slot"),
         "marker physical slot changed")
    need(marker.get("incarnation") == event.get("worker_incarnation") == job.get("worker_incarnation")
         == started.get("incarnation"), "marker physical incarnation changed")
    need(marker.get("owner_epoch") == 0 and job.get("dispatch_epoch") == 0,
         "marker belongs to a different Owner/session namespace")
    need(marker.get("pid") == started.get("pid") and type(marker.get("pid")) is int
         and marker["pid"] > 0 and marker.get("start_ticks") == started.get("start_ticks")
         and type(marker.get("start_ticks")) is int, "marker PID/start_ticks changed")
    need(marker.get("event_semantic_sha256") == semantic_fingerprint(event),
         "marker payload differs from original received event")
    need(type(marker.get("observed")) in (int, float), "marker has no actual clock")
    return True


def _bad(message):
    raise FixtureError(message)


class TimingFramedSender(FramedSender):
    def __init__(self, *args, fixture_context, **kwargs):
        super().__init__(*args, **kwargs)
        self.fixture_context = fixture_context

    def put(self, event):
        # The original sender's header/pickle/body writes finish first.
        # Do not edit the event, forward a substitute, or touch C/U.
        super().put(event)
        context = self.fixture_context
        spec = context["spec"]
        phase = event_phase(event, spec) if context["owner_epoch"] == 0 else None
        if phase is None:
            return
        root = Path(context["root"])
        marker_path = root / f"{phase}.ready.json"
        if marker_path.exists():
            previous = json.loads(marker_path.read_bytes())
            if (previous.get("nonce") != spec["nonce"] or
                    previous.get("experiment_id") != spec["experiment_id"] or
                    previous.get("phase") != phase):
                raise FixtureError("foreign or stale existing timing barrier")
            if previous.get("job_id") != event["job_id"]:
                # A mismatch control must continue normal necessary work from
                # the actual parent. Its new UID may have the same frontiers
                # but is not the once-bound dead producer's conditional job.
                return
            raise FixtureError("same bound execution repeated its timing barrier")
        marker = bound_marker(event, spec=spec, phase=phase, slot=self.slot,
                              incarnation=self.inc, owner_epoch=context["owner_epoch"])
        write_new(marker_path, marker)
        deadline = time.perf_counter() + spec["barrier_timeout_seconds"]
        while time.perf_counter() < deadline:
            # The child is intentionally never released: it must actually die.
            if phase == "parent" and (root / "parent.release.json").exists():
                release = json.loads((root / "parent.release.json").read_bytes())
                if (release.get("nonce") != spec["nonce"] or
                        release.get("experiment_id") != spec["experiment_id"] or
                        release.get("parent_marker_sha256") != sha_value(marker) or
                        release.get("fence_checked") is not True):
                    raise FixtureError("stale, forged or unbound parent release")
                from buffer_controller import validate_release, original_child_identity
                child_marker = json.loads((root / "child.ready.json").read_bytes())
                expected_job, expected_started = original_child_identity(root.parent, child_marker, spec)
                validate_release(root.parent, release, marker, spec,
                                 expected_child_job=expected_job, expected_child_started=expected_started,
                                 expected_child_marker=child_marker)
                write_new(root / "parent.resumed.json", dict(marker_sha256=sha_value(marker),
                          nonce=spec["nonce"], job_id=event["job_id"],
                          observed=time.perf_counter()))
                return
            time.sleep(.005)
        raise FixtureError(f"{phase} timing barrier expired; target witness failed")


def timing_worker_entry(slot, gpu, settings, commands, results, hints, control,
                        incarnation, fault, fired, lock):
    from stage_worker import worker_main
    context = json.loads(os.environ[SPEC_ENV])
    validate_spec(context["spec"])
    if settings.get("record_resources", False):
        raise FixtureError("v1 binds original terminal bytes with frozen resource snapshots disabled")
    if fault.get("kind", "none") != "none":
        raise FixtureError("timing fixture cannot be combined with a second hidden fault")
    sender = TimingFramedSender(results, control, slot, incarnation, fault, fired, lock,
                               record_resources=settings.get("record_resources", False),
                               fixture_context=context)
    worker_main(slot, gpu, "authority", settings, CommandReceiver(commands), sender,
                HintReceiver(hints))


def timing_owner_entry(config, manifest, out, epoch, control, publication,
                       accepted, origin, initials_hint):
    from resilience_owner import owner_main
    import resilience_transport
    spec = validate_spec(config["timing_fixture"])
    if config["settings"]["source_commit"] != NN_COMMIT:
        raise FixtureError("runtime C/U source tag must remain imported NN4f")
    if config.get("fault", {}).get("kind", "none") != "none":
        raise FixtureError("the only injected fault is the controller's actual SIGKILL")
    root = Path(out) / "timing_fixture"
    if not root.is_dir():
        raise FixtureError("controller must initialize unique marker root before Owner")
    os.environ[SPEC_ENV] = json.dumps(dict(root=str(root.resolve()), spec=spec,
                                         owner_epoch=epoch), ensure_ascii=False)
    resilience_transport.worker_entry = timing_worker_entry
    owner_main(config, manifest, out, epoch, control, publication, accepted, origin, initials_hint)


def make_controller(config, out):
    from buffer_controller import BufferFixtureController
    return BufferFixtureController(config, out)

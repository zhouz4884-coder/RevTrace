"""External fail-stop controller; original Owner decides receipt and eligibility."""
from __future__ import annotations

import json
import os
from pathlib import Path
import signal
import time

from buffer_fixture import (FixtureError, canonical, sha_value, validate_spec,
                            validate_marker, write_new)
from resilience_transport import start_ticks
from resilience_inbound import semantic_fingerprint


def need(condition, message):
    if not condition:
        raise FixtureError(message)


def cut_sha(state):
    from feedback_contract import FeedbackCut
    return FeedbackCut(state).sha256


def process_state(pid):
    return (Path("/proc") / str(pid) / "stat").read_text().rsplit(")", 1)[1].split()[0]


class JsonlTail:
    """Incremental reader: a partly written last line is never evidence."""
    def __init__(self, path):
        self.path = Path(path)
        self.offset = 0
        self.pending = b""
        self.line = 0

    def poll(self):
        if not self.path.exists():
            return []
        need(self.path.stat().st_size >= self.offset, "raw log truncated while fixture was active")
        with self.path.open("rb") as stream:
            stream.seek(self.offset)
            chunk = stream.read()
            self.offset = stream.tell()
        raw = self.pending + chunk
        pieces = raw.split(b"\n")
        self.pending = pieces.pop()
        need(len(self.pending) <= 32 * 1024 * 1024, "unbounded partial raw JSONL row")
        rows = []
        for line in pieces:
            self.line += 1
            need(bool(line), "empty original JSONL row")
            rows.append((self.line, json.loads(line)))
        return rows


def row_reference(name, line, row):
    return dict(file=name, line=line, sha256=sha_value(row))


def read_reference(out, ref):
    allowed = {"owner_e0/owner_events.jsonl", "owner_e0/policy_audit.jsonl"}
    need(ref.get("file") in allowed and type(ref.get("line")) is int and ref["line"] > 0,
         "release has an arbitrary or invalid native evidence path")
    path = Path(out) / ref["file"]
    with path.open("rb") as stream:
        for number, line in enumerate(stream, 1):
            if number == ref["line"]:
                need(line.endswith(b"\n"), "release references incomplete raw row")
                row = json.loads(line)
                need(sha_value(row) == ref.get("sha256"), "release raw evidence bytes changed")
                return row
    raise FixtureError("release references a missing native evidence row")


def validate_fence(rows, child_job, child_started):
    """Validate original physical closure and original accepted-result survival."""
    loss, death, sealed, replacement = (rows[k] for k in ("loss", "death", "sealed", "replacement"))
    slot = child_job["worker"]
    incarnation = child_job["worker_incarnation"]
    need(loss.get("kind") == "worker_lost", "no original policy worker-loss record")
    body = loss["body"]
    need(body.get("slot") == slot and body.get("incarnation") == incarnation,
         "fence belongs to a different physical incarnation")
    need(child_job["job_id"] in body.get("preserved_completed_jobs", []),
         "old completed buffer was not preserved by original worker_lost")
    need(child_job["job_id"] not in body.get("retired_live_jobs", []),
         "target was live work, not a completed buffer")
    need(body.get("physical_ownership_released") is True and
         body.get("input_obligations_changed") is False, "loss altered input obligations")
    need(death.get("kind") == "worker_death_confirmed", "missing original death confirmation")
    proof = death["proof"]
    need(proof == body.get("death_proof"), "policy and Owner death proof disagree")
    need(proof.get("slot") == slot and proof.get("incarnation") == incarnation,
         "death proof slot/incarnation changed")
    need(proof.get("pid") == child_started["pid"] and
         proof.get("start_ticks") == child_started["start_ticks"], "death proof PID identity changed")
    need(proof.get("confirmed_exit") is True and proof.get("confirmed_dead") is True and
         type(proof.get("exitcode")) is int and proof["exitcode"] == -9,
         "producer did not actually fail-stop")
    need(proof.get("result_channel_closed") is True and
         proof.get("control_channel_closed") is True and
         proof.get("partial_frame_thread_blocked") is False, "readers not joined/closed")
    cuda = proof.get("cuda_release", {})
    need(cuda.get("gpu_context_released") is True and cuda.get("old_pid") == proof["pid"] and
         cuda.get("gpu") == child_started["gpu"] and
         type(cuda.get("memory_used_MiB")) in (int, float) and cuda["memory_used_MiB"] < 128,
         "no actual producer CUDA release")
    need(sealed.get("kind") == "old_channel_validated_before_incarnation_fence" and
         sealed.get("slot") == slot and sealed.get("incarnation") == incarnation,
         "no original sealed channel barrier")
    drain = sealed.get("drain", {})
    need(drain.get("closure_before_incarnation_fence") is True and
         drain.get("new_authority_granted_by_helper") is False and
         drain.get("other_channels_reordered") is False, "sealed channel semantics changed")
    need(replacement.get("kind") == "worker_started" and replacement.get("slot") == slot and
         replacement.get("incarnation") == incarnation + 1 and
         replacement.get("pid") != proof["pid"], "old incarnation not replaced/fenced")
    clocks = [proof["requested_perf"], proof["confirmed_perf"], cuda["observed_perf"],
              sealed["observed"], loss["observed"], death["observed"], replacement["observed"]]
    need(all(type(t) in (int, float) for t in clocks) and clocks == sorted(clocks),
         "original OS/CUDA/channel/fence clocks are out of order")
    return dict(slot=slot, incarnation=incarnation, job_id=child_job["job_id"],
                confirmed_perf=proof["confirmed_perf"], cuda_release_perf=cuda["observed_perf"],
                fence_observed_perf=loss["observed"], replacement_started_perf=replacement["observed"])


def original_child_identity(out, child_marker, spec):
    """Read the expected child identity from original logs, never the release."""
    root = Path(out) / "owner_e0"
    def matching(name, predicate):
        selected = []
        with (root / name).open("rb") as stream:
            for raw in stream:
                if not raw.endswith(b"\n"):
                    break
                row = json.loads(raw)
                if predicate(row): selected.append(row)
        need(len(selected) == 1, "original child identity missing or duplicated: " + name)
        return selected[0]
    dispatch = matching("dispatch.jsonl", lambda row: row["job"]["job_id"] == child_marker.get("job_id"))
    job = dispatch["job"]
    started = matching("owner_events.jsonl", lambda row:
                       row.get("kind") == "worker_started" and
                       (row.get("slot"), row.get("incarnation")) ==
                       (job["worker"], job["worker_incarnation"]))
    completed = matching("worker_results.jsonl", lambda row:
                         row["event"].get("kind") == "completed" and
                         row["event"].get("job_id") == job["job_id"])["event"]
    validate_marker(child_marker, completed, job, started, spec, "child")
    return job, started


def validate_release(out, release, parent_marker, spec, *, expected_child_job,
                     expected_child_started, expected_child_marker):
    need(release.get("nonce") == spec["nonce"] and
         release.get("experiment_id") == spec["experiment_id"] and
         release.get("parent_marker_sha256") == sha_value(parent_marker) and
         release.get("fence_checked") is True, "unbound or forged parent release")
    need(canonical(release.get("child_job")) == canonical(expected_child_job) and
         canonical(release.get("child_started")) == canonical(expected_child_started),
         "release child job/physical identity differs from original bound child")
    need(release.get("child_marker_sha256") == sha_value(expected_child_marker),
         "release belongs to a different original child marker")
    refs = release.get("native_fence_refs", {})
    need(set(refs) == {"loss", "death", "sealed", "replacement"}, "release lacks native fence evidence")
    rows = {key: read_reference(out, ref) for key, ref in refs.items()}
    result = validate_fence(rows, expected_child_job, expected_child_started)
    need(release["observed"] >= result["replacement_started_perf"], "release preceded original fence")
    return result


def validate_buffer_binding(parent_marker, child_marker, parent_event, child_event,
                            parent_job, child_job, started, publication, spec):
    """Both raw events plus the original post-admission view are required."""
    validate_marker(parent_marker, parent_event, parent_job,
                    started[(parent_job["worker"], parent_job["worker_incarnation"])], spec, "parent")
    validate_marker(child_marker, child_event, child_job,
                    started[(child_job["worker"], child_job["worker_incarnation"])], spec, "child")
    need(parent_job["worker"] != child_job["worker"], "parent and child cannot share a live slot")
    need(child_job.get("started_on_canonical") is False and
         child_job.get("promoted_to_canonical") is False, "target was not a buffered conditional job")
    predicted = parent_event["projection"]["end"]
    need(canonical(child_job["start"]) == canonical(predicted) == canonical(child_event["start"]),
         "child did not execute the complete real parent prediction")
    need(parent_job["end"] == spec["parent_end"] and child_job["end"] == spec["child_end"],
         "changed frozen actual cadence/target")
    record = child_event["record"]
    need(record.get("role") == "authority" and record.get("candidate_handoff") is False and
         record.get("stage_execution") == "original_full_infer" and
         record.get("start_state") == cut_sha(child_job["start"]) and
         record.get("end_state") == cut_sha(child_event["end"]), "not an original complete C/U result")
    need(publication.get("bound_owner_epoch") == 0, "buffer view belongs to another Owner")
    event = publication["event"]
    need(event.get("kind") == "private" and event.get("source_id") == spec["source_id"] and
         event.get("canonical_sha") != cut_sha(child_job["start"]),
         "post-admission view already had the child's input as Canonical")
    steps = [s for s in event.get("steps", []) if s.get("job_id") == child_job["job_id"]]
    need(len(steps) == 1, "original accepted full node missing or duplicated")
    step = steps[0]
    need(step.get("kind") == "actual_original_full_conditional_closed_node" and
         step.get("actual_full_C_U_completed") is True and
         canonical(step["start"]) == canonical(child_job["start"]) and
         canonical(step["end"]) == canonical(child_event["end"]), "not an Owner registered complete buffer")
    need(publication["received_perf"] >= child_marker["observed"] or
         publication["received_perf"] >= child_event.get("sent_perf", 0),
         "publication clock predates actual child completion")
    return True


class BufferFixtureController:
    """Implements the resident Supervisor observer API; no independent service."""
    def __init__(self, config, out, *, signal_sender=None, ticks_reader=None, state_reader=None, clock=None):
        self.config = config
        self.spec = validate_spec(config["timing_fixture"])
        self.out = Path(out)
        self.root = self.out / "timing_fixture"
        self.clock = clock or time.perf_counter
        self.signal_sender = signal_sender or os.kill
        self.ticks_reader = ticks_reader or start_ticks
        self.state_reader = state_reader or process_state
        self.state = "not_started"
        self.jobs, self.started, self.events, self.views = {}, {}, {}, {}
        self.native = {}
        self.refs = {}
        self.markers = {}
        self.kill_perf = None
        self.log = None

    def note(self, kind, **body):
        row = dict(kind=kind, observed=self.clock(), **body)
        self.log.write(canonical(row) + b"\n")
        self.log.flush()
        os.fsync(self.log.fileno())
        return row

    def start(self):
        need(self.state == "not_started", "controller start repeated")
        self.root.mkdir(exist_ok=False)
        self.log = (self.root / "controller.jsonl").open("xb")
        self.begin = self.clock()
        self.tails = {name: JsonlTail(self.out / name) for name in (
            "owner_e0/dispatch.jsonl", "owner_e0/worker_results.jsonl",
            "owner_e0/owner_events.jsonl", "owner_e0/policy_audit.jsonl", "publications.jsonl")}
        write_new(self.root / "SPEC.json", self.spec)
        if self.config.get("execution_dependencies"):
            fixture = next(dep for dep in self.config["execution_dependencies"]
                           if Path(dep["source_root"]).resolve() == Path(__file__).resolve().parent)
            config_raw = (self.out / "CONFIG.json").read_bytes()
            environment_raw = (self.out / "ENVIRONMENT.json").read_bytes()
            import hashlib
            write_new(self.out / "BUFFER_FIXTURE_RUN_RECORD.json", dict(
                experiment_id=self.spec["experiment_id"], code_commit=fixture["source_commit"],
                fixture_source_manifest_sha256=fixture["source_manifest_sha256"],
                imported_NN_source_commit=self.spec["base_nn_commit"],
                imported_NN_manifest_sha256=self.spec["base_manifest_sha256"],
                execution_dependencies=self.config["execution_dependencies"],
                frozen_config=str(self.out / "CONFIG.json"), frozen_config_sha256=hashlib.sha256(config_raw).hexdigest(),
                environment_record=str(self.out / "ENVIRONMENT.json"),
                environment_record_sha256=hashlib.sha256(environment_raw).hexdigest(),
                raw_result_location=str(self.out), aggregate_summary_location=str(self.out / "SUMMARY.json"),
                gate_decision_location=str(self.out / "BUFFER_WITNESS_GATE.json"),
                scope="fixture + resident Supervisor + imported NN4f; controlled timing, not natural execution"))
        self.note("controller_started", experiment_id=self.spec["experiment_id"],
                  nonce=self.spec["nonce"], base_nn_commit=self.spec["base_nn_commit"],
                  scope="controlled timing fixture; not natural prevalence or performance")
        self.state = "waiting_for_buffer"

    def _collect(self):
        for name, tail in self.tails.items():
            for line, row in tail.poll():
                if name.endswith("dispatch.jsonl"):
                    job = row["job"]
                    if (job["source_id"] == self.spec["source_id"] and
                            job["start"]["frontier"] in (self.spec["parent_start"], self.spec["parent_end"]) and
                            job["dispatch_epoch"] == 0):
                        self.jobs[job["job_id"]] = job
                elif name.endswith("worker_results.jsonl"):
                    event = row["event"]
                    if (event.get("source_id") == self.spec["source_id"] and
                            event.get("kind") in ("asr_early", "completed")):
                        boundary = event.get("start_state", event.get("start", {})).get("frontier")
                        if boundary in (self.spec["parent_start"], self.spec["parent_end"]):
                            self.events[(event["job_id"], event["kind"])] = event
                elif name == "publications.jsonl":
                    event = row["event"]
                    if event.get("source_id") == self.spec["source_id"]:
                        for step in event.get("steps", []):
                            if (step.get("kind") == "actual_original_full_conditional_closed_node" and
                                    step["start"]["frontier"] == self.spec["parent_end"]):
                                self.views[step["job_id"]] = row
                elif name.endswith("owner_events.jsonl"):
                    kind = row["kind"]
                    if kind == "worker_started":
                        self.started[(row["slot"], row["incarnation"])] = row
                    if self.markers.get("child"):
                        child = self.markers["child"]
                        match = row.get("slot", row.get("proof", {}).get("slot")) == child["slot"]
                        inc = row.get("incarnation", row.get("proof", {}).get("incarnation"))
                        label = ("death" if kind == "worker_death_confirmed" and inc == child["incarnation"] else
                                 "sealed" if kind == "old_channel_validated_before_incarnation_fence" and inc == child["incarnation"] else
                                 "replacement" if kind == "worker_started" and inc == child["incarnation"] + 1 else None)
                        if match and label:
                            self.native[label] = row
                            self.refs[label] = row_reference(name, line, row)
                elif name.endswith("policy_audit.jsonl") and row.get("kind") == "worker_lost":
                    if self.markers.get("child"):
                        child = self.markers["child"]
                        if (row["body"].get("slot"), row["body"].get("incarnation")) == (child["slot"], child["incarnation"]):
                            self.native["loss"] = row
                            self.refs["loss"] = row_reference(name, line, row)

    def poll(self):
        need(self.state != "not_started", "controller not started")
        for phase in ("parent", "child"):
            path = self.root / f"{phase}.ready.json"
            if phase not in self.markers and path.exists():
                marker = json.loads(path.read_bytes())
                need(marker.get("nonce") == self.spec["nonce"] and
                     marker.get("experiment_id") == self.spec["experiment_id"], "foreign/stale barrier marker")
                self.markers[phase] = marker
        self._collect()
        now = self.clock()
        if self.state == "released":
            return
        if "parent" in self.markers:
            need(now - self.markers["parent"]["observed"] < self.spec["barrier_timeout_seconds"],
                 "controlled parent barrier did not complete before its frozen deadline")
        else:
            need(now - self.begin < self.spec["startup_timeout_seconds"], "preselected neural timing site not reached")
        if self.state == "waiting_for_buffer" and set(self.markers) == {"parent", "child"}:
            parent, child = self.markers["parent"], self.markers["child"]
            pjob, cjob = self.jobs.get(parent["job_id"]), self.jobs.get(child["job_id"])
            pe = self.events.get((parent["job_id"], "asr_early"))
            ce = self.events.get((child["job_id"], "completed"))
            view = self.views.get(child["job_id"])
            if not (pjob and cjob and pe and ce and view):
                return
            validate_buffer_binding(parent, child, pe, ce, pjob, cjob, self.started, view, self.spec)
            need((parent["job_id"], "completed") not in self.events,
                 "parent already completed before the controlled producer fault")
            child_started = self.started[(cjob["worker"], cjob["worker_incarnation"])]
            need(self.ticks_reader(child["pid"]) == child["start_ticks"], "PID identity changed before external SIGKILL")
            old_state = self.state_reader(child["pid"])
            need(old_state not in ("Z", "X"), "producer had already exited before fixture SIGKILL")
            need(hasattr(signal, "SIGKILL"), "physical producer fail-stop fixture requires Linux SIGKILL")
            self.note("owner_buffer_registered_before_kill", parent_marker=parent, child_marker=child,
                      child_job=cjob, publication_id=view["event"]["publication_id"],
                      publication_semantic_sha256=sha_value(view["event"]),
                      child_event_semantic_sha256=semantic_fingerprint(ce))
            self.kill_perf = self.clock()
            self.note("worker_sigkill", site="owner_received_full_buffer_before_parent_confirmation",
                      job_id=cjob["job_id"], slot=cjob["worker"], incarnation=cjob["worker_incarnation"],
                      pid=child["pid"], start_ticks=child["start_ticks"],
                      observed_process_state=old_state, requested_perf=self.kill_perf)
            self.signal_sender(child["pid"], signal.SIGKILL)
            self.state = "waiting_for_fence"
        if self.state == "waiting_for_fence" and set(self.native) == {"loss", "death", "sealed", "replacement"}:
            child = self.markers["child"]
            cjob = self.jobs[child["job_id"]]
            child_started = self.started[(cjob["worker"], cjob["worker_incarnation"])]
            fence = validate_fence(self.native, cjob, child_started)
            need(self.kill_perf <= fence["confirmed_perf"], "original death preceded fixture SIGKILL")
            release = dict(nonce=self.spec["nonce"], experiment_id=self.spec["experiment_id"],
                           parent_marker_sha256=sha_value(self.markers["parent"]),
                           child_marker_sha256=sha_value(child),
                           fence_checked=True, observed=self.clock(),
                           native_fence_refs=self.refs, child_job=cjob, child_started=child_started)
            validate_release(self.out, release, self.markers["parent"], self.spec,
                             expected_child_job=cjob, expected_child_started=child_started,
                             expected_child_marker=child)
            write_new(self.root / "parent.release.json", release)
            self.note("parent_release_after_original_fence", fence=fence,
                      release_sha256=sha_value(release))
            self.state = "released"

    def finish(self):
        self.poll()
        need(self.state == "released", "required buffer/physical fault/fence barrier not exercised")
        resumed = json.loads((self.root / "parent.resumed.json").read_bytes())
        need(resumed.get("marker_sha256") == sha_value(self.markers["parent"]) and
             resumed.get("nonce") == self.spec["nonce"], "no bound actual parent callback continuation")
        self.note("controller_complete", state=self.state)
        write_new(self.out / "TIMING_FIXTURE_CONTROL_GATE.json", dict(
            status="PASS_CONTROLLED_BUFFER_RECEIPT_KILL_FENCE_PARENT_RELEASE", new_neural_results_claimed=False,
            final_witness_requires_independent_audit=True, experiment_id=self.spec["experiment_id"]))

    def close(self):
        # On error never release a parent without the original fence. The
        # resident Supervisor owns group cleanup through its original finally.
        if self.log and not self.log.closed:
            self.log.close()

"""Development CPU controls. No neural execution or real fail-stop claim."""
import copy
import json
import os
import multiprocessing as mp
import queue
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

from buffer_fixture import (FixtureError, FramedSender, TimingFramedSender, bound_marker,
                            canonical, sha_value, validate_marker, validate_spec, write_new)
from buffer_controller import (BufferFixtureController, JsonlTail, cut_sha, validate_buffer_binding,
                               validate_fence, validate_release, original_child_identity)
from fixture_paths import frozen_path, validate_live_under
from fixture_watchdog import wait_hard, validate_registered_child, WatchdogError
from build_buffer_plan import specification, build, TARGET_SOURCE
from resilience_channel_close import drain_closed_worker_channel, ClosedChannelError

DEVELOPMENT_CPU_CHILD_TERMINATIONS = 0


def cut(frontier, text="", context=""):
    return dict(audio_segments=[], tokens=[[[1, 2, 3, 4]] * 4, [[frontier]] * 4],
                context=dict(text=context, prefix_token_ids=[9], token_ids=[9]),
                last_attend_frame=frontier // 100, detected_language="zh",
                initial_tokens=[[1, 2, 3, 4]], initial_token_length=4, sot_index=0,
                decoder_type="beam", contract=dict(source_sha="frozen-cpu-source"),
                frontier=frontier, transcript=text)


def append(path, row):
    with Path(path).open("ab") as stream:
        stream.write(canonical(row) + b"\n")


def scenario(root):
    spec = specification("development-cpu-fixture", True)
    start, predicted, end = cut(16000), cut(24000, "predicted"), cut(32000, "chosen")
    pj = dict(job_id="e0-j000000001", worker="full0", source_id=TARGET_SOURCE,
              start=start, end=24000, dispatch_epoch=0, worker_incarnation=0,
              started_on_canonical=True, promoted_to_canonical=False,
              birth_canonical_sha=cut_sha(start), dispatched_perf=10.0)
    cj = dict(job_id="e0-j000000002", worker="full1", source_id=TARGET_SOURCE,
              start=predicted, end=32000, dispatch_epoch=0, worker_incarnation=0,
              started_on_canonical=False, promoted_to_canonical=False,
              birth_canonical_sha=cut_sha(start), dispatched_perf=15.0)
    pe = dict(kind="asr_early", worker="full0", job_id=pj["job_id"], source_id=TARGET_SOURCE,
              worker_incarnation=0, dispatch_epoch=0, start_state=start, end_frontier=24000,
              projection=dict(end=predicted), sent_perf=19.0)
    ce = dict(kind="completed", worker="full1", job_id=cj["job_id"], source_id=TARGET_SOURCE,
              worker_incarnation=0, dispatch_epoch=0, start=predicted, end=end, sent_perf=20.0,
              record=dict(role="authority", candidate_handoff=False, stage_execution="original_full_infer",
                          start_state=cut_sha(predicted), end_state=cut_sha(end)))
    ps = dict(kind="worker_started", slot="full0", incarnation=0, pid=123, start_ticks=111,
              gpu=0, observed=1.0, owner_epoch=0)
    cs = dict(kind="worker_started", slot="full1", incarnation=0, pid=124, start_ticks=222,
              gpu=1, observed=1.1, owner_epoch=0)
    pm = bound_marker(pe, spec=spec, phase="parent", slot="full0", incarnation=0,
                      owner_epoch=0, pid=123, ticks=111)
    cm = bound_marker(ce, spec=spec, phase="child", slot="full1", incarnation=0,
                      owner_epoch=0, pid=124, ticks=222)
    pm["observed"], cm["observed"] = 19.5, 20.5
    pub = dict(bound_owner_epoch=0, received_perf=21.0,
               event=dict(kind="private", source_id=TARGET_SOURCE, canonical_sha=cut_sha(start),
                          publication_id=3, steps=[dict(job_id=cj["job_id"], start=predicted, end=end,
                          kind="actual_original_full_conditional_closed_node", actual_full_C_U_completed=True)]))
    proof = dict(slot="full1", incarnation=0, pid=124, start_ticks=222, exitcode=-9,
                 confirmed_exit=True, confirmed_dead=True, result_channel_closed=True,
                 control_channel_closed=True, partial_frame_thread_blocked=False,
                 requested_perf=25.0, confirmed_perf=26.0,
                 cuda_release=dict(gpu=1, old_pid=124, gpu_context_released=True,
                                   observed_perf=27.0, memory_used_MiB=0.0))
    sealed = dict(kind="old_channel_validated_before_incarnation_fence", slot="full1", incarnation=0,
                  observed=28.0, drain=dict(closure_before_incarnation_fence=True,
                  new_authority_granted_by_helper=False, other_channels_reordered=False))
    loss = dict(kind="worker_lost", observed=29.0, body=dict(slot="full1", incarnation=0,
                death_proof=proof, preserved_completed_jobs=[cj["job_id"]], retired_live_jobs=[],
                physical_ownership_released=True, input_obligations_changed=False))
    death = dict(kind="worker_death_confirmed", observed=30.0, proof=proof)
    replacement = dict(kind="worker_started", slot="full1", incarnation=1, pid=125,
                       start_ticks=333, gpu=1, observed=31.0)
    return dict(spec=spec, pj=pj, cj=cj, pe=pe, ce=ce, pm=pm, cm=cm, pub=pub,
                started={("full0", 0): ps, ("full1", 0): cs},
                native=dict(loss=loss, death=death, sealed=sealed, replacement=replacement))


class Connection:
    def __init__(self):
        self.frames = []
    def send_bytes(self, value):
        self.frames.append(bytes(value))


class TimingControls(unittest.TestCase):
    def setUp(self):
        self.scratch = Path(os.environ["REVTRACE_FIXTURE_TEST_ROOT"]).resolve()
        self.temp = tempfile.TemporaryDirectory(dir=self.scratch)
        self.root = Path(self.temp.name)
        self.data = scenario(self.root)
        self.controllers = []

    def tearDown(self):
        for controller in self.controllers:
            controller.close()
        if not self.root.resolve().is_relative_to(self.scratch):
            raise RuntimeError("test cleanup escaped the declared fixture scratch root")
        self.temp.cleanup()

    def test_original_header_and_payload_unchanged_before_barrier_timeout(self):
        spec = copy.deepcopy(self.data["spec"])
        spec["barrier_timeout_seconds"] = .02
        event = copy.deepcopy(self.data["ce"])
        original_event = copy.deepcopy(event)
        a, b = Connection(), Connection()
        FramedSender(a, slot="full1", incarnation=0).put(event)
        wrapped = TimingFramedSender(b, slot="full1", incarnation=0,
                    fixture_context=dict(root=str(self.root), spec=spec, owner_epoch=0))
        with self.assertRaisesRegex(FixtureError, "barrier expired"):
            wrapped.put(event)
        self.assertEqual(a.frames, b.frames)
        self.assertEqual(event, original_event)
        self.assertTrue((self.root / "child.ready.json").exists())

    def test_non_target_event_has_no_extra_bytes_or_marker(self):
        a, b = Connection(), Connection()
        event = dict(kind="ready", worker="full0", source_id="not-a-request")
        FramedSender(a, slot="full0", incarnation=0).put(event)
        TimingFramedSender(b, slot="full0", incarnation=0, fixture_context=dict(
            root=str(self.root), spec=self.data["spec"], owner_epoch=0)).put(event)
        self.assertEqual(a.frames, b.frames)
        self.assertFalse(list(self.root.iterdir()))

    def test_immutable_marker_creation_refuses_overwrite(self):
        path = self.root / "marker.json"
        write_new(path, {"first": True})
        with self.assertRaises(FileExistsError): write_new(path, {"second": True})
        self.assertEqual(json.loads(path.read_bytes()), {"first": True})

    def test_same_frontier_new_uid_recomputation_is_not_held_again(self):
        d = self.data
        write_new(self.root / "child.ready.json", d["cm"])
        event = copy.deepcopy(d["ce"])
        event["job_id"] = "e0-j000000003"
        event["start"]["context"]["text"] = "actual corrected input"
        a, b = Connection(), Connection()
        FramedSender(a, slot="full1", incarnation=1).put(event)
        TimingFramedSender(b, slot="full1", incarnation=1, fixture_context=dict(
            root=str(self.root), spec=d["spec"], owner_epoch=0)).put(event)
        self.assertEqual(a.frames, b.frames)
        self.assertEqual(json.loads((self.root / "child.ready.json").read_bytes()), d["cm"])
        with self.assertRaisesRegex(FixtureError, "repeated"):
            TimingFramedSender(Connection(), slot="full1", incarnation=0, fixture_context=dict(
                root=str(self.root), spec=d["spec"], owner_epoch=0)).put(d["ce"])

    def test_spawn_uses_actual_timing_entry_and_original_full_frame(self):
        from cpu_spawn_probe import probe
        context = dict(root=str(self.root), spec=copy.deepcopy(self.data["spec"]), owner_epoch=0)
        context["spec"]["barrier_timeout_seconds"] = .03
        ctx = mp.get_context("spawn")
        rx, tx = ctx.Pipe(duplex=False)
        report = ctx.Queue()
        child = ctx.Process(target=probe, args=(context, self.data["ce"], tx, report))
        child.start()
        tx.close()
        frames = [rx.recv_bytes(), rx.recv_bytes()]
        child.join(10)
        self.assertEqual(child.exitcode, 0)
        messages = [report.get(timeout=5), report.get(timeout=5)]
        self.assertEqual(messages[0]["value"], "TimingFramedSender")
        self.assertEqual(messages[1]["kind"], "expected_cpu_timeout")
        expected = Connection()
        FramedSender(expected, slot="full1", incarnation=0).put(self.data["ce"])
        self.assertEqual(frames, expected.frames)
        self.assertTrue((self.root / "child.ready.json").exists())
        rx.close(); report.close(); report.join_thread()

    def test_owner_entry_installs_only_worker_target_and_preserves_config(self):
        import resilience_owner
        import resilience_transport
        from buffer_fixture import timing_owner_entry, timing_worker_entry, SPEC_ENV, NN_COMMIT
        root = self.root / "timing_fixture"
        root.mkdir()
        config = dict(timing_fixture=self.data["spec"], settings=dict(source_commit=NN_COMMIT), fault=dict(kind="none"))
        before = copy.deepcopy(config)
        captured = []
        def owner(*args):
            captured.append(resilience_transport.worker_entry)
            self.assertEqual(json.loads(os.environ[SPEC_ENV])["root"], str(root.resolve()))
        with patch.object(resilience_owner, "owner_main", owner), patch.object(
                resilience_transport, "worker_entry", resilience_transport.worker_entry), patch.dict(os.environ):
            timing_owner_entry(config, "unused-cpu-manifest", str(self.root), 0, None, None, None, None, None)
        self.assertEqual(captured, [timing_worker_entry])
        self.assertEqual(before, config)

    def test_frozen_target_and_full_state_hash_cannot_change(self):
        for key, value in (("parent_end", 24001), ("historical_parent_actual_sha", "0" * 64),
                           ("base_nn_commit", "0" * 40), ("nonce", "old")):
            spec = copy.deepcopy(self.data["spec"])
            spec[key] = value
            with self.assertRaises(FixtureError):
                validate_spec(spec)

    def test_marker_forgery_needs_real_job_channel_and_payload(self):
        d = self.data
        for key, value in (("nonce", "stale"), ("pid", 999), ("start_ticks", 999),
                           ("event_semantic_sha256", "0" * 64), ("incarnation", 7),
                           ("sent_complete_before_marker", False)):
            marker = copy.deepcopy(d["cm"])
            marker[key] = value
            with self.assertRaises(FixtureError):
                validate_marker(marker, d["ce"], d["cj"], d["started"][("full1", 0)], d["spec"], "child")

    def test_typed_asr_node_is_not_complete_owner_buffer(self):
        d = self.data
        pub = copy.deepcopy(d["pub"])
        pub["event"]["steps"][0]["kind"] = "typed_ASR_projection"
        with self.assertRaises(FixtureError):
            validate_buffer_binding(d["pm"], d["cm"], d["pe"], d["ce"], d["pj"], d["cj"],
                                    d["started"], pub, d["spec"])

    def test_same_text_different_context_is_not_complete_input_match(self):
        d = self.data
        child = copy.deepcopy(d["cj"])
        child["start"]["context"]["text"] = "different hidden model context"
        with self.assertRaises(FixtureError):
            validate_buffer_binding(d["pm"], d["cm"], d["pe"], d["ce"], d["pj"], child,
                                    d["started"], d["pub"], d["spec"])

    def test_os_cuda_channel_and_preserved_uid_all_required(self):
        d = self.data
        validate_fence(d["native"], d["cj"], d["started"][("full1", 0)])
        for change in ("cuda", "live", "unjoined", "replacement", "clock", "not_sigkill"):
            rows = copy.deepcopy(d["native"])
            if change == "cuda": rows["death"]["proof"]["cuda_release"]["gpu_context_released"] = False
            if change == "live": rows["loss"]["body"]["preserved_completed_jobs"] = []
            if change == "unjoined": rows["death"]["proof"]["partial_frame_thread_blocked"] = True
            if change == "replacement": rows["replacement"]["incarnation"] = 0
            if change == "clock": rows["sealed"]["observed"] = 24.0
            if change == "not_sigkill": rows["death"]["proof"]["exitcode"] = -15
            # deepcopy preserves the proof aliases in this synthetic scenario.
            with self.assertRaises(FixtureError):
                validate_fence(rows, d["cj"], d["started"][("full1", 0)])

    def test_forged_boolean_release_has_no_native_evidence(self):
        d = self.data
        release = dict(nonce=d["spec"]["nonce"], experiment_id=d["spec"]["experiment_id"],
                       parent_marker_sha256=sha_value(d["pm"]), fence_checked=True)
        with self.assertRaises(FixtureError):
            validate_release(self.root, release, d["pm"], d["spec"],
                             expected_child_job=d["cj"], expected_child_started=d["started"][("full1", 0)],
                             expected_child_marker=d["cm"])

    def test_legitimate_foreign_uid_fence_cannot_be_spliced_into_release(self):
        d = self.data
        for change in ("uid", "incarnation"):
            foreign_job = copy.deepcopy(d["cj"])
            foreign_start = copy.deepcopy(d["started"][("full1", 0)])
            rows = copy.deepcopy(d["native"])
            if change == "uid":
                foreign_job["job_id"] = "e0-j999999999"
                rows["loss"]["body"]["preserved_completed_jobs"] = [foreign_job["job_id"]]
            else:
                foreign_job["worker_incarnation"] = 7
                foreign_start["incarnation"] = 7
            release = dict(nonce=d["spec"]["nonce"], experiment_id=d["spec"]["experiment_id"],
                           parent_marker_sha256=sha_value(d["pm"]), child_marker_sha256=sha_value(d["cm"]),
                           fence_checked=True, observed=32., child_job=foreign_job, child_started=foreign_start,
                           native_fence_refs={k: k for k in rows})
            with patch("buffer_controller.read_reference", side_effect=lambda out, ref: rows[ref]):
                with self.assertRaisesRegex(FixtureError, "original bound child"):
                    validate_release(self.root, release, d["pm"], d["spec"],
                                     expected_child_job=d["cj"], expected_child_started=d["started"][("full1", 0)],
                                     expected_child_marker=d["cm"])

    def test_target_posix_path_rejects_traversal_and_lookalike_prefix(self):
        base = "/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9/results"
        for value in (base + "/../../../../tmp/escaped", base + "-wrong/a",
                      base + "/./aliased", base + "//noncanonical", base + "/a/../b"):
            with self.assertRaises(ValueError): frozen_path(value)

    def test_live_path_rejects_wrong_frozen_out_and_symlink(self):
        disk = self.root / "disk"
        (disk / "results").mkdir(parents=True)
        raw = disk / "results" / "fixture"
        cfg = dict(cell_id="cell", frozen_raw_root=str(raw), raw_result_location=str(raw / "cells/cell"))
        self.assertEqual(validate_live_under(cfg, cfg["raw_result_location"], disk_root=disk), raw / "cells/cell")
        with self.assertRaises(ValueError): validate_live_under(cfg, raw / "other/cell", disk_root=disk)
        try:
            (disk / "results" / "aliased").symlink_to(self.root, target_is_directory=True)
        except OSError:
            # Windows sandbox may forbid creating links; exercise the exact
            # Path.is_symlink branch in that environment without bypassing it.
            with patch.object(Path, "is_symlink", lambda p: p == raw):
                with self.assertRaisesRegex(ValueError, "symlink"):
                    validate_live_under(cfg, cfg["raw_result_location"], disk_root=disk)
        else:
            cfg.update(frozen_raw_root=str(disk / "results/aliased"),
                       raw_result_location=str(disk / "results/aliased/cells/cell"))
            with self.assertRaisesRegex(ValueError, "symlink"):
                validate_live_under(cfg, cfg["raw_result_location"], disk_root=disk)

    def test_external_wall_clock_stops_owned_blocked_cpu_subprocess(self):
        global DEVELOPMENT_CPU_CHILD_TERMINATIONS
        ready = self.root / "blocked-cpu-ready"
        flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
        child = subprocess.Popen([sys.executable, "-c",
            "from pathlib import Path; import sys,time; Path(sys.argv[1]).write_text('ready'); time.sleep(30)",
            str(ready)], stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            creationflags=flags)
        try:
            deadline = time.monotonic() + 5
            while not ready.exists() and child.poll() is None and time.monotonic() < deadline:
                time.sleep(.01)
            self.assertTrue(ready.exists())
            def stop_owned_cpu():
                global DEVELOPMENT_CPU_CHILD_TERMINATIONS
                child.terminate()
                DEVELOPMENT_CPU_CHILD_TERMINATIONS += 1
                child.wait(timeout=5)
                return {"status": "PASS_DEVELOPMENT_OWNED_CPU_CHILD_TERMINATION"}
            state = wait_hard(child, .1, stop_owned_cpu)
            self.assertTrue(state["timed_out"])
            self.assertIsNotNone(child.poll())
            self.assertLess(state["elapsed_seconds"], 3)
            self.assertTrue(state["cleanup"]["status"].startswith("PASS_DEVELOPMENT"))
        finally:
            if child.poll() is None:
                child.terminate(); child.wait(timeout=5)

    def test_external_timeout_never_calls_failed_query_verified_cleanup(self):
        class Stuck:
            def poll(self): return None
        now = [0.]
        def clock():
            now[0] += .1
            return now[0]
        def blocked_query():
            raise TimeoutError("synthetic nvidia-smi timeout")
        result = wait_hard(Stuck(), .2, blocked_query, clock=clock, sleep=lambda delay: None)
        self.assertTrue(result["timed_out"])
        self.assertEqual(result["cleanup"]["status"], "FAIL_OWNED_CLEANUP_UNVERIFIED")

    def test_zero_exit_observed_after_hard_deadline_is_still_a_timeout(self):
        class OverdueZero:
            def poll(self): return 0
        stamps = iter((0., 901., 901.))
        calls = []
        state = wait_hard(OverdueZero(), 900., lambda: calls.append(True) or {"status": "cpu-cleanup"},
                          clock=lambda: next(stamps), sleep=lambda delay: None)
        self.assertTrue(state["timed_out"])
        self.assertEqual(calls, [True])

    def test_child_requires_live_watchdog_generation_and_exact_config(self):
        config = dict(cell_id="cpu-cell", timing_fixture=dict(nonce="cpu-nonce"))
        current = dict(pid=os.getpid(), start_ticks=123)
        parent = dict(pid=456, start_ticks=789)
        record = dict(child_pid=os.getpid(), child_start_ticks=123, watchdog_pid=456,
                      watchdog_start_ticks=789, cell_id="cpu-cell", nonce="cpu-nonce", config_sha256="abc")
        self.assertEqual(validate_registered_child(record, config, current, parent, config_sha256="abc"), record)
        for key, value in (("watchdog_start_ticks", 1), ("child_start_ticks", 1),
                           ("nonce", "old"), ("config_sha256", "changed")):
            changed = dict(record, **{key: value})
            with self.assertRaises(WatchdogError):
                validate_registered_child(changed, config, current, parent, config_sha256="abc")

    def test_both_cli_routes_refuse_arbitrary_out_before_source_or_neural_work(self):
        from run_buffer_fixture import run, execute_child
        base = "/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9/results/frozen-cpu-test"
        cfg = dict(cell_id="cell", frozen_raw_root=base, raw_result_location=base + "/cells/cell")
        path = self.root / "CONFIG.json"
        path.write_bytes(canonical(cfg))
        with patch("run_buffer_fixture.verify_dependency") as verify:
            with self.assertRaises(ValueError): run(path, Path("/tmp/escape"))
            with self.assertRaises(ValueError): execute_child(path, Path("/tmp/escape"), self.root)
            verify.assert_not_called()

    def test_closed_channel_requires_real_exit_and_joined_reader_contract(self):
        proof = dict(self.data["native"]["death"]["proof"])
        proof["result_channel_closed"] = False
        with self.assertRaises(ClosedChannelError):
            drain_closed_worker_channel(queue.Queue(), slot="full1", incarnation=0,
                                        death_proof=proof, on_message=lambda row: None)

    def test_original_closed_channel_drain_preserves_other_channel_fifo(self):
        d = self.data
        inbox = queue.Queue()
        other1 = dict(type="message", slot="full0", incarnation=0, payload={"x": 1})
        target = dict(type="message", slot="full1", incarnation=0, payload=d["ce"])
        other2 = dict(type="message", slot="full0", incarnation=0, payload={"x": 2})
        for row in (other1, target, other2): inbox.put(row)
        got = []
        result = drain_closed_worker_channel(inbox, slot="full1", incarnation=0,
                    death_proof=d["native"]["death"]["proof"], on_message=lambda row: got.append(row))
        self.assertEqual(got, [target])
        self.assertEqual([inbox.get_nowait(), inbox.get_nowait()], [other1, other2])
        self.assertTrue(result["closure_before_incarnation_fence"])

    def test_tail_never_accepts_a_partial_jsonl_row(self):
        p = self.root / "partial.jsonl"
        p.write_bytes(b'{"kind":"partial"')
        tail = JsonlTail(p)
        self.assertEqual(tail.poll(), [])
        with p.open("ab") as stream: stream.write(b'}\n')
        self.assertEqual(tail.poll(), [(1, {"kind": "partial"})])

    def test_marker_publication_fence_controller_order(self):
        d = self.data
        config = dict(timing_fixture=d["spec"])
        now, signals = [23.0], []
        controller = BufferFixtureController(config, self.root,
            signal_sender=lambda pid, sig: signals.append((pid, sig)),
            ticks_reader=lambda pid: 222, state_reader=lambda pid: "S", clock=lambda: now[0])
        self.controllers.append(controller)
        controller.start()
        owner = self.root / "owner_e0"
        owner.mkdir()
        append(owner / "dispatch.jsonl", dict(job=d["pj"]))
        append(owner / "dispatch.jsonl", dict(job=d["cj"]))
        append(owner / "worker_results.jsonl", dict(event=d["pe"]))
        append(owner / "worker_results.jsonl", dict(event=d["ce"]))
        for row in d["started"].values(): append(owner / "owner_events.jsonl", row)
        (owner / "policy_audit.jsonl").touch()
        (self.root / "publications.jsonl").touch()
        write_new(controller.root / "parent.ready.json", d["pm"])
        write_new(controller.root / "child.ready.json", d["cm"])
        controller.poll()
        self.assertEqual(signals, [])  # marker + raw result alone are insufficient
        append(self.root / "publications.jsonl", d["pub"])
        with patch.object(signal, "SIGKILL", 9, create=True): controller.poll()
        self.assertEqual(signals, [(124, 9)])
        self.assertFalse((controller.root / "parent.release.json").exists())
        for kind in ("sealed", "death", "replacement"):
            append(owner / "owner_events.jsonl", d["native"][kind])
        append(owner / "policy_audit.jsonl", d["native"]["loss"])
        now[0] = 32.0
        controller.poll()
        self.assertEqual(controller.state, "released")
        release = json.loads((controller.root / "parent.release.json").read_bytes())
        validate_release(self.root, release, d["pm"], d["spec"],
                         expected_child_job=d["cj"], expected_child_started=d["started"][("full1", 0)],
                         expected_child_marker=d["cm"])
        self.assertEqual(original_child_identity(self.root, d["cm"], d["spec"]),
                         (d["cj"], d["started"][("full1", 0)]))
        write_new(controller.root / "parent.resumed.json", dict(nonce=d["spec"]["nonce"],
                    marker_sha256=sha_value(d["pm"]), observed=32.1))
        controller.finish()
        controller.close()

    def test_fixed_four_trial_plan_rotation_and_optional_followup(self):
        template = dict(maximum_service_seconds=240,
                        settings=dict(sources=[dict(source_id=TARGET_SOURCE)], model_sources=[]))
        deps = {k: dict(source_commit=k) for k in ("base", "harness", "fixture")}
        raw = "/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9/results/revtrace/cpu-plan-not-run"
        a = build(template, deps, raw, followup=dict(source_id="fixed-next-request"))
        self.assertEqual(a, build(template, deps, raw, followup=dict(source_id="fixed-next-request")))
        self.assertEqual(len(a["cells"]), 4)
        self.assertEqual(sum(c["expect_match"] for c in a["cells"]), 2)
        self.assertEqual([c["primary_gpu"] for c in a["cells"]], [0, 0, 1, 1])
        self.assertEqual([c["expect_match"] for c in a["cells"][:2]],
                         list(reversed([c["expect_match"] for c in a["cells"][2:]])))
        for cell in a["cells"]:
            self.assertEqual(len(cell["config"]["request_order"]), 2 if cell["expect_match"] else 1)
            self.assertEqual(cell["config"]["maximum_service_seconds"], 240)
        with self.assertRaises(ValueError): build(template, deps, "/tmp/not-the-experiment-disk")


if __name__ == "__main__":
    unittest.main()

"""Adversarial CPU fixtures for the independent service retirement auditor."""
import ast
import copy
import hashlib
from pathlib import Path

import pytest

import retirement_audit as audit


def job(jid, sid, worker="p", role="proposal", batch=1):
    value = dict(job_id=jid, session_id=sid, source_id="arbitrary-source-"+str(sid), role=role,
        parent=0, prompt_tokens=[], chunk_id=0, end_window=1, contract_epoch=1,
        contract_digest="contract", runtime_digest="runtime-"+role, audio_start_sample=0,
        audio_end_sample=16000, prefix_audio_sha256="prefix", interval_audio_sha256="interval",
        branch_generation=0, audio_ready_perf=101.0, enqueue_perf=101.1)
    bid = f"{worker}:inc:{batch}"
    binding = {key:value[key] for key in ["job_id", "session_id", "role", "parent", "contract_epoch",
        "contract_digest", "runtime_digest", "audio_start_sample", "audio_end_sample", "interval_audio_sha256"]}
    binding.update(worker=worker, worker_incarnation="inc", batch_id=bid,
        input_identity=audit.service.sha({key:value.get(key) for key in audit.INPUT_KEYS}))
    value["_delivery"] = dict(worker=worker, incarnation="inc", batch_id=bid, binding=binding)
    return value


def full_result(value, terminal):
    result = dict(job_id=value["job_id"], runtime_digest=value["runtime_digest"], token_ids=[7, 9],
        state_tokens=[7, 9], text="full", generated_tokens=2, terminated_by_eos=True,
        hit_token_limit=False, started_perf=102.0, model_started_perf=103.0,
        completed_perf=terminal+.1)
    receipt = dict(binding=copy.deepcopy(value["_delivery"]["binding"]), terminal_perf=terminal,
        rendered_perf=terminal+.1, emitted_perf=terminal+.2, payload_sha256=audit.service.sha(result))
    return dict(result, _row_receipt=receipt, received_perf=terminal+.3)


def selected(jid, result):
    return dict(job_id=jid, Z_sha256=audit.service.tokens(result["token_ids"]),
        P_sha256=audit.service.tokens(result["state_tokens"]),
        text_sha256=hashlib.sha256(result["text"].encode()).hexdigest())


def cancel_message(value, rid="request-1"):
    message = dict(binding=copy.deepcopy(value["_delivery"]["binding"]), request_id=rid,
        reason="trusted-coverage", requested_perf=107.0, acknowledged_perf=108.0,
        emitted_perf=108.1, decoded_tokens=10)
    message["terminal_digest"] = audit.service.sha(dict(kind="row-cancelled-v1", **message))
    return message


def fixture():
    jobs = {value["job_id"]:value for value in [job("p0", 0), job("p1", 1), job("a0", 0, "a", "authority")]}
    results = {"p1":full_result(jobs["p1"], 111.0), "a0":full_result(jobs["a0"], 105.0)}
    message = cancel_message(jobs["p0"])
    receipt = dict(message=message, **message, received_perf=108.2, physical_worker_released=False)
    cancelled = [dict(job=copy.deepcopy(jobs["p0"]), cancellation=receipt)]
    accounting = []
    for worker, ids, lo, hi, drained in [("p", ["p0", "p1"], 103.0, 112.0, 112.5),
                                        ("a", ["a0"], 102.5, 105.1, 105.5)]:
        complete = {jid:results[jid]["_row_receipt"]["payload_sha256"] for jid in ids if jid in results}
        batch = dict(schema="row-cost-v1", batch_id=f"{worker}:inc:1", job_ids=ids,
            row_receipt_digests=complete, selected_output_digests=[selected(jid, results[jid]) for jid in complete],
            worker_started_perf=102.0, batch_drained_perf=drained,
            phases=[dict(started_perf=lo, completed_perf=hi, physical_batch_rows=len(ids),
                executed_job_ids=ids, fixed_layout_until_generation_return=True)])
        if worker == "p":
            batch.update(cancelled_rows=[copy.deepcopy(message)],
                cancelled_row_receipt_digests={"p0":message["terminal_digest"]},
                physical_release_basis="generation-return-and-CUDA-synchronize",
                masked_row_compute_charged_until_batch_drain=True)
        accounting.append(batch)
    request = dict(kind="cancel-request", job_id="p0", session_id=0, request_id="request-1",
        binding=copy.deepcopy(jobs["p0"]["_delivery"]["binding"]), reason="trusted-coverage",
        invalidation_kind="trusted-coverage", invalidated_perf=106.0, requested_perf=107.0,
        observed_perf=107.01, physical_worker_released=False, status="new-request")
    events = [dict(kind="commit", job_id="a0", session_id=0, audio_end_sample=16000,
                   installed=6.0, time=6.01, version=1), request,
              dict(kind="row-cancelled", job_id="p0", session_id=0, **receipt)]
    return dict(jobs=jobs, results=results, cancelled_records=cancelled, accounting=accounting,
        events=events, owner_start=100.0, dispatches={"p:inc:1":101.9, "a:inc:1":101.8},
        config=dict(physical_retirement=dict(policy="covered", watchdog_seconds=5.0)))


def complete_instead(data, terminal=106.2):
    data["results"]["p0"] = full_result(data["jobs"]["p0"], terminal)
    data["cancelled_records"] = []
    data["events"] = [event for event in data["events"] if event["kind"] != "row-cancelled"]
    batch = data["accounting"][0]
    batch.pop("cancelled_rows")
    batch.pop("cancelled_row_receipt_digests")
    batch["row_receipt_digests"]["p0"] = data["results"]["p0"]["_row_receipt"]["payload_sha256"]
    batch["selected_output_digests"].append(selected("p0", data["results"]["p0"]))


def test_cancel_terminal_does_not_release_physical_lease_or_masked_computation():
    summary, requests, batches = audit.audit_lifecycle(**fixture())
    assert summary["issued_rows"] == 3
    assert summary["complete_rows"] == 2 and summary["cancelled_rows"] == 1
    assert requests[0]["request_to_ack_seconds"] == 1.0
    assert requests[0]["post_ack_model_seconds"] == 4.0
    assert requests[0]["post_invalidation_model_seconds"] == 6.0
    assert requests[0]["post_invalidation_lease_seconds"] == 6.5
    assert batches[0]["model_seconds"] == 9.0  # Both masked and useful rows remain charged.


def test_no_cancellation_sham_actuator_audits_all_rows_and_drain():
    data = fixture()
    complete_instead(data)
    data["events"] = [event for event in data["events"] if event["kind"] != "cancel-request"]
    summary, requests, _ = audit.audit_lifecycle(**data)
    assert summary["complete_rows"] == 3 and summary["cancelled_rows"] == 0
    assert summary["cancellation_requests"] == 0 and requests == []
    assert summary["post_policy_trigger_model_seconds"] == 0.0
    assert summary["post_invalidation_model_seconds"] == 6.0  # No request must not erase baseline exposure.


def test_request_after_complete_is_a_noop_and_cannot_turn_result_into_cancelled():
    data = fixture()
    complete_instead(data)
    data["events"][1]["status"] = "already-terminal"
    summary, requests, _ = audit.audit_lifecycle(**data)
    assert summary["request_outcomes"] == {"completion-won":1}
    assert requests[0]["request_after_complete"]
    assert requests[0]["request_to_ack_seconds"] is None


def test_request_after_complete_cannot_also_claim_a_cancelled_terminal():
    data = fixture()
    data["results"]["p0"] = full_result(data["jobs"]["p0"], 106.2)
    with pytest.raises(AssertionError, match="terminal sets overlap"):
        audit.audit_lifecycle(**data)


def test_completion_after_request_may_legally_win_the_race():
    data = fixture()
    complete_instead(data, 108.3)
    _, requests, _ = audit.audit_lifecycle(**data)
    assert requests[0]["outcome"] == "completion-won"
    assert not requests[0]["request_after_complete"]


def test_drain_before_a_row_terminal_is_rejected():
    data = fixture()
    data["accounting"][0]["phases"][0]["completed_perf"] = 110.0
    data["accounting"][0]["batch_drained_perf"] = 110.5
    with pytest.raises(AssertionError, match="drained before row terminal"):
        audit.audit_lifecycle(**data)


def test_complete_and_cancelled_manifest_must_be_disjoint_and_cover_all_jobs():
    data = fixture()
    data["accounting"][0]["row_receipt_digests"]["p0"] = "fake-full"
    with pytest.raises(AssertionError, match="manifest overlap"):
        audit.audit_lifecycle(**data)
    data = fixture()
    data["accounting"][0]["cancelled_row_receipt_digests"] = {}
    with pytest.raises(AssertionError, match="do not cover"):
        audit.audit_lifecycle(**data)


def test_cancellation_cannot_carry_partial_output_even_with_resealed_digest():
    data = fixture()
    data["cancelled_records"][0]["cancellation"]["message"]["text"] = "unfinished prefix"
    with pytest.raises(AssertionError, match="output or unknown fields"):
        audit.audit_lifecycle(**data)


def test_cancellation_cannot_publish_or_commit_even_if_digest_is_valid():
    data = fixture()
    data["events"].append(dict(kind="display", job_id="p0"))
    with pytest.raises(AssertionError, match="complete output/admission"):
        audit.audit_lifecycle(**data)


def test_actual_binding_and_owner_request_are_required():
    data = fixture()
    data["cancelled_records"][0]["cancellation"]["message"]["binding"]["worker_incarnation"] = "old"
    with pytest.raises(AssertionError):
        audit.audit_lifecycle(**data)
    data = fixture()
    data["events"] = [event for event in data["events"] if event["kind"] != "cancel-request"]
    with pytest.raises(AssertionError, match="unrequested cancelled"):
        audit.audit_lifecycle(**data)


def test_invalidated_clock_is_derived_from_actual_installed_coverage():
    data = fixture()
    data["events"][1]["invalidated_perf"] = 105.9
    with pytest.raises(AssertionError, match="first actual qualifying event"):
        audit.audit_lifecycle(**data)
    data = fixture()
    data["events"][0]["audio_end_sample"] = 8000
    with pytest.raises(AssertionError, match="no independently observed invalidation"):
        audit.audit_lifecycle(**data)


def test_early_physical_release_and_hidden_masked_work_are_rejected():
    data = fixture()
    data["events"][1]["physical_worker_released"] = True
    with pytest.raises(AssertionError, match="incorrectly releases"):
        audit.audit_lifecycle(**data)
    data = fixture()
    data["accounting"][0]["masked_row_compute_charged_until_batch_drain"] = False
    with pytest.raises(AssertionError, match="removed from accounting"):
        audit.audit_lifecycle(**data)


def progress_fixture():
    specs = {0:dict(duration=3.0, offset=0.0), 1:dict(duration=3.0, offset=0.0)}
    snapshots = [dict(sessions={str(sid):dict(accepted=48000) for sid in specs})]
    consumer = []
    for sid, values in [(0, [(101.2,16000,0),(102.5,32000,16000),(104.5,48000,48000)]),
                        (1, [(101.5,16000,0),(103.5,32000,16000),(110.0,48000,48000)])]:
        for observed, visible, certified in values:
            consumer.append(dict(session_id=sid, observed_perf=observed, server_time=observed-100.1,
                valid_visible_frontier=visible, certified_frontier=certified))
    events = [dict(kind="commit",session_id=sid,audio_end_sample=48000) for sid in specs]
    return dict(specs=specs,consumer=consumer,snapshots=snapshots,events=events,origin=100.0,
        owner_start=100.0,fine_seconds=1.0,sample_rate=16000,end_perf=112.0)


def test_all_offered_frontiers_keep_missing_observations_and_original_deadlines():
    data = progress_fixture()
    data["specs"][2] = dict(duration=1.0,offset=0.0)
    data["snapshots"][0]["sessions"]["2"] = dict(accepted=0)
    frontiers, sessions, _, _ = audit.recount_progress(**data)
    assert len(frontiers) == 7  # Rejected/unaccepted source stays in the denominator.
    missing = next(row for row in frontiers if row["session_id"] == 2)
    assert missing["first_actual_visible_perf"] is None and not missing["dual_credit"]
    assert missing["original_ready_perf"] == 101.0
    assert all(row["accepted_unfulfilled_samples"] == 0 for row in sessions)


def test_accepted_input_cannot_be_deleted_or_left_unfulfilled():
    data = progress_fixture()
    data["snapshots"].append(dict(sessions={"0":dict(accepted=32000),"1":dict(accepted=48000)}))
    with pytest.raises(AssertionError, match="obligation was deleted"):
        audit.recount_progress(**data)
    data = progress_fixture()
    data["events"][0]["audio_end_sample"] = 32000
    with pytest.raises(AssertionError, match="obligations unfulfilled"):
        audit.recount_progress(**data)


def test_actual_consumer_observation_not_server_emission_gets_credit():
    data = progress_fixture()
    data["consumer"][0]["server_time"] = 2.0
    with pytest.raises(AssertionError, match="before actual Consumer"):
        audit.recount_progress(**data)


def test_unrelated_session_stalls_and_later_legal_progress_without_fault_labels():
    data = progress_fixture()
    _, sessions, progress, certified = audit.recount_progress(**data)
    requests = [dict(request_id="r",job_id="p",session_id=0,invalidated_perf=106.0,drained_perf=109.0)]
    rows = audit.interference_windows(requests, data["specs"], sessions, progress, certified,
        origin=100.0,end_perf=112.0)
    assert len(rows) == 1  # Session 0 finished at 104.5, and owes no later visible progress.
    assert rows[0]["relation"] == "unrelated-session" and rows[0]["session_id"] == 1
    assert rows[0]["longest_visible_stall_overlap_seconds"] == 3.0
    assert rows[0]["first_later_visible_perf"] == 110.0
    assert rows[0]["invalidation_to_next_visible_seconds"] == 4.0


def test_auditor_has_no_scheduler_or_production_lifecycle_imports():
    tree = ast.parse(Path(audit.__file__).read_text())
    imports = [node.module for node in ast.walk(tree) if isinstance(node,ast.ImportFrom)]
    imports += [alias.name for node in ast.walk(tree) if isinstance(node,ast.Import) for alias in node.names]
    assert not any(name and ("revtrace" in name or "scheduler" in name or "live_qwen" in name) for name in imports)

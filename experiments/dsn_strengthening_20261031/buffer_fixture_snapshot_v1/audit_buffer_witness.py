"""Independent offline check of original raw events, facts, and actual consumption.

Fixture markers are timing records, never substitutes for Owner/WAL/Consumer
evidence. Synthetic CPU conformance must be labelled development, not NN proof.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from buffer_fixture import validate_spec, sha_value, canonical, write_new
from buffer_controller import (need, cut_sha, validate_release, validate_buffer_binding,
                               validate_fence)


def load(path):
    return json.loads(Path(path).read_bytes())


def lines(path):
    data = Path(path).read_bytes()
    need(not data or data.endswith(b"\n"), "incomplete final original JSONL row")
    return [json.loads(line) for line in data.splitlines()]


def file_binding(path, root):
    data = path.read_bytes()
    return dict(path=path.relative_to(root).as_posix(), bytes=len(data),
                sha256=hashlib.sha256(data).hexdigest())


def audit(out, *, require_resident=True):
    # Independent binary-chain reader from the resident evidence harness,
    # rather than the NN writer's own scan/repair implementation.
    from common import verified_facts
    root = Path(out)
    config = load(root / "CONFIG.json")
    spec = validate_spec(config["timing_fixture"])
    gate_root = root / "timing_fixture"
    pm = load(gate_root / "parent.ready.json")
    cm = load(gate_root / "child.ready.json")
    resumed = load(gate_root / "parent.resumed.json")
    release = load(gate_root / "parent.release.json")
    need(load(gate_root / "SPEC.json") == spec, "controller ran a different timing specification")
    dispatch = lines(root / "owner_e0/dispatch.jsonl")
    worker = lines(root / "owner_e0/worker_results.jsonl")
    owners = lines(root / "owner_e0/owner_events.jsonl")
    policy = lines(root / "owner_e0/policy_audit.jsonl")
    pubs = lines(root / "publications.jsonl")
    consumer = lines(root / "consumer.jsonl")
    control = lines(gate_root / "controller.jsonl")
    jobs = {row["job"]["job_id"]: row["job"] for row in dispatch}
    started = {(row["slot"], row["incarnation"]): row for row in owners
               if row["kind"] == "worker_started"}
    results = {}
    for row in worker:
        event = row["event"]
        key = event.get("job_id"), event.get("kind")
        if key in results:
            need(canonical(results[key]) == canonical(event), "conflicting original worker receipts")
        results[key] = event
    pjob, cjob = jobs[pm["job_id"]], jobs[cm["job_id"]]
    pe = results[(pm["job_id"], "asr_early")]
    ce = results[(cm["job_id"], "completed")]
    parent_complete = results[(pm["job_id"], "completed")]
    full_views = [row for row in pubs if any(
        step.get("job_id") == cjob["job_id"] and
        step.get("kind") == "actual_original_full_conditional_closed_node"
        for step in row["event"].get("steps", []))]
    need(bool(full_views), "no original Owner full-buffer post-admission publication")
    view = min(full_views, key=lambda row: row["received_perf"])
    validate_buffer_binding(pm, cm, pe, ce, pjob, cjob, started, view, spec)
    fence = validate_release(root, release, pm, spec, expected_child_job=cjob,
                             expected_child_started=started[(cjob["worker"], cjob["worker_incarnation"])],
                             expected_child_marker=cm)
    need(resumed.get("nonce") == spec["nonce"] and
         resumed.get("marker_sha256") == sha_value(pm) and
         resumed.get("job_id") == pjob["job_id"] and
         resumed.get("observed", -1) >= release["observed"], "parent resumed without its bound native fence")
    registrations = [row for row in control if row["kind"] == "owner_buffer_registered_before_kill"]
    kills = [row for row in control if row["kind"] == "worker_sigkill"]
    need(len(registrations) == len(kills) == 1, "timing fixture requires exactly one bound fail-stop")
    registration, kill = registrations[0], kills[0]
    need(registration["child_job"] == cjob and
         registration["publication_semantic_sha256"] == sha_value(view["event"]),
         "controller did not use the original accepted full node")
    need(registration["observed"] <= kill["requested_perf"] <= fence["confirmed_perf"] and
         view["received_perf"] <= kill["requested_perf"], "kill preceded original Owner buffer receipt")
    need(kill["job_id"] == cjob["job_id"] and kill["pid"] == cm["pid"] and
         kill["start_ticks"] == cm["start_ticks"], "signal targeted another execution")
    need(parent_complete["record"].get("selected_correction") is not None and
         parent_complete["record"].get("native_model_evaluated") is True and
         parent_complete["record"]["model_end"] >= resumed["observed"],
         "parent did not continue the original neural C/U after the fence")
    predicted_sha = cut_sha(pe["projection"]["end"])
    actual_sha = cut_sha(parent_complete["end"])
    need(predicted_sha == spec["historical_parent_prediction_sha"] and
         actual_sha == spec["historical_parent_actual_sha"],
         "current full-state boundary did not reproduce the frozen historical exact-state premise")
    actual_match = canonical(parent_complete["end"]) == canonical(cjob["start"])
    need(actual_match == spec["expect_match"], "new actual complete parent input did not satisfy frozen expectation")
    facts = [(obj, dict(sequence=obj["sequence"])) for obj in verified_facts(root / "facts.wal")
             if obj["kind"] == "canonical"]
    parent_facts = [(obj, receipt) for obj, receipt in facts if obj["body"]["job"]["job_id"] == pjob["job_id"]]
    child_facts = [(obj, receipt) for obj, receipt in facts if obj["body"]["job"]["job_id"] == cjob["job_id"]]
    need(len(parent_facts) == 1 and canonical(parent_facts[0][0]["body"]["next_state"]) ==
         canonical(parent_complete["end"]), "actual parent was not installed through original durable state")
    parent_installs = [row for row in owners if row["kind"] == "canonical_install" and
                       row["job_id"] == pjob["job_id"]]
    need(len(parent_installs) == 1 and parent_installs[0]["observed"] >= resumed["observed"],
         "actual parent confirmation preceded gate release")
    if actual_match:
        need(len(child_facts) == 1, "matched old complete buffer was not installed exactly once")
        fact, receipt = child_facts[0]
        body = fact["body"]
        need(canonical(body["job"]) == canonical(cjob), "old job/birth/incarnation identity was rewritten")
        need(canonical(body["record"]) == canonical(ce["record"]) and
             canonical(body["next_state"]) == canonical(ce["end"]), "installed result was recomputed/substituted")
        need(canonical(body["parent_state"]) == canonical(parent_complete["end"]),
             "old buffer installed with a different actual complete input")
        installs = [row for row in owners if row["kind"] == "canonical_install" and row["job_id"] == cjob["job_id"]]
        consumed = [row for row in consumer if row.get("kind") == "canonical" and
                    row.get("journal_sequence") == receipt["sequence"]]
        need(len(installs) == len(consumed) == 1 and
             fence["fence_observed_perf"] < parent_installs[0]["observed"] <= installs[0]["observed"] <= consumed[0]["observed"],
             "old buffer not actually installed and consumed after original fence/parent confirmation")
        need(consumed[0]["canonical_sha"] == cut_sha(ce["end"]) and
             consumed[0]["certified_frontier"] >= spec["child_end"], "actual Consumer did not certify target old buffer")
        result = dict(old_uid_post_fence_canonical_install=1, old_uid_post_fence_certified_consume=1,
                      canonical_sequence=receipt["sequence"], consumer_observed_perf=consumed[0]["observed"])
    else:
        need(not child_facts, "mismatched dead-producer result acquired durable authority")
        discarded = [row for row in policy if row.get("kind") == "discarded_full" and
                     row["body"]["job"]["job_id"] == cjob["job_id"]]
        need(len(discarded) == 1, "mismatched old buffer lacks one original discard witness")
        proof = discarded[0]["body"]["proof"]
        need(proof.get("kind") == "actual_canonical_disagrees_with_complete_start" and
             proof.get("witness_frontier") == spec["parent_end"] and
             proof.get("expected_cut_sha") == cut_sha(cjob["start"]) and
             proof.get("actual_cut_sha") == actual_sha, "discard did not use actual same-frontier full-input mismatch")
        need(discarded[0]["observed"] >= resumed["observed"], "buffer discarded before actual parent was allowed to complete")
        need(not any(row["kind"] == "canonical_install" and row["job_id"] == cjob["job_id"] for row in owners),
             "mismatched old UID was installed")
        result = dict(old_uid_post_fence_canonical_install=0, old_uid_post_fence_certified_consume=0,
                      original_same_frontier_discard=1)
    requests = []
    if require_resident:
        resident = load(root / "SUMMARY.json")
        need(resident.get("gate") == "PASS_RESIDENT_COMPLETE_TASK_PER_REQUEST_CLOCK_AND_REFERENCE",
             "resident full-task/reference gate did not pass")
        need(resident["integrity"].get("all_original_obligations_eventually_processed") is True and
             resident["integrity"]["original_reference"]["status"] == "PASS_COMPLETE_SELECTED_TRACE_REFERENCE",
             "original task/reference and accepted obligations not completely checked")
        ledger = lines(root / "request_ledger.jsonl")
        order = config["request_order"]
        need(order[0] == spec["source_id"], "fault target was not the frozen first request")
        for i, sid in enumerate(order):
            admitted = [r for r in ledger if r["kind"] == "request_admitted" and r["source_id"] == sid]
            complete = [r for r in ledger if r["kind"] == "request_complete" and r["source_id"] == sid]
            need(len(admitted) == len(complete) == 1, "missing or duplicated request admission/EOS")
            if i:
                previous = requests[-1]
                need(admitted[0]["observed"] >= previous["complete_perf"] and
                     admitted[0]["previous_source_id"] == order[i - 1], "follow-up admitted before previous actual EOS")
            need(complete[0]["certified_frontier"] == complete[0]["EOS_frontier"] and
                 complete[0]["observed"] >= fence["fence_observed_perf"], "post-fault request did not finish certified EOS")
            requests.append(dict(source_id=sid, admission_perf=admitted[0]["observed"],
                                 complete_perf=complete[0]["observed"]))
        need(not list(root.glob("owner_e[1-9]*")), "Owner restarted; not the declared same-Owner follow-up witness")
    paths = [root / n for n in ("CONFIG.json", "owner_e0/dispatch.jsonl", "owner_e0/worker_results.jsonl",
             "owner_e0/owner_events.jsonl", "owner_e0/policy_audit.jsonl", "publications.jsonl",
             "consumer.jsonl", "facts.wal", "timing_fixture/controller.jsonl", "timing_fixture/parent.ready.json",
             "timing_fixture/child.ready.json", "timing_fixture/parent.release.json", "timing_fixture/parent.resumed.json")]
    return dict(status=("PASS_CONTROLLED_REAL_NN_BUFFER_POST_PRODUCER_DEATH_MATCH" if actual_match else
                "PASS_CONTROLLED_REAL_NN_BUFFER_POST_PRODUCER_DEATH_MISMATCH_REJECTED") if require_resident else
                "PASS_DEVELOPMENT_SYNTHETIC_BUFFER_TRACE_CONFORMANCE",
                experiment_id=spec["experiment_id"], scope="one predeclared controlled interleaving; not natural prevalence, performance or long-stream quality",
                base_nn_commit=spec["base_nn_commit"], fixture_identity=config.get("execution_dependencies"),
                original_child_job_id=cjob["job_id"], original_birth_canonical_sha=cjob["birth_canonical_sha"],
                original_worker_incarnation=cjob["worker_incarnation"], actual_parent_full_input_matches=actual_match,
                predicted_full_sha=predicted_sha, actual_parent_full_sha=actual_sha,
                physical_fence=fence, result=result, requests=requests,
                inputs=[file_binding(path, root) for path in paths])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    result = audit(args.out)
    write_new(args.out / "BUFFER_WITNESS_GATE.json", result)
    print(json.dumps({k: v for k, v in result.items() if k not in ("inputs", "fixture_identity")}, ensure_ascii=False))


if __name__ == "__main__":
    main()

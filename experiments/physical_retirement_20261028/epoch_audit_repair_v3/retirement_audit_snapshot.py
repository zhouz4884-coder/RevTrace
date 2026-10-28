"""Independent recorded-service audit for decode-safe physical retirement.

No scheduler, cancellation policy, production Consumer, or row lifecycle code is
imported. Hashing, input-WAL parsing and the existing actual-view safety recount
come from the independent x_service_metrics auditor. Counts and clocks describe
recorded behavior; neither a host request nor a row terminal proves GPU release.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from collections import Counter
from pathlib import Path

import x_service_metrics as service


BINDING_KEYS = {
    "worker", "worker_incarnation", "batch_id", "job_id", "session_id", "role",
    "parent", "contract_epoch", "contract_digest", "runtime_digest",
    "audio_start_sample", "audio_end_sample", "interval_audio_sha256", "input_identity",
}
INPUT_KEYS = [
    "session_id", "source_id", "role", "parent", "prompt_tokens", "chunk_id",
    "audio_start_sample", "audio_end_sample", "prefix_audio_sha256",
    "interval_audio_sha256", "fault_actual_prompt_tokens",
]
CANCEL_KEYS = {
    "binding", "request_id", "reason", "requested_perf", "acknowledged_perf",
    "emitted_perf", "decoded_tokens", "terminal_digest",
}
PARTIAL_OUTPUT_KEYS = {"token_ids", "state_tokens", "text", "segment_tokens", "next_prompt_tokens"}
EPSILON = 1e-6


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def finite(value):
    require(type(value) in (int, float) and math.isfinite(value), "nonfinite recorded clock")
    return float(value)


def event_perf(event, owner_start):
    return finite(event["observed_perf"] if "observed_perf" in event else owner_start + event["time"])


def validate_binding(job, binding):
    require(set(binding) == BINDING_KEYS, "changed or incomplete physical binding")
    declared = job["_delivery"]
    require(binding == declared["binding"], "receipt does not match immutable submitted binding")
    for key in ["job_id", "session_id", "role", "parent", "contract_epoch", "contract_digest",
                "runtime_digest", "audio_start_sample", "audio_end_sample", "interval_audio_sha256"]:
        require(binding[key] == job.get(key, 1 if key == "contract_epoch" else None),
                "row binding/job identity mismatch: " + key)
    require((binding["worker"], binding["worker_incarnation"], binding["batch_id"]) ==
            (declared["worker"], declared["incarnation"], declared["batch_id"]), "wrong worker incarnation")
    require(binding["input_identity"] == service.sha({key: job.get(key) for key in INPUT_KEYS}),
            "changed actual input identity")


def validate_cancel_message(message, job):
    # Exact schema is deliberate: no partial tokens, text or selection evidence
    # may be smuggled into a counts-only cancellation terminal.
    require(set(message) == CANCEL_KEYS, "cancelled terminal contains output or unknown fields")
    validate_binding(job, message["binding"])
    require(job["role"] == "proposal", "authority row was cancelled")
    require(isinstance(message["request_id"], str) and bool(message["request_id"]), "missing cancel request identity")
    require(isinstance(message["reason"], str) and bool(message["reason"]), "missing cancel reason")
    require(type(message["decoded_tokens"]) is int and message["decoded_tokens"] >= 0,
            "invalid cancelled token count")
    requested, acknowledged, emitted = [finite(message[key]) for key in
                                        ["requested_perf", "acknowledged_perf", "emitted_perf"]]
    require(requested <= acknowledged <= emitted, "noncausal cancellation clocks")
    body = {key: value for key, value in message.items() if key != "terminal_digest"}
    body["kind"] = "row-cancelled-v1"
    require(service.sha(body) == message["terminal_digest"], "mutated cancelled terminal digest")
    return message


def cancellation_message(audit):
    message = audit.get("message")
    require(isinstance(message, dict), "missing sealed cancellation message")
    for key in ["binding", "request_id", "reason", "requested_perf", "acknowledged_perf",
                "emitted_perf", "decoded_tokens", "terminal_digest"]:
        if key in audit:
            require(audit[key] == message[key], "cancellation wrapper/message disagreement: " + key)
    require(not PARTIAL_OUTPUT_KEYS.intersection(audit), "cancelled wrapper carries partial output")
    require(audit.get("physical_worker_released") is False, "cancelled row incorrectly releases worker")
    return message


def _phase_overlap(phases, lo, hi):
    return sum(max(0.0, min(hi, phase["completed_perf"]) - max(lo, phase["started_perf"]))
               for phase in phases)


def observed_invalidations(jobs, results, cancelled, accounting, events, *, owner_start, dispatches):
    """Proof-based exposure in EVERY arm, including arms issuing no requests.

    Parent advancement and watchdog expiry are deliberately not proof of semantic
    uselessness here. A row already terminal before coverage is not an active
    invalidation opportunity. Fixed-layout occupancy is billed through model
    return/drain and may include useful peers, so these are not waste/savings.
    """
    output = []
    by_job = {jid:batch for batch in accounting for jid in batch["job_ids"]}
    for jid, job in jobs.items():
        if job["role"] != "proposal":
            continue
        candidates = []
        for event in events:
            if event.get("session_id") != job["session_id"]:
                continue
            if event["kind"] == "commit" and event["audio_end_sample"] >= job["audio_end_sample"]:
                candidates.append((owner_start+event["installed"], "trusted-coverage"))
            elif (event["kind"] == "private-generation-retired" and event["generation"] > job.get("branch_generation", 0)
                  and owner_start+event["time"] >= job["enqueue_perf"]):
                candidates.append((owner_start+event["time"], "retired-generation"))
        if not candidates:
            continue
        invalidated, reason = min(candidates)
        terminal = cancelled[jid]["acknowledged_perf"] if jid in cancelled else results[jid]["_row_receipt"]["terminal_perf"]
        if invalidated >= terminal:
            continue
        batch = by_job[jid]
        phases = [phase for phase in batch["phases"] if jid in phase["executed_job_ids"]]
        drain = batch["batch_drained_perf"]
        output.append(dict(job_id=jid, session_id=job["session_id"], worker=job["_delivery"]["worker"],
            batch_id=batch["batch_id"], reason=reason, invalidated_perf=invalidated,
            row_terminal_perf=terminal, terminal_kind="cancelled" if jid in cancelled else "complete",
            batch_drained_perf=drain, invalidation_to_row_terminal_seconds=terminal-invalidated,
            invalidation_to_drain_seconds=drain-invalidated,
            post_invalidation_model_seconds=_phase_overlap(phases, invalidated, drain),
            post_invalidation_lease_seconds=max(0.0, drain-max(invalidated, dispatches[batch["batch_id"]]))))
    return output


def _invalidation(request, job, batch, events, owner_start, config):
    reason = request["invalidation_kind"]
    require(reason == request["reason"], "invalidation reason relabelled")
    sid = job["session_id"]
    commits = [event for event in events if event["kind"] == "commit" and event["session_id"] == sid]
    if reason == "trusted-coverage":
        candidates = [owner_start + event["installed"] for event in commits
                      if event["audio_end_sample"] >= job["audio_end_sample"]]
    elif reason == "parent-version-superseded":
        candidates = [owner_start + event["installed"] for event in commits if event["version"] > job["parent"]]
    elif reason == "retired-generation":
        candidates = [owner_start + event["time"] for event in events
                      if event["kind"] == "private-generation-retired" and event["session_id"] == sid
                      and event["generation"] > job.get("branch_generation", 0)
                      and owner_start+event["time"] >= job["enqueue_perf"]]
    elif reason == "watchdog-timeout":
        watchdog = config.get("physical_retirement", {}).get("watchdog_seconds")
        require(type(watchdog) in (int, float) and watchdog > 0, "unfrozen watchdog threshold")
        candidates = [batch["worker_started_perf"] + watchdog]
    else:
        raise AssertionError("unrecognized invalidation kind: " + str(reason))
    require(bool(candidates), "cancel request has no independently observed invalidation")
    invalidated = min(map(finite, candidates))
    declared = finite(request["invalidated_perf"])
    require(abs(declared - invalidated) <= EPSILON, "invalidation clock is not first actual qualifying event")
    require(invalidated <= request["requested_perf"] + EPSILON, "cancellation predates invalidation")
    return invalidated


def audit_lifecycle(jobs, results, cancelled_records, accounting, events, *, owner_start,
                    dispatches, config):
    """Reconstruct full/cancelled terminal coverage independently of policy.

    dispatches maps physical batch_id to the actual authorized pre-submit clock.
    results includes only full worker_records; cancelled_records is the separate
    [{job, cancellation}] stream. This interface also supports small CPU fixtures.
    """
    require(len(jobs) == len(set(jobs)), "duplicate job identity")
    full_ids = set(results)
    cancelled = {}
    for record in cancelled_records:
        job = record["job"]
        jid = job["job_id"]
        require(jid in jobs and job == jobs[jid], "changed cancelled job record")
        require(jid not in cancelled, "duplicate cancelled terminal record")
        message = validate_cancel_message(cancellation_message(record["cancellation"]), job)
        received = finite(record["cancellation"]["received_perf"])
        require(message["emitted_perf"] <= received, "cancel terminal received before emission")
        cancelled[jid] = message
    require(not full_ids.intersection(cancelled), "complete/cancelled terminal sets overlap")
    require(full_ids | set(cancelled) == set(jobs), "issued job lacks a terminal or hidden terminal job")
    complete_receipts = {}
    for jid, result in results.items():
        job = jobs[jid]
        require(not (result.get("row_terminal_kind") == "cancelled" or result.get("row_cancelled")),
                "cancelled prefix presented as full result")
        receipt = result["_row_receipt"]
        validate_binding(job, receipt["binding"])
        body = {key: value for key, value in result.items()
                if key not in ["_row_receipt", "received_perf", "text_binding"]}
        require(service.sha(body) == receipt["payload_sha256"], "mutated complete payload")
        terminal, rendered, emitted = [finite(receipt[key]) for key in ["terminal_perf", "rendered_perf", "emitted_perf"]]
        require(terminal <= rendered <= emitted <= finite(result["received_perf"]), "noncausal complete-row clocks")
        complete_receipts[jid] = receipt
    batches, job_batch, batch_rows = {}, {}, []
    for batch in accounting:
        bid = batch["batch_id"]
        require(bid not in batches, "repeated physical batch accounting")
        require(batch["schema"] == "row-cost-v1", "unknown accounting schema")
        ids = batch["job_ids"]
        require(bool(ids) and len(ids) == len(set(ids)), "duplicate/empty physical job set")
        complete_manifest = batch["row_receipt_digests"]
        cancel_manifest = batch.get("cancelled_row_receipt_digests", {})
        require(not set(complete_manifest).intersection(cancel_manifest), "complete/cancelled manifest overlap")
        require(set(complete_manifest) | set(cancel_manifest) == set(ids), "terminal manifests do not cover physical batch")
        require(set(complete_manifest) == set(ids).intersection(full_ids), "complete manifest disagrees with full records")
        require(set(cancel_manifest) == set(ids).intersection(cancelled), "cancel manifest disagrees with cancelled records")
        encoded_cancels = batch.get("cancelled_rows", [])
        require(len(encoded_cancels) == len(cancel_manifest), "cancelled receipt count differs from manifest")
        require({message["binding"]["job_id"] for message in encoded_cancels} == set(cancel_manifest),
                "missing or duplicate cancelled batch receipt")
        for message in encoded_cancels:
            jid = message["binding"]["job_id"]
            validate_cancel_message(message, jobs[jid])
            require(message == cancelled[jid] and message["terminal_digest"] == cancel_manifest[jid],
                    "batch/cancelled receipt mismatch")
        for jid, value in complete_manifest.items():
            require(value == complete_receipts[jid]["payload_sha256"], "batch/full receipt mismatch")
        selected = batch["selected_output_digests"]
        require(len(selected) == len(complete_manifest) and {row["job_id"] for row in selected} == set(complete_manifest),
                "cancelled row advertised as selected output or complete row omitted")
        for row in selected:
            result = results[row["job_id"]]
            require(row["Z_sha256"] == service.tokens(result["token_ids"]) and
                    row["P_sha256"] == service.tokens(result["state_tokens"]), "selected output changed")
            require(row["text_sha256"] == hashlib.sha256(result["text"].encode()).hexdigest(), "selected text changed")
        drain = finite(batch["batch_drained_perf"])
        worker_started = finite(batch["worker_started_perf"])
        require(bid in dispatches, "missing actual pre-submit dispatch receipt")
        dispatch = finite(dispatches[bid])
        require(dispatch <= worker_started <= drain, "noncausal dispatch/worker/drain clocks")
        phases = batch["phases"]
        require(bool(phases), "missing actual model-phase accounting")
        previous = worker_started
        for phase in sorted(phases, key=lambda value: value["started_perf"]):
            lo, hi = finite(phase["started_perf"]), finite(phase["completed_perf"])
            require(previous <= lo + EPSILON and lo <= hi <= drain, "overlapping or noncausal model phases")
            previous = hi
            require(set(phase["executed_job_ids"]).issubset(ids), "model phase executes foreign job")
            require(type(phase["physical_batch_rows"]) is int and
                    phase["physical_batch_rows"] >= len(set(phase["executed_job_ids"])), "invalid physical model layout")
        if cancel_manifest:
            require(batch.get("physical_release_basis") == "generation-return-and-CUDA-synchronize",
                    "cancelled batch lacks synchronized physical release")
            require(batch.get("masked_row_compute_charged_until_batch_drain") is True,
                    "masked row compute was removed from accounting")
        for jid in ids:
            require(jid in jobs and jid not in job_batch, "missing or multiply batched job")
            binding = jobs[jid]["_delivery"]["binding"]
            validate_binding(jobs[jid], binding)
            require(binding["batch_id"] == bid, "job moved to a different physical batch")
            require(any(jid in phase["executed_job_ids"] for phase in phases), "issued job has no paid model phase")
            emitted = cancelled[jid]["emitted_perf"] if jid in cancelled else complete_receipts[jid]["emitted_perf"]
            require(emitted <= drain, "batch drained before row terminal")
            job_batch[jid] = bid
        worker = jobs[ids[0]]["_delivery"]["worker"]
        require(all(jobs[jid]["_delivery"]["worker"] == worker for jid in ids), "cross-worker physical batch")
        batches[bid] = batch
        batch_rows.append(dict(batch_id=bid, worker=worker, dispatch_perf=dispatch,
                               worker_started_perf=worker_started, drained_perf=drain,
                               full_rows=len(complete_manifest), cancelled_rows=len(cancel_manifest),
                               physical_lease_seconds=drain - dispatch,
                               model_seconds=sum(phase["completed_perf"] - phase["started_perf"] for phase in phases)))
    require(set(job_batch) == set(jobs), "unaccounted issued jobs")
    for worker in {row["worker"] for row in batch_rows}:
        previous = -math.inf
        ordered = sorted((row for row in batch_rows if row["worker"] == worker), key=lambda value: value["dispatch_perf"])
        for index, row in enumerate(ordered):
            require(row["dispatch_perf"] >= previous, "new physical dispatch before actual prior batch drain")
            previous = row["drained_perf"]
            next_dispatch = ordered[index+1]["dispatch_perf"] if index+1 < len(ordered) else None
            row["next_actual_dispatch_perf"] = next_dispatch
            row["drain_to_next_dispatch_seconds"] = None if next_dispatch is None else next_dispatch-row["drained_perf"]
    for event in events:
        if event.get("job_id") in cancelled and event["kind"] in ["executor-complete", "worker-record", "display", "commit", "render-checked"]:
            raise AssertionError("cancelled prefix used as complete output/admission")
    requests, seen_requests, applied_requests = [], {}, set()
    owner_cancel_events = [event for event in events if event["kind"] == "row-cancelled"]
    require(len(owner_cancel_events) == len(cancelled), "missing or duplicate owner cancellation event")
    for event in owner_cancel_events:
        message = cancellation_message(event)
        require(message["binding"]["job_id"] in cancelled and message == cancelled[message["binding"]["job_id"]],
                "owner/worker cancellation disagreement")
        require(message["emitted_perf"] <= finite(event["received_perf"]), "owner cancel receipt before emission")
    for event in events:
        if event["kind"] != "cancel-request":
            continue
        require(event.get("physical_worker_released") is False, "cancel request incorrectly releases worker")
        if event.get("status") == "rejected":
            # Rejection cannot create a terminal. It is still counted below.
            requests.append(dict(job_id=event.get("job_id"), request_id=event.get("request_id"), outcome="request-rejected"))
            continue
        jid, rid = event["job_id"], event["request_id"]
        require(jid in jobs and rid not in seen_requests, "unknown job or repeated request identity")
        validate_binding(jobs[jid], event["binding"])
        require(jobs[jid]["role"] == "proposal", "authority cancellation request")
        requested = finite(event["requested_perf"])
        require(requested <= event_perf(event, owner_start) + EPSILON, "request event predates command")
        seen_requests[rid] = event
        batch = batches[job_batch[jid]]
        invalidated = _invalidation(event, jobs[jid], batch, events, owner_start, config)
        message = cancelled.get(jid)
        if message is not None:
            require(event.get("status") == "new-request", "cancelled terminal lacks accepted request")
            require((rid, event["reason"], requested) ==
                    (message["request_id"], message["reason"], message["requested_perf"]), "cancel terminal/request mismatch")
            require(rid not in applied_requests, "duplicate applied request")
            applied_requests.add(rid)
            acknowledged = message["acknowledged_perf"]
            received = next(record["cancellation"]["received_perf"] for record in cancelled_records
                            if record["job"]["job_id"] == jid)
            outcome = "row-cancelled"
        else:
            require(jid in results, "request disappeared without row terminal")
            acknowledged = received = None
            outcome = "completion-won"
        drain = batch["batch_drained_perf"]
        phases = [phase for phase in batch["phases"] if jid in phase["executed_job_ids"]]
        requests.append(dict(job_id=jid, session_id=jobs[jid]["session_id"], worker=event["binding"]["worker"],
            batch_id=job_batch[jid], request_id=rid, reason=event["reason"], outcome=outcome,
            invalidated_perf=invalidated, requested_perf=requested, acknowledged_perf=acknowledged,
            received_perf=received, drained_perf=drain,
            invalidation_to_request_seconds=max(0.0, requested-invalidated),
            request_to_ack_seconds=None if acknowledged is None else acknowledged-requested,
            invalidation_to_ack_seconds=None if acknowledged is None else acknowledged-invalidated,
            request_to_drain_seconds=max(0.0, drain-requested),
            invalidation_to_drain_seconds=max(0.0, drain-invalidated),
            post_invalidation_model_seconds=_phase_overlap(phases, invalidated, drain),
            post_invalidation_lease_seconds=max(0.0, drain-max(invalidated, dispatches[job_batch[jid]])),
            post_ack_model_seconds=None if acknowledged is None else _phase_overlap(phases, acknowledged, drain),
            request_after_complete=jid in results and complete_receipts[jid]["emitted_perf"] <= requested))
    require(applied_requests == {message["request_id"] for message in cancelled.values()}, "unrequested cancelled terminal")
    invalidation_rows = observed_invalidations(jobs, results, cancelled, accounting, events,
        owner_start=owner_start, dispatches=dispatches)
    # Resource aggregates count each physical batch once, never add overlapping
    # per-row masked tails as though they were separate GPU wall-clock savings.
    for row in batch_rows:
        affected = [request for request in requests if request.get("batch_id") == row["batch_id"]]
        earliest = min((request["invalidated_perf"] for request in affected), default=None)
        row["first_policy_trigger_perf"] = earliest
        row["post_policy_trigger_model_seconds"] = 0.0 if earliest is None else _phase_overlap(
            batches[row["batch_id"]]["phases"], earliest, row["drained_perf"])
        row["post_policy_trigger_lease_seconds"] = 0.0 if earliest is None else max(
            0.0, row["drained_perf"]-max(earliest, row["dispatch_perf"]))
        observed = [value["invalidated_perf"] for value in invalidation_rows if value["batch_id"] == row["batch_id"]]
        earliest = min(observed, default=None)
        row["first_invalidation_perf"] = earliest
        row["post_invalidation_model_seconds"] = 0.0 if earliest is None else _phase_overlap(
            batches[row["batch_id"]]["phases"], earliest, row["drained_perf"])
        row["post_invalidation_lease_seconds"] = 0.0 if earliest is None else max(
            0.0, row["drained_perf"]-max(earliest, row["dispatch_perf"]))
    summary = dict(status="PASS_INDEPENDENT_RETIREMENT_LIFECYCLE", issued_rows=len(jobs),
        complete_rows=len(results), cancelled_rows=len(cancelled), cancellation_requests=len(requests),
        request_outcomes=dict(Counter(request["outcome"] for request in requests)), physical_batches=len(batches),
        physical_model_seconds=sum(row["model_seconds"] for row in batch_rows),
        physical_lease_seconds=sum(row["physical_lease_seconds"] for row in batch_rows),
        independently_observed_inflight_invalidations=len(invalidation_rows),
        post_invalidation_model_seconds=sum(row["post_invalidation_model_seconds"] for row in batch_rows),
        post_invalidation_lease_seconds=sum(row["post_invalidation_lease_seconds"] for row in batch_rows),
        post_policy_trigger_model_seconds=sum(row["post_policy_trigger_model_seconds"] for row in batch_rows),
        post_policy_trigger_lease_seconds=sum(row["post_policy_trigger_lease_seconds"] for row in batch_rows),
        cancelled_prefix_publications=0, terminal_manifest_disjoint_cover=True,
        resource_scope="actual fixed-layout model phases and physical worker leases; no counterfactual savings")
    return summary, requests, batch_rows


def recount_progress(specs, consumer, snapshots, events, *, origin, owner_start, fine_seconds,
                     sample_rate, end_perf, display_deadline=2.0, commit_deadline=8.0):
    """All offered frontiers and actual Consumer progress; no source/fault labels."""
    accepted = {sid: 0 for sid in specs}
    for snapshot in snapshots:
        for key, state in snapshot["sessions"].items():
            sid = int(key)
            require(state["accepted"] >= accepted[sid], "accepted input obligation was deleted")
            accepted[sid] = state["accepted"]
    committed = {sid: 0 for sid in specs}
    for event in events:
        if event["kind"] == "commit":
            sid = event["session_id"]
            require(committed[sid] < event["audio_end_sample"] <= accepted[sid], "commit outside accepted obligation")
            committed[sid] = event["audio_end_sample"]
    first_visible, first_certified = {}, {}
    progress = {sid: [] for sid in specs}
    certified_progress = {sid: [] for sid in specs}
    previous_visible = {sid: 0 for sid in specs}
    previous_certified = {sid: 0 for sid in specs}
    last_observed = {sid: -math.inf for sid in specs}
    for row in sorted(consumer, key=lambda value: value["observed_perf"]):
        sid = row["session_id"]
        observed = finite(row["observed_perf"])
        require(observed >= last_observed[sid], "Consumer observation clock regressed")
        # The FIFO Consumer can apply an empty epoch/mode root for a declared
        # staggered session before that source starts. It represents no audio,
        # text or selected state and must never earn any frontier credit.
        empty_genesis = (row.get("kind") == "consumer-view"
            and row.get("source_kind") == "view-mode"
            and row.get("no_certified_snapshot_yet") is True
            and row.get("canonical_version") == 0
            and row.get("valid_visible_frontier") == row.get("certified_frontier") == 0
            and row.get("visible_text") == row.get("certified_text") == ""
            and all(row.get(key) is None for key in ("certified_transaction", "certified_Z_sha256",
                "certified_P_sha256", "certified_text_sha256"))
            and row.get("joined_suffix") is False
            and row.get("compatible_provisional_retained") is False)
        require(observed >= origin + specs[sid]["offset"] or empty_genesis,
                "Consumer precedes source arrival")
        last_observed[sid] = observed
        if "server_time" in row:
            require(observed + EPSILON >= owner_start + row["server_time"], "credit taken before actual Consumer observation")
        visible, certified = row["valid_visible_frontier"], row["certified_frontier"]
        total_samples = round(specs[sid]["duration"] * sample_rate)
        require(0 <= certified <= accepted[sid] and certified <= visible <= total_samples, "Consumer frontier outside offered/accepted audio")
        if visible > previous_visible[sid]:
            progress[sid].append((observed, visible))
            previous_visible[sid] = visible
        if certified > previous_certified[sid]:
            certified_progress[sid].append((observed, certified))
            previous_certified[sid] = certified
        for window in range(1, math.ceil(specs[sid]["duration"] / fine_seconds) + 1):
            frontier = min(round(window * fine_seconds * sample_rate), total_samples)
            if frontier <= visible:
                first_visible.setdefault((sid, frontier), observed)
            if frontier <= certified:
                first_certified.setdefault((sid, frontier), observed)
    frontiers, sessions = [], []
    for sid, spec in specs.items():
        previous = 0
        for window in range(1, math.ceil(spec["duration"] / fine_seconds) + 1):
            frontier = min(round(window * fine_seconds * sample_rate), round(spec["duration"] * sample_rate))
            ready = origin + spec["offset"] + frontier / sample_rate
            seen, certified = first_visible.get((sid, frontier)), first_certified.get((sid, frontier))
            dl = math.inf if seen is None else seen-ready
            cl = math.inf if certified is None else certified-ready
            require(dl >= -EPSILON and cl >= -EPSILON, "frontier credited before original input release")
            frontiers.append(dict(session_id=sid, frontier=frontier, original_ready_perf=ready,
                audio_seconds=(frontier-previous)/sample_rate, first_actual_visible_perf=seen,
                first_actual_certified_perf=certified, display_latency=service.export_float(dl),
                commit_view_latency=service.export_float(cl),
                dual_credit=dl <= display_deadline and cl <= commit_deadline))
            previous = frontier
        first_ready = origin + spec["offset"] + min(fine_seconds, spec["duration"])
        full_visible = first_visible.get((sid, round(spec["duration"] * sample_rate)))
        live_end = min(end_perf, full_visible) if full_visible is not None else end_perf
        ticks = [first_ready] + [t for t, _ in progress[sid] if first_ready <= t <= live_end] + [live_end]
        sessions.append(dict(session_id=sid, offered_samples=round(spec["duration"] * sample_rate),
            accepted_samples=accepted[sid], actual_committed_samples=committed[sid],
            accepted_unfulfilled_samples=max(0, accepted[sid]-committed[sid]),
            observed_visible_progress_events=len(progress[sid]),
            observed_certified_progress_events=len(certified_progress[sid]),
            longest_actual_visible_progress_gap_seconds=max((b-a for a,b in zip(ticks,ticks[1:])), default=0.0)))
    require(sum(row["accepted_unfulfilled_samples"] for row in sessions) == 0,
            "completed run leaves accepted input obligations unfulfilled")
    return frontiers, sessions, progress, certified_progress


def interference_windows(requests, specs, sessions, visible_progress, certified_progress, *, origin, end_perf,
                         fine_seconds=1.0, sample_rate=16000):
    """Observed local stalls around invalidation windows, not a causal speedup."""
    output = []
    accepted = {row["session_id"]: row["accepted_samples"] for row in sessions}
    for request in requests:
        if "invalidated_perf" not in request:
            continue
        lo, hi = request["invalidated_perf"], request["drained_perf"]
        if hi <= lo:
            continue
        for sid, spec in specs.items():
            if not accepted[sid] or origin + spec["offset"] > hi:
                continue
            full_samples = round(spec["duration"] * sample_rate)
            visible = visible_progress[sid]
            full_visible = next((t for t, frontier in visible if frontier >= full_samples), None)
            live_end = min(end_perf, full_visible) if full_visible is not None else end_perf
            if live_end <= lo:
                continue  # No more visible progress is owed after completion.
            first_ready = origin + spec["offset"] + min(fine_seconds, spec["duration"])
            begin = max(lo, first_ready)
            ticks = [first_ready] + [t for t, _ in visible if first_ready <= t <= live_end] + [live_end]
            stall = max((max(0.0, min(b, hi, live_end)-max(a, begin)) for a,b in zip(ticks,ticks[1:])), default=0.0)
            next_visible = next(((t, f) for t, f in visible if t >= lo), None)
            next_certified = next(((t, f) for t, f in certified_progress[sid] if t >= lo), None)
            output.append(dict(request_id=request["request_id"], invalidated_job_id=request["job_id"],
                session_id=sid, relation="same-session" if sid == request["session_id"] else "unrelated-session",
                invalidated_perf=lo, physical_drained_perf=hi,
                longest_visible_stall_overlap_seconds=stall,
                legal_visible_progress_during_occupancy=sum(begin <= t <= hi for t,_ in visible),
                legal_certified_progress_during_occupancy=sum(begin <= t <= hi for t,_ in certified_progress[sid]),
                first_later_visible_perf=None if next_visible is None else next_visible[0],
                first_later_visible_frontier=None if next_visible is None else next_visible[1],
                first_later_certified_perf=None if next_certified is None else next_certified[0],
                invalidation_to_next_visible_seconds=None if next_visible is None else next_visible[0]-lo))
    return output


def _actual_dispatches(root, jobs, accounting, events, owner_start, fine):
    direct = [event for event in events if event["kind"] == "batch-dispatched"]
    if direct:
        output = {}
        for event in direct:
            bids = {jobs[jid]["_delivery"]["batch_id"] for jid in event["job_ids"]}
            require(len(bids) == 1, "mixed physical dispatch IDs")
            bid = bids.pop()
            require(bid not in output, "repeated physical dispatch")
            output[bid] = owner_start + event["time"]
        return output
    trace = service.read(root/"kernel_trace.json")["events"]
    by_worker = {}
    for batch in accounting:
        worker = jobs[batch["job_ids"][0]]["_delivery"]["worker"]
        by_worker.setdefault(worker, []).append(batch)
    output = {}
    for worker, batches in by_worker.items():
        batches.sort(key=lambda batch: int(batch["batch_id"].rsplit(":", 1)[1]))
        submitted = [event for event in trace if event["kind"] == "dispatch" and event["operation"] == worker]
        require(len(submitted) == len(batches), "missing actual kernel pre-submit receipt")
        for event, batch in zip(submitted, batches):
            normalized = []
            for jid in batch["job_ids"]:
                job = jobs[jid]
                normalized.append(dict(id=jid, sid=job["session_id"], role=job["role"], parent=job["parent"],
                    start=job["audio_start_sample"], end=job["audio_end_sample"],
                    rootF=round(job["chunk_id"]*fine), inputP=service.tokens(job["prompt_tokens"]),
                    identity=service.sha({key:value for key,value in job.items() if key != "_delivery"})))
            require(service.sha(dict(worker=worker, jobs=normalized)) == event["payload_sha256"],
                    "kernel dispatch/job identity changed")
            output[batch["batch_id"]] = event["observed_perf"]
    return output


def audit_episode(episode, manifest):
    episode = Path(episode)
    root = episode/"attempt0"
    config = service.read(root/"config.json")
    events = service.lines(root/"events.jsonl")
    owner_start = next(event["t0_perf"] for event in events if event["kind"] == "run-start")
    records = service.lines(root/"worker_records.jsonl")
    cancel_path = root/"worker_cancelled_records.jsonl"
    cancelled = service.lines(cancel_path) if cancel_path.exists() else []
    jobs, results = {}, {}
    for record in records:
        jid = record["job"]["job_id"]
        require(jid not in jobs, "duplicate complete worker record")
        jobs[jid], results[jid] = record["job"], record["result"]
    for record in cancelled:
        jid = record["job"]["job_id"]
        require(jid not in jobs, "duplicate or conflicting cancelled worker record")
        jobs[jid] = record["job"]
    enqueues = [event["job_id"] for event in events if event["kind"] == "enqueue"]
    require(len(enqueues) == len(set(enqueues)) and set(enqueues) == set(jobs), "completed run hides issued input work")
    accounting = service.lines(root/"worker_batch_accounting.jsonl")
    dispatches = _actual_dispatches(root, jobs, accounting, events, owner_start,
                                   config["fine_seconds"]*config["sample_rate"])
    lifecycle, requests, batches = audit_lifecycle(jobs, results, cancelled, accounting, events,
        owner_start=owner_start, dispatches=dispatches, config=config)
    # Existing independent replay validates actual Consumer legality, immutable
    # full outputs, input ACK/WAL causality, original deadlines, energy and cost.
    base, _ = service.audit_episode(episode, manifest)
    specs = {row["session_id"]:row for row in service.read(root/"sessions.json")}
    context = service.read(episode/"episode.json")
    origin = context["origin_perf"]
    consumer = service.lines(root/"consumer.jsonl")
    frames = service.input_frames(episode/"input.wal")
    snapshots = [frame["snapshot"] for frame in frames.values() if frame["kind"] == "envelope-snapshot"]
    end = origin + base["original_episode_wall_seconds"]
    frontiers, sessions, progress, certified = recount_progress(specs, consumer, snapshots, events,
        origin=origin, owner_start=owner_start, fine_seconds=config["fine_seconds"],
        sample_rate=config["sample_rate"], end_perf=end)
    require(len(frontiers) == base["whole_offered_frontiers"], "offered frontier denominator changed")
    invalidated_messages = {record["job"]["job_id"]:record["cancellation"]["message"] for record in cancelled}
    invalidation_rows = observed_invalidations(jobs, results, invalidated_messages, accounting, events,
        owner_start=owner_start, dispatches=dispatches)
    # Use the same proof-derived windows for baseline and cancellation arms;
    # absence of a cancel request must not erase baseline interference.
    windows = [dict(request_id=next((request["request_id"] for request in requests if request.get("job_id") == row["job_id"]), None),
                    job_id=row["job_id"], session_id=row["session_id"],
                    invalidated_perf=row["invalidated_perf"], drained_perf=row["batch_drained_perf"])
               for row in invalidation_rows]
    effects = interference_windows(windows, specs, sessions, progress, certified, origin=origin, end_perf=end,
        fine_seconds=config["fine_seconds"], sample_rate=config["sample_rate"])
    return dict(status="PASS_INDEPENDENT_RETIREMENT_AND_INPUT_CONSUMER_AUDIT", episode=episode.name,
        policy=config.get("physical_retirement", {}), lifecycle=lifecycle, service=base,
        all_offered_frontiers=len(frontiers), accepted_unfulfilled_samples=0,
        interpretation="observed resource occupancy and Consumer progress; cross-arm comparison required for service benefit"), {
        "REQUESTS":requests, "BATCHES":batches, "OBSERVED_INVALIDATIONS":invalidation_rows,
        "FRONTIERS":frontiers, "SESSIONS":sessions, "INTERFERENCE":effects}


def write_tables(output, summary, tables):
    output.mkdir(parents=True, exist_ok=False)
    (output/"SUMMARY.json").write_text(json.dumps(summary, indent=2, allow_nan=False)+"\n", encoding="utf8")
    for name, rows in tables.items():
        (output/(name+".json")).write_text(json.dumps(rows, indent=2, allow_nan=False)+"\n", encoding="utf8")
        if rows:
            keys = list(dict.fromkeys(key for row in rows for key in row))
            with (output/(name+".csv")).open("w", newline="", encoding="utf8") as stream:
                writer = csv.DictWriter(stream, fieldnames=keys)
                writer.writeheader()
                writer.writerows(rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--episode", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    summary, tables = audit_episode(args.episode, service.read(args.manifest))
    write_tables(args.output, summary, tables)
    print(json.dumps(summary, allow_nan=False))


if __name__ == "__main__":
    main()

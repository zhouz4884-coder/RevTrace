"""Original full-call coordination with local delivery fences and bounded history.

Both serving arms use this coordinator and the same synchronous before_commit
hook.  The conservative scheduler chooses only canonical starts; the speculative
scheduler may also choose the legal conditional tail.  Neither changes C/U.
"""
from __future__ import annotations

from collections import deque
import re

from feedback_contract import FeedbackCut
from fullspec_policy import FullSpecCoordinator
from resilience_inbound import (
    IntegrityError, ResilientInbound, WritesFrozenError, audit_value, parse_job_id,
)


class CommitHookError(IntegrityError):
    """A durable outcome is uncertain; a fresh recovered Owner is required."""


class MonotonicIssuedJobs:
    """Never reissue an old ID without retaining the whole issued-ID set."""
    def __init__(self, epoch):
        self.epoch = epoch
        self.highwater = 0

    def __contains__(self, job_id):
        value = parse_job_id(job_id)
        return value is None or value[0] != self.epoch or value[1] <= self.highwater

    def add(self, job_id):
        value = parse_job_id(job_id)
        if value is None or value[0] != self.epoch or value[1] <= self.highwater:
            raise ValueError("job namespace or monotonic serial was reused")
        self.highwater = value[1]

    def __len__(self):
        return int(self.highwater > 0)


class BoundedAudit:
    """Complete records go to the sink; only a bounded recent window stays."""
    def __init__(self, kind, limit, sink, freeze):
        self.kind, self.sink, self.freeze = kind, sink, freeze
        self.recent = deque(maxlen=limit)
        self.total_count = 0

    def append(self, value):
        if self.sink is not None:
            try:
                self.sink(self.kind, audit_value(value))
            except Exception as exc:
                self.freeze("diagnostic_sink_failed")
                raise IntegrityError("diagnostic sink failed; Owner requires recovery") from exc
        self.total_count += 1
        self.recent.append(value)

    def __iter__(self):
        return iter(self.recent)

    def __len__(self):
        return len(self.recent)

    def __getitem__(self, index):
        return list(self.recent)[index]


class ResilientFullSpecCoordinator(FullSpecCoordinator):
    """The original strict full policy plus explicit delivery/lifecycle hooks.

    before_commit receives a pure dictionary with parent_state, next_state,
    full_record, and the unchanged owned job (including its frozen start).
    It must synchronously make the transition recoverable, then return a
    receipt containing transition_id, journal_seq, and record_sha.  The returned
    Canonical outcome carries that receipt as durable_receipt.

    receive_event is the ingress API for asr_early/completed/abandoned events.
    ready/failed/drained process-control messages remain Supervisor events.
    No local-drop return authorizes clearing a different or current busy job.
    """
    def __init__(self, *, owner_epoch, before_commit, worker_incarnations=None,
                 audit_sink=None, history_limit=64, **kwargs):
        if not callable(before_commit):
            raise ValueError("a synchronous durable-before-install hook is required")
        if type(owner_epoch) is not int or owner_epoch < 0 or history_limit < 1:
            raise ValueError("invalid owner namespace or history bound")
        super().__init__(**kwargs)
        self.owner_epoch = owner_epoch
        self.before_commit = before_commit
        self.writes_frozen = False
        self.frozen_reason = None
        self._pending_job_ids = set()
        self.history_limit = int(history_limit)
        self._seen_jobs = MonotonicIssuedJobs(owner_epoch)
        incs = worker_incarnations or {worker: 0 for worker in self.authorities}
        if set(incs) != self.authorities:
            raise ValueError("every Authority slot needs one physical incarnation")
        self.inbound = ResilientInbound(
            owner_epoch=owner_epoch, worker_incarnations=incs,
            session_epoch=lambda sid: self.epochs[sid],
            terminal_limit=self.history_limit,
        )
        self._audit_sink = audit_sink
        self._current_inbound_event = None
        sink = self._emit_audit if audit_sink is not None else None
        self.promotions = BoundedAudit("promotion", history_limit, sink, self._freeze)
        self.discarded_full = BoundedAudit("discarded_full", history_limit, sink, self._freeze)
        self.abandoned_full = BoundedAudit("abandoned_full", history_limit, sink, self._freeze)
        self.local_rejections = BoundedAudit("inbound_disposition", history_limit, sink, self._freeze)
        self.worker_losses = BoundedAudit("worker_lost", history_limit, sink, self._freeze)

    def _emit_audit(self, kind, value):
        payload = dict(value)
        if kind == "promotion":
            job = self.jobs.get(value["job_id"])
            if job is None:
                raise IntegrityError("promotion lost its actual owned job")
            payload["owned_job"] = audit_value(job)
            payload["actual_parent_state"] = self.canonical(job["source_id"]).state
        if kind == "abandoned_full" and self._current_inbound_event is not None:
            payload["worker_terminal_event"] = audit_value(self._current_inbound_event)
        self._audit_sink(kind, payload)

    def _freeze(self, reason):
        self.writes_frozen = True
        self.frozen_reason = str(reason)

    def _ensure_writes(self):
        if self.writes_frozen:
            raise WritesFrozenError(self.frozen_reason or "Owner writes are frozen")

    def register(self, *, worker_incarnation=None, **kwargs):
        self._ensure_writes()
        slot, job_id = kwargs["worker"], kwargs["job_id"]
        inc = self.inbound.worker_incarnations.get(slot)
        if worker_incarnation is None:
            worker_incarnation = inc
        if inc is None or worker_incarnation != inc:
            raise ValueError("dispatch requires its live physical incarnation")
        value = parse_job_id(job_id)
        if value is None or value[0] != self.owner_epoch or job_id in self._seen_jobs:
            raise ValueError("job ID must have a new monotonic owner serial")
        job = super().register(**kwargs)
        job["worker_incarnation"] = inc
        self.inbound.register(job, inc)
        return job

    def _commit(self, item):
        self._ensure_writes()
        job, sid = item["job"], item["job"]["source_id"]
        parent = self.canonical(sid)
        if job["dispatch_epoch"] != self.epochs[sid] or not job["start"].same(parent):
            self._freeze("unconfirmed_commit_parent")
            raise IntegrityError("unconfirmed full result cannot be journaled")
        transition = dict(
            kind="original_full_canonical_transition",
            owner_epoch=self.owner_epoch, source_id=sid,
            session_epoch=self.epochs[sid], parent_state=parent.state,
            parent_state_sha256=parent.sha256, next_state=item["cut"].state,
            next_state_sha256=item["cut"].sha256,
            full_record=audit_value(item["record"]), job=audit_value(job),
        )
        try:
            receipt = self.before_commit(transition)
            if (not isinstance(receipt, dict) or
                    not isinstance(receipt.get("transition_id"), str) or
                    not receipt["transition_id"] or
                    type(receipt.get("journal_seq")) is not int or
                    receipt["journal_seq"] < 0 or
                    not isinstance(receipt.get("record_sha"), str) or
                    re.fullmatch(r"[0-9a-f]{64}", receipt["record_sha"]) is None):
                raise ValueError("durable hook did not return its bound receipt")
            if not self.canonical(sid).same(parent) or job["dispatch_epoch"] != self.epochs[sid]:
                raise ValueError("durable hook changed the installed parent")
        except Exception as exc:
            self._freeze("durable_commit_outcome_uncertain")
            raise CommitHookError("before_commit failed; recover before further writes") from exc
        try:
            result = super()._commit(item)
        except Exception:
            self._freeze("durable_fact_not_fully_applied")
            raise
        result["durable_receipt"] = audit_value(receipt)
        return result

    def _sync_pins(self):
        pins = set(self._pending_job_ids)
        for owner in self.owners.values():
            pins.update(step.job_id for step in owner.steps)
        self.inbound.set_pins(pins)
        return pins

    def _validate_fenced_terminal(self, job, event):
        # A stale terminal may retire exactly its old physical lease only after
        # matching that dispatch; a spoof cannot clear a newer busy slot.
        if event["kind"] == "completed":
            start, end = FeedbackCut(event["start"]), FeedbackCut(event["end"])
            record = event["record"]
            if (not start.same(job["start"]) or end.frontier != job["end"] or
                    end.state["contract"] != start.state["contract"] or
                    record["start_state"] != start.sha256 or
                    record["end_state"] != end.sha256 or
                    record["candidate_handoff"] is not False or
                    record["role"] != "authority"):
                raise IntegrityError("fenced terminal changed its frozen full execution")
        else:
            self._validate_abandoned(job, event)

    def _validate_abandoned(self, job, event):
        if (not FeedbackCut(event["start"]).same(job["start"]) or
                event["target_end"] != job["end"] or
                event.get("asr_prefix_executed") is not True or
                event.get("learned_C_executed") is not False or
                event.get("C_U_completed") is not False or
                event.get("feedback_cut_emitted") is not False or
                event.get("actual_cache_decoder_cleared") is not True):
            raise IntegrityError("abandonment changed its input or asserted a partial result")

    def receive_event(self, slot, incarnation, event, *, received_perf):
        self._ensure_writes()
        self._sync_pins()
        self._current_inbound_event = event
        try:
            decision = self.inbound.classify(slot, incarnation, event)
            result = dict(disposition=decision.action, reason=decision.reason,
                          job_id=decision.job_id, physical_terminal=False)
            if decision.action == "retire_fenced_terminal":
                job = self.jobs[event["job_id"]]
                self._validate_fenced_terminal(job, event)
                del self.jobs[job["job_id"]]
                self._refresh_active()
                self.inbound.retire_fenced_terminal(event)
                result.update(physical_terminal=True,
                              outcome=dict(kind="fenced_terminal", job=job,
                                           certified_output=False))
                self.local_rejections.append(dict(result, event=event))
                return result
            if decision.action != "accept":
                self.local_rejections.append(dict(result, event=event))
                return result
            kind = event["kind"]
            if kind == "asr_early":
                outcome = super().admit_asr(slot, event, received_perf=received_perf)
            elif kind == "completed":
                outcome = super().complete(slot, event, received_perf=received_perf)
            else:
                job = self.jobs[event["job_id"]]
                self._validate_abandoned(job, event)
                outcome = super().abandon(slot, event["job_id"], event["proof"])
            terminal = kind in self.inbound.TERMINALS
            self.inbound.accept(event, terminal=terminal)
            result.update(physical_terminal=terminal, outcome=outcome)
            return result
        except CommitHookError:
            raise
        except (IntegrityError, ValueError, KeyError, TypeError, OverflowError) as exc:
            self._freeze("current_owned_message_integrity_failure")
            if isinstance(exc, IntegrityError):
                raise
            raise IntegrityError("strict current-owned message validation failed") from exc
        finally:
            self._current_inbound_event = None

    def pop_ready_commits(self):
        self._ensure_writes()
        return super().pop_ready_commits()

    def next_full_start(self, *args, **kwargs):
        self._ensure_writes()
        return super().next_full_start(*args, **kwargs)

    def worker_lost(self, slot, incarnation, death_proof):
        """Release live jobs only after Supervisor confirms real OS exit.

        A worker death does not invalidate a previously accepted complete
        result, a typed ASR view, or its immutable execution identity.
        """
        if (not isinstance(death_proof, dict) or
                death_proof.get("confirmed_exit") is not True or
                death_proof.get("slot") != slot or
                death_proof.get("incarnation") != incarnation or
                type(death_proof.get("pid")) is not int or
                death_proof["pid"] <= 0 or
                type(death_proof.get("exitcode")) is not int):
            raise ValueError("physical exit must be confirmed for this incarnation")
        if self.inbound.worker_incarnations.get(slot) != incarnation:
            raise ValueError("foreign or already released worker incarnation")
        before = {sid: r.canonical.sha256 for sid, r in self.owners.items()}
        self._sync_pins()
        retired = self.inbound.lose_worker(slot, incarnation)
        for job_id in retired:
            job = self.jobs.get(job_id)
            if job is None or job["worker"] != slot or job["worker_incarnation"] != incarnation:
                self._freeze("physical_ownership_registry_disagrees")
                raise IntegrityError("inbox and coordinator ownership disagree")
            del self.jobs[job_id]
            self._issued_proofs.pop(job_id, None)
        self._refresh_active()
        event = dict(
            slot=slot, incarnation=incarnation, death_proof=death_proof,
            retired_live_jobs=retired,
            preserved_completed_jobs=[j for j, item in self.completed_full.items()
                                      if item["job"]["worker"] == slot and
                                      item["job"].get("worker_incarnation") == incarnation],
            retained_view_jobs=[step.job_id for r in self.owners.values() for step in r.steps],
            canonical_shas=before, physical_ownership_released=True,
            input_obligations_changed=False,
        )
        if before != {sid: r.canonical.sha256 for sid, r in self.owners.items()}:
            self._freeze("worker_death_changed_Canonical")
            raise IntegrityError("worker death cannot change Canonical facts")
        self.worker_losses.append(event)
        return event

    def replace_worker(self, slot, new_incarnation):
        self.inbound.replace_worker(slot, new_incarnation)

    def collect_history(self, pending_job_ids=()):
        """Retain actual live/view/outbox dependencies, not every old state.

        pending_job_ids must include the external Consumer/outbox references
        not yet released by its actual application receipt.
        """
        self._ensure_writes()
        self._pending_job_ids = set(pending_job_ids)
        keep = self._sync_pins() | set(self.jobs) | set(self.completed_full)
        for mapping in (self.nodes, self.projections):
            for job_id in list(mapping):
                if job_id not in keep:
                    del mapping[job_id]
        for job_id in list(self._issued_proofs):
            if job_id not in self.jobs:
                del self._issued_proofs[job_id]
        for sid, epochs in self._canonical_witnesses.items():
            current_epoch = self.epochs[sid]
            needed = {self.canonical(sid).frontier}
            for job in self.jobs.values():
                if job["source_id"] == sid and job["dispatch_epoch"] == current_epoch:
                    needed.add(job["start"].frontier)
            for item in self.completed_full.values():
                job = item["job"]
                if job["source_id"] == sid and job["dispatch_epoch"] == current_epoch:
                    needed.add(job["start"].frontier)
            for step in self.owners[sid].steps:
                needed.update((step.start.frontier, step.end.frontier))
            # Frozen dependency chains themselves are immutable job fields.
            # Only their exact start frontier can authorize a same-F rejection.
            for epoch in list(epochs):
                if epoch != current_epoch:
                    del epochs[epoch]
            for frontier in list(epochs[current_epoch]):
                if frontier not in needed:
                    del epochs[current_epoch][frontier]
        return self.history_stats()

    def history_stats(self):
        audits = dict(promotions=self.promotions, discarded_full=self.discarded_full,
                      abandoned_full=self.abandoned_full,
                      inbound_dispositions=self.local_rejections,
                      worker_losses=self.worker_losses)
        return dict(
            live_jobs=len(self.jobs), completed_full=len(self.completed_full),
            branch_steps=sum(len(r.steps) for r in self.owners.values()),
            canonical_witnesses=sum(len(cuts) for epochs in self._canonical_witnesses.values()
                                    for cuts in epochs.values()),
            nodes=len(self.nodes), projections=len(self.projections),
            issued_proofs=len(self._issued_proofs),
            issued_id_memory_entries=len(self._seen_jobs),
            issued_highwater=self._seen_jobs.highwater,
            pending_job_refs=len(self._pending_job_ids),
            inbox=self.inbound.stats(),
            audit_retained={key: len(value) for key, value in audits.items()},
            audit_total={key: value.total_count for key, value in audits.items()},
            history_limit=self.history_limit, writes_frozen=self.writes_frozen,
            bound_scope="protocol entries relative to live/view/outbox references; current task state and cumulative output may themselves grow",
        )

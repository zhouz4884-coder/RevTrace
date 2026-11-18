"""Bounded delivery deduplication with owner and physical-incarnation fences.

This module never grants Canonical authority.  ACCEPT only permits the original
strict coordinator validation to run.  A local rejection cannot release a live
physical lease.  The caller supplies incarnation from its bound channel, not
from the message being checked.
"""
from __future__ import annotations

from collections import Counter, OrderedDict
from dataclasses import asdict, dataclass
import hashlib
import json
import re


class IntegrityError(RuntimeError):
    """A message contradicts one currently owned execution or its receipt."""


class WritesFrozenError(RuntimeError):
    """Owner state requires recovery; further transitions are disabled."""


def audit_value(value):
    """Make full immutable diagnostic objects streamable without raw packets."""
    from feedback_contract import FeedbackCut
    if isinstance(value, FeedbackCut):
        return value.state
    if isinstance(value, bytes):
        return {"byte_length": len(value), "sha256": hashlib.sha256(value).hexdigest()}
    if isinstance(value, dict):
        return {str(k): audit_value(v) for k, v in value.items()}
    if isinstance(value, (tuple, list)):
        return [audit_value(v) for v in value]
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    raise TypeError("unsupported diagnostic object: " + type(value).__name__)


_TRANSPORT_FIELDS = frozenset((
    "received_perf", "received_owner_perf", "physical_channel_worker",
    "channel_incarnation", "sent_perf", "wire_complete_perf",
))


def semantic_fingerprint(event):
    body = {k: v for k, v in event.items() if k not in _TRANSPORT_FIELDS}
    wire = json.dumps(audit_value(body), sort_keys=True, ensure_ascii=False,
                      separators=(",", ":"), allow_nan=False).encode("utf8")
    return hashlib.sha256(wire).hexdigest()


def parse_job_id(job_id):
    if not isinstance(job_id, str):
        return None
    match = re.fullmatch(r"e(0|[1-9][0-9]*)-j([0-9]{9})", job_id)
    if not match:
        return None
    epoch, serial = map(int, match.groups())
    return (epoch, serial) if serial > 0 else None


@dataclass(frozen=True)
class InboundDisposition:
    action: str
    reason: str
    job_id: str | None
    physical_terminal: bool = False

    def as_dict(self):
        return asdict(self)


class ResilientInbound:
    """A bounded inbox ledger; strict result/state checks remain downstream."""

    PHASES = frozenset(("asr_early", "completed", "abandoned"))
    TERMINALS = frozenset(("completed", "abandoned"))

    def __init__(self, *, owner_epoch, worker_incarnations, session_epoch,
                 terminal_limit=64):
        if type(owner_epoch) is not int or owner_epoch < 0 or terminal_limit < 1:
            raise ValueError("invalid owner epoch or inbox bound")
        self.owner_epoch = owner_epoch
        self.worker_incarnations = dict(worker_incarnations)
        self.last_incarnations = dict(worker_incarnations)
        if any(type(v) is not int or v < 0 for v in worker_incarnations.values()):
            raise ValueError("invalid initial worker incarnation")
        self.session_epoch = session_epoch
        self.terminal_limit = int(terminal_limit)
        self.active = {}
        self.terminal = OrderedDict()
        self.pins = set()
        self.issued_highwater = 0
        self.counters = Counter()

    def register(self, job, incarnation):
        parsed = parse_job_id(job["job_id"])
        if parsed is None or parsed[0] != self.owner_epoch:
            raise ValueError("job does not belong to this owner namespace")
        if parsed[1] <= self.issued_highwater:
            raise ValueError("issued job serial cannot be reused or decrease")
        if self.worker_incarnations.get(job["worker"]) != incarnation:
            raise ValueError("dispatch requires the live physical incarnation")
        self.issued_highwater = parsed[1]
        self.active[job["job_id"]] = dict(
            worker=job["worker"], incarnation=incarnation,
            source_id=job["source_id"], dispatch_epoch=job["dispatch_epoch"],
            start_sha=job["start"].sha256, target_end=job["end"], seen={},
        )

    def _decision(self, action, reason, job_id, physical_terminal=False):
        self.counters[action] += 1
        return InboundDisposition(action, reason, job_id, physical_terminal)

    def classify(self, slot, incarnation, event):
        """Classify without changing ownership, state, or accepted phases."""
        if not isinstance(event, dict):
            return self._decision("reject_envelope", "event_is_not_an_object", None)
        job_id, kind = event.get("job_id"), event.get("kind")
        if self.worker_incarnations.get(slot) != incarnation:
            return self._decision("ignore_fenced", "retired_physical_channel", job_id)
        if event.get("worker") != slot:
            return self._decision("reject_envelope", "foreign_worker_envelope", job_id)
        claimed = event.get("worker_incarnation")
        if claimed != incarnation:
            reason = "retired_incarnation_envelope" if (
                type(claimed) is int and claimed < incarnation
            ) else "unbound_incarnation_envelope"
            return self._decision("ignore_fenced" if reason.startswith("retired")
                                  else "reject_envelope", reason, job_id)
        parsed = parse_job_id(job_id)
        if parsed is not None and parsed[0] != self.owner_epoch:
            return self._decision("ignore_fenced", "different_owner_epoch", job_id)
        descriptor = self.active.get(job_id) or self.terminal.get(job_id)
        if descriptor is None:
            retired = parsed is not None and parsed[1] <= self.issued_highwater
            return self._decision("ignore_retired" if retired else "reject_unknown",
                                  "no_live_authority_for_job", job_id)
        if descriptor["worker"] != slot or descriptor["incarnation"] != incarnation:
            return self._decision("reject_envelope", "foreign_job_channel", job_id)
        if (event.get("source_id") != descriptor["source_id"] or
                event.get("dispatch_epoch") != descriptor["dispatch_epoch"]):
            raise IntegrityError("current owned job changed source or session epoch")
        if kind not in self.PHASES:
            return self._decision("reject_envelope", "unexpected_job_phase", job_id)
        try:
            fingerprint = semantic_fingerprint(event)
        except (TypeError, ValueError, OverflowError) as exc:
            raise IntegrityError("current owned payload cannot be encoded") from exc
        previous = descriptor["seen"].get(kind)
        if previous is not None:
            if previous != fingerprint:
                raise IntegrityError("same job phase carries contradictory contents")
            return self._decision("ignore_duplicate", "same_semantic_receipt", job_id)
        if job_id in self.terminal:
            # A delayed early ASR publication after its complete terminal is
            # harmless.  A second, different terminal contradicts that receipt.
            if kind in self.TERMINALS and descriptor["terminal_phase"] in self.TERMINALS:
                raise IntegrityError("one execution reported two terminal outcomes")
            return self._decision("ignore_retired", "late_phase_after_retirement", job_id)
        if descriptor["dispatch_epoch"] != self.session_epoch(descriptor["source_id"]):
            return self._decision("retire_fenced_terminal" if kind in self.TERMINALS
                                  else "ignore_fenced", "old_session_epoch", job_id,
                                  kind in self.TERMINALS)
        return self._decision("accept", "live_owned_phase", job_id)

    def accept(self, event, *, terminal=False):
        """Called only after all original payload checks succeeded."""
        job_id = event["job_id"]
        descriptor = self.active[job_id]
        descriptor["seen"][event["kind"]] = semantic_fingerprint(event)
        if terminal:
            self._retire(job_id, event["kind"])

    def retire_fenced_terminal(self, event):
        descriptor = self.active[event["job_id"]]
        descriptor["seen"][event["kind"]] = semantic_fingerprint(event)
        self._retire(event["job_id"], "fenced")

    def _retire(self, job_id, phase):
        descriptor = self.active.pop(job_id)
        descriptor["terminal_phase"] = phase
        self.terminal[job_id] = descriptor
        self.terminal.move_to_end(job_id)
        self._trim()

    def _trim(self):
        # Live-view/outbox references are a separate active dependency bound.
        # The diagnostic LRU bound applies to unreferenced terminal receipts.
        unpinned = [job for job in self.terminal if job not in self.pins]
        for job in unpinned[:-self.terminal_limit]:
            del self.terminal[job]

    def set_pins(self, job_ids):
        self.pins = set(job_ids)
        self._trim()

    def lose_worker(self, slot, incarnation):
        if self.worker_incarnations.get(slot) != incarnation:
            raise ValueError("cannot lose an already retired or foreign incarnation")
        lost = [job for job, d in self.active.items()
                if d["worker"] == slot and d["incarnation"] == incarnation]
        for job in lost:
            self._retire(job, "worker_lost")
        self.worker_incarnations[slot] = None
        self.counters["worker_incarnations_lost"] += 1
        return lost

    def replace_worker(self, slot, incarnation):
        if slot not in self.last_incarnations:
            raise ValueError("unknown physical worker slot")
        if self.worker_incarnations[slot] is not None:
            raise ValueError("old physical incarnation is not retired")
        if type(incarnation) is not int or incarnation <= self.last_incarnations[slot]:
            raise ValueError("worker incarnation must strictly increase")
        self.worker_incarnations[slot] = incarnation
        self.last_incarnations[slot] = incarnation

    def stats(self):
        return dict(active=len(self.active), terminal=len(self.terminal),
                    terminal_limit=self.terminal_limit,
                    pinned_terminals=sum(job in self.pins for job in self.terminal),
                    issued_highwater=self.issued_highwater,
                    worker_slots=len(self.worker_incarnations),
                    counters=dict(self.counters))

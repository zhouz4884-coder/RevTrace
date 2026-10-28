"""Host startup observations; no cached text or inference authorization.

Absolute perf_counter timestamps share the owner's monotonic clock.  The
external fault driver, rather than this module, supplies the kill timestamp.
All comparable initialization paths use the same instrumentation.
"""
from __future__ import annotations

from contextlib import contextmanager
import json
from pathlib import Path
import threading
import time


class RecoveryProfile:
    def __init__(self, path, *, process_entry_perf, processor_mode, clock=time.perf_counter):
        if processor_mode not in {"legacy_double", "reuse"}:
            raise ValueError("unknown startup processor mode")
        self.path = Path(path)
        self.clock = clock
        self.entry = float(process_entry_perf)
        self.processor_mode = processor_mode
        self.lock = threading.RLock()
        self.records = []
        self.active = {}
        self.counter = 0
        self.observations = []
        self.targets = None
        self.crossings = {}
        self.done_observing = False
        self.write_seconds = 0.0
        self.mark("profile-attached", process_entry_perf=self.entry,
                  startup_processor_mode=processor_mode,
                  durability="observational flushed JSONL; not fsync or a receipt")

    def _append(self, row):
        started = self.clock()
        with self.path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(row, sort_keys=True, allow_nan=False) + "\n")
            stream.flush()
        self.write_seconds += max(0.0, self.clock() - started)
        self.records.append(row)

    def mark(self, stage, *, observed_perf=None, **fields):
        with self.lock:
            at = self.clock() if observed_perf is None else float(observed_perf)
            self._append(dict(kind="startup-mark", stage=stage, observed_perf=at,
                              since_process_entry_seconds=at-self.entry, **fields))

    def begin(self, stage, **fields):
        with self.lock:
            self.counter += 1
            token = self.counter
            start = self.clock()
            self.active[token] = (stage, start)
            self._append(dict(kind="startup-span-begin", token=token, stage=stage,
                              observed_perf=start, **fields))
            return token

    def end(self, token, *, error_type=None, **fields):
        with self.lock:
            stage, start = self.active.pop(token)
            end = self.clock()
            self._append(dict(kind="startup-span-end", token=token, stage=stage,
                              started_perf=start, observed_perf=end,
                              elapsed_seconds=end-start, error_type=error_type, **fields))

    @contextmanager
    def span(self, stage, **fields):
        token = self.begin(stage, **fields)
        try:
            yield
        except BaseException as exc:
            self.end(token, error_type=type(exc).__name__)
            raise
        else:
            self.end(token)

    def configure_recovery(self, *, recovered_frontiers, accepted_frontiers,
                           owner_incarnation, original_origin_perf):
        """Register validated ledger facts without delaying their publication.

        The Consumer may already have applied the queued recovery publication.
        Its real timestamp was retained by observe_consumer and is reused.
        """
        F = {int(s): int(v) for s, v in recovered_frontiers.items()}
        A = {int(s): int(v) for s, v in accepted_frontiers.items()}
        if set(F) != set(A) or any(not 0 <= F[s] <= A[s] for s in F):
            raise ValueError("invalid recovered certified/accepted frontiers")
        with self.lock:
            if self.targets is not None:
                raise ValueError("recovery targets are immutable")
            self.targets = dict(F=F, A=A, owner=float(owner_incarnation),
                                origin=float(original_origin_perf))
            self.old_seen = {s: None for s, value in F.items() if value > 0}
            self.debt_seen = {s: None for s, value in A.items() if value > F[s]}
            self.expected_crossings = {"first-new-fact-consumed"}
            if self.old_seen:
                self.expected_crossings.add("all-old-facts-consumed")
            if self.debt_seen:
                self.expected_crossings.add("precrash-accepted-debt-consumed")
            self.mark("validated-recovery-targets", certified=F, accepted=A,
                      owner_incarnation=float(owner_incarnation),
                      original_origin_perf=float(original_origin_perf))
            pending, self.observations = self.observations, []
            for row in pending:
                self._accept_observation(row)

    def observe_consumer(self, row):
        """Call only after actual Consumer application, never at queue insertion."""
        with self.lock:
            if self.done_observing:
                return
            selected = {k: row[k] for k in
                ("session_id", "certified_frontier", "observed_perf", "owner_incarnation")}
            if self.targets is None:
                self.observations.append(selected)
            else:
                self._accept_observation(selected)

    def _accept_observation(self, row):
        t = self.targets
        if row["owner_incarnation"] != t["owner"] or int(row["session_id"]) not in t["F"]:
            return
        old, debt = self.old_seen, self.debt_seen
        s, at, frontier = int(row["session_id"]), float(row["observed_perf"]), int(row["certified_frontier"])
        if s in old and frontier >= t["F"][s]:
            old[s] = at if old[s] is None else min(old[s], at)
        if s in debt and frontier >= t["A"][s]:
            debt[s] = at if debt[s] is None else min(debt[s], at)
        candidates = {}
        if old and all(v is not None for v in old.values()):
            candidates["all-old-facts-consumed"] = max(old.values())
        if frontier > t["F"][s]:
            candidates["first-new-fact-consumed"] = at
        if debt and all(v is not None for v in debt.values()):
            candidates["precrash-accepted-debt-consumed"] = max(debt.values())
        for key, at in candidates.items():
            if key not in self.crossings:
                self.crossings[key] = at
                self.mark(key, observed_perf=at, original_origin_perf=t["origin"])
        self.done_observing = self.expected_crossings.issubset(self.crossings)

    def summary(self):
        with self.lock:
            targets = self.targets
            return dict(schema="trusted-recovery-profile-v1", process_entry_perf=self.entry,
                startup_processor_mode=self.processor_mode, clock="host monotonic perf_counter",
                targets=targets, applied_crossings_perf=dict(self.crossings),
                has_old_facts=bool(targets and any(targets["F"].values())),
                has_precrash_debt=bool(targets and any(targets["A"][s] > F for s, F in targets["F"].items())),
                open_spans=[dict(token=k, stage=v[0], started_perf=v[1]) for k, v in self.active.items()],
                profile_write_wall_seconds=self.write_seconds,
                scope="host/actual local Consumer observations; external kill timestamp required for RTO")


def recovery_processor(initial_processor, *, mode, load_processor, profile=None):
    """Only startup object reuse changes; both arms execute the same renderer."""
    if mode not in {"legacy_double", "reuse"}:
        raise ValueError("unknown startup processor mode")
    if initial_processor is None:
        raise ValueError("first identity-pinned processor is required")
    if profile is None:
        return initial_processor if mode == "reuse" else load_processor()
    with profile.span("trusted-render-processor", processor_mode=mode):
        return initial_processor if mode == "reuse" else load_processor()

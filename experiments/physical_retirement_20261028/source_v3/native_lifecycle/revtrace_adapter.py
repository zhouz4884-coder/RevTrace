"""Actual composed-kernel adapter for the independent native application DB.

Recovery reads every actual durable admission, its owned selection, requests and
input journal. It restores the last real C/D/I fact; only a genuinely empty DB
uses genesis. Host/provider wrappers and storage are trusted by this contract.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import time

from native_store import canonical, digest
from revtrace import composed_kernel
from revtrace.composed_kernel import Kernel, sha


def text_hash(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


class NativeKernelAdapter:
    def __init__(self, store, proposal):
        self.store, self.proposal = store, proposal
        self.k = None
        self.events = []
        self.prepared = None
        self.kernel_sha = hashlib.sha256(Path(composed_kernel.__file__).read_bytes()).hexdigest()

    def event(self, boundary, kind, op, payload):
        payload = {**payload, "epoch": self.k.state.epoch,
                   "owner": self.k.state.owner, "contract": self.k.state.contract}
        effects = self.k.event(boundary, kind, op, payload)
        self.events.append({"boundary": boundary, "kind": kind, "operation": op,
                            "payload": payload, "effects": effects, "observed_ns": time.time_ns()})
        return effects

    def recover(self, db):
        conf = {r["k"]: json.loads(r["payload"]) for r in db.execute("SELECT * FROM config")}
        meta = dict(db.execute("SELECT epoch,head,origin FROM meta").fetchone())
        contract = sha({"adapter": "native-two-family-input-journal-v1", "family": conf["task"]["family"],
                        "provider_identity": conf["provider_identity"], "kernel_sha256": self.kernel_sha})
        facts = {}
        values = {}
        rows = list(db.execute("SELECT * FROM admissions ORDER BY seq"))
        assert [r["seq"] for r in rows] == list(range(meta["head"] + 1)), "durable admission history incomplete"
        for r in rows:
            receipt, value = json.loads(r["receipt"]), json.loads(r["payload"])
            assert receipt["value"] == value
            v = r["seq"]
            values[v] = value
            if v == 0:
                fact = {"v": 0, "F": 0, "P": sha(value), "Z": "", "textsha": text_hash(value), "txn": ""}
            else:
                owned = db.execute("SELECT op,evidence FROM selections WHERE id=?", (receipt["selection_id"],)).fetchone()
                frozen_row = db.execute("SELECT frozen FROM requests WHERE op=?", (receipt["op"],)).fetchone()
                assert owned is not None and frozen_row is not None
                ev, frozen = json.loads(owned["evidence"]), json.loads(frozen_row["frozen"])
                assert owned["op"] == receipt["op"] and ev["selection_authorized"]
                assert ev["complete"] and ev["terminated_by_eos"] and ev["physical_worker_drained"]
                assert ev["value"] == value and json.loads(ev["rendered_text"]) == value
                assert ev["request"]["frozen_request_hash"] == frozen["request_hash"] == receipt["request_hash"]
                assert receipt["parent"] == v - 1 and receipt["frontier"] > 0
                assert receipt["kernel"]["contract"] == contract and receipt["kernel"]["source_sha256"] == self.kernel_sha
                fact = {"v": v, "F": receipt["frontier"], "P": sha(value), "Z": sha(ev["tokens"]),
                        "textsha": text_hash(value), "txn": receipt["op"]}
                assert receipt["kernel"]["fact"] == fact
                prior_f = 0 if v == 1 else facts[v - 1]["F"]
                assert fact["F"] > prior_f
            if v:
                facts[v] = fact
            else:
                genesis = fact
        current = facts[meta["head"]] if meta["head"] else genesis
        self.k = Kernel(contract, meta["epoch"], float(meta["epoch"]))
        self.event("validated-full-sqlite-history", "recover-fact", "recover",
                   {"sid": 0, "fact": current, "history": facts})
        accepted = [dict(r) for r in db.execute("SELECT * FROM accepted_inputs ORDER BY seq")]
        assert [r["seq"] for r in accepted] == list(range(1, len(accepted) + 1))
        sources = dict(db.execute("SELECT k,version FROM sources"))
        items = {0: {"accepted": len(accepted), "offered": len(accepted), "reserved": len(accepted),
                     "prefix": digest(accepted), "origin": meta["origin"], "sources": sources}}
        self.event("actual-durable-input-journal", "input-synced", "inputs", {"items": items, "recovery": True})
        if current["v"]:
            self.apply_current(db, current, values[current["v"]], "recovered")
        self.event("owned-complete-selection-provider", "worker-ready", "a", {"worker": "a"})
        self.recovery = {"restored_version": current["v"], "restored_frontier": current["F"],
                         "history_entries": len(facts), "accepted_input_records": len(accepted),
                         "epoch": meta["epoch"], "used_genesis": meta["head"] == 0}

    def apply_current(self, db, fact, value, label):
        # The consumer observes the actual application row while the caller's SQL
        # transaction is active. A hash-only cached string is not used here.
        row = db.execute("SELECT payload,receipt FROM admissions WHERE seq=?", (fact["v"],)).fetchone()
        assert row is not None and json.loads(row["payload"]) == value
        receipt = json.loads(row["receipt"])
        assert receipt["frontier"] == fact["F"]
        key = label + ":" + str(fact["v"])
        self.event("durable-native-publication", "publish", key,
                   {"sid": 0, "key": key, "publication": {"canonical": True, "fact": fact}})
        view = {"v": fact["v"], "F": fact["F"], "P": fact["P"], "visible": fact["F"],
                "text": canonical(value), "revision": fact["v"], "private": None}
        op = "consumer:" + key
        self.event("actual-sqlite-consumer-prepare", "apply-request", op,
                   {"sid": 0, "key": key, "operation": op, "view": view})
        observed = json.loads(db.execute("SELECT payload FROM admissions WHERE seq=?", (fact["v"],)).fetchone()[0])
        assert observed == value
        self.event("actual-sqlite-consumer-read", "view-applied", op, {"operation": op})

    def authorize(self, *, frozen, selection, history, observed, source_versions, db):
        self.recover(db)
        c = self.k.state.C[0]
        assert c["v"] == observed["head"] == frozen["parent"]
        assert self.k.state.epoch == observed["epoch"] == frozen["epoch"]
        assert frozen["readset"] == source_versions
        assert selection["selection_authorized"] and selection["physical_worker_drained"]
        assert selection["actual_input_ids"] == selection["request"]["input_ids"]
        identity = sha({"input_ids": selection["actual_input_ids"], "contract": selection["contract"],
                        "frozen_request_hash": frozen["request_hash"]})
        jid = frozen["op"]
        job = {"id": jid, "sid": 0, "role": "authority", "parent": c["v"], "start": c["F"],
               "end": frozen["accepted_frontier"], "rootF": c["F"], "inputP": c["P"],
               "readset": frozen["readset"], "identity": identity}
        executions = [json.loads(r[0]) for r in db.execute("SELECT payload FROM events WHERE kind='kernel-live-execution'")]
        matches = [x for x in executions if x["op"] == jid and x["complete"]]
        assert len(matches) == 1, "missing/ambiguous actual pre-execution kernel lifecycle"
        live = matches[0]
        assert live["job"] == job
        assert live["result"] == {"P": sha(selection["value"]), "Z": sha(selection["tokens"]),
                                  "textsha": text_hash(selection["value"])}
        # Reconstruct the old process's already executed dispatch/completion from
        # its actual persisted records. These are replay steps, not new GPU work.
        for old in live["execution_events"]:
            self.event("replay-owned-native-execution:" + old["boundary"], old["kind"], old["operation"], old["payload"])
        fact = {"v": c["v"] + 1, "F": frozen["accepted_frontier"], "P": sha(selection["value"]),
                "Z": sha(selection["tokens"]), "textsha": text_hash(selection["value"]), "txn": jid}
        self.prepared = {"job": job, "fact": fact, "value": selection["value"], "operation": "wal:" + jid}
        self.event("before-actual-application-transaction", "admission-request", self.prepared["operation"],
                   {"sid": 0, "job": jid, "operation": self.prepared["operation"], "fact": fact})

    def prepared_attachment(self):
        assert self.prepared is not None
        return {"contract": self.k.state.contract, "source_sha256": self.kernel_sha,
                "fact": self.prepared["fact"], "recovery": self.recovery}

    def finalize(self, *, receipt, application_db):
        assert Path(application_db) == self.store.path
        p = self.prepared
        assert receipt["kernel"]["fact"] == p["fact"]
        self.event("actual-sqlite-full-commit-returned", "canonical-synced", p["operation"], {"operation": p["operation"]})
        self.event("actual-owner-install", "install", p["operation"], {"sid": 0, "fact": p["fact"]})
        with self.store.db() as db:
            self.apply_current(db, p["fact"], p["value"], "new")
        self.store.record("kernel-operation-complete", self.export_trace())

    def restore_for_replay(self, *, db, original_result):
        self.recover(db)
        receipt = original_result["receipt"]
        actual = db.execute("SELECT receipt FROM admissions WHERE op=?", (receipt["op"],)).fetchone()
        assert actual is not None and json.loads(actual[0]) == receipt
        # Receipt replay leaves the currently recovered head intact. The old
        # receipt is evidence of its historical effect, not a new installation.
        assert self.k.state.C[0]["v"] >= receipt["seq"]

    def export_trace(self):
        return {"actual_kernel_source_sha256": self.kernel_sha, "recovery": self.recovery,
                "events": self.events, "installed_version": self.k.state.C[0]["v"],
                "consumer_version": self.k.state.V[0]["v"],
                "scope": "native SQLite lifecycle using actual composed kernel; no claim of ASR Private path coverage"}


def create_adapter(store, proposal):
    return NativeKernelAdapter(store, proposal)


class NativeExecutionAdapter(NativeKernelAdapter):
    def __init__(self, store, frozen, request):
        super().__init__(store, None)
        self.frozen, self.request = frozen, request

    def dispatch_before_execution(self):
        with self.store.db(True) as db:
            self.recover(db)
            c = self.k.state.C[0]
            identity = sha({"input_ids": self.request["input_ids"], "contract": self.request["contract"],
                            "frozen_request_hash": self.frozen["request_hash"]})
            self.job = {"id": self.frozen["op"], "sid": 0, "role": "authority", "parent": self.frozen["parent"],
                        "start": c["F"], "end": self.frozen["accepted_frontier"], "rootF": c["F"],
                        "inputP": sha(self.frozen["prior_memory"]), "readset": self.frozen["readset"], "identity": identity}
            self.execution_start = len(self.events)
            self.event("before-actual-native-provider-call", "dispatch", self.frozen["op"], {"worker": "a", "jobs": [self.job]})
            self.store.event(db, "kernel-before-execution", {"op": self.frozen["op"], "job": self.job,
                "recovery": self.recovery, "events": self.events})

    def complete_after_execution(self, selected):
        assert selected["selection_authorized"] and selected["physical_worker_drained"]
        assert selected["request"] == self.request and selected["actual_input_ids"] == self.request["input_ids"]
        result = {"P": sha(selected["value"]), "Z": sha(selected["tokens"]), "textsha": text_hash(selected["value"])}
        self.event("after-actual-native-provider-selection", "row-complete", self.frozen["op"],
                   {"id": self.job["id"], "worker": "a", "identity": self.job["identity"], **result})
        self.event("after-actual-native-provider-physical-drain", "batch-drained", self.frozen["op"], {"worker": "a"})
        self.store.record("kernel-live-execution", {"op": self.frozen["op"], "complete": True, "job": self.job,
            "result": result, "execution_events": self.events[self.execution_start:],
            "actual_started_ns": selected["started_ns"], "actual_completed_ns": selected["completed_ns"]})

    def retain_execution_failure(self, evidence):
        self.event("actual-provider-failure-retain-debt", "execution-failed", self.frozen["op"], {"worker": "a"})
        self.store.record("kernel-live-execution", {"op": self.frozen["op"], "complete": False, "job": self.job,
            "execution_events": self.events[self.execution_start:], "failure": evidence})


def create_execution_adapter(store, frozen, request):
    return NativeExecutionAdapter(store, frozen, request)

"""Persistent application state, separate from LangGraph's checkpoints.

Trusted host/provider wrappers own selection registration. SQLite checksums are
bindings, not a defense against a malicious trusted host or corrupted storage.
"""
from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
import hashlib
import json
import os
import sqlite3
import time

from tasks import canonical, validate_schema


def digest(x):
    return hashlib.sha256(canonical(x).encode()).hexdigest()


class Store:
    def __init__(self, directory):
        self.directory = Path(directory)
        self.path = self.directory / "application.sqlite"

    @contextmanager
    def db(self, write=False):
        db = sqlite3.connect(self.path, timeout=30)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA journal_mode=WAL")
        db.execute("PRAGMA synchronous=FULL")
        try:
            db.execute("BEGIN IMMEDIATE" if write else "BEGIN")
            yield db
            db.commit()
        except BaseException:
            db.rollback()
            raise
        finally:
            db.close()

    @staticmethod
    def event(db, kind, payload):
        db.execute("INSERT INTO events(kind,payload,pid,wall_ns,mono_ns) VALUES(?,?,?,?,?)",
                   (kind, canonical(payload), os.getpid(), time.time_ns(), time.monotonic_ns()))

    def initialize(self, task, provider_identity, evidence_tier):
        assert not self.path.exists(), "new experiment directory required"
        self.directory.mkdir(parents=True, exist_ok=True)
        with self.db(True) as db:
            db.executescript("""
              CREATE TABLE meta(id INTEGER PRIMARY KEY, epoch INTEGER, head INTEGER, origin REAL);
              CREATE TABLE config(k TEXT PRIMARY KEY, payload TEXT);
              CREATE TABLE sources(k TEXT PRIMARY KEY, version INTEGER, payload TEXT);
              CREATE TABLE requests(op TEXT PRIMARY KEY, request_hash TEXT, frozen TEXT);
              CREATE TABLE accepted_inputs(seq INTEGER PRIMARY KEY, kind TEXT, op TEXT, payload TEXT);
              CREATE TABLE selections(id TEXT PRIMARY KEY, op TEXT, evidence TEXT);
              CREATE TABLE admissions(seq INTEGER PRIMARY KEY, op TEXT UNIQUE, payload TEXT, receipt TEXT);
              CREATE TABLE operations(op TEXT PRIMARY KEY, request_hash TEXT, result TEXT);
              CREATE TABLE outbox(event_id TEXT PRIMARY KEY, seq INTEGER, receipt TEXT);
              CREATE TABLE receiver(event_id TEXT PRIMARY KEY, seq INTEGER, receipt TEXT);
              CREATE TABLE events(n INTEGER PRIMARY KEY AUTOINCREMENT, kind TEXT, payload TEXT,
                                  pid INTEGER, wall_ns INTEGER, mono_ns INTEGER);
            """)
            db.execute("INSERT INTO meta VALUES(1,1,0,?)", (time.monotonic(),))
            for k, v in {"task": task, "provider_identity": provider_identity,
                         "evidence_tier": evidence_tier}.items():
                db.execute("INSERT INTO config VALUES(?,?)", (k, canonical(v)))
            db.execute("INSERT INTO sources VALUES('source',1,?)", (canonical(task["source"]),))
            db.execute("INSERT INTO accepted_inputs VALUES(1,'initial-source','genesis',?)", (canonical(task["source"]),))
            genesis = {"seq": 0, "frontier": 0, "op": "genesis", "value": task["initial_memory"]}
            db.execute("INSERT INTO admissions VALUES(0,'genesis',?,?)",
                       (canonical(task["initial_memory"]), canonical(genesis)))
            self.event(db, "initialize", {"task": task, "epoch": 1,
                                         "provider_identity": provider_identity,
                                         "evidence_tier": evidence_tier})

    def config(self):
        with self.db() as db:
            return {r["k"]: json.loads(r["payload"]) for r in db.execute("SELECT * FROM config")}

    def freeze(self, op, cycle):
        with self.db(True) as db:
            old = db.execute("SELECT frozen FROM requests WHERE op=?", (op,)).fetchone()
            if old:
                previous = json.loads(old["frozen"])
                if previous["cycle"] != cycle:
                    raise ValueError("operation identity reused for a different cycle/request intent")
                return previous
            task = json.loads(db.execute("SELECT payload FROM config WHERE k='task'").fetchone()[0])
            meta = db.execute("SELECT epoch,head,origin FROM meta").fetchone()
            src = db.execute("SELECT version,payload FROM sources WHERE k='source'").fetchone()
            prior = db.execute("SELECT payload FROM admissions WHERE seq=?", (meta["head"],)).fetchone()
            next_input = db.execute("SELECT COALESCE(MAX(seq),0)+1 FROM accepted_inputs").fetchone()[0]
            db.execute("INSERT INTO accepted_inputs VALUES(?,'request',?,?)",
                       (next_input, op, canonical({"cycle": cycle, "request": task["requests"][cycle]})))
            accepted = [dict(r) for r in db.execute("SELECT * FROM accepted_inputs ORDER BY seq")]
            frozen = {"op": op, "cycle": cycle, "family": task["family"],
                      "epoch": meta["epoch"], "parent": meta["head"],
                      "readset": {"source": src["version"]}, "source": json.loads(src["payload"]),
                      "prior_memory": json.loads(prior["payload"]), "request": task["requests"][cycle],
                      "accepted_frontier": next_input, "input_prefix_sha256": digest(accepted),
                      "input_origin": meta["origin"]}
            frozen["request_hash"] = digest(frozen)
            db.execute("INSERT INTO requests VALUES(?,?,?)", (op, frozen["request_hash"], canonical(frozen)))
            self.event(db, "input-freeze", frozen)
            return frozen

    def register_selection(self, frozen, evidence):
        """Only the owned provider wrapper calls this after actual completion."""
        assert frozen["request_hash"] == digest({k: v for k, v in frozen.items() if k != "request_hash"})
        required = {"provider_identity", "evidence_tier", "request", "actual_input_ids", "tokens",
                    "rendered_text", "value", "terminated_by_eos", "complete", "contract",
                    "started_ns", "completed_ns", "selection_authorized", "physical_worker_drained"}
        assert required <= set(evidence), required - set(evidence)
        assert evidence["complete"] and evidence["terminated_by_eos"]
        assert evidence["physical_worker_drained"]
        assert evidence["started_ns"] <= evidence["completed_ns"]
        assert evidence["actual_input_ids"] == evidence["request"]["input_ids"]
        assert json.loads(evidence["rendered_text"]) == evidence["value"]
        assert validate_schema(frozen["family"], evidence["value"])
        assert evidence["request"]["frozen_request_hash"] == frozen["request_hash"]
        selected_id = digest({"op": frozen["op"], "request_hash": frozen["request_hash"],
                              "evidence": evidence})
        with self.db(True) as db:
            conf = {r["k"]: json.loads(r["payload"]) for r in db.execute("SELECT * FROM config")}
            assert evidence["provider_identity"] == conf["provider_identity"]
            assert evidence["evidence_tier"] == conf["evidence_tier"]
            db.execute("INSERT INTO selections VALUES(?,?,?)", (selected_id, frozen["op"], canonical(evidence)))
            self.event(db, "actual-selection", {"id": selected_id, "op": frozen["op"], "evidence": evidence})
        return {"selection_id": selected_id, "frozen": frozen}

    def install(self, proposal, mode="standard", crash=False, adapter=None):
        """Historical receipt first. New-write checks and effects are atomic.

        A revtrace adapter must implement authorize/finalize. Its authorize uses
        actual durable history and selection; this implementation never relabels
        the SQL reference as a RevTrace kernel comparison.
        """
        assert mode in {"standard", "minimal", "revtrace"}
        if mode == "revtrace" and adapter is None:
            raise RuntimeError("RevTrace mode requires an actual reviewed kernel adapter")
        frozen, selection_id = proposal["frozen"], proposal["selection_id"]
        op, rh = frozen["op"], frozen["request_hash"]
        with self.db(True) as db:
            bound = db.execute("SELECT frozen FROM requests WHERE op=?", (op,)).fetchone()
            if (bound is None or json.loads(bound["frozen"]) != frozen
                    or rh != digest({k: v for k, v in frozen.items() if k != "request_hash"})):
                self.event(db, "identity-conflict", {"op": op, "request_hash": rh})
                return {"status": "identity-conflict"}
            old = db.execute("SELECT request_hash,result FROM operations WHERE op=?", (op,)).fetchone()
            if old:
                if old["request_hash"] != rh:
                    self.event(db, "identity-conflict", {"op": op, "request_hash": rh})
                    return {"status": "identity-conflict"}
                result = json.loads(old["result"])
                if adapter is not None:
                    adapter.restore_for_replay(db=db, original_result=result)
                    self.event(db, "kernel-receipt-recovery", adapter.export_trace())
                self.event(db, "original-receipt-replay", {"op": op, "result": result})
                return result
            registered = db.execute("SELECT op,evidence FROM selections WHERE id=?", (selection_id,)).fetchone()
            if registered is None or registered["op"] != op:
                self.event(db, "reject-unselected", {"op": op, "selection_id": selection_id})
                return {"status": "rejected", "reasons": ["missing-owned-selection"]}
            ev = json.loads(registered["evidence"])
            meta = dict(db.execute("SELECT epoch,head FROM meta").fetchone())
            source_versions = dict(db.execute("SELECT k,version FROM sources"))
            reasons = []
            if frozen["parent"] != meta["head"]: reasons.append("parent-changed")
            if frozen["epoch"] != meta["epoch"]: reasons.append("writer-epoch-changed")
            if frozen["readset"] != source_versions: reasons.append("readset-changed")
            if not ev["selection_authorized"]: reasons.append("missing-trusted-selection")
            accepted = [dict(r) for r in db.execute("SELECT * FROM accepted_inputs ORDER BY seq")]
            end = frozen["accepted_frontier"]
            if not (0 < end <= len(accepted) and digest(accepted[:end]) == frozen["input_prefix_sha256"]):
                reasons.append("input-obligation-binding")
            if mode != "minimal" and reasons:
                result = {"status": "rejected", "reasons": reasons}
                self.event(db, "new-write-rejected", {"op": op, "frozen": frozen, "observed": meta,
                                                    "source_versions": source_versions, "result": result})
                return result
            history = [json.loads(r[0]) for r in db.execute("SELECT receipt FROM admissions ORDER BY seq")]
            if adapter is not None:
                adapter.authorize(frozen=frozen, selection=ev, history=history, observed=meta,
                                  source_versions=source_versions, db=db)
            seq = meta["head"] + 1
            receipt = {"seq": seq, "op": op, "parent": frozen["parent"], "epoch": frozen["epoch"],
                       "request_hash": rh, "selection_id": selection_id, "value": ev["value"],
                       "readset": frozen["readset"], "observed_at_commit": meta,
                       "source_versions_at_commit": source_versions, "committed_ns": time.time_ns(),
                       "frontier": frozen["accepted_frontier"], "input_prefix_sha256": frozen["input_prefix_sha256"]}
            if adapter is not None:
                receipt["kernel"] = adapter.prepared_attachment()
            result = {"status": "committed", "receipt": receipt}
            db.execute("INSERT INTO admissions VALUES(?,?,?,?)", (seq, op, canonical(ev["value"]), canonical(receipt)))
            db.execute("INSERT INTO operations VALUES(?,?,?)", (op, rh, canonical(result)))
            db.execute("INSERT INTO outbox VALUES(?,?,?)", (op, seq, canonical(receipt)))
            db.execute("UPDATE meta SET head=?", (seq,))
            self.event(db, "application-commit", {"mode": mode, "receipt": receipt, "omitted_violations": reasons})
        # The external commit above has completed before checkpoint task return.
        if crash:
            os._exit(91)
        if adapter is not None:
            adapter.finalize(receipt=receipt, application_db=str(self.path))
        return result

    def mutate(self, kind):
        with self.db(True) as db:
            if kind == "source-change":
                task = json.loads(db.execute("SELECT payload FROM config WHERE k='task'").fetchone()[0])
                db.execute("UPDATE sources SET version=version+1,payload=? WHERE k='source'",
                           (canonical(task["revised_source"]),))
                seq = db.execute("SELECT COALESCE(MAX(seq),0)+1 FROM accepted_inputs").fetchone()[0]
                db.execute("INSERT INTO accepted_inputs VALUES(?,'source-change','source',?)",
                           (seq, canonical(task["revised_source"])))
            elif kind == "owner-change":
                db.execute("UPDATE meta SET epoch=epoch+1")
            else:
                raise ValueError(kind)
            self.event(db, "mutation", {"kind": kind,
                "sources": [dict(r) for r in db.execute("SELECT * FROM sources")],
                "meta": dict(db.execute("SELECT epoch,head FROM meta").fetchone())})

    def deliver(self):
        with self.db(True) as db:
            for row in db.execute("SELECT * FROM outbox ORDER BY seq DESC").fetchall():
                exists = db.execute("SELECT receipt FROM receiver WHERE event_id=?", (row["event_id"],)).fetchone()
                if exists:
                    assert exists["receipt"] == row["receipt"]
                else:
                    db.execute("INSERT INTO receiver VALUES(?,?,?)", tuple(row))
                self.event(db, "consumer-receipt", {**dict(row), "new_effect": exists is None})

    def record(self, kind, payload):
        with self.db(True) as db:
            self.event(db, kind, payload)

    def dump(self):
        with self.db() as db:
            return {table: [dict(r) for r in db.execute("SELECT * FROM " + table)] for table in
                    ("meta", "config", "sources", "requests", "accepted_inputs", "selections", "admissions", "operations",
                     "outbox", "receiver", "events")}

"""Read-only lifecycle checker: no production admission/transition imports.

For GPU evidence supply independent encode_messages and decode_tokens callbacks
from the frozen tokenizer/renderer. Missing proof is UNKNOWN, not PASS.
Task truth is scored separately and never rewrites a selected model result.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sqlite3

from tasks import score, trajectory_metrics


def canon(x):
    return json.dumps(x, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha(x):
    return hashlib.sha256(canon(x).encode()).hexdigest()


def audit(directory, encode_messages=None, decode_tokens=None):
    directory = Path(directory)
    db = sqlite3.connect("file:" + str(directory / "application.sqlite") + "?mode=ro", uri=True)
    db.row_factory = sqlite3.Row
    tables = {t: [dict(r) for r in db.execute("SELECT * FROM " + t)] for t in
              ("config", "sources", "requests", "accepted_inputs", "selections", "admissions", "operations", "outbox", "receiver", "events")}
    db.close()
    violations, unknown, quality = [], [], []

    def require(condition, label):
        if not condition:
            violations.append(label)

    conf = {r["k"]: json.loads(r["payload"]) for r in tables["config"]}
    requests = {r["op"]: json.loads(r["frozen"]) for r in tables["requests"]}
    selections = {r["id"]: (r["op"], json.loads(r["evidence"])) for r in tables["selections"]}
    receipts = {r["seq"]: json.loads(r["receipt"]) for r in tables["admissions"]}
    inputs = sorted(tables["accepted_inputs"], key=lambda r: r["seq"])
    require([r["seq"] for r in inputs] == list(range(1, len(inputs) + 1)), "input-journal-gap")
    for op, f in requests.items():
        require(f["request_hash"] == sha({k: v for k, v in f.items() if k != "request_hash"}), f"request-binding:{op}")
        end = f.get("accepted_frontier")
        require(type(end) is int and 0 < end <= len(inputs), "invalid-input-frontier:" + op)
        if type(end) is int and 0 < end <= len(inputs):
            require(sha(inputs[:end]) == f.get("input_prefix_sha256"), "input-prefix-mismatch:" + op)
    for sid, (op, ev) in selections.items():
        f = requests.get(op)
        if f is None:
            violations.append("selection-without-request:" + sid)
            continue
        require(sid == sha({"op": op, "request_hash": f["request_hash"], "evidence": ev}), "selection-binding:" + sid)
        required = {"actual_input_ids", "tokens", "request", "rendered_text", "value", "complete",
                    "terminated_by_eos", "started_ns", "completed_ns", "provider_identity", "evidence_tier"}
        if not required <= set(ev):
            unknown.append("missing-actual-evidence:" + sid)
            continue
        require(ev["provider_identity"] == conf["provider_identity"], "wrong-provider:" + sid)
        require(ev["evidence_tier"] == conf["evidence_tier"], "wrong-tier:" + sid)
        require(ev["complete"] and ev["terminated_by_eos"], "incomplete-selection:" + sid)
        require(ev["started_ns"] <= ev["completed_ns"], "noncausal-completion:" + sid)
        req = ev["request"]
        require(req.get("frozen_request_hash") == f["request_hash"], "wrong-request:" + sid)
        require(req.get("input_ids") == ev["actual_input_ids"], "actual-input-mismatch:" + sid)
        try:
            require(json.loads(ev["rendered_text"]) == ev["value"], "rendered-value-mismatch:" + sid)
            user = json.loads(req["messages"][-1]["content"])
            require(user == {k: f[k] for k in ("source", "prior_memory", "request")}, "wrong-consumed-memory:" + sid)
        except (KeyError, ValueError, TypeError):
            unknown.append("unreadable-input-or-render:" + sid)
        if ev["evidence_tier"] == "CPU_FIXTURE_NO_MODEL":
            require(list(canon(req["messages"]).encode()) == ev["actual_input_ids"], "fixture-input-bytes:" + sid)
            require(ev["tokens"] == list(ev["rendered_text"].encode()) + [256], "fixture-token-text:" + sid)
        else:
            calls = ev.get("actual_calls")
            if not calls or "selected_call_index" not in ev:
                unknown.append("missing-actual-GPU-selection-calls:" + sid)
            else:
                chosen = calls[ev["selected_call_index"]]
                require(chosen.get("logical_input_ids") == req["input_ids"], "wrong-logical-GPU-input:" + sid)
                if chosen["operation"] == "verify":
                    require(chosen["actual_input_ids"] == req["input_ids"] + ev["tokens"], "wrong-verification-tensor:" + sid)
                    require(chosen["accepted"] and chosen["predicted_tokens"] == ev["tokens"], "incomplete-verification:" + sid)
                else:
                    require(chosen["actual_input_ids"] == req["input_ids"], "wrong-generation-tensor:" + sid)
                if ev.get("selection_authorized"):
                    require(chosen["role"] == "authority" and chosen["tokens"] == ev["tokens"], "untrusted-selected-call:" + sid)
                else:
                    require(chosen["role"] == "proposal", "wrong-untrusted-provider-role:" + sid)
                    injection = ev.get("controlled_injection")
                    if injection:
                        require(injection.get("kind") == "controlled-low-trust-return" and injection.get("CPU_only_encoding") is True,
                                "undeclared-candidate-substitution:" + sid)
                        require(injection.get("original_tokens") == chosen["tokens"] and injection.get("replacement_tokens") == ev["tokens"],
                                "candidate-substitution-not-bound-to-original:" + sid)
                    else:
                        require(chosen["tokens"] == ev["tokens"], "unexplained-low-trust-token-change:" + sid)
                require(abs(sum(c["actual_gpu_seconds"] for c in calls) - ev["actual_gpu_seconds"]) < 1e-8,
                        "GPU-cost-accounting:" + sid)
            if encode_messages is None:
                unknown.append("independent-tokenizer-not-supplied:" + sid)
            else:
                require(encode_messages(req["messages"], ev["contract"]) == ev["actual_input_ids"], "tokenizer-input:" + sid)
            if decode_tokens is None:
                unknown.append("independent-renderer-not-supplied:" + sid)
            else:
                require(decode_tokens(ev["tokens"], ev["contract"]) == ev["rendered_text"], "trusted-render:" + sid)
        quality.append({"op": op, "cycle": f["cycle"], "selection_id": sid,
                        "admitted": any(r.get("selection_id") == sid for r in receipts.values()),
                        "score": score(f["family"], f["source"], f["prior_memory"], f["request"], ev["value"]),
                        "global_objective": trajectory_metrics(conf["task"], f["cycle"], f["source"], ev["value"]),
                        "pair_key": {"task_id": conf["task"]["id"], "cycle": f["cycle"], "source_sha256": sha(f["source"]),
                                     "request_sha256": sha(f["request"])}})

    # Reconstruct source/owner/head from transactional event history rather than
    # trusting a runtime decision flag or invoking its gate.
    source_version, current_source, epoch, head = None, None, None, 0
    committed, registered, counters, native_returns = {}, set(), {}, []
    false_rejections = 0
    for row in sorted(tables["events"], key=lambda r: r["n"]):
        kind, e = row["kind"], json.loads(row["payload"])
        if kind == "initialize":
            current_source, source_version, epoch = e["task"]["source"], 1, e["epoch"]
        elif kind == "mutation":
            src = next(r for r in e["sources"] if r["k"] == "source")
            current_source, source_version, epoch = json.loads(src["payload"]), src["version"], e["meta"]["epoch"]
            require(e["meta"]["head"] == head, "unexplained-parent-mutation")
        elif kind == "input-freeze":
            require(e["parent"] == head and e["epoch"] == epoch, "incorrect-freeze-parent:" + e["op"])
            require(e["source"] == current_source and e["readset"] == {"source": source_version}, "incorrect-freeze-source:" + e["op"])
            require(head in receipts and e["prior_memory"] == receipts[head]["value"], "incorrect-freeze-memory:" + e["op"])
        elif kind == "actual-selection":
            require(e["id"] in selections and selections[e["id"]][1] == e["evidence"], "selection-table-event-mismatch")
            registered.add(e["id"])
        elif kind == "new-write-rejected":
            f = e["frozen"]
            evidence = [v for op, v in selections.values() if op == e["op"]]
            selected = len(evidence) == 1 and evidence[0].get("selection_authorized") is True
            legal = (selected and f["parent"] == head and f["epoch"] == epoch
                     and f["readset"] == {"source": source_version})
            if legal:
                false_rejections += 1
                violations.append("false-rejection-of-legal-progress:" + e["op"])
        elif kind == "application-commit":
            r = e["receipt"]
            require(r["seq"] == head + 1, "non-successor-admission:" + r["op"])
            require(r["op"] not in committed, "duplicate-application-effect:" + r["op"])
            require(r["parent"] == head, "stale-parent-admission:" + r["op"])
            require(r["epoch"] == epoch, "old-writer-admission:" + r["op"])
            require(r["readset"] == {"source": source_version}, "stale-source-admission:" + r["op"])
            require(r["selection_id"] in registered, "unowned-selection-admission:" + r["op"])
            require(receipts.get(r["seq"]) == r, "durable-receipt-mismatch:" + r["op"])
            selected = selections.get(r["selection_id"])
            if selected:
                require(selected[0] == r["op"] and selected[1]["value"] == r["value"], "selected-content-changed:" + r["op"])
                require(selected[1].get("selection_authorized") is True, "unauthorized-state-admission:" + r["op"])
                if "kernel" in r:
                    def kh(x):
                        return hashlib.sha256(json.dumps(x, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()
                    expected_fact = {"v": r["seq"], "F": r["frontier"], "P": kh(r["value"]),
                                     "Z": kh(selected[1]["tokens"]),
                                     "textsha": hashlib.sha256(canon(r["value"]).encode()).hexdigest(), "txn": r["op"]}
                    require(r["kernel"].get("fact") == expected_fact, "kernel-fact-binding:" + r["op"])
            else:
                unknown.append("missing-selection:" + r["op"])
            committed[r["op"]], head = r, r["seq"]
            previous = receipts.get(head - 1, {})
            require(r.get("frontier", -1) > previous.get("frontier", 0), "nonadvancing-input-frontier:" + r["op"])
        elif kind == "original-receipt-replay":
            require(committed.get(e["op"]) == e["result"]["receipt"], "receipt-replay-changed:" + e["op"])
        elif kind == "consumer-receipt":
            require(receipts.get(e["seq"]) == json.loads(e["receipt"]), "consumer-without-durable-fact")
        elif kind == "native-task-execute":
            key = (e["op"], e["task"])
            counters[key] = counters.get(key, 0) + 1
        elif kind == "native-return":
            native_returns.append(e)
            require(e["native"].get("checkpoint_id") is not None, "missing-native-checkpoint")
    outbox = {r["event_id"]: r for r in tables["outbox"]}
    receiver = {r["event_id"]: r for r in tables["receiver"]}
    require(outbox == receiver, "outbox-not-fully-delivered-or-receipt-changed")
    for op, r in committed.items():
        ops = [row for row in tables["operations"] if row["op"] == op]
        require(len(ops) == 1 and json.loads(ops[0]["result"])["receipt"] == r, "operation-receipt-mismatch:" + op)
    downstream = [op for op, f in requests.items() if f["parent"] > 0
                  and any(o == op for o, _ in selections.values())]
    unfulfilled = [json.loads(r["payload"]) for r in tables["events"] if r["kind"] == "model-unfulfilled"]
    cycle_outcomes = []
    for cycle, request_spec in enumerate(conf["task"]["requests"]):
        related = sorted([f for f in requests.values() if f["cycle"] == cycle], key=lambda f: f["accepted_frontier"])
        admitted = [q for q in quality if q["cycle"] == cycle and q["admitted"]]
        require(len(admitted) <= 1, "multiple-commits-for-one-offered-cycle:" + str(cycle))
        current = admitted[-1] if admitted else None
        cycle_outcomes.append({"cycle": cycle, "offered": True, "committed": current is not None,
            "unfulfilled": current is None, "attempt_operations": [f["op"] for f in related],
            "pair_key": {"task_id": conf["task"]["id"], "cycle": cycle,
                         "source_sha256": sha(related[-1]["source"]) if related else None,
                         "request_sha256": sha(request_spec)},
            "current_step_success": current["score"]["current_step_success"] if current else False,
            "source_grounded_prior_history": current["score"]["source_grounded_prior_history"] if current else None,
            "current_output_valid": current["score"]["current_output_valid"] if current else False,
            "repair_observed": current["score"].get("repair_observed", False) if current else False,
            "global_objective": current["global_objective"] if current else None})
    return {"status": "FAIL" if violations else "UNKNOWN" if unknown else "PASS_SCOPED_CPU_FIXTURE" if conf["evidence_tier"] == "CPU_FIXTURE_NO_MODEL" else "PASS_SCOPED_ACTUAL_MODEL",
            "evidence_tier": conf["evidence_tier"], "violations": violations, "unknown": unknown,
            "committed_cycles": len(committed), "actual_downstream_input_operations": downstream,
            "native_checkpoint_returns": len(native_returns), "false_rejections": false_rejections,
            "native_multi_cycle_evidence_complete": len(native_returns) >= 3 and len(committed) >= 3 and len(downstream) >= 2,
            "offered_request_operations": len(requests), "unfulfilled_model_operations": len(unfulfilled),
            "offered_cycles": len(conf["task"]["requests"]), "cycle_outcomes": cycle_outcomes,
            "controlled_low_trust_substitutions": sum(bool(e.get("controlled_injection")) for _, e in selections.values()),
            "direct_calls_without_candidate_exposure": sum(e.get("candidate_exposure") == "none_direct_generation" for _, e in selections.values()),
            "verification_rejections_observed": sum(bool(e.get("verification_rejection_observed")) for _, e in selections.values()),
            "task_execution_counts": {op + ":" + task: n for (op, task), n in counters.items()},
            "task_scores": quality,
            "scope": "trusted host/selection wrapper; intact SQLite; declared atomic application contract; task truth separate"}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("directory", type=Path)
    parser.add_argument("--model-path", type=Path)
    parser.add_argument("--model-manifest", type=Path)
    args = parser.parse_args()
    if args.model_path or args.model_manifest:
        assert args.model_path and args.model_manifest
        from independent_codec import Codec
        codec = Codec(args.model_path, args.model_manifest)
        result = audit(args.directory, codec.encode, codec.decode)
    else:
        result = audit(args.directory)
    print(json.dumps(result, indent=2))

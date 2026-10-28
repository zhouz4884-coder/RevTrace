"""Independent event-sweep audit of frozen V6 cancellation opportunities.

No model loading, GPU work, source mutation, or replayed serving result.  The
event sweep removes a row either at its observed full terminal or after an
already installed canonical frontier covers its fixed target.  Future
completion clocks are used ONLY to score the frozen-trace ideal bound.
"""
from __future__ import annotations

import csv
import hashlib
import json
import math
import platform
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
BANK = ROOT / "experiments/ces_v6_abcd_20261025/evidence/results"
PREVIOUS = ROOT / "docs/research/independent_synthesis_20261028/TAIL_OPPORTUNITY_BATCHES.csv"
INPUTS = []


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def read(path, lines=False):
    raw = path.read_bytes()
    INPUTS.append({"path": path.relative_to(ROOT).as_posix(), "bytes": len(raw), "sha256": sha(raw)})
    return [json.loads(x) for x in raw.decode("utf8").splitlines() if x.strip()] if lines else json.loads(raw)


def dump(name, value):
    (HERE / name).write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf8")


def event_sweep(jobs, records, commits, begin, end, use_logged_time=False):
    """Use chronological owner events, rather than the earlier max/min code."""
    active = set(jobs)
    events = []
    for jid in jobs:
        terminal = min(end, records[jid]["result"]["row_terminal_perf"])
        events.append((max(begin, terminal), 0, {"job_id": jid}))
    for commit in commits:
        if commit["absolute_log" if use_logged_time else "absolute_install"] <= end:
            events.append((max(begin, commit["absolute_log" if use_logged_time else "absolute_install"]), 1, commit))
    retired = {}
    drain = begin
    for when, kind, payload in sorted(events, key=lambda x: (x[0], x[1])):
        if kind == 0:
            active.discard(payload["job_id"])
        else:
            for jid in tuple(active):
                j = records[jid]["job"]
                if j["session_id"] == payload["session_id"] and j["audio_end_sample"] <= payload["audio_end_sample"]:
                    active.remove(jid)
                    retired[jid] = payload
        if not active:
            drain = when
            break
    assert not active
    original_last = max(max(begin, min(end, records[j]["result"]["row_terminal_perf"])) for j in jobs)
    return max(0.0, original_last - drain), drain, retired


def frontier_before(events, sid, when, key, clock):
    previous = [e for e in events if e["session_id"] == sid and e[clock] <= when]
    return max(previous, key=lambda e:e[clock])[key] if previous else 0


def unfulfilled_windows(sessions, cfg, commits, consumer, when, t0, excluded_sids=()):
    """Offered fine windows only; does not pretend to reconstruct scheduler state."""
    result = []
    for s in sessions:
        sid = s["session_id"]
        if sid in excluded_sids:
            continue
        cf = frontier_before(commits, sid, when, "audio_end_sample", "absolute_install")
        vf = frontier_before(consumer, sid, when, "valid_visible_frontier", "observed_perf")
        missing_canonical, missing_visible = [], []
        for window in range(1, math.ceil(s["duration"] / cfg["fine_seconds"]) + 1):
            audio_end_s = min(s["duration"], window * cfg["fine_seconds"])
            target = round(audio_end_s * cfg["sample_rate"])
            released = t0 + s["offset"] + audio_end_s
            if released > when:
                continue
            if target > cf:
                missing_canonical.append(window)
            if target > vf:
                missing_visible.append(window)
        if missing_canonical or missing_visible:
            result.append({"session_id": sid, "source_id": s["source_id"],
                           "released_uncommitted_windows": missing_canonical,
                           "released_not_visible_windows": missing_visible})
    return result


def main():
    INPUTS.append({"path":PREVIOUS.relative_to(ROOT).as_posix(),"bytes":PREVIOUS.stat().st_size,"sha256":sha(PREVIOUS.read_bytes())})
    original_rows = {(r["stage"], r["cell"], r["batch"]): r for r in csv.DictReader(PREVIOUS.open(encoding="utf8"))}
    batch_checks, runs, probes = [], [], []
    all_caps, violations, context_signatures = [], [], set()
    mismatches = []
    for ep in sorted(BANK.glob("*/*/events.jsonl")):
        path, stage, cell = ep.parent, ep.parent.parent.name, ep.parent.name
        events = read(ep, True)
        records = {r["job"]["job_id"]: r for r in read(path / "worker_records.jsonl", True)}
        accounting = read(path / "worker_batch_accounting.jsonl", True)
        cfg = read(path / "config.json")
        sessions = read(path / "sessions.json")
        provenance = read(path / "provenance.json")
        consumer = read(path / "consumer.jsonl", True)
        t0 = next(e["t0_perf"] for e in events if e["kind"] == "run-start")
        commits = [dict(e, absolute_install=t0 + e["installed"], absolute_log=t0 + e["time"]) for e in events if e["kind"] == "commit"]
        for sid in {c["session_id"] for c in commits}:
            ccs = sorted((c for c in commits if c["session_id"] == sid), key=lambda c:c["absolute_install"])
            if [c["audio_end_sample"] for c in ccs] != sorted(c["audio_end_sample"] for c in ccs):
                violations.append([stage, cell, "nonmonotone canonical frontier", sid])
        batches = [b for b in accounting if b["worker"].startswith("proposal")]
        batches.sort(key=lambda b: b["worker_started_perf"])
        run_tail, run_model, run_covered, capped = 0.0, 0.0, 0, 0
        for b in batches:
            assert len(b["phases"]) == 1
            phase = b["phases"][0]
            begin, end = phase["started_perf"], phase["completed_perf"]
            tail, drain, retired = event_sweep(b["job_ids"], records, commits, begin, end)
            logged_tail, logged_drain, _ = event_sweep(b["job_ids"], records, commits, begin, end, True)
            old = original_rows[(stage, cell, b["batch_id"])]
            error = abs(float(old["ideal_reclaimable_tail"]) - tail)
            if error > 1e-8:
                mismatches.append({"stage":stage,"cell":cell,"batch":b["batch_id"],"error":error})
            if set(retired) != set(filter(None,old["covered_jobs"].split("|"))):
                mismatches.append({"stage":stage,"cell":cell,"batch":b["batch_id"],"error":"retired row identities differ"})
            run_tail += tail
            run_model += end-begin
            run_covered += len(retired)
            cap_jobs = [j for j in b["job_ids"] if records[j]["result"]["hit_token_limit"]]
            capped += len(cap_jobs)
            for jid in cap_jobs:
                j, r = records[jid]["job"], records[jid]["result"]
                context = r["execution_context_audit"]
                signature = sha(json.dumps({"source": j["source_id"], "audio": context["actual_audio_sha256"],
                  "prompt": context["executed_prompt_tokens"], "end": j["audio_end_sample"]}, sort_keys=True).encode())
                context_signatures.add(signature)
                all_caps.append({"stage":stage,"cell":cell,"batch":b["batch_id"],"job_id":jid,"source_id":j["source_id"],
                                 "signature":signature,"tail":tail,"target":j["audio_end_sample"],"covered":jid in retired})
            later = [x for x in batches if x["worker"] == b["worker"] and x["worker_started_perf"] > b["worker_started_perf"]]
            last = max(min(end, records[j]["result"]["row_terminal_perf"]) for j in b["job_ids"])
            item = {"stage":stage,"cell":cell,"batch":b["batch_id"],"rows":len(b["job_ids"]),"model_wall_s":end-begin,
                    "ideal_tail_s":tail,"owner_log_tail_s":logged_tail,"covered_before_terminal_rows":len(retired),
                    "cap_rows":len(cap_jobs),"is_last_proposer_batch":not later,
                    "later_proposer_batches":len(later),"original_csv_abs_error":error}
            batch_checks.append(item)
            if tail > 0.5 or (stage == "D_heldout" and tail > 0.1):
                cap_sids = {records[j]["job"]["session_id"] for j in cap_jobs}
                row_details=[]
                for jid in b["job_ids"]:
                    j,r=records[jid]["job"],records[jid]["result"]
                    commit=retired.get(jid)
                    row_details.append({k:j[k] for k in ["job_id","session_id","source_id","parent","end_window","audio_start_sample","audio_end_sample"]} | {
                      "tokens":r["generated_tokens"],"cap":r["hit_token_limit"],"terminal_run_s":r["row_terminal_perf"]-t0,
                      "retired_at_install_run_s":None if commit is None else commit["installed"],
                      "retire_commit_job":None if commit is None else commit["job_id"],
                      "actual_context_override":r["execution_context_audit"].get("fault_override",False),
                      "direct_fault_field_present":"fault_actual_prompt_tokens" in j})
                missing=unfulfilled_windows(sessions,cfg,commits,consumer,drain,t0,cap_sids)
                observations=[c for c in consumer if drain < c["observed_perf"] <= last and c["session_id"] not in cap_sids]
                probes.append(item | {"source_commit":provenance["code_commit"],"run_dir":path.relative_to(ROOT).as_posix(),
                  "config_sha256":sha((path/"config.json").read_bytes()),
                  "model_begin_run_s":begin-t0,"ideal_drain_run_s":drain-t0,"original_last_terminal_run_s":last-t0,
                  "batch_drained_run_s":b["batch_drained_perf"]-t0,
                  "unfulfilled_other_session_windows_at_ideal_drain":missing,
                  "actual_other_consumer_events_during_tail":len(observations),
                  "actual_other_provisional_events_during_tail":sum(c["source_kind"]=="display" for c in observations),
                  "actual_other_canonical_events_during_tail":sum(c["source_kind"]=="canonical-display" for c in observations),
                  "row_details":row_details})
        runs.append({"stage":stage,"cell":cell,"batches":len(batches),"model_wall_s":run_model,"ideal_tail_s":run_tail,
                     "ideal_tail_fraction":run_tail/run_model if run_model else 0,"covered_rows":run_covered,"cap_rows":capped,
                     "source_commit":provenance["code_commit"]})
    development=read(BANK.parents[0]/"inputs/development_manifest.json")
    heldout=read(BANK.parents[0]/"inputs/heldout_manifest.json")
    groups=defaultdict(list)
    for r in runs:
        groups[(r["stage"],r["cell"].rsplit("-r",1)[0])].append(r)
    grouped=[{"stage":k[0],"stratum":k[1],"runs":len(rs),"median_tail_s":statistics.median(r["ideal_tail_s"] for r in rs),
              "each_tail_s":[r["ideal_tail_s"] for r in rs],"median_fraction":statistics.median(r["ideal_tail_fraction"] for r in rs)} for k,rs in sorted(groups.items())]
    large=[r for r in batch_checks if r["ideal_tail_s"]>5]
    held=[r for r in runs if r["stage"]=="D_heldout"]
    summary={"experiment_id":"REVTRACE-PHYSICAL-RETIREMENT-OPPORTUNITY-REVIEW-20261028",
      "type":"independent archival event-sweep analysis, no new serving execution",
      "analysis_script_sha256":sha(Path(__file__).read_bytes()),"python":sys.version,"platform":platform.platform(),
      "source_runs":len(runs),"proposal_batches":len(batch_checks),"comparison_mismatches":mismatches,
      "max_absolute_error_vs_original_s":max(r["original_csv_abs_error"] for r in batch_checks),
      "max_owner_log_delay_cost_s":max(r["ideal_tail_s"]-r["owner_log_tail_s"] for r in batch_checks),
      "integrity_violations":violations,"large_tail_threshold_s":5,"large_tail_batches":len(large),
      "large_tails_final_batches":sum(r["is_last_proposer_batch"] for r in large),
      "all_cap_rows":len(all_caps),"unique_cap_sources":sorted({r["source_id"] for r in all_caps}),
      "unique_cap_execution_contexts":len(context_signatures),"large_tail_cap_sources":sorted({c["source_id"] for c in all_caps if c["tail"]>5}),
      "heldout_runs":len(held),"heldout_cap_rows":sum(r["cap_rows"] for r in held),
      "heldout_total_ideal_tail_s":sum(r["ideal_tail_s"] for r in held),
      "heldout_total_proposal_model_s":sum(r["model_wall_s"] for r in held),
      "heldout_max_run_ideal_tail_s":max(r["ideal_tail_s"] for r in held),
      "heldout_max_batch_ideal_tail_s":max(r["ideal_tail_s"] for r in batch_checks if r["stage"]=="D_heldout"),
      "source_independence":{"development_sources":len(development["sessions"]),"heldout_sources":len(heldout["sessions"]),
        "shared_source_ids":sorted({s["source_id"] for s in development["sessions"]}&{s["source_id"] for s in heldout["sessions"]}),
        "shared_audio_sha256":sorted({s["audio_sha256"] for s in development["sessions"]}&{s["audio_sha256"] for s in heldout["sessions"]}),
        "shared_speakers":sorted({s.get("speaker",s.get("speaker_id")) for s in development["sessions"]}&{s.get("speaker",s.get("speaker_id")) for s in heldout["sessions"]})},
      "groups":grouped,"decision":"GO bounded physical-exit probe; no universal throughput or causal-policy superiority claim",
      "new_GPU_calls":0}
    dump("SUMMARY.json",summary)
    dump("PROBE_DETAILS.json",sorted(probes,key=lambda r:r["ideal_tail_s"],reverse=True))
    shortlist=[]
    for r in sorted(probes,key=lambda r:(r["stage"],r["cell"])):
        category=None
        if r["stage"]=="D_development" and r["cell"].startswith("development-sync-mixed-") and any(x in r["cell"] for x in ["-fine-","-standard-"]) and r["batch"].endswith(":5"):
            category="primary-existing-follow-on-service"
        elif r["stage"]=="D_development" and r["cell"]=="development-staggered-mixed-standard-r0" and r["cap_rows"]:
            category="large-tail-executor-feasibility"
        elif r["stage"]=="C" and r["cell"].startswith("development-sync-mixed-hold_15-") and r["cap_rows"]:
            category="repeated-controlled-abnormal-context"
        elif r["stage"]=="D_heldout" and r["cell"]=="heldout-staggered-clean-anchor_cost-r0" and r["ideal_tail_s"]==summary["heldout_max_batch_ideal_tail_s"]:
            category="small-independent-source-boundary"
        if category:
            shortlist.append({"category":category,**r})
    for cell in ["heldout-sync-clean-fine-r0","heldout-sync-clean-standard-r0"]:
        r=next(r for r in batch_checks if r["stage"]=="D_heldout" and r["cell"]==cell and r["batch"].endswith(":1"))
        shortlist.append({"category":"short-no-trigger-overhead",**r,
          "run_dir":f"experiments/ces_v6_abcd_20261025/evidence/results/D_heldout/{cell}"})
    dump("PROBE_SHORTLIST.json",shortlist)
    dump("CAP_SOURCE_CONTEXTS.json",all_caps)
    dump("INPUT_MANIFEST.json",INPUTS)
    for name,rows in [("BATCH_CHECK.csv",batch_checks),("RUN_CHECK.csv",runs)]:
        with (HERE/name).open("w",encoding="utf8",newline="") as f:
            w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    print(json.dumps({k:v for k,v in summary.items() if k not in ["groups","python","platform"]},indent=2))


if __name__=="__main__":
    main()

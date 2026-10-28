"""Opportunity screening from frozen V6 traces, not a GPU performance result.

Question: once Canonical covers a running Private target, can stopping that
useless row shorten the physical batch tail? Uses only observed installation
times and complete row terminal times. No hypothetical cancellation is run.
"""
import csv
import hashlib
import json
import statistics
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
BANK = ROOT / "experiments/ces_v6_abcd_20261025/evidence/results"
inputs, batch_rows, run_rows = [], [], []


def read(p):
    raw = p.read_bytes()
    inputs.append(dict(path=str(p.relative_to(ROOT)), sha256=hashlib.sha256(raw).hexdigest(), bytes=len(raw)))
    return [json.loads(x) for x in raw.decode("utf-8").splitlines() if x.strip()]


for ep in sorted(BANK.glob("*/*/events.jsonl")):
    stage, cell = ep.parent.parent.name, ep.parent.name
    ev = read(ep)
    wr = read(ep.parent / "worker_records.jsonl")
    batches = read(ep.parent / "worker_batch_accounting.jsonl")
    t0 = next(e["t0_perf"] for e in ev if e["kind"] == "run-start")
    commits = defaultdict(list)
    for e in ev:
        if e["kind"] == "commit":
            commits[e["session_id"]].append((e["audio_end_sample"], e["installed"]+t0))
    records = {r["job"]["job_id"]: r for r in wr}
    saved, model_wall, relevant, obsolete_in_flight = 0., 0., 0, 0
    for b in batches:
        if not b["worker"].startswith("proposal"):
            continue
        # The observed proposer has one independent-generation phase. Fail
        # loudly if a different executor contract appears in this bank.
        assert len(b["phases"]) == 1, (stage, cell, b["batch_id"])
        phase = b["phases"][0]
        begin, end = phase["started_perf"], phase["completed_perf"]
        model_wall += end-begin
        expiry_or_terminal, terminal_times, expired = [], [], []
        for jid in b["job_ids"]:
            r = records[jid]
            j, res = r["job"], r["result"]
            terminal = res["row_terminal_perf"]
            # Bound by recorded neural phase end; retained postprocessing is
            # never counted as model time saved.
            terminal = min(terminal, end)
            cover = min((time for frontier, time in commits[j["session_id"]]
                         if frontier >= j["audio_end_sample"]), default=float("inf"))
            effective = max(begin, min(terminal, cover))
            expiry_or_terminal.append(effective)
            terminal_times.append(max(begin, terminal))
            if cover < terminal:
                expired.append(jid)
        # Compare the last actual row terminal to the last terminal-or-cover,
        # excluding phase bookends. Assumes zero communication/token-boundary
        # cost and unchanged live-row timing: a fixed-trace ideal bound only.
        tail = max(0., max(terminal_times)-max(expiry_or_terminal))
        saved += tail
        relevant += tail > .001
        obsolete_in_flight += len(expired)
        batch_rows.append(dict(stage=stage, cell=cell, batch=b["batch_id"], rows=len(b["job_ids"]),
            model_wall=end-begin, covered_before_terminal_rows=len(expired),
            ideal_reclaimable_tail=tail, last_original_terminal=max(terminal_times)-t0,
            last_terminal_or_coverage=max(expiry_or_terminal)-t0,
            capped_rows=sum(bool(records[j]["result"]["hit_token_limit"]) for j in b["job_ids"]),
            capped_source_ids="|".join(sorted({records[j]["job"]["source_id"] for j in b["job_ids"]
                                               if records[j]["result"]["hit_token_limit"]})),
            covered_jobs="|".join(expired)))
    label = cell.rsplit("-r", 1)[0]
    run_rows.append(dict(stage=stage, cell=cell, stratum=label,
        proposal_model_wall=model_wall, ideal_reclaimable_tail=saved,
        ideal_fraction_of_observed_proposal_model_wall=saved/model_wall if model_wall else 0,
        tail_batches=relevant, covered_in_flight_rows=obsolete_in_flight))

def write_csv(name, rr):
    with (HERE/name).open("w",encoding="utf-8",newline="") as f:
        w=csv.DictWriter(f,fieldnames=list(rr[0]));w.writeheader();w.writerows(rr)

write_csv("TAIL_OPPORTUNITY_BATCHES.csv", batch_rows)
write_csv("TAIL_OPPORTUNITY_RUNS.csv", run_rows)
groups=defaultdict(list)
for r in run_rows:groups[(r["stage"],r["stratum"])].append(r)
summary=[]
for (stage,label),rr in sorted(groups.items()):
    summary.append(dict(stage=stage,stratum=label,runs=len(rr),
        median_ideal_tail=statistics.median(r["ideal_reclaimable_tail"] for r in rr),
        median_ideal_fraction=statistics.median(r["ideal_fraction_of_observed_proposal_model_wall"] for r in rr),
        each_ideal_tail=[r["ideal_reclaimable_tail"] for r in rr]))
out=dict(scope="Post-hoc opportunity screen; no new execution, no achieved speedup, no live policy validation",
    hypothesis="Physically retire covered Private rows at decode boundaries while keeping state admission fail closed",
    bound_assumptions=["instantaneous receipt/control and stopping", "unchanged observed completion of still-useful rows",
                       "frozen canonical installation schedule", "covers only whole-batch tails, not compaction/interior FLOPs"],
    exclusions=["old parent alone is not invalid", "no Authority cancellation", "no partial output is certified",
                "cannot sum parallel GPUs into end-to-end speedup", "Mixed and held interventions are controlled conditions"],
    runs=len(run_rows),proposal_batches=len(batch_rows),groups=summary,input_manifest=inputs,
    script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),new_GPU_calls=0)
(HERE/"TAIL_OPPORTUNITY.json").write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps({"runs":len(run_rows),"proposal_batches":len(batch_rows),"top_groups":sorted(summary,key=lambda r:r['median_ideal_tail'],reverse=True)[:8]},ensure_ascii=False))

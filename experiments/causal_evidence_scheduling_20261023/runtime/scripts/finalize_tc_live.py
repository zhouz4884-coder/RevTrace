"""Aggregate audited real-arrival cells and pair only identical workloads/resources."""
import argparse
import csv
import json
import re
import statistics
from collections import defaultdict
from pathlib import Path

def units(text):
    return re.findall(r"[a-z0-9']+|[\u3400-\u9fff]",text.lower())

def edits(a,b):
    row=list(range(len(b)+1))
    for i,x in enumerate(a,1):
        nxt=[i]
        for j,y in enumerate(b,1):
            nxt.append(min(nxt[-1]+1,row[j]+1,row[j-1]+(x!=y)))
        row=nxt
    return row[-1]

def percentile(xs,q):
    xs=sorted(xs); p=(len(xs)-1)*q; lo=int(p); hi=min(len(xs)-1,lo+1)
    return xs[lo]+(xs[hi]-xs[lo])*(p-lo)

def collect(root,platform,manifest):
    specs=json.loads((root/"frozen_matrix.json").read_text())
    sources={r["source_id"]:r for r in manifest["sessions"]}
    rows=[]
    missing=[]
    for spec in specs["cells"]:
        p=root/spec["name"]
        if not (p/"audit.json").exists() or not (p/"result.json").exists():
            missing.append(spec["name"]); continue
        audit=json.loads((p/"audit.json").read_text())
        if audit["decision"]!="PASS_REPLAYED_CERTIFICATES_AND_CAUSAL_CLOCKS":
            raise ValueError(f"nonpassing integrity audit {p}")
        result=json.loads((p/"result.json").read_text())
        config=json.loads((p/"config.json").read_text())
        sessions={s["session_id"]:s for s in json.loads((p/"sessions.json").read_text())}
        seen=set(); errors=defaultdict(int); counts=defaultdict(int)
        texts={s["session_id"]:s["text"] for s in result["final_states"]}
        frontier_latencies={}
        if (p/"events.jsonl").exists():
            for line in (p/"events.jsonl").read_text().splitlines():
                event=json.loads(line)
                if event["kind"]=="commit":
                    key=(event["session_id"],event["audio_end_sample"])
                    if key in frontier_latencies: raise ValueError("duplicate forward frontier")
                    frontier_latencies[key]=event["latency_seconds"]
        for sid,text in texts.items():
            source=sources[sessions[sid]["source_id"]]
            if source["source_id"] in seen: continue
            seen.add(source["source_id"])
            ref=units(source["reference"])
            errors[source["language"]]+=edits(ref,units(text))
            counts[source["language"]]+=len(ref)
        row={**spec,"platform":platform,"run_directory":str(p),
            "code_commit":specs["code_commit"],"manifest_sha256":config["manifest_sha256"],
            "proposal_barrier":config.get("proposal_barrier","segment"),
            "display_p99":result["display_p99_seconds"],"commit_p99":result["commit_p99_seconds"],
            "display_misses":result["display_2s_misses"],"displays":result["display_events"],
            "commits":result["certified_commits"],"token_limit_events":result["token_limit_events"],
            "wall":result["wall_seconds_including_arrival_and_drain"],
            "drain":result["wall_seconds_including_arrival_and_drain"]-result["last_audio_arrival_seconds"],
            "audio_xrt":result["audio_seconds_per_wall_second"],
            "audio_seconds":result["audio_seconds"],
            "energy_per_audio_second":result["energy_joules_per_audio_second"],
            "unique_quality_sessions":len(seen),
            "english_wer":errors["English"]/max(1,counts["English"]),
            "chinese_cer":errors["Chinese"]/max(1,counts["Chinese"]),"texts":texts,
            "frontier_latencies":frontier_latencies}
        rows.append(row)
    return rows,missing

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--root-3090",type=Path,required=True)
    p.add_argument("--root-v100",type=Path,required=True)
    p.add_argument("--manifest",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    a=p.parse_args(); a.output.mkdir(parents=True,exist_ok=True)
    manifest=json.loads(a.manifest.read_text())
    rows=[]; missing={}
    for label,root in (("RTX3090",a.root_3090),("V100",a.root_v100)):
        part,missing[label]=collect(root,label,manifest); rows+=part
    groups=defaultdict(list)
    index={}
    for r in rows:
        k=(r["platform"],r["model"],r["sessions"],r["proposal_gpus"],r["authority_gpus"],r["arrival"],r["mode"])
        groups[k].append(r)
        index[(*k[:-1],r["seed"],r["mode"])]=r
    aggregates=[]
    for k,rs in sorted(groups.items()):
        item=dict(zip(("platform","model","sessions","proposal_gpus","authority_gpus","arrival","mode"),k))
        item.update(repeats=len(rs),all_repeats_display_slo_pass=all(r["display_p99"]<=2 for r in rs),
                    zero_token_limits=all(r["token_limit_events"]==0 for r in rs))
        for metric in ("display_p99","commit_p99","audio_xrt","wall","drain","energy_per_audio_second","english_wer","chinese_cer"):
            values=[r[metric] for r in rs]
            item[metric]={"median":statistics.median(values),"min":min(values),"max":max(values)}
        item["certified_commits"]=sum(r["commits"] for r in rs)
        item["display_events"]=sum(r["displays"] for r in rs)
        aggregates.append(item)
    pairs=[]
    for k,r in index.items():
        if k[-1]!="coarse": continue
        ref=index.get((*k[:-1],"fine_certified"))
        if ref is None: continue
        assert r["manifest_sha256"]==ref["manifest_sha256"] and r["audio_seconds"]==ref["audio_seconds"]
        assert r["code_commit"]==ref["code_commit"]
        d=[edits(units(ref["texts"][sid]),units(text))/max(1,len(units(ref["texts"][sid])))
           for sid,text in r["texts"].items()]
        pair={"coarse":r["name"],"fine":ref["name"],"platform":r["platform"],
            "model":r["model"],"sessions":r["sessions"],"proposal_gpus":r["proposal_gpus"],
            "authority_gpus":r["authority_gpus"],"arrival":r["arrival"],"seed":r["seed"],
            "inclusive_wall_speedup":ref["wall"]/r["wall"],
            "energy_reduction":1-r["energy_per_audio_second"]/ref["energy_per_audio_second"],
            "display_latency_ratio":r["display_p99"]/ref["display_p99"],
            "commit_latency_ratio_different_intervals":r["commit_p99"]/ref["commit_p99"],
            "paired_final_edit_p95":percentile(d,.95),"paired_final_edit_max":max(d),
            "exact_terminal_sessions":sum(x==0 for x in d),"sessions_total":len(d)}
        if r["frontier_latencies"] and ref["frontier_latencies"]:
            coarse_values=[]; fine_values=[]
            for key,value in r["frontier_latencies"].items():
                if key not in ref["frontier_latencies"]:
                    raise ValueError("missing matching fine authority frontier")
                coarse_values.append(value); fine_values.append(ref["frontier_latencies"][key])
            pair.update(common_frontiers=len(coarse_values),
                coarse_common_frontier_p99=percentile(coarse_values,.99),
                fine_common_frontier_p99=percentile(fine_values,.99))
        pairs.append(pair)
    compact=[{k:v for k,v in r.items() if k not in ("texts","frontier_latencies")} for r in rows]
    with (a.output/"cells.csv").open("w",newline="",encoding="utf-8") as f:
        writer=csv.DictWriter(f,fieldnames=list(compact[0])); writer.writeheader(); writer.writerows(compact)
    payload={"decision":"COMPLETE" if not any(missing.values()) else "INCOMPLETE",
        "missing":missing,"cells":compact,"aggregates":aggregates,"paired_comparisons":pairs,
        "scope":"real-arrival certified runtime; constructed twelve-session pool; repeated slots not independent quality samples"}
    (a.output/"summary.json").write_text(json.dumps(payload,indent=2)+"\n")
    print(json.dumps({"decision":payload["decision"],"cells":len(rows),"pairs":len(pairs),"missing":missing}))

if __name__=="__main__": main()

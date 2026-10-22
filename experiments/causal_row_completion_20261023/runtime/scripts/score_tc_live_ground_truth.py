"""Offline ground-truth scoring of frozen live transcripts; no inference.

Deduplicate load replicas by source ID, require their terminal text to agree,
reproduce existing per-run quality values, and pair only identical resources,
input pools, arrivals and seeds. Chinese CER uses characters (all strings in
this frozen Chinese pool contain no ASCII letters/digits after normalization).
"""
from collections import defaultdict
from pathlib import Path
import argparse
import csv
import hashlib
import json
import re
import statistics
import unicodedata
from finalize_tc_live import edits, units

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"results/tc_live_20260906/ground_truth"
MANIFEST=ROOT/"tmp/tc_live_audio/tc_live_20260906/manifest.json"

def read(p):return json.loads(p.read_text(encoding="utf8"))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def tokens(text,language):
    text=unicodedata.normalize("NFKC",text).lower()
    if language=="English":return re.findall(r"[a-z0-9']+",text)
    return [c for c in text if c.isalnum()]

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    manifest=read(MANIFEST); sources={s["source_id"]:s for s in manifest["sessions"]}
    summary=read(ROOT/"results/tc_live_20260906/summary/summary.json")
    assert summary["decision"]=="COMPLETE" and len(summary["cells"])==96
    runs={}; source_rows=[]; files=[]
    for c in summary["cells"]:
        folder=Path(c["run_directory"])
        if not folder.is_absolute():folder=ROOT/folder
        result=read(folder/"result.json"); sessions={r["session_id"]:r for r in read(folder/"sessions.json")}
        copies=defaultdict(list)
        for r in result["final_states"]:
            copies[sessions[r["session_id"]]["source_id"]].append((r["session_id"],r["text"]))
        counts=defaultdict(int); errors=defaultdict(int); unique=defaultdict(int)
        for sid,items in sorted(copies.items()):
            assert len({text for _,text in items})==1,(c["name"],sid,"replica text differs")
            slot,hyp=min(items); src=sources[sid]; lang=src["language"]
            ref_tokens=tokens(src["reference"],lang); hyp_tokens=tokens(hyp,lang)
            # Verify compatibility with the previously published aggregate normalizer.
            assert ref_tokens==units(src["reference"]) and hyp_tokens==units(hyp),(sid,lang)
            error=edits(ref_tokens,hyp_tokens); denominator=len(ref_tokens)
            counts[lang]+=denominator;errors[lang]+=error;unique[lang]+=1
            source_rows.append({"platform":c["platform"],"run":c["name"],"model":c["model"],
                "mode":c["mode"],"source_id":sid,"language":lang,"load_copies":len(items),
                "representative_slot":slot,"reference":src["reference"],"hypothesis":hyp,
                "reference_units":denominator,"edit_errors":error,"error_rate":error/denominator,
                "audio_sha256":src["audio_sha256"]})
        wer=errors["English"]/counts["English"];cer=errors["Chinese"]/counts["Chinese"]
        assert abs(wer-c["english_wer"])<1e-12 and abs(cer-c["chinese_cer"])<1e-12,c["name"]
        runs[c["platform"],c["name"]]={"wer":wer,"cer":cer,"source_ids":sorted(copies),
            "reference_words":counts["English"],"reference_characters":counts["Chinese"],
            "english_sources":unique["English"],"chinese_sources":unique["Chinese"]}
        for name in ("result.json","sessions.json","config.json"):
            p=folder/name;files.append({"path":p.relative_to(ROOT).as_posix(),"sha256":sha(p)})
    pairs=[]
    for p in summary["paired_comparisons"]:
        f=runs[p["platform"],p["fine"]];c=runs[p["platform"],p["coarse"]]
        assert f["source_ids"]==c["source_ids"]
        row={k:p[k] for k in ("platform","model","sessions","proposal_gpus","authority_gpus","arrival","seed","fine","coarse")}
        row.update(source_ids=c["source_ids"],unique_sources=len(c["source_ids"]),
            english_sources=c["english_sources"],chinese_sources=c["chinese_sources"],
            reference_words=c["reference_words"],reference_characters=c["reference_characters"],
            fine_wer=f["wer"],coarse_wer=c["wer"],delta_wer_pp=100*(c["wer"]-f["wer"]),
            fine_cer=f["cer"],coarse_cer=c["cer"],delta_cer_pp=100*(c["cer"]-f["cer"]))
        pairs.append(row)
    groups=defaultdict(list)
    for p in pairs:
        groups[tuple(p[k] for k in ("platform","model","sessions","proposal_gpus","authority_gpus","arrival"))].append(p)
    aggregates=[]
    for key,rs in sorted(groups.items()):
        assert len(rs)==3
        a=dict(zip(("platform","model","sessions","proposal_gpus","authority_gpus","arrival"),key))
        a.update({k:rs[0][k] for k in ("source_ids","unique_sources","english_sources","chinese_sources","reference_words","reference_characters")})
        a["repeats"]=3
        for metric in ("fine_wer","coarse_wer","delta_wer_pp","fine_cer","coarse_cer","delta_cer_pp"):
            values=[r[metric] for r in rs];a[metric]={"median":statistics.median(values),"min":min(values),"max":max(values)}
        aggregates.append(a)
    assert len(pairs)==36 and len(aggregates)==12
    # All repeats at each operating point have identical ground-truth error counts.
    assert all(a[k]["min"]==a[k]["max"] for a in aggregates for k in ("fine_wer","coarse_wer","fine_cer","coarse_cer"))
    for name,rows in (("per_source.csv",source_rows),("paired_runs.csv",pairs)):
        with (OUT/name).open("w",encoding="utf8",newline="") as f:
            w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    audit={"decision":"PASS_OFFLINE_GT_RESCORING","manifest_sha256":sha(MANIFEST),
        "runs_checked":96,"matched_run_pairs":36,"matched_configurations":12,
        "replica_terminal_agreement":True,"existing_aggregates_reproduced":True,
        "method":"Corpus error ratios over distinct source sessions, deduplicated by source ID. NFKC/lowercase; English words preserving apostrophes, Chinese alphanumeric characters; no number expansion. Delta is Coarse minus Fine-certified in percentage points.",
        "source_sessions":manifest["sessions"],"paired_configurations":aggregates,"source_files":files}
    (OUT/"audit.json").write_text(json.dumps(audit,ensure_ascii=False,indent=2)+"\n",encoding="utf8")
    tex=[r"\begin{table*}[t]",r"\centering",r"\footnotesize",
      r"\caption{Ground-truth quality of matched live runs. F/C denote Fine-certified/Coarse; WER/CER are corpus error rates (\%). $\Delta$ is Coarse minus Fine-certified (percentage points). Each row uses the same unique source pool for both policies, with identical scores over three process repeats. The c8 rows cover four English and four Chinese sources; all other rows cover six of each. P+A counts GPUs; S/T denotes synchronous/staggered arrivals.}",
      r"\label{supp:tab:live-ground-truth}",r"\setlength{\tabcolsep}{3.5pt}",
      r"\begin{tabular}{@{}llrrccrrrrrr@{}}",r"\toprule",
      r"GPU & Model & c & Unique & P+A & Arrival & WER F & WER C & $\Delta$WER & CER F & CER C & $\Delta$CER \\",r"\midrule"]
    for a in aggregates:
        gpu="3090" if a["platform"]=="RTX3090" else "V100"
        topology=str(len(a["proposal_gpus"].split(',')))+"+"+str(len(a["authority_gpus"].split(',')))
        metric=[100*a[k]["median"] if not k.startswith("delta") else a[k]["median"] for k in ("fine_wer","coarse_wer","delta_wer_pp","fine_cer","coarse_cer","delta_cer_pp")]
        vals=[f"{v:+.3f}" if i in (2,5) else f"{v:.3f}" for i,v in enumerate(metric)]
        tex.append(" & ".join([gpu,a["model"],str(a["sessions"]),str(a["unique_sources"]),topology,"S" if a["arrival"]=="sync" else "T",*vals])+r" \\")
    tex += [r"\bottomrule",r"\end{tabular}",r"\end{table*}"]
    (ROOT/"Paper_TC/tables/t11_live_ground_truth.tex").write_text("\n".join(tex)+"\n",encoding="utf8")
    print(json.dumps({"decision":audit["decision"],"runs":96,"pairs":36,"rows":aggregates},ensure_ascii=False))

def verify_csv(path):
    with path.open(encoding="utf8",newline="") as f:rows=list(csv.DictReader(f))
    for r in rows:
        ref=tokens(r["reference"],r["language"])
        hyp=tokens(r["hypothesis"],r["language"])
        n=edits(ref,hyp)
        assert n==int(r["edit_errors"]) and len(ref)==int(r["reference_units"])
        assert abs(n/len(ref)-float(r["error_rate"]))<1e-12
    print(json.dumps({"decision":"PASS_CSV_RESCORING","source_run_rows":len(rows)}))

if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--verify-csv",type=Path)
    args=parser.parse_args()
    verify_csv(args.verify_csv) if args.verify_csv else main()

"""Independent local, retrospective text/service recount for all three pilot cells.

No model calls. Original primary endpoints are verified, never replaced.
The vendored native-content endpoint is byte-identical to its earlier freeze.
"""
from __future__ import annotations
import argparse, hashlib, json, platform, subprocess, sys
from collections import Counter
from pathlib import Path
from native_content_endpoint import analyze_cell, normalize


def sha(data): return hashlib.sha256(data).hexdigest()
def load(path): return json.loads(Path(path).read_text(encoding="utf-8"))
def put(path, value):
    with Path(path).open("x", encoding="utf-8", newline="\n") as f:
        json.dump(value, f, ensure_ascii=False, indent=2, allow_nan=False); f.write("\n")


def quantile(values, p):
    values=sorted(values); x=(len(values)-1)*p; lo=int(x)
    return values[lo]+(values[min(lo+1,len(values)-1)]-values[lo])*(x-lo)


def same_f_support(row, canonical):
    G=row["visible_frontier"]; reference=canonical.get(G)
    return dict(actual_view_frontier=G, exact_reference_exists=reference is not None,
                reference_state_sha256=reference["state_sha256"] if reference else None,
                reference_text=reference["state"]["transcript"] if reference else None,
                raw_equal=row["text"]==reference["state"]["transcript"] if reference else None,
                whitespace_stripped_equal=normalize(row["text"])==normalize(reference["state"]["transcript"]) if reference else None)


def analyze(meta, config, origin, rows, wal, primary, captured_content):
    sources={s["source_id"]:s for s in config["settings"]["sources"]}
    assert len(sources)==1
    rr,events,spans,frontiers=analyze_cell(meta,rows,sources,origin["origin_perf"])
    assert origin["original_D"]==2. and origin["original_C"]==8.
    assert abs(rr["original_dual_credit_audio_seconds"]-primary["dual_deadline_audio_credit_seconds"])<1e-9
    assert rr["offered_frontiers"]==primary["offered_frontiers"]
    assert abs(rr["offered_audio_seconds"]-primary["offered_audio_seconds"])<1e-9
    for mode in ("raw","whitespace_stripped"):
        assert rr[mode]==captured_content[mode]
    assert abs(quantile([f["D"] for f in frontiers],.99)-primary["primary_linear_all_offered_D99"])<1e-9
    assert abs(quantile([f["C"] for f in frontiers],.99)-primary["primary_linear_all_offered_C99"])<1e-9
    assert sum(f["D"]>2 for f in frontiers)==primary["D2_misses_all_offered"]
    assert sum(f["C"]>8 for f in frontiers)==primary["C8_misses_all_offered"]
    canonical={}
    for row in wal:
        F=row["state"]["frontier"]
        assert F not in canonical
        canonical[F]=row
    first_by_F={}; unique_views={}; withdrawals=[]; corrections=[]
    previous=None
    for i,row in enumerate(rows):
        G=row["visible_frontier"]
        if G>0:
            item=dict(cell_id=meta["cell_id"],row_index=i,source_id=row["source_id"],
                      observed_perf=row["observed"],text=row["text"],view_node=row["view_node"],
                      text_support=same_f_support(row,canonical))
            first_by_F.setdefault(G,item)
            unique_views.setdefault((G,row["text"]),item)
        if previous and G<previous["visible_frontier"]:
            withdrawals.append(dict(cell_id=meta["cell_id"],row_index=i,kind=row["kind"],
                                    before=previous["visible_frontier"],after=G,
                                    classification="REQUIRES_COMPLETE_DEPENDENCY_RECONSTRUCTION"))
        if previous and events[i]["raw"]["erased_code_points"]:
            correction=dict(cell_id=meta["cell_id"],row_index=i,kind=row["kind"],
                            before_F=previous["visible_frontier"],after_F=G,
                            before_text=previous["text"],after_text=row["text"],
                            previous_view_kind=previous["view_node"]["kind"],
                            raw_LCP_erased=events[i]["raw"]["erased_code_points"],
                            new_text_support=same_f_support(row,canonical))
            corrections.append(correction)
        previous=row
    # No observed F withdrawal needs a compatibility label in this pilot.
    # Future nonzero cases remain unclassified rather than trusting runtime flags.
    summary=dict(meta,primary=primary,original_credit_preserved=True,content_recount=rr,
                 audio_frontier_withdrawals=len(withdrawals),
                 compatible_audio_frontier_withdrawals=0 if not withdrawals else None,
                 incompatible_audio_frontier_withdrawals=0 if not withdrawals else None,
                 actual_text_LCP_retraction_rows=len(corrections),
                 canonical_text_replacement_rows=sum(c["kind"]=="canonical" for c in corrections),
                 positive_F_first_views=len(first_by_F),unique_positive_F_raw_text_views=len(unique_views))
    for f in frontiers:
        d=rows[f["first_visible_row"]]
        G=d["visible_frontier"]
        assert G>=f["frontier"]
        f["first_visible_text"]=d["text"]
        f["first_visible_view_kind"]=d["view_node"]["kind"]
        f["support_at_actual_view_G"]=same_f_support(d,canonical)
        f["offered_F_equals_actual_view_G"]=G==f["frontier"]
        f["support_at_exact_offered_F"]={
            "comparable":G==f["frontier"],
            "raw_equal":d["text"]==canonical[f["frontier"]]["state"]["transcript"] if G==f["frontier"] else None,
            "whitespace_stripped_equal":normalize(d["text"])==normalize(canonical[f["frontier"]]["state"]["transcript"]) if G==f["frontier"] else None}
        f["EOS"]=f["frontier"]==sources[f["source_id"]]["frames"]
    for mode in ("raw","whitespace_stripped"):
        key=mode+"_equal"
        summary[mode+"_support"]={
            "all_offered_first_covers_same_actual_G_matching_rows":sum(f["support_at_actual_view_G"][key] is True for f in frontiers),
            "all_offered_first_covers_same_actual_G_matching_audio_seconds":sum(f["audio_seconds"] for f in frontiers if f["support_at_actual_view_G"][key] is True),
            "all_offered_first_covers_mismatching_F_seconds":[f["frontier"]/16000 for f in frontiers if f["support_at_actual_view_G"][key] is False],
            "original_credit_with_same_actual_G_complete_text_match":sum(f["audio_seconds"] for f in frontiers if f["original_dual_credit"] and f["support_at_actual_view_G"][key] is True),
            "original_credit_with_same_actual_G_complete_text_mismatch":sum(f["audio_seconds"] for f in frontiers if f["original_dual_credit"] and f["support_at_actual_view_G"][key] is False),
            "original_credit_with_exact_offered_F_aligned_text_match":sum(f["audio_seconds"] for f in frontiers if f["original_dual_credit"] and f["support_at_exact_offered_F"][key] is True),
            "higher_F_first_cover_rows":sum(not f["offered_F_equals_actual_view_G"] for f in frontiers),
            "higher_F_first_cover_original_credit_seconds":sum(f["audio_seconds"] for f in frontiers if f["original_dual_credit"] and not f["offered_F_equals_actual_view_G"]),
            "positive_F_first_views_matched":sum(x["text_support"][key] is True for x in first_by_F.values()),
            "positive_F_first_views_mismatched":sum(x["text_support"][key] is False for x in first_by_F.values()),
            "unique_F_text_views_matched":sum(x["text_support"][key] is True for x in unique_views.values()),
            "unique_F_text_views_mismatched":sum(x["text_support"][key] is False for x in unique_views.values()),
        }
    full=[f for f in frontiers if not f["EOS"]]
    summary["EOS_and_complete_intervals"]={
        "complete_interval_count":len(full),"complete_interval_audio_seconds":sum(f["audio_seconds"] for f in full),
        "complete_interval_D2_misses":sum(f["D"]>2 for f in full),"complete_interval_C8_misses":sum(f["C"]>8 for f in full),
        "complete_interval_D_max":max(f["D"] for f in full),"complete_interval_C_max":max(f["C"] for f in full),
        "EOS":[{k:f[k] for k in ("frontier","audio_seconds","D","C","original_dual_credit")} for f in frontiers if f["EOS"]]}
    return summary,frontiers,events,spans,list(first_by_F.values()),list(unique_views.values()),withdrawals,corrections


def source_gate(manifest):
    root=Path(__file__).resolve().parent
    git=lambda *a:subprocess.check_output(["git","-C",str(root),*a],text=True).strip()
    assert Path(git("rev-parse","--show-toplevel")).resolve()==root
    assert git("rev-parse","HEAD")==manifest["code_commit"]
    assert not git("status","--porcelain","--untracked-files=all")
    assert set(git("ls-files").splitlines())=={f["path"] for f in manifest["files"]}
    for item in manifest["files"]: assert sha((root/item["path"]).read_bytes())==item["sha256"]


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    ap=argparse.ArgumentParser();ap.add_argument("--config",type=Path,required=True);ap.add_argument("--source-manifest",type=Path,required=True);ap.add_argument("--out",type=Path,required=True);args=ap.parse_args()
    config=load(args.config);manifest=load(args.source_manifest);source_gate(manifest)
    args.out.mkdir(exist_ok=False)
    put(args.out/"CONFIG.json",config)
    environment=dict(python=sys.version,platform=platform.platform(),new_model_calls=0,execution="local offline only")
    assert environment==config["frozen_environment"]
    put(args.out/"ENVIRONMENT.json",environment)
    put(args.out/"RUN_RECORD.json",dict(experiment_id=config["experiment_id"],code_commit=manifest["code_commit"],
        source_manifest_sha256=sha(args.source_manifest.read_bytes()),frozen_config_sha256=sha(args.config.read_bytes()),
        environment_sha256=sha((args.out/"ENVIRONMENT.json").read_bytes()),
        actual_neural_source_commit=config["actual_neural_source_commit"],
        raw_result_location=config["raw_result_location"],aggregate_summary_location=str(args.out/"SUMMARY.json"),gate_decision_location=str(args.out/"GATE.json")))
    try:
        root=Path(config["raw_result_location"]);inputs={};used=0
        def checked(name,jsonl=False):
            nonlocal used
            b=(root/name).read_bytes(); item=config["inputs"][name]
            assert len(b)==item["bytes"] and sha(b)==item["sha256"]
            used+=len(b); assert used<=config["max_input_bytes"]
            inputs[name]=dict(bytes=len(b),sha256=sha(b))
            return [json.loads(x) for x in b.decode("utf-8").splitlines() if x] if jsonl else json.loads(b)
        results=[];all_f=[];all_e=[];all_s=[];all_first=[];all_unique=[];all_w=[];all_c=[];canonical_histories=[]
        for cell in config["cells"]:
            prefix=cell["cell_id"]+"/"
            cfg=checked(prefix+"CONFIG.json");origin=checked(prefix+"ORIGIN.json");rows=checked(prefix+"consumer.jsonl",True)
            wal=checked(prefix+"canonical_wal.jsonl",True);primary=checked(prefix+"PRIMARY_METRICS.json");content=checked(prefix+"CONTENT.json")
            assert cfg["settings"]["source_commit"]==config["actual_neural_source_commit"]
            assert cfg["arm"]==cell["arm"]
            for file,field in (("CONFIG.json","config_sha256"),("ORIGIN.json","origin_sha256"),("consumer.jsonl","consumer_sha256")):
                assert primary["raw_inputs"][field]==config["inputs"][prefix+file]["sha256"]
            rr,ff,ee,ss,first,unique,ww,cc=analyze(cell,cfg,origin,rows,wal,primary,content)
            results.append(rr);all_f.extend(ff);all_e.extend(ee);all_s.extend(ss);all_first.extend(first);all_unique.extend(unique);all_w.extend(ww);all_c.extend(cc);canonical_histories.append(wal)
        assert len(results)==3
        assert all(h==canonical_histories[0] for h in canonical_histories[1:])
        assert len(canonical_histories[0])==17
        outputs={"RUNS":results,"FIRST_COVERS_WITH_EXACT_F_SUPPORT":all_f,"ACTUAL_TEXT_EVENTS":all_e,
                 "LCP_OCCURRENCE_SPANS":all_s,"FIRST_ACTUAL_VIEW_PER_POSITIVE_F":all_first,
                 "FIRST_UNIQUE_F_TEXT_VIEWS":all_unique,"FRONTIER_WITHDRAWALS":all_w,
                 "CANONICAL_TEXT_REPLACEMENTS":all_c,"INPUT_HASHES":inputs}
        for name,value in outputs.items():put(args.out/(name+".json"),value)
        source_gate(manifest)
        assert sum(p.stat().st_size for p in args.out.iterdir())<=config["max_output_bytes"]
        put(args.out/"SUMMARY.json",dict(status="COMPLETE_ALL3_INDEPENDENT_LOCAL_CONTENT_RECOUNT",cells=3,new_model_calls=0,
            all_original_primary_credits_and_P99_preserved=True,all_captured_content_summaries_reproduced=True,
            full_Canonical_state_selection_and_dispatch_epoch_histories_equal=True,canonical_steps_per_cell=17,
            input_bytes=used,interpretation="Retrospective exact-frontier complete-text support; no groundtruth claim, token/audio alignment or changed service metric."))
        put(args.out/"GATE.json",dict(gate="PASS_ALL3_PILOT_CONTENT_SERVICE_RECOUNT",source_commit=manifest["code_commit"]))
        print(json.dumps(dict(gate="PASS_ALL3_PILOT_CONTENT_SERVICE_RECOUNT",summary=[dict(arm=r["arm"],original_credit=r["primary"]["dual_deadline_audio_credit_seconds"],same_actual_G_supported_credit=r["raw_support"]["original_credit_with_same_actual_G_complete_text_match"],exact_offered_F_aligned_supported_credit=r["raw_support"]["original_credit_with_exact_offered_F_aligned_text_match"],frontier_withdrawals=r["audio_frontier_withdrawals"]) for r in results]),ensure_ascii=False))
    except BaseException as exc:
        put(args.out/"GATE.json",dict(gate="FAIL_PRESERVED_PILOT_CONTENT_RECOUNT",exception_type=type(exc).__name__,reason=str(exc)));raise


if __name__=="__main__":main()

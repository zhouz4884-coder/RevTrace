"""Independent four-new-speaker/16-cell driver; c12803e definitions unchanged."""
from __future__ import annotations
import argparse,json,platform,sys
from collections import defaultdict
from pathlib import Path
from analyze_pilot_content import analyze,load,put,sha,source_gate
from analyze_confirmation import independent_sources


def contrast(base,new):
    """Paired all-offered accounting; no interval is dropped for text mismatch."""
    b={f["frontier"]:f for f in base};n={f["frontier"]:f for f in new}
    assert b.keys()==n.keys()
    for F in b:assert b[F]["audio_seconds"]==n[F]["audio_seconds"]
    result={}
    for label,mode in (("original_credit",None),("raw_same_actual_G_supported_credit","raw_equal"),("whitespace_same_actual_G_supported_credit","whitespace_stripped_equal")):
        def credited(f):return f["original_dual_credit"] and (mode is None or f["support_at_actual_view_G"][mode] is True)
        bsum=sum(f["audio_seconds"] for f in b.values() if credited(f));nsum=sum(f["audio_seconds"] for f in n.values() if credited(f))
        gain=sum(n[F]["audio_seconds"] for F in b if credited(n[F]) and not credited(b[F]))
        loss=sum(b[F]["audio_seconds"] for F in b if credited(b[F]) and not credited(n[F]))
        assert abs(nsum-bsum-(gain-loss))<1e-9
        result[label]=dict(conservative_seconds=bsum,fullspec_seconds=nsum,net_fullspec_minus_conservative_seconds=nsum-bsum,
                           gross_gained_seconds=gain,gross_lost_seconds=loss,
                           gained_frontier_seconds=[F/16000 for F in b if credited(n[F]) and not credited(b[F])],
                           lost_frontier_seconds=[F/16000 for F in b if credited(b[F]) and not credited(n[F])])
    return result


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    ap=argparse.ArgumentParser();ap.add_argument("--config",type=Path,required=True);ap.add_argument("--source-manifest",type=Path,required=True);ap.add_argument("--out",type=Path,required=True);a=ap.parse_args()
    cfg=load(a.config);manifest=load(a.source_manifest);source_gate(manifest)
    environment=dict(python=sys.version,platform=platform.platform(),new_model_calls=0,execution="local offline only")
    assert environment==cfg["frozen_environment"]
    a.out.mkdir(exist_ok=False)
    put(a.out/"CONFIG.json",cfg);put(a.out/"ENVIRONMENT.json",environment)
    put(a.out/"RUN_RECORD.json",dict(experiment_id=cfg["experiment_id"],code_commit=manifest["code_commit"],
        unchanged_endpoint_source_commit=cfg["unchanged_endpoint_source_commit"],source_manifest_sha256=sha(a.source_manifest.read_bytes()),
        frozen_config_sha256=sha(a.config.read_bytes()),environment_sha256=sha((a.out/"ENVIRONMENT.json").read_bytes()),
        actual_neural_source_commit=cfg["actual_neural_source_commit"],raw_result_location=cfg["raw_result_location"],
        aggregate_summary_location=str(a.out/"SUMMARY.json"),gate_decision_location=str(a.out/"GATE.json")))
    try:
        root=Path(cfg["raw_result_location"]);inputs={};used=0
        provenance={}
        for key in ("source_receipt","metadata_selection","appraisal","method_freeze"):
            p=Path(cfg[key]);assert sha(p.read_bytes())==cfg[key+"_sha256"];provenance[key]=load(p)
        acoustic=independent_sources(provenance["source_receipt"],provenance["metadata_selection"],provenance["appraisal"],provenance["method_freeze"])
        def checked(name,jsonl=False):
            nonlocal used
            b=(root/name).read_bytes();expected=cfg["inputs"][name]
            assert len(b)==expected["bytes"] and sha(b)==expected["sha256"]
            used+=len(b);assert used<=cfg["max_input_bytes"]
            inputs[name]=dict(bytes=len(b),sha256=sha(b))
            return [json.loads(x) for x in b.decode("utf-8").splitlines() if x] if jsonl else json.loads(b)
        results=[];all_f=[];all_e=[];all_s=[];all_first=[];all_unique=[];all_w=[];all_c=[]
        canonical_by_source=defaultdict(list);by_pair=defaultdict(dict);frontiers_by_cell={}
        for cell in cfg["cells"]:
            prefix=cell["cell_id"]+"/"
            cc=checked(prefix+"CONFIG.json");origin=checked(prefix+"ORIGIN.json");rows=checked(prefix+"consumer.jsonl",True)
            wal=checked(prefix+"canonical_wal.jsonl",True);primary=checked(prefix+"PRIMARY_METRICS.json");content=checked(prefix+"CONTENT.json")
            assert cc["settings"]["source_commit"]==cfg["actual_neural_source_commit"] and cc["arm"]==cell["arm"]
            assert len(cc["settings"]["sources"])==1 and cc["settings"]["sources"][0]["source_id"]==cell["source_id"]
            assert cc["settings"]["sources"][0]==next(s for s in provenance["source_receipt"]["sources"] if s["source_id"]==cell["source_id"])
            for file,field in (("CONFIG.json","config_sha256"),("ORIGIN.json","origin_sha256"),("consumer.jsonl","consumer_sha256")):
                assert primary["raw_inputs"][field]==cfg["inputs"][prefix+file]["sha256"]
            rr,ff,ee,ss,first,unique,ww,corrections=analyze(cell,cc,origin,rows,wal,primary,content)
            for mode in ("raw","whitespace_stripped"):
                support=rr[mode+"_support"];key=mode+"_equal"
                support["all_offered_unknown_actual_G_reference_rows"]=sum(f["support_at_actual_view_G"][key] is None for f in ff)
                support["all_offered_unknown_actual_G_reference_audio_seconds"]=sum(f["audio_seconds"] for f in ff if f["support_at_actual_view_G"][key] is None)
                support["original_credit_with_unknown_actual_G_reference_audio_seconds"]=sum(f["audio_seconds"] for f in ff if f["original_dual_credit"] and f["support_at_actual_view_G"][key] is None)
            results.append(rr);all_f.extend(ff);all_e.extend(ee);all_s.extend(ss);all_first.extend(first);all_unique.extend(unique);all_w.extend(ww);all_c.extend(corrections)
            frontiers_by_cell[cell["cell_id"]]=ff
            canonical_by_source[cell["source_id"]].append(wal)
            key=(cell["source_id"],cell["repeat"])
            assert cell["arm"] not in by_pair[key];by_pair[key][cell["arm"]]=rr
        assert len(results)==cfg["expected_cells"]==16
        assert len(all_f)==cfg["expected_offered_frontiers"]==272
        assert len(canonical_by_source)==4
        for source,histories in canonical_by_source.items():
            assert len(histories)==4 and all(h==histories[0] for h in histories[1:])
        pairs=[]
        for (source,repeat),arms in sorted(by_pair.items()):
            assert set(arms)=={"two_full_early","two_full_spec_early"}
            base,new=arms["two_full_early"],arms["two_full_spec_early"]
            pair=dict(source_id=source,repeat=repeat,offered_audio_seconds=base["primary"]["offered_audio_seconds"],
                      conservative_cell=base["cell_id"],fullspec_cell=new["cell_id"],
                      contrast=contrast(frontiers_by_cell[base["cell_id"]],frontiers_by_cell[new["cell_id"]]))
            for label,run in (("conservative",base),("fullspec",new)):
                pair[label]=dict(primary=run["primary"],raw_support=run["raw_support"],whitespace_support=run["whitespace_stripped_support"],
                                 raw_text=run["content_recount"]["raw"],whitespace_text=run["content_recount"]["whitespace_stripped"],
                                 EOS_and_complete_intervals=run["EOS_and_complete_intervals"],audio_frontier_withdrawals=run["audio_frontier_withdrawals"])
            pairs.append(pair)
        assert len(pairs)==8
        aggregates={}
        for arm in ("two_full_early","two_full_spec_early"):
            runs=[r for r in results if r["arm"]==arm]
            aggregates[arm]=dict(cells=len(runs),offered_frontiers=sum(r["primary"]["offered_frontiers"] for r in runs),
                offered_audio_seconds=sum(r["primary"]["offered_audio_seconds"] for r in runs),
                original_credit_seconds=sum(r["primary"]["dual_deadline_audio_credit_seconds"] for r in runs),
                raw_same_actual_G_supported_credit=sum(r["raw_support"]["original_credit_with_same_actual_G_complete_text_match"] for r in runs),
                raw_same_actual_G_mismatching_credit=sum(r["raw_support"]["original_credit_with_same_actual_G_complete_text_mismatch"] for r in runs),
                raw_same_actual_G_unknown_credit=sum(r["raw_support"]["original_credit_with_unknown_actual_G_reference_audio_seconds"] for r in runs),
                raw_unknown_actual_G_rows=sum(r["raw_support"]["all_offered_unknown_actual_G_reference_rows"] for r in runs),
                raw_exact_offered_F_aligned_supported_credit=sum(r["raw_support"]["original_credit_with_exact_offered_F_aligned_text_match"] for r in runs),
                whitespace_same_actual_G_supported_credit=sum(r["whitespace_stripped_support"]["original_credit_with_same_actual_G_complete_text_match"] for r in runs),
                whitespace_same_actual_G_unknown_credit=sum(r["whitespace_stripped_support"]["original_credit_with_unknown_actual_G_reference_audio_seconds"] for r in runs),
                whitespace_unknown_actual_G_rows=sum(r["whitespace_stripped_support"]["all_offered_unknown_actual_G_reference_rows"] for r in runs),
                raw_credit_first_row_classes={k:sum(r["content_recount"]["raw"]["original_credit_by_first_visible_row_class"][k] for r in runs) for k in ("strict_append","unchanged","replacement","erase_only","not_observed")},
                raw_introduced_occurrences=sum(r["content_recount"]["raw"]["introduced_code_point_occurrences"] for r in runs),
                raw_LCP_erased_occurrences=sum(r["content_recount"]["raw"]["LCP_erased_code_point_occurrences"] for r in runs),
                raw_final_observed_code_points=sum(r["content_recount"]["raw"]["final_observed_text_code_points"] for r in runs),
                whole_D2_C8_P99_pass_cells=sum(r["primary"]["complete_coverage_and_original_quantile_pass"] for r in runs),
                D2_misses=sum(r["primary"]["D2_misses_all_offered"] for r in runs),C8_misses=sum(r["primary"]["C8_misses_all_offered"] for r in runs),
                nonEOS_D2_misses=sum(r["EOS_and_complete_intervals"]["complete_interval_D2_misses"] for r in runs),
                EOS_D2_misses=sum(e["D"]>2 for r in runs for e in r["EOS_and_complete_intervals"]["EOS"]),
                audio_frontier_withdrawals=sum(r["audio_frontier_withdrawals"] for r in runs))
        outputs={"RUNS":results,"PAIRS":pairs,"AGGREGATES":aggregates,"FIRST_COVERS_WITH_EXACT_F_SUPPORT":all_f,"ACTUAL_TEXT_EVENTS":all_e,
                 "LCP_OCCURRENCE_SPANS":all_s,"FIRST_ACTUAL_VIEW_PER_POSITIVE_F":all_first,"FIRST_UNIQUE_F_TEXT_VIEWS":all_unique,
                 "FRONTIER_WITHDRAWALS":all_w,"CANONICAL_TEXT_REPLACEMENTS":all_c,"INPUT_HASHES":inputs}
        for name,value in outputs.items():put(a.out/(name+".json"),value)
        source_gate(manifest)
        assert sum(p.stat().st_size for p in a.out.iterdir())<=cfg["max_output_bytes"]
        put(a.out/"SUMMARY.json",dict(status="COMPLETE_ALL16_INDEPENDENT_NEW_SPEAKER_CONTENT_RECOUNT",cells=16,pairs=8,offered_frontiers=272,
            new_model_calls=0,all_original_primary_credit_P99_and_misses_preserved=True,all_captured_content_summaries_reproduced=True,
            all_complete_Canonical_WAL_objects_equal_within_each_source=True,independent_acoustic_sources=4,fresh_repeats_per_arm_source=2,
            source_selection="four metadata-first new speaker-disjoint acoustic sources; two repeated processes perarm/source, not eight acoustic units",acoustic_units=acoustic,input_bytes=used,aggregates=aggregates))
        put(a.out/"GATE.json",dict(gate="PASS_ALL16_272_ORIGINAL_AND_CONTENT_RECOUNT",code_commit=manifest["code_commit"],unchanged_endpoint_source_commit=cfg["unchanged_endpoint_source_commit"]))
        print(json.dumps(dict(gate="PASS_ALL16_272_ORIGINAL_AND_CONTENT_RECOUNT",aggregates=aggregates),ensure_ascii=False))
    except BaseException as exc:
        put(a.out/"GATE.json",dict(gate="FAIL_PRESERVED_CONFIRMATION_CONTENT_RECOUNT",exception_type=type(exc).__name__,reason=str(exc)));raise


if __name__=="__main__":main()

"""Strict complete-state/C/ID reference audit plus actual Consumer recount."""
from __future__ import annotations
import hashlib, pathlib
from common import need,read,lines,sha,canonical,mapped_state,verified_facts
from endpoints import recount
from external_power import energy

def selected_trace(out,config,reference,actual):
    out=pathlib.Path(out);sources={s['source_id']:s for s in config['settings']['sources']};refs={(r['source_id'],r['end']):r for r in reference};steps=[]
    if (out/'facts.wal').exists():
        roots={};sequence=0
        for obj in verified_facts(out/'facts.wal'):
            if obj['kind']=='genesis':
                need(not roots and obj['sequence']==1,'duplicate fact genesis');roots=obj['body']['initials'];need(set(roots)==set(sources),'fact genesis source set');continue
            need(obj['kind']=='canonical','unknown complete fact kind');b=obj['body'];sid=b['source_id'];r=b['record'];start=b['parent_state'];end=b['next_state'];job=b['job']
            need(sid in roots and roots[sid]==start,'fact parent chain differs');need(job['source_id']==sid and job['start']==start and job['end']==end['frontier'],'fact owned input binding differs')
            need(r['start_state']==hashlib.sha256(canonical(start)).hexdigest() and r['end_state']==hashlib.sha256(canonical(end)).hexdigest(),'fact input/output digest differs')
            need(r['role']=='authority' and r['candidate_handoff'] is False,'not protected original complete C/U')
            need(end['frontier']==min(sources[sid]['frames'],start['frontier']+8000),'original cadence/EOS changed');roots[sid]=end;steps.append((sid,start,end,r))
    else:
        histories=read(out/'CANONICAL_HISTORIES.json');wal=lines(out/'canonical_wal.jsonl');jobs=lines(out/'native_jobs.jsonl');by={(r['source_id'],r['end']['frontier']):r for r in jobs};need(set(histories)==set(sources),'history source set')
        for sid,history in histories.items():
            commits=[r for r in wal if r['source_id']==sid];need(len(commits)==len(history),'WAL history length')
            for h,w in zip(history,commits):
                need(h['state']==w['state'] and h['F']==h['state']['frontier'],'history/WAL differs');event=by[(sid,h['F'])];r=event['record']
                need(event['end']==h['state'] and r['token_ids']==h['token_ids'] and r['selected_correction']==w['selected'],'actual completed result differs from installed history')
                steps.append((sid,event['start'],event['end'],r))
        roots={sid:history[-1]['state'] for sid,history in histories.items()}
    expected=sum((s['frames']+7999)//8000 for s in sources.values());need(len(steps)==expected,'missing/duplicate original steps')
    seen=set()
    for sid,start,end,r in steps:
        key=(sid,end['frontier']);need(key not in seen and key in refs,'duplicate/unreferenced frontier');seen.add(key);ref=refs[key]
        need(mapped_state(start,actual)==mapped_state(ref['original_full_start_cut'],actual),'complete original input state differs')
        need(mapped_state(end,actual)==mapped_state(ref['original_full_cut'],actual),'complete original output state differs')
        need(r['token_ids']==ref['original_full_result']['token_ids'] and r['selected_correction']==ref['original_full_result']['selected_correction'],'original selected C/returned IDs differ')
    consumer=lines(out/'consumer.jsonl')
    for sid,source in sources.items():
        need(roots[sid]['frontier']==source['frames'],'final Canonical EOS incomplete');eligible=[r for r in consumer if r['source_id']==sid and r['certified_frontier']==source['frames']]
        need(eligible and eligible[-1]['canonical_sha']==hashlib.sha256(canonical(roots[sid])).hexdigest(),'actual Consumer lacks exact final certified EOS')
    return dict(status='PASS_COMPLETE_SELECTED_TRACE_REFERENCE',checked_steps=len(steps),sources=len(sources),projection='only exact source marker BDFA/current -> BDFA; no other field removed',actual_NN_source_commit=actual,reference_is_offline_not_serving=True)

def audit_cell(cell,config,reference,observer):
    out=pathlib.Path(cell['out']);origin=read(out/'ORIGIN.json')['origin_perf'];rows=lines(out/'consumer.jsonl');sources={s['source_id']:s for s in config['settings']['sources']}
    primary=recount(rows,sources,{sid:origin for sid in sources});semantic=selected_trace(out,config,reference,config['settings']['source_commit'])
    eos=max(min(r['observed'] for r in rows if r['source_id']==sid and r['certified_frontier']==s['frames']) for sid,s in sources.items())
    original=read(out/'ENERGY.json') if (out/'ENERGY.json').exists() else read(out/'SUMMARY.json')['energy']
    shared=dict(origin_to_useful_certified_EOS=energy(observer.path,origin,eos),origin_to_confirmed_physical_model_drain=energy(observer.path,origin,observer.drain['confirmed_perf']),physical_drain_observation=observer.drain,useful_EOS_definition='actual Consumer certified frontier reaches each original EOS after full C/U; not provisional display/replay',original_source_energy=original,original_source_windows_are_preserved_not_assumed_identical=True)
    return dict(cell_id=cell['cell_id'],source_id=cell['source_id'],version=cell['version'],strategy=cell['strategy'],repeat=cell['repeat'],primary=primary,semantic=semantic,common_external_energy=shared,raw_result_location=str(out),summary_sha256=sha(out/'SUMMARY.json'))

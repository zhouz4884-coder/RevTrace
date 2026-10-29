"""Extract a witnessed same-root example from two original service cells."""
from pathlib import Path
from collections import defaultdict
import argparse,hashlib,json,platform,subprocess,sys
from interaction_opportunities_v1 import complete_chain

H=Path(__file__).resolve().parent
INPUTS={}
def digest(b):return hashlib.sha256(b).hexdigest()
def read(p,lines=False):
    b=Path(p).read_bytes();INPUTS[str(p)]=dict(bytes=len(b),sha256=digest(b))
    return [json.loads(x) for x in b.decode().splitlines() if x] if lines else json.loads(b)
def put(p,v):
    with Path(p).open('x') as f:json.dump(v,f,indent=2,allow_nan=False);f.write('\n')
def source_gate(m):
    git=lambda *a:subprocess.check_output(['git','-C',str(H),*a],text=True).strip()
    assert Path(git('rev-parse','--show-toplevel')).resolve()==H
    assert git('rev-parse','HEAD')==m['code_commit'] and not git('status','--porcelain','--untracked-files=all')
    assert set(git('ls-files').splitlines())=={r['path'] for r in m['files']}
    for r in m['files']:assert (H/r['path']).stat().st_size==r['bytes'] and digest((H/r['path']).read_bytes())==r['sha256']
def main():
    p=argparse.ArgumentParser();p.add_argument('--config',type=Path,required=True);p.add_argument('--config-sha256',required=True)
    p.add_argument('--source-manifest',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    assert digest(a.config.read_bytes())==a.config_sha256;m=read(a.source_manifest);source_gate(m);cfg=read(a.config);out=a.output;out.mkdir(parents=True,exist_ok=False)
    put(out/'CONFIG.json',cfg);put(out/'ENVIRONMENT.json',dict(python=sys.version,platform=platform.platform(),hostname=platform.node(),new_model_calls=0))
    put(out/'RUN_RECORD.json',dict(experiment_id=cfg['experiment_id'],code_commit=m['code_commit'],source_manifest_sha256=digest(a.source_manifest.read_bytes()),
        frozen_config_sha256=a.config_sha256,environment_sha256=digest((out/'ENVIRONMENT.json').read_bytes()),raw_result_location=[c['path'] for c in cfg['cells']],
        aggregate_summary_location=str(out/'SUMMARY.json'),gate_decision_location=str(out/'GATE.json')))
    proofs=[];histories=[];hypotheses=[]
    for c in cfg['cells']:
        d=Path(c['path']);sid=cfg['session_id'];F=cfg['shared_F'];D=out/c['arm'];D.mkdir()
        assert read(d/'GATE.json')['gate']=='PASS_SINGLE_CELL_EXECUTION_AND_INDEPENDENT_AUDIT'
        for name in ('events.jsonl','consumer.jsonl','worker_records.jsonl','sessions.json'):
            file=d/'attempt0'/name;expected=cfg['expected_inputs'][str(file)]
            assert file.stat().st_size==expected['bytes'] and digest(file.read_bytes())==expected['sha256']
        all_events=read(d/'attempt0/events.jsonl',True);events=[r for r in all_events if r.get('session_id')==sid or r['kind']=='run-start']
        consumer=[r for r in read(d/'attempt0/consumer.jsonl',True) if r['session_id']==sid]
        workers=[r for r in read(d/'attempt0/worker_records.jsonl',True) if r['job']['session_id']==sid]
        session=next(r for r in read(d/'attempt0/sessions.json') if r['session_id']==sid)
        assert session['source_id']==cfg['source_id']
        episode=read(d/'episode.json');original_manifest=read(d/'manifest.json');meta=next(r for r in original_manifest['sessions'] if r['source_id']==cfg['source_id'])
        records={r['job']['job_id']:r for r in workers};owner=next(r['t0_perf'] for r in events if r['kind']=='run-start')
        commit=next(r for r in events if r['kind']=='commit' and r['audio_end_sample']==F)
        authority=records[commit['job_id']]
        assert authority['job']['role']=='authority' and authority['result']['token_ids']==commit['segment_tokens'] and authority['result']['state_tokens']==commit['next_prompt_tokens']
        pub=next(r for r in events if r['kind']=='canonical-display' and r['version']==commit['version'])
        index=next(i for i,r in enumerate(consumer) if r['source_kind']=='canonical-display' and r['server_time']==pub['displayed'])
        before,after=consumer[index-1],consumer[index]
        assert before['valid_visible_frontier']>F and after['certified_frontier']==F
        visible_job=None;previous=None
        event_lookup={(r['kind'],r.get('displayed')):r for r in events if r['kind'] in ('display','canonical-display','view-mode')}
        for r in consumer[:index]:
            e=event_lookup.get((r['source_kind'],r['server_time']))
            if r['source_kind']=='display' and e and e['text']==r['visible_text'] and e['audio_end_sample']==r['valid_visible_frontier']:visible_job=e['job_id']
            elif previous is None or (previous['valid_visible_frontier'],previous['visible_text'])!=(r['valid_visible_frontier'],r['visible_text']):visible_job=None
            previous=r
        assert visible_job==c['expected_visible_job'] and commit['job_id']==c['expected_selected_job']
        published={e['job_id'] for e in events if e['kind']=='display' and owner+e['displayed']<=after['observed_perf']}
        compatible,reason,chain=complete_chain(visible_job,F,commit['next_prompt_tokens'],records,published,32000)
        assert compatible is True
        history=[dict(F=e['audio_end_sample'],Z=e['segment_tokens'],P=e['next_prompt_tokens'],text=records[e['job_id']]['result']['text']) for e in events if e['kind']=='commit']
        histories.append(history);hypotheses.append({k:records[visible_job]['result'][k] for k in ('token_ids','state_tokens','text')})
        origin=episode['origin_perf']+session['offset']
        proof=dict(arm=c['arm'],session_id=sid,source_id=cfg['source_id'],shared_F=F,
            selected_job=commit['job_id'],visible_job=visible_job,chain=chain,compatible=compatible,reason=reason,
            actual_input_prompt_tokens=records[visible_job]['result']['execution_context_audit']['executed_prompt_tokens'],
            selected_next_prompt_tokens=commit['next_prompt_tokens'],
            before_visible_F=before['valid_visible_frontier'],after_visible_F=after['valid_visible_frontier'],
            original_source_origin_perf=origin,Consumer_canonical_apply_seconds=after['observed_perf']-origin,
            before_observed_seconds=before['observed_perf']-origin,
            outcome='retained_same_complete_view' if (after['valid_visible_frontier'],after['visible_text'])==(before['valid_visible_frontier'],before['visible_text']) else 'withdrawn_to_canonical',
            note='Proof recomputed from actual complete Authority/Private outputs and consumed prompt; no retention-flag inference')
        proofs.append(proof)
        for name,v in [('EVENTS',events),('CONSUMER',consumer),('WORKER_RECORDS',workers),('SESSION',session),('EPISODE',episode),('MANIFEST_ROW',meta),('PROOF',proof)]:put(D/(name+'.json'),v)
    assert histories[0]==histories[1]
    put(out/'SUMMARY.json',dict(gate='PASS_SAME_SELECTED_HISTORY_AND_SHARED_COMPATIBLE_ROOT',
        source_id=cfg['source_id'],session_id=cfg['session_id'],shared_F=cfg['shared_F'],
        complete_Canonical_F_Z_P_text_history_equal=True,complete_visible_Private_Z_P_text_equal=hypotheses[0]==hypotheses[1],
        proofs=proofs,inputs=INPUTS,selection=cfg['selection'],new_model_calls=0))
    source_gate(m);put(out/'GATE.json',dict(gate='PASS_SAME_SELECTED_HISTORY_AND_SHARED_COMPATIBLE_ROOT',new_model_calls=0))
    print(json.dumps(dict(output=str(out),proofs=proofs,private_equal=hypotheses[0]==hypotheses[1])))
if __name__=='__main__':main()

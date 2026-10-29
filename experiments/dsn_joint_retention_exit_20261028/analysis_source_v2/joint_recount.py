"""Independent offline R x K recount; no scheduler, GPU or new model calls."""
from __future__ import annotations
from collections import Counter, defaultdict
from pathlib import Path
import argparse, hashlib, json, platform, statistics, subprocess, sys

INPUTS={}
INPUT_KEYS=('source_id','language','prompt_tokens','fault_actual_prompt_tokens','chunk_id',
            'audio_start_sample','audio_end_sample','prefix_audio_sha256','interval_audio_sha256')
OUTPUT_KEYS=('token_ids','state_tokens','text','terminated_by_eos','hit_token_limit','generated_tokens')
METRICS=('dual_credited_audio_seconds','all_offered_audio_goodput_2_8','display_P99','commit_view_P99',
         'audio_rollback_events','audio_rollback_seconds','rollback_area','longest_visible_progress_gap',
         'all_offered_WER_percent','GPU_joules','physical_model_seconds','physical_lease_seconds')

def sha(v):return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
def read(path,lines=False):
    path=Path(path);data=path.read_bytes();INPUTS[str(path)]=dict(bytes=len(data),sha256=hashlib.sha256(data).hexdigest())
    return [json.loads(s) for s in data.decode('utf8').splitlines() if s] if lines else json.loads(data)
def projection(v,keys):return {k:v[k] for k in keys if k in v}
def need(v,s):
    if not v:raise ValueError(s)

def verify_source(path):
    root=Path(__file__).resolve().parent;manifest=read(path)
    git=lambda *a:subprocess.check_output(['git','-C',str(root),*a],text=True).strip()
    commit=manifest['code_commit'];need(len(commit)==40 and git('rev-parse','HEAD')==commit,'analysis source commit mismatch')
    need(git('rev-parse','--show-toplevel').replace('\\','/').lower()==root.as_posix().lower(),'analysis must be its own checkout')
    need(not git('status','--porcelain','--untracked-files=all'),'dirty analysis source')
    tracked=set(git('ls-files','-z').split('\0'))-{''}
    need(tracked=={r['path'] for r in manifest['files']},'complete analysis manifest required')
    for row in manifest['files']:
        f=root/row['path'];need(f.stat().st_size==row['bytes'] and hashlib.sha256(f.read_bytes()).hexdigest()==row['sha256'],'analysis source bytes changed')
    return commit

def compatible_input(job,F,P,records,published,fine=32000):
    """Exact earlier published ancestry to selected F/P, independent of runtime flag."""
    route=[];seen=set();identity=tuple(job.get(k) for k in ('session_id','source_id','contract_epoch','contract_digest','branch_generation'))
    while True:
        if job['job_id'] in seen:return False,'cycle',route
        seen.add(job['job_id']);route.append(job['job_id'])
        if job['chunk_id']==round(F/fine):return job['prompt_tokens']==P,'selected_input_boundary',route
        if job['chunk_id']<round(F/fine):return False,'selected_root_ahead_of_input_boundary',route
        choices=[]
        for jid,row in records.items():
            j,z=row['job'],row['result'];actual=z.get('execution_context_audit',{}).get('executed_prompt_tokens',j.get('fault_actual_prompt_tokens',j['prompt_tokens']))
            if (jid in published and published[jid]<=job['enqueue_perf'] and actual==j['prompt_tokens'] and j['role']=='proposal' and
                tuple(j.get(k) for k in ('session_id','source_id','contract_epoch','contract_digest','branch_generation'))==identity and
                j['end_window']==job['chunk_id'] and F<=j['audio_end_sample']<job['audio_end_sample'] and
                z['state_tokens']==job['prompt_tokens'] and z['received_perf']<=job['enqueue_perf']):choices.append(row)
        if len(choices)!=1:return None,'missing_or_ambiguous_earlier_published_ancestor',route
        pred=choices[0]
        if pred['job']['audio_end_sample']==F:
            route.append(pred['job']['job_id']);return pred['result']['state_tokens']==P,'complete_ancestor_selected_boundary',route
        job=pred['job']

def verify_fixture_identity(cell,out,frozen):
    original=Path(cell['fixture']);copied=Path(out)/'fixture.json'
    need(hashlib.sha256(original.read_bytes()).hexdigest()==cell['fixture_sha256'],'original fixture bytes differ from plan')
    need(hashlib.sha256(copied.read_bytes()).hexdigest()==frozen['fixture_sha256'],'materialized fixture bytes differ from run freeze')
    need(read(original)==read(copied),'materialized fixture object differs from frozen original')


def load(cell):
    out=Path(cell['output']);a=out/'attempt0'
    gate=read(out/'GATE.json');need(gate['gate']=='PASS_SINGLE_CELL_EXECUTION_AND_INDEPENDENT_AUDIT','cell not audited')
    record=read(out/'RUN_RECORD.json');freeze=read(out/'FREEZE.json');frozen=freeze['frozen_config']
    expected=cell['expected_source_commit'];need(gate['source_commit']==record['code_commit']==expected,'neural execution source differs from plan')
    for key in ('policy','method','rho','sessions','arrival','repeat','adapter','confirmation_consumer'):
        need(frozen[key]==cell[key],'actual cell config differs from frozen plan: '+key)
    need(frozen['retain_private_prefix']==cell['retain'],'retention arm changed')
    need(frozen['original_manifest_sha256']==cell['manifest_sha256'],'original manifest freeze differs from plan')
    need(hashlib.sha256(Path(cell['manifest']).read_bytes()).hexdigest()==cell['manifest_sha256'],'original manifest bytes changed')
    verify_fixture_identity(cell,out,frozen)
    audit=read(out/'audit/SUMMARY.json');need(audit['status']=='PASS_INDEPENDENT_RETIREMENT_AND_INPUT_CONSUMER_AUDIT','bad independent audit')
    events=read(a/'events.jsonl',True);records=read(a/'worker_records.jsonl',True);consumer=read(a/'consumer.jsonl',True)
    batches=read(a/'worker_batch_accounting.jsonl',True);frontiers=read(out/'audit/FRONTIERS.json');cfg=read(a/'config.json')
    session_audit=read(out/'audit/SESSIONS.json');audited_batches=read(out/'audit/BATCHES.json');power=read(a/'power_samples.json')
    cancellations=read(a/'worker_cancelled_records.jsonl',True) if (a/'worker_cancelled_records.jsonl').exists() else []
    byid={row['job']['job_id']:row for row in records};need(len(byid)==len(records),'duplicate job ID')
    start=next(e['t0_perf'] for e in events if e['kind']=='run-start')
    published={e['job_id']:start+e['displayed'] for e in events if e['kind']=='display'}
    outcomes=defaultdict(list)
    for e in events:
        if e['kind'] in ('display','proposal-obsolete','proposal-rebase'):outcomes[e.get('job_id')].append(e['kind'])
    pressure=[]
    for row in records:
        j,z=row['job'],row['result']
        context=z.get('execution_context_audit',{})
        if (j['role']!='proposal' or context.get('fault_override') or
            context.get('executed_prompt_tokens',j.get('fault_actual_prompt_tokens',j['prompt_tokens']))!=j['prompt_tokens']):continue
        for e in events:
            if (e['kind']=='commit' and e['session_id']==j['session_id'] and
                z['model_started_perf']<=start+e['installed']<z['row_terminal_perf'] and e['audio_end_sample']<j['audio_end_sample']):
                ok,reason,route=compatible_input(j,e['audio_end_sample'],e['next_prompt_tokens'],byid,published)
                pressure.append(dict(job_id=j['job_id'],source_id=j['source_id'],tokens=z['generated_tokens'],
                    model_to_terminal_seconds=z['row_terminal_perf']-z['model_started_perf'],
                    selected_F=e['audio_end_sample'],target_F=j['audio_end_sample'],compatible=ok,reason=reason,chain=route,
                    owner_outcomes=outcomes[j['job_id']],actual_prompt_equals_declared=True))
    # Cancellations cannot publish text/state and require actual coverage at request.
    requests=[e for e in events if e['kind']=='cancel-request']
    for e in requests:
        need(e['invalidation_kind']=='trusted-coverage','new cancellation reason entered frozen K policy')
        job=byid.get(e['job_id']) or next(r for r in cancellations if r['job']['job_id']==e['job_id'])
        job=job['job'];need(e['observed_current_F']>=job['audio_end_sample'],'uncovered row cancellation')
    revised=defaultdict(list)
    for c in consumer:revised[c['session_id']].append(c)
    drops=0;drop_seconds=0.;area=0.;gaps=[]
    end=power['measurement_end_perf']
    for sid,rows in revised.items():
        high=0;prev=None;ticks=[]
        for c in sorted(rows,key=lambda v:v['observed_perf']):
            if prev:
                area+=max(0,high-prev['valid_visible_frontier'])/16000*(c['observed_perf']-prev['observed_perf'])
                delta=prev['valid_visible_frontier']-c['valid_visible_frontier']
                if delta>0:drops+=1;drop_seconds+=delta/16000
            if c['valid_visible_frontier']>high:ticks.append(c['observed_perf'])
            high=max(high,c['valid_visible_frontier']);prev=c
        if prev:area+=max(0,high-prev['valid_visible_frontier'])/16000*(end-prev['observed_perf'])
        gaps.extend(b-a for a,b in zip(ticks,ticks[1:]))
    metrics=dict(audit['service'],**{k:audit['lifecycle'][k] for k in ('physical_model_seconds','physical_lease_seconds')})
    metrics.update(dual_credited_audio_seconds=sum(f['audio_seconds'] for f in frontiers if f['dual_credit']),
        audio_rollback_events=drops,audio_rollback_seconds=drop_seconds,rollback_area=area,
        longest_visible_progress_gap=max(r['longest_actual_visible_progress_gap_seconds'] for r in session_audit))
    canonical=[dict(session_id=e['session_id'],version=e['version'],start=e['audio_start_sample'],
                    F=e['audio_end_sample'],Z=e['segment_tokens'],P=e['next_prompt_tokens'],text=byid[e['job_id']]['result']['text'])
               for e in events if e['kind']=='commit']
    canonical.sort(key=lambda v:(v['session_id'],v['F']))
    exit_chains=[]
    for row in cancellations:
        j,c=row['job'],row['cancellation'];batch=next(b for b in audited_batches if b['batch_id']==j['_delivery']['batch_id'])
        following=next((b for b in audited_batches if b['worker']==batch['worker'] and b['dispatch_perf']==batch['next_actual_dispatch_perf']),None)
        nextids=[] if following is None else next(b['job_ids'] for b in batches if b['batch_id']==following['batch_id'])
        nextout=Counter(kind for jid in nextids for kind in outcomes[jid])
        exit_chains.append(dict(job_id=j['job_id'],session_id=j['session_id'],decoded_tokens=c['decoded_tokens'],
            requested_perf=c['requested_perf'],acknowledged_perf=c['acknowledged_perf'],row_terminal_perf=c['emitted_perf'],
            actual_batch_drain_perf=batch['drained_perf'],request_to_ack_seconds=c['acknowledged_perf']-c['requested_perf'],
            ack_to_drain_seconds=batch['drained_perf']-c['acknowledged_perf'],actual_batch_model_seconds=batch['model_seconds'],
            next_actual_dispatch_perf=batch['next_actual_dispatch_perf'],following_batch_id=None if following is None else following['batch_id'],
            following_owner_outcomes=dict(nextout),following_job_ids=nextids))
    return dict(cell=cell,metrics=metrics,canonical=canonical,canonical_sha256=sha(canonical),
        legal_pressure=pressure,requests=requests,records=records,batches=batches,cancellations=cancellations,
        exit_chains=exit_chains,outcomes=outcomes,consumer=consumer,origin=cfg['episode_origin_perf'],
        accepted_debt=audit['accepted_unfulfilled_samples'],all_offered_frontiers=audit['all_offered_frontiers'],
        offered_audio_seconds=sum(f['audio_seconds'] for f in frontiers))

def matched_rows(a,b):
    def keyed(arm):
        groups=defaultdict(list);alljobs={r['job']['job_id']:r['job'] for r in arm['records']+arm['cancellations']}
        batchbyid={v['batch_id']:v for v in arm['batches']}
        for row in arm['records']:
            if row['job']['role']!='proposal':continue
            j,z=row['job'],row['result'];key=sha(projection(j,INPUT_KEYS));batch=batchbyid[z['physical_batch_id']]
            peers=[projection(alljobs[jid],INPUT_KEYS) for jid in batch['job_ids']]
            groups[key].append(dict(job=j,result=z,peers=peers))
        return groups
    ga,gb=keyed(a),keyed(b);rows=[]
    for key in sorted(ga.keys()&gb.keys()):
        if len(ga[key])!=1 or len(gb[key])!=1:continue
        x,y=ga[key][0],gb[key][0];zx,zy=x['result'],y['result']
        def timing(arm,row):
            j,z=row['job'],row['result'];view=next(c for c in arm['consumer'] if c['session_id']==j['session_id'] and c['valid_visible_frontier']>=j['audio_end_sample'])
            return dict(model_start_relative_origin=z['model_started_perf']-arm['origin'],
                row_terminal_relative_origin=z['row_terminal_perf']-arm['origin'],owner_outcomes=arm['outcomes'][j['job_id']],
                first_actual_consumer_relative_origin=view['observed_perf']-arm['origin'],first_actual_consumer_source_kind=view['source_kind'])
        rows.append(dict(source_id=x['job']['source_id'],chunk_id=x['job']['chunk_id'],target_F=x['job']['audio_end_sample'],input_sha256=key,
            output_equal=projection(zx,OUTPUT_KEYS)==projection(zy,OUTPUT_KEYS),
            actual_execution_context_equal=zx.get('execution_context_audit')==zy.get('execution_context_audit'),
            full_model_input_audit_equal=zx.get('model_input_audit')==zy.get('model_input_audit'),
            peers_equal=x['peers']==y['peers'],a_job=x['job']['job_id'],b_job=y['job']['job_id'],a_timing=timing(a,x),b_timing=timing(b,y)))
    return dict(a=a['cell']['cell_id'],b=b['cell']['cell_id'],a_distinct_input_keys=len(ga),b_distinct_input_keys=len(gb),
                matched_unique_inputs=len(rows),same_complete_outputs=sum(r['output_equal'] for r in rows),
                same_full_model_input_and_peers=sum(r['full_model_input_audit_equal'] and r['peers_equal'] for r in rows),rows=rows)

def main():
    p=argparse.ArgumentParser();p.add_argument('--plan',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    p.add_argument('--source-manifest',type=Path,required=True)
    args=p.parse_args();source_commit=verify_source(args.source_manifest)
    args.out.mkdir(parents=True,exist_ok=False);plan=read(args.plan);runs=[];failures=[]
    for cell in plan['cells']:
        cell=dict(cell,expected_source_commit=plan['code_commit'])
        try:runs.append(load(cell))
        except Exception as e:failures.append(dict(cell_id=cell['cell_id'],error=repr(e)))
    groups=defaultdict(dict)
    for run in runs:groups[run['cell']['paired_block']][run['cell']['arm']]=run
    effects=[];matches=[]
    for block,arms in groups.items():
        if set(arms)!={'R0K0','R0K1','R1K0','R1K1'}:continue
        effects.append(dict(block=block,canonical_histories_equal=len({r['canonical_sha256'] for r in arms.values()})==1,
            effects={m:arms['R1K1']['metrics'][m]-arms['R1K0']['metrics'][m]-arms['R0K1']['metrics'][m]+arms['R0K0']['metrics'][m] for m in METRICS}))
        for r in (0,1):matches.append(matched_rows(arms[f'R{r}K0'],arms[f'R{r}K1']))
    compact=[dict(cell_id=r['cell']['cell_id'],arm=r['cell']['arm'],arrival=r['cell']['arrival'],repeat=r['cell']['repeat'],
        metrics={k:r['metrics'][k] for k in METRICS},canonical_sha256=r['canonical_sha256'],
        legal_pressure=r['legal_pressure'],requests=r['requests'],exit_chains=r['exit_chains'],cancelled_rows=len(r['cancellations']),
        accepted_unfulfilled_samples=r['accepted_debt'],offered_audio_seconds=r['offered_audio_seconds'],
        all_offered_frontiers=r['all_offered_frontiers']) for r in runs]
    outputs={'RUNS.json':compact,'FACTORIAL_EFFECTS.json':effects,'MATCHED_ROWS.json':matches,
        'SUMMARY.json':dict(status='COMPLETE_OFFLINE_RECOUNT' if len(runs)==len(plan['cells']) else 'INCOMPLETE_PRESERVED',
            planned=len(plan['cells']),accepted=len(runs),failures=failures,complete_factorial_blocks=len(effects),
            epistemic_status='Controlled service and temporal repeats only; no natural prevalence or automatic superiority claim'),
        'ANALYSIS_RECORD.json':dict(experiment_id=plan['experiment_id']+'-OFFLINE-RECOUNT',
            analysis_code_commit=source_commit,neural_execution_commit=plan['code_commit'],
            frozen_config=str(args.plan),frozen_config_sha256=hashlib.sha256(args.plan.read_bytes()).hexdigest(),
            source_manifest=str(args.source_manifest),source_manifest_sha256=hashlib.sha256(args.source_manifest.read_bytes()).hexdigest(),
            python=sys.version,executable=sys.executable,platform=platform.platform(),inputs=INPUTS,
            script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),raw_result_locations=[c['output'] for c in plan['cells']],
            aggregate_summary_location=str(args.out/'SUMMARY.json'),gate_decision_location=str(args.out/'GATE.json'))}
    need(verify_source(args.source_manifest)==source_commit,'analysis source changed during recount')
    outputs['GATE.json']=dict(gate='PASS_OFFLINE_RECOUNT' if len(runs)==len(plan['cells']) else 'INCOMPLETE_PRESERVED',
                             scientific_superiority='NOT_INFERRED_FROM_ANALYSIS_EXECUTION')
    for name,value in outputs.items():
        with (args.out/name).open('x',encoding='utf8') as f:json.dump(value,f,indent=2,allow_nan=False);f.write('\n')
    print(json.dumps(outputs['SUMMARY.json']))

if __name__=='__main__':main()

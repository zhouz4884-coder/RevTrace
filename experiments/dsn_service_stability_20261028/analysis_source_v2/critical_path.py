"""Offline observed ready-to-Consumer decomposition, without scheduler imports.

Stages partition a witnessed path, not a counterfactual attribution. In
particular ACK-to-enqueue includes legal dependency and executor availability;
overlapping prior physical leases and WAL spans are descriptors, never savings.
"""
from pathlib import Path
from collections import Counter,defaultdict
import argparse,csv,hashlib,json,math,platform,sys

INPUTS={}
STAGES=('coalescing_wait','ready_to_input_ACK','ACK_to_enqueue','enqueue_to_worker',
    'worker_to_model','model_to_terminal','terminal_to_owner_receive',
    'owner_receive_to_publication','publication_to_Consumer')

def read(p,lines=False):
    p=Path(p);b=p.read_bytes();INPUTS[str(p.resolve())]=dict(bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
    return [json.loads(x) for x in b.decode('utf8').splitlines() if x] if lines else json.loads(b)

def union_overlap(spans,lo,hi):
    ss=sorted((max(lo,a),min(hi,b)) for a,b in spans if max(lo,a)<min(hi,b))
    total=0.;end=-math.inf
    for a,b in ss:
        total+=max(0,b-max(a,end));end=max(end,b)
    return total

def q(xs,quantile):
    xs=sorted(xs)
    if not xs:return None
    z=(len(xs)-1)*quantile;i=int(z);j=min(i+1,len(xs)-1)
    return xs[i]+(xs[j]-xs[i])*(z-i)

def cell_path(raw):
    argv=raw.get('argv',[]);p=argv[argv.index('--out')+1] if '--out' in argv else raw['output']
    if raw.get('output') and raw['output']!=p:raise ValueError('frozen command/output mismatch')
    return Path(p)

def recount(raw):
    d=cell_path(raw);cell=raw['cell_id'];meta={k:raw.get(k) for k in ['arm','cohort','arrival','repeat','sessions','paired_block']}
    out=dict(cell_id=cell,**meta,path=str(d),status='MISSING',accepted=False)
    if not (d/'GATE.json').exists():return out,[]
    if read(d/'GATE.json').get('gate')!='PASS_SINGLE_CELL_EXECUTION_AND_INDEPENDENT_AUDIT':
        return dict(out,status='EXECUTION_GATE_NOT_ACCEPTED'),[]
    audit=read(d/'INDEPENDENT_SUMMARY.json');root=d/'attempt0'
    events=read(root/'events.jsonl',True);owner=next(e['t0_perf'] for e in events if e['kind']=='run-start')
    records=read(root/'worker_records.jsonl',True);records={r['job']['job_id']:r for r in records}
    consumers=read(root/'consumer.jsonl',True);frontiers=read(d/'audit/FRONTIERS.json')
    batches=read(root/'worker_batch_accounting.jsonl',True)
    acks=defaultdict(list)
    for e in events:
        if e['kind']=='input-ack':acks[e['session_id']].append(e)
    pubs=defaultdict(list)
    for e in events:
        if e['kind'] in ('display','canonical-display'):pubs[(e['session_id'],e['kind'])].append(e)
    consumer_by=defaultdict(list)
    for c in consumers:consumer_by[c['session_id']].append(c)
    wals=[(owner+e['started'],owner+e['completed']) for e in events if e['kind']=='wal-physical-timing']
    leases=defaultdict(list)
    for b in batches:
        leases[b['worker']].append((b['worker_started_perf'],b.get('batch_drained_perf',b['batch_result_complete_perf'])))
    rows=[]
    for f in frontiers:
        base=dict(cell_id=cell,**meta,session_id=f['session_id'],frontier=f['frontier'],
            audio_seconds=f['audio_seconds'],display_latency=f['display_latency'],
            commit_view_latency=f['commit_view_latency'],dual_credit=f['dual_credit'],
            display_miss=f['display_latency'] is None or f['display_latency']>2.,
            status='UNMATCHED_FIRST_ACTUAL_VIEW')
        cs=[c for c in consumer_by[f['session_id']] if abs(c['observed_perf']-f['first_actual_visible_perf'])<1e-7]
        if len(cs)!=1:rows.append(base);continue
        c=cs[0];ps=[e for e in pubs[(c['session_id'],c['source_kind'])] if abs(e['displayed']-c['server_time'])<1e-7]
        if len(ps)!=1:rows.append(dict(base,status='UNMATCHED_OWNER_PUBLICATION',source_kind=c['source_kind']));continue
        e=ps[0];jid=e.get('job_id');r=records.get(jid)
        if not r:rows.append(dict(base,status='NO_COMPLETE_PUBLISHING_JOB',job_id=jid));continue
        j,res=r['job'],r['result'];receipt=res['_row_receipt']
        if j['audio_end_sample']<f['frontier']:
            rows.append(dict(base,status='RETAINED_VIEW_ORIGIN_NOT_PUBLISHING_JOB',job_id=jid));continue
        aa=[a for a in acks[j['session_id']] if a['to_sample']>=j['audio_end_sample'] and owner+a['time']<=j['enqueue_perf']+1e-7]
        if not aa:rows.append(dict(base,status='NO_EARLIER_COMPLETE_INPUT_ACK',job_id=jid));continue
        ack=owner+min(aa,key=lambda a:a['time'])['time'];pub=owner+e['displayed']
        times=[f['original_ready_perf'],j['audio_ready_perf'],ack,j['enqueue_perf'],res['started_perf'],
            res['model_started_perf'],receipt['terminal_perf'],res['received_perf'],pub,c['observed_perf']]
        values=[b-a for a,b in zip(times,times[1:])]
        if any(x< -1e-6 for x in values):
            rows.append(dict(base,status='NONMONOTONIC_WITNESSED_PATH',job_id=jid,times=times));continue
        stages=dict(zip(STAGES,values));total=sum(values)
        if abs(total-f['display_latency'])>1e-6:raise AssertionError('stage partition changed original deadline')
        worker=j['_delivery']['worker']
        rows.append(dict(base,status='OBSERVED_COMPLETE_PATH',job_id=jid,role=j['role'],
            publishing_audio_end=j['audio_end_sample'],source_kind=c['source_kind'],stages=stages,
            stage_sum=total,ACK_to_enqueue_prior_worker_lease_overlap=union_overlap(leases[worker],ack,j['enqueue_perf']),
            owner_receive_to_publication_WAL_overlap=union_overlap(wals,res['received_perf'],pub),
            physical_batch_rows=res['model_input_audit']['batch_rows'],generated_tokens=res['generated_tokens']))
    complete=[r for r in rows if r['status']=='OBSERVED_COMPLETE_PATH'];misses=[r for r in complete if r['display_miss']]
    service=audit['service']
    metrics={k:service[k] for k in ['whole_offered_frontiers','whole_run_dual_P99_pass','display_P99','commit_view_P99',
        'all_offered_audio_goodput_2_8','all_offered_WER_percent','GPU_joules','input_fsync_seconds',
        'input_snapshot_syncs','controller_host_seconds','controller_CPU_seconds']}
    def stats(rr):return dict(frontiers=len(rr),audio_seconds=sum(r['audio_seconds'] for r in rr),
        stage_P50={k:q([r['stages'][k] for r in rr],.5) for k in STAGES},
        stage_P99={k:q([r['stages'][k] for r in rr],.99) for k in STAGES},
        dominant_stage_counts=dict(Counter(max(r['stages'],key=r['stages'].get) for r in rr)))
    return dict(out,status='OFFLINE_RECOUNT_COMPLETE',accepted=True,metrics=metrics,
        observed_complete_paths=len(complete),path_status_counts=dict(Counter(r['status'] for r in rows)),
        all_frontier_path=stats(complete),display_miss_paths=stats(misses),
        physical_batches=len(batches),physical_batch_rows_P50=q([len(b['job_ids']) for b in batches],.5),
        worst_actual_frontiers=sorted(rows,key=lambda r:r['display_latency'] if r['display_latency'] is not None else math.inf,reverse=True)[:5]),rows

def write(path,value):
    with path.open('x',encoding='utf8') as f:json.dump(value,f,indent=2,allow_nan=False);f.write('\n')

def main():
    p=argparse.ArgumentParser();p.add_argument('--plan',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--adapter',default='qwen');a=p.parse_args();plan=read(a.plan);out=a.output;out.mkdir(exist_ok=False,parents=True)
    reports=[];rows=[]
    for c in plan['cells']:
        if c.get('adapter','qwen')!=a.adapter:continue
        r,rr=recount(c);reports.append(r);rows.extend(rr)
    write(out/'RUNS.json',reports);write(out/'FRONTIER_PATHS.json',rows)
    write(out/'SUMMARY.json',dict(status='OFFLINE_RECOUNT_COMPLETE' if all(r['accepted'] for r in reports) else 'INCOMPLETE_FROZEN_PLAN',
        planned_cells=len(reports),accepted_cells=sum(r['accepted'] for r in reports),
        path_status_counts=dict(Counter(r['status'] for r in rows)),GPU_calls=0,
        interpretation='observed stage partition; input-ACK to enqueue includes feedback/lease eligibility; phase/lease overlaps are not causal exclusive shares or counterfactual savings'))
    with (out/'FRONTIER_PATHS.csv').open('x',encoding='utf8',newline='') as f:
        flat=[dict({k:v for k,v in r.items() if k not in ('stages','times')},**r.get('stages',{})) for r in rows]
        keys=list(dict.fromkeys(k for r in flat for k in r));w=csv.DictWriter(f,fieldnames=keys);w.writeheader();w.writerows(flat)
    write(out/'ANALYSIS_RECORD.json',dict(analysis_script=str(Path(__file__).resolve()),
        analysis_script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        frozen_plan=str(a.plan.resolve()),python=sys.version,platform=platform.platform(),
        input_files=INPUTS,new_GPU_calls=0,measured_neural_commit=plan.get('code_commit')))
    print(json.dumps(dict(output=str(out),cells=len(reports),accepted=sum(r['accepted'] for r in reports))))

if __name__=='__main__':main()

"""Receipt-bound leases, physical spans, neural-call wall and nonuse partitions."""
from pathlib import Path
from collections import defaultdict,Counter
import argparse,csv,traceback
from common import begin,put,digest


def union_overlap(lo,hi,spans):
    cuts=sorted((max(lo,a),min(hi,b)) for a,b in spans if min(hi,b)>max(lo,a))
    total=0.;end=lo
    for a,b in cuts:
        if b>end:total+=b-max(a,end);end=b
    return total


def stats(x):
    a=sorted(x)
    def q(p):
        if not a:return None
        z=(len(a)-1)*p;i=int(z);return a[i] if i==len(a)-1 else a[i]+(a[i+1]-a[i])*(z-i)
    return dict(n=len(a),sum=sum(a),p50=q(.5),p95=q(.95),p99=q(.99),maximum=max(a) if a else None)


def lease_pairs(trace):
    active={};out=defaultdict(list)
    for r in trace:
        if r['kind']=='dispatch':
            w=r['operation'];assert w not in active,'physical lease reused before drain';active[w]=r['observed_perf']
        elif r['kind']=='batch-drained':
            w=r['operation'];start=active.pop(w);assert r['observed_perf']>=start
            out[w].append((start,r['observed_perf']))
    assert not active,'unreleased paid lease'
    return out


def main():
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--indices',type=Path,nargs='+',required=True)
    p.add_argument('--source-manifest',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    source,e=begin(a,'PAID-WORK-DECOMPOSITION');rows=[];batch_rows=[];frontier_rows=[];baseline=None
    study='dev_v10_c16_staggered_r0_revtrace_b040_prior'
    try:
        summary=e.json(study+'/SUMMARY.json');assert summary['status']=='COMPLETE_DEVELOPMENT_PILOT' and len(summary['completed'])==6
        assert summary['rows'][0]['policy']=='immediate','explicit comparison reference required'
        for cell,reported in zip(summary['completed'],summary['rows']):
            pre=study+'/'+cell+'/attempt0/';events=e.lines(pre+'events.jsonl');wr=e.lines(pre+'worker_records.jsonl');batches=e.lines(pre+'worker_batch_accounting.jsonl');kernel=e.json(pre+'kernel_trace.json');cfg=e.json(pre+'config.json')
            specs=e.json(pre+'sessions.json');consumer=e.lines(pre+'consumer.jsonl')
            assert cfg['rho']==1 and cfg['replicas']=={'proposal':[0],'authority':[1]}
            t0=next(x['t0_perf'] for x in events if x['kind']=='run-start');origin=cfg['episode_origin_perf']
            records={r['job']['job_id']:r for r in wr};assert len(records)==len(wr)
            leases=lease_pairs(kernel['events']);byworker=defaultdict(list)
            for b in batches:byworker[b['worker']].append(b)
            obsolete={r['job_id'] for r in events if r['kind']=='proposal-obsolete'}
            displayed={r['job_id'] for r in events if r['kind']=='display'};assert not obsolete&displayed
            jobkeys={};inputmap={}
            for r in wr:
                j,v=r['job'],r['result'];key=(j['role'],j['session_id'],j['audio_end_sample']);assert key not in jobkeys;jobkeys[key]=j['job_id']
                m=v['model_input_audit'];inputmap[key]=dict(P=j['prompt_tokens'],root=[j['chunk_id'],j['parent'],j['audio_start_sample']],row_input=[m['unpadded_input_ids'],m['row_features']],batch=m['batch_tensors'],Z=v['token_ids'])
            if baseline is None:baseline=inputmap
            cross={}
            for role in ['proposal','authority']:
                keys=[k for k in inputmap if k[0]==role and k in baseline]
                cross[role]=dict(common=len(keys),missing_vs_immediate=sum(k[0]==role and k not in inputmap for k in baseline),new_vs_immediate=sum(k[0]==role and k not in baseline for k in inputmap),declared_P_changed=sum(inputmap[k]['P']!=baseline[k]['P'] for k in keys),root_changed=sum(inputmap[k]['root']!=baseline[k]['root'] for k in keys),processed_row_changed=sum(inputmap[k]['row_input']!=baseline[k]['row_input'] for k in keys),batch_tensors_changed=sum(inputmap[k]['batch']!=baseline[k]['batch'] for k in keys),output_Z_changed=sum(inputmap[k]['Z']!=baseline[k]['Z'] for k in keys))
            costs={};authority_spans=[]
            for worker,bs in byworker.items():
                bs.sort(key=lambda b:b['worker_started_perf']);assert len(bs)==len(leases[worker])
                resource=[]
                for b,(leased,reusable) in zip(bs,leases[worker]):
                    js=[records[x]['job'] for x in b['job_ids']];roles={j['role'] for j in js};assert len(roles)==1;role=next(iter(roles))
                    start,end=b['worker_started_perf'],b['batch_drained_perf'];assert leased<=start<=b['batch_result_complete_perf']<=end<=reusable
                    phases=sorted(b['phases'],key=lambda x:x['started_perf']);assert phases
                    assert all(start<=x['started_perf']<=x['completed_perf']<=end for x in phases)
                    assert all(x['completed_perf']<=y['started_perf']+1e-7 for x,y in zip(phases,phases[1:]))
                    neural=sum(x['completed_perf']-x['started_perf'] for x in phases);gap=sum(max(0,y['started_perf']-x['completed_perf']) for x,y in zip(phases,phases[1:]))
                    parts=dict(owner_pre_worker_seconds=start-leased,worker_pre_model_seconds=phases[0]['started_perf']-start,synchronized_model_call_wall_seconds=neural,between_model_calls_seconds=gap,worker_post_model_seconds=end-phases[-1]['completed_perf'],owner_post_drain_seconds=reusable-end)
                    assert all(v>=-1e-6 for v in parts.values()) and abs(sum(parts.values())-(reusable-leased))<1e-6
                    old=[j['job_id'] in obsolete for j in js];partition='all_obsolete' if all(old) else 'mixed_obsolete' if any(old) else 'no_obsolete'
                    r=dict(policy=reported['policy'],worker=worker,role=role,batch_id=b['batch_id'],rows=len(js),receipt_bound_paid_lease_seconds=reusable-leased,physical_worker_span_seconds=end-start,obsolete_rows=sum(old),output_nonuse_partition=partition,**parts)
                    batch_rows.append(r);resource.append(r)
                    if role=='authority':authority_spans.append((start,end))
                role=resource[0]['role'];costs[role]=dict(worker=worker,batches=len(resource),rows=sum(x['rows'] for x in resource),batch_size_histogram=dict(Counter(x['rows'] for x in resource)),receipt_bound_paid_lease=stats([x['receipt_bound_paid_lease_seconds'] for x in resource]),physical_worker_span=stats([x['physical_worker_span_seconds'] for x in resource]),synchronized_model_call_wall=stats([x['synchronized_model_call_wall_seconds'] for x in resource]),parts_seconds={k:sum(x[k] for x in resource) for k in parts},nonuse_partition={name:dict(batches=sum(x['output_nonuse_partition']==name for x in resource),paid_lease_seconds=sum(x['receipt_bound_paid_lease_seconds'] for x in resource if x['output_nonuse_partition']==name)) for name in ['all_obsolete','mixed_obsolete','no_obsolete']})
            commits={x['job_id']:x for x in events if x['kind']=='commit'};versions={(x['session_id'],x['version']):x for x in commits.values()}
            paths=[]
            for r in wr:
                j,v=r['job'],r['result']
                if j['role']!='authority':continue
                sid=j['session_id'];F=j['audio_end_sample'];release=j['audio_ready_perf'];parent=t0+versions[sid,j['parent']]['installed'] if j['parent'] else origin
                ack=min(t0+x['time'] for x in events if x['kind']=='input-ack' and x['session_id']==sid and x['to_sample']>=F)
                eligible=max(release,parent,ack);installed=t0+commits[j['job_id']]['installed'];applied=min(x['observed_perf'] for x in consumer if x['session_id']==sid and x['certified_frontier']>=F)
                pieces=dict(prerequisite_wait=eligible-release,owner_queue=j['enqueue_perf']-eligible,IPC_to_worker=v['started_perf']-j['enqueue_perf'],worker_to_host_row=v['received_perf']-v['started_perf'],host_row_to_install=installed-v['received_perf'],install_to_actual_consumer=applied-installed)
                assert min(pieces.values())>=-1e-5 and abs(sum(pieces.values())-(applied-release))<1e-5
                busy=union_overlap(eligible,j['enqueue_perf'],authority_spans)
                paths.append(dict(policy=reported['policy'],session_id=sid,frontier=F,latency=applied-release,queue_gpu_worker_busy=busy,queue_other=max(0,j['enqueue_perf']-eligible-busy),**pieces))
            frontier_rows+=paths
            covered={(x['session_id'],x['window']) for x in events if x['kind']=='proposal-skip'}
            expired={(x['session_id'],x['window']) for x in events if x['kind']=='private-deadline-retired'}
            assert not covered&expired
            rows.append(dict(policy=reported['policy'],costs=costs,offered_frontiers=reported['whole_offered_frontiers'],private_obsolete_rows=len(obsolete),canonical_covered_unissued=len(covered),deadline_expired_unissued=len(expired),input_comparison_to_immediate=cross,authority_path_stats={k:stats([r[k] for r in paths]) for k in paths[0] if k not in ['policy','session_id','frontier']},reported_service={k:reported[k] for k in ['all_offered_audio_goodput_2_8','display_P99','commit_view_P99','GPU_J_per_offered_audio_second','whole_run_dual_P99_pass','WER_errors','WER_reference_words']},scope='per-row latency components and free-run input comparisons are NOT additive physical savings or isolated causal shares'))
        put(a.out/'RESULT.json',dict(status='COMPLETE_INDEXED_PAID_WORK_AND_PATH_DECOMPOSITION',rows=rows,batches=batch_rows,authority_frontiers=frontier_rows,input_files=list(e.used.values()),GPU_inference_calls=0,definitions=dict(paid_lease='trusted kernel dispatch receipt to batch-drained receipt; includes transport/host checks; never early-row release',worker_span='worker batch start to physical Batch-drained timestamp',model_wall='sum of synchronized real model-call wall intervals, not hardware CUDA utilization',obsolete_partition='disjoint whole-batch categories; mixed rows do not imply per-row cancellable GPU time',unissued='no paid call, not an invented measured saving')))
        for name,data in [('BATCH_PAID_WORK.csv',batch_rows),('AUTHORITY_LATENCY_COMPONENTS.csv',frontier_rows)]:
            with (a.out/name).open('x',newline='',encoding='utf8') as f:w=csv.DictWriter(f,fieldnames=list(data[0]));w.writeheader();w.writerows(data)
        put(a.out/'GATE.json',dict(gate='PASS_RECEIPT_PHYSICAL_AND_COMPONENT_RECOUNT',code_commit=source['code_commit'],policies=6,GPU_inference_calls=0))
    except BaseException:
        put(a.out/'STOP.json',dict(error=traceback.format_exc(),completed_policies=len(rows),GPU_inference_calls=0));raise


if __name__=='__main__':main()

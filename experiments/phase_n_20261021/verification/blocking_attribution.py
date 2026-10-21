"""Post-hoc interval reconstruction from actual lifecycle events, not _ready()."""
import argparse,csv,json
from collections import defaultdict
from pathlib import Path

def reconstruct(cell,out):
    cfg=json.loads((cell/'config.json').read_text());events=[json.loads(x) for x in (cell/'events.jsonl').read_text().splitlines()]
    t0=next(e['t0_perf'] for e in events if e['kind']=='run-start')
    jobs={e['job_id']:e for e in events if e['kind']=='enqueue'}
    done={e['job_id']:e for e in events if e['kind']=='executor-complete'}
    commits={e['job_id']:e for e in events if e['kind']=='commit'}
    proposal={(j['session_id'],j['audio_end_sample']):done[jid] for jid,j in jobs.items() if j['role']=='proposal'}
    authority={jid:j for jid,j in jobs.items() if j['role']=='authority'}
    declared_dispatch={tuple(e['job_ids']):e['time'] for e in events if e['kind']=='batch-dispatched' and e['role']=='authority'}
    completed_observed={tuple(e['job_ids']):e['time'] for e in events if e['kind']=='worker-status' and e['status']=='batch-completed'}
    batches=[]
    for e in events:
        if e['kind']!='worker-status' or e['status']!='batch-started':continue
        if not e['job_ids'] or jobs[e['job_ids'][0]]['role']!='authority':continue
        ids=tuple(e['job_ids']);dispatch=declared_dispatch.get(ids)
        batches.append({'worker':e['worker'],'ids':ids,'dispatch':dispatch,
            'gpu_started':min(done[j].get('gpu_model_started') or done[j]['started'] for j in ids),
            'gpu_completed':max(done[j].get('gpu_model_completed') or done[j]['completed'] for j in ids),
            'completion_observed':completed_observed[ids],'first_receipt':min(done[j]['received'] for j in ids)})
    physical=[e for e in events if e['kind']=='wal-physical-timing' and e['phase']=='fsync']
    owner=[];opening=None
    for e in events:
        if e['kind']=='wal-owner-start':opening=e['time']
        elif e['kind']=='wal-owner-complete':owner.append((opening,e['time']));opening=None
    barriers=[]
    if cfg['proposal_barrier']=='segment':
        for jid,j in authority.items():
            p=proposal.get((j['session_id'],j['audio_end_sample']))
            if p and done[jid]['received']<p['received']:
                barriers.append((j['session_id'],done[jid]['received'],p['received']))
    rows=[];stats=defaultdict(float);by_source=defaultdict(lambda:defaultdict(float));unknown=0.
    allboundaries={v for b in batches for v in [b['dispatch'],b['gpu_started'],b['gpu_completed'],b['completion_observed'],b['first_receipt']] if v is not None}
    allboundaries|={v for j in authority.values() for v in [j['enqueue_perf']-t0,done[j['job_id']]['received'],commits[j['job_id']]['installed']]}
    allboundaries|={v for e in physical for v in [e['started'],e['completed']]}
    allboundaries|={v for r in owner for v in r}
    allboundaries|={v for _,l,r in barriers for v in [l,r]}
    for jid,j in authority.items():
        left=j['audio_ready_perf']-t0;right=j['enqueue_perf']-t0
        boundaries=sorted({left,right}|{b for b in allboundaries if left<b<right})
        own_jobs=[p for p in authority.values() if p['session_id']==j['session_id'] and p['job_id']!=jid]
        for l,r in zip(boundaries,boundaries[1:]):
            if r<=l:continue
            mid=(l+r)/2;duration=r-l;active=[];uncertain=[]
            for b in batches:
                start=b['dispatch']
                if start is not None and start<=mid<b['completion_observed']:active.append(b)
                elif b['completion_observed']<=mid<b['first_receipt']:uncertain.append(b)
            workers={b['worker'] for b in batches};active_workers={b['worker'] for b in active}
            capacity=True if len(active_workers)==len(workers) else (None if uncertain else False)
            members=[x for b in active for x in b['ids']]
            own_exec=any(done[p['job_id']].get('gpu_model_started') is not None and
                done[p['job_id']]['gpu_model_started']<=mid<done[p['job_id']]['gpu_model_completed'] for p in own_jobs)
            exec_unknown=any(done[p['job_id']].get('gpu_model_started') is None and
                done[p['job_id']]['started']<=mid<done[p['job_id']]['completed'] for p in own_jobs)
            self_inflight=any(p['enqueue_perf']-t0<=mid<done[p['job_id']]['received'] for p in own_jobs)
            pending=any(done[p['job_id']]['received']<=mid<commits[p['job_id']]['installed'] for p in own_jobs)
            F=max([0]+[c['audio_end_sample'] for c in commits.values() if c['session_id']==j['session_id'] and c['installed']<=mid])
            bits={'self_inflight':self_inflight,'self_exec_on_gpu':None if exec_unknown else own_exec,'commit_pending':pending,
                'barrier_hold':any(sid==j['session_id'] and a<=mid<b for sid,a,b in barriers),'candidate_missing':False,
                'worker_capacity_occupied':capacity,'other_session_jobs_on_worker':any(jobs[x]['session_id']!=j['session_id'] for x in members),
                'coordinator_wal_sync':any(e['started']<=mid<e['completed'] for e in physical),
                'owner_wal_call':any(a<=mid<b for a,b in owner),'parent_uninstalled':F<j['audio_start_sample'],
                'scheduler_delay':False}
            bits['scheduler_delay']=False if capacity is None else not any(v for k,v in bits.items() if k!='scheduler_delay')
            stats['target_wait_seconds']+=duration;by_source[j['source_id']]['target_wait_seconds']+=duration
            for k,v in bits.items():
                if v is True:stats[k]+=duration;by_source[j['source_id']][k]+=duration
                if v is None:unknown+=duration
            if own_exec and capacity is True:stats['BOTH_self_execution_and_worker_capacity']+=duration
            rows.append({'job_id':jid,'source_id':j['source_id'],'session_id':j['session_id'],'entered':l,'exited':r,'duration':duration,
                'frontier_at_midpoint':F,'target':j['audio_end_sample'],'batch_members':';'.join(members),**bits})
    out.mkdir(exist_ok=True)
    with (out/(cell.name+'-blocking.csv')).open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    summary={'cell':cell.name,'intervals':len(rows),'overlapping_target_seconds':dict(stats),'by_source':dict(by_source),
        'uncertain_capacity_target_seconds':unknown,'workers':sorted({b['worker'] for b in batches}),
        'scope':'Complete ready-to-enqueue intervals reconstructed independently; overlapping occupancy, NOT causal contributions. Capacity release bounded between observed completion and first receipt.'}
    (out/(cell.name+'-blocking.json')).write_text(json.dumps(summary,indent=2)+'\n');return summary
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    summaries=[]
    for cell in sorted(a.root.iterdir()):
        if (cell/'result.json').exists() and json.loads((cell/'config.json').read_text()).get('blocking_instrumentation'):
            summaries.append(reconstruct(cell,a.out));print(cell.name,'independent blocking intervals complete',flush=True)
    (a.out/'BLOCKING_SUMMARY.json').write_text(json.dumps({'cells':summaries},indent=2)+'\n')

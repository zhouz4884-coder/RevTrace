"""Current visibility versus ever-covered audio, including intentional corrections."""
import argparse,hashlib,json
from collections import defaultdict
from pathlib import Path

def audit(cell):
    cfg=json.loads((cell/'config.json').read_text());res=json.loads((cell/'result.json').read_text())
    events=[json.loads(x) for x in (cell/'events.jsonl').read_text().splitlines()]
    actions=defaultdict(list);jobs={};completed={};outcome={};F=defaultdict(int);generation=defaultdict(int)
    corrections=[];retired=[];skipped=0
    for seq,e in enumerate(events):
        kind=e['kind'];sid=e.get('session_id')
        if kind=='enqueue':jobs[e['job_id']]=e
        elif kind=='executor-complete':completed[e['job_id']]=e
        elif kind=='segment-parent' and cfg['proposal_barrier']=='segment':generation[sid]+=1
        elif kind=='proposal-rebase':generation[sid]+=1
        elif kind=='commit':
            F[sid]=e['audio_end_sample'];actions[sid].append((e['installed'],seq,'F',F[sid],True))
        elif kind=='canonical-display':
            actions[sid].append((e['displayed'],seq,'V',e['audio_end_sample'],True))
            corrections.append({'session_id':sid,'version':e['version'],'audio_rollback_samples':e['audio_rollback_samples'],
                'erased_characters':e['erased_characters']})
        elif kind=='display':
            j=jobs[e['job_id']];valid=j['audio_end_sample']>F[sid] and j['branch_generation']==generation[sid]
            actions[sid].append((e['displayed'],seq,'V',e['audio_end_sample'],valid));outcome[e['job_id']]='display'
        elif kind=='proposal-obsolete':retired.append(e['job_id']);outcome[e['job_id']]='retired'
        elif kind=='proposal-skip':skipped+=1
    slots=[]
    for sid,stream in actions.items():
        current=ever=committed=0;last=0.;withdrawn=behind=area=0.
        for t,seq,kind,end,valid in sorted(stream)+[(res['wall_seconds_including_arrival_and_drain'],10**12,'END',0,True)]:
            dt=max(0.,t-last);gap=max(0,ever-current)/16000
            if gap>0:withdrawn+=dt;area+=dt*gap
            if current<committed:behind+=dt
            if kind=='F':committed=end
            elif kind=='V':
                current=end
                if valid:ever=max(ever,end)
            last=t
        slots.append({'session_id':sid,'withdrawn_future_coverage_slot_seconds':withdrawn,
            'withdrawn_audio_wall_area':area,'visible_behind_committed_slot_seconds':behind,
            'final_visible_frontier':current,'ever_valid_frontier':ever,'final_committed_frontier':committed})
    batch_union=all_retired_union=mixed_union=retired_job_sum=0.
    for e in events:
        if e['kind']!='worker-status' or e['status']!='batch-started':continue
        ids=e['job_ids']
        if jobs[ids[0]]['role']!='proposal':continue
        ds=[completed[j] for j in ids]
        if any(d.get('gpu_model_started') is None for d in ds):continue
        duration=max(d['gpu_model_completed'] for d in ds)-min(d['gpu_model_started'] for d in ds)
        batch_union+=duration;n=sum(outcome.get(j)=='retired' for j in ids)
        if n==len(ids):all_retired_union+=duration
        elif n:mixed_union+=duration
        for jid,d in zip(ids,ds):
            if jid in retired:retired_job_sum+=d['gpu_model_completed']-d['gpu_model_started']
    return {'cell':cell.name,'slots':slots,'corrections':corrections,'retired_jobs':len(retired),'skipped_without_dispatch':skipped,
        'proposal_batch_model_call_seconds':batch_union if batch_union else None,'all_retired_batch_model_call_seconds':all_retired_union if batch_union else None,
        'mixed_retirement_batch_model_call_seconds':mixed_union if batch_union else None,'retired_job_model_duration_sum':retired_job_sum if batch_union else None,
        'scope':'Model-call interval is not kernel busy time; per-job sum duplicates shared batch duration. Ever-first-display latency is not continuous visibility.'}
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    rows=[audit(c) for c in sorted(a.root.iterdir()) if (c/'result.json').exists()]
    a.out.write_text(json.dumps({'cells':rows},indent=2)+'\n');print('visibility and retired-work cells',len(rows))

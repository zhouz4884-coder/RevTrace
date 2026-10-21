"""Independent event-time audit of actual Phase N T1 publications, not a new GPU trial."""
import csv,hashlib,json,math,sys
from pathlib import Path
from collections import defaultdict
BASE=Path(sys.argv[1]);OUT=Path(sys.argv[2]);OUT.mkdir(parents=True,exist_ok=True)
ROOT=BASE/'results/revtrace/phaseN_20261021/t1_v4'
def quantile(v,q):
 if not v:return None
 v=sorted(v);x=(len(v)-1)*q;a=int(x);return v[a]+(v[min(a+1,len(v)-1)]-v[a])*(x-a)
def writecsv(p,rows):
 if not rows:return
 with p.open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
cases=[];norm=[];traces=[];hashes=[];issues=[]
for cell in sorted(ROOT.iterdir()):
 if not (cell/'result.json').exists():continue
 cfg=json.loads((cell/'config.json').read_text());res=json.loads((cell/'result.json').read_text());sessions={s['session_id']:s for s in json.loads((cell/'sessions.json').read_text())}
 es=[json.loads(x) for x in (cell/'events.jsonl').read_text().splitlines()];jobs={e['job_id']:e for e in es if e['kind']=='enqueue'}
 done={e['job_id']:e for e in es if e['kind']=='executor-complete'};commits={e['job_id']:e for e in es if e['kind']=='commit'};acks={e['job_id']:e for e in es if e['kind']=='install-ack'}
 vis={sid:{'F':0,'V':0,'E':0,'text':'','canonical':'','last':0.,'area':0.,'lag_area':0.,'lead_area':0.} for sid in sessions};streams=defaultdict(list);cellcases=[]
 for e in es:
  if e.get('session_id') is not None and e['kind'] in ['commit','canonical-display','display']:streams[e['session_id']].append(e)
 for sid,stream in streams.items():
  s=sessions[sid];state=vis[sid];duration=s['duration'];offset=s['offset'];timeline=[]
  for e in stream:
   k=e['kind'];t=e.get('displayed',e.get('installed',e['time']));t=max(t,state['last'])
   dt=t-state['last'];state['area']+=max(0,state['E']-state['V'])/16000*dt
   # Integrate released frontier exactly for constant committed F between events.
   a=max(offset+state['F']/16000,state['last']);b=t
   if b>a:
    z=offset+duration;m=min(b,z)
    if m>a:state['lag_area']+=((m-offset-state['F']/16000)**2-(a-offset-state['F']/16000)**2)/2
    if b>max(a,z):state['lag_area']+=(b-max(a,z))*(duration-state['F']/16000)
   state['lead_area']+=max(0,state['V']-state['F'])/16000*dt
   if k=='commit':state['F']=e['audio_end_sample']
   else:
    end=e['audio_end_sample'];oldF=state['F'] if k=='display' else commits[e['job_id']]['audio_start_sample'];lcp=0
    for a,b in zip(state['text'],e['text']):
     if a!=b:break
     lcp+=1
    erased=len(state['text'])-lcp;rollback=max(0,state['V']-end)/16000
    if abs(rollback-e.get('audio_rollback_samples',0)/16000)>1e-9 or erased!=e.get('erased_characters',0):issues.append([cell.name,sid,'logged rollback mismatch'])
    if k=='canonical-display':
     c=commits[e['job_id']];d=done[e['job_id']];j=jobs[e['job_id']];ack=acks[e['job_id']]
     ready=min(duration,max(0,t-offset));canonical_lcp=0
     for a,b in zip(state['canonical'],e['text']):
      if a!=b:break
      canonical_lcp+=1
     nexts=[x for x in stream if x.get('displayed',-1)>t and x.get('audio_end_sample',0)>=state['V'] and x['kind'] in ['display','canonical-display']]
     recovery=nexts[0]['displayed']-t if rollback and nexts else (None if rollback else 0.)
     prev=timeline[-1] if timeline else {};pj=jobs.get(prev.get('job_id'),{})
     row={'cell':cell.name,'rho':cfg['rho'],'barrier':cfg['proposal_barrier'],'repeat':int(cell.name.rsplit('r',1)[1]),'observer':int('-obs1-' in cell.name),'session_id':sid,'source_id':s['source_id'],'language':s['language'],
      'version':e['version'],'job_id':e['job_id'],'time':t,'audio_duration':duration,'old_committed_frontier':oldF/16000,'pre_visible_frontier':state['V']/16000,'new_committed_frontier':end/16000,
      'released_frontier':ready,'arrival_lag_before':max(0,ready-oldF/16000),'speculative_lead_before':max(0,state['V']-oldF)/16000,'rollback_audio_seconds':rollback,'erased_characters':erased,
      'canonical_text_erased':len(state['canonical'])-canonical_lcp,'prior_publication_kind':prev.get('kind','none'),'prior_private_parent':pj.get('parent'),'prior_private_generation':pj.get('branch_generation'),
      'new_parent':j['parent'],'old_text':state['text'],'new_text':e['text'],'prior_canonical_text':state['canonical'],
      'authority_model_start':d['gpu_model_started'],'authority_model_end':d['gpu_model_completed'],'authority_received':d['received'],'wal_installed':c['installed'],'acknowledged':ack['acknowledged'],
      'publication_after_install':t-c['installed'],'rollback_recovered_seconds':recovery,'recovery_censored':int(bool(rollback and recovery is None)),
      'observed_category':'full_snapshot_covers_ahead_private_potentially_avoidable_NOT_PROVEN' if rollback else ('canonical_content_revision' if erased else 'no_erasure'),
      'next_authority_model_start':next((done[x['job_id']]['gpu_model_started'] for x in stream if x['kind']=='commit' and x['version']==e['version']+1),None)}
     cellcases.append(row);state['canonical']=e['text']
    state['V']=end;state['E']=max(state['E'],end);state['text']=e['text'];timeline.append(e)
   state['last']=t
   traces.append({'cell':cell.name,'session_id':sid,'source_id':s['source_id'],'kind':k,'time':t,'released':min(duration,max(0,t-offset)),'committed':state['F']/16000,'visible':state['V']/16000,'ever':state['E']/16000})
  dt=max(0,res['wall_seconds_including_arrival_and_drain']-state['last']);state['area']+=max(0,state['E']-state['V'])/16000*dt
  rows=[r for r in cellcases if r['session_id']==sid];depth=[r['rollback_audio_seconds'] for r in rows if r['rollback_audio_seconds']>0];roll=len(depth)
  norm.append({'cell':cell.name,'rho':cfg['rho'],'barrier':cfg['proposal_barrier'],'observer':int('-obs1-' in cell.name),'session_id':sid,'source_id':s['source_id'],'language':s['language'],'canonical_publications':len(rows),'rollback_events':roll,'rollback_event_rate':roll/len(rows) if rows else None,'audio_minutes':duration/60,'events_per_audio_minute':roll*60/duration,'depth_p50':quantile(depth,.5),'depth_p95':quantile(depth,.95),'depth_p99':quantile(depth,.99),'depth_max':max(depth,default=0),'rollback_audio_seconds_sum':sum(depth),'erased_characters':sum(r['erased_characters'] for r in rows),'canonical_revision_events':sum(r['canonical_text_erased']>0 for r in rows),'withdrawn_audio_wall_area':state['area'],'lag_time_area_until_last_publication':state['lag_area'],'speculative_lead_area':state['lead_area'],'recovery_censored_events':sum(r['recovery_censored'] for r in rows)})
 cases+=cellcases;hashes.append({'cell':cell.name,'events_sha256':hashlib.sha256((cell/'events.jsonl').read_bytes()).hexdigest(),'config_sha256':hashlib.sha256((cell/'config.json').read_bytes()).hexdigest(),'code_commit':json.loads((cell/'provenance.json').read_text())['code_commit']})
writecsv(OUT/'ROLLBACK_EVENT_CASES.csv',cases);writecsv(OUT/'ROLLBACK_NORMALIZED.csv',norm);writecsv(OUT/'FRONTIER_TRAJECTORIES.csv',traces)
groups=[]
for cell in sorted(set(r['cell'] for r in norm)):
 rs=[r for r in norm if r['cell']==cell];cr=[r for r in cases if r['cell']==cell]
 groups.append({'cell':cell,'canonical_publications':sum(r['canonical_publications'] for r in rs),'rollback_events':sum(r['rollback_events'] for r in rs),'rate':sum(r['rollback_events'] for r in rs)/len(cr),'audio_seconds':sum(r['audio_minutes']*60 for r in rs),'erased_characters':sum(r['erased_characters'] for r in rs),'rollback_audio_seconds_sum':sum(r['rollback_audio_seconds_sum'] for r in rs),'withdrawn_audio_wall_area':sum(r['withdrawn_audio_wall_area'] for r in rs),'canonical_revision_events':sum(r['canonical_revision_events'] for r in rs)})
writecsv(OUT/'ROLLBACK_BY_CELL.csv',groups)
(OUT/'AUDIT.json').write_text(json.dumps({'decision':'PASS_EVENT_RECONSTRUCTION' if not issues else 'FAIL','issues':issues,'cells':groups,'source_hashes':hashes,'scope':'actual GPU trace read-only audit; repeated slots not independent sources; potential avoidability not proved'},indent=2)+'\n')
print(json.dumps({'decision':'PASS' if not issues else 'FAIL','cells':len(groups),'rows':len(cases),'formal': [r for r in groups if '-obs1-' in r['cell']]}));assert not issues

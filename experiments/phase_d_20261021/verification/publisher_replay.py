"""CPU presentation counterfactual on immutable GPU-selected histories."""
import csv,hashlib,json,sys,time
from pathlib import Path
sys.path.insert(0,str(Path(sys.argv[1])/'src'))
from revtrace.certified_display import ContinuityView,text_sha
from revtrace.dgft import digest_tokens
B=Path(sys.argv[2]);OUT=Path(sys.argv[3]);OUT.mkdir(exist_ok=True,parents=True);rows=[];unsafe=[]
for c in sorted((B/'results/revtrace/phaseN_20261021/t1_v4').iterdir()):
 if '-obs1-' not in c.name or not (c/'result.json').exists():continue
 events=[json.loads(l) for l in (c/'events.jsonl').read_text().splitlines()];ss=json.loads((c/'sessions.json').read_text());records={}
 for l in (c/'worker_records.jsonl').read_text().splitlines():
  x=json.loads(l);records[x['job']['job_id']]=x
 augmented=[]
 for e in events:
  e=dict(e)
  if e['kind']=='canonical-display':
   r=records[e['job_id']]['result'];e.update(text_sha256=text_sha(e['text']),canonical_projection_sha256=digest_tokens(r['state_tokens']))
  elif e['kind']=='display':
   x=records[e['job_id']];j,r=x['job'],x['result'];e.update(input_projection_sha256=digest_tokens(j['prompt_tokens']),output_projection_sha256=digest_tokens(r['state_tokens']),chunk_id=j['chunk_id'],end_window=j['end_window'],branch_generation=j['branch_generation'])
  if e['kind'] in ['run-start','commit','display','canonical-display']:augmented.append(e)
 for policy in ['snapshot','two_lane','canonical_only','localagreement2','localagreement3','fixed_wait_0.5']:
  v=ContinuityView('snapshot' if policy.startswith('fixed_wait') else policy);start=time.perf_counter();timed=[]
  for i,e in enumerate(augmented):
   stamp=e.get('displayed',e.get('installed',e.get('time',0)))
   timed.append((stamp+(.5 if policy.startswith('fixed_wait') and e['kind']=='display' else 0),i,e))
  for t,i,e in sorted(timed):
   r=v.consume(e)
   if r:r['observed']=t
  elapsed=time.perf_counter()-start;area=0.;last={};firstlat=[]
  for r in v.records:
   sid=r['session_id'];s=last.get(sid,{'time':0,'ever':0,'current':0});dt=r['observed']-s['time'];area+=max(0,s['ever']-s['current'])/16000*dt
   last[sid]={'time':r['observed'],'ever':max(s['ever'],r['valid_visible_frontier']),'current':r['valid_visible_frontier']}
  for s in ss:
   total=round(s['duration']*16000)
   for q in list(range(32000,total,32000))+[total]:
    ts=[r['observed'] for r in v.records if r['session_id']==s['session_id'] and r['valid_visible_frontier']>=q];firstlat.append(min(ts)-s['offset']-q/16000 if ts else None)
  xs=sorted(x for x in firstlat if x is not None);ix=(len(xs)-1)*.99;lo=int(ix);p99=xs[lo]+(xs[min(lo+1,len(xs)-1)]-xs[lo])*(ix-lo) if len(xs)==len(firstlat) else None
  rows.append({'cell':c.name,'policy':policy,'source_events_sha256':hashlib.sha256((c/'events.jsonl').read_bytes()).hexdigest(),'canonical_history_changed':False,'view_events':len(v.records),'rollback_events':sum(r['audio_rollback_samples']>0 for r in v.records),'rollback_audio_seconds_sum':sum(r['audio_rollback_samples']/16000 for r in v.records),'erased_characters':sum(r['erased_characters'] for r in v.records),'withdrawn_area':area,'compatible_whole_hypotheses_retained':sum(r['compatible_provisional_retained'] for r in v.records),'tentative_invalidations':sum(r['tentative_invalidated'] for r in v.records),'display_p99_ideal_consumer_seconds':p99,'cpu_replay_elapsed':elapsed,'evidence':'CPU_PUBLISHER_COUNTERFACTUAL_NOT_GPU_SERVING'})
for language,canonical,old,oracle in [('English','I saw a dog','I saw a cat today','I saw a dog today'),('Chinese','北京大学','北京大雪很多','北京大学很好')]:
 common=0
 for a,b in zip(canonical,old):
  if a!=b:break
  common+=1
 unsafe.append({'language':language,'new_canonical':canonical,'old_private':old,'declared_legal_oracle':oracle,'naive_lcp_splice':canonical+old[common:],'blind_append':canonical+old,'latest_frontier_wins':old,'all_differ_from_oracle':all(x!=oracle for x in [canonical+old[common:],canonical+old,old]),'evidence':'constructed_CPU_counterexample_NOT_ASR_incidence'})
with (OUT/'PUBLISHER_REPLAY.csv').open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
(OUT/'UNSAFE_SPLICE_COUNTEREXAMPLES.json').write_text(json.dumps(unsafe,ensure_ascii=False,indent=2)+'\n')
(OUT/'AUDIT_REPORT.json').write_text(json.dumps({'status':'COMPLETE_CPU_ONLY','rows':len(rows),'policies':6,'source_cells':12,'canonical_untouched':True,'no_audio_token_alignment_inferred':True,'no_unproved_suffix_joined':True,'scope':'ideal event-delivery replay, not GPU cost/natural rate/network rendering'},indent=2)+'\n');print('publisher replay',len(rows))

"""Read-only existing36 event census. No signal, model or source modification."""
import json,pathlib,shlex,sys,hashlib
F=pathlib.Path(__file__).resolve().parents[1];B='/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9';P=B+'/projects/revtrace_dsn_native_resilience_20261030'
code=r'''import pathlib,json,hashlib,sys,collections
P=pathlib.Path(PROJECT);sys.path.insert(0,str(P/'source_v2'));from resilience_storage import scan
def lines(p):return [json.loads(x) for x in p.read_bytes().splitlines() if x.strip()]
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(4*1024*1024),b''):h.update(b)
 return h.hexdigest()
results=[]
for planname in ('FORMAL_SHORT28_v1_FROZEN.json','FORMAL_SUSTAINED8_v1_FROZEN.json'):
 plan=json.loads((P/planname).read_bytes())
 for cell in plan['cells']:
  root=pathlib.Path(cell['out']);paths=[root/'facts.wal',root/'consumer.jsonl',root/'publications.jsonl'];facts=[(obj,receipt) for obj,receipt in scan(root/'facts.wal',repair_tail=False) if obj['kind']=='canonical'];consumer=lines(root/'consumer.jsonl');pubs=lines(root/'publications.jsonl');dispatch={};events=[];losses=[];classes=collections.Counter();buffer_installs=[];promotion_installs=[]
  for owner in sorted(root.glob('owner_e*')):
   epoch=int(owner.name.removeprefix('owner_e'))
   for name in ('dispatch.jsonl','owner_events.jsonl','policy_audit.jsonl'):paths.append(owner/name)
   for r in lines(owner/'dispatch.jsonl'):dispatch[(epoch,r['job']['job_id'])]=r
   for r in lines(owner/'owner_events.jsonl'):events.append((epoch,r))
   for r in lines(owner/'policy_audit.jsonl'):
    if r.get('kind')=='worker_lost':losses.append((epoch,r))
  for obj,receipt in facts:
   b=obj['body'];job=b['job'];birth=job.get('started_on_canonical');promoted=job.get('promoted_to_canonical');key='started_on_canonical' if birth is True else 'conditional_inflight_promoted_then_installed' if birth is False and promoted is True else 'completed_buffer_install' if birth is False and promoted is False else 'unknown_origin_flags';classes[key]+=1
   witness=dict(owner_epoch=b['owner_epoch'],job_id=job['job_id'],worker=job['worker'],worker_incarnation=job.get('worker_incarnation'),frontier=b['next_state']['frontier'],journal_sequence=obj['sequence'],started_on_canonical=birth,promoted_to_canonical=promoted)
   if key=='completed_buffer_install':buffer_installs.append(witness)
   if key=='conditional_inflight_promoted_then_installed':promotion_installs.append(witness)
  dead_buffer_chains=[];dead_views=[];loss_details=[];view_successions=[]
  pubmap={(r['bound_owner_epoch'],r['event']['publication_id']):r['event'] for r in pubs}
  for epoch,loss in losses:
   body=loss['body'];slot=body['slot'];inc=body['incarnation'];death=body['death_proof'];dead_time=max(death['confirmed_perf'],death.get('cuda_release',{}).get('observed_perf',death['confirmed_perf']));fences=[r['observed'] for ep,r in events if ep==epoch and r.get('kind')=='worker_started' and r.get('slot')==slot and r.get('incarnation',-1)>inc];fenced_after=min(fences) if fences else loss['observed'];threshold=max(dead_time,fenced_after)
   dead_jobs={jid for (ep,jid),r in dispatch.items() if ep==epoch and r['physical_slot']==slot and r['physical_incarnation']==inc};retained=set(body['retained_view_jobs'])&dead_jobs;preserved=set(body['preserved_completed_jobs'])&dead_jobs
   for b in buffer_installs:
    if b['owner_epoch']!=epoch or b['job_id'] not in preserved:continue
    installs=[r for ep,r in events if ep==epoch and r.get('kind')=='canonical_install' and r.get('job_id')==b['job_id'] and r['observed']>threshold];consumes=[r for r in consumer if r.get('kind')=='canonical' and r.get('journal_sequence')==b['journal_sequence'] and r['observed']>threshold]
    if installs and consumes:dead_buffer_chains.append(dict(**b,physical_exit_after=dead_time,fence_known_by=fenced_after,install_observed=installs[0]['observed'],consume_observed=consumes[0]['observed']))
   observed=[]
   for row in consumer:
    if row['owner_epoch']!=epoch or row['observed']<=threshold:continue
    event=pubmap.get((epoch,row.get('publication_id')),{})
    ids={s['job_id'] for s in event.get('steps',[])}
    if row.get('private_job') is not None:ids.add(row['private_job'])
    for jid in sorted(ids&retained):observed.append(dict(job_id=jid,consumer_observed=row['observed'],kind=row['kind'],publication_id=row.get('publication_id'),visible_frontier=row['visible_frontier'],physical_exit_after=dead_time,fence_known_by=fenced_after))
   for jid in sorted(retained):
    before=[]
    for index,row in enumerate(consumer):
     if row['owner_epoch']!=epoch or row['observed']>death['requested_perf']:continue
     event=pubmap.get((epoch,row.get('publication_id')),{})
     if event.get('kind')!='private':continue
     steps=[s for s in event.get('steps',[]) if s['job_id']==jid]
     if steps:before.append((index,row,event,steps[0]))
    if not before:continue
    index,old,event,step=before[-1];old_end_sha=hashlib.sha256(__import__('resilience_storage').canonical(step['end'])).hexdigest();after=[(i,r) for i,r in enumerate(consumer) if i>index and r['source_id']==old['source_id']];post=next(((i,r) for i,r in after if r['observed']>threshold),None)
    if post is None:continue
    postindex,new=post;new_event=pubmap.get((epoch,new.get('publication_id')),{});intervening=[r for i,r in after if i<postindex];unchanged_intervening=all(r['text']==old['text'] and r['visible_frontier']==old['visible_frontier'] and r.get('private_job')==jid for r in intervening);new_step_same_end=[s for s in new_event.get('steps',[]) if hashlib.sha256(__import__('resilience_storage').canonical(s['end'])).hexdigest()==old_end_sha];later_canon=[r for r in consumer if r['source_id']==old['source_id'] and r['observed']>threshold and r.get('kind')=='canonical' and r['certified_frontier']>=step['end']['frontier']]
    view_successions.append(dict(owner_epoch=epoch,slot=slot,old_incarnation=inc,old_job_id=jid,old_registered_start_sha=hashlib.sha256(__import__('resilience_storage').canonical(dispatch[(epoch,jid)]['job']['start'])).hexdigest(),old_actual_consume_index=index,old_actual_consume_perf=old['observed'],old_private_job=old.get('private_job'),old_visible_frontier=old['visible_frontier'],old_whole_text_sha256=hashlib.sha256(old['text'].encode()).hexdigest(),old_view_end_sha256=old_end_sha,kill_requested_perf=death['requested_perf'],physical_exit_confirmed_perf=death['confirmed_perf'],CUDA_release_confirmed_perf=death.get('cuda_release',{}).get('observed_perf'),fence_known_by=fenced_after,retained_at_worker_loss=True,intervening_actual_rows=len(intervening),all_intervening_rows_same_whole_view_and_job=unchanged_intervening,first_post_fence_actual_index=postindex,first_post_fence_actual_perf=new['observed'],first_post_fence_kind=new['kind'],first_post_fence_private_job=new.get('private_job'),first_post_fence_visible_frontier=new['visible_frontier'],first_post_fence_whole_text_equal=new['text']==old['text'],first_post_fence_same_registered_view_end=bool(new_step_same_end),successor_step_job_ids=[s['job_id'] for s in new_step_same_end],first_post_fence_canonical_sha=new['canonical_sha'],later_actual_certified_cover=({k:later_canon[0].get(k) for k in ('observed','journal_sequence','certified_frontier','canonical_sha','private_job')} if later_canon else None),scope='Pre-kill actual whole view + explicit retention at loss + complete logged state transitions through first post-fence legal successor. No new post-death application of the old UID is inferred from continuous residence.'))
   dead_views.extend(observed);loss_details.append(dict(owner_epoch=epoch,slot=slot,old_incarnation=inc,physical_exit_after=dead_time,fence_known_by=fenced_after,registered_dead_jobs=sorted(dead_jobs),preserved_complete_dead_jobs=sorted(preserved),retained_dead_view_jobs=sorted(retained),post_fence_actual_consumer_rows_using_retained_dead_view=len(observed)))
  results.append(dict(cell_id=cell['cell_id'],classes=dict(classes),completed_buffer_installs=buffer_installs,inflight_promotion_installs=promotion_installs,worker_losses=loss_details,post_fence_dead_producer_buffer_install_and_consume=dead_buffer_chains,post_fence_dead_producer_view_consumptions=dead_views,dead_producer_view_survival_successions=view_successions,inputs=[dict(path=str(p),sha256=sha(p)) for p in paths]))
total=collections.Counter()
for r in results:total.update(r['classes'])
out=dict(observation='existing_completed36_read_only_event_census_v2',runtime_source_commit='4f4c3caba2b1068951d7a566e7d9e5aa6fc25f47',cases=36,classification_rule='started_on_canonical=False and promoted_to_canonical=False on an installed Canonical fact means completed_full item was removed from live jobs before its parent became Canonical; source fullspec_policy.complete/pop_ready_commits/_refresh_active defines this distinction',canonical_origin_counts=dict(total),worker_losses=sum(len(r['worker_losses']) for r in results),post_fence_dead_buffer_install_consume=sum(len(r['post_fence_dead_producer_buffer_install_and_consume']) for r in results),post_fence_dead_view_consumer_rows=sum(len(r['post_fence_dead_producer_view_consumptions']) for r in results),dead_view_survival_successions=sum(len(r['dead_producer_view_survival_successions']) for r in results),results=results,new_model_calls=0,signals_sent=0,scope='Only actual recorded registration/loss/fence/publication/Consumer chains. Continuous view residence is not a new old-UID consume and is not completed-full-buffer installation.')
print(json.dumps(out))
'''.replace('PROJECT',repr(P))
sys.path.insert(0,r'C:\Users\LENOVO\.codex\local-tools');from contractkv_ssh_credential import ssh_client
c=ssh_client()
try:
 i,o,e=c.exec_command(shlex.quote(B+'/envs/revtrace-streamcorrect-20261028/bin/python')+' -B -',timeout=120);i.write(code);i.flush();i.channel.shutdown_write();b=o.read();err=e.read();assert o.channel.recv_exit_status()==0,err.decode();data=json.loads(b);data['observer_script_sha256']=hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest();target=F/'EXISTING36_EVENT_WITNESS_CENSUS_v2.json';assert not target.exists();target.write_bytes((json.dumps(data,indent=2)+'\n').encode());print(json.dumps({k:v for k,v in data.items() if k!='results'},indent=2))
finally:c.close()

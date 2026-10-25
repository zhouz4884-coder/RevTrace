"""Independent recorded-prefix recovery and whole-offered cost audit.

Imports only shared stat/hash helpers, not the live scheduler, input journal,
Consumer or control rule. Read-only production admission replay is a SEPARATE
gate. Missing observations receive no deadline credit. No GPU generation here.
"""
from pathlib import Path
import argparse,hashlib,json,math,re,struct
from audit_n5 import read,wire,sha,tokens,edits,normalized,quantile,export_float,chain

def rows(p,partial=False):
 if not p.exists():return [],0
 raw=p.read_bytes();out=[];lost=0
 for i,line in enumerate(raw.splitlines(keepends=True)):
  try:out.append(json.loads(line))
  except (json.JSONDecodeError,UnicodeDecodeError):
   assert partial and not line.endswith(b'\n') and i==len(raw.splitlines())-1
   lost=len(line)
 return out,lost
def frames(p,partial=False,input_log=False):
 raw=p.read_bytes();offset=0;seq=0;prev='';result=[]
 while offset<len(raw):
  if len(raw)-offset<4:assert partial;break
  n=struct.unpack_from('>I',raw,offset)[0];assert 0<n<=32*1024*1024
  end=offset+4+n+32
  if end>len(raw):assert partial;break
  body=raw[offset+4:offset+4+n];checksum=hashlib.sha256(body).digest();assert raw[offset+4+n:end]==checksum
  r=json.loads(body);assert r['sequence']==seq and r['previous_sha256']==prev
  result.append(r);prev=sha(r) if input_log else checksum.hex();offset=end;seq+=1
 return result,len(raw)-offset
def episode(E,manifest):
 ctx=read(E/'CONTEXT.json');origin=ctx['origin_perf'];kill=read(E/'KILL.json');assert kill['episode_origin_perf']==origin
 final=read(E/'attempt1/result.json');cfg=read(E/'attempt1/config.json');assert cfg['episode_origin_perf']==origin
 assert read(E/'attempt0/config.json')==cfg,'same execution/arrival contract across restart'
 specs={s['session_id']:s for s in read(E/'attempt1/sessions.json')};fine=cfg['fine_seconds']*16000
 sources={s['source_id']:s for s in manifest['sessions']};fr,tail=frames(E/'input.wal',input_log=True);assert tail==0
 pre_input,pre_tail=frames(E/'input.wal.pre-recovery',True,True)
 wal,tail=frames(E/'canonical.wal');assert tail==0
 pre_wal,pre_wal_tail=frames(E/'canonical.wal.pre-recovery',True)
 assert wal[:len(pre_wal)]==pre_wal and fr[:len(pre_input)]==pre_input
 assert fr[0]['manifest_sha256']==cfg['manifest_sha256']
 Aold={sid:0 for sid in specs};Cmeta={sid:0 for sid in specs};J=set();maxdebt=maxcredit=0
 for r in fr[1:]:
  assert r['kind']=='envelope-snapshot';s=r['snapshot'];assert sha(s)==r['snapshot_sha256'] and s['origin_perf']==origin
  debt=credit=0
  for k,v in s['sessions'].items():
   sid=int(k);O,A,C,R=[v[x] for x in ['offered','accepted','certified','reserved']]
   assert 0<=C<=A<=O and R>=A and A>=Aold[sid] and C>=Cmeta[sid]
   if sid in J:assert v['rejected']
   if v['rejected']:assert A==C==0 and v['rejection_reason'];J.add(sid)
   debt+=A-C;credit+=R-C;Aold[sid]=A;Cmeta[sid]=C
  assert 0<=debt<=credit<=s['budget'];maxdebt=max(maxdebt,debt);maxcredit=max(maxcredit,credit)
 # Parse immutable pre-dispatch and worker-complete evidence under each process.
 alljobs={};allres={};paid_batches=completed_batches=completed_rows=0;partial_traces=0;drain_times=[]
 for attempt in [0,1]:
  D=E/f'attempt{attempt}';jobs={};results={};drained=[];lease_timeline=[]
  for path in D.glob('*.submissions'):
   items,lost=rows(path,attempt==0);partial_traces+=lost
   for row in items:
    assert row['kind']=='batch-submit';paid_batches+=1
    lease_timeline.append((row['observed_perf'],1,row['worker'],row['batch_id']))
    for j in row['jobs']:
     assert j['job_id'] not in jobs;jobs[j['job_id']]=j
  for path in D.glob('worker-*-receipts.jsonl'):
   items,lost=rows(path,attempt==0);partial_traces+=lost
   for row in items:
    m=row['message']
    if row['kind']=='row-complete':
     r=json.loads(m['payload_json']);assert hashlib.sha256(m['payload_json'].encode()).hexdigest()==m['payload_digest']
     b=m['binding'];j=jobs[b['job_id']]
     assert b==j['_delivery']['binding'] and b['contract_epoch']==attempt+1
     assert r['job_id']==j['job_id'] and r['runtime_digest']==j['runtime_digest']
     assert j['audio_ready_perf']<=j['enqueue_perf']<=r['started_perf']<=r['model_started_perf']<=m['terminal_perf']<=m['rendered_perf']<=m['emitted_perf']
     sid=j['session_id'];assert abs(j['audio_ready_perf']-(origin+specs[sid]['offset']+j['audio_end_sample']/16000))<1e-7
     audit=r['model_input_audit'];exe=r['execution_context_audit']
     assert exe['executed_prompt_tokens']==j['prompt_tokens'] and not exe['fault_override']
     assert audit['declared_prompt_tokens']==j['prompt_tokens'] and audit['waveform_sha256']==j['prefix_audio_sha256']==r['prefix_audio_sha256']
     assert audit['dtype']==('float32' if j['role']=='authority' else 'float16')
     assert r['generated_tokens']==len(r['token_ids'])<=256
     assert r['terminated_by_eos']==(r['token_ids'][-1] in audit['eos_token_ids'])
     assert r['terminated_by_eos'] or len(r['token_ids'])==256
     r['_row_receipt']=m;r['received_perf']=m['emitted_perf'];results[j['job_id']]=r;completed_rows+=1
    elif row['kind']=='batch-drained':
     b=row['physical_accounting'];assert set(b['job_ids'])==set(dict(m['row_digests']))
     for jid,digest in m['row_digests']:assert results[jid]['_row_receipt']['payload_digest']==digest
     drained.append(b);completed_batches+=1;drain_times.append(m['completed_perf'])
     lease_timeline.append((m['completed_perf'],0,m['worker'],m['batch_id']))
    else:raise AssertionError('unknown worker trace')
  leases={}
  for at,kind,worker,batch in sorted(lease_timeline):
   if kind:
    assert worker not in leases,'physical lease reused before actual Batch-drained';leases[worker]=batch
   else:assert leases.pop(worker)==batch
  if attempt==1:assert not leases
  # Old pending leases are killed, never described as drained or free earlier.
  for k,j in jobs.items():alljobs[attempt,k]=j
  for k,r in results.items():allres[attempt,k]=r
  if attempt==1:
   owner={r['job']['job_id']:r for r in rows(D/'worker_records.jsonl')[0]}
   assert set(owner)==set(jobs)==set(results)
   for jid,r in owner.items():
    for k in ['token_ids','state_tokens','text','terminated_by_eos']:assert r['result'][k]==results[jid][k]
 # Independently verify all canonical intervals, binding and real selected rows.
 state={int(k):dict(F=s['audio_frontier_window'],P=s['prompt_tokens'],version=s['checkpoint_id'],epoch=s['contract_epoch']) for k,s in wal[0]['states'].items()}
 consumed=set();canonical={};restart=0;preC={sid:0 for sid in specs};prior=0
 for record in wal[1:]:
  if record['kind']=='restart_epoch':
   restart+=1;preC={sid:s['F'] for sid,s in state.items()};prior=len(canonical)
   for s in state.values():assert record['next_contract_epoch']==s['epoch']+1;s['epoch']+=1
   continue
  assert record['kind']=='commit';e=record['event'];d=record['state_delta'];sid=record['session_id'];s=state[sid]
  assert (sid,record['transaction_id']) not in consumed;consumed.add((sid,record['transaction_id']))
  assert record['transaction_id']==f"{sid}:{d['audio_start_sample']}:{d['audio_end_sample']}"
  assert record['parent_checkpoint_id']==s['version'] and d['audio_start_sample']==s['F']<d['audio_end_sample']
  cert=e['certificate']
  # Epoch is bound by the frozen job/row registry and WAL restart chain, not
  # a nonexistent field in this serialized DualAxis certificate.
  assert cert['contract_digest']==final['contract_digest'] and cert['prompt_sha256']==tokens(s['P'])
  assert cert['parent_checkpoint_id']==s['version']
  candidates=[(j,r) for key,r in allres.items() for j in [alljobs[key]] if j['role']=='authority' and
   j['session_id']==sid and j['contract_epoch']==s['epoch'] and j['parent']==s['version'] and
   j['audio_start_sample']==s['F'] and j['audio_end_sample']==d['audio_end_sample'] and
   r['token_ids']==d['segment_tokens'] and r['state_tokens']==d['next_prompt_tokens']]
  assert candidates,'no completed actual Authority evidence for selected canonical write'
  assert all(j['prompt_tokens']==s['P'] for j,r in candidates)
  assert cert['display_sha256']==tokens(d['segment_tokens']) and cert['feedback_state_sha256']==tokens(d['next_prompt_tokens'])
  state[sid]=dict(F=d['audio_end_sample'],P=d['next_prompt_tokens'],version=s['version']+1,epoch=s['epoch'])
  canonical[sid,record['transaction_id']]=record
 assert restart==1 and len(canonical)==prior+final['certified_commits']
 initial1={r['session_id']:r['state'] for r in read(E/'attempt1/initial_states.json')}
 assert all(initial1[sid]['audio_frontier_window']==preC[sid] and initial1[sid]['contract_epoch']==2 for sid in specs)
 # Replay owner-event/actual applied view observations, under each owner epoch.
 firstV={};firstC={};post_recovery={};illegal=stale=modebad=0;allcons=[];ack_count=0
 for attempt in [0,1]:
  D=E/f'attempt{attempt}';events,lost=rows(D/'events.jsonl',attempt==0);partial_traces+=lost
  views,lost=rows(D/'consumer-live.jsonl',attempt==0);partial_traces+=lost;allcons+=views
  if attempt==1:assert views==rows(D/'consumer.jsonl')[0]
  start=next(e['t0_perf'] for e in events if e['kind']=='run-start');lookup={(r['session_id'],r['source_kind'],r['server_time']):r for r in views}
  assert len(lookup)==len(views)
  init={r['session_id']:r['state'] for r in read(D/'initial_states.json')}
  live={sid:dict(F=s['audio_frontier_window'],P=tuple(s['prompt_tokens']),version=s['checkpoint_id']) for sid,s in init.items()}
  A={sid:0 for sid in specs};nodes={sid:set() for sid in specs};generations={sid:0 for sid in specs}
  jobs={k[1]:v for k,v in alljobs.items() if k[0]==attempt};res={k[1]:v for k,v in allres.items() if k[0]==attempt}
  for e in events:
   kind=e['kind'];sid=e.get('session_id');at=start+e['time']
   if kind=='input-ledger-recovered':
    A={int(k):v for k,v in e['accepted'].items()}
    assert all(e['certified'][str(sid)]==live[sid]['F']<=A[sid] for sid in specs)
   if kind=='input-snapshot-synchronized':
    f=fr[e['input_sequence']];assert f['snapshot_sha256']==e['snapshot_sha256']
    for k,b in f['snapshot']['sessions'].items():
     slot=int(k);assert b['certified']==live[slot]['F'] and b['version']==live[slot]['version']
     O=min(round(specs[slot]['duration']*16000),max(0,math.floor((at-origin-specs[slot]['offset'])/cfg['fine_seconds'])*round(fine)))
     if at>=origin+specs[slot]['offset']+specs[slot]['duration']:O=round(specs[slot]['duration']*16000)
     assert b['offered']<=O and b['accepted']>=A[slot];A[slot]=b['accepted']
   if kind=='input-ack':
    b=fr[e['input_sequence']]['snapshot']['sessions'][str(sid)]
    assert e['to_sample']==b['accepted'] and e['prefix_sha256']==b['accepted_prefix_sha256'];ack_count+=1
    assert initial1[sid]['audio_frontier_window']<=max(A[sid],preC[sid]) if attempt==1 else True
   if kind=='enqueue':assert jobs[e['job_id']]['audio_end_sample']<=A[sid]
   if kind=='private-generation-retired':generations[sid]=e['generation']
   if kind=='enqueue' and e['role']=='proposal':generations[sid]=e['branch_generation']
   if kind=='commit':
    r=canonical[sid,e['segment_id']];assert r['event']['certificate']==e['certificate']
    assert e['parent']==live[sid]['version'] and e['audio_start_sample']==live[sid]['F']<e['audio_end_sample']<=A[sid]
    live[sid]=dict(F=e['audio_end_sample'],P=tuple(e['next_prompt_tokens']),version=e['version'])
   if kind=='display':
    j=jobs[e['job_id']];nodes[sid].add(j['job_id']);stale+=int(j['audio_end_sample']<=live[sid]['F'] or j['branch_generation']!=generations[sid])
   if kind not in ['display','canonical-display','view-mode']:continue
   row=lookup.get((sid,kind,e['displayed']))
   if row is None:continue # May be a nonapplied tail; never grant credit.
   s=live[sid];assert row['certified_frontier']==s['F'] and row['canonical_version']==s['version']
   assert row['canonical_epoch']==attempt+1 and row['observed_perf']>=start+e['displayed']
   vf=row['valid_visible_frontier']
   if vf>s['F']:
    candidates=[jid for jid in nodes[sid] if jobs[jid]['audio_end_sample']==vf and res[jid]['text']==row['visible_text']]
    illegal+=int(not any(chain(j,s['F'],s['P'],jobs,res,nodes[sid],fine) for j in candidates))
   if row['envelope_mode'] in ['RECOVERY','CERTIFIED-ONLY']:modebad+=int(vf!=s['F'])
   if attempt==1 and row['certified_frontier']>=preC[sid]:post_recovery.setdefault(sid,row['observed_perf'])
   for w in range(1,math.ceil(specs[sid]['duration']/cfg['fine_seconds'])+1):
    F=min(round(w*fine),round(specs[sid]['duration']*16000));key=(sid,F)
    if F<=vf:firstV.setdefault(key,row['observed_perf'])
    if F<=s['F']:firstC.setdefault(key,row['observed_perf'])
 assert illegal==stale==modebad==0 and set(post_recovery)==set(specs)
 for ack in kill['server_input_ACKs']:
  assert state[ack['session_id']]['F']>=ack['to_sample'],'accepted input obligation was lost'
 for row in final['final_states']:
  s=state[row['session_id']];assert row['state']['audio_frontier_window']==s['F'] and row['state']['prompt_tokens']==s['P']
  assert s['F']==round(specs[row['session_id']]['duration']*16000)
 # Same primary boundary as normal episodes: original arrival through actual
 # Consumer/model drain, including fault and cold reload, not rich-log teardown.
 # Retain the longer whole-process/resource lifecycle clock separately.
 outer_end=read(E/'RUN_COMPLETE_PENDING_AUDIT.json')['actual_episode_end_perf']
 start1=next(e['t0_perf'] for e in rows(E/'attempt1/events.jsonl')[0] if e['kind']=='run-start')
 end=max(origin+max(s['offset']+s['duration'] for s in specs.values()),max(r['observed_perf'] for r in allcons),
  max(drain_times),start1+final['wall_seconds_including_arrival_and_drain']);elapsed=end-origin
 frontiers=[]
 for sid,s in specs.items():
  prev=0
  for w in range(1,math.ceil(s['duration']/cfg['fine_seconds'])+1):
   F=min(round(w*fine),round(s['duration']*16000));ready=origin+s['offset']+F/16000
   d=firstV.get((sid,F),math.inf)-ready;c=firstC.get((sid,F),math.inf)-ready
   frontiers.append(dict(session=sid,frontier=F,audio_seconds=(F-prev)/16000,display_latency=d,commit_latency=c,dual_credit=d<=2 and c<=8));prev=F
 total=sum(s['duration'] for s in specs.values());power=read(E/'EPISODE_POWER.json');energy=0;coverage={}
 for gpu in [0,1]:
  xs=[r for r in power['samples'] if r['gpu']==gpu];covered=0
  for a,b in zip(xs,xs[1:]):
   lo=max(origin,a['t']);hi=min(end,b['t'])
   if hi<=lo:continue
   slope=(b['power_w']-a['power_w'])/(b['t']-a['t']);p0=a['power_w']+slope*(lo-a['t']);p1=a['power_w']+slope*(hi-a['t'])
   energy+=(p0+p1)*(hi-lo)/2;covered+=hi-lo
  coverage[str(gpu)]=covered/elapsed;assert coverage[str(gpu)]>.98
 we=wc=ce=cc=0
 for row in final['final_states']:
  ref=normalized(sources[specs[row['session_id']]['source_id']]['reference']);hyp=normalized(row['text'])
  a=re.findall(r"[a-z0-9']+",ref);b=re.findall(r"[a-z0-9']+",hyp);we+=edits(a,b);wc+=len(a)
  a=[x for x in ref if x.isalnum()];b=[x for x in hyp if x.isalnum()];ce+=edits(a,b);cc+=len(a)
 ds=[r['display_latency'] for r in frontiers];cs=[r['commit_latency'] for r in frontiers]
 return dict(episode=E.name,method=cfg['envelope']['method'],status='PASS_RECORDED_PREFIX_INPUT_CANONICAL_ACTUAL_VIEW_RECOVERY',
  unauthorized_admissions=0,stale_as_fresh=0,root_incompatible_views=illegal,false_certified_mode_views=modebad,
  original_deadlines_retained=True,server_input_ACKs=ack_count,prekill_ACKs=len(kill['server_input_ACKs']),
  acknowledged_input_loss_samples=0,offered_frontiers=len(frontiers),certified_coverage=1.,
  paid_submitted_batches=paid_batches,drained_batches=completed_batches,actual_completed_rows=completed_rows,
  abandoned_or_no_receipt_rows=len(alljobs)-len(allres),prekill_durable_commits=prior,total_unique_commits=len(canonical),
  original_episode_wall_seconds=elapsed,resource_lifecycle_seconds_from_origin=outer_end-origin,
  post_serving_log_and_process_teardown_seconds=outer_end-end,
  kill_to_all_previous_certified_consumed_seconds=max(post_recovery.values())-kill['kill_perf'],
  restart_process_launch_to_all_previous_certified_consumed_seconds=max(post_recovery.values())-read(E/'OWNER_HANDLE_1.json')['launch_perf'],
  canonical_journal_recovery_seconds=final['journal_recovery_seconds'],GPU_J_per_offered_audio_second=energy/total,
  GPU_joules_including_killed_work_and_reload=energy,power_coverage=coverage,
  all_offered_audio_goodput_2_8=sum(r['audio_seconds'] for r in frontiers if r['dual_credit'])/elapsed,
  display_P50=export_float(quantile(ds,.5)),display_P95=export_float(quantile(ds,.95)),display_P99=export_float(quantile(ds,.99)),
  commit_P50=export_float(quantile(cs,.5)),commit_P95=export_float(quantile(cs,.95)),commit_P99=export_float(quantile(cs,.99)),
  whole_run_dual_P99_pass=quantile(ds,.99)<=2 and quantile(cs,.99)<=8,
  WER_errors=we,WER_reference_words=wc,all_offered_WER_percent=100*we/wc,English_CER_percent=100*ce/cc,
  accepted_debt_peak_audio_seconds=maxdebt/16000,reserved_debt_peak_audio_seconds=maxcredit/16000,
  prekill_partial_input_tail_bytes=pre_tail,prekill_partial_canonical_tail_bytes=pre_wal_tail,partial_diagnostic_tail_bytes=partial_traces,
  scope='frozen independent formal process-group cold restart; no power-loss, arbitrary-network, natural-rate or speedup claim')

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
 p.add_argument('--runtime-manifest',type=Path,required=True);a=p.parse_args();assert not a.output.exists()
 manifest=read(a.root/'INDEPENDENT_MANIFEST_v1.json');complete=read(a.root/'formal_fault/SUMMARY.json')
 assert complete['cells']==complete['expected']==len(set(complete['completed']))==21 and not (a.root/'formal_fault/STOP.json').exists()
 freeze=read(a.root/'formal_fault/FREEZE.json');runtime=read(a.runtime_manifest);assert runtime['code_commit']==freeze['runtime_commit']
 shas={r['path']:r['sha256'] for r in runtime['files']}
 planned={f"{c['method']}-{c['workload']}-r{c['repeat']}":c for c in freeze['cells']}
 assert list(planned)==complete['completed']
 assert hashlib.sha256((a.root/'INDEPENDENT_MANIFEST_v1.json').read_bytes()).hexdigest()==freeze['source_manifest_sha256']
 out=[]
 for name in complete['completed']:
  E=a.root/'formal_fault'/name;c=planned[name]
  for attempt in [0,1]:
   cfg=read(E/f'attempt{attempt}/config.json');provenance=read(E/f'attempt{attempt}/provenance.json')
   assert cfg['envelope']['method']==c['method'] and cfg['rho']==(1 if c['method']=='fine_fair' else 3)
   assert len(read(E/f'attempt{attempt}/sessions.json'))==c['load']
   assert provenance['code_commit']==runtime['code_commit']
   for file,digest in provenance['source_sha256'].items():assert shas[file]==digest
  out.append(episode(E,manifest))
 result=dict(decision='PASS21_RECORDED_PREFIX_RECOVERY_PENDING_SEPARATE_WAL_AND_ASSET_GATES',runtime_commit=runtime['code_commit'],episodes=out,
  metadata=dict(checker_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),frozen_plan_sha256=hashlib.sha256((a.root/'formal_fault/FREEZE.json').read_bytes()).hexdigest(),
   runtime_manifest_sha256=hashlib.sha256(a.runtime_manifest.read_bytes()).hexdigest(),new_neural_GPU_calls=0))
 a.output.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n');print(json.dumps(dict(episodes=len(out),recorded_accepted_input_loss=sum(r['acknowledged_input_loss_samples'] for r in out))))

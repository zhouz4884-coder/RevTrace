"""Version 2 closed-loop audit: corrected first-successor model identity; original audit retained.

All original certificate/WAL/D1/receipt/lease/Consumer checks remain. Paths and
expected cells are explicit; failed/missing requested runs are retained. Added
visibility persistence metrics are sensitivity measures, not the primary SLO.
"""
from pathlib import Path
from collections import defaultdict
import argparse,dataclasses,traceback
import csv,hashlib,json,math,sys

ap=argparse.ArgumentParser(description=__doc__)
ap.add_argument('--root',type=Path,required=True)
ap.add_argument('--stage',required=True)
ap.add_argument('--source',type=Path,required=True)
ap.add_argument('--output',type=Path,required=True)
ap.add_argument('--model',type=Path,required=True)
ap.add_argument('--references',type=Path,action='append',required=True)
ap.add_argument('--expected-cells',type=Path,required=True)
args=ap.parse_args();O=args.root;stage=args.stage;S=args.source
expected_data=json.loads(args.expected_cells.read_text())
expected_names=expected_data if isinstance(expected_data,list) else expected_data['cells']
expected_names=[r if isinstance(r,str) else r['cell'] for r in expected_names]
assert len(set(expected_names))==len(expected_names)
expected=len(expected_names)
sys.path[:0]=[str(S/'src'),str(S/'scripts')]
from audit_tc_live_qwen import audit as certificates
from audit_dsn_journal import audit as journal
from revtrace.dgft import digest_tokens
from revtrace.live_qwen import fingerprint
from revtrace.certified_display import TrustedQwenRender,ContinuityView
from revtrace.online_admission import gate_candidate,target_identity
from revtrace.row_lifecycle import digest as receipt_digest
from summarize_closed import quantile,quality_counts,good_audio,visibility_sensitivity,clean_json
from revtrace.ces_policy import Target
from revtrace.ces_v5_policy import V5Target
from audit_closed_helpers_v2 import audit_closed_events, CLOSED
from transformers import AutoProcessor,GenerationConfig
from qwen_asr import parse_asr_output

model=args.model;tok=AutoProcessor.from_pretrained(model,local_files_only=True).tokenizer
eos=GenerationConfig.from_pretrained(model,local_files_only=True).eos_token_id;eos=[eos] if isinstance(eos,int) else eos
render=TrustedQwenRender(tok,parse_asr_output,eos,256)
references={}
for manifest in args.references:
 rows=json.loads(manifest.read_text())['sessions']
 for row in rows:
  if row['source_id'] in references:assert references[row['source_id']]==row['reference']
  references[row['source_id']]=row['reference']

def read(p):return json.loads(p.read_text())
def lines(p):return [json.loads(x) for x in p.read_text().splitlines()]
def csvsave(p,rows):
 with p.open('w',newline='',encoding='utf8') as f:
  if rows:
   w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
A=args.output;A.mkdir(parents=True,exist_ok=False)
cells=[];fronts=[];qualities=[];costs=[];checks=[];failures=[]
try:
 for cell_name in sorted(expected_names):
  C=O/stage/cell_name
  if not C.is_dir() or not (C/'result.json').is_file():
   failures.append({'cell':cell_name,'status':'MISSING_OR_INCOMPLETE','requested_cell_retained':True});continue
  sizes=tuple(map(len,(cells,fronts,qualities,costs,checks)))
  try:
   cfg=read(C/'config.json');result=read(C/'result.json');method=cfg['ces_study']['method'];delivery=cfg['result_delivery']
   label=cfg['ces_study'].get('label',C.name.rsplit('-r',1)[0].split('-',3)[-1])
   assert cfg['rho']==1 and cfg['fine_seconds']==2 and cfg['authority_runtime']['dtype']=='float32' and cfg['proposal_runtime']['dtype']=='float16'
   assert cfg['replicas']=={'proposal':[0],'authority':[1]} and delivery=='row'
   cert=certificates(C);provenance=read(C/'provenance.json');wal=journal(Path(provenance['durable_journal_path']))
   es=lines(C/'events.jsonl');vs=lines(C/'consumer.jsonl');rs=lines(C/'worker_records.jsonl');ss=read(C/'sessions.json')
   assert all(r['state']['audio_frontier_window']==0 for r in read(C/'initial_states.json')),'recovery is not a fresh serving comparison'
   t0=next(e['t0_perf'] for e in es if e['kind']=='run-start');byid={r['job']['job_id']:r for r in rs}
   assert len(byid)==len(rs)
   commits=[e for e in es if e['kind']=='commit'];bycommit={(e['session_id'],e['version']):e for e in commits}
   batchrows=defaultdict(list);accounts={}
   if delivery=='row':
    acct=lines(C/'worker_batch_accounting.jsonl')
    accounts={e['batch_id']:e for e in acct};assert len(accounts)==len(acct)
   for rec in rs:
    j,r=rec['job'],rec['result'];assert r['runtime_digest']==j['runtime_digest'] and r['prefix_audio_sha256']==j['prefix_audio_sha256']
    Pout,text=render(j,r['token_ids']);assert Pout==r['state_tokens'] and text==r['text']
    if j['role']=='authority':
     ctx=r['execution_context_audit'];assert ctx['executed_prompt_tokens']==j['prompt_tokens'] and not ctx['fault_override']
     assert r['model_input_audit']['dtype']=='float32'
     assert j['ces_operation']==r['ces_operation'] and j['ces_operation'] in ['generate','verify']
     if method in ['fine','standard']:assert j['ces_operation']=='generate'
     if method=='strict':assert j['ces_operation']=='verify'
     if j['ces_operation']=='verify':
      p=r['online_verification'];assert p['target_identity']==target_identity(j) and p['dtype']=='float32'
      origin=byid[j['candidate_origin_job_id']];assert origin['job']['role']=='proposal'
      assert origin['job']['session_id']==j['session_id'] and origin['job']['source_id']==j['source_id']
      assert origin['result']['token_ids']==j['candidate_token_ids']
      assert origin['result']['received_perf']<=j['enqueue_perf'] and origin['job']['audio_end_sample']==j['audio_end_sample']
      if p['fallback_used']:
       paid=p['fallback_row_compute_seconds_so_far'] if p.get('row_completion_protocol') else p['fallback_batch_seconds']
       assert paid>0 and p['fallback_generated'] and j['job_id'] in p['fallback_executed_job_ids']
      else:
       ok,_=gate_candidate('strict',j['candidate_token_ids'],p['predicted_token_ids'],p['candidate_margins'],eos=p['eos_token_ids'],budget=256,threshold=.05)
       assert ok and r['token_ids']==j['candidate_token_ids']
       z=j['candidate_token_ids'];assert z and len(z)<=256 and z==p['predicted_token_ids'][:len(z)]
       stops=[i for i,t in enumerate(z) if t in p['eos_token_ids']]
       assert stops==[len(z)-1] or (not stops and len(z)==256)
      oracle=p.get('pilot_oracle',{})
      if oracle:
       assert oracle['same_input_repeat_equal'] and all(oracle['oracle_selfchecks']) and all(oracle['accepted_equal_independent_greedy'])
     else:assert 'online_verification' not in r
    if delivery=='row':
     meta=r['_row_receipt'];body={k:v for k,v in r.items() if k not in ['_row_receipt','received_perf','text_binding']}
     assert receipt_digest(body)==meta['payload_sha256']
     assert meta['binding']==j['_delivery']['binding'];bid=r['physical_batch_id']
     inp={k:j.get(k) for k in ['session_id','source_id','role','parent','prompt_tokens','chunk_id','audio_start_sample','audio_end_sample','prefix_audio_sha256','interval_audio_sha256','fault_actual_prompt_tokens','ces_operation','candidate_origin_job_id','candidate_token_ids']}
     assert receipt_digest(inp)==meta['binding']['input_identity']
     assert meta['binding']['batch_id']==bid
     assert meta['terminal_perf']<=meta['rendered_perf']<=meta['emitted_perf']<=r['received_perf']
     assert accounts[bid]['row_receipt_digests'][j['job_id']]==meta['payload_sha256']
     batchrows[bid].append(rec)
    else:batchrows[j['role'],r['started_perf'],r['completed_perf']].append(rec)
   physical=defaultdict(float);role_batches=defaultdict(int);phases=[]
   for key,group in batchrows.items():
    role=group[0]['job']['role'];role_batches[role]+=1
    if role=='authority':assert len({r['job']['ces_operation'] for r in group})==1,'heterogeneous invocation disguised as free batch'
    if delivery=='row':
     ac=accounts[key];assert set(ac['job_ids'])=={r['job']['job_id'] for r in group}
     assert ac['batch_drained_perf']>=max(r['result']['_row_receipt']['emitted_perf'] for r in group)
     assert ac['batch_drained_perf']<=t0+result['wall_seconds_including_arrival_and_drain']+1e-6
     physical[role]+=ac['batch_result_complete_perf']-ac['worker_started_perf'];pp=ac['phases']
     for digest in ac['selected_output_digests']:
      rr=byid[digest['job_id']]['result'];assert digest['Z_sha256']==digest_tokens(rr['token_ids']) and digest['P_sha256']==digest_tokens(rr['state_tokens'])
    else:
     rr=group[0]['result'];physical[role]+=rr['completed_perf']-rr['started_perf']
     pp=rr.get('online_verification',{}).get('phases',[])
     if not pp and rr.get('model_started_perf') is not None:pp=[{'phase':'independent-generate','started_perf':rr['model_started_perf'],'completed_perf':rr['model_completed_perf']}]
    phases.extend(dict(p,role=role) for p in pp)
   # Reuse of a row worker must happen after the previous physical batch drain.
   if delivery=='row':
    perworker=defaultdict(list)
    for bid,ac in accounts.items():perworker[ac['worker']].append(ac)
    for worker,seq in perworker.items():
     seq.sort(key=lambda a:a['worker_started_perf'])
     for prior,later in zip(seq,seq[1:]):
      assert min(byid[j]['job']['enqueue_perf'] for j in later['job_ids'])>=prior['batch_drained_perf']
   saved={(v['session_id'],v['source_kind'],v['server_time']):v for v in vs}
   view=ContinuityView(cfg['consumer_policy'],strict_bound=True)
   for e in es:
    actual=saved.get((e.get('session_id'),e['kind'],e.get('displayed')))
    replay=view.consume(e,actual['consumer_received_perf'] if actual else t0+e['time'])
    if replay:
     assert actual is not None
     for k in ['canonical_version','certified_frontier','certified_text','valid_visible_frontier','visible_text','tentative_invalidated','compatible_provisional_retained','joined_suffix']:assert replay[k]==actual[k]
   assert len(view.records)==len(vs)
   # ACKs must name actual already-applied Consumer observations. Reconstruct
   # the owner's first-visible ledger in event order, including retractions.
   spec_by_sid={s['session_id']:s for s in ss};first_seen={};accepted_acks=[]
   for event in es:
    if event['kind']=='ces-consumer-ack':
     sequence=event['sequence'];assert isinstance(sequence,int) and 1<=sequence<=len(vs)
     actual=vs[sequence-1]
     for key in ['owner_incarnation','contract_digest','session_id','canonical_epoch','canonical_version','valid_visible_frontier','certified_frontier','observed_perf']:
      assert event[key]==actual[key],('ACK differs from actual Consumer',key)
     assert event['ack_received_perf']>=event['observed_perf']
     assert sequence not in accepted_acks;accepted_acks.append(sequence)
     spec=spec_by_sid[event['session_id']];total=round(spec['duration']*16000)
     for window,frontier in enumerate(list(range(32000,total,32000))+[total],1):
      if frontier<=event['valid_visible_frontier']:
       key=event['session_id'],window
       first_seen[key]=min(first_seen.get(key,float('inf')),event['observed_perf'])
    elif event['kind']=='ces-decision' and method in ['risk_cost','progress','progress_joint']+sorted(CLOSED):
     now=event['observed_perf']
     assert all(a['ack_received_perf']<=now for a in es if a['kind']=='ces-consumer-ack' and a['sequence'] in accepted_acks)
     for feature in event['features']:
      applied=first_seen.get((feature['sid'],feature['window']))
      met=applied is not None and applied<=feature['ready']+cfg['ces_study']['display_slo']
      expired=not met and now>feature['ready']+cfg['ces_study']['display_slo']
      assert feature['display_met']==met and feature['display_expired']==expired,'unbacked residual display feature'
   if 'CES_consumer_ack' in result:
    assert result['CES_consumer_ack']['accepted']==len(accepted_acks)
   closed_checks=audit_closed_events(cfg,es,rs,ss,read(C/'initial_states.json'),trusted_render=render,digest_tokens=digest_tokens,fingerprint=fingerprint)
   local=[];quality=[]
   for s in ss:
    sv=[v for v in vs if v['session_id']==s['session_id']];total=round(s['duration']*16000);before=0
    assert max(c['audio_end_sample'] for c in commits if c['session_id']==s['session_id'])==total
    for f in list(range(32000,total,32000))+[total]:
     release=s['offset']+f/16000;d=[v['observed'] for v in sv if v['valid_visible_frontier']>=f]
     co=[c['installed'] for c in commits if c['session_id']==s['session_id'] and c['audio_end_sample']>=f]
     certified=[v['observed'] for v in sv if v['certified_frontier']>=f]
     q={'cell':C.name,'method':label,'delivery':delivery,'source_id':s['source_id'],'frontier_sample':f,
        'audio_seconds':(f-before)/16000,'display':min(d)-release if d else None,'commit':min(co)-release if co else None,
        'certified_consumer':min(certified)-release if certified else None}
     q.update(visibility_sensitivity(sv,f,release,min(co) if co else None))
     local.append(q);before=f
    text=max((v for v in sv if v['certified_frontier']==total),key=lambda v:v['canonical_version'])['certified_text']
    quality.append({'cell':C.name,'source_id':s['source_id'],**quality_counts(references[s['source_id']],text)})
   wall=max(result['wall_seconds_including_arrival_and_drain'],max(v['observed'] for v in vs));audio=sum(s['duration'] for s in ss)
   power=read(C/'power_samples.json')['samples'];energy=0;coverage=[]
   for gpu in {p['gpu'] for p in power}:
    samples=sorted([p for p in power if p['gpu']==gpu],key=lambda p:p['t']);left=t0;right=t0+wall
    coverage.append(max(0.,min(right,samples[-1]['t'])-max(left,samples[0]['t']))/wall)
    for x,y in zip(samples,samples[1:]):
     a,b=max(left,x['t']),min(right,y['t'])
     if b>a:
      interp=lambda t:x['power_w']+(y['power_w']-x['power_w'])*(t-x['t'])/(y['t']-x['t'])
      energy+=(interp(a)+interp(b))*(b-a)/2
   assert len(coverage)==2 and min(coverage)>=.995
   vr=[r for r in rs if r['job']['role']=='authority' and r['job']['ces_operation']=='verify']
   enqueue_events={e['job_id']:e for e in es if e['kind']=='enqueue'}
   wait_sum=sum(max(0.,byid[r['job']['candidate_origin_job_id']]['result']['received_perf']-
       max(r['job']['audio_ready_perf'],enqueue_events[r['job']['job_id']].get('eligible_perf') or r['job']['audio_ready_perf'])) for r in vr)
   source_features=[t for e in es if e['kind']=='ces-decision' for t in e['features']]
   allowed_features={f.name for f in dataclasses.fields(V5Target if method in ['risk_cost','progress','progress_joint']+sorted(CLOSED) else Target)}
   assert all(set(t)==allowed_features for t in source_features)
   assert not any(any(word in key for word in ['fault_label','future_output','injection_label']) for t in source_features for key in t)
   obsolete={e['job_id'] for e in es if e['kind']=='proposal-obsolete'}
   associated=[p for p in phases if p['role']=='proposal' and obsolete.intersection(p['executed_job_ids'])]
   cells.append({'cell':C.name,'method':label,'runtime_method':method,'proposer_order':cfg['ces_study'].get('proposer_order','ready'),'delivery':delivery,'traffic':cfg['ces_study']['traffic'],
    'audio_seconds':audio,'wall_seconds':wall,'Audio_Goodput_2_8':good_audio(local)/wall,
    'Audio_Goodput_certified_consumer_2_8':good_audio(local,commit_key='certified_consumer')/wall,
    'Audio_Goodput_stable_2_8':good_audio(local,display_key='stable_display',commit_key='certified_consumer')/wall,
    'withdrawn_before_certified_frontiers':sum(q['first_visible_withdrawn_before_certified'] for q in local),
    'withdrawn_before_certified_audio_s':sum(q['audio_seconds'] for q in local if q['first_visible_withdrawn_before_certified']),
    'display_P99':quantile([q['display'] for q in local],.99),'commit_P99':quantile([q['commit'] for q in local],.99),
    'display_P50':quantile([q['display'] for q in local],.5),'display_P95':quantile([q['display'] for q in local],.95),
    'commit_P50':quantile([q['commit'] for q in local],.5),'commit_P95':quantile([q['commit'] for q in local],.95),
    'dual_P99_2_8_pass':quantile([q['display'] for q in local],.99)<=2 and quantile([q['commit'] for q in local],.99)<=8,
    'verified_rows':len(vr),'accepted_rows':sum(r['result']['online_verification']['candidate_accepted'] for r in vr),
    'rejected_rows':sum(not r['result']['online_verification']['candidate_accepted'] for r in vr),
    'fallback_rows':sum(r['result']['online_verification']['fallback_used'] for r in vr),
    'fallback_physical_calls':sum(p['phase']=='fresh-FP32-fallback' for p in phases),
    'fallback_executed_rows':sum(p['physical_batch_rows'] for p in phases if p['phase']=='fresh-FP32-fallback'),
    'candidate_wait_before_eligibility_seconds':wait_sum,
    'verified_target_release_to_enqueue_seconds':sum(max(0.,r['job']['enqueue_perf']-r['job']['audio_ready_perf']) for r in vr),
    'CES_explicit_wait_s':sum(e.get('wait_seconds',0) for e in es if e['kind']=='ces-decision' and e['operation'] is None),
    'decision_count':sum(e['kind']=='ces-decision' for e in es),
    'planner_wall_s':result['CES_host_cost']['planner_wall_seconds'],
    'feature_wall_s':result['CES_host_cost']['feature_wall_seconds'],
    'decision_attempts':result['CES_host_cost']['decision_attempts'],
    'obsolete_private_jobs':sum(e['kind']=='proposal-obsolete' for e in es),
    'obsolete_row_latency_sum_s_not_GPU_s':sum(e.get('job_execution_seconds',0) for e in es if e['kind']=='proposal-obsolete'),
    'obsolete_private_generated_tokens':sum(len(byid[jid]['result']['token_ids']) for jid in obsolete),
    'associated_private_physical_calls':len(associated),
    'associated_private_phase_envelope_s_not_exclusive':sum(p['completed_perf']-p['started_perf'] for p in associated),
    'direct_consumed_F2_jobs':sum(r['job']['role']=='proposal' and 'fault_actual_prompt_tokens' in r['job'] for r in rs),
    'GPU_J_audio_s':energy/audio,'WER':sum(q['WER_errors'] for q in quality)/sum(q['reference_words'] for q in quality),
    'peak_sampled_GPU0_MiB':max(p['memory_mib'] for p in power if p['gpu']==0),
    'peak_sampled_GPU1_MiB':max(p['memory_mib'] for p in power if p['gpu']==1),
    'consumer_cpu_s':result['consumer']['consumer_cpu_seconds'],
    'consumer_queue_max_depth':result['consumer']['queue_max_depth'],
    'power_coverage_min':min(coverage),'strict_energy_comparison_eligible':min(coverage)>=.995,
    'CER':sum(q['CER_errors'] for q in quality)/sum(q['reference_characters'] for q in quality),
    'commits':len(commits),'unfinished_sources':0,'capped_authority_admissions':sum(byid[e['job_id']]['result']['hit_token_limit'] for e in commits),
    'visible_audio_rollback_samples':sum(v['audio_rollback_samples'] for v in vs),'erased_characters':sum(v['erased_characters'] for v in vs),
    'physical_fsyncs':sum(e['kind']=='wal-physical-timing' and e['phase']=='fsync' for e in es)})
   fronts.extend(local);qualities.extend(quality)
   for role in ['proposal','authority']:
    pp=[p for p in phases if p['role']==role]
    costs.append({'cell':C.name,'role':role,'physical_batches':role_batches[role],'worker_service_s':physical[role],
       'physical_model_call_wall_s':sum(p['completed_perf']-p['started_perf'] for p in pp),
       'physical_model_calls':len(pp),'not_kernel_active_time_or_row_time_sum':True})
   checks.append({'cell':C.name,'old_certificate_WAL_and_D1_checks':'PASS','actual_consumer_replay':'PASS','immutable_and_physical_lease_checks':'PASS' if delivery=='row' else 'legacy-full-batch','closed_loop_checks':closed_checks,'generation_budget_boundary':'TOKEN_LIMIT_BOUNDARY_RETAINED' if any(byid[e['job_id']]['result']['hit_token_limit'] for e in commits) else 'NO_CAP_HIT'})
   print('AUDITED',C.name,flush=True)
  except Exception as cell_error:
   for array,size in zip((cells,fronts,qualities,costs,checks),sizes):del array[size:]
   failures.append({'cell':cell_name,'status':'FAILED_AUDIT','error':repr(cell_error),'traceback':traceback.format_exc(),'requested_cell_retained':True})
   print('AUDIT_FAILED',cell_name,repr(cell_error),flush=True)

 assert len(cells)+len(failures)==expected,(len(cells),len(failures),expected)
 for name,rs in [('SERVICE_CELLS.csv',cells),('COMMON_FRONTIERS.csv',fronts),('SOURCE_QUALITY.csv',qualities),('PHYSICAL_COSTS.csv',costs)]:csvsave(A/name,rs)
 report={'status':'PASS_FRESH_ROW_SERVING_SAFETY_AND_METRIC_AUDIT' if not failures else 'INCOMPLETE_OR_FAILED_NO_SUPERIORITY_CLAIM','cells':len(cells),'expected_cells':expected,'failures':failures,'checks':checks,
   'new_model_calls':0,'pilot_not_formal_superiority':True,'actual_model_calls':sum(row['physical_model_calls'] for row in costs),'sources_reused_for_diagnosis':True,'source_scope':'Reused sources: closed-loop diagnostic; not independent confirmation',
   'all_failed_requested_cells_retained_no_partial_superiority_claim':True,
   'TOKEN_LIMIT_BOUNDARY_is_retained_not_silently_filtered':True,
   'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
 (A/'SUMMARY.json').write_text(json.dumps(clean_json(report),indent=2,allow_nan=False)+'\n');print(json.dumps({k:v for k,v in report.items() if k!='checks'}))
except BaseException as e:
 (A/'STOP.json').write_text(json.dumps({'error':repr(e),'audited_cells':len(cells),'raw_preserved':True})+'\n');raise





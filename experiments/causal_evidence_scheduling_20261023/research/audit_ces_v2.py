"""Fresh-cell audit: old safety predicates plus new immutable/physical evidence."""
from pathlib import Path
from collections import defaultdict
import csv,hashlib,json,math,sys

B=Path(sys.argv[1]);stage=sys.argv[2];expected=int(sys.argv[3]);S=Path(sys.argv[4])
O=B/'results/revtrace/ces_20261023';P=B/'projects/revtrace_ces_20261023'
sys.path[:0]=[str(S/'src'),str(S/'scripts'),str(B/'projects/revtrace_online_admission_20261022')]
from audit_tc_live_qwen import audit as certificates
from audit_dsn_journal import audit as journal
from revtrace.dgft import digest_tokens
from revtrace.live_qwen import fingerprint
from revtrace.certified_display import TrustedQwenRender,ContinuityView
from revtrace.online_admission import gate_candidate,target_identity
from revtrace.row_lifecycle import digest as receipt_digest
from analysis_core import quantile,quality_counts,good_audio
from transformers import AutoProcessor,GenerationConfig
from qwen_asr import parse_asr_output

model=B/'models/Qwen3-ASR-1.7B';tok=AutoProcessor.from_pretrained(model,local_files_only=True).tokenizer
eos=GenerationConfig.from_pretrained(model,local_files_only=True).eos_token_id;eos=[eos] if isinstance(eos,int) else eos
render=TrustedQwenRender(tok,parse_asr_output,eos,256)
references={r['source_id']:r['reference'] for r in json.loads((B/'datasets/revtrace/phaseD_20261021/manifest.json').read_text())['sessions']}
validation=B/'results/revtrace/row_completion_20261023/validation_source_v1/MANIFEST.json'
if validation.exists():
 extra=json.loads(validation.read_text())['sessions'];assert not set(references)&{r['source_id'] for r in extra}
 references.update({r['source_id']:r['reference'] for r in extra})
def read(p):return json.loads(p.read_text())
def lines(p):return [json.loads(x) for x in p.read_text().splitlines()]
def csvsave(p,rows):
 with p.open('w',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
A=O/(stage+'_independent_audit_v2');A.mkdir(exist_ok=False)
cells=[];fronts=[];qualities=[];costs=[];checks=[]
try:
 for C in sorted((O/stage).iterdir()):
  if not C.is_dir() or not (C/'result.json').is_file():continue
  cfg=read(C/'config.json');result=read(C/'result.json');method=cfg['ces_study']['method'];delivery=cfg['result_delivery']
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
    assert j['ces_operation']==r['ces_operation'] and j['ces_operation'] in ['generate','verify']
    if method in ['fine','standard']:assert j['ces_operation']=='generate'
    if method=='strict':assert j['ces_operation']=='verify'
    if j['ces_operation']=='verify':
     p=r['online_verification'];assert p['target_identity']==target_identity(j) and p['dtype']=='float32'
     origin=byid[j['candidate_origin_job_id']];assert origin['job']['role']=='proposal'
     assert origin['result']['token_ids']==j['candidate_token_ids']
     assert origin['result']['received_perf']<=j['enqueue_perf'] and origin['job']['audio_end_sample']==j['audio_end_sample']
     if p['fallback_used']:
      paid=p['fallback_row_compute_seconds_so_far'] if p.get('row_completion_protocol') else p['fallback_batch_seconds']
      assert paid>0 and p['fallback_generated'] and j['job_id'] in p['fallback_executed_job_ids']
     else:
      ok,_=gate_candidate('strict',j['candidate_token_ids'],p['predicted_token_ids'],p['candidate_margins'],eos=p['eos_token_ids'],budget=256,threshold=.05)
      assert ok and r['token_ids']==j['candidate_token_ids']
     oracle=p.get('pilot_oracle',{})
     if oracle:
      assert oracle['same_input_repeat_equal'] and all(oracle['oracle_selfchecks']) and all(oracle['accepted_equal_independent_greedy'])
    else:assert 'online_verification' not in r
   if delivery=='row':
    meta=r['_row_receipt'];body={k:v for k,v in r.items() if k not in ['_row_receipt','received_perf','text_binding']}
    assert receipt_digest(body)==meta['payload_sha256']
    assert meta['binding']==j['_delivery']['binding'];bid=r['physical_batch_id']
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
  local=[];quality=[]
  for s in ss:
   sv=[v for v in vs if v['session_id']==s['session_id']];total=round(s['duration']*16000);before=0
   assert max(c['audio_end_sample'] for c in commits if c['session_id']==s['session_id'])==total
   for f in list(range(32000,total,32000))+[total]:
    release=s['offset']+f/16000;d=[v['observed'] for v in sv if v['valid_visible_frontier']>=f]
    co=[c['installed'] for c in commits if c['session_id']==s['session_id'] and c['audio_end_sample']>=f]
    certified=[v['observed'] for v in sv if v['certified_frontier']>=f]
    q={'cell':C.name,'method':method,'delivery':delivery,'source_id':s['source_id'],'frontier_sample':f,
       'audio_seconds':(f-before)/16000,'display':min(d)-release if d else None,'commit':min(co)-release if co else None,
       'certified_consumer':min(certified)-release if certified else None}
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
  assert len(coverage)==2 and min(coverage)>=(.98 if stage=='pilot_v1' else .995)
  vr=[r for r in rs if r['job']['role']=='authority' and r['job']['ces_operation']=='verify']
  enqueue_events={e['job_id']:e for e in es if e['kind']=='enqueue'}
  wait_sum=sum(max(0.,byid[r['job']['candidate_origin_job_id']]['result']['received_perf']-
      max(r['job']['audio_ready_perf'],enqueue_events[r['job']['job_id']].get('eligible_perf') or r['job']['audio_ready_perf'])) for r in vr)
  source_features=[t for e in es if e['kind']=='ces-decision' for t in e['features']]
  assert all(set(t)=={'sid','window','ready','deadline','candidate_ready','same_birth','previous_reject','candidate_tokens','descendant_count','descendant_seconds','candidate_eta'} for t in source_features)
  cells.append({'cell':C.name,'method':method,'delivery':delivery,'traffic':cfg['ces_study']['traffic'],
   'audio_seconds':audio,'wall_seconds':wall,'Audio_Goodput_2_8':good_audio(local)/wall,
   'display_P99':quantile([q['display'] for q in local],.99),'commit_P99':quantile([q['commit'] for q in local],.99),
   'display_P50':quantile([q['display'] for q in local],.5),'display_P95':quantile([q['display'] for q in local],.95),
   'commit_P50':quantile([q['commit'] for q in local],.5),'commit_P95':quantile([q['commit'] for q in local],.95),
   'dual_P99_2_8_pass':quantile([q['display'] for q in local],.99)<=2 and quantile([q['commit'] for q in local],.99)<=8,
   'verified_rows':len(vr),'accepted_rows':sum(r['result']['online_verification']['candidate_accepted'] for r in vr),
   'fallback_rows':sum(r['result']['online_verification']['fallback_used'] for r in vr),
   'candidate_wait_before_eligibility_seconds':wait_sum,
   'verified_target_release_to_enqueue_seconds':sum(max(0.,r['job']['enqueue_perf']-r['job']['audio_ready_perf']) for r in vr),
   'CES_explicit_wait_s':sum(e.get('wait_seconds',0) for e in es if e['kind']=='ces-decision' and e['operation'] is None),
   'decision_count':sum(e['kind']=='ces-decision' for e in es),
   'obsolete_private_jobs':sum(e['kind']=='proposal-obsolete' for e in es),
   'obsolete_private_service_s':sum(e.get('job_execution_seconds',0) for e in es if e['kind']=='proposal-obsolete'),
   'direct_consumed_F2_jobs':sum(r['job']['role']=='proposal' and 'fault_actual_prompt_tokens' in r['job'] for r in rs),
   'GPU_J_audio_s':energy/audio,'WER':sum(q['WER_errors'] for q in quality)/sum(q['reference_words'] for q in quality),
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
  checks.append({'cell':C.name,'old_certificate_WAL_and_D1_checks':'PASS','actual_consumer_replay':'PASS','immutable_and_physical_lease_checks':'PASS' if delivery=='row' else 'legacy-full-batch'})
  print('AUDITED',C.name,flush=True)
 assert len(cells)==expected,(len(cells),expected)
 for name,rs in [('SERVICE_CELLS.csv',cells),('COMMON_FRONTIERS.csv',fronts),('SOURCE_QUALITY.csv',qualities),('PHYSICAL_COSTS.csv',costs)]:csvsave(A/name,rs)
 report={'status':'PASS_FRESH_ROW_SERVING_SAFETY_AND_METRIC_AUDIT','cells':len(cells),'checks':checks,
   'new_model_calls':0,'pilot_not_formal_superiority':stage.startswith('row_live_pilot'),
   'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
 (A/'SUMMARY.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n');print(json.dumps({k:v for k,v in report.items() if k!='checks'}))
except BaseException as e:
 (A/'STOP.json').write_text(json.dumps({'error':repr(e),'audited_cells':len(cells),'raw_preserved':True})+'\n');raise

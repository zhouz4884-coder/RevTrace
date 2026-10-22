"""Independent read-only raw replay; CPU analysis of real GPU serving evidence."""
from pathlib import Path
from collections import defaultdict
import csv,hashlib,json,math,re,sys,unicodedata
B=Path(sys.argv[1]);stage=sys.argv[2];expected=int(sys.argv[3]);P=B/'projects/revtrace_online_admission_20261022';O=B/'results/revtrace/online_admission_20261022';S=P/('pilot_sdk_v2' if stage=='pilot_v2' else 'pilot_sdk_v3');sys.path[:0]=[str(S/'src'),str(S/'scripts')]
from audit_tc_live_qwen import audit as audit_certificate
from audit_dsn_journal import audit as audit_journal
from revtrace.dgft import digest_tokens
from transformers import AutoProcessor
from qwen_asr import parse_asr_output
tok=AutoProcessor.from_pretrained(B/'models/Qwen3-ASR-1.7B',local_files_only=True).tokenizer
manifest=json.loads((O/'PILOT_MANIFEST.json').read_text()) if stage.startswith('pilot') else json.loads((B/'datasets/revtrace/phaseD_20261021/manifest.json').read_text())
reference={x['source_id']:x['reference'] for x in manifest['sessions']}
def read(p):return json.loads(p.read_text())
def lines(p):return [json.loads(s) for s in p.read_text().splitlines()]
def sha(raw):return hashlib.sha256(raw).hexdigest()
def q99(xs):
 if not xs:return None
 xs=sorted(math.inf if x is None else x for x in xs);k=(len(xs)-1)*.99;i=int(k);f=k-i
 value=xs[i] if not f else math.inf if math.isinf(xs[min(i+1,len(xs)-1)]) else xs[i]+(xs[min(i+1,len(xs)-1)]-xs[i])*f
 return None if math.isinf(value) else value
def dist(a,b):
 r=list(range(len(b)+1))
 for i,x in enumerate(a,1):
  z=[i]
  for j,y in enumerate(b,1):z.append(min(z[-1]+1,r[j]+1,r[j-1]+(x!=y)))
  r=z
 return r[-1]
def words(t):return re.findall(r"[a-z0-9']+",unicodedata.normalize('NFKC',t).lower())
def chars(t):return [x for x in unicodedata.normalize('NFKC',t).lower() if x.isalnum()]
def prefix(j,actual=False):
 ids=j.get('fault_actual_prompt_tokens',j['prompt_tokens']) if actual else j['prompt_tokens'];raw=tok.decode(ids,skip_special_tokens=False,clean_up_tokenization_spaces=False)
 if j['chunk_id']<2 or not raw:return ''
 ids=tok.encode(raw);k=5
 while True:
  out=tok.decode(ids[:max(0,len(ids)-k)])
  if '\ufffd' not in out or k>=len(ids):return out
  k+=1
def render(j,Z,actual=False):
 raw=prefix(j,actual)+tok.decode(Z,skip_special_tokens=True,clean_up_tokenization_spaces=False);_,text=parse_asr_output(raw,user_language=j['language']);return tok.encode(raw),text
def shape(Z,pred,eos,budget):
 if not Z or len(Z)>budget:return False
 stops=[i for i,t in enumerate(Z) if t in eos]
 if stops and stops!=[len(Z)-1]:return False
 if not stops and len(Z)!=budget:return False
 return len(pred)>=len(Z) and list(Z)==list(pred[:len(Z)])
def dumpcsv(p,rs):
 if not rs:return
 with p.open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=list(rs[0]));w.writeheader();w.writerows(rs)
cells=[];frontiers=[];costs=[];rounds=[];source_quality=[];proofs=[];faults=[];clock_rows=[];physical_phases=[];selection_checks=[]
formal=stage=='formal_v1'
frozen=read(O/'FORMAL_FREEZE.json') if formal else None
frozen_names={f"{x['method']}-{x['load']}-{x['traffic']}-r{x['repeat']}" for x in frozen['matrix']} if formal else None
if formal:
 assert expected==72 and len(frozen_names)==72
 assert read(O/'FORMAL_SUMMARY.json')['status']=='COMPLETE_72_FRESH_ONLINE_FORMAL_CELLS'
 assert not (O/'STOP_FORMAL_v1.json').exists()
source_manifest=read(S/'SOURCE_MANIFEST.json');source_identities={r['path']:r['sha256'] for r in source_manifest['files']}
for c in sorted((O/stage).iterdir()):
 if not c.is_dir() or not (c/'result.json').exists():continue
 cfg=read(c/'config.json');method=cfg['online_study']['method'];traffic=cfg['online_study']['traffic'];res=read(c/'result.json');ss=read(c/'sessions.json');es=lines(c/'events.jsonl');vs=lines(c/'consumer.jsonl');wr=lines(c/'worker_records.jsonl');records={r['job']['job_id']:r for r in wr};t0=next(e['t0_perf'] for e in es if e['kind']=='run-start');provenance=read(c/'provenance.json')
 if formal:
  assert c.name in frozen_names and provenance['code_commit']==frozen['runtime_code_commit']
  assert provenance['manifest_sha256']==frozen['source_manifest_sha256']
  assert all(source_identities[k]==v for k,v in provenance['source_sha256'].items())
  assert len(ss)==len({s['source_id'] for s in ss})==16
 cert=audit_certificate(c);journal=audit_journal(Path(read(c/'provenance.json')['durable_journal_path']),c);proofs.append({'cell':c.name,'certificate':cert,'journal':journal,'structural_replay_not_a_claim_unsafe_has_trusted_selection':True})
 assert cfg['display_protocol']=='canonical-snapshot-v1' and cfg['trusted_text_binding'] and cfg['journal_mode']=='durable'
 commits=[e for e in es if e['kind']=='commit'];pubs={(e['session_id'],e['version']):e for e in es if e['kind']=='canonical-display'};F=defaultdict(int);H=defaultdict(list);selected={};by_batch=defaultdict(list);phase_cost={};bad=good=fa=fr=accepted=fallback=0
 for rr in wr:
  j,r=rr['job'],rr['result'];assert r['runtime_digest']==j['runtime_digest'];a=r['execution_context_audit'];actual=j.get('fault_actual_prompt_tokens',j['prompt_tokens'])
  assert a['executed_prompt_tokens']==actual and a['declared_prompt_digest']==digest_tokens(j['prompt_tokens']) and a['executed_prompt_digest']==digest_tokens(actual)
  assert a['actual_audio_sha256']==r['prefix_audio_sha256']==j['prefix_audio_sha256'];assert a['conditioning_prefix_sha256']==sha(prefix(j,True).encode())
  assert j['audio_ready_perf']<=j['enqueue_perf']<=r['started_perf']<=r['completed_perf']<=r['received_perf']
  ai=r['model_input_audit'];assert ai['rollback_prefix']==prefix(j,True) and ai['waveform_sha256']==j['prefix_audio_sha256'] and ai['audio_end_sample']==j['audio_end_sample']
  if 'fault_actual_prompt_tokens' in j:
   actualP,actualtext=render(j,r['token_ids'],True);assert actualP==r['F2_raw_execution_state_tokens'] and actualtext==r['F2_raw_execution_text']
   faults.append({'cell':c.name,'method':method,'traffic':traffic,'session_id':j['session_id'],'source_id':j['source_id'],'job_id':j['job_id'],'end_window':j['end_window'],'chunk_id':j['chunk_id'],'conditioning_changed':prefix(j,True)!=prefix(j),'raw_projection_differs_normalized':actualP!=r['state_tokens'],'declared_prompt_sha256':digest_tokens(j['prompt_tokens']),'executed_prompt_sha256':digest_tokens(actual),'fault_kind':'controlled_actual_context_then_declared_parent_field_reconstruction'})
  Pnew,text=render(j,r['token_ids']);assert Pnew==r['state_tokens'] and text==r['text']
  by_batch[j['role'],r['started_perf'],r['completed_perf']].append(rr)
  clock_rows.append({'cell':c.name,'method':method,'traffic':traffic,'role':j['role'],'job_id':j['job_id'],'source_id':j['source_id'],'audio_ready_perf':j['audio_ready_perf'],'enqueue_perf':j['enqueue_perf'],'worker_started_perf':r['started_perf'],'worker_completed_perf':r['completed_perf'],'owner_received_perf':r['received_perf'],'audio_ready_to_enqueue_s':j['enqueue_perf']-j['audio_ready_perf'],'worker_queue_s':r['started_perf']-j['enqueue_perf'],'worker_service_s':r['completed_perf']-r['started_perf'],'completion_to_owner_receipt_s':r['received_perf']-r['completed_perf'],'new_tokens':len(r['token_ids']),'hit_token_limit':r['hit_token_limit'],'not_a_physical_batch_sum':True})
  proof=r.get('online_verification')
  if proof:
   assert j['role']=='authority' and proof['mode']==method and proof['dtype']=='float32' and not proof['context_override_used']
   assert proof['executed_prompt_tokens']==j['prompt_tokens'] and proof['actual_audio_sha256']==j['prefix_audio_sha256']
   candidate=j['candidate_token_ids'];strict_ok=shape(candidate,proof['predicted_token_ids'],proof['eos_token_ids'],cfg['authority_runtime']['max_new_tokens']) if method!='unprotected' else None
   decision=proof['candidate_accepted'];fb=proof['fallback_used'];assert decision!=fb
   if method=='strict':assert decision==strict_ok
   if method=='score':
    score=proof['candidate_margins'];assert decision==(shape(candidate,candidate,proof['eos_token_ids'],cfg['authority_runtime']['max_new_tokens']) and len(score)>=len(candidate) and all(math.isfinite(x) and x>=.05 for x in score[:len(candidate)]))
   if fb:assert proof['fallback_generated'] and proof['fallback_batch_seconds']>0
   else:assert r['token_ids']==candidate
   accepted+=decision;fallback+=fb
   if strict_ok is not None:
    bad+=not strict_ok;good+=strict_ok;fa+=decision and not strict_ok;fr+=not decision and strict_ok
   for phase in proof['phases']:
    key=(phase['phase'],phase['started_perf'],phase['completed_perf']);phase_cost[key]=phase
   origin=records[j['candidate_origin_job_id']];assert origin['result']['completed_perf']==j['candidate_ready_perf']
   assert origin['result']['received_perf']<=j['enqueue_perf'] and origin['result']['completed_perf']<=origin['result']['received_perf']
   rounds.append({'cell':c.name,'method':method,'traffic':traffic,'session_id':j['session_id'],'source_id':j['source_id'],'parent':j['parent'],'job_id':j['job_id'],'candidate_origin_job_id':j['candidate_origin_job_id'],'candidate_ready_perf':j['candidate_ready_perf'],'candidate_owner_received_perf':origin['result']['received_perf'],'target_enqueue_perf':j['enqueue_perf'],'audio_ready_to_enqueue_s':j['enqueue_perf']-j['audio_ready_perf'],'audio_ready_to_candidate_GPU_completion_s':max(0.,origin['result']['completed_perf']-j['audio_ready_perf']),'candidate_receipt_to_target_enqueue_s':j['enqueue_perf']-origin['result']['received_perf'],'candidate_tokens':len(candidate),'candidate_actual_F2_origin':'fault_actual_prompt_tokens' in origin['job'],'accepted':decision,'fallback':fb,'strict_complete_against_same_target_forward':strict_ok,'independent_greedy_oracle_label':None,'offered_P_matches_reconstruction':proof['offered_projection_equal_target_render']})
 for key,group in by_batch.items():
  if group[0]['result'].get('online_verification'):
   for i,rr in enumerate(group):
    j,r=rr['job'],rr['result'];proof=r['online_verification'];assert proof['physical_batch_rows']==len(group)
    oracle=proof['pilot_oracle']
    if method in ['strict','score'] and cfg['online_study']['oracle_diagnostic']:
     assert oracle['same_input_repeat_equal'] and all(oracle['oracle_selfchecks']) and all(oracle['accepted_equal_independent_greedy'])
     assert not proof['candidate_accepted'] or j['candidate_token_ids']==oracle['oracle_token_ids'][i]
     if proof['fallback_used'] and 'fallback_layout_repeat_equal' in oracle:assert oracle['fallback_layout_repeat_equal'] and all(oracle['fallback_layout_selfchecks'])
     row=next(z for z in rounds if z['cell']==c.name and z['job_id']==j['job_id']);row['independent_greedy_oracle_label']=j['candidate_token_ids']==oracle['oracle_token_ids'][i]
    if 'fallback_row_indices' in proof and proof['fallback_generated']:
     failed=[k for k,other in enumerate(group) if other['result']['online_verification']['fallback_used']]
     separable=all(v['shape'] and v['shape'][0]==len(group) for v in r['model_input_audit']['batch_tensors'].values())
     expected_rows=failed if proof['fallback_requested_layout']=='selective' and separable else list(range(len(group)))
     assert proof['fallback_row_indices']==expected_rows and proof['fallback_batch_rows']==len(expected_rows)
     assert proof['fallback_executed_job_ids']==[group[k]['job']['job_id'] for k in expected_rows]
     for pos,k in enumerate(expected_rows):
      assert proof['fallback_input_ids'][pos]==group[k]['result']['model_input_audit']['input_ids']
      assert proof['fallback_input_row_origins'][pos]==group[k]['result']['model_input_audit']
 for e in commits:
  j,r=records[e['job_id']]['job'],records[e['job_id']]['result'];sid=e['session_id'];assert j['audio_start_sample']==F[sid] and j['prompt_tokens']==H[sid];F[sid]=j['audio_end_sample'];H[sid]=r['state_tokens'];assert r['token_ids']==e['segment_tokens'] and r['state_tokens']==e['next_prompt_tokens']
  pub=pubs[sid,e['version']];assert pub['text']==r['text'] and pub['displayed']>=e['installed'];selected[sid,e['version']]=(pub['text'],e['audio_end_sample'])
  selection_checks.append({'cell':c.name,'method':method,'traffic':traffic,'job_id':j['job_id'],'source_id':j['source_id'],'parent':j['parent'],'version':e['version'],'audio_start_sample':j['audio_start_sample'],'audio_end_sample':j['audio_end_sample'],'Z_sha256':digest_tokens(r['token_ids']),'P_sha256':digest_tokens(r['state_tokens']),'installed':e['installed'],'canonical_published':pub['displayed'],'terminated_by_eos':r.get('terminated_by_eos'),'hit_token_limit':r['hit_token_limit'],'trust_path':'unsafe-candidate-not-certified-selection' if method=='unprotected' else 'correct-context-verify-or-paid-fallback' if method in ['score','strict'] else 'independent-FP32-authority','selected_shape_valid':shape(r['token_ids'],r['token_ids'],r['model_input_audit']['eos_token_ids'],cfg['authority_runtime']['max_new_tokens'])})
 for v in vs:
  if v['canonical_version']:
   text,f=selected[v['session_id'],v['canonical_version']];assert v['certified_text']==text and v['certified_frontier']==f
 wall=max(res['wall_seconds_including_arrival_and_drain'],max((v['observed'] for v in vs),default=0));audio=sum(s['duration'] for s in ss);qs=[];we=wn=ce=cn=0
 for s in ss:
  sid=s['session_id'];total=round(s['duration']*16000);before=0;sv=[v for v in vs if v['session_id']==sid]
  for q in list(range(32000,total,32000))+[total]:
   release=s['offset']+q/16000;dt=[v['observed'] for v in sv if v['valid_visible_frontier']>=q];ct=[e['installed'] for e in commits if e['session_id']==sid and e['audio_end_sample']>=q];cc=[v['observed'] for v in sv if v['certified_frontier']>=q]
   qs.append({'cell':c.name,'method':method,'traffic':traffic,'session_id':sid,'source_id':s['source_id'],'frontier_sample':q,'release':release,'display':min(dt)-release if dt else None,'commit':min(ct)-release if ct else None,'certified_consumer':min(cc)-release if cc else None,'audio_seconds':(q-before)/16000});before=q
  versions=[e['version'] for e in commits if e['session_id']==sid];text=selected[sid,max(versions)][0] if versions else '';ref=reference[s['source_id']];w=dist(words(ref),words(text));n=len(words(ref));a=dist(chars(ref),chars(text));b=len(chars(ref));we+=w;wn+=n;ce+=a;cn+=b
  source_quality.append({'cell':c.name,'method':method,'traffic':traffic,'source_id':s['source_id'],'session_id':sid,'WER_errors':w,'reference_words':n,'CER_errors':a,'reference_characters':b,'final_frontier_complete':F[sid]==total,'final_canonical_text':text,'reference':ref})
 frontiers.extend(qs);power=defaultdict(list)
 for z in read(c/'power_samples.json')['samples']:power[z['gpu']].append(z)
 energy=0.;coverage=[];left=t0;right=t0+wall
 for samples in power.values():
  samples.sort(key=lambda z:z['t']);coverage.append(max(0,min(right,samples[-1]['t'])-max(left,samples[0]['t']))/wall)
  for x,y in zip(samples,samples[1:]):
   a,b=max(left,x['t']),min(right,y['t'])
   if b<=a:continue
   def watts(t):return x['power_w']+(y['power_w']-x['power_w'])*(t-x['t'])/(y['t']-x['t'])
   energy+=(watts(a)+watts(b))*(b-a)/2
 assert len(power)==2 and min(coverage)>=.995
 for key,group in by_batch.items():
  r=group[0]['result'];pp=r.get('online_verification',{}).get('phases',[])
  assert all(z['result'].get('online_verification',{}).get('phases',[])==pp for z in group)
  if pp:
   for p in pp:physical_phases.append({'cell':c.name,'method':method,'traffic':traffic,'role':key[0],'phase':p['phase'],'started_perf':p['started_perf'],'completed_perf':p['completed_perf'],'seconds':p['completed_perf']-p['started_perf'],'physical_rows':p['physical_batch_rows'],'executed_job_ids':p['executed_job_ids']})
  elif r.get('model_started_perf') is not None:
   physical_phases.append({'cell':c.name,'method':method,'traffic':traffic,'role':key[0],'phase':'independent-generate','started_perf':r['model_started_perf'],'completed_perf':r['model_completed_perf'],'seconds':r['model_completed_perf']-r['model_started_perf'],'physical_rows':len(group),'executed_job_ids':[z['job']['job_id'] for z in group]})
 for role in ['proposal','authority']:
  batches=[(k,g) for k,g in by_batch.items() if k[0]==role];modelspans=set((g[0]['result']['model_started_perf'],g[0]['result']['model_completed_perf']) for k,g in batches if g[0]['result'].get('model_started_perf') is not None and not g[0]['result'].get('online_verification'))
  pphases=list(phase_cost.values()) if role=='authority' else []
  fallback_names=['fresh-FP32-fallback','full-layout-FP32-fallback']
  costs.append({'cell':c.name,'method':method,'traffic':traffic,'role':role,'physical_worker_batches':len(batches),'worker_service_seconds':sum(k[2]-k[1] for k,g in batches),'normal_model_calls':len(modelspans),'normal_model_seconds':sum(b-a for a,b in modelspans),'verification_calls':sum(x['phase'].startswith('correct-context') for x in pphases),'verification_seconds':sum(x['completed_perf']-x['started_perf'] for x in pphases if x['phase'].startswith('correct-context')),'fallback_calls':sum(x['phase'] in fallback_names for x in pphases),'fallback_seconds':sum(x['completed_perf']-x['started_perf'] for x in pphases if x['phase'] in fallback_names),'diagnostic_oracle_calls':sum(x['phase'].startswith('pilot') for x in pphases),'diagnostic_oracle_seconds':sum(x['completed_perf']-x['started_perf'] for x in pphases if x['phase'].startswith('pilot'))})
 cpu_file=O/stage/(c.name+'.CPU_IO.txt');cpu_text=cpu_file.read_text() if cpu_file.exists() else ''
 def cpu_value(label):
  m=re.search(r'^\s*'+re.escape(label)+r':\s*(.*)$',cpu_text,re.M);return m.group(1).strip() if m else None
 wal_owner_starts=[e for e in es if e['kind']=='wal-owner-start'];wal_owner_ends=[e for e in es if e['kind']=='wal-owner-complete'];assert len(wal_owner_starts)==len(wal_owner_ends)
 owner_wall=0.
 for a,b in zip(wal_owner_starts,wal_owner_ends):assert a['job_ids']==b['job_ids'];owner_wall+=b['time']-a['time']
 physical_io={p:sum(e['completed']-e['started'] for e in es if e['kind']=='wal-physical-timing' and e['phase']==p) for p in ['write','fsync']}
 cells.append({'cell':c.name,'method':method,'traffic':traffic,'unique_sources':len(ss),'audio_seconds':audio,'wall_seconds':wall,'Audio_Goodput_2_8':sum(q['audio_seconds'] for q in qs if q['display'] is not None and q['commit'] is not None and q['display']<=2 and q['commit']<=8)/wall,'display_P99':q99([q['display'] for q in qs]),'commit_P99':q99([q['commit'] for q in qs]),'certified_consumer_P99':q99([q['certified_consumer'] for q in qs]),'GPU_strict_J_audio_s':energy/audio,'minimum_power_window_coverage':min(coverage),'maximum_power_sample_gap_s':max(y['t']-x['t'] for samples in power.values() for x,y in zip(samples,samples[1:])),'WER':we/wn,'CER':ce/cn,'certified_commits':len(commits),'candidate_accepts':accepted,'fallback_rows':fallback,'same_forward_bad_candidates':bad,'same_forward_good_candidates':good,'false_acceptance_against_complete_forward':fa,'false_rejection_against_complete_forward':fr,'token_limit_events':res['token_limit_events'],'capped_authority_admissions':sum(records[e['job_id']]['result']['hit_token_limit'] for e in commits),'unfinished_sources':sum(F[s['session_id']]!=round(s['duration']*16000) for s in ss),'frontiers':len(qs),'render_host_wall_s':sum(e['host_cpu_wall_seconds'] for e in es if e['kind']=='render-checked'),'wal_owner_wall_s':owner_wall,'physical_wal_write_s':physical_io['write'],'physical_fsync_s':physical_io['fsync'],'wal_bytes':Path(provenance['durable_journal_path']).stat().st_size,'consumer_cpu_s':res['consumer']['consumer_cpu_seconds'],'consumer_queue_max_depth':res['consumer']['queue_max_depth'],'worker_initialization_outside_serving_s':res['worker_initialization_seconds'],'whole_process_user_s':cpu_value('User time (seconds)'),'whole_process_system_s':cpu_value('System time (seconds)'),'whole_process_max_RSS_KiB':cpu_value('Maximum resident set size (kbytes)'),'whole_process_filesystem_outputs':cpu_value('File system outputs'),'pilot_diagnostic_not_formal_performance':cfg['online_study']['oracle_diagnostic']})
 print('audited',c.name,flush=True)
A=O/(stage+'_audit_v3');A.mkdir(exist_ok=True)
if formal:assert {x['cell'] for x in cells}==frozen_names
for n,rs in [('SERVICE_CELLS.csv',cells),('COST_DECOMPOSITION.csv',costs),('CANDIDATE_ROUNDS.csv',rounds),('SOURCE_QUALITY.csv',source_quality),('COMMON_FRONTIERS.csv',frontiers),('F2_ACTUAL_INPUT.csv',faults),('JOB_CLOCKS.csv',clock_rows),('PHYSICAL_MODEL_PHASES.csv',physical_phases),('SELECTION_AND_ADMISSION.csv',selection_checks)]:dumpcsv(A/n,rs)
(A/'PROOFS.json').write_text(json.dumps(proofs,indent=2)+'\n')
status=('PASS_COMPLETE_FORMAL_RAW_REPLAY' if formal else 'PASS_COMPLETE_PILOT_MECHANISM_AUDIT') if len(cells)==expected else 'PARTIAL_AUDIT_NOT_A_FORMAL_LAUNCH_GATE'
(A/'AUDIT_REPORT.json').write_text(json.dumps({'status':status,'cells':len(cells),'expected':expected,'source_commit':source_manifest['code_commit'],'audit_script_sha256':sha(Path(__file__).read_bytes()),'formal_launch_allowed_by_this_partial_script':False,'unsafe_negative_control_not_certified_selection':True,'independent_greedy_Oracle_scope':'only explicitly executed diagnostic rows; all other generated-Oracle labels unknown pending post-serving replay','actual_processor_feature_replay':'separate CPU all-tensor replay required; this script audits logged identities, not recomputed features','unfinished_sources':sum(c['unfinished_sources'] for c in cells),'performance_claim':False},indent=2)+'\n')
print(status,len(cells))
